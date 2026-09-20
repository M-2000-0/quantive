"""PFM Data Import API — CSV/Excel upload and validation for government financial data.

Supports importing:
  - Budget entries (formulation, approval, execution)
  - Revenue records (tax, customs, other income)
  - Expenditure records (procurement, payroll, transfers)
  - Audit findings (internal, external, compliance)
  - Financial statements (annual, quarterly)
"""

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.government import GovernmentEntity
from app.models.pfm import (
    AuditFinding,
    AuditSeverity,
    AuditType,
    BudgetEntry,
    BudgetStatus,
    ExpenditureRecord,
    ExpenditureType,
    FinancialStatement,
    IFMISConnection,
    RevenueRecord,
    RevenueType,
    StatementType,
)
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/pfm", tags=["pfm"])


# ── Request/Response Models ──────────────────────────────────────────

class ImportResult(BaseModel):
    status: str
    records_imported: int
    records_skipped: int
    errors: list[str]
    warnings: list[str]
    import_id: str


class BudgetEntryInput(BaseModel):
    fiscal_year: int
    budget_code: str
    program_name: str
    department: str
    budget_category: str = "recurrent"
    description: str | None = None
    proposed_amount: float
    approved_amount: float
    executed_amount: float = 0
    revised_amount: float | None = None
    status: str = "proposed"
    currency: str = "USD"
    performance_indicator: str | None = None
    target_value: float | None = None
    actual_value: float | None = None


class RevenueRecordInput(BaseModel):
    fiscal_year: int
    fiscal_period: str
    revenue_type: str
    revenue_source: str
    target_amount: float
    collected_amount: float = 0
    currency: str = "USD"
    tax_to_gdp_pct: float | None = None


class ExpenditureRecordInput(BaseModel):
    fiscal_year: int
    fiscal_period: str
    expenditure_type: str
    description: str
    budgeted_amount: float
    committed_amount: float = 0
    actual_amount: float = 0
    procurement_method: str | None = None
    vendor_name: str | None = None
    contract_reference: str | None = None
    is_arrears: bool = False
    payment_delay_days: int | None = None
    currency: str = "USD"


class AuditFindingInput(BaseModel):
    audit_type: str
    audit_date: str  # ISO format
    auditor_name: str
    audit_reference: str | None = None
    title: str
    description: str
    criteria: str | None = None
    condition: str | None = None
    cause: str | None = None
    effect: str | None = None
    severity: str
    financial_impact: float | None = None
    currency: str = "USD"
    recommendation: str | None = None
    management_response: str | None = None


class FinancialStatementInput(BaseModel):
    statement_type: str
    fiscal_year: int
    period_end_date: str  # ISO format
    accounting_standard: str = "IPSAS"
    total_assets: float | None = None
    total_liabilities: float | None = None
    net_assets: float | None = None
    total_revenue: float | None = None
    total_expenditure: float | None = None
    fiscal_surplus_deficit: float | None = None
    total_debt_stock: float | None = None
    debt_to_gdp_pct: float | None = None
    currency: str = "USD"


class PFMSummary(BaseModel):
    total_budget_entries: int
    total_revenue_records: int
    total_expenditure_records: int
    total_audit_findings: int
    total_statements: int
    total_ifmis_connections: int
    latest_fiscal_year: int | None
    budget_execution_rate: float
    revenue_collection_rate: float
    open_audit_findings: int
    total_financial_impact: float


# ── CSV Parsing Helpers ──────────────────────────────────────────────

