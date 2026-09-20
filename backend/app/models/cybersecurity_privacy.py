"""Cybersecurity, Privacy, and Interoperability models.

Covers the 4 gaps from exchange partnership research:
  1. Real-time regulatory monitoring (behavioral signals, performance metrics)
  2. Cybersecurity controls (AI-specific security, encryption, adversarial protection)
  3. Data privacy compliance (GDPR, data breach protection, sensitive data)
  4. Interoperability standards (cross-framework compliance, AML/KYC standardization)
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


# --- 1. Real-Time Regulatory Monitoring ---

class MonitoringStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class AlertSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RegulatoryMonitoring(Base):
    __tablename__ = "regulatory_monitoring"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    monitor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[MonitoringStatus] = mapped_column(SAEnum(MonitoringStatus), default=MonitoringStatus.ACTIVE)

    # Target
    target_model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    exchange_connection_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("exchange_connections.id"), nullable=True)

    # Behavioral signals
    signal_types: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sampling_interval_seconds: Mapped[int] = mapped_column(Integer, default=60)
    retention_days: Mapped[int] = mapped_column(Integer, default=90)

    # Performance metrics tracked
    metrics_tracked: Mapped[list | None] = mapped_column(JSON, nullable=True)
    accuracy_threshold: Mapped[float] = mapped_column(Float, default=0.85)
    latency_threshold_ms: Mapped[float] = mapped_column(Float, default=100.0)
    drift_threshold_pct: Mapped[float] = mapped_column(Float, default=5.0)

    # Alerting
    alert_severity: Mapped[AlertSeverity] = mapped_column(SAEnum(AlertSeverity), default=AlertSeverity.MEDIUM)
    alert_contacts: Mapped[list | None] = mapped_column(JSON, nullable=True)
    auto_escalate: Mapped[bool] = mapped_column(Boolean, default=True)

    # Current status
    current_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_drift_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_signal_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_signals_captured: Mapped[int] = mapped_column(Integer, default=0)
    total_alerts_fired: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# --- 2. Cybersecurity Controls ---

class SecurityControlType(str, enum.Enum):
    ENCRYPTION_AT_REST = "encryption_at_rest"
    ENCRYPTION_IN_TRANSIT = "encryption_in_transit"
    KEY_MANAGEMENT = "key_management"
    ACCESS_CONTROL = "access_control"
    ADVERSARIAL_DEFENSE = "adversarial_defense"
    INTRUSION_DETECTION = "intrusion_detection"
    VULNERABILITY_SCAN = "vulnerability_scan"
    PENETRATION_TEST = "penetration_test"
    SECURE_ML_PIPELINE = "secure_ml_pipeline"
    MODEL_SAFETY = "model_safety"


class SecurityStatus(str, enum.Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    IN_PROGRESS = "in_progress"
    EXEMPTED = "exempted"
    UNKNOWN = "unknown"


class CybersecurityControl(Base):
    __tablename__ = "cybersecurity_controls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    control_name: Mapped[str] = mapped_column(String(255), nullable=False)
    control_type: Mapped[SecurityControlType] = mapped_column(SAEnum(SecurityControlType), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SecurityStatus] = mapped_column(SAEnum(SecurityStatus), default=SecurityStatus.UNKNOWN)

    # Encryption specifics
    encryption_algorithm: Mapped[str | None] = mapped_column(String(50), nullable=True)
    key_length_bits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    key_rotation_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Adversarial defense
    adversarial_testing_frequency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    adversarial_robustness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    attack_types_defended: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # ML pipeline security
    model_integrity_verification: Mapped[bool] = mapped_column(Boolean, default=False)
    supply_chain_scanning: Mapped[bool] = mapped_column(Boolean, default=False)
    sandbox_execution: Mapped[bool] = mapped_column(Boolean, default=False)

    # Compliance
    framework_references: Mapped[list | None] = mapped_column(JSON, nullable=True)
    last_audit_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_audit_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auditor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Metrics
    vulnerabilities_found: Mapped[int] = mapped_column(Integer, default=0)
    vulnerabilities_remediated: Mapped[int] = mapped_column(Integer, default=0)
    mean_time_to_remediate_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    security_score: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# --- 3. Data Privacy Compliance ---

class PrivacyFramework(str, enum.Enum):
    GDPR = "gdpr"
    CCPA = "ccpa"
    PIPL = "pipi"
    LGPD = "lgpd"
    PDPA = "pdpa"
    CUSTOM = "custom"


class DataClassification(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


class DataPrivacyCompliance(Base):
    __tablename__ = "data_privacy_compliance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    policy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    framework: Mapped[PrivacyFramework] = mapped_column(SAEnum(PrivacyFramework), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Data scope
    data_types: Mapped[list | None] = mapped_column(JSON, nullable=True)
    data_classification: Mapped[DataClassification] = mapped_column(SAEnum(DataClassification), default=DataClassification.CONFIDENTIAL)
    jurisdictions: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Controls
    encryption_required: Mapped[bool] = mapped_column(Boolean, default=True)
    anonymization_required: Mapped[bool] = mapped_column(Boolean, default=False)
    pseudonymization_required: Mapped[bool] = mapped_column(Boolean, default=False)
    data_retention_days: Mapped[int] = mapped_column(Integer, default=365)
    right_to_erasure: Mapped[bool] = mapped_column(Boolean, default=True)
    data_portability: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_management: Mapped[bool] = mapped_column(Boolean, default=True)

    # Breach management
    breach_notification_hours: Mapped[int] = mapped_column(Integer, default=72)
    breach_notification_authorities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    breach_response_plan: Mapped[bool] = mapped_column(Boolean, default=True)

    # Status
    is_compliant: Mapped[bool] = mapped_column(Boolean, default=False)
    last_audit_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_audit_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    dpia_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    dpo_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Metrics
    data_subject_requests: Mapped[int] = mapped_column(Integer, default=0)
    breach_incidents: Mapped[int] = mapped_column(Integer, default=0)
    privacy_score: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


# --- 4. Interoperability Standards ---

class InteroperabilityFramework(str, enum.Enum):
    FIX_PROTOCOL = "fix_protocol"
    ISO_20022 = "iso_20022"
    SWIFT_MESSAGING = "swift_messaging"
    REST_API = "rest_api"
    GRPC = "grpc"
    BLOCKCHAIN = "blockchain"
    CUSTOM = "custom"


class ComplianceStandardStatus(str, enum.Enum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    PLANNED = "planned"
    NOT_SUPPORTED = "not_supported"


class InteroperabilityStandard(Base):
    __tablename__ = "interoperability_standards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    standard_name: Mapped[str] = mapped_column(String(255), nullable=False)
    framework: Mapped[InteroperabilityFramework] = mapped_column(SAEnum(InteroperabilityFramework), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Scope
    jurisdictions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    asset_types: Mapped[list | None] = mapped_column(JSON, nullable=True)
    exchange_venues: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # AML/KYC standardization
    aml_kyc_standard: Mapped[str | None] = mapped_column(String(100), nullable=True)
    kyc_data_format: Mapped[str | None] = mapped_column(String(50), nullable=True)
    transaction_monitoring_format: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Settlement interoperability
    settlement_systems: Mapped[list | None] = mapped_column(JSON, nullable=True)
    dtvp_support: Mapped[bool] = mapped_column(Boolean, default=False)
    netting_support: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    status: Mapped[ComplianceStandardStatus] = mapped_column(SAEnum(ComplianceStandardStatus), default=ComplianceStandardStatus.PLANNED)
    implementation_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_test_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_review_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Testing
    test_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    compatibility_score: Mapped[float] = mapped_column(Float, default=0.0)
    messages_processed: Mapped[int] = mapped_column(Integer, default=0)
    error_rate_pct: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
