"""Email sending API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.email_service import (
    send_optimization_complete_email,
    send_password_reset_email,
    send_rate_alert_email,
    send_welcome_email,
    get_email_store,
)
from app.models import User
from app.security import get_current_user, require_role, UserRole

router = APIRouter(prefix="/api/email", tags=["email"])


class WelcomeEmailRequest(BaseModel):
    to: str = Field(..., description="Recipient email")
    name: str = Field(..., description="Recipient name")


class PasswordResetRequest(BaseModel):
    to: str = Field(..., description="Recipient email")
    token: str = Field(..., description="Reset token")


class RateAlertRequest(BaseModel):
    to: str = Field(..., description="Recipient email")
    rate_name: str = Field(..., description="Rate name")
    current_value: float = Field(..., description="Current rate value")
    previous_value: float = Field(..., description="Previous rate value")


@router.post("/welcome")
async def send_welcome(
    data: WelcomeEmailRequest,
    user: User = Depends(get_current_user),
):
    """Send a welcome email."""
    record = await send_welcome_email(data.to, data.name)
    return {"status": record.status.value, "id": record.id}


@router.post("/password-reset")
async def send_reset(
    data: PasswordResetRequest,
):
    """Send a password reset email."""
    record = await send_password_reset_email(data.to, data.token)
    return {"status": record.status.value, "id": record.id}


@router.post("/rate-alert")
async def send_alert(
    data: RateAlertRequest,
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Send a rate alert email."""
    record = await send_rate_alert_email(
        data.to, data.rate_name, data.current_value, data.previous_value
    )
    return {"status": record.status.value, "id": record.id}


@router.get("/deliveries")
def list_deliveries(
    limit: int = 50,
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """List email delivery history."""
    store = get_email_store()
    records = store.list_records(limit)
    return {
        "deliveries": [
            {
                "id": r.id,
                "to": r.to,
                "subject": r.subject,
                "status": r.status.value,
                "provider": r.provider,
                "created_at": r.created_at,
                "sent_at": r.sent_at,
            }
            for r in records
        ],
        "total": store.count(),
    }