def parse_csv_upload(file_content: bytes) -> list[dict]:
    """Parse CSV file content into list of dicts."""
    text = file_content.decode("utf-8-sig")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def parse_excel_upload(file_content: bytes, filename: str) -> list[dict]:
    """Parse Excel file content using openpyxl."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True)
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        rows = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            rows.append({headers[i]: row[i] for i in range(len(headers)) if i < len(row)})
        return rows
    except ImportError:
        raise HTTPException(status_code=400, detail="Excel support requires openpyxl. Use CSV format.")


# ── Budget Entry Import ──────────────────────────────────────────────

@router.post("/import/budget", response_model=ImportResult)
async def import_budget_entries(
    file: UploadFile = File(...),
    fiscal_year: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import budget entries from CSV or Excel file.

    Expected columns: fiscal_year, budget_code, program_name, department,
    budget_category, proposed_amount, approved_amount, executed_amount, status, currency
    """
    content = await file.read()
    filename = file.filename or "unknown.csv"

    if filename.endswith((".xlsx", ".xls")):
        rows = parse_excel_upload(content, filename)
    else:
        rows = parse_csv_upload(content)

    errors = []
    warnings = []
    imported = 0
    skipped = 0
    import_id = str(uuid.uuid4())

    for i, row in enumerate(rows, 1):
        try:
            fy = fiscal_year or int(row.get("fiscal_year", 0))
            if fy == 0:
                errors.append(f"Row {i}: Missing fiscal_year")
                skipped += 1
                continue

            budget_code = row.get("budget_code", "").strip()
            if not budget_code:
                errors.append(f"Row {i}: Missing budget_code")
                skipped += 1
                continue

            entry = BudgetEntry(
                org_id=user.org_id,
                fiscal_year=fy,
                budget_code=budget_code,
                program_name=row.get("program_name", f"Program {budget_code}"),
                department=row.get("department", "Unknown"),
                budget_category=row.get("budget_category", "recurrent"),
                description=row.get("description"),
                proposed_amount=float(row.get("proposed_amount", 0)),
                approved_amount=float(row.get("approved_amount", 0)),
                executed_amount=float(row.get("executed_amount", 0)),
                revised_amount=float(row.get("revised_amount")) if row.get("revised_amount") else None,
                status=BudgetStatus(row.get("status", "proposed")),
                currency=row.get("currency", "USD"),
                performance_indicator=row.get("performance_indicator"),
                target_value=float(row["target_value"]) if row.get("target_value") else None,
                actual_value=float(row["actual_value"]) if row.get("actual_value") else None,
                source_file=filename,
            )
            db.add(entry)
            imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
            skipped += 1

    db.commit()

    return ImportResult(
        status="success" if imported > 0 else "no_records",
        records_imported=imported,
        records_skipped=skipped,
        errors=errors,
        warnings=warnings,
        import_id=import_id,
    )


# ── Revenue Record Import ────────────────────────────────────────────

