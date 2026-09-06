"""Billing and subscription API endpoints."""
import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.billing import (
    PlanTier,
    PLAN_DETAILS,
    check_limit,
    create_checkout_session,
    create_customer_portal,
    create_subscription,
    get_subscription,
    get_usage,
    handle_stripe_event,
    record_usage,
    verify_stripe_webhook,
)
from app.database import get_db
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/plans")
def list_plans():
    """List all available subscription plans."""
    return {
        "plans": [
            {
                "tier": tier.value,
                "name": details["name"],
                "price_monthly": details["price_monthly"],
                "price_yearly": details["price_yearly"],
                "features": details["features"],
            }
            for tier, details in PLAN_DETAILS.items()
        ]
    }


@router.get("/subscription")
def get_my_subscription(
    user: User = Depends(get_current_user),
):
    """Get current subscription for the user's organization."""
    sub = get_subscription(user.org_id)
    if not sub:
        return {
            "subscription": None,
            "tier": "free",
            "limits": PLAN_DETAILS[PlanTier.FREE]["limits"],
        }

    return {
        "subscription": {
            "id": sub.id,
            "tier": sub.tier.value,
            "billing_cycle": sub.billing_cycle,
            "status": sub.status,
            "current_period_start": sub.current_period_start,
            "current_period_end": sub.current_period_end,
        },
        "tier": sub.tier.value,
        "limits": PLAN_DETAILS[sub.tier]["limits"],
    }


@router.post("/checkout")
async def create_checkout(
    request: Request,
    tier: str = Query(..., description="Plan tier: pro, enterprise"),
    billing_cycle: str = Query("monthly", description="monthly or yearly"),
    user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout session for upgrading."""
    try:
        plan_tier = PlanTier(tier)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid tier: {tier}")

    if plan_tier == PlanTier.FREE:
        raise HTTPException(status_code=422, detail="Free tier does not require checkout")

    # Success/cancel URLs: env override first, else derive from the request
    # so localhost/staging/production all return to the right place without
    # hardcoding an environment-specific URL in code.
    base_url = os.environ.get("STRIPE_SUCCESS_BASE_URL", "").rstrip("/") or str(request.base_url).rstrip("/")
    success_url = f"{base_url}/billing?checkout=success"
    cancel_url = f"{base_url}/billing?checkout=cancelled"

    session = await create_checkout_session(
        org_id=user.org_id,
        user_id=user.id,
        tier=plan_tier,
        billing_cycle=billing_cycle,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session


@router.post("/portal")
async def customer_portal(
    user: User = Depends(get_current_user),
):
    """Create a Stripe Customer Portal session."""
    sub = get_subscription(user.org_id)
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No active subscription found")

    portal = await create_customer_portal(sub.stripe_customer_id)
    return portal


@router.get("/usage")
def my_usage(
    resource: str = Query("optimization", description="Resource type"),
    since_hours: int = Query(24, ge=1, le=720),
    user: User = Depends(get_current_user),
):
    """Get usage stats for the current org."""
    return get_usage(user.org_id, resource, since_hours)


@router.get("/limits")
def my_limits(
    resource: str = Query("optimizations_per_day", description="Resource to check"),
    user: User = Depends(get_current_user),
):
    """Check current limits against usage."""
    return check_limit(user.org_id, resource)


logger = logging.getLogger("quantive.billing.webhook")


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request):
    """Receive Stripe webhook events.

    Signature-verified (Stripe-Signature header); the raw request body is
    required for HMAC computation, so the body must be read before any JSON
    parsing. Unverified signatures are rejected with 400.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    if not verify_stripe_webhook(payload, signature):
        logger.warning("Stripe webhook signature verification failed")
        return JSONResponse(status_code=400, content={"error": "Invalid signature"})

    try:
        event = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JSONResponse(status_code=400, content={"error": "Invalid payload"})

    event_type = event.get("type", "")
    result = handle_stripe_event(event_type, event.get("data", {}))

    # Always 200 so Stripe retries don't hammer us for handled no-ops.
    return {"received": True, "handled": result is not None, "action": (result or {}).get("action")}
