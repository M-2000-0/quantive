"""Exchange Due Diligence models - Pre-Trade Controls, Simulation, Surveillance, Proof of Reserve.

Covers the 5 gaps from exchange partnership research:
  1. Pre-trade controls (volume limits, price collars, self-trade avoidance)
  2. Simulation environments (paper trading, strategy testing before live)
  3. Market surveillance (manipulation detection, collusion, flash crashes)
  4. Proof of reserves (crypto exchange compliance)
  5. Decision logs with SHAP-style explanations
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


# --- 1. Pre-Trade Controls ---

class ControlType(str, enum.Enum):
    VOLUME_LIMIT = "volume_limit"
    PRICE_COLLAR = "price_collar"
    SELF_TRADE_AVOIDANCE = "self_trade_avoidance"
    POSITION_LIMIT = "position_limit"
    ORDER_SIZE_LIMIT = "order_size_limit"
    FREQUENCY_LIMIT = "frequency_limit"
    NOTIONAL_LIMIT = "notional_limit"
    DRAWDOWN_LIMIT = "drawdown_limit"
    CIRCUIT_BREAKER = "circuit_breaker"
    KILL_SWITCH = "kill_switch"


class ControlStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BREACHED = "breached"
    SUSPENDED = "suspended"


class PreTradeControl(Base):
    __tablename__ = "pre_trade_controls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    exchange_connection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("exchange_connections.id"), nullable=True)

    control_name: Mapped[str] = mapped_column(String(255), nullable=False)
    control_type: Mapped[ControlType] = mapped_column(SAEnum(ControlType), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ControlStatus] = mapped_column(SAEnum(ControlStatus), default=ControlStatus.ACTIVE)

    max_value: Mapped[float] = mapped_column(Float, nullable=False)
    warning_threshold_pct: Mapped[float] = mapped_column(Float, default=80.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    time_window_minutes: Mapped[int] = mapped_column(Integer, default=60)

    price_collar_upper_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_collar_lower_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    reference_price_source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    self_trade_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    self_trade_same_account: Mapped[bool] = mapped_column(Boolean, default=True)
    self_trade_related_accounts: Mapped[bool] = mapped_column(Boolean, default=True)

    reject_on_breach: Mapped[bool] = mapped_column(Boolean, default=True)
    alert_on_breach: Mapped[bool] = mapped_column(Boolean, default=True)
    escalation_contacts: Mapped[list | None] = mapped_column(JSON, nullable=True)

    total_checks: Mapped[int] = mapped_column(Integer, default=0)
    total_breaches: Mapped[int] = mapped_column(Integer, default=0)
    last_breach_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_check_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# --- 2. Simulation Environment ---

class SimulationStatus(str, enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimulationEnvironment(Base):
    __tablename__ = "simulation_environments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    environment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SimulationStatus] = mapped_column(SAEnum(SimulationStatus), default=SimulationStatus.CREATED)

    exchange_venue: Mapped[str] = mapped_column(String(100), nullable=False)
    instrument_types: Mapped[list | None] = mapped_column(JSON, nullable=True)
    historical_period: Mapped[str | None] = mapped_column(String(100), nullable=True)
    starting_capital: Mapped[float] = mapped_column(Float, default=10000000.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    simulated_latency_ms: Mapped[float] = mapped_column(Float, default=50.0)
    slippage_model: Mapped[str] = mapped_column(String(50), default="fixed")
    slippage_bps: Mapped[float] = mapped_column(Float, default=2.0)
    fill_rate_pct: Mapped[float] = mapped_column(Float, default=95.0)

    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    sharpe_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    win_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    fill_rejection_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    pre_trade_controls_tested: Mapped[list | None] = mapped_column(JSON, nullable=True)
    kill_switch_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    circuit_breaker_triggered: Mapped[bool] = mapped_column(Boolean, default=False)

    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    report_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# --- 3. Market Surveillance ---

class SurveillanceAlertType(str, enum.Enum):
    MANIPULATION = "manipulation"
    COLLUSION = "collusion"
    SPOOFING = "spoofing"
    LAYERING = "layering"
    WASH_TRADING = "wash_trading"
    FRONT_RUNNING = "front_running"
    MARKET_CORNER = "market_corner"
    FLASH_CRASH_RISK = "flash_crash_risk"
    UNUSUAL_VOLUME = "unusual_volume"
    UNUSUAL_PRICE_MOVE = "unusual_price_move"


class SurveillanceSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SurveillanceStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    REPORTED = "reported"


class MarketSurveillance(Base):
    __tablename__ = "market_surveillance_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    exchange_connection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("exchange_connections.id"), nullable=True)

    alert_type: Mapped[SurveillanceAlertType] = mapped_column(SAEnum(SurveillanceAlertType), nullable=False)
    severity: Mapped[SurveillanceSeverity] = mapped_column(SAEnum(SurveillanceSeverity), nullable=False)
    status: Mapped[SurveillanceStatus] = mapped_column(SAEnum(SurveillanceStatus), default=SurveillanceStatus.OPEN)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instrument_identifier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    affected_accounts: Mapped[list | None] = mapped_column(JSON, nullable=True)

    detection_rule: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)

    price_at_detection: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_at_detection: Mapped[float | None] = mapped_column(Float, nullable=True)
    spread_at_detection_bps: Mapped[float | None] = mapped_column(Float, nullable=True)

    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    investigation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_to_authority: Mapped[bool] = mapped_column(Boolean, default=False)
    authority_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    detected_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# --- 4. Proof of Reserve ---

class ReserveChain(str, enum.Enum):
    ETHEREUM = "ethereum"
    BITCOIN = "bitcoin"
    SOLANA = "solana"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    MULTI_CHAIN = "multi_chain"


class ReserveStatus(str, enum.Enum):
    VERIFIED = "verified"
    PENDING = "pending"
    FAILED = "failed"
    EXPIRED = "expired"
    DISPUTED = "disputed"


class ProofOfReserve(Base):
    __tablename__ = "proof_of_reserves"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    reserve_name: Mapped[str] = mapped_column(String(255), nullable=False)
    custodian_name: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False)

    total_reserves: Mapped[float] = mapped_column(Float, nullable=False)
    total_liabilities: Mapped[float] = mapped_column(Float, nullable=False)
    reserve_ratio_pct: Mapped[float] = mapped_column(Float, nullable=False)
    excess_reserves: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    reserve_assets: Mapped[list | None] = mapped_column(JSON, nullable=True)
    asset_types: Mapped[list | None] = mapped_column(JSON, nullable=True)

    chain: Mapped[ReserveChain] = mapped_column(SAEnum(ReserveChain), nullable=True)
    tx_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    block_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    merkle_root: Mapped[str | None] = mapped_column(String(256), nullable=True)
    attestation_service: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[ReserveStatus] = mapped_column(SAEnum(ReserveStatus), default=ReserveStatus.PENDING)
    verification_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_verification_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auditor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audit_report_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    zero_knowledge_proof: Mapped[bool] = mapped_column(Boolean, default=False)
    zkp_circuit_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    zkp_public_inputs: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# --- 5. Decision Logs (Enhanced Audit Trail) ---

class DecisionType(str, enum.Enum):
    TRADE_EXECUTION = "trade_execution"
    RISK_ALERT = "risk_alert"
    REBALANCE = "rebalance"
    HEDGING = "hedging"
    LIQUIDATION = "liquidation"
    COMPLIANCE_CHECK = "compliance_check"
    KILL_SWITCH = "kill_switch"
    CIRCUIT_BREAKER = "circuit_breaker"
    MANUAL_OVERRIDE = "manual_override"


class DecisionLog(Base):
    __tablename__ = "decision_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    exchange_connection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("exchange_connections.id"), nullable=True)
    model_card_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ai_model_cards.id"), nullable=True)

    decision_type: Mapped[DecisionType] = mapped_column(SAEnum(DecisionType), nullable=False)
    decision_id: Mapped[str] = mapped_column(String(100), nullable=False)

    instrument_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    instrument_identifier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[str | None] = mapped_column(String(10), nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    feature_contributions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    shap_values: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    explanation_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    pre_trade_checks_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    compliance_rules_checked: Mapped[list | None] = mapped_column(JSON, nullable=True)
    compliance_violations: Mapped[list | None] = mapped_column(JSON, nullable=True)

    human_review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_outcome: Mapped[str | None] = mapped_column(String(50), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    event_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    previous_event_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tamper_evident: Mapped[bool] = mapped_column(Boolean, default=True)

    decision_timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    execution_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
