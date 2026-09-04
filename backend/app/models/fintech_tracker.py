"""
FinTech & Sovereign Debt Competitive Intelligence Tracker
==========================================================

Focused competitive intelligence for Quantive's direct market:
- DeFi protocols & infrastructure
- Trading platforms & exchanges
- Market data providers & analytics
- Sovereign debt management tools
- Government treasury platforms
- Bond issuance & refinancing tools

Each item includes threat assessment, feature overlap, and market positioning
relative to Quantive's capabilities.
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


class ThreatLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CompetitorCategory(str, enum.Enum):
    DEFI = "defi"
    TRADING_PLATFORM = "trading_platform"
    MARKET_DATA = "market_data"
    SOVEREIGN_DEBT = "sovereign_debt"
    TREASURY_PLATFORM = "treasury_platform"
    BOND_ISSUANCE = "bond_issuance"
    RISK_ANALYTICS = "risk_analytics"
    COMPLIANCE_TECH = "compliance_tech"
    FINANCIAL_MODELING = "financial_modeling"
    GOVTECH = "govtech"


class LaunchStage(str, enum.Enum):
    CONCEPT = "concept"
    PROTOTYPE = "prototype"
    SEED_ROUND = "seed_round"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    GROWTH = "growth"
    PUBLIC = "public"
    ACQUIRED = "acquired"
    SHELVED = "shelved"


class FintechLaunch(Base):
    __tablename__ = "fintech_launches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)

    # Company info
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_url: Mapped[str] = mapped_column(String(500), nullable=True)
    hq_location: Mapped[str] = mapped_column(String(100), nullable=True)
    founded_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    employee_count: Mapped[str] = mapped_column(String(50), nullable=True)
    total_funding: Mapped[str] = mapped_column(String(50), nullable=True)
    valuation: Mapped[str] = mapped_column(String(50), nullable=True)

    # Product details
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subcategory: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    target_users: Mapped[str] = mapped_column(String(255), nullable=True)
    pricing_model: Mapped[str] = mapped_column(String(100), nullable=True)

    # Launch status
    stage: Mapped[str] = mapped_column(String(30), nullable=False, default="concept")
    announced_date: Mapped[str] = mapped_column(String(30), nullable=True)
    launch_date: Mapped[str] = mapped_column(String(30), nullable=True)
    status_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Competitive intelligence
    threat_level: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    threat_score: Mapped[float] = mapped_column(Float, nullable=True)  # 0-100
    feature_overlap_pct: Mapped[float] = mapped_column(Float, nullable=True)  # 0-100
    quantive_advantage: Mapped[str] = mapped_column(Text, nullable=True)
    quantive_weakness: Mapped[str] = mapped_column(Text, nullable=True)
    competitor_advantage: Mapped[str] = mapped_column(Text, nullable=True)
    comparison_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Market data
    market_size_billion: Mapped[float] = mapped_column(Float, nullable=True)
    market_growth_pct: Mapped[float] = mapped_column(Float, nullable=True)
    competitors_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    geographic_focus: Mapped[str] = mapped_column(String(255), nullable=True)

    # Technology
    tech_stack: Mapped[str] = mapped_column(String(255), nullable=True)
    api_available: Mapped[bool] = mapped_column(default=False)
    open_source: Mapped[bool] = mapped_column(default=False)
    blockchain: Mapped[str] = mapped_column(String(100), nullable=True)

    # Metadata
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_urls: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), default="medium")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
