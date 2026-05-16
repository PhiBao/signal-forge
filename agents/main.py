"""
SignalForge FastAPI server.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agents.config import UserStrategy
from agents.models import StrategyMode, RiskLevel
from agents.orchestrator import Orchestrator
from agents.circle_stack import get_stack_status

orchestrator: Orchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    orchestrator = Orchestrator()
    yield


app = FastAPI(
    title="SignalForge",
    description="Autonomous prediction market agent powered by DGrid AI. Reasoning traces anchored on Arc. Subscriptions via Circle Nanopayments.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "ai_provider": "dgrid", "settlement": "arc"}


@app.get("/api/config")
async def get_config():
    if not orchestrator:
        return {}
    s = orchestrator.strategy
    return {
        "mode": s.mode.value,
        "risk": s.risk.value,
        "max_position_usd": s.max_position_usd,
        "min_ev_pct": s.min_ev_pct,
        "min_confidence": s.min_confidence,
        "kelly_fraction": s.kelly_fraction,
        "auto_cycle_minutes": s.auto_cycle_minutes,
        "paper_trade": s.paper_trade,
    }


@app.put("/api/config")
async def update_config(cfg: dict):
    if not orchestrator:
        return {"error": "not ready"}
    s = orchestrator.strategy
    if "mode" in cfg:
        s.mode = StrategyMode(cfg["mode"])
    if "risk" in cfg:
        s.risk = RiskLevel(cfg["risk"])
    if "max_position_usd" in cfg:
        s.max_position_usd = float(cfg["max_position_usd"])
    if "min_ev_pct" in cfg:
        s.min_ev_pct = float(cfg["min_ev_pct"])
    if "min_confidence" in cfg:
        s.min_confidence = float(cfg["min_confidence"])
    if "kelly_fraction" in cfg:
        s.kelly_fraction = float(cfg["kelly_fraction"])
    if "auto_cycle_minutes" in cfg:
        s.auto_cycle_minutes = int(cfg["auto_cycle_minutes"])
    if "paper_trade" in cfg:
        s.paper_trade = bool(cfg["paper_trade"])
    orchestrator.update_strategy(s)
    return {
        "mode": s.mode.value,
        "risk": s.risk.value,
        "max_position_usd": s.max_position_usd,
        "min_ev_pct": s.min_ev_pct,
        "min_confidence": s.min_confidence,
        "kelly_fraction": s.kelly_fraction,
        "auto_cycle_minutes": s.auto_cycle_minutes,
        "paper_trade": s.paper_trade,
    }


@app.post("/api/agent/start")
async def start_agent():
    if not orchestrator:
        return {"error": "not ready"}
    interval = orchestrator.strategy.auto_cycle_minutes or 15
    await orchestrator.start_auto_cycle(interval)
    return {"status": "started", "interval_minutes": interval}


@app.post("/api/agent/stop")
async def stop_agent():
    if not orchestrator:
        return {"error": "not ready"}
    orchestrator.stop_auto_cycle()
    return {"status": "stopped"}


@app.get("/api/agent/status")
async def agent_status():
    if not orchestrator:
        return {"error": "not ready"}
    return orchestrator.get_status()


@app.post("/api/cycle")
async def run_cycle():
    if not orchestrator:
        return {"error": "not ready"}
    signals = await orchestrator.run_cycle()
    return {
        "cycle": orchestrator.state.total_cycles,
        "signals_found": len(signals),
        "top_signal": signals[0].model_dump(mode="json") if signals else None,
    }


@app.get("/api/stats")
async def stats():
    if not orchestrator:
        return {}
    return orchestrator.get_status()


@app.get("/api/trades")
async def trades(limit: int = 50):
    if not orchestrator:
        return []
    return [
        t.model_dump(mode="json")
        for t in orchestrator.executor.trades[-limit:]
    ]


@app.get("/api/signals")
async def signals():
    if not orchestrator:
        return []
    return [s.model_dump(mode="json") for s in orchestrator.signals]


@app.get("/api/portfolio")
async def portfolio():
    if not orchestrator:
        return {}
    return orchestrator.get_portfolio()


@app.get("/api/circle-stack")
async def circle_stack():
    return get_stack_status()


@app.post("/api/seed")
async def seed_demo():
    """Generate demo signals for UI testing."""
    if not orchestrator:
        return []
    from agents.models import PredictionMarket, MarketOutcome, MarketStatus, ReasoningTrace, TradeSignal, TradeAction
    from datetime import datetime

    demo_markets = [
        PredictionMarket(
            id="demo-1",
            question="Will the Fed cut rates in June 2026?",
            category="Economics",
            tags=["fed", "rates", "macro"],
            outcomes=[MarketOutcome(name="Yes", price=0.35), MarketOutcome(name="No", price=0.65)],
            status=MarketStatus.ACTIVE,
            volume_24h=1250000,
            liquidity=450000,
            url="https://polymarket.com",
        ),
        PredictionMarket(
            id="demo-2",
            question="Will Bitcoin exceed $150K by end of 2026?",
            category="Crypto",
            tags=["bitcoin", "crypto", "price"],
            outcomes=[MarketOutcome(name="Yes", price=0.42), MarketOutcome(name="No", price=0.58)],
            status=MarketStatus.ACTIVE,
            volume_24h=3400000,
            liquidity=890000,
            url="https://polymarket.com",
        ),
        PredictionMarket(
            id="demo-3",
            question="Will AI regulation pass Congress in Q3 2026?",
            category="Politics",
            tags=["ai", "regulation", "congress"],
            outcomes=[MarketOutcome(name="Yes", price=0.28), MarketOutcome(name="No", price=0.72)],
            status=MarketStatus.ACTIVE,
            volume_24h=780000,
            liquidity=220000,
            url="https://polymarket.com",
        ),
    ]

    demo_signals = [
        TradeSignal(
            market=demo_markets[0],
            action=TradeAction.BUY_YES,
            target_outcome="Yes",
            position_size_usd=25.0,
            estimated_probability=0.52,
            market_implied_probability=0.35,
            edge_pct=17.0,
            confidence=68,
            reasoning=ReasoningTrace(
                market_id="demo-1",
                market_question=demo_markets[0].question,
                analysis="Labor market cooling faster than expected. Core PCE trending toward 2%. Fed has signaled data-dependence. Market underpricing cut probability by 17pp.",
                signal_type="BUY_YES",
                estimated_probability=0.52,
                market_implied_probability=0.35,
                edge_pct=17.0,
                confidence=68,
                key_factors=["Labor market cooling", "Core PCE trending down", "Fed data-dependent stance"],
                risks=["Inflation could re-accelerate", "Fed may hold for political reasons"],
            ),
            kelly_fraction=0.25,
        ),
        TradeSignal(
            market=demo_markets[1],
            action=TradeAction.BUY_YES,
            target_outcome="Yes",
            position_size_usd=15.0,
            estimated_probability=0.55,
            market_implied_probability=0.42,
            edge_pct=13.0,
            confidence=58,
            reasoning=ReasoningTrace(
                market_id="demo-2",
                market_question=demo_markets[1].question,
                analysis="Institutional adoption accelerating. ETF inflows at record levels. Halving cycle historically produces 12-18 month bull runs. Current trajectory supports $150K target.",
                signal_type="BUY_YES",
                estimated_probability=0.55,
                market_implied_probability=0.42,
                edge_pct=13.0,
                confidence=58,
                key_factors=["Record ETF inflows", "Post-halving cycle pattern", "Institutional adoption"],
                risks=["Macro recession could pressure all risk assets", "Regulatory crackdown"],
            ),
            kelly_fraction=0.25,
        ),
        TradeSignal(
            market=demo_markets[2],
            action=TradeAction.BUY_NO,
            target_outcome="No",
            position_size_usd=20.0,
            estimated_probability=0.22,
            market_implied_probability=0.28,
            edge_pct=6.0,
            confidence=52,
            reasoning=ReasoningTrace(
                market_id="demo-3",
                market_question=demo_markets[2].question,
                analysis="Congressional gridlock on tech regulation. AI bill lacks bipartisan support. Lobbying intensity from Big Tech at record levels. Timeline too aggressive for Q3 passage.",
                signal_type="BUY_NO",
                estimated_probability=0.22,
                market_implied_probability=0.28,
                edge_pct=6.0,
                confidence=52,
                key_factors=["Congressional gridlock", "Big Tech lobbying", "Aggressive timeline"],
                risks=["Bipartisan breakthrough possible", "Executive action could force hand"],
            ),
            kelly_fraction=0.25,
        ),
    ]

    orchestrator._signals = demo_signals
    orchestrator.state.total_signals = len(demo_signals)
    orchestrator.state.total_cycles = 1

    return [s.model_dump(mode="json") for s in demo_signals]


# --- Subscription Endpoints ---

@app.post("/api/subscribe")
async def subscribe(data: dict):
    """Subscribe to agent signals. Pay per signal via Circle Nanopayments."""
    if not orchestrator:
        return {"error": "not ready"}
    user_address = data.get("user_address", "")
    price = float(data.get("price_per_signal", 0.01))
    if not user_address:
        return {"error": "user_address required"}
    return orchestrator.subscribe_user(user_address, price)


@app.get("/api/subscriptions")
async def get_subscriptions():
    """Get all active subscriptions."""
    if not orchestrator:
        return []
    return orchestrator.subscriptions.get_subscriptions()


@app.get("/api/subscriptions/stats")
async def subscription_stats():
    """Get subscription statistics."""
    if not orchestrator:
        return {}
    return orchestrator.subscriptions.get_stats()


@app.get("/api/logs")
async def agent_logs(limit: int = 50):
    """Get recent agent activity logs."""
    if not orchestrator:
        return []
    return orchestrator.get_logs(limit)
