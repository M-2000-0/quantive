"""Public Financial Management (PFM) data models.

Covers the full government financial management cycle:
  - Budget entries (formulation, approval, execution)
  - Revenue records (tax, customs, other income)
  - Expenditure records (procurement, payroll, transfers)
  - Audit findings (internal, external, compliance)
  - Financial statements (annual reports, quarterly)
  - IFMIS integration records
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Budget Entries ────────────────────────────────────────────────────

class BudgetStatus(str, enum.Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    EXECUTING = "executing"
    CLOSED = "closed"
    REVISED = "revised"


class BudgetEntry(Base):
    """Budget line item from formulation through execution."""
    __tablename__ = "pfm_budget_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=True)

    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_code: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "01-02-03-001"
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    budget_category: Mapped[str] = mapped_column(String(100), nullable=False)  # capital, recurrent, servicing
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Amounts in local currency
    proposed_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    approved_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    executed_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    revised_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    status: Mapped[BudgetStatus] = mapped_column(SAEnum(BudgetStatus), default=BudgetStatus.PROPOSED)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Performance metrics (for PBB)
    performance_indicator: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)  # imported from
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    revenue_records: Mapped[list["RevenueRecord"]] = relationship(back_populates="budget_entry")
    expenditure_records: Mapped[list["ExpenditureRecord"]] = relationship(back_populates="budget_entry")


# ── Revenue Records ──────────────────────────────────────────────────

class RevenueType(str, enum.Enum):
    TAX = "tax"
    CUSTOMS = "customs"
    NON_TAX = "non_tax"
    GRANTS = "grants"
    LOANS = "loans"
    OTHER = "other"


class RevenueRecord(Base):
    """Revenue collection records (tax, customs, other income)."""
    __tablename__ = "pfm_revenue_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=True)
    budget_entry_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("pfm_budget_entries.id"), nullable=True)

    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_period: Mapped[str] = mapped_column(String(20), nullable=False)  # "Q1", "M01", "annual"
    revenue_type: Mapped[RevenueType] = mapped_column(SAEnum(RevenueType), nullable=False)
    revenue_source: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., "VAT", "Income Tax", "Import Duties"

    # Amounts
    target_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    collected_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    variance_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    variance_pct: Mapped[float] = mapped_column(Float, default=0)

    collection_rate: Mapped[float] = mapped_column(Float, default=0)  # percentage
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Tax effort indicators
    tax_to_gdp_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    buoyancy_elasticity: Mapped[float | None] = mapped_column(Float, nullable=True)

    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    budget_entry: Mapped["BudgetEntry | None"] = relationship(back_populates="revenue_records")


# ── Expenditure Records ──────────────────────────────────────────────

class ExpenditureType(str, enum.Enum):
    PERSONNEL = "personnel"
    GOODS_SERVICES = "goods_services"
    CAPITAL = "capital"
    SUBSIDIES = "subsidies"
    TRANSFERS = "transfers"
    DEBT_SERVICE = "debt_service"
    GRANTS = "grants"
    OTHER = "other"


class ExpenditureRecord(Base):
    """Expenditure records (procurement, payroll, transfers)."""
    __tablename__ = "pfm_expenditure_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=True)
    budget_entry_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("pfm_budget_entries.id"), nullable=True)

    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_period: Mapped[str] = mapped_column(String(20), nullable=False)
    expenditure_type: Mapped[ExpenditureType] = mapped_column(SAEnum(ExpenditureType), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)

    # Amounts
    budgeted_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    committed_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    actual_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    variance_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    # Procurement specifics
    procurement_method: Mapped[str | None] = mapped_column(String(100), nullable=True)  # tender, direct, emergency
    vendor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contract_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Arrears tracking
    is_arrears: Mapped[bool] = mapped_column(default=False)
    payment_delay_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    currency: Mapped[str] = mapped_column(String(3), default="USD")
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    budget_entry: Mapped["BudgetEntry | None"] = relationship(back_populates="expenditure_records")


# ── Audit Findings ───────────────────────────────────────────────────

class AuditType(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"
    IT = "it"


class AuditSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditFinding(Base):
    """Audit findings from internal and external audits."""
    __tablename__ = "pfm_audit_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=True)

    audit_type: Mapped[AuditType] = mapped_column(SAEnum(AuditType), nullable=False)
    audit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    auditor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    audit_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Finding details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    criteria: Mapped[str | None] = mapped_column(Text, nullable=True)  # what should have been
    condition: Mapped[str | None] = mapped_column(Text, nullable=True)  # what was found
    cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    effect: Mapped[str | None] = mapped_column(Text, nullable=True)

    severity: Mapped[AuditSeverity] = mapped_column(SAEnum(AuditSeverity), nullable=False)
    financial_impact: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Follow-up
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    management_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_resolution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_resolved: Mapped[bool] = mapped_column(default=False)

    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Financial Statements ─────────────────────────────────────────────

class StatementType(str, enum.Enum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    MID_YEAR = "mid_year"
    SUPPLEMENTARY = "supplementary"


class FinancialStatement(Base):
    """Aggregated financial statements (balance sheet, income, cash flow)."""
    __tablename__ = "pfm_financial_statements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=True)

    statement_type: Mapped[StatementType] = mapped_column(SAEnum(StatementType), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accounting_standard: Mapped[str] = mapped_column(String(50), default="IPSAS")  # IPSAS, GAAP, IFRS

    # Balance sheet
    total_assets: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    total_liabilities: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    net_assets: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Income statement
    total_revenue: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    total_expenditure: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    fiscal_surplus_deficit: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Cash flow
    operating_cash_flow: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    investing_cash_flow: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    financing_cash_flow: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Debt metrics from statements
    total_debt_stock: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    debt_to_gdp_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    debt_service_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    currency: Mapped[str] = mapped_column(String(3), default="USD")
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # full parsed statement
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── IFMIS Integration Log �────────────────────────────────────────────

class IFMISConnection(Base):
    """Tracks IFMIS system connections and data syncs."""
    __tablename__ = "pfm_ifmis_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("government_entities.id"), nullable=True)

    system_name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g., "IFMIS-Zambia", "GIFMIS-Philippines"
    system_type: Mapped[str] = mapped_column(String(100), nullable=False)  # ifmis, gifmis, custom, spreadsheet
    connection_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Sync status
    last_sync_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, syncing, completed, failed
    records_synced: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Configuration
    data_format: Mapped[str] = mapped_column(String(50), default="csv")  # csv, json, xml, api
    sync_frequency: Mapped[str] = mapped_column(String(50), default="manual")  # manual, daily, weekly, monthly
    is_active: Mapped[bool] = mapped_column(default=True)

    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
