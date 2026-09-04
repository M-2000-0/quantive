"""Management dashboards API — revenue, MRR, customers, churn, pipeline."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.management import Deal, EmailCampaign
from app.security import get_current_user

router = APIRouter(prefix="/api/management", tags=["management"])


# ── Revenue Dashboard ─────────────────────────────────────────────


@router.get("/revenue")
def get_revenue_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Revenue metrics — ARR, growth, by stage."""
    deals = db.query(Deal).filter(Deal.org_id == user.org_id).all()

    total_revenue = sum(d.value for d in deals if d.stage == "closed_won")
    pipeline_value = sum(d.value * (d.probability / 100) for d in deals if d.stage not in ("closed_won", "closed_lost"))
    won_count = sum(1 for d in deals if d.stage == "closed_won")
    lost_count = sum(1 for d in deals if d.stage == "closed_lost")
    win_rate = (won_count / (won_count + lost_count) * 100) if (won_count + lost_count) > 0 else 0

    by_stage = {}
    for d in deals:
        by_stage.setdefault(d.stage, {"count": 0, "value": 0})
        by_stage[d.stage]["count"] += 1
        by_stage[d.stage]["value"] += d.value

    return {
        "total_revenue": round(total_revenue, 2),
        "pipeline_value": round(pipeline_value, 2),
        "annual_recurring": round(total_revenue, 2),
        "win_rate": round(win_rate, 1),
        "total_deals": len(deals),
        "won_deals": won_count,
        "lost_deals": lost_count,
        "by_stage": by_stage,
    }


# ── MRR Dashboard ─────────────────────────────────────────────────


@router.get("/mrr")
def get_mrr_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Monthly Recurring Revenue metrics."""
    deals = db.query(Deal).filter(
        Deal.org_id == user.org_id,
        Deal.stage == "closed_won",
    ).all()

    mrr = sum(d.value / 12 for d in deals if d.value > 0)
    arr = mrr * 12

    return {
        "mrr": round(mrr, 2),
        "arr": round(arr, 2),
        "subscription_count": len(deals),
        "avg_revenue_per_deal": round(sum(d.value for d in deals) / len(deals), 2) if deals else 0,
    }


# ── Customer Dashboard ────────────────────────────────────────────


@router.get("/customers")
def get_customer_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Customer metrics and health."""
    from app.models import User as UserModel

    total_users = db.query(UserModel).filter(UserModel.org_id == user.org_id).count()
    active_users = db.query(UserModel).filter(UserModel.org_id == user.org_id, UserModel.is_active == True).count()

    deals = db.query(Deal).filter(Deal.org_id == user.org_id).all()
    companies = set(d.company for d in deals if d.company)

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "unique_companies": len(companies),
        "companies": list(companies)[:20],
    }


# ── Churn Dashboard ───────────────────────────────────────────────


@router.get("/churn")
def get_churn_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Churn metrics and at-risk identification."""
    deals = db.query(Deal).filter(Deal.org_id == user.org_id).all()

    total = len(deals)
    lost = [d for d in deals if d.stage == "closed_lost"]
    at_risk = [d for d in deals if d.stage in ("lead", "qualified") and d.probability < 30]

    churn_rate = (len(lost) / total * 100) if total > 0 else 0
    lost_value = sum(d.value for d in lost)

    return {
        "churn_rate": round(churn_rate, 1),
        "total_deals": total,
        "lost_deals": len(lost),
        "lost_value": round(lost_value, 2),
        "at_risk_count": len(at_risk),
        "at_risk_deals": [{"id": d.id, "name": d.name, "company": d.company, "value": d.value, "probability": d.probability} for d in at_risk[:10]],
    }


# ── Sales Pipeline ────────────────────────────────────────────────


class DealCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    company: str = ""
    contact_email: str = ""
    value: float = 0
    stage: str = "lead"
    probability: int = 10
    expected_close_date: Optional[str] = None
    notes: str = ""


class DealUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    value: Optional[float] = None
    stage: Optional[str] = None
    probability: Optional[int] = None
    expected_close_date: Optional[str] = None
    notes: Optional[str] = None


class DealResponse(BaseModel):
    id: str
    name: str
    company: str
    value: float
    currency: str
    stage: str
    probability: int
    expected_close_date: Optional[str]
    owner_id: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("/pipeline", response_model=list[DealResponse])
def list_deals(
    stage: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List deals in the sales pipeline."""
    q = db.query(Deal).filter(Deal.org_id == user.org_id)
    if stage:
        q = q.filter(Deal.stage == stage)
    deals = q.order_by(desc(Deal.created_at)).limit(limit).all()
    return [DealResponse.model_validate(d).model_dump(mode="json") for d in deals]


