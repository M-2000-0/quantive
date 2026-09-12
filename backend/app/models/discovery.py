"""
Discovery / Personalized Opportunities Models
==============================================

Powers the personalized investment discovery algorithm:

- ``DiscoveryAsset``: a curated, investable universe spanning four asset
  classes (stocks, ETFs, cryptocurrencies, and alternative assets). Each
  asset carries the feature snapshot used by the scoring engine.
- ``DiscoveryPreference``: per-user personalization state (asset-class
  interests, sector/ESG flags, and the learned behavioral pillar weights).
- ``DiscoveryFeedback``: a user interaction with a recommended opportunity,
  used by the iterative feedback loop to refine future suggestions.

The asset universe is sourced either from validated market feed providers
or from an embedded reference snapshot. Fields ending in ``_snapshot`` are
historical reference values; live values (when available) are refreshed by
the market-data layer before scoring.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _gen_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AssetClass(str, enum.Enum):
    STOCK = "stock"
    ETF = "etf"
    CRYPTO = "crypto"
    ALTERNATIVE = "alternative"


class AssetRiskBand(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class FeedbackAction(str, enum.Enum):
    """User actions recorded against a surfaced opportunity."""

    SHOWN = "shown"
    LIKED = "liked"
    RESEARCHED = "researched"
    DISMISSED = "dismissed"
    NOT_RELEVANT = "not_relevant"
    TOO_RISKY = "too_risky"
    UNFAMILIAR = "unfamiliar"


class DiscoveryAsset(Base):
    """A single investable opportunity in the discovery universe."""

    __tablename__ = "discovery_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_uuid)
    symbol: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_class: Mapped[AssetClass] = mapped_column(SAEnum(AssetClass), nullable=False, index=True)
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    geography: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # Feature snapshot used by the scoring engine. ``None`` means the
    # metric is not available — engines must treat missing values as
    # neutral rather than fabricate them.
    annual_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    annual_volatility_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    momentum_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    fundamental_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1..1
    esg_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    liquidity_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    risk_band: Mapped[AssetRiskBand | None] = mapped_column(SAEnum(AssetRiskBand), nullable=True)

    # Tags used for relevance matching (sectors, themes, asset categories)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Provenance
    data_source: Mapped[str] = mapped_column(String(80), default="snapshot")  # snapshot | live
    data_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "asset_class": self.asset_class.value if isinstance(self.asset_class, AssetClass) else self.asset_class,
            "sector": self.sector,
            "geography": self.geography,
            "annual_return_pct": self.annual_return_pct,
            "annual_volatility_pct": self.annual_volatility_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "momentum_score": self.momentum_score,
            "fundamental_score": self.fundamental_score,
            "sentiment_score": self.sentiment_score,
            "esg_score": self.esg_score,
            "liquidity_score": self.liquidity_score,
            "risk_band": self.risk_band.value if isinstance(self.risk_band, AssetRiskBand) else self.risk_band,
            "tags": self.tags or [],
            "data_source": self.data_source,
        }


class DiscoveryPreference(Base):
    """Per-user state for the personalized discovery algorithm."""

    __tablename__ = "discovery_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)

    # Explicit interest flags per asset class (1.0 = very interested)
    interest_stock: Mapped[float] = mapped_column(Float, default=1.0)
    interest_etf: Mapped[float] = mapped_column(Float, default=1.0)
    interest_crypto: Mapped[float] = mapped_column(Float, default=0.5)
    interest_alternative: Mapped[float] = mapped_column(Float, default=0.5)

    sector_preferences: Mapped[list | None] = mapped_column(JSON, nullable=True)  # e.g. ["tech", "energy"]
    min_esg_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # hard filter if set
    exclusions: Mapped[list | None] = mapped_column(JSON, nullable=True)  # symbols/names to never show

    # Learned assessment of the user (derived from current holdings / risk quiz)
    max_acceptable_drawdown_pct: Mapped[float] = mapped_column(Float, default=0.20)
    volatility_tolerance: Mapped[str] = mapped_column(String(20), default="medium")  # low|medium|high

    # Pillar weights (learned over time via the feedback loop) — default to the
    # algorithm's baseline relevance/risk-fit weighting.
    weight_relevance: Mapped[float] = mapped_column(Float, default=0.35)
    weight_riskfit: Mapped[float] = mapped_column(Float, default=0.30)
    weight_trend: Mapped[float] = mapped_column(Float, default=0.20)
    weight_diversity: Mapped[float] = mapped_column(Float, default=0.15)

    # Engagement counters
    total_shown: Mapped[int] = mapped_column(Integer, default=0)
    total_liked: Mapped[int] = mapped_column(Integer, default=0)
    total_dismissed: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class DiscoveryFeedback(Base):
    """Every recorded interaction with a recommended opportunity."""

    __tablename__ = "discovery_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    preference_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    asset_symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    asset_class: Mapped[AssetClass] = mapped_column(SAEnum(AssetClass), nullable=False)

    action: Mapped[FeedbackAction] = mapped_column(SAEnum(FeedbackAction), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)  # optional free-text

    # Ranking context at time of recommendation
    surfaced_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_at_surface: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
