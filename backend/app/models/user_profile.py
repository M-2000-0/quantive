"""
User Profile & Behavioral Tracking
===================================

Tracks user preferences, behavioral signals, and recommendation
interactions to power personalized investment recommendations.

Each user builds an embedding through:
- Explicit preferences (risk tolerance, horizon, currency focus)
- Implicit signals (clicks, dismissals, exports, time spent)
- Portfolio context (their actual holdings and constraints)
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


class RiskTolerance(str, enum.Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)

    # Explicit preferences
    risk_tolerance: Mapped[str] = mapped_column(String(20), default="moderate")
    investment_horizon_years: Mapped[int] = mapped_column(Integer, default=10)
    currency_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # ["MXN", "USD"]
    liquidity_needs: Mapped[str] = mapped_column(String(20), default="medium")  # low/medium/high
    compliance_constraints: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    focus_sectors: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # ["sovereign", "corporate"]
    exclusions: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)  # tickers / instruments the user never wants to see

    # Behavioral weights (learned over time)
    risk_insight_weight: Mapped[float] = mapped_column(Float, default=1.0)
    cost_insight_weight: Mapped[float] = mapped_column(Float, default=1.0)
    refinancing_weight: Mapped[float] = mapped_column(Float, default=1.0)
    currency_weight: Mapped[float] = mapped_column(Float, default=1.0)
    compliance_weight: Mapped[float] = mapped_column(Float, default=1.0)
    market_weight: Mapped[float] = mapped_column(Float, default=1.0)

    # Engagement metrics
    total_recommendations_shown: Mapped[int] = mapped_column(Integer, default=0)
    total_recommendations_clicked: Mapped[int] = mapped_column(Integer, default=0)
    total_recommendations_acted: Mapped[int] = mapped_column(Integer, default=0)
    total_recommendations_dismissed: Mapped[int] = mapped_column(Integer, default=0)
    avg_engagement_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Profile embedding (for collaborative filtering)
    profile_embedding: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecommendationInteraction(Base):
    """Track every user interaction with a recommendation."""
    __tablename__ = "recommendation_interactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # What was recommended
    recommendation_type: Mapped[str] = mapped_column(String(50), nullable=False)  # refinancing, risk, currency, compliance, cost, market
    recommendation_title: Mapped[str] = mapped_column(String(255), nullable=False)
    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)

    # User action
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # shown, clicked, dismissed, acted, exported
    time_spent_seconds: Mapped[float] = mapped_column(Float, default=0)

    # Context at time of recommendation
    market_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    portfolio_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
