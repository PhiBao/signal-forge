"""
Signal engine: Kelly Criterion + edge detection + position sizing.
Pure math layer on top of AI analysis.
"""

from agents.models import TradeAction, RiskLevel, StrategyMode
from agents.config import UserStrategy


def kelly_criterion(probability: float, odds: float) -> float:
    """
    Kelly Criterion: f* = (p*b - q) / b
    p = estimated probability of winning
    b = decimal odds - 1 (payout ratio)
    q = 1 - p
    """
    if odds <= 1:
        return 0
    b = odds - 1
    q = 1 - probability
    f = (probability * b - q) / b
    return max(0, f)


def implied_odds(price: float) -> float:
    """Convert prediction market price to decimal odds."""
    if price <= 0 or price >= 1:
        return 0
    return 1 / price


def compute_edge(ai_probability: float, market_price: float) -> float:
    """Edge = AI estimated probability - market implied probability."""
    return (ai_probability - market_price) * 100


def risk_multiplier(risk: RiskLevel) -> float:
    return {
        RiskLevel.CONSERVATIVE: 0.5,
        RiskLevel.MODERATE: 1.0,
        RiskLevel.AGGRESSIVE: 2.0,
    }.get(risk, 1.0)


def confidence_threshold(risk: RiskLevel) -> float:
    return {
        RiskLevel.CONSERVATIVE: 60,
        RiskLevel.MODERATE: 45,
        RiskLevel.AGGRESSIVE: 30,
    }.get(risk, 45)


def should_trade(
    ai_probability: float,
    market_price: float,
    confidence: float,
    strategy: UserStrategy,
) -> tuple[bool, TradeAction, float]:
    """
    Decide whether to trade and what action to take.
    Returns: (should_trade, action, position_size_usd)
    """
    edge = compute_edge(ai_probability, market_price)
    abs_edge = abs(edge)

    if abs_edge < strategy.min_ev_pct:
        return False, TradeAction.HOLD, 0

    if confidence < strategy.min_confidence:
        return False, TradeAction.HOLD, 0

    if confidence < confidence_threshold(strategy.risk):
        return False, TradeAction.HOLD, 0

    # Determine direction
    if edge > 0:
        action = TradeAction.BUY_YES
        price = market_price
    else:
        action = TradeAction.BUY_NO
        price = 1 - market_price
        ai_probability = 1 - ai_probability

    # Kelly sizing
    odds = implied_odds(price)
    kelly = kelly_criterion(ai_probability, odds)
    kelly_adjusted = kelly * strategy.kelly_fraction
    kelly_adjusted *= risk_multiplier(strategy.risk)

    # Cap at max position
    position_size = min(kelly_adjusted * 100, strategy.max_position_usd)
    position_size = max(position_size, 1)  # minimum $1

    return True, action, round(position_size, 2)
