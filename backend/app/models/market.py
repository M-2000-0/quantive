"""Persisted market data — scheduled snapshots with staleness tracking.

Fetchers in app.market_data degrade to in-memory fallbacks; this table keeps
the history so freshness, audit, and agents can observe data over time.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy import JSON
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

JSONType = JSON().with_variant(SQLiteJSON(), "sqlite")

#: Sources captured by the market_refresh automation.
SOURCES = ("treasury_yields", "fx_rates")

#: Seconds after which a source counts as stale (daily cadence + slack).
STALE_AFTER_SECONDS = 25 * 3600


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MarketSnapshot(Base):
    """One persisted fetch of a market data source."""

    __tablename__ = "market_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # ok | fallback | error
    status: Mapped[str] = mapped_column(String(20), default="ok", index=True)
    payload: Mapped[dict] = mapped_column(JSONType, default=dict)
    record_count: Mapped[int] = mapped_column(default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
