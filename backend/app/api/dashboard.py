"""
Dashboard API — Summary, tasks, and metrics for the main dashboard.
==================================================================

Provides the data the React frontend needs to replace hardcoded values
with live database queries.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    DebtInstrument,
    JobStatus,
    OptimizationJob,
    Portfolio,
    Strategy,
    User,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ── Response Schemas ─────────────────────────────────────────────────

class RiskScoreSummary(BaseModel):
    refinancing_risk: float = 0.0
    currency_risk: float = 0.0
    interest_rate_risk: float = 0.0
    overall: float = 0.0


class MaturityBucket(BaseModel):
    year: int
    count: int
    total_principal: float


class DashboardSummary(BaseModel):
    total_debt: float = 0.0
    instrument_count: int = 0
    currency_count: int = 0
    portfolio_count: int = 0
    avg_maturity_years: float = 0.0
    weighted_coupon_pct: float = 0.0
    active_optimizations: int = 0
    completed_optimizations: int = 0
    risk_scores: RiskScoreSummary = RiskScoreSummary()
    maturity_distribution: list[MaturityBucket] = []
    top_currencies: list[dict] = []
    recent_activity: list[dict] = []


class DashboardTask(BaseModel):
    id: str
    type: str  # "optimization", "maturity_alert", "portfolio"
    title: str
    meta: str
    status: str
    priority: str  # "high", "medium", "low"
    link: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────

def _compute_avg_maturity(instruments: list) -> float:
    """Compute weighted average years to maturity."""
    if not instruments:
        return 0.0
    now = datetime.now(timezone.utc)
    total_principal = 0.0
    weighted_years = 0.0
    for inst in instruments:
        principal = float(inst.principal_outstanding)
        total_principal += principal
        try:
            mat_date = datetime.strptime(inst.maturity_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            years_left = max(0, (mat_date - now).days / 365.25)
            weighted_years += years_left * principal
        except (ValueError, AttributeError):
            continue
    return round(weighted_years / total_principal, 1) if total_principal > 0 else 0.0


def _compute_weighted_coupon(instruments: list) -> float:
    """Compute principal-weighted average coupon rate as percentage."""
    if not instruments:
        return 0.0
    total_principal = 0.0
    weighted_coupon = 0.0
    for inst in instruments:
        principal = float(inst.principal_outstanding)
        coupon = float(inst.coupon_rate)
        total_principal += principal
        weighted_coupon += coupon * principal
    return round((weighted_coupon / total_principal) * 100, 2) if total_principal > 0 else 0.0


def _compute_maturity_distribution(instruments: list) -> list[MaturityBucket]:
    """Group instruments by maturity year and sum principal."""
    buckets: dict[int, dict] = {}
    for inst in instruments:
        try:
            year = int(inst.maturity_date.split("-")[0])
        except (ValueError, IndexError):
            continue
        if year not in buckets:
            buckets[year] = {"count": 0, "total_principal": 0.0}
        buckets[year]["count"] += 1
        buckets[year]["total_principal"] += float(inst.principal_outstanding)

    result = [
        MaturityBucket(
            year=year,
            count=data["count"],
            total_principal=round(data["total_principal"], 2),
        )
        for year, data in sorted(buckets.items())
    ]
    return result


def _compute_top_currencies(instruments: list, limit: int = 5) -> list[dict]:
    """Return top currencies by total principal outstanding."""
    ccy_totals: dict[str, float] = {}
    for inst in instruments:
        ccy = inst.currency
        ccy_totals[ccy] = ccy_totals.get(ccy, 0) + float(inst.principal_outstanding)
    sorted_ccys = sorted(ccy_totals.items(), key=lambda x: x[1], reverse=True)[:limit]
    total = sum(v for _, v in sorted_ccys) if sorted_ccys else 1
    return [
        {
            "currency": ccy,
            "total_principal": round(principal, 2),
            "percentage": round((principal / total) * 100, 1),
        }
        for ccy, principal in sorted_ccys
    ]


def _compute_risk_scores(instruments: list) -> RiskScoreSummary:
    """
    Compute simplified risk scores (0-100) based on portfolio composition.

    These are heuristic scores derived from observable portfolio characteristics:
    - Refinancing risk: higher when many instruments mature soon
    - Currency risk: higher when foreign currency exposure is large
    - Interest rate risk: higher when floating-rate or short-maturity exposure is high
    """
    if not instruments:
        return RiskScoreSummary()

    now = datetime.now(timezone.utc)
    total_principal = sum(float(i.principal_outstanding) for i in instruments)
    if total_principal == 0:
        return RiskScoreSummary()

    # Refinancing risk: fraction maturing within 2 years, scaled 0-100
    short_term_principal = 0.0
    for inst in instruments:
        try:
            mat = datetime.strptime(inst.maturity_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            years_left = (mat - now).days / 365.25
            if years_left <= 2:
                short_term_principal += float(inst.principal_outstanding)
        except (ValueError, AttributeError):
            continue
    refinancing_risk = min(100, round((short_term_principal / total_principal) * 100, 1))

    # Currency risk: fraction in non-USD currencies
    usd_principal = sum(
        float(i.principal_outstanding) for i in instruments if i.currency == "USD"
    )
    foreign_principal = total_principal - usd_principal
    currency_risk = min(100, round((foreign_principal / total_principal) * 100, 1))

    # Interest rate risk: fraction with short maturity (< 3 years) or floating rate
    rate_sensitive = 0.0
    for inst in instruments:
        try:
            mat = datetime.strptime(inst.maturity_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            years_left = (mat - now).days / 365.25
            if years_left <= 3 or (inst.instrument_type and "floating" in str(inst.instrument_type.value).lower()):
                rate_sensitive += float(inst.principal_outstanding)
        except (ValueError, AttributeError):
            continue
    interest_rate_risk = min(100, round((rate_sensitive / total_principal) * 100, 1))

    overall = round(
        (refinancing_risk * 0.4 + currency_risk * 0.3 + interest_rate_risk * 0.3), 1
    )

    return RiskScoreSummary(
        refinancing_risk=refinancing_risk,
        currency_risk=currency_risk,
        interest_rate_risk=interest_rate_risk,
        overall=overall,
    )


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/summary")
def dashboard_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Aggregated dashboard data for the main overview page.

    Returns live data from the database: portfolio metrics, risk scores,
    maturity distribution, currency breakdown, and optimization counts.
    """
    # Fetch all instruments for this organization's portfolios
    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    portfolio_ids = [p.id for p in portfolios]

    instruments = (
        db.query(DebtInstrument)
        .filter(DebtInstrument.portfolio_id.in_(portfolio_ids))
        .all()
        if portfolio_ids
        else []
    )

    # Portfolio metrics
    total_debt = sum(float(i.principal_outstanding) for i in instruments)
    currencies = {i.currency for i in instruments}

    # Optimization counts
    active_count = (
        db.query(func.count(OptimizationJob.id))
        .filter(
            OptimizationJob.org_id == user.org_id,
            OptimizationJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
        )
        .scalar()
        or 0
    )
    completed_count = (
        db.query(func.count(OptimizationJob.id))
        .filter(
            OptimizationJob.org_id == user.org_id,
            OptimizationJob.status == JobStatus.COMPLETED,
        )
        .scalar()
        or 0
    )

    return {
        "total_debt": round(total_debt, 2),
        "instrument_count": len(instruments),
        "currency_count": len(currencies),
        "portfolio_count": len(portfolios),
        "avg_maturity_years": _compute_avg_maturity(instruments),
        "weighted_coupon_pct": _compute_weighted_coupon(instruments),
        "active_optimizations": active_count,
        "completed_optimizations": completed_count,
        "risk_scores": _compute_risk_scores(instruments).model_dump(),
        "maturity_distribution": [b.model_dump() for b in _compute_maturity_distribution(instruments)],
        "top_currencies": _compute_top_currencies(instruments),
    }