@router.post("/import/revenue", response_model=ImportResult)
async def import_revenue_records(
    file: UploadFile = File(...),
    fiscal_year: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import revenue records from CSV/Excel.

    Expected columns: fiscal_year, fiscal_period, revenue_type, revenue_source,
    target_amount, collected_amount, currency
    """
    content = await file.read()
    filename = file.filename or "unknown.csv"

    if filename.endswith((".xlsx", ".xls")):
        rows = parse_excel_upload(content, filename)
    else:
        rows = parse_csv_upload(content)

    errors = []
    imported = 0
    skipped = 0
    import_id = str(uuid.uuid4())

    for i, row in enumerate(rows, 1):
        try:
            fy = fiscal_year or int(row.get("fiscal_year", 0))
            if fy == 0:
                errors.append(f"Row {i}: Missing fiscal_year")
                skipped += 1
                continue

            target = float(row.get("target_amount", 0))
            collected = float(row.get("collected_amount", 0))
            variance = collected - target
            variance_pct = (variance / target * 100) if target > 0 else 0
            collection_rate = (collected / target * 100) if target > 0 else 0

            record = RevenueRecord(
                org_id=user.org_id,
                fiscal_year=fy,
                fiscal_period=row.get("fiscal_period", "annual"),
                revenue_type=RevenueType(row.get("revenue_type", "tax")),
                revenue_source=row.get("revenue_source", "Unknown"),
                target_amount=target,
                collected_amount=collected,
                variance_amount=variance,
                variance_pct=round(variance_pct, 2),
                collection_rate=round(collection_rate, 2),
                currency=row.get("currency", "USD"),
                tax_to_gdp_pct=float(row["tax_to_gdp_pct"]) if row.get("tax_to_gdp_pct") else None,
                source_file=filename,
            )
            db.add(record)
            imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
            skipped += 1

    db.commit()

    return ImportResult(
        status="success" if imported > 0 else "no_records",
        records_imported=imported,
        records_skipped=skipped,
        errors=errors,
        warnings=[],
        import_id=import_id,
    )


# ── Expenditure Record Import ────────────────────────────────────────

@router.post("/import/expenditure", response_model=ImportResult)
async def import_expenditure_records(
    file: UploadFile = File(...),
    fiscal_year: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import expenditure records from CSV/Excel.

    Expected columns: fiscal_year, fiscal_period, expenditure_type, description,
    budgeted_amount, committed_amount, actual_amount, procurement_method,
    vendor_name, is_arrears, payment_delay_days, currency
    """
    content = await file.read()
    filename = file.filename or "unknown.csv"

    if filename.endswith((".xlsx", ".xls")):
        rows = parse_excel_upload(content, filename)
    else:
        rows = parse_csv_upload(content)

    errors = []
    imported = 0
    skipped = 0
    import_id = str(uuid.uuid4())

    for i, row in enumerate(rows, 1):
        try:
            fy = fiscal_year or int(row.get("fiscal_year", 0))
            if fy == 0:
                errors.append(f"Row {i}: Missing fiscal_year")
                skipped += 1
                continue

            budgeted = float(row.get("budgeted_amount", 0))
            actual = float(row.get("actual_amount", 0))
            variance = actual - budgeted

            record = ExpenditureRecord(
                org_id=user.org_id,
                fiscal_year=fy,
                fiscal_period=row.get("fiscal_period", "annual"),
                expenditure_type=ExpenditureType(row.get("expenditure_type", "goods_services")),
                description=row.get("description", "Unknown expenditure"),
                budgeted_amount=budgeted,
                committed_amount=float(row.get("committed_amount", 0)),
                actual_amount=actual,
                variance_amount=variance,
                procurement_method=row.get("procurement_method"),
                vendor_name=row.get("vendor_name"),
                contract_reference=row.get("contract_reference"),
                is_arrears=row.get("is_arrears", "").lower() in ("true", "1", "yes"),
                payment_delay_days=int(row["payment_delay_days"]) if row.get("payment_delay_days") else None,
                currency=row.get("currency", "USD"),
                source_file=filename,
            )
            db.add(record)
            imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
            skipped += 1

    db.commit()

    return ImportResult(
        status="success" if imported > 0 else "no_records",
        records_imported=imported,
        records_skipped=skipped,
        errors=errors,
        warnings=[],
        import_id=import_id,
    )


# ── Audit Finding Import ─────────────────────────────────────────────

@router.post("/import/audit", response_model=ImportResult)
async def import_audit_findings(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import audit findings from CSV/Excel.

    Expected columns: audit_type, audit_date, auditor_name, audit_reference,
    title, description, criteria, condition, cause, effect, severity,
    financial_impact, currency, recommendation, management_response
    """
    content = await file.read()
    filename = file.filename or "unknown.csv"

    if filename.endswith((".xlsx", ".xls")):
        rows = parse_excel_upload(content, filename)
    else:
        rows = parse_csv_upload(content)

    errors = []
    imported = 0
    skipped = 0
    import_id = str(uuid.uuid4())

    for i, row in enumerate(rows, 1):
        try:
            audit_date_str = row.get("audit_date", "")
            if audit_date_str:
                audit_date = datetime.fromisoformat(audit_date_str.replace("Z", "+00:00"))
            else:
                audit_date = datetime.now(timezone.utc)

            finding = AuditFinding(
                org_id=user.org_id,
                audit_type=AuditType(row.get("audit_type", "internal")),
                audit_date=audit_date,
                auditor_name=row.get("auditor_name", "Unknown"),
                audit_reference=row.get("audit_reference"),
                title=row.get("title", f"Finding {i}"),
                description=row.get("description", ""),
                criteria=row.get("criteria"),
                condition=row.get("condition"),
                cause=row.get("cause"),
                effect=row.get("effect"),
                severity=AuditSeverity(row.get("severity", "medium")),
                financial_impact=float(row["financial_impact"]) if row.get("financial_impact") else None,
                currency=row.get("currency", "USD"),
                recommendation=row.get("recommendation"),
                management_response=row.get("management_response"),
                source_file=filename,
            )
            db.add(finding)
            imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
            skipped += 1

    db.commit()

    return ImportResult(
        status="success" if imported > 0 else "no_records",
        records_imported=imported,
        records_skipped=skipped,
        errors=errors,
        warnings=[],
        import_id=import_id,
    )


# ── Financial Statement Import ───────────────────────────────────────

@router.post("/import/financial-statement", response_model=ImportResult)
async def import_financial_statements(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import financial statements from CSV/Excel.

    Expected columns: statement_type, fiscal_year, period_end_date,
    accounting_standard, total_assets, total_liabilities, net_assets,
    total_revenue, total_expenditure, fiscal_surplus_deficit,
    total_debt_stock, debt_to_gdp_pct, currency
    """
    content = await file.read()
    filename = file.filename or "unknown.csv"

    if filename.endswith((".xlsx", ".xls")):
        rows = parse_excel_upload(content, filename)
    else:
        rows = parse_csv_upload(content)

    errors = []
    imported = 0
    skipped = 0
    import_id = str(uuid.uuid4())

    for i, row in enumerate(rows, 1):
        try:
            fy = int(row.get("fiscal_year", 0))
            if fy == 0:
                errors.append(f"Row {i}: Missing fiscal_year")
                skipped += 1
                continue

            period_end_str = row.get("period_end_date", "")
            if period_end_str:
                period_end = datetime.fromisoformat(period_end_str.replace("Z", "+00:00"))
            else:
                period_end = datetime(fy, 12, 31, tzinfo=timezone.utc)

            stmt = FinancialStatement(
                org_id=user.org_id,
                statement_type=StatementType(row.get("statement_type", "annual")),
                fiscal_year=fy,
                period_end_date=period_end,
                accounting_standard=row.get("accounting_standard", "IPSAS"),
                total_assets=float(row["total_assets"]) if row.get("total_assets") else None,
                total_liabilities=float(row["total_liabilities"]) if row.get("total_liabilities") else None,
                net_assets=float(row["net_assets"]) if row.get("net_assets") else None,
                total_revenue=float(row["total_revenue"]) if row.get("total_revenue") else None,
                total_expenditure=float(row["total_expenditure"]) if row.get("total_expenditure") else None,
                fiscal_surplus_deficit=float(row["fiscal_surplus_deficit"]) if row.get("fiscal_surplus_deficit") else None,
                total_debt_stock=float(row["total_debt_stock"]) if row.get("total_debt_stock") else None,
                debt_to_gdp_pct=float(row["debt_to_gdp_pct"]) if row.get("debt_to_gdp_pct") else None,
                currency=row.get("currency", "USD"),
                source_file=filename,
                raw_data=row,
            )
            db.add(stmt)
            imported += 1

        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")
            skipped += 1

    db.commit()

    return ImportResult(
        status="success" if imported > 0 else "no_records",
        records_imported=imported,
        records_skipped=skipped,
        errors=errors,
        warnings=[],
        import_id=import_id,
    )


# ── PFM Dashboard Summary ────────────────────────────────────────────

@router.get("/summary", response_model=PFMSummary)
def get_pfm_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get PFM data summary for the organization."""
    budget_count = db.query(BudgetEntry).filter(BudgetEntry.org_id == user.org_id).count()
    revenue_count = db.query(RevenueRecord).filter(RevenueRecord.org_id == user.org_id).count()
    expenditure_count = db.query(ExpenditureRecord).filter(ExpenditureRecord.org_id == user.org_id).count()
    audit_count = db.query(AuditFinding).filter(AuditFinding.org_id == user.org_id).count()
    statement_count = db.query(FinancialStatement).filter(FinancialStatement.org_id == user.org_id).count()
    ifmis_count = db.query(IFMISConnection).filter(IFMISConnection.org_id == user.org_id).count()

    # Latest fiscal year
    latest_budget = db.query(BudgetEntry).filter(
        BudgetEntry.org_id == user.org_id
    ).order_by(BudgetEntry.fiscal_year.desc()).first()
    latest_fy = latest_budget.fiscal_year if latest_budget else None

    # Budget execution rate
    total_budgeted = db.query(BudgetEntry).filter(
        BudgetEntry.org_id == user.org_id
    ).with_entities(BudgetEntry.approved_amount).all()
    total_executed = db.query(BudgetEntry).filter(
        BudgetEntry.org_id == user.org_id
    ).with_entities(BudgetEntry.executed_amount).all()

    budgeted_sum = sum(float(b[0]) for b in total_budgeted) if total_budgeted else 0
    executed_sum = sum(float(e[0]) for e in total_executed) if total_executed else 0
    execution_rate = (executed_sum / budgeted_sum * 100) if budgeted_sum > 0 else 0

    # Revenue collection rate
    total_target = db.query(RevenueRecord).filter(
        RevenueRecord.org_id == user.org_id
    ).with_entities(RevenueRecord.target_amount).all()
    total_collected = db.query(RevenueRecord).filter(
        RevenueRecord.org_id == user.org_id
    ).with_entities(RevenueRecord.collected_amount).all()

    target_sum = sum(float(t[0]) for t in total_target) if total_target else 0
    collected_sum = sum(float(c[0]) for c in total_collected) if total_collected else 0
    collection_rate = (collected_sum / target_sum * 100) if target_sum > 0 else 0

    # Open audit findings
    open_findings = db.query(AuditFinding).filter(
        AuditFinding.org_id == user.org_id,
        AuditFinding.is_resolved == False,
    ).count()

    # Total financial impact from audit findings
    impact_query = db.query(AuditFinding).filter(
        AuditFinding.org_id == user.org_id,
        AuditFinding.financial_impact.isnot(None),
    ).with_entities(AuditFinding.financial_impact).all()
    total_impact = sum(float(f[0]) for f in impact_query) if impact_query else 0

    return PFMSummary(
        total_budget_entries=budget_count,
        total_revenue_records=revenue_count,
        total_expenditure_records=expenditure_count,
        total_audit_findings=audit_count,
        total_statements=statement_count,
        total_ifmis_connections=ifmis_count,
        latest_fiscal_year=latest_fy,
        budget_execution_rate=round(execution_rate, 2),
        revenue_collection_rate=round(collection_rate, 2),
        open_audit_findings=open_findings,
        total_financial_impact=round(total_impact, 2),
    )


# ── Data Retrieval Endpoints ─────────────────────────────────────────

@router.get("/budget")
def list_budget_entries(
    fiscal_year: Optional[int] = None,
    department: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List budget entries with optional filters."""
    query = db.query(BudgetEntry).filter(BudgetEntry.org_id == user.org_id)
    if fiscal_year:
        query = query.filter(BudgetEntry.fiscal_year == fiscal_year)
    if department:
        query = query.filter(BudgetEntry.department == department)
    entries = query.order_by(BudgetEntry.fiscal_year.desc()).limit(limit).all()
    return {
        "entries": [
            {
                "id": e.id,
                "fiscal_year": e.fiscal_year,
                "budget_code": e.budget_code,
                "program_name": e.program_name,
                "department": e.department,
                "budget_category": e.budget_category,
                "proposed_amount": float(e.proposed_amount),
                "approved_amount": float(e.approved_amount),
                "executed_amount": float(e.executed_amount),
                "execution_rate": round(float(e.executed_amount) / float(e.approved_amount) * 100, 2) if float(e.approved_amount) > 0 else 0,
                "status": e.status.value if e.status else "proposed",
                "currency": e.currency,
            }
            for e in entries
        ],
        "total": len(entries),
    }


@router.get("/revenue")
def list_revenue_records(
    fiscal_year: Optional[int] = None,
    revenue_type: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List revenue records with optional filters."""
    query = db.query(RevenueRecord).filter(RevenueRecord.org_id == user.org_id)
    if fiscal_year:
        query = query.filter(RevenueRecord.fiscal_year == fiscal_year)
    if revenue_type:
        query = query.filter(RevenueRecord.revenue_type == revenue_type)
    records = query.order_by(RevenueRecord.fiscal_year.desc()).limit(limit).all()
    return {
        "records": [
            {
                "id": r.id,
                "fiscal_year": r.fiscal_year,
                "fiscal_period": r.fiscal_period,
                "revenue_type": r.revenue_type.value if r.revenue_type else "tax",
                "revenue_source": r.revenue_source,
                "target_amount": float(r.target_amount),
                "collected_amount": float(r.collected_amount),
                "variance_pct": r.variance_pct,
                "collection_rate": r.collection_rate,
                "currency": r.currency,
            }
            for r in records
        ],
        "total": len(records),
    }


@router.get("/expenditure")
def list_expenditure_records(
    fiscal_year: Optional[int] = None,
    expenditure_type: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List expenditure records with optional filters."""
    query = db.query(ExpenditureRecord).filter(ExpenditureRecord.org_id == user.org_id)
    if fiscal_year:
        query = query.filter(ExpenditureRecord.fiscal_year == fiscal_year)
    if expenditure_type:
        query = query.filter(ExpenditureRecord.expenditure_type == expenditure_type)
    records = query.order_by(ExpenditureRecord.fiscal_year.desc()).limit(limit).all()
    return {
        "records": [
            {
                "id": r.id,
                "fiscal_year": r.fiscal_year,
                "fiscal_period": r.fiscal_period,
                "expenditure_type": r.expenditure_type.value if r.expenditure_type else "goods_services",
                "description": r.description,
                "budgeted_amount": float(r.budgeted_amount),
                "actual_amount": float(r.actual_amount),
                "variance_amount": float(r.variance_amount),
                "procurement_method": r.procurement_method,
                "is_arrears": r.is_arrears,
                "currency": r.currency,
            }
            for r in records
        ],
        "total": len(records),
    }


@router.get("/audit")
def list_audit_findings(
    audit_type: Optional[str] = None,
    severity: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List audit findings with optional filters."""
    query = db.query(AuditFinding).filter(AuditFinding.org_id == user.org_id)
    if audit_type:
        query = query.filter(AuditFinding.audit_type == audit_type)
    if severity:
        query = query.filter(AuditFinding.severity == severity)
    if resolved is not None:
        query = query.filter(AuditFinding.is_resolved == resolved)
    findings = query.order_by(AuditFinding.audit_date.desc()).limit(limit).all()
    return {
        "findings": [
            {
                "id": f.id,
                "audit_type": f.audit_type.value if f.audit_type else "internal",
                "audit_date": f.audit_date.isoformat() if f.audit_date else None,
                "auditor_name": f.auditor_name,
                "title": f.title,
                "severity": f.severity.value if f.severity else "medium",
                "financial_impact": float(f.financial_impact) if f.financial_impact else None,
                "is_resolved": f.is_resolved,
                "recommendation": f.recommendation,
                "currency": f.currency,
            }
            for f in findings
        ],
        "total": len(findings),
    }


# ── CSV Template Downloads ───────────────────────────────────────────

@router.get("/templates/{data_type}")
def download_template(data_type: str):
    """Download CSV template for data import.

    Supported data_types: budget, revenue, expenditure, audit, financial-statement
    """
    templates = {
        "budget": "fiscal_year,budget_code,program_name,department,budget_category,description,proposed_amount,approved_amount,executed_amount,revised_amount,status,currency,performance_indicator,target_value,actual_value\n2024,01-02-03-001,Health Program,Health Ministry,recurrent,Primary healthcare delivery,50000000,48000000,42000000,,executing,USD,Coverage rate,80,75",
        "revenue": "fiscal_year,fiscal_period,revenue_type,revenue_source,target_amount,collected_amount,currency,tax_to_gdp_pct\n2024,Q1,tax,Value Added Tax,2500000000,2350000000,USD,8.5\n2024,Q2,tax,Value Added Tax,2600000000,2480000000,USD,8.7",
        "expenditure": "fiscal_year,fiscal_period,expenditure_type,description,budgeted_amount,committed_amount,actual_amount,procurement_method,vendor_name,is_arrears,payment_delay_days,currency\n2024,Q1,goods_services,Medical supplies procurement,15000000,14500000,14000000,tender,PharmaCorp,,false,,USD\n2024,Q1,personnel,Teacher salaries,25000000,25000000,25000000,,,false,,USD",
        "audit": "audit_type,audit_date,auditor_name,audit_reference,title,description,criteria,condition,cause,effect,severity,financial_impact,currency,recommendation,management_response\ninternal,2024-06-15,Internal Audit Unit,IA-2024-001,Procurement irregularities,Contracts awarded without competitive bidding,Procurement Act Section 15,Three contracts awarded directly,Weak oversight,Financial loss,high,2500000,USD,Strengthen procurement controls,Training planned for Q3",
        "financial-statement": "statement_type,fiscal_year,period_end_date,accounting_standard,total_assets,total_liabilities,net_assets,total_revenue,total_expenditure,fiscal_surplus_deficit,total_debt_stock,debt_to_gdp_pct,currency\nannual,2024,2024-12-31,IPSAS,150000000000,120000000000,30000000000,45000000000,48000000000,-3000000000,85000000000,42.5,USD",
    }

    if data_type not in templates:
        raise HTTPException(status_code=400, detail=f"Unknown template type: {data_type}. Use: budget, revenue, expenditure, audit, financial-statement")

    return {"template": templates[data_type], "filename": f"pfm_{data_type}_template.csv"}
