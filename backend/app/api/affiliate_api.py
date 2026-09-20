"""Affiliate program API — referral tracking and commission management for Qubo Tax.

Flow:
1. User joins affiliate program → gets unique referral code
2. Affiliate shares referral link: /qubo/workspace?ref=CODE
3. New user clicks link → click tracked, cookie set
4. New user registers → Referral record created, status=pending
5. Referred user subscribes to Qubo → Commission record created
6. Admin approves/pays commissions manually

Commission: recurring % of referred user's Qubo subscription payment."""
from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.affiliate import (
    AffiliateProgram,
    Commission,
    Payout,
    Referral,
    ReferralClick,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/affiliate", tags=["affiliate"])

REFERRAL_COOKIE = "qubo_ref"
REFERRAL_COOKIE_DAYS = 30


def _uid() -> str:
    import uuid
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _generate_code(length: int = 8) -> str:
    """Generate a unique referral code like QUBO-a3F7k9."""
    alphabet = string.ascii_uppercase + string.digits
    return "QUBO-" + "".join(secrets.choice(alphabet) for _ in range(length))


def _serialize_affiliate(a: AffiliateProgram) -> dict:
    return {
        "id": a.id,
        "referral_code": a.referral_code,
        "commission_rate": a.commission_rate,
        "is_active": a.is_active,
        "payout_email": a.payout_email,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _serialize_referral(r: Referral) -> dict:
    return {
        "id": r.id,
        "referred_user_id": r.referred_user_id,
        "referral_code": r.referral_code,
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "registered_at": r.registered_at.isoformat() if r.registered_at else None,
        "converted_at": r.converted_at.isoformat() if r.converted_at else None,
    }


def _serialize_commission(c: Commission) -> dict:
    return {
        "id": c.id,
        "referred_user_id": c.referred_user_id,
        "billing_period": c.billing_period,
        "subscription_amount_cents": c.subscription_amount_cents,
        "commission_rate": c.commission_rate,
        "commission_amount_cents": c.commission_amount_cents,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "paid_at": c.paid_at.isoformat() if c.paid_at else None,
    }


def _serialize_payout(p: Payout) -> dict:
    return {
        "id": p.id,
        "commission_ids": p.commission_ids,
        "total_amount_cents": p.total_amount_cents,
        "method": p.method,
        "status": p.status,
        "admin_notes": p.admin_notes,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "completed_at": p.completed_at.isoformat() if p.completed_at else None,
    }


# ── Affiliate Registration ───────────────────────────────────────────

class JoinBody(BaseModel):
    payout_email: str = Field(default="")
    commission_rate: float = Field(default=0.20, ge=0.05, le=0.50)


@router.post("/join")
def join_affiliate_program(
    body: JoinBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Join the Qubo Tax affiliate program and get a referral code."""
    existing = db.query(AffiliateProgram).filter(
        AffiliateProgram.user_id == user.id,
        AffiliateProgram.is_active == True,
    ).first()
    if existing:
        return _serialize_affiliate(existing)

    code = _generate_code()
    while db.query(AffiliateProgram).filter(AffiliateProgram.referral_code == code).first():
        code = _generate_code()

    affiliate = AffiliateProgram(
        id=_uid(),
        user_id=user.id,
        org_id=user.org_id,
        referral_code=code,
        commission_rate=body.commission_rate,
        payout_email=body.payout_email,
    )
    db.add(affiliate)
    db.commit()
    db.refresh(affiliate)
    return _serialize_affiliate(affiliate)


@router.get("/me")
def get_my_affiliate(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's affiliate account."""
    affiliate = db.query(AffiliateProgram).filter(
        AffiliateProgram.user_id == user.id,
        AffiliateProgram.is_active == True,
    ).first()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Not enrolled in affiliate program")
    return _serialize_affiliate(affiliate)


# ── Referral Tracking ────────────────────────────────────────────────

@router.get("/track/{code}")
def track_referral_click(
    code: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Track a referral link click and set a tracking cookie.

    Called when someone visits /qubo/workspace?ref=CODE."""
    affiliate = db.query(AffiliateProgram).filter(
        AffiliateProgram.referral_code == code,
        AffiliateProgram.is_active == True,
    ).first()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Invalid referral code")

    # Record the click
    click = ReferralClick(
        id=_uid(),
        referral_code=code,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        landing_page=str(request.url),
        referrer=request.headers.get("referer", "")[:512],
    )
    db.add(click)
    db.commit()

    # Set tracking cookie (30 days)
    response.set_cookie(
        key=REFERRAL_COOKIE,
        value=code,
        max_age=REFERRAL_COOKIE_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=True,
    )

    return {"status": "tracked", "code": code}


@router.post("/register")
def register_referral(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Called after a new user registers — checks for referral cookie and
    creates a Referral record linking the new user to the affiliate."""
    # Check for referral cookie
    code = request.cookies.get(REFERRAL_COOKIE)
    if not code:
        return {"referral": False}

    affiliate = db.query(AffiliateProgram).filter(
        AffiliateProgram.referral_code == code,
        AffiliateProgram.is_active == True,
    ).first()
    if not affiliate:
        return {"referral": False}

    # Don't refer yourself
    if affiliate.user_id == user.id:
        return {"referral": False}

    # Check if already referred
    existing = db.query(Referral).filter(
        Referral.referred_user_id == user.id,
    ).first()
    if existing:
        return {"referral": False, "already_referred": True}

    referral = Referral(
        id=_uid(),
        affiliate_id=affiliate.id,
        referred_user_id=user.id,
        referred_org_id=user.org_id,
        referral_code=code,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        status="registered",
        registered_at=_utcnow(),
    )
    db.add(referral)
    db.commit()

    return {"referral": True, "affiliate_id": affiliate.id}


# ── Commission Tracking ──────────────────────────────────────────────

class CommissionCreateBody(BaseModel):
    referral_id: str
    referred_user_id: str
    billing_period: str = Field(description="e.g. 2026-01")
    subscription_amount_cents: int = Field(ge=1)


@router.post("/commissions")
def create_commission(
    body: CommissionCreateBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a commission for a referred user's payment.

    In production this would be called by a webhook from the payment processor.
    For manual tracking, an admin can create it directly."""
    referral = db.query(Referral).filter(Referral.id == body.referral_id).first()
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")

    affiliate = db.query(AffiliateProgram).filter(AffiliateProgram.id == referral.affiliate_id).first()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Affiliate not found")

    commission_amount = int(body.subscription_amount_cents * affiliate.commission_rate)

    commission = Commission(
        id=_uid(),
        affiliate_id=affiliate.id,
        referral_id=referral.id,
        referred_user_id=body.referred_user_id,
        billing_period=body.billing_period,
        subscription_amount_cents=body.subscription_amount_cents,
        commission_rate=affiliate.commission_rate,
        commission_amount_cents=commission_amount,
        status="pending",
    )
    db.add(commission)

    # Update referral status
    referral.status = "converted"
    referral.converted_at = _utcnow()
    db.commit()
    db.refresh(commission)

    return _serialize_commission(commission)


# ── Dashboard ────────────────────────────────────────────────────────

@router.get("/dashboard")
def affiliate_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get affiliate dashboard stats: referrals, commissions, earnings."""
    affiliate = db.query(AffiliateProgram).filter(
        AffiliateProgram.user_id == user.id,
        AffiliateProgram.is_active == True,
    ).first()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Not enrolled in affiliate program")

    referrals = db.query(Referral).filter(Referral.affiliate_id == affiliate.id).all()
    commissions = db.query(Commission).filter(Commission.affiliate_id == affiliate.id).all()

    total_clicks = db.query(ReferralClick).filter(ReferralClick.referral_code == affiliate.referral_code).count()

    by_status = {"pending": 0, "registered": 0, "converted": 0, "churned": 0}
    for r in referrals:
        by_status[r.status] = by_status.get(r.status, 0) + 1

    total_commission_cents = sum(c.commission_amount_cents for c in commissions)
    paid_commission_cents = sum(c.commission_amount_cents for c in commissions if c.status == "paid")
    pending_commission_cents = sum(c.commission_amount_cents for c in commissions if c.status == "pending")

    return {
        "affiliate": _serialize_affiliate(affiliate),
        "stats": {
            "total_clicks": total_clicks,
            "total_referrals": len(referrals),
            "referrals_by_status": by_status,
            "total_commissions": len(commissions),
            "total_commission_cents": total_commission_cents,
            "paid_commission_cents": paid_commission_cents,
            "pending_commission_cents": pending_commission_cents,
        },
        "referrals": [_serialize_referral(r) for r in referrals[:50]],
        "commissions": [_serialize_commission(c) for c in commissions[:50]],
    }


@router.get("/referrals")
def list_referrals(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all referrals for the affiliate."""
    affiliate = db.query(AffiliateProgram).filter(
        AffiliateProgram.user_id == user.id,
        AffiliateProgram.is_active == True,
    ).first()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Not enrolled in affiliate program")

    referrals = (
        db.query(Referral)
        .filter(Referral.affiliate_id == affiliate.id)
        .order_by(Referral.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"referrals": [_serialize_referral(r) for r in referrals]}


@router.get("/commissions")
def list_commissions(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all commissions for the affiliate."""
    affiliate = db.query(AffiliateProgram).filter(
        AffiliateProgram.user_id == user.id,
        AffiliateProgram.is_active == True,
    ).first()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Not enrolled in affiliate program")

    q = db.query(Commission).filter(Commission.affiliate_id == affiliate.id)
    if status:
        q = q.filter(Commission.status == status)
    commissions = q.order_by(Commission.created_at.desc()).limit(limit).all()
    return {"commissions": [_serialize_commission(c) for c in commissions]}


# ── Admin: Commission Approval & Payouts ─────────────────────────────

class ApproveCommissionBody(BaseModel):
    status: str = Field(pattern="^(approved|cancelled)$")


@router.post("/admin/commissions/{commission_id}/approve")
def approve_commission(
    commission_id: str,
    body: ApproveCommissionBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin: approve or cancel a pending commission."""
    # Simple admin check — in production, use RBAC
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    commission = db.query(Commission).filter(Commission.id == commission_id).first()
    if not commission:
        raise HTTPException(status_code=404, detail="Commission not found")

    commission.status = body.status
    if body.status == "approved":
        commission.approved_at = _utcnow()
    db.commit()
    db.refresh(commission)
    return _serialize_commission(commission)


class CreatePayoutBody(BaseModel):
    affiliate_id: str
    commission_ids: list[str]
    method: str = Field(default="manual")
    admin_notes: str = Field(default="")


@router.post("/admin/payouts")
def create_payout(
    body: CreatePayoutBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin: create a payout record for approved commissions."""
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    commissions = db.query(Commission).filter(
        Commission.id.in_(body.commission_ids),
        Commission.affiliate_id == body.affiliate_id,
        Commission.status == "approved",
    ).all()

    if not commissions:
        raise HTTPException(status_code=400, detail="No approved commissions found")

    total = sum(c.commission_amount_cents for c in commissions)

    payout = Payout(
        id=_uid(),
        affiliate_id=body.affiliate_id,
        commission_ids=body.commission_ids,
        total_amount_cents=total,
        method=body.method,
        status="pending",
        admin_notes=body.admin_notes,
    )
    db.add(payout)

    for c in commissions:
        c.status = "paid"
        c.paid_at = _utcnow()
        c.payout_id = payout.id

    db.commit()
    db.refresh(payout)
    return _serialize_payout(payout)


@router.get("/admin/payouts")
def list_payouts(
    affiliate_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin: list all payouts."""
    if user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    q = db.query(Payout)
    if affiliate_id:
        q = q.filter(Payout.affiliate_id == affiliate_id)
    payouts = q.order_by(Payout.created_at.desc()).limit(limit).all()
    return {"payouts": [_serialize_payout(p) for p in payouts]}


# ── Referral Link Helper ─────────────────────────────────────────────

@router.get("/link")
def get_referral_link(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the affiliate's referral link for sharing."""
    affiliate = db.query(AffiliateProgram).filter(
        AffiliateProgram.user_id == user.id,
        AffiliateProgram.is_active == True,
    ).first()
    if not affiliate:
        raise HTTPException(status_code=404, detail="Not enrolled in affiliate program")

    return {
        "referral_code": affiliate.referral_code,
        "referral_link": f"/qubo/workspace?ref={affiliate.referral_code}",
        "share_text": f"Start saving on taxes with Qubo Tax — use my referral link: /qubo/workspace?ref={affiliate.referral_code}",
    }
