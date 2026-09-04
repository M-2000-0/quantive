"""Metrics API — Behavioral tracking and analytics endpoints.

- POST /api/metrics/track — Record a user event
- GET /api/metrics/summary — Get user behavioral summary
- GET /api/metrics/organization — Get org-level metrics
- GET /api/metrics/adoption — Get feature adoption rates
"""

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import User

_optional_bearer = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    token = None
    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(token)
        if payload:
            uid = payload.get("sub")
            return db.query(User).filter(User.id == uid).first()
    except Exception:
        pass
    return None


class TrackEventRequest(BaseModel):
    event_type: str
    event_category: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    metadata: Optional[dict] = None
    session_id: Optional[str] = None
    duration_ms: Optional[int] = None


@router.post("/track")
def track_event(
    data: TrackEventRequest,
    request: Request,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Record a user event."""
    if not user:
        return {"tracked": False}

    from app.services.behavioral_metrics import BehavioralMetrics
    tracker = BehavioralMetrics(db)
    return tracker.track(
        user_id=str(user.id),
        event_type=data.event_type,
        event_category=data.event_category,
        resource_type=data.resource_type,
        resource_id=data.resource_id,
        metadata=data.metadata,
        session_id=data.session_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        duration_ms=data.duration_ms,
    )


@router.get("/summary")
def get_summary(
    days: int = 30,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get behavioral summary for current user."""
    if not user:
        return {"error": "Not authenticated"}

    from app.services.behavioral_metrics import BehavioralMetrics
    tracker = BehavioralMetrics(db)
    return tracker.get_user_summary(str(user.id), days=days)


@router.get("/organization")
def get_org_metrics(
    days: int = 30,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get aggregate metrics for the user's organization."""
    if not user:
        return {"error": "Not authenticated"}

    from app.services.behavioral_metrics import BehavioralMetrics
    tracker = BehavioralMetrics(db)
    return tracker.get_org_summary(user.org_id, days=days)


@router.get("/adoption")
def get_adoption(
    days: int = 30,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get feature adoption rates."""
    if not user:
        return {"error": "Not authenticated"}

    from app.services.behavioral_metrics import BehavioralMetrics
    tracker = BehavioralMetrics(db)
    return {"features": tracker.get_feature_adoption(user.org_id, days=days)}
