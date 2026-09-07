"""Sovereign Debt Transparency Index models.

Ranks countries on the transparency and sophistication of their debt management
practices. Positions Quantive as a thought leader and generates inbound interest.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IndexCategory(str, enum.Enum):
    """Categories for the transparency index scoring."""
    DISCLOSURE = "disclosure"           # Public debt reporting quality
    DATA_ACCESS = "data_access"         # Availability of debt data
    INSTITUTIONAL = "institutional"     # DMO independence and capacity
    REPORTING_FREQ = "reporting_freq"   # Frequency of debt reports
    AUDIT_TRAIL = "audit_trail"         # Audit and oversight mechanisms
    DIGITAL_INFRA = "digital_infra"     # Digital debt management tools
    COMPLIANCE = "compliance"           # International standards adherence
    STAKEHOLDER = "stakeholder"         # Parliamentary/public engagement


class CountryTier(str, enum.Enum):
    """Tiers for country classification based on index score."""
    LEADER = "leader"           # 80-100: Best practices
    ADVANCED = "advanced"       # 60-79: Strong framework
    DEVELOPING = "developing"   # 40-59: Improving
    EMERGING = "emerging"       # 20-39: Basic
    LAGGARD = "laggard"         # 0-19: Significant gaps


class SovereignDebtIndex(Base):
    """Country-level transparency index scores."""
    __tablename__ = "sovereign_debt_index"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False, unique=True)
    country_name: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    income_group: Mapped[str] = mapped_column(String(50), nullable=False)

    # Overall score
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[CountryTier] = mapped_column(SAEnum(CountryTier), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=True)

    # Category scores (each 0-100)
    disclosure_score: Mapped[float] = mapped_column(Float, default=0.0)
    data_access_score: Mapped[float] = mapped_column(Float, default=0.0)
    institutional_score: Mapped[float] = mapped_column(Float, default=0.0)
    reporting_freq_score: Mapped[float] = mapped_column(Float, default=0.0)
    audit_trail_score: Mapped[float] = mapped_column(Float, default=0.0)
    digital_infra_score: Mapped[float] = mapped_column(Float, default=0.0)
    compliance_score: Mapped[float] = mapped_column(Float, default=0.0)
    stakeholder_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Metadata
    data_sources: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    methodology_version: Mapped[str] = mapped_column(String(20), default="1.0")
    assessment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    next_assessment: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Detailed findings
    strengths: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    weaknesses: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class IndexMethodology(Base):
    """Methodology documentation for the transparency index."""
    __tablename__ = "index_methodology"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category_weights: Mapped[dict] = mapped_column(JSON, nullable=False)
    scoring_criteria: Mapped[dict] = mapped_column(JSON, nullable=False)
    data_sources: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_current: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IndexHistory(Base):
    """Historical index scores for trend analysis."""
    __tablename__ = "index_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[CountryTier] = mapped_column(SAEnum(CountryTier), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=True)
    assessment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    category_scores: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
