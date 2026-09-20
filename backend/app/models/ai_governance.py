"""AI Governance models — Model Cards, Algorithm Register, Validation Records, Bias Reports.

Covers the full governance lifecycle for AI in public debt optimization:
  - Model cards documenting purpose, limitations, validation results
  - Algorithm register for public transparency
  - Historical crisis backtesting records
  - Bias detection and mitigation logs
  - Human-in-the-loop approval workflows
  - Data lineage tracking
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


# ── Model Cards ──────────────────────────────────────────────────────

class ModelStatus(str, enum.Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    DEPLOYED = "deployed"
    RETIRED = "retired"
    FAILED_VALIDATION = "failed_validation"


class ModelCard(Base):
    """ML model documentation card — purpose, assumptions, limitations, validation."""
    __tablename__ = "ai_model_cards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    # Identity
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(String(100), nullable=False)  # ml_classifier, rule_engine, optimization, simulation
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # debt_sustainability, maturity_optimization, rating_prediction, etc.
    status: Mapped[ModelStatus] = mapped_column(SAEnum(ModelStatus), default=ModelStatus.DRAFT)

    # Purpose
    intended_use: Mapped[str] = mapped_column(Text, nullable=False)
    target_users: Mapped[str] = mapped_column(String(500), nullable=False)  # "Debt Management Office analysts"
    input_features: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {name: description, ...}
    output_type: Mapped[str] = mapped_column(String(255), nullable=False)  # "risk_score", "allocation", "classification"

    # Assumptions & Limitations
    assumptions: Mapped[list | None] = mapped_column(JSON, nullable=True)  # list of strings
    limitations: Mapped[list | None] = mapped_column(JSON, nullable=True)  # list of strings
    known_biases: Mapped[list | None] = mapped_column(JSON, nullable=True)  # list of strings
    training_data_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    training_data_period: Mapped[str | None] = mapped_column(String(100), nullable=True)
    training_data_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Performance
    accuracy_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {metric: value, ...}
    benchmark_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stress_test_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Ethical & Compliance
    fairness_assessment: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    explainability_method: Mapped[str | None] = mapped_column(String(255), nullable=True)  # "shap", "lime", "feature_importance", "rule_trace"
    human_oversight_required: Mapped[bool] = mapped_column(default=True)
    approval_required_before_deployment: Mapped[bool] = mapped_column(default=True)

    # Governance
    owner: Mapped[str] = mapped_column(String(255), nullable=False)  # responsible person/team
    reviewer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approval_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ── Algorithm Register (Public Transparency) ─────────────────────────

class AlgorithmEntry(Base):
    """Public register of all AI algorithms used in debt management."""
    __tablename__ = "ai_algorithm_register"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    # Registration
    register_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # "ALG-2024-001"
    algorithm_name: Mapped[str] = mapped_column(String(255), nullable=False)
    algorithm_type: Mapped[str] = mapped_column(String(100), nullable=False)  # optimization, classification, forecasting, anomaly_detection
    version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Purpose & Scope
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(String(255), nullable=False)  # "Sovereign debt portfolio optimization"
    domain: Mapped[str] = mapped_column(String(100), nullable=False)  # "public_finance"
    risk_level: Mapped[str] = mapped_column(String(50), nullable=False)  # "high", "medium", "low" per EU AI Act

    # Technical Details
    method_description: Mapped[str] = mapped_column(Text, nullable=False)
    input_data_sources: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ["yield_curve", "macro_indicators", ...]
    output_description: Mapped[str] = mapped_column(Text, nullable=False)
    computational_requirements: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Performance & Validation
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    f1_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    backtest_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Human Oversight
    human_oversight_level: Mapped[str] = mapped_column(String(50), nullable=False)  # "full_review", "approval_gate", "monitoring_only"
    decision_authority: Mapped[str] = mapped_column(String(255), nullable=False)  # "Finance Minister", "DMF Director"
    override_capability: Mapped[bool] = mapped_column(default=True)

    # Transparency
    public_description: Mapped[str | None] = mapped_column(Text, nullable=True)  # citizen-facing summary
    technical_documentation_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_public: Mapped[bool] = mapped_column(default=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    deployment_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_validation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_validation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ── Historical Crisis Backtesting ────────────────────────────────────

class CrisisScenario(Base):
    """Historical sovereign debt crisis scenario for backtesting."""
    __tablename__ = "ai_crisis_scenarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)

    crisis_name: Mapped[str] = mapped_column(String(255), nullable=False)  # "Argentina 2001", "Greece 2012"
    country_code: Mapped[str] = mapped_column(String(10), nullable=False)
    crisis_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "default", "restructuring", "currency_crisis", "contagion"
    start_date: Mapped[str] = mapped_column(String(20), nullable=False)  # "2001-12"
    end_date: Mapped[str] = mapped_column(String(20), nullable=False)  # "2005-03"

    # Pre-crisis indicators
    debt_to_gdp_at_crisis: Mapped[float] = mapped_column(Float, nullable=False)
    external_debt_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    reserve_coverage_months: Mapped[float] = mapped_column(Float, nullable=False)
    fiscal_balance_pct_gdp: Mapped[float] = mapped_column(Float, nullable=False)
    current_account_pct_gdp: Mapped[float] = mapped_column(Float, nullable=False)
    inflation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    gdp_growth_pct: Mapped[float] = mapped_column(Float, nullable=False)

    # Crisis parameters
    haircuts_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # % face value lost
    recovery_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    years_to_resolution: Mapped[float | None] = mapped_column(Float, nullable=True)
    contagion_spread_bps: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Historical data for backtesting
    historical_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # time series of indicators
    market_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # yield, CDS, FX data

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_references: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BacktestResult(Base):
    """Results of backtesting a model against historical crisis scenarios."""
    __tablename__ = "ai_backtest_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    model_card_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_model_cards.id"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_crisis_scenarios.id"), nullable=False)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    # Test configuration
    test_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lookback_months: Mapped[int] = mapped_column(Integer, nullable=False)  # how many months before crisis used as input
    prediction_horizon_months: Mapped[int] = mapped_column(Integer, nullable=False)

    # Results
    prediction: Mapped[str] = mapped_column(String(100), nullable=False)  # "crisis_predicted", "no_crisis_predicted"
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    actual_outcome: Mapped[str] = mapped_column(String(100), nullable=False)  # "crisis_occurred", "no_crisis"
    was_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Timing
    early_warning_months: Mapped[int | None] = mapped_column(Integer, nullable=True)  # how many months before crisis did model warn
    false_positive_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    false_negative_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Feature importance for this prediction
    top_features: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{feature: "debt_to_gdp", importance: 0.32}, ...]
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Recommendation vs actual
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_taken_historically: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Bias Detection & Data Quality ────────────────────────────────────

class BiasReport(Base):
    """Bias detection report for AI models and training data."""
    __tablename__ = "ai_bias_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    model_card_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ai_model_cards.id"), nullable=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "data_audit", "model_audit", "output_audit"

    # Data quality metrics
    completeness_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False)
    consistency_score: Mapped[float] = mapped_column(Float, nullable=False)
    timeliness_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Bias indicators
    demographic_parity: Mapped[float | None] = mapped_column(Float, nullable=True)
    equalized_odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    calibration_by_group: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Data coverage
    country_coverage: Mapped[list | None] = mapped_column(JSON, nullable=True)  # countries represented
    time_period_coverage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_freshness_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Findings
    biases_detected: Mapped[list | None] = mapped_column(JSON, nullable=True)  # list of bias descriptions
    severity_level: Mapped[str] = mapped_column(String(50), nullable=False)  # "low", "medium", "high", "critical"
    mitigation_actions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Sign-off
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, approved, rejected
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Human-in-the-Loop Governance ─────────────────────────────────────

class DecisionRecord(Base):
    """Record of an AI-generated decision requiring human approval."""
    __tablename__ = "ai_decision_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    model_card_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ai_model_cards.id"), nullable=True)

    # Decision context
    decision_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "portfolio_allocation", "refinancing", "issuance_timing"
    description: Mapped[str] = mapped_column(Text, nullable=False)
    urgency: Mapped[str] = mapped_column(String(50), default="normal")  # "urgent", "normal", "low"

    # AI output
    ai_recommendation: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    risk_factors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    alternative_scenarios: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Human decision
    human_decision: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "approved", "modified", "rejected"
    human_modifications: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    decision_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Workflow
    status: Mapped[str] = mapped_column(String(50), default="pending_review")  # pending_review, under_review, approved, modified, rejected, implemented
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    review_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_chain: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{role: "analyst", action: "reviewed", timestamp: ...}]

    # Audit
    immutable_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)  # SHA-256 of decision + outcome
    previous_state_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ── Data Lineage ─────────────────────────────────────────────────────

class DataLineageRecord(Base):
    """Tracks data from source through transformation to output."""
    __tablename__ = "ai_data_lineage"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)

    # Source
    source_system: Mapped[str] = mapped_column(String(255), nullable=False)  # "IFMIS", "Treasury.gov", "ECB", "manual_upload"
    source_table: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Transformation
    transformation_type: Mapped[str] = mapped_column(String(100), nullable=False)  # "import", "clean", "aggregate", "normalize", "merge"
    transformation_description: Mapped[str] = mapped_column(Text, nullable=False)
    transformation_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)  # hash of transformation code/version

    # Output
    output_system: Mapped[str] = mapped_column(String(255), nullable=False)  # "ai_model_input", "dashboard", "report"
    output_table: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_record_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Quality
    input_records: Mapped[int] = mapped_column(Integer, default=0)
    output_records: Mapped[int] = mapped_column(Integer, default=0)
    records_dropped: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Chain
    upstream_lineage_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # link to previous transformation
    model_card_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ai_model_cards.id"), nullable=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Explainability Reports ───────────────────────────────────────────

class ExplainabilityReport(Base):
    """Human-readable explanation for an AI recommendation or decision."""
    __tablename__ = "ai_explainability_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    model_card_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ai_model_cards.id"), nullable=True)
    decision_record_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ai_decision_records.id"), nullable=True)

    # Report content
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "shap", "lime", "feature_importance", "rule_trace", "counterfactual"
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Feature contributions
    feature_contributions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # [{feature: "debt_to_gdp", value: 65.2, contribution: +0.32, direction: "increases_risk"}]

    # Rule trace (for rule-based systems)
    rules_fired: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # [{rule: "IF debt_to_gdp > 60 THEN risk = HIGH", confidence: 0.95, weight: 0.4}]

    # Counterfactual
    counterfactuals: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # [{scenario: "If GDP growth were 1% higher", impact: "Risk score would decrease by 12 points"}]

    # Risk factors
    top_risk_factors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    mitigating_factors: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Visualization hints
    chart_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # pre-computed data for charts
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)  # plain-English explanation

    # Audience
    target_audience: Mapped[str] = mapped_column(String(50), nullable=False)  # "technical", "executive", "public"
    language: Mapped[str] = mapped_column(String(10), default="en")

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
