"""
Daily Briefing API — Proactive alerts and action items.
=====================================================

Aggregates signals from:
- Portfolio risk changes
- Upcoming maturities
- Market condition shifts
- Optimization results
- Watchlist alerts
- Early warning triggers

Returns a prioritized briefing with one-click action items.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    DebtInstrument,
    Notification,
    OptimizationJob,
    Portfolio,
    User,
    Watchlist,
    WatchlistItem,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/briefing", tags=["daily-briefing"])


def _get_upcoming_maturities(user: User, db: Session, days: int = 90) -> list[dict]:
    """Find instruments maturing within the next N days."""
    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    portfolio_ids = [p.id for p in portfolios]

    if not portfolio_ids:
        return []

    cutoff = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id.in_(portfolio_ids),
        DebtInstrument.maturity_date > today,
        DebtInstrument.maturity_date <= cutoff,
    ).order_by(DebtInstrument.maturity_date.asc()).all()

    return [
        {
            "id": inst.id,
            "name": inst.name,
            "currency": inst.currency,
            "principal": float(inst.principal_outstanding),
            "coupon_rate": float(inst.coupon_rate),
            "maturity_date": inst.maturity_date,
            "days_until_maturity": (
                (datetime.strptime(inst.maturity_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) - datetime.now(timezone.utc))
            ).days,
            "portfolio_id": inst.portfolio_id,
            "urgency": "critical" if (
                (datetime.strptime(inst.maturity_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) - datetime.now(timezone.utc))
            ).days <= 30 else "high" if (
                (datetime.strptime(inst.maturity_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) - datetime.now(timezone.utc))
            ).days <= 60 else "medium",
        }
        for inst in instruments
    ]


def _get_optimization_insights(user: User, db: Session) -> list[dict]:
    """Get insights from recent and running optimizations."""
    insights = []

    # Running optimizations
    running = db.query(OptimizationJob).filter(
        OptimizationJob.org_id == user.org_id,
        OptimizationJob.status.in_(["queued", "running", "scenario_generation", "solving", "benchmarking", "stress_testing"]),
    ).all()

    for job in running:
        insights.append({
            "type": "optimization_running",
            "title": f"Optimization in progress: {job.name}",
            "detail": f"Currently in {job.status.replace('_', ' ')} phase ({job.progress:.0%} complete)",
            "action_label": "View Progress",
            "action_url": f"/optimizations/{job.id}",
            "priority": "medium",
            "icon": "optimization",
        })

    # Recently completed
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    completed = db.query(OptimizationJob).filter(
        OptimizationJob.org_id == user.org_id,
        OptimizationJob.status == "completed",
        OptimizationJob.completed_at >= recent_cutoff,
    ).order_by(OptimizationJob.completed_at.desc()).limit(3).all()

    for job in completed:
        portfolio = db.query(Portfolio).filter(Portfolio.id == job.portfolio_id).first()
        portfolio_name = portfolio.name if portfolio else "Unknown"

        insights.append({
            "type": "optimization_completed",
            "title": f"Optimization completed: {job.name}",
            "detail": f"Portfolio '{portfolio_name}' — review results and recommended strategy",
            "action_label": "View Results",
            "action_url": f"/optimizations/{job.id}",
            "priority": "high",
            "icon": "",
        })

    # No optimizations yet
    total = db.query(OptimizationJob).filter(
        OptimizationJob.org_id == user.org_id,
    ).count()
    if total == 0:
        insights.append({
            "type": "first_optimization",
            "title": "No optimizations run yet",
            "detail": "Run your first optimization to discover potential savings",
            "action_label": "Start Optimization",
            "action_url": "/optimizations/new",
            "priority": "high",
            "icon": "action",
        })

    return insights


def _get_market_alerts() -> list[dict]:
    """Get market condition alerts."""
    alerts = []

    try:
        from app.market_data.yield_curve import fetch_treasury_yield_curve
        from app.market_data.interest_rates import fetch_all_benchmark_rates

        yield_data = fetch_treasury_yield_curve() or {}
        rates_data = fetch_all_benchmark_rates() or {}

        # Handle both formats: maturities list and rates dict
        rates = {}
        maturities = yield_data.get("maturities", [])
        for m in maturities:
            label = m.get("label", "")
            rate = m.get("rate_pct", m.get("rate", 0))
            if label and rate:
                rates[label] = rate
        if not rates:
            rates = yield_data.get("rates", {})
        rate_2y = rates.get("2Y") or rates.get("02") or 0
        rate_10y = rates.get("10Y") or rates.get("10") or 0

        if rate_2y and rate_10y and rate_2y > rate_10y:
            alerts.append({
                "type": "yield_curve_inversion",
                "title": "Yield curve inverted",
                "detail": f"2Y ({rate_2y}%) > 10Y ({rate_10y}%) — refinancing window may be opening",
                "action_label": "View Market Data",
                "action_url": "/market",
                "priority": "high",
                "icon": "alert",
            })
    except Exception:
        pass

    return alerts


def _get_watchlist_alerts(user: User, db: Session) -> list[dict]:
    """Get alerts from user watchlists."""
    alerts = []

    watchlists = db.query(Watchlist).filter(Watchlist.user_id == user.id).all()
    for wl in watchlists:
        items = db.query(WatchlistItem).filter(WatchlistItem.watchlist_id == wl.id).all()
        if items:
            alerts.append({
                "type": "watchlist_update",
                "title": f"Watchlist '{wl.name}' has {len(items)} items",
                "detail": "Check for threshold breaches and new alerts",
                "action_label": "View Watchlist",
                "action_url": "/watchlists",
                "priority": "low",
                "icon": "watchlist",
            })

    return alerts


def _get_notification_summary(user: User, db: Session) -> dict:
    """Get unread notification summary."""
    unread_count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.read.is_(False),
    ).count()

    recent = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.created_at >= datetime.now(timezone.utc) - timedelta(days=1),
    ).order_by(Notification.created_at.desc()).limit(5).all()

    return {
        "unread_count": unread_count,
        "recent": [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in recent
        ],
    }


# ── Main endpoint ──────────────────────────────────────────────────────


@router.get("")
def get_daily_briefing(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the complete daily briefing.

    Aggregates all alerts, insights, and action items into a
    prioritized briefing with one-click actions.
    """
    # Gather all data
    upcoming_maturities = _get_upcoming_maturities(user, db)
    optimization_insights = _get_optimization_insights(user, db)
    market_alerts = _get_market_alerts()
    watchlist_alerts = _get_watchlist_alerts(user, db)
    notification_summary = _get_notification_summary(user, db)

    # Combine and prioritize
    all_items = []

    # Maturities
    for mat in upcoming_maturities:
        all_items.append({
            "category": "maturity",
            "priority": mat["urgency"],
            "title": f"{mat['name']} matures in {mat['days_until_maturity']} days",
            "detail": f"${mat['principal']:,.0f} {mat['currency']} — {mat['coupon_rate']}% coupon",
            "action_label": "Pre-fund Now",
            "action_url": f"/optimizations/new?portfolio={mat['portfolio_id']}",
            "icon": "maturity",
            "metadata": {
                "days": mat["days_until_maturity"],
                "principal": mat["principal"],
                "currency": mat["currency"],
            },
        })

    # Optimization insights
    all_items.extend(optimization_insights)

    # Market alerts
    all_items.extend(market_alerts)

    # Watchlist alerts
    all_items.extend(watchlist_alerts)

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_items.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 4))

    # Compute summary stats
    critical_count = sum(1 for item in all_items if item.get("priority") == "critical")
    high_count = sum(1 for item in all_items if item.get("priority") == "high")
    total_maturity_value = sum(
        m["principal"] for m in upcoming_maturities
    )

    # Overall briefing message
    if critical_count > 0:
        briefing_message = (
            f"{critical_count} critical items require immediate attention. "
            f"{len(upcoming_maturities)} instruments approaching maturity "
            f"totaling ${total_maturity_value:,.0f}."
        )
    elif high_count > 0:
        briefing_message = (
            f"{len(all_items)} items need your attention. "
            f"{len(upcoming_maturities)} instruments maturing soon."
        )
    else:
        briefing_message = "All clear. No urgent items today."

    return {
        "briefing_message": briefing_message,
        "items": all_items,
        "item_count": len(all_items),
        "critical_count": critical_count,
        "high_count": high_count,
        "upcoming_maturities": upcoming_maturities,
        "total_maturity_value_usd": total_maturity_value,
        "notifications": notification_summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/action-items")
def get_action_items(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get prioritized one-click action items for the user."""
    briefing = get_daily_briefing(user, db)

    # Extract only actionable items
    action_items = [
        item for item in briefing["items"]
        if item.get("action_label") and item.get("action_url")
    ]

    return {
        "action_items": action_items,
        "total": len(action_items),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/maturity-timeline")
def get_maturity_timeline(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    horizon_days: int = Query(default=365, ge=30, le=730),
):
    """Get a maturity timeline for visualization."""
    maturities = _get_upcoming_maturities(user, db, days=horizon_days)

    # Group by month
    monthly = {}
    for mat in maturities:
        month_key = mat["maturity_date"][:7]  # YYYY-MM
        if month_key not in monthly:
            monthly[month_key] = {
                "month": month_key,
                "instruments": [],
                "total_principal": 0,
                "currency_breakdown": {},
            }
        monthly[month_key]["instruments"].append(mat)
        monthly[month_key]["total_principal"] += mat["principal"]
        currency = mat["currency"]
        monthly[month_key]["currency_breakdown"][currency] = (
            monthly[month_key]["currency_breakdown"].get(currency, 0) + mat["principal"]
        )

    timeline = sorted(monthly.values(), key=lambda x: x["month"])

    return {
        "timeline": timeline,
        "total_instruments": len(maturities),
        "total_value_usd": sum(m["total_principal"] for m in timeline),
        "horizon_days": horizon_days,
    }
