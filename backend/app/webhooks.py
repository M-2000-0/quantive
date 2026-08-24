"""Webhook system for event-driven notifications.

Provides:
- Event registry for supported webhook events
- Webhook delivery with exponential backoff retries
- Webhook management (CRUD, secret rotation, testing)
- Delivery tracking and logging
"""
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

import httpx

logger = logging.getLogger("quantive.webhooks")

# ── Event Registry ──────────────────────────────────────────────────────────

class WebhookEvent(str, Enum):
    """Supported webhook event types."""
    # Portfolio events
    PORTFOLIO_CREATED = "portfolio.created"
    PORTFOLIO_UPDATED = "portfolio.updated"
    PORTFOLIO_DELETED = "portfolio.deleted"
    PORTFOLIO_INSTRUMENT_ADDED = "portfolio.instrument.added"
    PORTFOLIO_INSTRUMENT_UPDATED = "portfolio.instrument.updated"
    PORTFOLIO_INSTRUMENT_DELETED = "portfolio.instrument.deleted"

    # Optimization events
    OPTIMIZATION_CREATED = "optimization.created"
    OPTIMIZATION_STARTED = "optimization.started"
    OPTIMIZATION_COMPLETED = "optimization.completed"
    OPTIMIZATION_FAILED = "optimization.failed"
    OPTIMIZATION_CANCELLED = "optimization.cancelled"

    # Report events
    REPORT_GENERATED = "report.generated"
    REPORT_FAILED = "report.failed"

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Organization events
    ORG_SETTINGS_UPDATED = "org.settings.updated"

    # System events
    SYSTEM_ALERT = "system.alert"
    SYSTEM_MAINTENANCE = "system.maintenance"


# Event descriptions for documentation
EVENT_DESCRIPTIONS = {
    WebhookEvent.PORTFOLIO_CREATED: "A new portfolio was created",
    WebhookEvent.PORTFOLIO_UPDATED: "A portfolio was updated",
    WebhookEvent.PORTFOLIO_DELETED: "A portfolio was deleted",
    WebhookEvent.PORTFOLIO_INSTRUMENT_ADDED: "An instrument was added to a portfolio",
    WebhookEvent.PORTFOLIO_INSTRUMENT_UPDATED: "An instrument was updated",
    WebhookEvent.PORTFOLIO_INSTRUMENT_DELETED: "An instrument was deleted",
    WebhookEvent.OPTIMIZATION_CREATED: "An optimization job was created",
    WebhookEvent.OPTIMIZATION_STARTED: "An optimization job started running",
    WebhookEvent.OPTIMIZATION_COMPLETED: "An optimization job completed successfully",
    WebhookEvent.OPTIMIZATION_FAILED: "An optimization job failed",
    WebhookEvent.OPTIMIZATION_CANCELLED: "An optimization job was cancelled",
    WebhookEvent.REPORT_GENERATED: "A report was generated successfully",
    WebhookEvent.REPORT_FAILED: "Report generation failed",
    WebhookEvent.USER_CREATED: "A new user was created",
    WebhookEvent.USER_UPDATED: "A user profile was updated",
    WebhookEvent.USER_DELETED: "A user was deleted",
    WebhookEvent.ORG_SETTINGS_UPDATED: "Organization settings were updated",
    WebhookEvent.SYSTEM_ALERT: "A system alert was triggered",
    WebhookEvent.SYSTEM_MAINTENANCE: "System maintenance scheduled",
}


def get_all_events() -> list[dict]:
    """Get all supported events with descriptions."""
    return [
        {"event": event.value, "description": EVENT_DESCRIPTIONS.get(event, "")}
        for event in WebhookEvent
    ]


# ── Webhook Signing ─────────────────────────────────────────────────────────