@router.post("/pipeline", response_model=DealResponse, status_code=201)
def create_deal(data: DealCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new deal."""
    deal = Deal(
        org_id=user.org_id,
        name=data.name,
        company=data.company,
        contact_email=data.contact_email,
        value=data.value,
        stage=data.stage,
        owner_id=user.id,
        probability=data.probability,
        expected_close_date=data.expected_close_date,
        notes=data.notes,
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return DealResponse.model_validate(deal).model_dump(mode="json")


@router.put("/pipeline/{deal_id}", response_model=DealResponse)
def update_deal(deal_id: str, data: DealUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update a deal."""
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.org_id == user.org_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(deal, field, value)
    db.commit()
    db.refresh(deal)
    return DealResponse.model_validate(deal).model_dump(mode="json")


@router.delete("/pipeline/{deal_id}", status_code=204)
def delete_deal(deal_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a deal."""
    deal = db.query(Deal).filter(Deal.id == deal_id, Deal.org_id == user.org_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    db.delete(deal)
    db.commit()


@router.get("/pipeline/summary")
def pipeline_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Pipeline summary by stage with weighted values."""
    deals = db.query(Deal).filter(Deal.org_id == user.org_id).all()
    stages = {}
    for d in deals:
        stages.setdefault(d.stage, {"count": 0, "total_value": 0, "weighted_value": 0})
        stages[d.stage]["count"] += 1
        stages[d.stage]["total_value"] += d.value
        stages[d.stage]["weighted_value"] += d.value * (d.probability / 100)

    return {
        "total_pipeline": sum(d.value for d in deals if d.stage not in ("closed_won", "closed_lost")),
        "weighted_pipeline": sum(d.value * (d.probability / 100) for d in deals if d.stage not in ("closed_won", "closed_lost")),
        "stages": stages,
    }


# ── Email Campaigns ───────────────────────────────────────────────


class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)


@router.get("/campaigns")
def list_campaigns(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List email campaigns."""
    campaigns = db.query(EmailCampaign).filter(
        EmailCampaign.org_id == user.org_id
    ).order_by(desc(EmailCampaign.created_at)).limit(50).all()
    return [{"id": c.id, "name": c.name, "subject": c.subject, "status": c.status,
             "sent_count": c.sent_count, "open_count": c.open_count, "click_count": c.click_count,
             "created_at": c.created_at.isoformat() if c.created_at else ""} for c in campaigns]


@router.post("/campaigns", status_code=201)
def create_campaign(data: CampaignCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create an email campaign."""
    campaign = EmailCampaign(org_id=user.org_id, name=data.name, subject=data.subject, body=data.body)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return {"id": campaign.id, "name": campaign.name, "status": campaign.status}


# ── User Activity ─────────────────────────────────────────────────


@router.get("/activity")
def get_user_activity(
    hours: int = Query(24, ge=1, le=168),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get user activity metrics."""
    from datetime import datetime, timedelta, timezone
    from app.models.social import ActivityLog

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    total = db.query(ActivityLog).filter(
        ActivityLog.org_id == user.org_id,
        ActivityLog.created_at >= cutoff,
    ).count()

    return {
        "period_hours": hours,
        "total_events": total,
        "active_users": db.query(ActivityLog.user_id).filter(
            ActivityLog.org_id == user.org_id,
            ActivityLog.created_at >= cutoff,
        ).distinct().count(),
    }