@router.get("/tasks")
def dashboard_tasks(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[dict]:
    """
    Priority tasks for the dashboard: active optimizations, upcoming maturities,
    and portfolio alerts.
    """
    tasks: list[dict] = []
    now = datetime.now(timezone.utc)

    # Active optimizations (high priority)
    active_jobs = (
        db.query(OptimizationJob)
        .filter(
            OptimizationJob.org_id == user.org_id,
            OptimizationJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
        )
        .order_by(OptimizationJob.created_at.desc())
        .limit(5)
        .all()
    )
    for job in active_jobs:
        progress_pct = round((job.progress or 0) * 100)
        tasks.append({
            "id": job.id,
            "type": "optimization",
            "title": f"Optimization: {job.name}",
            "meta": f"Running · {progress_pct}% complete",
            "status": "running",
            "priority": "high",
            "link": f"/optimizations/{job.id}",
        })

    # Upcoming maturities (medium priority) — instruments maturing within 90 days
    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    portfolio_ids = [p.id for p in portfolios]
    if portfolio_ids:
        instruments = (
            db.query(DebtInstrument)
            .filter(DebtInstrument.portfolio_id.in_(portfolio_ids))
            .all()
        )
        from datetime import timedelta
        cutoff = now + timedelta(days=90)
        upcoming = []
        for inst in instruments:
            try:
                mat = datetime.strptime(inst.maturity_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if now < mat <= cutoff:
                    upcoming.append(inst)
            except (ValueError, AttributeError):
                continue
        upcoming.sort(key=lambda i: i.maturity_date)
        for inst in upcoming[:5]:
            days_left = (datetime.strptime(inst.maturity_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) - now).days
            tasks.append({
                "id": inst.id,
                "type": "maturity_alert",
                "title": f"{inst.name} matures",
                "meta": f"{inst.currency} {inst.principal_outstanding:,.0f} · {days_left} days",
                "status": "upcoming",
                "priority": "medium",
                "link": f"/portfolios/{inst.portfolio_id}",
            })

    # Recent completed optimizations (low priority)
    recent_completed = (
        db.query(OptimizationJob)
        .filter(
            OptimizationJob.org_id == user.org_id,
            OptimizationJob.status == JobStatus.COMPLETED,
        )
        .order_by(OptimizationJob.completed_at.desc())
        .limit(3)
        .all()
    )
    for job in recent_completed:
        tasks.append({
            "id": job.id,
            "type": "optimization",
            "title": f"Review: {job.name}",
            "meta": f"Completed · View results",
            "status": "completed",
            "priority": "low",
            "link": f"/optimizations/{job.id}",
        })

    return tasks[:limit]
