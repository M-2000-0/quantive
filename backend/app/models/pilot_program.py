"""Government Pilot Program infrastructure.

Tracks pilot programs, generates case study templates, and manages
the "First Five" government pilots recommended in the 6.md document.

Each pilot is a free 12-month engagement in exchange for:
- Case study rights
- Data access for model training
- Commitment to paid conversion if outcomes meet thresholds
"""

import enum
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, Boolean
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PilotStatus(str, enum.Enum):
    """Pilot program status."""
    PROSPECTING = "prospecting"
    PROPOSAL_SENT = "proposal_sent"
    NEGOTIATION = "negotiation"
    ACTIVE = "active"
    EXTENDED = "extended"
    CONVERSION = "conversion"
    COMPLETED = "completed"
    LOST = "lost"


class PilotTier(str, enum.Enum):
    """Pilot program tiers based on portfolio size."""
    STARTER = "starter"           # < $1B
    PROFESSIONAL = "professional" # $1B - $10B
    ENTERPRISE = "enterprise"     # $10B - $100B
    SOVEREIGN = "sovereign"       # > $100B


class ConversionStatus(str, enum.Enum):
    """Conversion status after pilot."""
    PENDING = "pending"
    CONTRACT_SENT = "contract_sent"
    NEGOTIATING = "negotiating"
    CONVERTED = "converted"
    DECLINED = "declined"
    EXTENDED = "extended"


class GovernmentPilot(Base):
    """Government pilot program tracking."""
    __tablename__ = "government_pilots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)

    # Government details
    country_code: Mapped[str] = mapped_column(String(3), nullable=False)
    country_name: Mapped[str] = mapped_column(String(255), nullable=False)
    government_entity: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # DMO, Ministry, Central Bank
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_title: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Portfolio details
    total_debt_outstanding: Mapped[float] = mapped_column(Float, nullable=False)
    annual_issuance: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    debt_to_gdp: Mapped[float] = mapped_column(Float, default=0.0)
    portfolio_tier: Mapped[PilotTier] = mapped_column(SAEnum(PilotTier), nullable=False)

    # Pilot program
    status: Mapped[PilotStatus] = mapped_column(SAEnum(PilotStatus), nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extension_months: Mapped[int] = mapped_column(Integer, default=0)

    # Success metrics (measured during pilot)
    financing_cost_reduction_bps: Mapped[float] = mapped_column(Float, default=0.0)
    risk_score_improvement_pct: Mapped[float] = mapped_column(Float, default=0.0)
    report_generation_time_min: Mapped[float] = mapped_column(Float, default=0.0)
    user_adoption_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Conversion tracking
    conversion_status: Mapped[ConversionStatus] = mapped_column(
        SAEnum(ConversionStatus), nullable=False
    )
    conversion_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    conversion_value_usd: Mapped[float] = mapped_column(Float, default=0.0)
    contract_term_years: Mapped[int] = mapped_column(Integer, default=0)

    # Case study
    case_study_published: Mapped[bool] = mapped_column(Boolean, default=False)
    case_study_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    testimonial_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    data_for_training: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notes and metadata
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PilotMilestone(Base):
    """Track milestones within a pilot program."""
    __tablename__ = "pilot_milestones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    pilot_id: Mapped[str] = mapped_column(String(36), nullable=False)
    milestone_name: Mapped[str] = mapped_column(String(255), nullable=False)
    milestone_type: Mapped[str] = mapped_column(String(50), nullable=False)  # deployment, training, go-live, etc.
    target_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PilotMetric(Base):
    """Track metrics over time during a pilot."""
    __tablename__ = "pilot_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    pilot_id: Mapped[str] = mapped_column(String(36), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    metric_unit: Mapped[str] = mapped_column(String(50), nullable=False)
    recorded_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PilotCaseStudy(Base):
    """Case study template and content."""
    __tablename__ = "pilot_case_studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    pilot_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Template fields
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(500), nullable=True)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    challenge: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    testimonials: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Publishing
    status: Mapped[str] = mapped_column(String(20), default="draft")
    published_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
