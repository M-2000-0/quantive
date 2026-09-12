"""Billing and subscription API endpoints."""
import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.billing import (
    STRIPE_API_KEY,
    STRIPE_BASE_URL,
    STRIPE_WEBHOOK_SECRET,
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
from app.models import User, UserRole
from app.security import get_current_user, require_role

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
    tier: str = Query(..., description="Plan tier: pro, enterprise, personal_2k, personal, personal_10k"),
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


class SimulateRequest(BaseModel):
    session_id: str = Field(..., min_length=3, max_length=255)


@router.get("/mode")
def billing_mode(user: User = Depends(get_current_user)):
    """Which billing mode the server is operating in (for UI hints)."""
    return {
        "stripe_configured": bool(STRIPE_API_KEY),
        "webhook_secret_set": bool(STRIPE_WEBHOOK_SECRET),
        # Fulfillment simulation is only permitted while no real webhook
        # secret exists (local/test). Once Stripe signs our webhooks, the
        # simulator hard-locks.
        "simulate_allowed": not STRIPE_WEBHOOK_SECRET,
    }


@router.post("/webhook/simulate")
async def simulate_checkout_completed(
    data: SimulateRequest,
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Admin-only, test-mode-only fulfillment simulator.

    Fetches the REAL Checkout Session from Stripe (no invented data) and
    replays it through the exact handle_stripe_event path a genuine
    checkout.session.completed webhook would take. This completes the loop
    locally, where Stripe cannot reach us (no public webhook host).

    Hard-locked once STRIPE_WEBHOOK_SECRET is configured — production
    fulfillment may only come from signature-verified real webhooks.
    """
    if STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=403,
            detail="Simulator disabled: a webhook secret is configured; fulfillment must come from real Stripe webhooks.",
        )
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=400, detail="Simulator requires STRIPE_SECRET_KEY (dev mode fulfills directly at checkout).")

    import httpx

    # Accept both cs_test_... (checkout session) and pi_... (payment intent,
    # how one-time payments report success).
    if data.session_id.startswith("pi_"):
        path = f"payment_intents/{data.session_id}"
        event_type = "payment_intent.succeeded"
        paid_statuses = {"succeeded"}
        status_key = "status"
        hint = "Confirm the PaymentIntent with a test payment method, then simulate again."
    else:
        path = f"checkout/sessions/{data.session_id}"
        event_type = "checkout.session.completed"
        paid_statuses = {"paid", "no_payment_required"}
        status_key = "payment_status"
        hint = "Complete the payment with test card 4242 4242 4242 4242, then simulate again."

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{STRIPE_BASE_URL}/{path}",
            auth=(STRIPE_API_KEY, ""),
            timeout=30,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail=f"Object not found at Stripe: {data.session_id}")
        obj = resp.json()

    if obj.get(status_key) not in paid_statuses:
        return {
            "simulated": False,
            "reason": "object not paid",
            "status": obj.get(status_key),
            "note": hint,
        }

    # Checkout sessions store metadata at top level; PaymentIntents under
    # metadata. The handler reads obj['metadata'] either way.
    if "metadata" not in obj or not obj.get("metadata"):
        obj["metadata"] = {}

    result = handle_stripe_event(event_type, {"object": obj})
    return {"simulated": True, "handled": result is not None, "result": result}


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
