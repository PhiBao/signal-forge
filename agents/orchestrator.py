"""
Orchestrator: coordinates the full analysis -> signal -> execution cycle.
Integrates DGrid AI, Arc anchoring, Circle Gateway, and subscription management.
"""

import asyncio
import logging
from datetime import datetime
from agents.models import (
    PredictionMarket, TradeSignal, ReasoningTrace,
    TradeAction, AgentState,
)
from agents.config import settings, UserStrategy
from agents.scout import ScoutAgent
from agents.analyst import DGridAnalyst
from agents.signals import should_trade
from agents.executor import ExecutorAgent
from agents.arc_wallet import ArcWallet
from agents.circle_wallet import CircleWalletManager
from agents.circle_gateway import CircleGatewayManager
from agents.clob_client import PolymarketCLOBClient
from agents.subscriptions import SubscriptionManager

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, strategy: UserStrategy | None = None):
        self.strategy = strategy or UserStrategy()
        self.scout = ScoutAgent()
        self.analyst = DGridAnalyst()

        # Arc blockchain
        self.arc = ArcWallet()
        self.arc.connect()

        # Circle Wallet SDK
        self.circle = CircleWalletManager()

        # Circle Gateway (cross-chain USDC + Nanopayments)
        self.gateway = CircleGatewayManager()

        # Polymarket CLOB trading
        self.clob = PolymarketCLOBClient(
            api_key="",  # Set from env if available
            api_secret="",
            passphrase="",
        )

        # Subscription management
        self.subscriptions = SubscriptionManager()

        # Executor
        self.executor = ExecutorAgent(
            arc_wallet=self.arc,
            poly_client=self.scout.poly,
            clob_client=self.clob,
            gateway=self.gateway,
            subscriptions=self.subscriptions,
        )

        self.state = AgentState()
        self._signals: list[TradeSignal] = []
        self._running = False
        self._task: asyncio.Task | None = None
        self._logs: list[str] = []

    def update_strategy(self, strategy: UserStrategy):
        self.strategy = strategy

    async def run_cycle(self) -> list[TradeSignal]:
        """Run one full analysis cycle: scan -> analyze -> signal -> execute."""
        cycle_num = self.state.total_cycles + 1
        logger.info(f"Starting cycle #{cycle_num}")
        self.add_log(f"Starting cycle #{cycle_num}")
        self.state.total_cycles += 1
        self.state.last_cycle_at = datetime.utcnow()

        # Step 1: Scan markets + fetch news
        self.add_log("Fetching 50 markets from Polymarket Gamma API...")
        markets, news = await self.scout.scan(limit=50)
        logger.info(f"Scanned {len(markets)} markets")
        self.add_log(f"Scanned {len(markets)} markets, fetching news context...")

        # Step 2: AI analysis (batch, concurrent)
        self.add_log("Sending markets to DGrid AI for analysis...")
        analyzed = await self.analyst.batch_analyze(markets, news_context=news, max_concurrent=5)
        logger.info(f"Analyzed {len(analyzed)} markets with DGrid AI")
        self.add_log(f"DGrid AI analyzed {len(analyzed)} markets")

        # Step 3: Generate trade signals
        signals = []
        for market, analysis in analyzed:
            if not analysis or analysis.get("recommendation") == "HOLD":
                continue

            ai_prob = analysis.get("estimated_probability_yes", 0.5)
            market_price = market.outcomes[0].price if market.outcomes else 0.5
            confidence = analysis.get("confidence", 50)

            can_trade, action, size = should_trade(
                ai_probability=ai_prob,
                market_price=market_price,
                confidence=confidence,
                strategy=self.strategy,
            )

            if not can_trade:
                continue

            edge = abs(ai_prob - market_price) * 100

            reasoning = ReasoningTrace(
                market_id=market.id,
                market_question=market.question,
                analysis=analysis.get("analysis", ""),
                signal_type=action.value,
                estimated_probability=ai_prob,
                market_implied_probability=market_price,
                edge_pct=round(edge, 2),
                confidence=confidence,
                key_factors=analysis.get("key_factors", []),
                risks=analysis.get("risks", []),
            )

            signal = TradeSignal(
                market=market,
                action=action,
                target_outcome=market.outcomes[0].name if market.outcomes else "Yes",
                position_size_usd=size,
                estimated_probability=ai_prob,
                market_implied_probability=market_price,
                edge_pct=round(edge, 2),
                confidence=confidence,
                reasoning=reasoning,
                kelly_fraction=self.strategy.kelly_fraction,
            )
            signals.append(signal)

        # Sort by edge descending
        signals.sort(key=lambda s: s.edge_pct, reverse=True)
        self._signals = signals[:10]  # Keep top 10
        self.state.total_signals += len(signals)
        self.add_log(f"Found {len(signals)} signals — applying Kelly Criterion sizing...")

        # Step 4: Execute top signals + notify subscribers
        subscriber_ids = [s.id for s in self.subscriptions.subscriptions.values() if s.active]
        mode = "LIVE" if not self.strategy.paper_trade else "PAPER"
        for signal in self._signals[:3]:  # Execute top 3 per cycle
            try:
                self.add_log(f"Executing {signal.action.value} on '{signal.market.question[:50]}...'")
                await self.executor.execute_signal(
                    signal,
                    paper_trade=self.strategy.paper_trade,
                    subscriber_ids=subscriber_ids if subscriber_ids else None,
                )
                self.state.total_trades += 1
                self.add_log(f"Anchored reasoning trace on Arc ✓")
            except Exception as e:
                logger.error(f"Failed to execute signal: {e}")
                self.add_log(f"Execution failed: {str(e)}")

        self.state.last_error = None
        logger.info(f"Cycle complete: {len(signals)} signals, executed {min(3, len(signals))}")
        self.add_log(f"Cycle #{self.state.total_cycles} complete — {len(signals)} signals, {min(3, len(signals))} executed [{mode}]")
        return self._signals

    async def start_auto_cycle(self, interval_minutes: int = 15):
        """Start automatic cycling."""
        if self._running:
            return
        self._running = True
        self.strategy.auto_cycle_minutes = interval_minutes

        async def _loop():
            while self._running:
                try:
                    await self.run_cycle()
                except Exception as e:
                    self.state.last_error = str(e)
                    logger.error(f"Cycle error: {e}")
                await asyncio.sleep(interval_minutes * 60)

        self._task = asyncio.create_task(_loop())

    def stop_auto_cycle(self):
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    def subscribe_user(self, user_address: str, price_per_signal: float = 0.01) -> dict:
        """Subscribe a user to agent signals."""
        sub = self.subscriptions.subscribe(user_address, price_per_signal)
        return {
            "subscription_id": sub.id,
            "user_address": sub.user_address,
            "price_per_signal": sub.price_per_signal_usd,
            "message": "Subscribed to SignalForge signals. Pay per signal via Circle Nanopayments.",
        }

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def signals(self) -> list[TradeSignal]:
        return self._signals

    def get_status(self) -> dict:
        circle_info = self.circle.get_wallet_info()
        gateway_info = self.gateway.get_info()
        sub_stats = self.subscriptions.get_stats()

        return {
            "is_running": self.is_running,
            "total_cycles": self.state.total_cycles,
            "total_signals": self.state.total_signals,
            "total_trades": self.state.total_trades,
            "auto_cycle_minutes": self.strategy.auto_cycle_minutes,
            "paper_trade": self.strategy.paper_trade,
            "arc_connected": self.arc.connected,
            "arc_address": self.arc.account.address if self.arc.account else None,
            "usdc_balance": self.arc.get_usdc_balance(),
            "circle_wallet_id": circle_info.get("wallet_id"),
            "circle_wallet_address": circle_info.get("wallet_address"),
            "circle_connected": circle_info.get("connected", False),
            "circle_usdc_balance": self.circle.get_balance(),
            "gateway_connected": gateway_info.get("connected", False),
            "gateway_features": gateway_info.get("features", []),
            "subscribers": sub_stats["total_subscribers"],
            "subscription_revenue": sub_stats["total_revenue_usd"],
            "signals_delivered": sub_stats["total_signals_delivered"],
            "last_cycle_at": self.state.last_cycle_at.isoformat() if self.state.last_cycle_at else None,
            "last_error": self.state.last_error,
            **self.executor.get_stats(),
        }

    def get_portfolio(self) -> dict:
        return {
            "usdc_balance": self.arc.get_usdc_balance(),
            "total_exposure": sum(s.position_size_usd for s in self._signals),
            "signal_count": len(self._signals),
            "avg_position_size": (
                sum(s.position_size_usd for s in self._signals) / max(len(self._signals), 1)
            ),
            "risk_level": self.strategy.risk.value,
            "strategy_mode": self.strategy.mode.value,
        }

    def add_log(self, msg: str):
        """Add a log entry for the frontend to display."""
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        self._logs.append(f"[{timestamp}] {msg}")
        self._logs = self._logs[-100:]  # Keep last 100 logs

    def get_logs(self, limit: int = 50) -> list[str]:
        """Get recent agent logs."""
        return self._logs[-limit:]
