"""Quantive Banking API (sandbox ledger).

Compliant-by-design framing, enforced in code:
- Every movement carries ``fee_cents = 0``. There is no code path that
  charges a per-transaction fee — revenue comes from deposit spread,
  subscriptions, lending and treasury products, never from fees.
- All money is integer cents; balances move as double-entry pairs.
- Transfers are idempotent (``idempotency_key`` scoped per org).
- Everything is org-scoped: users only ever see their own org's money.
- This is a sandbox ledger. Real funds would sit with a licensed
  partner bank (BaaS) with KYC/KYB, AML monitoring and reporting.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.models.banking import BankAccount, BankTransaction, BankTransfer, BusinessProfile
from app.security import get_current_user, require_role

router = APIRouter(prefix="/api/banking", tags=["banking"])

FEE_CENTS = 0  # Structural zero. There is no fee code path.
MAX_CENTS = 999_999_999_999


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return str(uuid.uuid4())


# ── AI CFO helpers (rule-based, deterministic, labeled estimates) ──

_CATEGORY_RULES: tuple[tuple[str, str, str], ...] = (
    ("payroll", "Payroll", "payroll"),
    ("acme", "Revenue", "taxable-revenue"),
    ("invoice", "Revenue", "taxable-revenue"),
    ("doorway", "Rental income", "rental"),
    ("rent", "Rental income", "rental"),
    ("stripe", "Processing payout", "revenue"),
    ("customer", "Revenue", "taxable-revenue"),
    ("tax", "Tax payment", "tax-paid"),
    ("utility", "Utilities", "deductible"),
    ("software", "Software", "deductible"),
    ("travel", "Travel", "deductible"),
)


def suggest_category(counterparty: str, memo: str) -> tuple[str, str]:
    text = f"{counterparty} {memo}".lower()
    for keyword, category, tax_tag in _CATEGORY_RULES:
        if keyword in text:
            return category, tax_tag
    return "Uncategorized", "review"


def _serialize_account(a: BankAccount) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "account_type": a.account_type,
        "currency": a.currency,
        "balance_cents": a.balance_cents,
        "status": a.status,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _serialize_txn(t: BankTransaction) -> dict:
    return {
        "id": t.id,
        "account_id": t.account_id,
        "direction": t.direction,
        "txn_type": t.txn_type,
        "amount_cents": t.amount_cents,
        "fee_cents": t.fee_cents,
        "counterparty": t.counterparty,
        "memo": t.memo,
        "category": t.category,
        "tax_tag": t.tax_tag,
        "status": t.status,
        "transfer_id": t.transfer_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _get_account(db: Session, org_id: str, account_id: str) -> BankAccount:
    acct = (
        db.query(BankAccount)
        .filter(BankAccount.id == account_id, BankAccount.org_id == org_id)
        .first()
    )
    if acct is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return acct


def _post_txn(
    db: Session,
    *,
    org_id: str,
    account: BankAccount,
    direction: str,
    txn_type: str,
    amount_cents: int,
    counterparty: str = "",
    memo: str = "",
    status: str = "posted",
    transfer_id: str | None = None,
    idempotency_key: str | None = None,
) -> BankTransaction:
    if amount_cents <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")
    category, tax_tag = suggest_category(counterparty, memo)
    txn = BankTransaction(
        id=_uid(),
        org_id=org_id,
        account_id=account.id,
        direction=direction,
        txn_type=txn_type,
        amount_cents=amount_cents,
        fee_cents=FEE_CENTS,  # always 0 — enforced, not requested
        counterparty=counterparty,
        memo=memo,
        category=category,
        tax_tag=tax_tag,
        status=status,
        transfer_id=transfer_id,
        idempotency_key=idempotency_key,
    )
    db.add(txn)
    if status == "posted":
        if direction == "in":
            account.balance_cents += amount_cents
        else:
            account.balance_cents -= amount_cents
    return txn


# ── Schemas ────────────────────────────────────────────────

class OpenAccountBody(BaseModel):
    name: str = Field(default="Operating", max_length=128)
    account_type: str = Field(default="operating", pattern="^(operating|reserve|yield)$")
    currency: str = Field(default="USD", min_length=3, max_length=3)


class TransferBody(BaseModel):
    from_account_id: str
    to_account_id: str | None = None
    counterparty: str = Field(default="", max_length=255)
    amount_cents: int = Field(gt=0, le=MAX_CENTS)
    memo: str = Field(default="", max_length=500)
    idempotency_key: str | None = Field(default=None, max_length=128)


class CategorizeBody(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    tax_tag: str = Field(min_length=1, max_length=64)


class ProfileBody(BaseModel):
    legal_name: str = Field(default="", max_length=255)
    dba: str = Field(default="", max_length=255)
    entity_type: str = Field(default="", max_length=64)
    country: str = Field(default="US", min_length=2, max_length=2)
    industry: str = Field(default="", max_length=128)
    tax_id_last4: str = Field(default="", max_length=4)


# ── Overview ───────────────────────────────────────────────

@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org_id = user.org_id
    accounts = (
        db.query(BankAccount)
        .filter(BankAccount.org_id == org_id, BankAccount.status == "active")
        .all()
    )
    total = sum(a.balance_cents for a in accounts)
    since = _utcnow() - timedelta(days=30)
    posted = db.query(BankTransaction).filter(
        BankTransaction.org_id == org_id,
        BankTransaction.status == "posted",
        BankTransaction.created_at >= since,
    ).all()
    moved = sum(t.amount_cents for t in posted)
    fees = sum(t.fee_cents for t in posted)
    net = sum(t.amount_cents if t.direction == "in" else -t.amount_cents for t in posted)
    avg_daily_net = net / 30
    pending = (
        db.query(BankTransaction)
        .filter(BankTransaction.org_id == org_id, BankTransaction.status == "pending")
        .all()
    )
    recent = (
        db.query(BankTransaction)
        .filter(BankTransaction.org_id == org_id)
        .order_by(BankTransaction.created_at.desc())
        .limit(5)
        .all()
    )
    return {
        "total_balance_cents": total,
        "fees_paid_30d_cents": fees,  # always 0 — shown, not hidden
        "moved_30d_cents": moved,
        "projected_net_90d_cents": round(avg_daily_net * 90),
        "forecast_basis": "trailing-30d average daily net flow (estimate, not advice)",
        "pending_count": len(pending),
        "pending_cents": sum(t.amount_cents for t in pending),
        "accounts": [_serialize_account(a) for a in accounts],
        "recent": [_serialize_txn(t) for t in recent],
    }


# ── Accounts ───────────────────────────────────────────────

@router.get("/accounts")
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = (
        db.query(BankAccount)
        .filter(BankAccount.org_id == user.org_id)
        .order_by(BankAccount.created_at.asc())
        .all()
    )
    return {"accounts": [_serialize_account(a) for a in accounts]}


@router.post("/accounts", status_code=201)
def open_account(body: OpenAccountBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    acct = BankAccount(
        id=_uid(),
        org_id=user.org_id,
        owner_user_id=user.id,
        name=body.name.strip() or "Operating",
        account_type=body.account_type,
        currency=body.currency.upper(),
        balance_cents=0,
        status="active",
        partner_ref=f"sandbox-{uuid.uuid4().hex[:12]}",
    )
    db.add(acct)
    db.commit()
    db.refresh(acct)
    return _serialize_account(acct)


@router.get("/accounts/{account_id}")
def get_account(account_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _serialize_account(_get_account(db, user.org_id, account_id))


@router.get("/accounts/{account_id}/transactions")
def account_transactions(
    account_id: str,
    limit: int = Query(default=25, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    acct = _get_account(db, user.org_id, account_id)
    txns = (
        db.query(BankTransaction)
        .filter(BankTransaction.account_id == acct.id)
        .order_by(BankTransaction.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"account": _serialize_account(acct), "transactions": [_serialize_txn(t) for t in txns]}


# ── Transfers (0-fee, double-entry, idempotent) ────────────

@router.post("/transfers", status_code=201)
def create_transfer(body: TransferBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org_id = user.org_id
    if body.idempotency_key:
        existing = (
            db.query(BankTransfer)
            .filter(
                BankTransfer.org_id == org_id,
                BankTransfer.idempotency_key == body.idempotency_key,
            )
            .first()
        )
        if existing:
            return _serialize_transfer(db, existing)
    src = _get_account(db, org_id, body.from_account_id)
    if src.status != "active":
        raise HTTPException(status_code=422, detail="Source account is not active")
    dst = None
    if body.to_account_id:
        if body.to_account_id == src.id:
            raise HTTPException(status_code=422, detail="Source and destination must differ")
        dst = _get_account(db, org_id, body.to_account_id)
        if dst.status != "active":
            raise HTTPException(status_code=422, detail="Destination account is not active")
    elif not body.counterparty.strip():
        raise HTTPException(status_code=422, detail="External transfer needs a counterparty")
    if src.balance_cents < body.amount_cents:
        raise HTTPException(status_code=422, detail="Insufficient funds")
    transfer = BankTransfer(
        id=_uid(),
        org_id=org_id,
        from_account_id=src.id,
        to_account_id=dst.id if dst else None,
        amount_cents=body.amount_cents,
        fee_cents=FEE_CENTS,
        status="posted",
        counterparty=body.counterparty.strip() or (dst.name if dst else ""),
        memo=body.memo.strip(),
        idempotency_key=body.idempotency_key,
        created_by=user.id,
    )
    db.add(transfer)
    db.flush()
    _post_txn(
        db, org_id=org_id, account=src, direction="out",
        txn_type="transfer_out" if dst else "ach_out",
        amount_cents=body.amount_cents,
        counterparty=transfer.counterparty, memo=transfer.memo,
        transfer_id=transfer.id,
        idempotency_key=f"{body.idempotency_key}:out" if body.idempotency_key else None,
    )
    if dst:
        _post_txn(
            db, org_id=org_id, account=dst, direction="in",
            txn_type="transfer_in",
            amount_cents=body.amount_cents,
            counterparty=src.name, memo=transfer.memo,
            transfer_id=transfer.id,
            idempotency_key=f"{body.idempotency_key}:in" if body.idempotency_key else None,
        )
    db.commit()
    return _serialize_transfer(db, transfer)


def _serialize_transfer(db: Session, tr: BankTransfer) -> dict:
    txns = (
        db.query(BankTransaction)
        .filter(BankTransaction.transfer_id == tr.id)
        .order_by(BankTransaction.created_at.asc())
        .all()
    )
    return {
        "id": tr.id,
        "from_account_id": tr.from_account_id,
        "to_account_id": tr.to_account_id,
        "amount_cents": tr.amount_cents,
        "fee_cents": tr.fee_cents,
        "status": tr.status,
        "counterparty": tr.counterparty,
        "memo": tr.memo,
        "idempotency_key": tr.idempotency_key,
        "created_at": tr.created_at.isoformat() if tr.created_at else None,
        "transactions": [_serialize_txn(t) for t in txns],
    }


@router.get("/transfers")
def list_transfers(
    limit: int = Query(default=25, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transfers = (
        db.query(BankTransfer)
        .filter(BankTransfer.org_id == user.org_id)
        .order_by(BankTransfer.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"transfers": [_serialize_transfer(db, t) for t in transfers]}


# ── AI CFO: categorization + insights ──────────────────────

@router.post("/transactions/{txn_id}/categorize")
def categorize_txn(txn_id: str, body: CategorizeBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    txn = (
        db.query(BankTransaction)
        .filter(BankTransaction.id == txn_id, BankTransaction.org_id == user.org_id)
        .first()
    )
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    txn.category = body.category.strip()
    txn.tax_tag = body.tax_tag.strip()
    db.commit()
    db.refresh(txn)
    return _serialize_txn(txn)


@router.get("/insights")
def insights(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org_id = user.org_id
    accounts = (
        db.query(BankAccount)
        .filter(BankAccount.org_id == org_id, BankAccount.status == "active")
        .all()
    )
    total = sum(a.balance_cents for a in accounts)
    operating = next((a for a in accounts if a.account_type == "operating"), None)
    since = _utcnow() - timedelta(days=30)
    posted = db.query(BankTransaction).filter(
        BankTransaction.org_id == org_id,
        BankTransaction.status == "posted",
        BankTransaction.created_at >= since,
    ).all()
    outflows = [t for t in posted if t.direction == "out"]
    inflows = [t for t in posted if t.direction == "in"]
    avg_daily_out = (sum(t.amount_cents for t in outflows) / 30) if outflows else 0
    revenue_30d = sum(
        t.amount_cents for t in inflows
        if t.tax_tag in ("taxable-revenue", "revenue", "rental")
    )
    payroll_recent = [t for t in outflows if t.category == "Payroll"]
    last_payroll = max((t.amount_cents for t in payroll_recent), default=0)
    uncategorized = sum(1 for t in posted if t.category == "Uncategorized")
    cards: list[dict] = []
    if avg_daily_out > 0:
        runway = total / avg_daily_out
        cards.append({
            "id": "runway",
            "title": f"~{runway:.0f} days of runway at current spend",
            "body": (
                f"Balances total {total / 100:,.2f} against a 30-day average outflow of "
                f"{avg_daily_out / 100:,.2f}/day. Estimate from trailing flows — not advice."
            ),
            "severity": "info" if runway > 60 else "warn",
        })
    else:
        cards.append({
            "id": "runway",
            "title": "No outflows yet — runway is unbounded",
            "body": "Move money to start building a cash-flow picture.",
            "severity": "info",
        })
    if last_payroll and operating:
        covered = operating.balance_cents >= last_payroll
        cards.append({
            "id": "payroll",
            "title": ("Next payroll covered" if covered else "Payroll shortfall risk"),
            "body": (
                f"Last payroll was {last_payroll / 100:,.2f}; operating holds "
                f"{operating.balance_cents / 100:,.2f}."
            ),
            "severity": "info" if covered else "warn",
        })
    if revenue_30d:
        cards.append({
            "id": "tax",
            "title": f"Set aside ~{revenue_30d * 0.25 / 100:,.2f} for tax",
            "body": (
                f"25% flat-rate estimate on {revenue_30d / 100:,.2f} of 30-day revenue. "
                "Confirm with your CPA — rules vary by jurisdiction."
            ),
            "severity": "info",
        })
    idle = (operating.balance_cents - 2 * sum(t.amount_cents for t in outflows)) if operating and outflows else 0
    if idle > 5_000_00:
        cards.append({
            "id": "yield",
            "title": f"~{idle / 100:,.2f} looks idle",
            "body": (
                f"Above a 2-month outflow buffer. A yield pocket at ~4% APY would earn "
                f"~{idle * 0.04 / 12 / 100:,.2f}/mo (estimate)."
            ),
            "severity": "info",
        })
    if uncategorized:
        cards.append({
            "id": "review",
            "title": f"{uncategorized} transactions need review",
            "body": "Auto-categorization missed these — one click each to tag them for tax.",
            "severity": "warn",
        })
    return {"insights": cards, "disclaimer": "Rule-based estimates from your ledger. Not tax, legal or investment advice."}


# ── Onboarding / KYB ───────────────────────────────────────

def _serialize_profile(p: BusinessProfile) -> dict:
    return {
        "org_id": p.org_id,
        "legal_name": p.legal_name,
        "dba": p.dba,
        "entity_type": p.entity_type,
        "country": p.country,
        "industry": p.industry,
        "tax_id_last4": p.tax_id_last4,
        "kyb_status": p.kyb_status,
        "kyb_notes": p.kyb_notes,
        "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
        "decided_at": p.decided_at.isoformat() if p.decided_at else None,
    }


@router.get("/profile")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(BusinessProfile).filter(BusinessProfile.org_id == user.org_id).first()
    if profile is None:
        return {"profile": None, "kyb_status": "draft"}
    return {"profile": _serialize_profile(profile), "kyb_status": profile.kyb_status}


@router.put("/profile")
def upsert_profile(body: ProfileBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(BusinessProfile).filter(BusinessProfile.org_id == user.org_id).first()
    if profile is None:
        profile = BusinessProfile(id=_uid(), org_id=user.org_id)
        db.add(profile)
    if profile.kyb_status == "verified":
        raise HTTPException(status_code=422, detail="Verified profiles are locked — contact support to amend")
    profile.legal_name = body.legal_name.strip()
    profile.dba = body.dba.strip()
    profile.entity_type = body.entity_type.strip()
    profile.country = body.country.upper()
    profile.industry = body.industry.strip()
    profile.tax_id_last4 = body.tax_id_last4.strip()
    db.commit()
    db.refresh(profile)
    return _serialize_profile(profile)


@router.post("/profile/submit")
def submit_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(BusinessProfile).filter(BusinessProfile.org_id == user.org_id).first()
    if profile is None or not profile.legal_name or not profile.entity_type:
        raise HTTPException(status_code=422, detail="Complete legal name and entity type first")
    if profile.kyb_status == "verified":
        raise HTTPException(status_code=422, detail="Already verified")
    profile.kyb_status = "pending"
    profile.submitted_at = _utcnow()
    db.commit()
    db.refresh(profile)
    return _serialize_profile(profile)


@router.post("/profile/verify")
def verify_profile(
    approved: bool = True,
    notes: str = "",
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    # Simulates the partner bank's KYB decision. Restricted to admins,
    # mirroring a back-office approval with a full audit trail.
    profile = db.query(BusinessProfile).filter(BusinessProfile.org_id == user.org_id).first()
    if profile is None or profile.kyb_status != "pending":
        raise HTTPException(status_code=422, detail="No pending KYB submission")
    profile.kyb_status = "verified" if approved else "rejected"
    profile.kyb_notes = notes[:500]
    profile.decided_at = _utcnow()
    db.commit()
    db.refresh(profile)
    return _serialize_profile(profile)


# ── Demo seed (matches the landing-page story) ─────────────

@router.post("/seed", status_code=201)
def seed_demo(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    org_id = user.org_id
    existing = db.query(BankAccount).filter(BankAccount.org_id == org_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Banking already initialized for this org")
    operating = BankAccount(
        id=_uid(), org_id=org_id, owner_user_id=user.id,
        name="Operating", account_type="operating", currency="USD",
        balance_cents=0, status="active", partner_ref=f"sandbox-{uuid.uuid4().hex[:12]}",
    )
    db.add(operating)
    db.flush()
    seed_txns = [
        ("in", "opening_balance", 20_249_000, "Quantive Partner Bank", "Initial funding", "posted"),
        ("in", "invoice", 1_240_000, "Acme Corp", "Invoice #1042", "posted"),
        ("out", "payroll", 3_820_000, "Payroll", "14 employees", "posted"),
        ("in", "payout", 485_000, "Open Doorway", "Rental payout", "posted"),
        ("in", "invoice", 932_000, "Stripe Payout", "Weekly payout", "pending"),
        ("in", "invoice", 275_000, "Customer Payment", "Invoice #1041", "posted"),
    ]
    for i, (direction, txn_type, cents, counterparty, memo, status) in enumerate(seed_txns):
        _post_txn(
            db, org_id=org_id, account=operating, direction=direction,
            txn_type=txn_type, amount_cents=cents, counterparty=counterparty,
            memo=memo, status=status, idempotency_key=f"seed-{i}",
        )
    db.commit()
    db.refresh(operating)
    return _serialize_account(operating)
