"""Notification system and Dashboard analytics API."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AuditEvent,
    JobStatus,
    Notification,
    OptimizationJob,
    Portfolio,
    User,
)
from app.security import get_current_user

logger = logging.getLogger("quantive.notifications")

# ── Notification Router ─────────────────────────────────────────────────────

notif_router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    read: bool
    created_at: str

    class Config:
        from_attributes = True


@notif_router.get("", response_model=list[NotificationResponse])
def list_notifications(
    user: User = Depends(get_current_user),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List notifications for the current user."""
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.read.is_(False))
    notifs = query.order_by(Notification.created_at.desc()).limit(limit).all()
    return [NotificationResponse.model_validate(n).model_dump(mode="json") for n in notifs]


@notif_router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get count of unread notifications."""
    count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.read.is_(False),
    ).count()
    return {"count": count}


@notif_router.post("/{notification_id}/read", status_code=204)
def mark_read(notification_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a notification as read."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = True
    db.commit()


@notif_router.post("/read-all", status_code=204)
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark all notifications as read."""
    db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.read.is_(False),
    ).update({"read": True})
    db.commit()


# ── Notification Helper ─────────────────────────────────────────────────────

def create_notification(
    db: Session,
    user_id: str,
    notif_type: str,
    title: str,
    message: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
):
    """Helper to create a notification."""
    notif = Notification(
        user_id=user_id,
        type=notif_type,
        title=title,
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db.add(notif)
    db.commit()
    logger.info(f"Notification created: {title} for user {user_id}")
    return notif


# ── Dashboard Analytics Router ──────────────────────────────────────────────

dashboard_router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@dashboard_router.get("")
def get_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get dashboard summary with key metrics.

    Returns:
    - Portfolio count and total value
    - Active optimizations and recent completions
    - Unread notification count
    - Recent activity feed
    - Upcoming maturities
    - Risk overview
    """
    org_id = user.org_id

    # Portfolio metrics
    portfolio_count = db.query(Portfolio).filter(Portfolio.org_id == org_id).count()

    # Optimization metrics
    active_optimizations = db.query(OptimizationJob).filter(
        OptimizationJob.org_id == org_id,
        OptimizationJob.status.in_([
            JobStatus.QUEUED, JobStatus.RUNNING,
            JobStatus.SCENARIO_GENERATION, JobStatus.SOLVING,
            JobStatus.BENCHMARKING, JobStatus.STRESS_TESTING,
        ]),
    ).count()

    completed_recent = db.query(OptimizationJob).filter(
        OptimizationJob.org_id == org_id,
        OptimizationJob.status == JobStatus.COMPLETED,
        OptimizationJob.completed_at >= datetime.now(timezone.utc) - timedelta(days=7),
    ).count()

    failed_recent = db.query(OptimizationJob).filter(
        OptimizationJob.org_id == org_id,
        OptimizationJob.status == JobStatus.FAILED,
        OptimizationJob.completed_at >= datetime.now(timezone.utc) - timedelta(days=7),
    ).count()

    # Notifications
    unread_count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.read.is_(False),
    ).count()

    # Recent activity
    recent_activities = db.query(AuditEvent).filter(
        AuditEvent.org_id == org_id,
    ).order_by(AuditEvent.created_at.desc()).limit(10).all()

    activity_feed = [
        {
            "action": a.action,
            "resource_type": a.resource_type,
            "actor_email": a.actor_email,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in recent_activities
    ]

    return {
        "portfolios": {
            "count": portfolio_count,
        },
        "optimizations": {
            "active": active_optimizations,
            "completed_recent": completed_recent,
            "failed_recent": failed_recent,
        },
        "notifications": {
            "unread": unread_count,
        },
        "recent_activity": activity_feed,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
