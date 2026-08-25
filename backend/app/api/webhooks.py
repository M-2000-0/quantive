"""Webhooks Management API — CRUD, test, and delivery tracking."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.security import require_role
from app.webhooks import WebhookEvent, get_all_events, get_webhook_store

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class WebhookCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., max_length=2000)
    events: list[str] = Field(..., min_length=1, description="Event types to subscribe to")


class WebhookUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = Field(None, max_length=2000)
    events: Optional[list[str]] = None
    is_active: Optional[bool] = None


class WebhookResponse(BaseModel):
    id: str
    name: str
    url: str
    events: list[str]
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class WebhookTestResponse(BaseModel):
    success: bool
    status_code: Optional[int]
    message: str


@router.get("/events")
def list_events():
    """List all available webhook event types."""
    return {"events": get_all_events()}


@router.get("", response_model=list[WebhookResponse])
def list_webhooks(
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """List all webhooks for the organization."""
    store = get_webhook_store()
    return store.list_webhooks(user.org_id)


@router.post("", response_model=WebhookResponse, status_code=201)
def create_webhook(
    data: WebhookCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Create a new webhook."""
    # Validate events
    valid_events = {e.value for e in WebhookEvent}
    for event in data.events:
        if event not in valid_events and event != "*":
            raise HTTPException(status_code=422, detail=f"Invalid event type: {event}")

    store = get_webhook_store()
    webhook = store.create_webhook(
        org_id=user.org_id,
        name=data.name,
        url=data.url,
        events=data.events,
    )
    return webhook


@router.get("/{webhook_id}", response_model=WebhookResponse)
def get_webhook(
    webhook_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Get a webhook by ID."""
    store = get_webhook_store()
    webhook = store.get_webhook(webhook_id)
    if not webhook or webhook["org_id"] != user.org_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


@router.put("/{webhook_id}", response_model=WebhookResponse)
def update_webhook(
    webhook_id: str,
    data: WebhookUpdate,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Update a webhook."""
    store = get_webhook_store()
    webhook = store.get_webhook(webhook_id)
    if not webhook or webhook["org_id"] != user.org_id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if "events" in updates:
        valid_events = {e.value for e in WebhookEvent}
        for event in updates["events"]:
            if event not in valid_events and event != "*":
                raise HTTPException(status_code=422, detail=f"Invalid event type: {event}")

    return store.update_webhook(webhook_id, updates)


@router.delete("/{webhook_id}", status_code=204)
def delete_webhook(
    webhook_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Delete a webhook."""
    store = get_webhook_store()
    webhook = store.get_webhook(webhook_id)
    if not webhook or webhook["org_id"] != user.org_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    store.delete_webhook(webhook_id)


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
def test_webhook(
    webhook_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Send a test event to the webhook."""
    store = get_webhook_store()
    webhook = store.get_webhook(webhook_id)
    if not webhook or webhook["org_id"] != user.org_id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    import asyncio

    from app.webhooks import deliver_webhook

    test_payload = {
        "event": "system.test",
        "timestamp": "2026-08-24T00:00:00Z",
        "webhook_id": webhook_id,
        "data": {"message": "This is a test webhook delivery"},
    }

    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(
            deliver_webhook(webhook["url"], webhook["secret"], "system.test", test_payload, webhook_id)
        )
        loop.close()
        return WebhookTestResponse(
            success=result["success"],
            status_code=result.get("status_code"),
            message="Delivered" if result["success"] else f"Failed: {result.get('error', 'Unknown')}",
        )
    except Exception as e:
        return WebhookTestResponse(success=False, status_code=None, message=str(e))


@router.get("/{webhook_id}/deliveries")
def list_deliveries(
    webhook_id: str,
    limit: int = 50,
    user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """List delivery history for a webhook."""
    store = get_webhook_store()
    webhook = store.get_webhook(webhook_id)
    if not webhook or webhook["org_id"] != user.org_id:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"deliveries": store.get_deliveries(webhook_id, limit)}
