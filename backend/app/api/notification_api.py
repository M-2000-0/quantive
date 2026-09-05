"""Notification delivery API.

Endpoints:
  GET  /api/v1/notifications/settings  — Get user's notification preferences
  POST /api/v1/notifications/settings  — Update preferences (email/SMS toggles)
  POST /api/v1/notifications/test      — Send a test notification to verify delivery
  GET  /api/v1/notifications/history   — Recent notification deliveries
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/notifications", tags=["notification-delivery"])


def _get_user(request: Request, db: Session):
    token = request.cookies.get("access_token", "")
    if not token:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(token)
        if payload:
            return db.query(User).filter(User.id == payload.get("sub")).first()
    except Exception:
        pass
    return None


class NotificationSettings(BaseModel):
    email_alerts: bool = True
    sms_alerts: bool = False
    bubble_alerts: bool = True
    price_thresholds: bool = True
    phone_number: Optional[str] = None


def _get_or_create_settings(db: Session, user: User) -> dict:
    """Notification prefs live on user_profiles.metadata if available, else a simple default."""
    try:
        from app.models.user_profile import UserProfile
        prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if prof and getattr(prof, "compliance_constraints", None):
            meta = prof.compliance_constraints or {}
            if isinstance(meta, dict) and "notification_settings" in meta:
                return meta["notification_settings"]
    except Exception:
        pass
    return {
        "email_alerts": True,
        "sms_alerts": False,
        "bubble_alerts": True,
        "price_thresholds": True,
        "phone_number": None,
    }


def _save_settings(db: Session, user: User, settings: dict):
    try:
        from app.models.user_profile import UserProfile
        prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if prof:
            meta = prof.compliance_constraints if isinstance(prof.compliance_constraints, dict) else {}
            meta["notification_settings"] = settings
            flag_modified = False
            try:
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(prof, "compliance_constraints")
                flag_modified = True
            except ImportError:
                pass
            prof.compliance_constraints = meta
            db.commit()
            return True
    except Exception:
        pass
    return False


@router.get("/settings")
def get_notification_settings(request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return {"error": "Not authenticated"}
    settings = _get_or_create_settings(db, user)
    from app.services.notification_dispatcher import is_sms_configured
    return {
        "settings": settings,
        "sms_configured": is_sms_configured(),
        "email_available": True,
    }


@router.post("/settings")
def update_notification_settings(data: NotificationSettings, request: Request, db: Session = Depends(get_db)):
    user = _get_user(request, db)
    if not user:
        return {"error": "Not authenticated"}
    settings = {
        "email_alerts": data.email_alerts,
        "sms_alerts": data.sms_alerts,
        "bubble_alerts": data.bubble_alerts,
        "price_thresholds": data.price_thresholds,
        "phone_number": data.phone_number,
    }
    ok = _save_settings(db, user, settings)
    return {"saved": ok, "settings": settings}


@router.post("/test")
def send_test_notification(request: Request, db: Session = Depends(get_db)):
    """Send a test alert through all enabled channels so users can verify delivery."""
    user = _get_user(request, db)
    if not user:
        return {"error": "Not authenticated"}

    settings = _get_or_create_settings(db, user)
    import asyncio

    async def _send():
        from app.services.notification_dispatcher import send_price_alert
        return await send_price_alert(
            user_id=user.id,
            user_email=user.email if settings.get("email_alerts", True) else "",
            symbol="TEST",
            alert_type="test",
            message="This is a test notification from Quantive. If you received this, delivery works.",
            current_price=123.45,
            threshold=100.0,
            user_phone=settings.get("phone_number") or getattr(user, "phone", None),
            notify_email=settings.get("email_alerts", True),
            notify_sms=settings.get("sms_alerts", False),
        )

    try:
        loop = asyncio.get_running_loop()
        results = loop.run_until_complete(_send())
    except RuntimeError:
        results = asyncio.run(_send())

    return {"sent": True, "channels": results}


@router.get("/history")
def notification_history(request: Request, db: Session = Depends(get_db), limit: int = 50):
    user = _get_user(request, db)
    if not user:
        return {"error": "Not authenticated"}
    from app.services.notification_dispatcher import get_delivery_history
    history = [h for h in get_delivery_history(limit) if h.get("user_id") == user.id]
    return {"history": history, "count": len(history)}
