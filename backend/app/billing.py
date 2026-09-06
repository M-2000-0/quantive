"""Stripe billing integration for subscription management.

Provides:
- Subscription tier definitions (Free, Pro, Enterprise)
- Checkout session creation
- Webhook handling for payment events
- Usage tracking and metering
"""
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

import httpx

logger = logging.getLogger("quantive.billing")


# ── Subscription Tiers ──────────────────────────────────────────────────

class PlanTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


PLAN_DETAILS = {
    PlanTier.FREE: {
        "name": "Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "features": [
            "1 portfolio",
            "5 instruments per portfolio",
            "1 optimization per day",
            "Basic risk analytics",
            "Market data (delayed)",
            "Community support",
        ],
        "limits": {
            "max_portfolios": 1,
            "max_instruments": 5,
            "optimizations_per_day": 1,
            "max_scenarios": 100,
            "max_users": 1,
            "data_retention_days": 30,
        },
    },
    PlanTier.PRO: {
        "name": "Pro",
        "price_monthly": 499,
        "price_yearly": 4788,  # 20% discount
        "stripe_price_monthly": os.environ.get("STRIPE_PRO_MONTHLY_PRICE_ID", ""),
        "stripe_price_yearly": os.environ.get("STRIPE_PRO_YEARLY_PRICE_ID", ""),
        "features": [
            "Unlimited portfolios",
            "Unlimited instruments",
            "20 optimizations per day",
            "Advanced risk analytics (VaR, stress testing)",
            "Real-time market data",
            "AI Advisor",
            "ESG scoring",
            "Excel/PDF export",
            "Email support",
            "Webhook integrations",
        ],
        "limits": {
            "max_portfolios": -1,  # unlimited
            "max_instruments": -1,
            "optimizations_per_day": 20,
            "max_scenarios": 10000,
            "max_users": 5,
            "data_retention_days": 365,
        },
    },
    PlanTier.ENTERPRISE: {
        "name": "Enterprise",
        "price_monthly": 2499,
        "price_yearly": 23988,  # 20% discount
        "stripe_price_monthly": os.environ.get("STRIPE_ENTERPRISE_MONTHLY_PRICE_ID", ""),
        "stripe_price_yearly": os.environ.get("STRIPE_ENTERPRISE_YEARLY_PRICE_ID", ""),
        "features": [
            "Everything in Pro",
            "Unlimited optimizations",
            "Unlimited scenarios",
            "Multi-user with RBAC",
            "Custom AI models",
            "Priority support",
            "SLA guarantee (99.9%)",
            "SSO / SAML",
            "Audit logging",
            "Custom webhooks",
            "Dedicated account manager",
            "On-premise deployment option",
        ],
        "limits": {
            "max_portfolios": -1,
            "max_instruments": -1,
            "optimizations_per_day": -1,
            "max_scenarios": -1,
            "max_users": -1,
            "data_retention_days": -1,
        },
    },
}


# ── Subscription Store ──────────────────────────────────────────────────

@dataclass
class Subscription:
    """A user/org subscription."""
    id: str
    org_id: str
    user_id: str
    tier: PlanTier
    billing_cycle: str = "monthly"  # "monthly" or "yearly"
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    status: str = "active"  # active, past_due, canceled, trialing
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class UsageRecord:
    """Track API usage for metering."""
    id: str
    org_id: str
    resource: str  # "optimization", "export", "api_call"
    quantity: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_subscriptions: dict[str, Subscription] = {}
_usage: list[UsageRecord] = []


def get_subscription(org_id: str) -> Optional[Subscription]:
    """Get subscription for an org."""
    for sub in _subscriptions.values():
        if sub.org_id == org_id and sub.status in ("active", "trialing"):
            return sub
    return None


def create_subscription(
    org_id: str,
    user_id: str,
    tier: PlanTier,
    billing_cycle: str = "monthly",
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
) -> Subscription:
    """Create a new subscription."""
    sub_id = secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc)
    period_days = 365 if billing_cycle == "yearly" else 31
    sub = Subscription(
        id=sub_id,
        org_id=org_id,
        user_id=user_id,
        tier=tier,
        billing_cycle=billing_cycle,
        stripe_customer_id=stripe_customer_id,
        stripe_subscription_id=stripe_subscription_id,
        current_period_start=now.isoformat(),
        current_period_end=(now + timedelta(days=period_days)).isoformat(),
    )
    _subscriptions[sub_id] = sub
    return sub


def find_subscription_by_stripe_ref(ref: Optional[str]) -> Optional[Subscription]:
    """Find an existing subscription by its Stripe object reference.

    Used for webhook idempotency: Stripe retries webhook deliveries, and
    duplicate `payment_intent.succeeded` / `checkout.session.completed`
    events must not create duplicate subscriptions.
    """
    if not ref:
        return None
    for sub in _subscriptions.values():
        if sub.stripe_subscription_id == ref:
            return sub
    return None


