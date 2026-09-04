"""
Market Intelligence — Upcoming Product Launch Tracker
=====================================================

Tracks pending product launches across 50 industries, 20 subcategories each,
with 3-5 launches per subcategory (3,000-5,000 items total).

Provides competitive intelligence for Quantive users.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LaunchStatus(str, enum.Enum):
    RUMORED = "rumored"
    ANNOUNCED = "announced"
    IN_DEVELOPMENT = "in_development"
    BETA = "beta"
    PILOT = "pilot"
    AWAITING_FUNDING = "awaiting_funding"
    IN_PRODUCTION = "in_production"
    SOON = "soon"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class MarketLaunch(Base):
    __tablename__ = "market_launches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)

    # Taxonomy
    industry: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subcategory: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Item details
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    target_market: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    # Status
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="announced")
    estimated_launch: Mapped[str] = mapped_column(String(50), nullable=False, default="")

    # Market data
    market_size_billion: Mapped[float] = mapped_column(Float, nullable=True)
    competitive_advantage: Mapped[str] = mapped_column(Text, nullable=True)
    risk_factors: Mapped[str] = mapped_column(Text, nullable=True)

    # Metadata
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), default="medium")  # high/medium/low

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
