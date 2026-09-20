"""Independent Model Validation and Vendor Risk Assessment models.

Covers the final 2 gaps from exchange partnership research:
  1. Independent model validation (backtesting, out-of-sample, champion/challenger)
  2. Third-party vendor risk management (due diligence, SLA, security, supply chain)
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


# --- 1. Independent Model Validation ---

class ValidationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    CONDITIONAL = "conditional"
    EXEMPTED = "exempted"


class ValidationType(str, enum.Enum):
    BACKTESTING = "backtesting"
    OUT_OF_SAMPLE = "out_of_sample"
    WALK_FORWARD = "walk_forward"
    MONTE_CARLO = "monte_carlo"
    STRESS_TEST = "stress_test"
    CHAMPION_CHALLENGER = "champion_challenger"
    AB_TEST = "ab_test"
    ROBUSTNESS = "robustness"


class SignOffRole(str, enum.Enum):
    CRO = "cro"
    CTO = "cto"
    CISO = "ciso"
    COMPLIANCE = "compliance"
    RISK_COMMITTEE = "risk_committee"
    BOARD = "board"
    EXTERNAL_AUDITOR = "external_auditor"


class IndependentValidation(Base):
    __tablename__ = "independent_validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    validation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    validation_type: Mapped[ValidationType] = mapped_column(SAEnum(ValidationType), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ValidationStatus] = mapped_column(SAEnum(ValidationStatus), default=ValidationStatus.PENDING)

    # Model being validated
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    validation_frequency: Mapped[str] = mapped_column(String(50), default="quarterly")

    # Backtesting parameters
    backtest_start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    backtest_end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    backtest_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    in_sample_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    out_of_sample_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Performance metrics
    in_sample_sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    out_of_sample_sharpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    in_sample_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    out_of_sample_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    calmar_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    sortino_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    information_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Degradation checks
    sharpe_degradation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    return_degradation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_acceptable_degradation_pct: Mapped[float] = mapped_column(Float, default=20.0)

    # Champion/Challenger
    is_champion: Mapped[bool] = mapped_column(Boolean, default=False)
    is_challenger: Mapped[bool] = mapped_column(Boolean, default=False)
    champion_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    challenger_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ab_test_sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ab_test_p_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    ab_test_significant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Monte Carlo
    monte_carlo_simulations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monte_carlo_confidence_interval: Mapped[float | None] = mapped_column(Float, nullable=True)
    monte_carlo_var_95: Mapped[float | None] = mapped_column(Float, nullable=True)
    monte_carlo_var_99: Mapped[float | None] = mapped_column(Float, nullable=True)
    monte_carlo_cvar_95: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Robustness
    regime_changes_tested: Mapped[list | None] = mapped_column(JSON, nullable=True)
    edge_cases_tested: Mapped[list | None] = mapped_column(JSON, nullable=True)
    parameter_sensitivity: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Sign-off
    sign_off_required: Mapped[bool] = mapped_column(Boolean, default=True)
    sign_off_role: Mapped[SignOffRole | None] = mapped_column(SAEnum(SignOffRole), nullable=True)
    sign_off_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sign_off_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sign_off_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    conditions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Validation report
    report_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    next_validation_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# --- 2. Vendor Risk Assessment ---

class VendorCriticality(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VendorStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNDER_REVIEW = "under_review"
    TERMINATED = "terminated"
    ONBOARDED = "onboarded"


class VendorCategory(str, enum.Enum):
    MARKET_DATA = "market_data"
    CLOUD_INFRASTRUCTURE = "cloud_infrastructure"
    CUSTODIAN = "custodian"
    EXCHANGE = "exchange"
    BROKER = "broker"
    KYC_AML = "kyc_aml"
    CYBERSECURITY = "cybersecurity"
    AUDIT = "audit"
    LEGAL = "legal"
    OTHER = "other"


class VendorRiskAssessment(Base):
    __tablename__ = "vendor_risk_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_category: Mapped[VendorCategory] = mapped_column(SAEnum(VendorCategory), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[VendorStatus] = mapped_column(SAEnum(VendorStatus), default=VendorStatus.ONBOARDED)
    criticality: Mapped[VendorCriticality] = mapped_column(SAEnum(VendorCriticality), default=VendorCriticality.MEDIUM)

    # Vendor details
    vendor_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor_website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contract_start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    contract_end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    annual_spend_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Due diligence
    due_diligence_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    due_diligence_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    due_diligence_score: Mapped[float] = mapped_column(Float, default=0.0)
    background_check: Mapped[bool] = mapped_column(Boolean, default=False)
    financial_stability_check: Mapped[bool] = mapped_column(Boolean, default=False)
    regulatory_status_check: Mapped[bool] = mapped_column(Boolean, default=False)

    # Security assessment
    soc2_type_ii: Mapped[bool] = mapped_column(Boolean, default=False)
    iso27001_certified: Mapped[bool] = mapped_column(Boolean, default=False)
    penetration_test_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    penetration_test_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    vulnerability_scan_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    open_vulnerabilities: Mapped[int] = mapped_column(Integer, default=0)
    critical_vulnerabilities: Mapped[int] = mapped_column(Integer, default=0)
    encryption_standard: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_residency_compliance: Mapped[bool] = mapped_column(Boolean, default=False)

    # SLA tracking
    sla_uptime_pct: Mapped[float] = mapped_column(Float, default=99.9)
    actual_uptime_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sla_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    sla_breaches_ytd: Mapped[int] = mapped_column(Integer, default=0)
    last_sla_review: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Supply chain
    sub_processors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fourth_party_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    data_sharing_agreement: Mapped[bool] = mapped_column(Boolean, default=False)
    incident_response_plan: Mapped[bool] = mapped_column(Boolean, default=False)
    business_continuity_plan: Mapped[bool] = mapped_column(Boolean, default=False)
    disaster_recovery_rto_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Compliance
    gdpr_compliant: Mapped[bool] = mapped_column(Boolean, default=False)
    ccpa_compliant: Mapped[bool] = mapped_column(Boolean, default=False)
    sanctions_screening: Mapped[bool] = mapped_column(Boolean, default=False)
    amil_kyc_compliant: Mapped[bool] = mapped_column(Boolean, default=False)

    # Risk scoring
    overall_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    security_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    operational_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    compliance_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    financial_risk_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Monitoring
    last_review_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_review_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_frequency: Mapped[str] = mapped_column(String(50), default="quarterly")
    incidents_ytd: Mapped[int] = mapped_column(Integer, default=0)
    escalations_ytd: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
