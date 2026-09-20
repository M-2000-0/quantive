"""Broker Integration models — KYC/AML, Client Onboarding, Transaction Monitoring.

Covers the full broker-dealer lifecycle for government clients:
  - KYC/AML compliance (CIP, CDD, EDD)
  - Client onboarding workflows
  - Transaction monitoring and SAR filing
  - Broker registration tracking (Form BD, FINRA)
  - Fee and commission management
  - Best execution monitoring
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── KYC/AML Engine ───────────────────────────────────────────────────

class KYCStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    PENDING_DOCUMENTS = "pending_documents"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ESCALATED = "escalated"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"


class ClientKYC(Base):
    """Know Your Customer record for government entity clients."""
    __tablename__ = "broker_kyc_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    # Client identity
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "sovereign_wealth", "central_bank", "ministry", "treasury", "pension_fund"
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False)
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # CIP (Customer Identification Program)
    cip_verified: Mapped[bool] = mapped_column(default=False)
    cip_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cip_documents: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ["government_decree", "treasury_charter", "board_resolution"]
    cip_verification_method: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "documentary", "electronic", "reliance"

    # CDD (Customer Due Diligence)
    cdd_status: Mapped[KYCStatus] = mapped_column(SAEnum(KYCStatus), default=KYCStatus.NOT_STARTED)
    cdd_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    beneficial_ownership: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # [{name: "Ministry of Finance", ownership_pct: 100, role: "sole_owner"}]
    source_of_funds: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_of_wealth: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_activity: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # {monthly_trading_volume: 50000000, asset_types: ["bonds", "fx"], risk_tolerance: "conservative"}

    # EDD (Enhanced Due Diligence) — for high-risk clients
    edd_required: Mapped[bool] = mapped_column(default=False)
    edd_status: Mapped[KYCStatus] = mapped_column(SAEnum(KYCStatus), default=KYCStatus.NOT_STARTED)
    edd_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edd_findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    pep_status: Mapped[bool] = mapped_column(default=False)  # Politically Exposed Person
    sanctions_screening: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # { screened: true, matches: [], status: "clear" }

    # Risk assessment
    risk_level: Mapped[RiskLevel] = mapped_column(SAEnum(RiskLevel), default=RiskLevel.LOW)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    risk_factors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ["high_jurisdiction_risk", "complex_ownership", "large_transaction_volume"]

    # Overall status
    kyc_status: Mapped[KYCStatus] = mapped_column(SAEnum(KYCStatus), default=KYCStatus.NOT_STARTED)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approval_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Ongoing monitoring
    last_transaction_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ongoing_monitoring_frequency: Mapped[str] = mapped_column(String(50), default="annual")  # "quarterly", "semi_annual", "annual"
    alerts_count: Mapped[int] = mapped_column(Integer, default=0)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ── Client Onboarding ────────────────────────────────────────────────

class OnboardingStage(str, enum.Enum):
    INITIATED = "initiated"
    DOCUMENT_COLLECTION = "document_collection"
    KYC_REVIEW = "kyc_review"
    COMPLIANCE_APPROVAL = "compliance_approval"
    LEGAL_REVIEW = "legal_review"
    ACCOUNT_SETUP = "account_setup"
    FUNDING = "funding"
    ACTIVE = "active"
    REJECTED = "rejected"


class ClientOnboarding(Base):
    """Government client onboarding workflow."""
    __tablename__ = "broker_client_onboarding"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    kyc_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("broker_kyc_records.id"), nullable=True)

    # Client info
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_type: Mapped[str] = mapped_column(String(50), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False)

    # Onboarding workflow
    stage: Mapped[OnboardingStage] = mapped_column(SAEnum(OnboardingStage), default=OnboardingStage.INITIATED)
    initiated_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    target_completion_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_completion_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Document checklist
    documents_required: Mapped[list] = mapped_column(JSON, nullable=False)
    # ["government_decree", "board_resolution", "authorized_signatories", "proof_of_address", "financial_statements"]
    documents_submitted: Mapped[list | None] = mapped_column(JSON, nullable=True)
    documents_verified: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Stage progress
    stage_history: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # [{stage: "initiated", date: "...", actor: "...", notes: "..."}]
    current_assignee: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Account configuration
    account_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "cash", "margin", "custody"
    settlement_instructions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # {bank_name: "...", account_number: "...", swift: "...", currency: "USD"}
    trading_restrictions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ["no_short_selling", "bonds_only", "investment_grade_only"]

    # Fee schedule
    fee_schedule: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # {commission_bps: 5, custody_fee_annual: 0.001, min_balance: 1000000}

    status: Mapped[str] = mapped_column(String(50), default="in_progress")
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ── Transaction Monitoring ───────────────────────────────────────────

class TransactionAlertSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TransactionRecord(Base):
    """Transaction record for monitoring and reporting."""
    __tablename__ = "broker_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    kyc_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("broker_kyc_records.id"), nullable=True)
    trade_order_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Transaction details
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "buy", "sell", "transfer", "settlement"
    instrument_type: Mapped[str] = mapped_column(String(50), nullable=False)
    instrument_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    total_value: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Monitoring
    is_suspicious: Mapped[bool] = mapped_column(default=False)
    alert_severity: Mapped[TransactionAlertSeverity | None] = mapped_column(SAEnum(TransactionAlertSeverity), nullable=True)
    alert_reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # ["large_transaction", "unusual_pattern", "sanctions_match", "structuring"]

    # SAR (Suspicious Activity Report)
    sar_filed: Mapped[bool] = mapped_column(default=False)
    sar_filing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sar_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sar_narrative: Mapped[str | None] = mapped_column(Text, nullable=True)

    # CTR (Currency Transaction Report)
    ctr_required: Mapped[bool] = mapped_column(default=False)
    ctr_filed: Mapped[bool] = mapped_column(default=False)
    ctr_filing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status
    review_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, reviewed, cleared, escalated
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TransactionMonitoringRule(Base):
    """Rules for detecting suspicious transactions."""
    __tablename__ = "broker_monitoring_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "threshold", "pattern", "velocity", "sanctions"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Rule logic
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_currency: Mapped[str] = mapped_column(String(3), default="USD")
    time_window_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pattern_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Response
    alert_severity: Mapped[TransactionAlertSeverity] = mapped_column(SAEnum(TransactionAlertSeverity), default=TransactionAlertSeverity.MEDIUM)
    auto_escalate: Mapped[bool] = mapped_column(default=False)
    require_sar: Mapped[bool] = mapped_column(default=False)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Broker Registration ──────────────────────────────────────────────

class BrokerRegistration(Base):
    """Broker-dealer registration status with SEC, FINRA, and state regulators."""
    __tablename__ = "broker_registrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    # Registration identity
    registration_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "form_bd", "finra_membership", "state_registration", "government_securities"
    regulator: Mapped[str] = mapped_column(String(255), nullable=False)  # "SEC", "FINRA", "State of New York"
    crd_number: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Central Registration Depository
    filing_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, filed, under_review, approved, denied, suspended
    expiration_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    renewal_required: Mapped[bool] = mapped_column(default=True)

    # Requirements
    requirements: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # [{requirement: "net_capital", status: "met", value: 250000, threshold: 250000}]
    deficiencies: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Filings
    form_bd_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # parsed Form BD fields
    supporting_documents: Mapped[list | None] = mapped_column(JSON, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ── Fee & Commission Management ──────────────────────────────────────

class FeeSchedule(Base):
    """Fee and commission schedule for broker services."""
    __tablename__ = "broker_fee_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    schedule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "sovereign_wealth", "central_bank", "treasury"
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Commission structure
    commission_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "per_share", "per_trade", "bps_of_volume", "fixed"
    commission_value: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    minimum_commission: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    maximum_commission: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Asset-based fees
    custody_fee_annual_pct: Mapped[float] = mapped_column(Float, default=0)
    management_fee_annual_pct: Mapped[float] = mapped_column(Float, default=0)
    advisory_fee_annual_pct: Mapped[float] = mapped_column(Float, default=0)

    # Volume tiers
    volume_tiers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # [{min_volume: 0, max_volume: 10000000, commission_bps: 5}, ...]

    # Other fees
    settlement_fee: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    wire_fee: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    account_maintenance_fee: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    is_active: Mapped[bool] = mapped_column(default=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Best Execution ───────────────────────────────────────────────────

class BestExecutionRecord(Base):
    """Best execution analysis for order routing decisions."""
    __tablename__ = "broker_best_execution"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    trade_order_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Order details
    instrument_type: Mapped[str] = mapped_column(String(50), nullable=False)
    order_type: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)

    # Execution venues analyzed
    venues_analyzed: Mapped[list] = mapped_column(JSON, nullable=False)
    # [{venue: "NYSE", estimated_price: 100.25, estimated_spread_bps: 2, estimated_latency_ms: 50}]

    # Selected venue
    selected_venue: Mapped[str] = mapped_column(String(255), nullable=False)
    selection_reason: Mapped[str] = mapped_column(Text, nullable=False)

    # Execution quality
    actual_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    benchmark_price: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    price_improvement_bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_speed_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    fill_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Post-trade analysis
    implementation_shortfall_bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_impact_bps: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_cost_bps: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Compliance
    best_execution_confirmed: Mapped[bool] = mapped_column(default=True)
    exception_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Client Reporting ─────────────────────────────────────────────────

class ClientReport(Base):
    """Reports generated for broker clients."""
    __tablename__ = "broker_client_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    kyc_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("broker_kyc_records.id"), nullable=True)

    # Report details
    report_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "portfolio", "transaction", "compliance", "fee", "regulatory"
    report_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    report_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Content
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    report_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    # Delivery
    delivery_method: Mapped[str] = mapped_column(String(50), nullable=False)  # "portal", "email", "api", "sftp"
    delivered: Mapped[bool] = mapped_column(default=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged: Mapped[bool] = mapped_column(default=False)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
