"""Multi-Factor Authentication (MFA) API endpoints.

SECURITY FIX: MFA secrets now persist to database (not in-memory dict).
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.mfa_config import MFAConfig
from app.security import get_current_user, log_audit_event
from app.security.mfa import (
    generate_backup_codes,
    generate_qr_code_base64,
    generate_secret,
    generate_totp_uri,
    hash_backup_code,
    verify_backup_code,
    verify_totp,
)

router = APIRouter(prefix="/api/auth/mfa", tags=["mfa"])


# ── Schemas ─────────────────────────────────────────────────────────────────

class MFASetupResponse(BaseModel):
    secret: str
    qr_code_base64: str
    uri: str
    backup_codes: list[str]


class MFAEnableRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class MFAVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=10, description="TOTP code or backup code")


class MFADisableRequest(BaseModel):
    password: str = Field(..., description="Current password for confirmation")


class MFAStatusResponse(BaseModel):
    enabled: bool
    backup_codes_remaining: Optional[int] = None


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/setup", response_model=MFASetupResponse)
def setup_mfa(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a new TOTP secret and QR code for MFA setup.

    Persists to database so setup survives server restarts.
    """
    secret = generate_secret()
    uri = generate_totp_uri(secret, user.email)
    qr_base64 = generate_qr_code_base64(uri)

    # Generate backup codes
    codes = generate_backup_codes()
    code_hashes = [hash_backup_code(c) for c in codes]

    # SECURITY FIX: Persist to database, not in-memory dict
    existing = db.query(MFAConfig).filter(MFAConfig.user_id == user.id).first()
    if existing:
        existing.totp_secret = secret
        existing.backup_code_hashes = json.dumps(code_hashes)
        existing.enabled = False
    else:
        mfa_config = MFAConfig(
            user_id=user.id,
            totp_secret=secret,
            backup_code_hashes=json.dumps(code_hashes),
            enabled=False,
        )
        db.add(mfa_config)
    db.commit()

    log_audit_event(db, user, "mfa.setup_initiated", "user", user.id)

    return MFASetupResponse(
        secret=secret,
        qr_code_base64=qr_base64,
        uri=uri,
        backup_codes=codes,
    )


@router.post("/enable", status_code=204)
def enable_mfa(
    data: MFAEnableRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enable MFA by verifying the first TOTP code."""
    mfa_config = db.query(MFAConfig).filter(MFAConfig.user_id == user.id).first()
    if not mfa_config:
        raise HTTPException(status_code=400, detail="MFA setup not initiated.")

    # Verify the code
    if not verify_totp(mfa_config.totp_secret, data.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code.")

    from datetime import datetime, timezone
    mfa_config.enabled = True
    mfa_config.enabled_at = datetime.now(timezone.utc)
    db.commit()

    log_audit_event(db, user, "mfa.enabled", "user", user.id)


@router.post("/disable", status_code=204)
def disable_mfa(
    data: MFADisableRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disable MFA after verifying current password."""
    from app.security import verify_password
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid password.")

    mfa_config = db.query(MFAConfig).filter(MFAConfig.user_id == user.id).first()
    if mfa_config:
        mfa_config.enabled = False
        db.commit()

    log_audit_event(db, user, "mfa.disabled", "user", user.id)


@router.post("/verify")
def verify_mfa(
    data: MFAVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify a TOTP code or backup code during login."""
    mfa_config = db.query(MFAConfig).filter(MFAConfig.user_id == user.id).first()
    if not mfa_config or not mfa_config.enabled:
        return {"verified": True, "method": "none", "message": "MFA not enabled"}

    # Try TOTP first
    if verify_totp(mfa_config.totp_secret, data.code):
        from datetime import datetime, timezone
        mfa_config.last_used_at = datetime.now(timezone.utc)
        db.commit()
        log_audit_event(db, user, "mfa.verified", "user", user.id, metadata={"method": "totp"})
        return {"verified": True, "method": "totp"}

    # Try backup codes
    code_hashes = json.loads(mfa_config.backup_code_hashes)
    for i, stored_hash in enumerate(code_hashes):
        if stored_hash and verify_backup_code(stored_hash, data.code):
            # Remove used backup code
            code_hashes[i] = None
            mfa_config.backup_code_hashes = json.dumps(code_hashes)
            from datetime import datetime, timezone
            mfa_config.last_used_at = datetime.now(timezone.utc)
            db.commit()
            log_audit_event(db, user, "mfa.verified", "user", user.id, metadata={"method": "backup_code"})
            return {"verified": True, "method": "backup_code"}

    log_audit_event(db, user, "mfa.verification_failed", "user", user.id)
    raise HTTPException(status_code=400, detail="Invalid code.")


@router.get("/status", response_model=MFAStatusResponse)
def mfa_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Check MFA status."""
    mfa_config = db.query(MFAConfig).filter(MFAConfig.user_id == user.id).first()
    if not mfa_config:
        return MFAStatusResponse(enabled=False)

    backup_codes_remaining = sum(1 for h in json.loads(mfa_config.backup_code_hashes) if h is not None)
    return MFAStatusResponse(
        enabled=mfa_config.enabled,
        backup_codes_remaining=backup_codes_remaining,
    )
