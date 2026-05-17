"""
Subscription and copy-trading layer.
Users subscribe to agent signals, pay per-signal via Nanopayments.
Agent earns builder fees from Polymarket when users trade its recommendations.
"""

import uuid
import logging
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Subscription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_address: str
    subscribed_at: datetime = Field(default_factory=datetime.utcnow)
    signals_received: int = 0
    total_paid_usd: float = 0
    price_per_signal_usd: float = 0.01
    active: bool = True
    payment_txs: list[dict] = []  # [{tx_hash, network, amount, timestamp}]


class CopyTradeRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subscription_id: str
    signal_id: str
    user_action: str  # BUY_YES, BUY_NO, etc.
    user_size_usd: float
    agent_signal_edge: float
    copied_at: datetime = Field(default_factory=datetime.utcnow)
    result: str = "pending"  # pending, win, loss
    pnl_usd: float = 0


class SubscriptionManager:
    """
    Manages user subscriptions to agent signals.
    - Users subscribe with their wallet address
    - Pay per-signal via Circle Nanopayments
    - Can copy-trade agent's recommendations
    - Agent earns builder fees from Polymarket
    """

    def __init__(self):
        self.subscriptions: dict[str, Subscription] = {}
        self.copy_trades: list[CopyTradeRecord] = []
        self.total_revenue_usd: float = 0
        self.total_signals_delivered: int = 0

    def subscribe(self, user_address: str, price_per_signal: float = 0.01) -> Subscription:
        """Create a new subscription for a user."""
        sub = Subscription(
            user_address=user_address,
            price_per_signal_usd=price_per_signal,
        )
        self.subscriptions[sub.id] = sub
        logger.info(f"New subscription: {user_address} at ${price_per_signal}/signal")
        return sub

    def get_subscriptions(self) -> list[dict]:
        """Get all active subscriptions."""
        return [
            {
                "id": s.id,
                "user_address": s.user_address,
                "signals_received": s.signals_received,
                "total_paid": s.total_paid_usd,
                "price_per_signal": s.price_per_signal_usd,
                "active": s.active,
                "payment_txs": s.payment_txs,
            }
            for s in self.subscriptions.values()
            if s.active
        ]

    def record_signal_delivery(self, subscription_id: str, nanopayment_tx: dict | None = None) -> float:
        """Record that a signal was delivered to a subscriber."""
        sub = self.subscriptions.get(subscription_id)
        if not sub or not sub.active:
            return 0

        sub.signals_received += 1
        sub.total_paid_usd += sub.price_per_signal_usd
        self.total_revenue_usd += sub.price_per_signal_usd
        self.total_signals_delivered += 1

        if nanopayment_tx and nanopayment_tx.get("success"):
            sub.payment_txs.append({
                "tx_hash": nanopayment_tx.get("transaction", ""),
                "network": nanopayment_tx.get("network", ""),
                "amount": nanopayment_tx.get("amount", "0.01"),
                "timestamp": datetime.utcnow().isoformat(),
            })

        logger.info(
            f"Signal delivered to {sub.user_address}: "
            f"#{sub.signals_received}, revenue=${sub.total_paid_usd:.4f}"
        )
        return sub.price_per_signal_usd

    def record_copy_trade(
        self,
        subscription_id: str,
        signal_id: str,
        user_action: str,
        user_size_usd: float,
        agent_edge: float,
    ) -> CopyTradeRecord:
        """Record when a user copies a trade."""
        record = CopyTradeRecord(
            subscription_id=subscription_id,
            signal_id=signal_id,
            user_action=user_action,
            user_size_usd=user_size_usd,
            agent_signal_edge=agent_edge,
        )
        self.copy_trades.append(record)
        return record

    def resolve_copy_trade(self, record_id: str, result: str, pnl: float):
        """Resolve a copy trade with its outcome."""
        for record in self.copy_trades:
            if record.id == record_id:
                record.result = result
                record.pnl_usd = pnl
                break

    def get_stats(self) -> dict:
        active_subs = [s for s in self.subscriptions.values() if s.active]
        winning_trades = [t for t in self.copy_trades if t.result == "win"]
        losing_trades = [t for t in self.copy_trades if t.result == "loss"]

        return {
            "total_subscribers": len(active_subs),
            "total_signals_delivered": self.total_signals_delivered,
            "total_revenue_usd": round(self.total_revenue_usd, 4),
            "total_copy_trades": len(self.copy_trades),
            "win_rate": (
                len(winning_trades) / max(len(self.copy_trades), 1) * 100
            ),
            "avg_pnl_per_trade": (
                sum(t.pnl_usd for t in self.copy_trades) / max(len(self.copy_trades), 1)
            ),
        }
