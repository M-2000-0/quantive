"""Exchange & Broker Integration models — RegTech, Risk Controls, Interoperability.

Covers the full lifecycle of government-to-exchange partnerships:
  - Regulatory compliance monitoring and reporting
  - Exchange connectivity and order routing
  - Counterparty risk scoring and due diligence
  - Risk allocation frameworks
  - Regulatory data sharing with authorities
  - Ethical firewalls and conflict-of-interest tracking
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


# ── Exchange Connections ─────────────────────────────────────────────

class ExchangeType(str, enum.Enum):
    TRADITIONAL = "traditional"  # NYSE, LSE, TSE
    CRYPTO = "crypto"  # Binance, Coinbase, Kraken
    OTC = "otc"  # Over-the-counter desks
    INTERBANK = "interbank"  # FX and money market
    COMMODITY = "commodity"  # Commodity exchanges
    BOND = "bond"  # Bond trading platforms


class ConnectionStatus(str, enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SUSPENDED = "suspended"
    ERROR = "error"


class ExchangeConnection(Base):
    """Exchange or broker connection with API credentials and status."""
    __tablename__ = "exchange_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    # Identity
    exchange_name: Mapped[str] = mapped_column(String(255), nullable=False)  # "NYSE", "Binance", "Bloomberg"
    exchange_type: Mapped[ExchangeType] = mapped_column(SAEnum(ExchangeType), nullable=False)
    exchange_id: Mapped[str] = mapped_column(String(100), nullable=False)  # unique exchange identifier
    mic_code: Mapped[str | None] = mapped_column(String(10), nullable=True)  # Market Identifier Code

    # Connection
    api_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[ConnectionStatus] = mapped_column(SAEnum(ConnectionStatus), default=ConnectionStatus.DISCONNECTED)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Capabilities
    supports_bonds: Mapped[bool] = mapped_column(default=False)
    supports_fx: Mapped[bool] = mapped_column(default=False)
    supports_equities: Mapped[bool] = mapped_column(default=False)
    supports_derivatives: Mapped[bool] = mapped_column(default=False)
    supports_settlement_t_plus: Mapped[int] = mapped_column(Integer, default=2)  # T+2

    # Regulatory
    regulatory_status: Mapped[str] = mapped_column(String(50), default="pending_review")  # approved, pending_review, suspended
    regulatory_jurisdiction: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "SEC", "FCA", "CFTC"
    last_compliance_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    compliance_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Risk limits
    daily_trade_limit: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    max_single_trade: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    max_counterparty_exposure: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ── Regulatory Compliance ────────────────────────────────────────────

class ComplianceRule(Base):
    """Regulatory compliance rule that must be monitored."""
    __tablename__ = "compliance_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    # Rule definition
    rule_code: Mapped[str] = mapped_column(String(50), nullable=False)  # "REG-SEC-17a-4"
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    regulation: Mapped[str] = mapped_column(String(255), nullable=False)  # "SEC Rule 17a-4", "MiFID II", "Basel III"
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False)  # "US", "EU", "UK", "GLOBAL"
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # "recordkeeping", "reporting", "risk_limits", "capital_requirements"
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Thresholds
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "percentage", "days", "count", "currency"
    comparison_operator: Mapped[str] = mapped_column(String(10), default="<=")  # "<=", ">=", "==", "!="

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    is_critical: Mapped[bool] = mapped_column(default=False)  # violation triggers automatic halt
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ComplianceEvent(Base):
    """Record of a compliance check or violation."""
    __tablename__ = "compliance_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    rule_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("compliance_rules.id"), nullable=True)
    exchange_connection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("exchange_connections.id"), nullable=True)

    # Event details
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "check_passed", "check_failed", "violation", "waiver"
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Measurement
    measured_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    deviation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Resolution
    severity: Mapped[str] = mapped_column(String(50), nullable=False)  # "info", "warning", "critical", "halt"
    status: Mapped[str] = mapped_column(String(50), default="open")  # open, acknowledged, investigating, resolved, waived
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Reporting
    reported_to_authority: Mapped[bool] = mapped_column(default=False)
    authority_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reporting_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Counterparty Risk ────────────────────────────────────────────────

class CounterpartyRiskScore(Base):
    """Risk score for exchange/broker counterparties."""
    __tablename__ = "counterparty_risk_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    exchange_connection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("exchange_connections.id"), nullable=True)

    # Counterparty identity
    counterparty_name: Mapped[str] = mapped_column(String(255), nullable=False)
    counterparty_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "exchange", "broker", "bank", "market_maker"
    counterparty_rating: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "AAA", "BBB+", etc.
    jurisdiction: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Risk scores (0-100, higher = riskier)
    credit_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    operational_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    market_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    liquidity_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    regulatory_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    composite_risk_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Exposure
    current_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    potential_future_exposure: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    exposure_limit: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    utilization_pct: Mapped[float] = mapped_column(Float, default=0)

    # Due diligence
    last_audit_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_audit_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_diligence_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, complete, overdue
    documents_verified: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ["AML_policy", "financial_statements", ...]

    # Recommendation
    recommendation: Mapped[str] = mapped_column(String(50), nullable=False)  # "approved", "conditional", "restricted", "rejected"
    conditions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    max_trade_size: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    max_daily_volume: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ── Trade Order Tracking ─────────────────────────────────────────────

class TradeOrderStatus(str, enum.Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    SETTLED = "settled"


class TradeOrder(Base):
    """Government trade order with full audit trail and compliance checks."""
    __tablename__ = "trade_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    exchange_connection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("exchange_connections.id"), nullable=True)

    # Order details
    order_reference: Mapped[str] = mapped_column(String(100), nullable=False)  # internal reference
    exchange_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # exchange-assigned ID
    order_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "market", "limit", "stop", "twap", "vwap"
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # "buy", "sell"
    instrument_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "bond", "fx", "equity", "derivative"
    instrument_identifier: Mapped[str] = mapped_column(String(100), nullable=False)  # ISIN, CUSIP, ticker
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    price: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    total_value: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Execution
    status: Mapped[TradeOrderStatus] = mapped_column(SAEnum(TradeOrderStatus), default=TradeOrderStatus.PENDING_APPROVAL)
    filled_quantity: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    filled_price: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    commission: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    settlement_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settlement_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, settled, failed

    # Compliance
    pre_trade_compliance_passed: Mapped[bool] = mapped_column(default=False)
    post_trade_compliance_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    compliance_check_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Approval chain
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Risk metrics at time of order
    portfolio_impact: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    risk_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Audit
    immutable_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ── Risk Allocation Framework ────────────────────────────────────────

class RiskAllocation(Base):
    """Defines risk allocation between government and exchange counterparties."""
    __tablename__ = "risk_allocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    exchange_connection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("exchange_connections.id"), nullable=True)

    # Allocation framework
    framework_name: Mapped[str] = mapped_column(String(255), nullable=False)
    framework_version: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Risk categories and allocation
    market_risk_allocation: Mapped[dict] = mapped_column(JSON, nullable=False)
    # {government_pct: 60, counterparty_pct: 40, cap_per_trade: 1000000}
    credit_risk_allocation: Mapped[dict] = mapped_column(JSON, nullable=False)
    operational_risk_allocation: Mapped[dict] = mapped_column(JSON, nullable=False)
    liquidity_risk_allocation: Mapped[dict] = mapped_column(JSON, nullable=False)
    settlement_risk_allocation: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Limits
    max_government_loss: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    max_counterparty_loss: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    loss_sharing_trigger: Mapped[str] = mapped_column(String(100), nullable=False)  # "breach_of_contract", "system_failure", "market_event"
    dispute_resolution: Mapped[str] = mapped_column(String(100), nullable=False)  # "arbitration", "mediation", "litigation"
    governing_law: Mapped[str] = mapped_column(String(100), nullable=False)  # "English Law", "New York Law"

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approval_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Ethical Firewall ─────────────────────────────────────────────────

class EthicalFirewall(Base):
    """Tracks and prevents conflicts of interest in government-exchange partnerships."""
    __tablename__ = "ethical_firewalls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    # Personnel
    person_name: Mapped[str] = mapped_column(String(255), nullable=False)
    person_role: Mapped[str] = mapped_column(String(255), nullable=False)
    person_department: Mapped[str] = mapped_column(String(255), nullable=False)

    # Conflict tracking
    conflict_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "employment", "investment", "family", "advisory"
    conflict_description: Mapped[str] = mapped_column(Text, nullable=False)
    related_entity: Mapped[str] = mapped_column(String(255), nullable=False)  # exchange/broker name
    detected_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Cooling-off period
    cooling_off_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cooling_off_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_in_cooling_off: Mapped[bool] = mapped_column(default=False)

    # Mitigation
    mitigation_action: Mapped[str | None] = mapped_column(Text, nullable=True)  # "recusal", "divestment", "rotation"
    is_resolved: Mapped[bool] = mapped_column(default=False)
    resolved_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Regulatory Reporting ─────────────────────────────────────────────

class RegulatoryReport(Base):
    """Machine-readable regulatory report submitted to authorities."""
    __tablename__ = "regulatory_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    # Report identity
    report_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "transaction_report", "position_report", "risk_report", "compliance_report"
    report_format: Mapped[str] = mapped_column(String(50), nullable=False)  # "XML", "JSON", "CSV", "XBRL"
    reporting_authority: Mapped[str] = mapped_column(String(255), nullable=False)  # "SEC", "FCA", "CFTC", "ESMA"
    reporting_requirement: Mapped[str] = mapped_column(String(255), nullable=False)  # "MiFID II Article 26", "SEC Rule 13h-1"

    # Content
    reporting_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reporting_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    report_hash: Mapped[str] = mapped_column(String(128), nullable=False)  # SHA-256 of report content

    # Submission
    submission_status: Mapped[str] = mapped_column(String(50), default="draft")  # draft, validated, submitted, accepted, rejected
    submission_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    authority_acknowledgement: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Validation
    validation_errors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_valid: Mapped[bool] = mapped_column(default=False)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ── Market Data Feed ─────────────────────────────────────────────────

class MarketDataFeed(Base):
    """Real-time market data feed from connected exchanges."""
    __tablename__ = "market_data_feeds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    exchange_connection_id: Mapped[str] = mapped_column(String(36), ForeignKey("exchange_connections.id"), nullable=False)

    # Feed configuration
    feed_name: Mapped[str] = mapped_column(String(255), nullable=False)
    feed_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "quotes", "trades", "depth", "news"
    instruments: Mapped[list] = mapped_column(JSON, nullable=False)  # ["US10Y", "EUR/USD", ...]
    update_frequency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    last_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Quality
    data_quality_score: Mapped[float] = mapped_column(Float, default=1.0)
    gap_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── CCP (Central Counterparty) Compatibility ─────────────────────────

class CCPClearingMember(Base):
    """CCP clearing membership status and requirements."""
    __tablename__ = "ccp_clearing_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    exchange_connection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("exchange_connections.id"), nullable=True)

    ccp_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ccp_jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False)
    membership_status: Mapped[str] = mapped_column(String(50), nullable=False)

    initial_margin_required: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    variation_margin_frequency: Mapped[str] = mapped_column(String(50), default="daily")
    default_fund_contribution: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    skin_in_the_game: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    supports_bonds: Mapped[bool] = mapped_column(default=False)
    supports_derivatives: Mapped[bool] = mapped_column(default=False)
    supports_fx: Mapped[bool] = mapped_column(default=False)
    supports_commodities: Mapped[bool] = mapped_column(default=False)
    settlement_currency: Mapped[str] = mapped_column(String(3), default="USD")

    stress_test_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    mutualized_default_fund: Mapped[bool] = mapped_column(default=False)
    portability_enabled: Mapped[bool] = mapped_column(default=False)

    is_compliant: Mapped[bool] = mapped_column(default=True)
    last_audit_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    regulatory_requirements: Mapped[list | None] = mapped_column(JSON, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class SmartContractTemplate(Base):
    """Smart contract templates for automated trade execution and settlement."""
    __tablename__ = "smart_contract_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_type: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    blockchain: Mapped[str] = mapped_column(String(50), nullable=False)

    contract_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    pre_conditions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    execution_triggers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    settlement_logic: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    max_value_per_execution: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    requires_human_approval: Mapped[bool] = mapped_column(default=True)
    approval_threshold: Mapped[str] = mapped_column(String(50), default="any")
    emergency_halt_enabled: Mapped[bool] = mapped_column(default=True)

    code_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_audit_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    audit_result: Mapped[str | None] = mapped_column(String(50), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Institutional Capacity Assessment ────────────────────────────────

class InstitutionalCapacityAssessment(Base):
    """Assessment of government institutional capacity for exchange partnerships."""
    __tablename__ = "institutional_capacity_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    assessment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assessor: Mapped[str] = mapped_column(String(255), nullable=False)
    assessment_period: Mapped[str] = mapped_column(String(100), nullable=False)

    hr_score: Mapped[float] = mapped_column(Float, nullable=False)
    hr_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tech_score: Mapped[float] = mapped_column(Float, nullable=False)
    tech_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    process_score: Mapped[float] = mapped_column(Float, nullable=False)
    process_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    governance_score: Mapped[float] = mapped_column(Float, nullable=False)
    governance_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    data_quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    data_quality_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    composite_score: Mapped[float] = mapped_column(Float, nullable=False)
    rating: Mapped[str] = mapped_column(String(20), nullable=False)
    exchange_readiness: Mapped[str] = mapped_column(String(50), nullable=False)
    gaps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Algorithm Audit Trail ────────────────────────────────────────────

class AlgorithmAuditTrail(Base):
    """Immutable audit trail for algorithm decisions shown to exchanges during due diligence."""
    __tablename__ = "algorithm_audit_trails"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    model_card_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_description: Mapped[str] = mapped_column(Text, nullable=False)

    input_data_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    input_data_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    feature_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    execution_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    feature_importance: Mapped[list | None] = mapped_column(JSON, nullable=True)
    decision_path: Mapped[list | None] = mapped_column(JSON, nullable=True)
    rules_fired: Mapped[list | None] = mapped_column(JSON, nullable=True)

    human_review_required: Mapped[bool] = mapped_column(default=True)
    human_reviewed: Mapped[bool] = mapped_column(default=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    previous_event_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Pre-Built Exchange Connectors ────────────────────────────────────

class ExchangeConnectorTemplate(Base):
    """Pre-built connector templates for major exchanges and brokers."""
    __tablename__ = "exchange_connector_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)

    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange_name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange_type: Mapped[ExchangeType] = mapped_column(SAEnum(ExchangeType), nullable=False)
    mic_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country: Mapped[str] = mapped_column(String(50), nullable=False)

    supported_instruments: Mapped[list] = mapped_column(JSON, nullable=False)
    supported_order_types: Mapped[list] = mapped_column(JSON, nullable=False)
    settlement_cycles: Mapped[list] = mapped_column(JSON, nullable=False)
    supported_currencies: Mapped[list] = mapped_column(JSON, nullable=False)

    api_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_docs_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    authentication_method: Mapped[str] = mapped_column(String(100), nullable=False)
    rate_limits: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    regulatory_jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False)
    regulatory_requirements: Mapped[list | None] = mapped_column(JSON, nullable=True)
    kyc_required: Mapped[bool] = mapped_column(default=True)
    aml_required: Mapped[bool] = mapped_column(default=True)

    config_template: Mapped[dict] = mapped_column(JSON, nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
