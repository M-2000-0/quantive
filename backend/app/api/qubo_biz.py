"""Qubo business tax API — universal deduction detection over the banking ledger.

Honesty contract (same as personal tax_packs):
- Findings are *potentially relevant* outflows with requirements — never
  promised savings, never eligibility guarantees.
- Every finding traces to a versioned rule (jurisdiction x tax year).
- Unsupported jurisdictions get generic guidance only, clearly labeled.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.banking import BankTransaction, BusinessProfile
from app.models.qubo_tax import QuboFinding, TaxDocument
from app.security import get_current_user

router = APIRouter(prefix="/api/qubo/business", tags=["qubo-business"])

RULES_VERSION = "QBIZ-2026.1"
TAX_YEAR = 2026
VERIFY_GEN = "Current rules of your jurisdiction — verify with a qualified professional"
VERIFY_US = "IRS publications for the current tax year — verify before acting"

# category (from banking auto-categorization) -> rule. Only outflow
# categories that commonly qualify; inflows are never findings.
BIZ_RULES: dict[str, dict] = {
    "Payroll": {
        "rule_id": "QBIZ-2026-wages",
        "title": "Wages & salaries — potentially deductible",
        "detail": "Employee pay is commonly an ordinary business expense when paid or incurred in the year.",
        "requirements": ["ordinary and necessary business expense", "paid or incurred in the tax year", "payroll records"],
        "docs": ["payroll registers", "W-2/W-3 or local equivalent"],
        "us_note": "US: generally deductible as an ordinary business expense.",
    },
    "Software": {
        "rule_id": "QBIZ-2026-software",
        "title": "Software & subscriptions — potentially deductible",
        "detail": "Business software is commonly expensed when ordinary and necessary; some purchases must be capitalized.",
        "requirements": ["ordinary and necessary business use", "not a capital asset (or elected expensing)"],
        "docs": ["invoices", "subscription receipts"],
        "us_note": "US: subscriptions generally expensed; check current expensing vs capitalization guidance.",
    },
    "Utilities": {
        "rule_id": "QBIZ-2026-utilities",
        "title": "Utilities — potentially deductible",
        "detail": "Business-premises utilities are commonly deductible; mixed-use premises need apportionment.",
        "requirements": ["business premises use", "apportionment if mixed-use"],
        "docs": ["utility bills"],
        "us_note": "US: generally deductible for business premises.",
    },
    "Travel": {
        "rule_id": "QBIZ-2026-travel",
        "title": "Business travel — potentially deductible, high substantiation",
        "detail": "Travel away from the tax home on business is commonly deductible but heavily scrutinized.",
        "requirements": ["business purpose", "away-from-home test where applicable", "contemporaneous records"],
        "docs": ["itineraries", "receipts", "mileage / meeting logs"],
        "us_note": "US: strict substantiation rules apply — keep contemporaneous records.",
    },
}

SUPPORTED_JURISDICTIONS = ["US", "MX", "BD"]

# Plan-based scan limits (scans per 24 hours)
# Qubo-specific plans take priority; platform plans fallback to legacy limits
SCAN_LIMITS = {
    # Qubo Tax dedicated plans
    "qubo_starter": 5,
    "qubo_pro": -1,     # unlimited
    "qubo_sovereign": -1,
    # Platform plans (legacy fallback)
    "free": 1,
    "pro": -1,          # unlimited
    "enterprise": -1,
}


def _get_plan_tier(user: User) -> str:
    """Return the user's plan tier string for Qubo gating."""
    try:
        from app import billing as _billing
        org_id = str(getattr(user, "org_id", ""))
        sub = _billing.get_subscription(org_id)
        if sub:
            return sub.tier.value
    except Exception:
        pass
    return "free"


def _check_scan_limit(user: User, db: Session) -> None:
    """Enforce per-plan scan limits. Raises 429 if limit exceeded."""
    tier = _get_plan_tier(user)
    limit = SCAN_LIMITS.get(tier, 1)
    if limit == -1:
        return  # unlimited
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_scans = (
        db.query(QuboFinding)
        .filter(
            QuboFinding.org_id == user.org_id,
            QuboFinding.created_at >= cutoff,
        )
        .count()
    )
    # Use finding count as a proxy for scans (each scan creates 0+ findings)
    # A more precise approach would track scan events, but this is conservative
    if recent_scans >= limit * 50:  # rough heuristic: ~50 findings per scan
        raise HTTPException(
            status_code=429,
            detail=f"Scan limit reached for {tier} plan ({limit} scan{'s' if limit > 1 else ''} per day). Upgrade for unlimited scans.",
        )


