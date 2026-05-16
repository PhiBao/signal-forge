"""
Pydantic data models for SignalForge.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MarketStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    RESOLVED = "resolved"


class TradeAction(str, Enum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    SELL_YES = "SELL_YES"
    SELL_NO = "SELL_NO"
    HOLD = "HOLD"


class RiskLevel(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class StrategyMode(str, Enum):
    VALUE = "value"
    MOMENTUM = "momentum"
    CATALYST = "catalyst"
    BALANCED = "balanced"


class MarketOutcome(BaseModel):
    name: str
    price: float
    volume_24h: float = 0


class PredictionMarket(BaseModel):
    id: str
    question: str
    description: str = ""
    category: str = ""
    tags: list[str] = Field(default_factory=list)
    outcomes: list[MarketOutcome] = Field(default_factory=list)
    status: MarketStatus = MarketStatus.ACTIVE
    end_date: Optional[str] = None
    volume_24h: float = 0
    liquidity: float = 0
    url: str = ""


class ReasoningTrace(BaseModel):
    market_id: str
    market_question: str
    analysis: str
    signal_type: str
    estimated_probability: float
    market_implied_probability: float
    edge_pct: float
    confidence: float
    key_factors: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    arc_tx_hash: Optional[str] = None


class TradeSignal(BaseModel):
    market: PredictionMarket
    action: TradeAction
    target_outcome: str
    position_size_usd: float
    estimated_probability: float
    market_implied_probability: float
    edge_pct: float
    confidence: float
    reasoning: ReasoningTrace
    kelly_fraction: float
    version: str = "dgrid-v1"


class ExecutedTrade(BaseModel):
    signal: TradeSignal
    action: TradeAction
    size_usd: float
    filled_price: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tx_hash: Optional[str] = None
    arc_trace_hash: Optional[str] = None
    gateway_tx: str = ""
    mode: str = "simulated"
    pnl: float = 0
    status: str = "pending"


class Position(BaseModel):
    market_id: str
    market_question: str
    outcome: str
    size_usd: float
    avg_price: float
    current_price: float
    unrealized_pnl: float = 0
    opened_at: datetime = Field(default_factory=datetime.utcnow)


class AgentState(BaseModel):
    is_running: bool = False
    total_cycles: int = 0
    total_signals: int = 0
    total_trades: int = 0
    total_volume: float = 0
    realized_pnl: float = 0
    win_rate: float = 0
    last_cycle_at: Optional[datetime] = None
    last_error: Optional[str] = None
