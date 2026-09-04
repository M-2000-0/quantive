"""
Disclaimer Acceptance API

Tracks user acceptance of financial disclaimers.
Required before running optimizations or viewing financial recommendations.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/disclaimer", tags=["disclaimer"])

# ── In-memory disclaimer acceptance store ────────────────────────────────────
# In production, this should be a database table with audit trail.
# Schema: { user_id: { version: str, accepted_at: str, ip: str, user_agent: str } }

DISCLAIMER_ACCEPTANCES: dict[str, dict] = {}


class DisclaimerAcceptanceRequest(BaseModel):
    version: str = "1.0.0"
    accepted_terms: bool = True
    accepted_privacy: bool = True
    accepted_financial_disclaimer: bool = True
    read_and_understood: bool = True


class DisclaimerStatus(BaseModel):
    accepted: bool
    version: Optional[str] = None
    accepted_at: Optional[str] = None
    all_accepted: bool = False


class DisclaimerAcceptanceResponse(BaseModel):
    success: bool
    message: str
    accepted_at: str
    version: str


# ── API Endpoints ────────────────────────────────────────────────────────────


@router.get("/status", response_model=DisclaimerStatus)
async def get_disclaimer_status(request: Request):
    """Check if the current user has accepted all disclaimers."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return DisclaimerStatus(accepted=False, all_accepted=False)

    record = DISCLAIMER_ACCEPTANCES.get(user_id)
    if not record:
        return DisclaimerStatus(accepted=False, all_accepted=False)

    return DisclaimerStatus(
        accepted=True,
        version=record.get("version"),
        accepted_at=record.get("accepted_at"),
        all_accepted=record.get("all_accepted", False),
    )


@router.post("/accept", response_model=DisclaimerAcceptanceResponse)
async def accept_disclaimer(
    body: DisclaimerAcceptanceRequest,
    request: Request,
):
    """Record user's acceptance of all disclaimers."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Validate all fields are accepted
    if not all([
        body.accepted_terms,
        body.accepted_privacy,
        body.accepted_financial_disclaimer,
        body.read_and_understood,
    ]):
        raise HTTPException(
            status_code=400,
            detail="All disclaimers must be accepted. Please accept Terms of Service, Privacy Policy, and Financial Disclaimer.",
        )

    now = datetime.now(timezone.utc).isoformat()
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    DISCLAIMER_ACCEPTANCES[user_id] = {
        "version": body.version,
        "accepted_at": now,
        "ip": client_ip,
        "user_agent": user_agent,
        "all_accepted": True,
        "accepted_terms": True,
        "accepted_privacy": True,
        "accepted_financial_disclaimer": True,
    }

    # Audit log
    logger.info(
        f"[DISCLAIMER] User {user_id} accepted disclaimer v{body.version} "
        f"from IP {client_ip} at {now}"
    )

    # Try to log to audit system
    try:
        from app.audit.logger import AuditLogger
        AuditLogger.log_event(
            action="disclaimer_accepted",
            resource_type="user",
            resource_id=user_id,
            actor=user_id,
            metadata={
                "version": body.version,
                "ip": client_ip,
                "accepted_terms": True,
                "accepted_privacy": True,
                "accepted_financial_disclaimer": True,
            },
        )
    except Exception:
        pass  # Audit logging is best-effort

    return DisclaimerAcceptanceResponse(
        success=True,
        message="All disclaimers accepted. You may now use financial features.",
        accepted_at=now,
        version=body.version,
    )


@router.delete("/revoke")
async def revoke_disclaimer(request: Request):
    """Revoke disclaimer acceptance (user can re-consent later)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if user_id in DISCLAIMER_ACCEPTANCES:
        del DISCLAIMER_ACCEPTANCES[user_id]
        logger.info(f"[DISCLAIMER] User {user_id} revoked disclaimer acceptance")

    return {"success": True, "message": "Disclaimer acceptance revoked"}