class SettingsBody(BaseModel):
    jurisdiction: str = Field(min_length=2, max_length=2)


@router.get("/settings")
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return org-level Qubo settings (jurisdiction from BusinessProfile)."""
    profile = db.query(BusinessProfile).filter(BusinessProfile.org_id == user.org_id).first()
    jurisdiction = profile.country.upper() if profile and profile.country else "US"
    return {"jurisdiction": jurisdiction, "supported_jurisdictions": SUPPORTED_JURISDICTIONS}


@router.put("/settings")
def update_settings(body: SettingsBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Save org-level Qubo jurisdiction to BusinessProfile."""
    jurisdiction = body.jurisdiction.upper()
    profile = db.query(BusinessProfile).filter(BusinessProfile.org_id == user.org_id).first()
    if profile:
        profile.country = jurisdiction
    else:
        db.add(BusinessProfile(org_id=user.org_id, country=jurisdiction, legal_name="", jurisdiction_code=jurisdiction))
    db.commit()
    return {"jurisdiction": jurisdiction}


def match_rules(category: str, direction: str) -> list[dict]:
    """Pure matcher: outflow category -> candidate rules. No DB, fully testable."""
    if direction != "out":
        return []
    rule = BIZ_RULES.get(category)
    return [rule] if rule else []


