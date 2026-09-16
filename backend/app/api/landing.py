"""Landing Page API — Public endpoints for the marketing site."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/landing", tags=["landing"])


class SubscribeRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)


_subscribers: list[dict] = []


@router.post("/subscribe")
def subscribe(data: SubscribeRequest):
    """Accept early-access email signup."""
    # Deduplicate
    existing = [s for s in _subscribers if s["email"] == data.email.lower()]
    if existing:
        return {"status": "already_subscribed", "message": "You're already on the list."}

    _subscribers.append({
        "email": data.email.lower(),
        "source": "landing_page",
    })
    return {"status": "subscribed", "message": "Thanks for joining the waitlist!"}


@router.get("/subscribers")
def list_subscribers():
    """List all subscribers (demo/admin use)."""
    return {"subscribers": _subscribers, "total": len(_subscribers)}
