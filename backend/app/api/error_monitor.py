"""Error Monitoring API — error rates, thresholds, trends."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import get_current_user
from app.services.error_monitor import (
    check_error_thresholds,
    get_error_breakdown,
    get_error_metrics,
    get_error_trend,
)

router = APIRouter(prefix="/api/error-monitor", tags=["error-monitoring"])


@router.get("/metrics")
def metrics(
    hours: int = Query(24, ge=1, le=168),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get error rate metrics."""
    return get_error_metrics(db, user.org_id, hours=hours)


@router.get("/breakdown")
def breakdown(
    hours: int = Query(24, ge=1, le=168),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get error breakdown by resource and action."""
    return get_error_breakdown(db, user.org_id, hours=hours)


@router.get("/alerts")
def alerts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check error thresholds and return active alerts."""
    return {"alerts": check_error_thresholds(db, user.org_id)}


@router.get("/trend")
def trend(
    days: int = Query(7, ge=1, le=30),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get error rate trend over time."""
    return {"trend": get_error_trend(db, user.org_id, days=days)}