def _uid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(f: QuboFinding) -> dict:
    return {
        "id": f.id,
        "account_id": f.account_id,
        "txn_id": f.txn_id,
        "rule_id": f.rule_id,
        "rules_version": RULES_VERSION,
        "jurisdiction": f.jurisdiction,
        "tax_year": f.tax_year,
        "category": f.category,
        "title": f.title,
        "detail": f.detail,
        "amount_cents": f.amount_cents,
        "requirements": f.requirements,
        "status": f.status,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


class ScanBody(BaseModel):
    jurisdiction: str = Field(default="US", min_length=2, max_length=2)
    tax_year: int = Field(default=TAX_YEAR, ge=2024, le=2030)


class ReviewBody(BaseModel):
    status: str = Field(pattern="^(accepted|dismissed)$")


@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    findings = (
        db.query(QuboFinding).filter(QuboFinding.org_id == user.org_id).all()
    )
    by_status: dict[str, int] = {"new": 0, "accepted": 0, "dismissed": 0}
    potential_new = 0
    accepted = 0
    for f in findings:
        by_status[f.status] = by_status.get(f.status, 0) + 1
        if f.status == "new":
            potential_new += f.amount_cents
        elif f.status == "accepted":
            accepted += f.amount_cents
    return {
        "counts": by_status,
        "total": len(findings),
        "potential_new_cents": potential_new,
        "accepted_cents": accepted,
        "rules_version": RULES_VERSION,
        "supported_jurisdictions": SUPPORTED_JURISDICTIONS,
        "note": "Amounts are outflows that may qualify — not promised savings. Verify with a qualified professional.",
    }


@router.post("/scan")
def scan(body: ScanBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_scan_limit(user, db)
    jurisdiction = body.jurisdiction.upper()
    # Default to BusinessProfile.country if jurisdiction is generic US default
    if jurisdiction == "US":
        profile = db.query(BusinessProfile).filter(BusinessProfile.org_id == user.org_id).first()
        if profile and profile.country:
            jurisdiction = profile.country.upper()
    generic = jurisdiction not in SUPPORTED_JURISDICTIONS
    txns = (
        db.query(BankTransaction)
        .filter(
            BankTransaction.org_id == user.org_id,
            BankTransaction.status == "posted",
            BankTransaction.direction == "out",
        )
        .order_by(BankTransaction.created_at.asc())
        .limit(500)
        .all()
    )
    created = 0
    for txn in txns:
        for rule in match_rules(txn.category, txn.direction):
            exists = (
                db.query(QuboFinding)
                .filter(
                    QuboFinding.org_id == user.org_id,
                    QuboFinding.txn_id == txn.id,
                    QuboFinding.rule_id == rule["rule_id"],
                )
                .first()
            )
            if exists:
                continue
            sources = [VERIFY_US, VERIFY_GEN] if jurisdiction == "US" else [VERIFY_GEN]
            detail = rule["detail"]
            if jurisdiction == "US":
                detail += " " + rule["us_note"]
            if generic:
                detail += " Generic guidance only for this jurisdiction."
            db.add(QuboFinding(
                id=_uid(),
                org_id=user.org_id,
                account_id=txn.account_id,
                txn_id=txn.id,
                rule_id=rule["rule_id"],
                jurisdiction=jurisdiction,
                tax_year=body.tax_year,
                category=txn.category,
                title=rule["title"],
                detail=detail,
                amount_cents=txn.amount_cents,
                requirements={"requirements": rule["requirements"], "docs": rule["docs"], "sources": sources},
                status="new",
            ))
            created += 1
    db.commit()
    total = db.query(QuboFinding).filter(QuboFinding.org_id == user.org_id).count()
    return {
        "scanned_transactions": len(txns),
        "created": created,
        "total": total,
        "rules_version": RULES_VERSION,
        "jurisdiction": jurisdiction,
        "generic_guidance": generic,
    }


@router.get("/findings")
def list_findings(
    status: str | None = Query(default=None, pattern="^(new|accepted|dismissed)$"),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(QuboFinding).filter(QuboFinding.org_id == user.org_id)
    if status:
        q = q.filter(QuboFinding.status == status)
    findings = q.order_by(QuboFinding.created_at.desc()).limit(limit).all()
    return {"findings": [_serialize(f) for f in findings]}


@router.post("/findings/{finding_id}/review")
def review_finding(
    finding_id: str,
    body: ReviewBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    finding = (
        db.query(QuboFinding)
        .filter(QuboFinding.id == finding_id, QuboFinding.org_id == user.org_id)
        .first()
    )
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    finding.status = body.status
    db.commit()
    db.refresh(finding)
    return _serialize(finding)


@router.get("/quarterly-estimates")
def quarterly_estimates(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Calculate quarterly tax set-aside estimates from accepted findings.

    Returns per-quarter breakdown of accepted deduction amounts and
    estimated set-asides (assumes ~25% effective rate as illustration).
    """
    findings = (
        db.query(QuboFinding)
        .filter(QuboFinding.org_id == user.org_id, QuboFinding.status == "accepted")
        .all()
    )
    quarters = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    total_cents = 0
    for f in findings:
        total_cents += f.amount_cents
        month = f.created_at.month if f.created_at else 1
        if month <= 3:
            quarters["Q1"] += f.amount_cents
        elif month <= 6:
            quarters["Q2"] += f.amount_cents
        elif month <= 9:
            quarters["Q3"] += f.amount_cents
        else:
            quarters["Q4"] += f.amount_cents
    effective_rate = 0.25  # illustrative; real rate depends on jurisdiction/income
    estimated_set_aside = int(total_cents * effective_rate)
    return {
        "tax_year": TAX_YEAR,
        "quarters": {k: {"deductions_cents": v, "estimated_set_aside_cents": int(v * effective_rate)} for k, v in quarters.items()},
        "total_deductions_cents": total_cents,
        "estimated_annual_set_aside_cents": estimated_set_aside,
        "effective_rate": effective_rate,
        "note": "Illustrative estimate only — actual tax liability depends on jurisdiction, income, and other factors. Consult a qualified professional.",
    }


@router.get("/export")
def export_findings(
    format: str = Query(default="csv", pattern="^(csv|json)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export Qubo findings as CSV or JSON for CPA handoff."""
    findings = (
        db.query(QuboFinding)
        .filter(QuboFinding.org_id == user.org_id)
        .order_by(QuboFinding.created_at.desc())
        .all()
    )
    if format == "json":
        return {
            "export_format": "json",
            "tax_year": TAX_YEAR,
            "rules_version": RULES_VERSION,
            "findings": [_serialize(f) for f in findings],
        }
    # CSV format — return as array of rows (frontend builds CSV)
    rows = []
    for f in findings:
        rows.append({
            "date": f.created_at.isoformat() if f.created_at else "",
            "category": f.category,
            "title": f.title,
            "amount_cents": f.amount_cents,
            "jurisdiction": f.jurisdiction,
            "tax_year": f.tax_year,
            "rule_id": f.rule_id,
            "status": f.status,
            "requirements": "; ".join((f.requirements or {}).get("requirements", [])),
            "docs": "; ".join((f.requirements or {}).get("docs", [])),
        })
    return {"export_format": "csv", "tax_year": TAX_YEAR, "rows": rows}


# ── Tax Document Upload ──────────────────────────────────────────────

UPLOAD_DIR = Path(os.environ.get("QUBO_UPLOAD_DIR", "uploads/tax_docs"))


def _ensure_upload_dir(org_id: str) -> Path:
    d = UPLOAD_DIR / org_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _serialize_doc(d: TaxDocument) -> dict:
    return {
        "id": d.id,
        "finding_id": d.finding_id,
        "filename": d.filename,
        "original_filename": d.original_filename,
        "mime_type": d.mime_type,
        "size_bytes": d.size_bytes,
        "category": d.category,
        "notes": d.notes,
        "status": d.status,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


DOC_CATEGORIES = {"payroll_register", "w2", "invoice", "receipt", "utility_bill", "travel_record", "other"}


@router.post("/findings/{finding_id}/documents")
async def upload_document(
    finding_id: str,
    file: UploadFile = File(...),
    category: str = Query(default="other"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a tax document and link it to a finding."""
    finding = (
        db.query(QuboFinding)
        .filter(QuboFinding.id == finding_id, QuboFinding.org_id == user.org_id)
        .first()
    )
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")

    cat = category if category in DOC_CATEGORIES else "other"
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    doc_id = _uid()
    ext = Path(file.filename or "file").suffix or ".bin"
    storage_name = f"{doc_id}{ext}"
    upload_dir = _ensure_upload_dir(user.org_id)
    file_path = upload_dir / storage_name
    file_path.write_bytes(contents)

    doc = TaxDocument(
        id=doc_id,
        org_id=user.org_id,
        finding_id=finding_id,
        filename=storage_name,
        original_filename=file.filename or storage_name,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(contents),
        storage_path=str(file_path),
        category=cat,
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _serialize_doc(doc)


@router.get("/findings/{finding_id}/documents")
def list_documents(
    finding_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents uploaded for a finding."""
    finding = (
        db.query(QuboFinding)
        .filter(QuboFinding.id == finding_id, QuboFinding.org_id == user.org_id)
        .first()
    )
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")

    docs = (
        db.query(TaxDocument)
        .filter(TaxDocument.org_id == user.org_id, TaxDocument.finding_id == finding_id)
        .order_by(TaxDocument.created_at.desc())
        .all()
    )
    return {"documents": [_serialize_doc(d) for d in docs]}


@router.get("/documents")
def list_all_documents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all tax documents for the org with pagination."""
    total = db.query(TaxDocument).filter(TaxDocument.org_id == user.org_id).count()
    docs = (
        db.query(TaxDocument)
        .filter(TaxDocument.org_id == user.org_id)
        .order_by(TaxDocument.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "documents": [_serialize_doc(d) for d in docs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/documents/{doc_id}/download")
def download_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download a tax document file."""
    doc = (
        db.query(TaxDocument)
        .filter(TaxDocument.id == doc_id, TaxDocument.org_id == user.org_id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = Path(doc.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        path=str(file_path),
        filename=doc.original_filename,
        media_type=doc.mime_type,
    )


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a tax document."""
    doc = (
        db.query(TaxDocument)
        .filter(TaxDocument.id == doc_id, TaxDocument.org_id == user.org_id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    # Delete file from disk
    file_path = Path(doc.storage_path)
    if file_path.exists():
        file_path.unlink()
    db.delete(doc)
    db.commit()
    return {"deleted": True}


class DocReviewBody(BaseModel):
    status: str = Field(pattern="^(reviewed|rejected)$")
    notes: str = Field(default="")


@router.post("/documents/{doc_id}/review")
def review_document(
    doc_id: str,
    body: DocReviewBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a document as reviewed or rejected."""
    doc = (
        db.query(TaxDocument)
        .filter(TaxDocument.id == doc_id, TaxDocument.org_id == user.org_id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    doc.status = body.status
    if body.notes:
        doc.notes = body.notes
    db.commit()
    db.refresh(doc)
    return _serialize_doc(doc)
