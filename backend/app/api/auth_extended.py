"""Password reset and email verification endpoints."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.password_reset import EmailVerificationToken, PasswordResetToken
from app.security import hash_password, log_audit_event, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

RESET_TOKEN_EXPIRE_MINUTES = 30
VERIFY_TOKEN_EXPIRE_MINUTES = 60


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    from pydantic import field_validator

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


@router.post("/forgot-password", status_code=202)
def forgot_password(data: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """Send a password reset token to the user's email.

    Always returns 202 to prevent email enumeration.
    """
    email = data.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if user and user.is_active:
        # Invalidate any existing reset tokens
        existing = db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used.is_(False),
        ).all()
        for t in existing:
            t.used = True
        db.commit()

        # Generate new token
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        db.commit()

        # TODO: Send email with raw_token via email service
        # For now, log it for development
        import logging
        logger = logging.getLogger("quantive.auth")
        logger.info(f"Password reset token for {email}: {raw_token}")

        ip = request.client.host if request.client else None
        log_audit_event(db, user, "user.password_reset_requested", "user", user.id, ip_address=ip)

    return {"detail": "If the email exists, a reset link has been sent."}


@router.post("/reset-password", status_code=204)
def reset_password(data: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """Reset password using a valid token."""
    token_hash = _hash_token(data.token)

    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used.is_(False),
    ).first()

    if not reset_token or not reset_token.is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    # Mark token as used
    reset_token.used = True

    # Update password
    user.password_hash = hash_password(data.new_password)
    db.commit()

    ip = request.client.host if request.client else None
    log_audit_event(db, user, "user.password_reset_completed", "user", user.id, ip_address=ip)


@router.post("/verify-email", status_code=204)
def verify_email(data: VerifyEmailRequest, request: Request, db: Session = Depends(get_db)):
    """Verify email address using a valid token."""
    token_hash = _hash_token(data.token)

    verify_token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token_hash == token_hash,
        EmailVerificationToken.used.is_(False),
    ).first()

    if not verify_token or not verify_token.is_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user = db.query(User).filter(User.id == verify_token.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    verify_token.used = True
    # TODO: Set email_verified flag on user when that column exists
    db.commit()

    ip = request.client.host if request.client else None
    log_audit_event(db, user, "user.email_verified", "user", user.id, ip_address=ip)


@router.post("/resend-verification", status_code=202)
def resend_verification(data: ResendVerificationRequest, request: Request, db: Session = Depends(get_db)):
    """Resend email verification. Always returns 202."""
    email = data.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()

    if user and user.is_active:
        # Invalidate existing
        existing = db.query(EmailVerificationToken).filter(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used.is_(False),
        ).all()
        for t in existing:
            t.used = True
        db.commit()

        # Generate new
        raw_token = secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=VERIFY_TOKEN_EXPIRE_MINUTES)

        verify_token = EmailVerificationToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(verify_token)
        db.commit()

        import logging
        logger = logging.getLogger("quantive.auth")
        logger.info(f"Email verification token for {email}: {raw_token}")

    return {"detail": "If the email exists, a verification link has been sent."}
