"""Signal Outcome Tracking model.

Persistent record of every signal the platform publishes (discovery scores,
trading signals, price alerts, bubble flags) so the system can later evaluate
whether the claim came true and publish an honest hit/miss track record.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, JSON, Index,
)

from app.database import Base


class SignalOutcome(Base):
    __tablename__ = "signal_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # What the signal was
    signal_type = Column(String(40), nullable=False, index=True)
    # discovery_stock | discovery_crypto | strong_move | price_alert | bubble_flag
    symbol = Column(String(30), nullable=False, index=True)
    asset_class = Column(String(20), default="stock")
    direction = Column(String(10), nullable=False)  # bullish | bearish
    claim = Column(String(500), default="")  # plain-language statement of the claim
    strength = Column(Integer, default=0)  # 0-100 confidence/score at record time

    # When and where it was recorded
    recorded_price = Column(Float)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    recorded_date = Column(String(10), index=True)  # YYYY-MM-DD, for dedupe

    # Evaluation window
    horizon_days = Column(Integer, default=5)

    # Outcome
    outcome_status = Column(String(12), default="pending", index=True)
    # pending | win | loss | flat | expired
    outcome_threshold_pct = Column(Float, default=2.0)  # move needed to count as win/loss
    evaluated_price = Column(Float)
    evaluated_at = Column(DateTime)
    price_change_pct = Column(Float)  # actual move over the window

    outcome_metadata = Column(JSON, default=dict)

    __table_args__ = (
        Index("idx_outcome_symbol_type", "symbol", "signal_type"),
        Index("idx_outcome_status_recorded", "outcome_status", "recorded_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "signal_type": self.signal_type,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "direction": self.direction,
            "claim": self.claim,
            "strength": self.strength,
            "recorded_price": self.recorded_price,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "horizon_days": self.horizon_days,
            "outcome_status": self.outcome_status,
            "evaluated_price": self.evaluated_price,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "price_change_pct": self.price_change_pct,
            "metadata": self.outcome_metadata or {},
        }
