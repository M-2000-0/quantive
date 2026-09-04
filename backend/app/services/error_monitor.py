"""Error monitoring service — tracks error rates, thresholds, and alerts."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.monitoring.error")


def get_error_metrics(db: Session, org_id: str, hours: int = 24) -> dict:
    """Get error rate metrics over a time window."""
    from app.models import AuditEvent

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    # Count error events (failed actions in audit log)
    total_events = db.query(AuditEvent).filter(
        AuditEvent.org_id == org_id,
        AuditEvent.created_at >= cutoff,
    ).count()

    error_events = db.query(AuditEvent).filter(
        AuditEvent.org_id == org_id,
        AuditEvent.created_at >= cutoff,
        AuditEvent.action.like("%failed%"),
    ).count()

    error_rate = (error_events / max(total_events, 1)) * 100

    return {
        "period_hours": hours,
        "total_events": total_events,
        "error_events": error_events,
        "error_rate_pct": round(error_rate, 2),
        "status": "critical" if error_rate > 10 else "warning" if error_rate > 5 else "healthy",
    }


def get_error_breakdown(db: Session, org_id: str, hours: int = 24) -> dict:
    """Get error breakdown by type/resource."""
    from app.models import AuditEvent

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    errors = db.query(AuditEvent).filter(
        AuditEvent.org_id == org_id,
        AuditEvent.created_at >= cutoff,
        AuditEvent.action.like("%failed%"),
    ).all()

    by_resource = {}
    by_action = {}
    for e in errors:
        by_resource.setdefault(e.resource_type, 0)
        by_resource[e.resource_type] += 1
        by_action.setdefault(e.action, 0)
        by_action[e.action] += 1

    return {
        "by_resource": dict(sorted(by_resource.items(), key=lambda x: -x[1])[:10]),
        "by_action": dict(sorted(by_action.items(), key=lambda x: -x[1])[:10]),
        "total_errors": len(errors),
    }


def check_error_thresholds(
    db: Session,
    org_id: str,
    error_rate_threshold: float = 5.0,
    error_count_threshold: int = 50,
) -> list[dict]:
    """Check if error rates exceed thresholds and generate alerts."""
    metrics = get_error_metrics(db, org_id, hours=1)
    alerts = []

    if metrics["error_rate_pct"] > error_rate_threshold:
        alerts.append({
            "type": "error_rate_exceeded",
            "severity": "critical" if metrics["error_rate_pct"] > 10 else "warning",
            "message": f"Error rate {metrics['error_rate_pct']:.1f}% exceeds threshold {error_rate_threshold}%",
            "current_rate": metrics["error_rate_pct"],
            "threshold": error_rate_threshold,
        })

    if metrics["error_events"] > error_count_threshold:
        alerts.append({
            "type": "error_count_exceeded",
            "severity": "warning",
            "message": f"Error count {metrics['error_events']} exceeds threshold {error_count_threshold}",
            "current_count": metrics["error_events"],
            "threshold": error_count_threshold,
        })

    return alerts


def get_error_trend(db: Session, org_id: str, days: int = 7) -> list[dict]:
    """Get error rate trend over multiple days."""
    from app.models import AuditEvent

    trend = []
    for d in range(days):
        day_start = (datetime.now(timezone.utc) - timedelta(days=d + 1)).isoformat()
        day_end = (datetime.now(timezone.utc) - timedelta(days=d)).isoformat()

        total = db.query(AuditEvent).filter(
            AuditEvent.org_id == org_id,
            AuditEvent.created_at >= day_start,
            AuditEvent.created_at < day_end,
        ).count()

        errors = db.query(AuditEvent).filter(
            AuditEvent.org_id == org_id,
            AuditEvent.created_at >= day_start,
            AuditEvent.created_at < day_end,
            AuditEvent.action.like("%failed%"),
        ).count()

        trend.append({
            "date": day_end[:10],
            "total_events": total,
            "error_events": errors,
            "error_rate_pct": round((errors / max(total, 1)) * 100, 2),
        })

    return list(reversed(trend))
