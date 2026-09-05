"""Weekly Digest Email API.

Endpoints:
  GET  /api/v1/weekly-digest/preview  — Render the digest (auth'd users; no send)
  POST /api/v1/weekly-digest/send     — Send to all opted-in users (admin) or self (test)
"""
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger("quantive.weekly_digest_api")

router = APIRouter(prefix="/weekly-digest", tags=["weekly-digest"])


def _get_user(request: Request, db: Session):
    token = request.cookies.get("access_token", "")
    if not token:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(token)
        if payload:
            from app.models import User
            return db.query(User).filter(User.id == payload.get("sub")).first()
    except Exception:
        pass
    return None


@router.get("/preview")
def preview_digest():
    """Build and return the digest content without sending (for preview/testing)."""
    from app.services.weekly_digest_email import build_digest

    digest = build_digest()
    return {
        "week": digest["data"]["week"],
        "subject": digest["subject"],
        "body_text": digest["body_text"],
        "summary": {
            "track_record": digest["data"]["track_record"],
            "discovery_count": len(digest["data"]["discovery"]),
            "bubble_count": len(digest["data"]["bubble"]),
            "context": digest["data"]["context"],
        },
        "body_html": digest["body_html"],
    }


@router.post("/send")
async def send_digest(request: Request, db: Session = Depends(get_db)):
    """Send the weekly digest.

    Admins send to all opted-in users; regular users send only to themselves
    (useful as a "send me a test" action).
    """
    import asyncio

    from app.models import UserRole
    from app.services.weekly_digest_email import send_weekly_digest

    user = _get_user(request, db)
    if not user:
        return {"error": "Not authenticated"}

    is_admin = user.role in (UserRole.ADMIN, "admin", "ADMIN")

    if is_admin:
        result = await send_weekly_digest(db=db, user=None)
        return {**result, "scope": "all opted-in users"}

    # Non-admin: send only to self (respects their opt-in flag)
    result = await send_weekly_digest(db=db, user=user)
    return {**result, "scope": "self (opt-in respected)"}


@router.get("/optin")
def get_optin_status(request: Request, db: Session = Depends(get_db)):
    """Current user's weekly-digest opt-in status."""
    user = _get_user(request, db)
    if not user:
        return {"error": "Not authenticated"}
    from app.services.weekly_digest_email import _is_opted_in
    return {"opted_in": _is_opted_in(db, user), "email": user.email}


@router.post("/optin")
def set_optin(request: Request, db: Session = Depends(get_db), enabled: bool = True):
    """Toggle weekly digest opt-in for the current user."""
    user = _get_user(request, db)
    if not user:
        return {"error": "Not authenticated"}

    try:
        from sqlalchemy.orm.attributes import flag_modified

        from app.models.user_profile import UserProfile

        prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if prof:
            meta = prof.compliance_constraints if isinstance(prof.compliance_constraints, dict) else {}
            settings = meta.get("notification_settings") or {}
            settings["weekly_digest"] = enabled
            settings.setdefault("email_alerts", True)
            meta["notification_settings"] = settings
            prof.compliance_constraints = meta
            flag_modified(prof, "compliance_constraints")
            db.commit()
            return {"opted_in": enabled}
        return {"error": "No profile found", "opted_in": False}
    except Exception as e:
        logger.warning("optin toggle failed: %s", e)
        return {"error": str(e)}