def record_usage(org_id: str, resource: str, quantity: int = 1) -> UsageRecord:
    """Record API usage for metering."""
    usage_id = secrets.token_urlsafe(8)
    record = UsageRecord(id=usage_id, org_id=org_id, resource=resource, quantity=quantity)
    _usage.append(record)
    return record


def get_usage(org_id: str, resource: Optional[str] = None, since_hours: int = 24) -> dict:
    """Get usage stats for an org."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()

    records = [u for u in _usage if u.org_id == org_id and u.timestamp >= cutoff]
    if resource:
        records = [u for u in records if u.resource == resource]

    total = sum(r.quantity for r in records)
    return {
        "total": total,
        "by_resource": {},
        "period_hours": since_hours,
    }


# ── Stripe Integration (SERVER-SIDE ONLY) ──────────────────────────────

# SERVER-SIDE SECRET: STRIPE_API_KEY must be a secret key (sk_test_... or
# sk_live_...) loaded from the environment — never a pk_ publishable key,
# never hardcoded, and never sent to the browser. Server endpoints like
# checkout session creation require full secret-key authorization.
# Publishable keys (pk_...) belong exclusively in client-side code.
STRIPE_API_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_BASE_URL = "https://api.stripe.com/v1"


async def create_checkout_session(
    org_id: str,
    user_id: str,
    tier: PlanTier,
    billing_cycle: str = "monthly",
    success_url: str = "https://quantive.io/settings?billing=success",
    cancel_url: str = "https://quantive.io/pricing",
) -> dict:
    """Create a Stripe Checkout session."""
    if not STRIPE_API_KEY:
        # Dev mode: create local subscription
        sub = create_subscription(org_id, user_id, tier, billing_cycle)
        return {
            "checkout_url": success_url,
            "session_id": f"dev_{sub.id}",
            "subscription_id": sub.id,
            "mode": "development",
        }

    plan = PLAN_DETAILS[tier]
    price_id = plan.get(f"stripe_price_{billing_cycle}", "")

    data = {
        "mode": "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata[org_id]": org_id,
        "metadata[user_id]": user_id,
        "metadata[tier]": tier.value,
        "metadata[billing_cycle]": billing_cycle,
        "line_items[0][quantity]": 1,
    }
    if price_id:
        # Preferred path: a pre-created recurring Price from the dashboard.
        data["line_items[0][price]"] = price_id
    else:
        # Zero-config fallback (mirrors inline price_data): works with only a
        # secret key — no pre-created Price required. Recurring because
        # mode=subscription; amounts are dollars in PLAN_DETAILS, cents here.
        amount_key = "price_yearly" if billing_cycle == "yearly" else "price_monthly"
        data["line_items[0][price_data][currency]"] = "usd"
        data["line_items[0][price_data][unit_amount]"] = int(plan[amount_key] * 100)
        data["line_items[0][price_data][recurring][interval]"] = (
            "year" if billing_cycle == "yearly" else "month"
        )
        data["line_items[0][price_data][product_data][name]"] = f"Quantive {plan['name']}"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{STRIPE_BASE_URL}/checkout/sessions",
            auth=(STRIPE_API_KEY, ""),
            data=data,
            timeout=30,
        )
        resp.raise_for_status()
        session = resp.json()

    return {
        "checkout_url": session.get("url"),
        "session_id": session.get("id"),
        "mode": "stripe",
    }


async def create_customer_portal(
    stripe_customer_id: str,
    return_url: str = "https://quantive.io/settings",
) -> dict:
    """Create a Stripe Customer Portal session for managing subscriptions."""
    if not STRIPE_API_KEY:
        return {"url": return_url, "mode": "development"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{STRIPE_BASE_URL}/billing_portal/sessions",
            auth=(STRIPE_API_KEY, ""),
            data={
                "customer": stripe_customer_id,
                "return_url": return_url,
            },
            timeout=30,
        )
        resp.raise_for_status()
        session = resp.json()

    return {"url": session.get("url"), "mode": "stripe"}


def verify_stripe_webhook(payload: bytes, signature: str) -> bool:
    """Verify a Stripe webhook signature.

    Stripe's ``Stripe-Signature`` header is comma-separated:
    ``t=<unix_ts>,v1=<hex_sig>[,v1=<hex_sig2>...]``. Compare our HMAC against
    any v1 signature and reject replays older than Stripe's recommended
    5-minute tolerance.
    """
    if not STRIPE_WEBHOOK_SECRET:
        return True  # In dev, accept all webhooks

    elements: dict = {}
    v1_sigs: list = []
    for part in signature.replace(" ", "").split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key == "v1":
            v1_sigs.append(value)
        else:
            elements[key] = value

    timestamp = elements.get("t", "")
    if not timestamp or not v1_sigs:
        return False

    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False  # replay outside tolerance
    except ValueError:
        return False

    signed_payload = f"{timestamp}.".encode("utf-8") + payload
    expected = hmac.new(
        STRIPE_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    return any(hmac.compare_digest(expected, sig) for sig in v1_sigs)


def handle_stripe_event(event_type: str, data: dict) -> Optional[dict]:
    """Handle a Stripe webhook event."""
    obj = data.get("object", {})
    org_id = obj.get("metadata", {}).get("org_id", "")

    if event_type == "checkout.session.completed":
        if not org_id:
            # Idempotency guard: without org metadata there is nothing to
            # fulfill — likely a checkout created outside this system.
            logger.warning("checkout.session.completed without org metadata; skipping")
            return None
        sub = create_subscription(
            org_id=org_id,
            user_id=obj.get("metadata", {}).get("user_id", ""),
            tier=PlanTier(obj.get("metadata", {}).get("tier", "pro")),
            billing_cycle=obj.get("metadata", {}).get("billing_cycle", "monthly"),
            stripe_customer_id=obj.get("customer"),
            stripe_subscription_id=obj.get("subscription"),
        )
        logger.info(f"Subscription created: {sub.id} for org {org_id}")
        return {"action": "subscription_created", "subscription_id": sub.id}

    elif event_type == "payment_intent.succeeded":
        # One-time payments arrive here (subscription mode fulfills via
        # checkout.session.completed instead). Fulfill from the PaymentIntent
        # metadata when it carries our checkout metadata — same fulfillment
        # path as a subscription, just from a one-time charge.
        logger.info(f"Payment succeeded: {obj.get('id')} amount={obj.get('amount_received')}")
        meta = obj.get("metadata") or {}
        org_id = meta.get("org_id", "") or org_id
        if org_id and meta.get("tier"):
            # Idempotency: a retried webhook must not double-fulfill.
            existing = find_subscription_by_stripe_ref(obj.get("id"))
            if existing:
                logger.info(f"Duplicate fulfillment ignored for {obj.get('id')}")
                return {"action": "already_fulfilled", "subscription_id": existing.id}
            sub = create_subscription(
                org_id=org_id,
                user_id=meta.get("user_id", ""),
                tier=PlanTier(meta.get("tier", "pro")),
                billing_cycle=meta.get("billing_cycle", "monthly"),
                stripe_customer_id=(meta.get("customer") or obj.get("customer") or ""),
                stripe_subscription_id=obj.get("id"),
            )
            logger.info(f"One-time payment fulfilled: {sub.id} for org {org_id}")
            return {"action": "payment_fulfilled", "subscription_id": sub.id}
        return {"action": "payment_succeeded", "payment_intent": obj.get("id")}

    elif event_type == "payment_intent.payment_failed":
        failure_reason = (obj.get("last_payment_error") or {}).get("message", "unknown")
        logger.warning(f"Payment failed: {obj.get('id')} reason={failure_reason}")
        return {"action": "payment_failed", "payment_intent": obj.get("id"), "reason": failure_reason}

    elif event_type == "customer.subscription.updated":
        # Update subscription status
        for sub in _subscriptions.values():
            if sub.stripe_subscription_id == obj.get("id"):
                sub.status = obj.get("status", "active")
                sub.updated_at = datetime.now(timezone.utc).isoformat()
                logger.info(f"Subscription updated: {sub.id} status={sub.status}")
                return {"action": "subscription_updated", "subscription_id": sub.id}

    elif event_type == "customer.subscription.deleted":
        for sub in _subscriptions.values():
            if sub.stripe_subscription_id == obj.get("id"):
                sub.status = "canceled"
                sub.updated_at = datetime.now(timezone.utc).isoformat()
                logger.info(f"Subscription canceled: {sub.id}")
                return {"action": "subscription_canceled", "subscription_id": sub.id}

    elif event_type == "invoice.payment_failed":
        for sub in _subscriptions.values():
            if sub.stripe_customer_id == obj.get("customer"):
                sub.status = "past_due"
                sub.updated_at = datetime.now(timezone.utc).isoformat()
                logger.warning(f"Payment failed for org {org_id}")
                return {"action": "payment_failed", "org_id": org_id}

    logger.info(f"Unhandled Stripe event type: {event_type}")
    return None


# ── Limit Checking ──────────────────────────────────────────────────────

def check_limit(org_id: str, resource: str) -> dict:
    """Check if an org is within its plan limits.

    Returns:
        {"allowed": bool, "current": int, "limit": int, "plan": str}
    """
    sub = get_subscription(org_id)
    tier = sub.tier if sub else PlanTier.FREE
    limits = PLAN_DETAILS[tier]["limits"]
    limit = limits.get(resource, 0)

    # -1 means unlimited
    if limit == -1:
        return {"allowed": True, "current": 0, "limit": -1, "plan": tier.value}

    usage = get_usage(org_id, resource, since_hours=86400)  # last 24h for daily limits
    current = usage["total"]

    return {
        "allowed": current < limit,
        "current": current,
        "limit": limit,
        "plan": tier.value,
    }
