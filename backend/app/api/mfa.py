"""Multi-Factor Authentication (MFA) API endpoints.

Provides:
- POST /api/auth/mfa/setup — Generate TOTP secret + QR code
- POST /api/auth/mfa/enable — Enable MFA after verifying first code
- POST /api/auth/mfa/disable — Disable MFA
- POST /api/auth/mfa/verify — Verify a TOTP code during login
- GET /api/auth/mfa/status — Check MFA status
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
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

# In-memory MFA setup state (maps user_id -> setup state)
# In production, this would be stored in Redis or a dedicated MFA table
_mfa_setup_state: dict[str, dict] = {}


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
def setup_mfa(user: User = Depends(get_current_user)):
    """Generate a new TOTP secret and QR code for MFA setup.

    This does NOT enable MFA yet — the user must verify a code first via /enable.
    """
    secret = generate_secret()
    uri = generate_totp_uri(secret, user.email)
    qr_base64 = generate_qr_code_base64(uri)

    # Generate backup codes
    codes = generate_backup_codes()
    code_hashes = [hash_backup_code(c) for c in codes]

    # Store the setup state temporarily
    _mfa_setup_state[user.id] = {
        "secret": secret,
        "code_hashes": code_hashes,
    }

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
    """Enable MFA by verifying the first TOTP code.

    Must call /setup first to generate the secret.
    """
    setup = _mfa_setup_state.get(user.id)
    if not setup:
        raise HTTPException(status_code=400, detail="MFA setup not initiated. Call POST /api/auth/mfa/setup first.")

    secret = setup["secret"]

    # Verify the code
    if not verify_totp(secret, data.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code. Please try again.")

    # TODO: Persist secret and code_hashes to database (MFAConfig table)
    # For now, mark as enabled in-memory

    # Clean up setup state
    _mfa_setup_state.pop(user.id, None)

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
        raise HTTPException(status_code=400, detail="Invalid password")

    # TODO: Clear MFA settings from database

    log_audit_event(db, user, "mfa.disabled", "user", user.id)


@router.post("/verify")
def verify_mfa_code(
    data: MFAVerifyRequest,
    user: User = Depends(get_current_user),
):
    """Verify a TOTP code or backup code during login flow.

    Returns a temporary MFA session token.
    """
    setup = _mfa_setup_state.get(user.id)

    if not setup:
        raise HTTPException(status_code=400, detail="MFA not configured for this user")

    # Try TOTP verification first
    if len(data.code) == 6 and data.code.isdigit():
        if verify_totp(setup["secret"], data.code):
            from app.security import create_access_token
            token = create_access_token({
                "sub": user.id,
                "org_id": user.org_id,
                "role": user.role,
                "mfa_verified": True,
            })
            return {"access_token": token, "token_type": "bearer"}

    # Try backup code
    backup_index = verify_backup_code(data.code, setup.get("code_hashes", []))
    if backup_index is not None:
        # Remove used backup code
        setup["code_hashes"].pop(backup_index)
        from app.security import create_access_token
        token = create_access_token({
            "sub": user.id,
            "org_id": user.org_id,
            "role": user.role,
            "mfa_verified": True,
        })
        return {"access_token": token, "token_type": "bearer"}

    raise HTTPException(status_code=400, detail="Invalid MFA code")


@router.get("/status", response_model=MFAStatusResponse)
def get_mfa_status(user: User = Depends(get_current_user)):
    """Check MFA status for the current user."""
    setup = _mfa_setup_state.get(user.id)
    return MFAStatusResponse(
        enabled=False,  # TODO: Check database for persisted MFA config
        backup_codes_remaining=len(setup.get("code_hashes", [])) if setup else None,
    )
