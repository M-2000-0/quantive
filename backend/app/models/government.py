"""Government entity hierarchy, fiscal rules, contingent liabilities, and transfers.

Covers national + subnational scope:
  - Entity hierarchy (national → state → municipality)
  - Fiscal rule compliance checks
  - Contingent liability / guarantee registry
  - Intergovernmental transfer linkage
  - Versioned assumptions with audit trail
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Entity Hierarchy ────────────────────────────────────────────────

class EntityType(str, enum.Enum):
    NATIONAL = "national"
    STATE = "state"
    MUNICIPALITY = "municipality"
    SOE = "soe"                       # state-owned enterprise
    SPECIAL_PURPOSE = "special_purpose"  # SPV for PPP etc.


class GovernmentEntity(Base):
    """A node in the public-sector entity tree."""
    __tablename__ = "government_entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(SAEnum(EntityType), nullable=False)
    iso_code: Mapped[str | None] = mapped_column(String(10), nullable=True)   # ISO 3166-2
    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gdp_local: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # self-referential
    parent: Mapped["GovernmentEntity | None"] = relationship(
        remote_side="GovernmentEntity.id", back_populates="children"
    )
    children: Mapped[list["GovernmentEntity"]] = relationship(back_populates="parent")

    portfolios: Mapped[list["EntityPortfolio"]] = relationship(back_populates="entity")
    fiscal_rules: Mapped[list["FiscalRule"]] = relationship(back_populates="entity")
    contingent_liabilities: Mapped[list["ContingentLiability"]] = relationship(back_populates="entity")
    transfer_links: Mapped[list["TransferLink"]] = relationship(
        back_populates="entity", foreign_keys="TransferLink.entity_id"
    )
    assumptions: Mapped[list["VersionedAssumption"]] = relationship(back_populates="entity")


class EntityPortfolio(Base):
    """A debt portfolio scoped to a government entity."""
    __tablename__ = "entity_portfolios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=False)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    entity: Mapped["GovernmentEntity"] = relationship(back_populates="portfolios")


# ── Fiscal Rules ────────────────────────────────────────────────────

class RuleType(str, enum.Enum):
    DEBT_CEILING = "debt_ceiling"                  # total debt ≤ X% GDP
    DEBT_SERVICE_RATIO = "debt_service_ratio"       # debt service ≤ X% revenue
    DEFICIT_LIMIT = "deficit_limit"                 # deficit ≤ X% GDP
    CURRENT_BALANCE = "current_balance"             # current balance ≥ X% GDP
    MATURITY_CONCENTRATION = "maturity_concentration"  # no single year > X% total
    FX_EXPOSURE_LIMIT = "fx_exposure_limit"         # foreign debt ≤ X% total
    CUSTOM = "custom"


class RuleSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    BREACH = "breach"
    CRITICAL = "critical"


class FiscalRule(Base):
    __tablename__ = "fiscal_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[RuleType] = mapped_column(SAEnum(RuleType), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)  # e.g. 60 for 60% GDP
    threshold_unit: Mapped[str] = mapped_column(String(50), nullable=False)         # "pct_gdp", "pct_revenue", "pct_total"
    is_hard_limit: Mapped[bool] = mapped_column(Boolean, default=True)
    statute_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    entity: Mapped["GovernmentEntity"] = relationship(back_populates="fiscal_rules")


class FiscalRuleEvaluation(Base):
    """Point-in-time evaluation of a fiscal rule."""
    __tablename__ = "fiscal_rule_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("fiscal_rules.id"), nullable=False)
    current_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    threshold_value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    headroom: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)       # threshold - current
    headroom_pct: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)   # headroom / threshold * 100
    severity: Mapped[RuleSeverity] = mapped_column(SAEnum(RuleSeverity), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    evaluation_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # underlying data used


# ── Contingent Liabilities ──────────────────────────────────────────

class CLType(str, enum.Enum):
    GOVT_GUARANTEE = "govt_guarantee"
    SOE_LOAN = "soe_loan"
    PPP_OBLIGATION = "ppp_obligation"
    SUBNATIONAL_LOAN = "subnational_loan"
    PENSION_OBLIGATION = "pension_obligation"
    ENVIRONMENTAL = "environmental"
    JUDGICIAL = "judicial"
    CUSTOM = "custom"


class ContingentLiability(Base):
    __tablename__ = "contingent_liabilities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cl_type: Mapped[CLType] = mapped_column(SAEnum(CLType), nullable=False)
    exposure_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    probability_of_call: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)  # 0-1
    expected_loss: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)     # exposure * probability
    counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instrument_ref_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("debt_instruments.id"), nullable=True)
    maturity_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_national_guarantee: Mapped[bool] = mapped_column(Boolean, default=False)
    statute_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    entity: Mapped["GovernmentEntity"] = relationship(back_populates="contingent_liabilities")


# ── Intergovernmental Transfers ─────────────────────────────────────

class TransferType(str, enum.Enum):
    REVENUE_SHARING = "revenue_sharing"
    BLOCK_GRANT = "block_grant"
    CONDITIONAL_GRANT = "conditional_grant"
    EQUALIZATION = "equalization"
    DEBT_SERVICE_SUPPORT = "debt_service_support"
    CUSTOM = "custom"


class TransferLink(Base):
    """Models the dependency: entity's debt service is partly backed by transfers from another entity."""
    __tablename__ = "transfer_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=False)
    source_entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=False)
    transfer_type: Mapped[TransferType] = mapped_column(SAEnum(TransferType), nullable=False)
    annual_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    covers_debt_service_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0.0)  # % of entity's debt service covered
    is_statutory: Mapped[bool] = mapped_column(Boolean, default=True)  # legally mandated vs discretionary
    conditionality: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    entity: Mapped["GovernmentEntity"] = relationship(
        back_populates="transfer_links", foreign_keys=[entity_id]
    )
    source_entity: Mapped["GovernmentEntity"] = relationship(foreign_keys=[source_entity_id])


# ── Versioned Assumptions ────────────────────────────────────────────

class AssumptionCategory(str, enum.Enum):
    MACRO = "macro"
    MARKET = "market"
    POLICY = "policy"
    DEMOGRAPHIC = "demographic"
    CUSTOM = "custom"


class AssumptionRisk(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VersionedAssumption(Base):
    """Every assumption is versioned and auditable with full transition tracking."""
    __tablename__ = "versioned_assumptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    entity_id: Mapped[str] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[AssumptionCategory] = mapped_column(SAEnum(AssumptionCategory), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)  # "pct", "ratio", "years", "usd"
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    changed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_value: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)

    # Administrative transition tracking
    administration_label: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., "Current", "Previous-Mensah"
    minister_at_change: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transition_trigger: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "handover", "policy_shift", "expiry"

    # Risk & initiative linkage
    associated_risks: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # risks activated/generated on assumption change
    active_initiatives: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # initiatives still open from this assumption period
    unresolved_issues: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # issues carried forward
    upcoming_deadlines: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # deadlines tied to this assumption period

    # Audit & knowledge persistence
    audit_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # chain hash for immutability
    knowledge_base_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # external KB reference
    persistence_status: Mapped[str] = mapped_column(String(20), default="active")  # "active", "archived", "migrated"
    migration_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    entity: Mapped["GovernmentEntity"] = relationship(back_populates="assumptions")
