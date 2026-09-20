"""Regulatory Compliance & Explainable AI models.

Covers the 5 critical gaps identified by exchange/broker research:
  1. Regulatory Certification (conformity assessments, EU AI Act, SEC/ESMA)
  2. Algorithmic Impact Assessment (model validation, risk scoring)
  3. Stress Testing (market stability, flash crash prevention)
  4. Cross-Border Settlement (blockchain, multi-currency, multi-jurisdiction)
  5. Explainability Disclosures (standardized AI reports, regulatory transparency)
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- 1. Regulatory Certification ---

class CertificationStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    CERTIFIED = "certified"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


class CertificationType(str, enum.Enum):
    EU_AI_ACT = "eu_ai_act"
    SEC_ALGO = "sec_algo"
    ESMA_AI = "esma_ai"
    FCA_AI = "fca_ai"
    MAS_TECH = "mas_tech"
    ISO_27001 = "iso_27001"
    SOC2 = "soc2"
    CUSTOM = "custom"


class RegulatoryCertification(Base):
    __tablename__ = "regulatory_certifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    certification_name: Mapped[str] = mapped_column(String(255), nullable=False)
    certification_type: Mapped[CertificationType] = mapped_column(SAEnum(CertificationType), nullable=False)
    issuing_authority: Mapped[str] = mapped_column(String(255), nullable=False)
    certification_number: Mapped[str] = mapped_column(String(100), nullable=True)
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[CertificationStatus] = mapped_column(SAEnum(CertificationStatus), default=CertificationStatus.NOT_STARTED)
    compliance_score: Mapped[float] = mapped_column(Float, default=0.0)
    conformity_assessment_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    conformity_assessment_result: Mapped[str | None] = mapped_column(String(50), nullable=True)
    conformity_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    data_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    data_lineage_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    data_freshness_hours: Mapped[int] = mapped_column(Integer, default=24)
    traceability_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    decision_logging_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    audit_trail_completeness: Mapped[float] = mapped_column(Float, default=0.0)
    issued_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    renewal_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_audit_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_audit_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    documentation_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_files: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# --- 2. Algorithmic Impact Assessment ---

class ImpactSeverity(str, enum.Enum):
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    CONDITIONAL = "conditional"


class AlgorithmicImpactAssessment(Base):
    __tablename__ = "algorithmic_impact_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    model_card_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ai_model_cards.id"), nullable=True)
    assessment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    assessor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    assessor_organization: Mapped[str] = mapped_column(String(255), nullable=False)
    impact_severity: Mapped[ImpactSeverity] = mapped_column(SAEnum(ImpactSeverity), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    systemic_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    market_impact_score: Mapped[float] = mapped_column(Float, default=0.0)
    validation_status: Mapped[ValidationStatus] = mapped_column(SAEnum(ValidationStatus), default=ValidationStatus.PENDING)
    independent_validator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    validation_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    validation_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    training_data_period: Mapped[str | None] = mapped_column(String(100), nullable=True)
    training_data_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_bias_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    fairness_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    kill_switch_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    position_limits: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    circuit_breakers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    human_oversight_required: Mapped[bool] = mapped_column(Boolean, default=True)
    findings_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    assessment_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    review_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_assessment_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# --- 3. Stress Testing ---

class StressTestType(str, enum.Enum):
    HISTORICAL = "historical"
    HYPOTHETICAL = "hypothetical"
    REVERSE = "reverse"
    MONTE_CARLO = "monte_carlo"
    SENSITIVITY = "sensitivity"
    SCENARIO = "scenario"


class StressTestResultStatus(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    MARGINAL = "marginal"
    IN_PROGRESS = "in_progress"


class StressTest(Base):
    __tablename__ = "stress_tests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    test_name: Mapped[str] = mapped_column(String(255), nullable=False)
    test_type: Mapped[StressTestType] = mapped_column(SAEnum(StressTestType), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    shock_magnitude_pct: Mapped[float] = mapped_column(Float, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, default=1)
    affected_markets: Mapped[list | None] = mapped_column(JSON, nullable=True)
    interest_rate_shock_bps: Mapped[float] = mapped_column(Float, default=0.0)
    fx_shock_pct: Mapped[float] = mapped_column(Float, default=0.0)
    equity_shock_pct: Mapped[float] = mapped_column(Float, default=0.0)
    credit_spread_shock_bps: Mapped[float] = mapped_column(Float, default=0.0)
    commodity_shock_pct: Mapped[float] = mapped_column(Float, default=0.0)
    result: Mapped[StressTestResultStatus] = mapped_column(SAEnum(StressTestResultStatus), default=StressTestResultStatus.IN_PROGRESS)
    portfolio_impact_pct: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown_pct: Mapped[float] = mapped_column(Float, default=0.0)
    recovery_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    liquidity_impact: Mapped[str | None] = mapped_column(String(50), nullable=True)
    flash_crash_threshold_bps: Mapped[float] = mapped_column(Float, default=500.0)
    circuit_breaker_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_halt_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    executed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    execution_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    report_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# --- 4. Cross-Border Settlement ---

class SettlementStatus(str, enum.Enum):
    PENDING = "pending"
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    SETTLED = "settled"
    FAILED = "failed"
    DISPUTED = "disputed"
    RECONCILED = "reconciled"


class SettlementNetwork(str, enum.Enum):
    SWIFT = "swift"
    CHIPS = "chips"
    TARGET2 = "target2"
    CIPS = "cips"
    FEDWIRE = "fedwire"
    BLOCKCHAIN_PUBLIC = "blockchain_public"
    BLOCKCHAIN_PRIVATE = "blockchain_private"
    HYBRID = "hybrid"


class CrossBorderSettlement(Base):
    __tablename__ = "cross_border_settlements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    exchange_connection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("exchange_connections.id"), nullable=True)
    settlement_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    settlement_network: Mapped[SettlementNetwork] = mapped_column(SAEnum(SettlementNetwork), nullable=False)
    origin_jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False)
    destination_jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False)
    origin_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    destination_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    amount_origin: Mapped[float] = mapped_column(Float, nullable=False)
    amount_destination: Mapped[float] = mapped_column(Float, nullable=False)
    exchange_rate: Mapped[float] = mapped_column(Float, nullable=False)
    fx_spread_bps: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[SettlementStatus] = mapped_column(SAEnum(SettlementStatus), default=SettlementStatus.PENDING)
    settlement_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    value_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    blockchain_tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    blockchain_network: Mapped[str | None] = mapped_column(String(100), nullable=True)
    smart_contract_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    compliance_checks_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    aml_screening_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    sanctions_screening_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    counterparty_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    counterparty_bic: Mapped[str | None] = mapped_column(String(20), nullable=True)
    settlement_fees: Mapped[float] = mapped_column(Float, default=0.0)
    netting_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    dvp_rvp: Mapped[str | None] = mapped_column(String(10), nullable=True)
    confirmation_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reconciliation_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dispute_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# --- 5. Explainability Disclosures ---

class DisclosureType(str, enum.Enum):
    MODEL_CARD = "model_card"
    TECHNICAL_REPORT = "technical_report"
    CONSUMER_SUMMARY = "consumer_summary"
    REGULATORY_FILING = "regulatory_filing"
    IMPACT_ASSESSMENT = "impact_assessment"
    AUDIT_REPORT = "audit_report"
    TRANSPARENCY_REPORT = "transparency_report"


class DisclosureStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class ExplainabilityDisclosure(Base):
    __tablename__ = "explainability_disclosures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    model_card_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ai_model_cards.id"), nullable=True)
    disclosure_type: Mapped[DisclosureType] = mapped_column(SAEnum(DisclosureType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    target_audience: Mapped[str] = mapped_column(String(100), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[DisclosureStatus] = mapped_column(SAEnum(DisclosureStatus), default=DisclosureStatus.DRAFT)
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    methodology_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    feature_contributions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    decision_explanation_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_intervals: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    limitations_and_biases: Mapped[list | None] = mapped_column(JSON, nullable=True)
    data_sources_used: Mapped[list | None] = mapped_column(JSON, nullable=True)
    regulatory_references: Mapped[list | None] = mapped_column(JSON, nullable=True)
    publication_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_review_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
