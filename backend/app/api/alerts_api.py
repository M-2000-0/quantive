"""Alerts API — Proactive notification endpoints.

- GET /api/alerts — List user alerts (with unread filter)
- GET /api/alerts/count — Get unread count
- POST /api/alerts/check — Run alert checks for current user
- PUT /api/alerts/{id}/read — Mark single alert as read
- PUT /api/alerts/read-all — Mark all as read
"""

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import User

_optional_bearer = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


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


@router.get("/")
def list_alerts(
    unread_only: bool = False,
    limit: int = 50,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """List alerts for the current user."""
    if not user:
        return {"alerts": [], "count": 0}

    from app.services.alert_engine import AlertEngine
    engine = AlertEngine(db)
    alerts = engine.get_user_alerts(str(user.id), unread_only=unread_only, limit=limit)
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/count")
def unread_count(
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get unread alert count for badge display."""
    if not user:
        return {"count": 0}

    from app.services.alert_engine import AlertEngine
    engine = AlertEngine(db)
    return {"count": engine.get_unread_count(str(user.id))}


@router.post("/check")
def check_alerts(
    request: Request,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Run all alert checks and return any new alerts."""
    if not user:
        return {"alerts": [], "new_count": 0}

    from app.services.alert_engine import AlertEngine
    engine = AlertEngine(db)
    new_alerts = engine.check_all_alerts(str(user.id), user.org_id)
    return {
        "alerts": new_alerts,
        "new_count": len(new_alerts),
        "checked_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


@router.put("/{alert_id}/read")
def mark_read(
    alert_id: int,
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Mark a single alert as read."""
    if not user:
        return {"success": False}

    from app.services.alert_engine import AlertEngine
    engine = AlertEngine(db)
    success = engine.mark_read(alert_id, str(user.id))
    return {"success": success}


@router.put("/read-all")
def mark_all_read(
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Mark all alerts as read."""
    if not user:
        return {"success": False, "count": 0}

    from app.services.alert_engine import AlertEngine
    engine = AlertEngine(db)
    count = engine.mark_all_read(str(user.id))
    return {"success": True, "count": count}