def sign_payload(payload: str, secret: str) -> str:
    """Sign a webhook payload using HMAC-SHA256.

    Args:
        payload: JSON-serialized payload string
        secret: Webhook secret

    Returns:
        Hex-encoded HMAC signature
    """
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify a webhook signature.

    Args:
        payload: The raw request body
        signature: The X-Webhook-Signature header value
        secret: The webhook secret

    Returns:
        True if signature is valid
    """
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(signature, expected)


# ── Delivery Engine ─────────────────────────────────────────────────────────

# Retry configuration
MAX_RETRIES = 5
RETRY_DELAYS = [1, 5, 30, 300, 1800]  # seconds: 1s, 5s, 30s, 5m, 30m
TIMEOUT_SECONDS = 30


async def deliver_webhook(
    url: str,
    secret: str,
    event: str,
    payload: dict[str, Any],
    webhook_id: str,
) -> dict:
    """Deliver a webhook with retries and exponential backoff.

    Args:
        url: Target URL
        secret: Webhook secret for signing
        event: Event type
        payload: Event payload
        webhook_id: Webhook ID for tracking

    Returns:
        Delivery result dict with status, attempts, and timing info
    """
    body = json.dumps(payload, default=str)
    signature = sign_payload(body, secret)
    timestamp = datetime.now(timezone.utc).isoformat()

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-ID": webhook_id,
        "X-Webhook-Event": event,
        "X-Webhook-Signature": signature,
        "X-Webhook-Timestamp": timestamp,
        "User-Agent": "Quantive-Webhooks/1.0",
    }

    last_error = None
    status_code = None
    response_body = None
    attempts = 0

    for attempt in range(MAX_RETRIES + 1):
        attempts = attempt + 1
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    content=body,
                    headers=headers,
                    timeout=TIMEOUT_SECONDS,
                )
                status_code = response.status_code
                response_body = response.text[:2000]

                # 2xx status codes are considered successful
                if 200 <= response.status_code < 300:
                    logger.info(f"Webhook {webhook_id} delivered to {url} (attempt {attempts})")
                    return {
                        "success": True,
                        "status_code": status_code,
                        "response_body": response_body,
                        "attempts": attempts,
                    }

                last_error = f"HTTP {response.status_code}: {response_body[:200]}"

        except httpx.TimeoutException:
            last_error = f"Timeout after {TIMEOUT_SECONDS}s"
            logger.warning(f"Webhook {webhook_id} timeout (attempt {attempts})")
        except httpx.RequestError as e:
            last_error = str(e)[:200]
            logger.warning(f"Webhook {webhook_id} request error (attempt {attempts}): {e}")
        except Exception as e:
            last_error = str(e)[:200]
            logger.error(f"Webhook {webhook_id} unexpected error (attempt {attempts}): {e}")

        # Wait before retry (if not last attempt)
        if attempt < MAX_RETRIES:
            delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
            logger.info(f"Webhook {webhook_id} retrying in {delay}s (attempt {attempts + 1})")
            time.sleep(delay)

    logger.error(f"Webhook {webhook_id} failed after {attempts} attempts: {last_error}")
    return {
        "success": False,
        "status_code": status_code,
        "response_body": response_body,
        "error": last_error,
        "attempts": attempts,
    }


# ── In-Memory Webhook Store ─────────────────────────────────────────────────

class WebhookStore:
    """In-memory webhook store for development/testing.

    In production, this would use the database.
    """

    def __init__(self):
        self._webhooks: dict[str, dict] = {}
        self._deliveries: list[dict] = []

    def create_webhook(
        self,
        org_id: str,
        name: str,
        url: str,
        events: list[str],
        secret: Optional[str] = None,
    ) -> dict:
        """Create a new webhook."""
        webhook_id = secrets.token_urlsafe(16)
        if not secret:
            secret = secrets.token_hex(32)

        webhook = {
            "id": webhook_id,
            "org_id": org_id,
            "name": name,
            "url": url,
            "secret": secret,
            "events": events,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._webhooks[webhook_id] = webhook
        return webhook

    def get_webhook(self, webhook_id: str) -> Optional[dict]:
        return self._webhooks.get(webhook_id)

    def list_webhooks(self, org_id: str) -> list[dict]:
        return [w for w in self._webhooks.values() if w["org_id"] == org_id]

    def update_webhook(self, webhook_id: str, updates: dict) -> Optional[dict]:
        webhook = self._webhooks.get(webhook_id)
        if webhook:
            webhook.update(updates)
            webhook["updated_at"] = datetime.now(timezone.utc).isoformat()
        return webhook

    def delete_webhook(self, webhook_id: str) -> bool:
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            return True
        return False

    def record_delivery(self, delivery: dict):
        """Record a webhook delivery attempt."""
        self._deliveries.append(delivery)

    def get_deliveries(self, webhook_id: str, limit: int = 50) -> list[dict]:
        """Get delivery history for a webhook."""
        return [
            d for d in self._deliveries
            if d.get("webhook_id") == webhook_id
        ][-limit:]


# Singleton instance
_webhook_store: Optional[WebhookStore] = None


def get_webhook_store() -> WebhookStore:
    global _webhook_store
    if _webhook_store is None:
        _webhook_store = WebhookStore()
    return _webhook_store


# ── Event Dispatcher ────────────────────────────────────────────────────────

def dispatch_event(
    event: str,
    payload: dict[str, Any],
    org_id: Optional[str] = None,
):
    """Dispatch a webhook event to all matching webhooks.

    This is the main entry point for firing events.
    Call this from API endpoints when something happens.
    """
    store = get_webhook_store()

    # Find all active webhooks for this org that subscribe to this event
    webhooks = store.list_webhooks(org_id or "")
    matching = [
        w for w in webhooks
        if w["is_active"] and (event in w["events"] or "*" in w["events"])
    ]

    if not matching:
        return

    import asyncio

    for webhook in matching:
        delivery_id = secrets.token_urlsafe(16)
        full_payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "webhook_id": webhook["id"],
            "delivery_id": delivery_id,
            "data": payload,
        }

        # Attempt delivery
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule as a task if we're in an async context
                asyncio.create_task(_deliver_and_record(webhook, full_payload, delivery_id))
            else:
                result = loop.run_until_complete(
                    deliver_webhook(webhook["url"], webhook["secret"], event, full_payload, webhook["id"])
                )
                result["delivery_id"] = delivery_id
                store.record_delivery(result)
        except RuntimeError:
            # No event loop, run synchronously
            import threading
            def _run():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(
                        deliver_webhook(webhook["url"], webhook["secret"], event, full_payload, webhook["id"])
                    )
                    result["delivery_id"] = delivery_id
                    store.record_delivery(result)
                except Exception as e:
                    logger.error(f"Webhook delivery thread error: {e}")
                finally:
                    loop.close()

            thread = threading.Thread(target=_run, daemon=True)
            thread.start()


async def _deliver_and_record(webhook: dict, payload: dict, delivery_id: str):
    """Deliver webhook and record the result."""
    store = get_webhook_store()
    result = await deliver_webhook(
        webhook["url"], webhook["secret"], payload["event"], payload, webhook["id"]
    )
    result["delivery_id"] = delivery_id
    store.record_delivery(result)
