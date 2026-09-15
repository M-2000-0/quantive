"""Qubo business tax API — universal deduction detection over the banking ledger.

Honesty contract (same as personal tax_packs):
- Findings are *potentially relevant* outflows with requirements — never
  promised savings, never eligibility guarantees.
- Every finding traces to a versioned rule (jurisdiction x tax year).
- Unsupported jurisdictions get generic guidance only, clearly labeled.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.banking import BankTransaction, QuboFinding
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
SCAN_LIMITS = {
    "free": 1,
    "pro": -1,   # unlimited
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
