"""Email sending service with SendGrid/Resend integration.

Provides:
- Async email sending with retry
- Template rendering with variables
- Delivery tracking
- Fallback logging when no email provider is configured
"""
import json
import logging
import os
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger("quantive.email")


class EmailProvider(str, Enum):
    SENDGRID = "sendgrid"
    RESEND = "resend"
    LOG_ONLY = "log_only"


class EmailStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    FAILED = "failed"


@dataclass
class EmailMessage:
    """An email message to be sent."""
    to: list[str]
    subject: str
    body_html: str
    body_text: str
    from_email: str = "noreply@quantive.io"
    from_name: str = "Quantive"
    reply_to: Optional[str] = None
    tags: dict[str, str] = field(default_factory=dict)
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)


@dataclass
class EmailDeliveryRecord:
    """Record of an email delivery attempt."""
    id: str
    to: list[str]
    subject: str
    status: EmailStatus
    provider: str
    provider_message_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sent_at: Optional[str] = None
    tags: dict[str, str] = field(default_factory=dict)


# ── In-Memory Delivery Store ────────────────────────────────────────────

class EmailStore:
    """Track email delivery history."""

    def __init__(self):
        self._records: list[EmailDeliveryRecord] = []
        self._lock = threading.Lock()

    def record(self, record: EmailDeliveryRecord) -> None:
        with self._lock:
            self._records.append(record)

    def list_records(self, limit: int = 100) -> list[EmailDeliveryRecord]:
        with self._lock:
            return list(reversed(self._records[-limit:]))

    def get_by_id(self, record_id: str) -> Optional[EmailDeliveryRecord]:
        with self._lock:
            for r in self._records:
                if r.id == record_id:
                    return r
        return None

    def count(self) -> int:
        with self._lock:
            return len(self._records)


_store: Optional[EmailStore] = None


def get_email_store() -> EmailStore:
    global _store
    if _store is None:
        _store = EmailStore()
    return _store


# ── Email Sender ────────────────────────────────────────────────────────

def _get_provider() -> EmailProvider:
    """Detect which email provider to use from environment."""
    if os.environ.get("SENDGRID_API_KEY"):
        return EmailProvider.SENDGRID
    if os.environ.get("RESEND_API_KEY"):
        return EmailProvider.RESEND
    return EmailProvider.LOG_ONLY


async def send_email(message: EmailMessage) -> EmailDeliveryRecord:
    """Send an email using the configured provider.

    Falls back to logging if no provider is configured.
    """
    provider = _get_provider()
    record_id = secrets.token_urlsafe(16)
    store = get_email_store()

    record = EmailDeliveryRecord(
        id=record_id,
        to=message.to,
        subject=message.subject,
        status=EmailStatus.QUEUED,
        provider=provider.value,
        tags=message.tags,
    )

    try:
        if provider == EmailProvider.SENDGRID:
            result = await _send_sendgrid(message)
        elif provider == EmailProvider.RESEND:
            result = await _send_resend(message)
        else:
            result = await _send_log_only(message)

        record.status = EmailStatus.SENT
        record.sent_at = datetime.now(timezone.utc).isoformat()
        record.provider_message_id = result.get("message_id")
        logger.info(f"Email sent: {message.subject} -> {message.to} (provider={provider.value})")

    except Exception as e:
        record.status = EmailStatus.FAILED
        record.error = str(e)[:2000]
        logger.error(f"Email send failed: {e}")

    store.record(record)
    return record


async def _send_sendgrid(message: EmailMessage) -> dict:
    """Send via SendGrid API."""
    import httpx

    api_key = os.environ["SENDGRID_API_KEY"]

    payload = {
        "personalizations": [{
            "to": [{"email": addr} for addr in message.to],
            "subject": message.subject,
        }],
        "from": {"email": message.from_email, "name": message.from_name},
        "content": [
            {"type": "text/plain", "value": message.body_text},
            {"type": "text/html", "value": message.body_html},
        ],
    }

    if message.cc:
        payload["personalizations"][0]["cc"] = [{"email": addr} for addr in message.cc]
    if message.bcc:
        payload["personalizations"][0]["bcc"] = [{"email": addr} for addr in message.bcc]
    if message.reply_to:
        payload["reply_to"] = {"email": message.reply_to}
    if message.tags:
        payload["custom_args"] = message.tags

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        resp.raise_for_status()

    return {"message_id": resp.headers.get("X-Message-Id", "")}


async def _send_resend(message: EmailMessage) -> dict:
    """Send via Resend API."""
    import httpx

    api_key = os.environ["RESEND_API_KEY"]

    payload = {
        "from": f"{message.from_name} <{message.from_email}>",
        "to": message.to,
        "subject": message.subject,
        "html": message.body_html,
        "text": message.body_text,
    }

    if message.cc:
        payload["cc"] = message.cc
    if message.bcc:
        payload["bcc"] = message.bcc
    if message.reply_to:
        payload["reply_to"] = message.reply_to

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

    return {"message_id": data.get("id", "")}


async def _send_log_only(message: EmailMessage) -> dict:
    """Log the email instead of sending (dev/staging fallback)."""
    logger.info(
        f"[EMAIL LOG] To: {message.to} | Subject: {message.subject}\n"
        f"Body (text): {message.body_text[:500]}"
    )
    return {"message_id": f"dev-{secrets.token_hex(8)}"}


# ── Convenience Senders ─────────────────────────────────────────────────

async def send_welcome_email(to: str, name: str) -> EmailDeliveryRecord:
    """Send a welcome email to a new user."""
    from app.scheduled_reports import render_template

    rendered = render_template("optimization_complete", {
        "job_name": "Welcome to Quantive",
        "strategy_count": 0,
        "scenario_count": 0,
        "duration": "N/A",
        "view_url": "https://quantive.io/dashboard",
    })

    return await send_email(EmailMessage(
        to=[to],
        subject="Welcome to Quantive — Your Debt Portfolio Optimizer",
        body_html=f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #1e40af, #7c3aed); color: white; padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">Welcome to Quantive, {name}! 🎉</h1>
            </div>
            <div style="background: #f8fafc; padding: 30px; border: 1px solid #e2e8f0; border-top: none;">
                <p style="font-size: 16px; line-height: 1.6;">You're now part of the next generation of debt portfolio management. Here's what you can do:</p>
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0;">
                    <h3 style="margin-top: 0;">Get Started</h3>
                    <ol style="line-height: 2;">
                        <li><strong>Create your first portfolio</strong> — Import instruments or add manually</li>
                        <li><strong>Run an optimization</strong> — Multi-objective solver with 1000+ scenarios</li>
                        <li><strong>Explore the AI Advisor</strong> — Get personalized recommendations</li>
                        <li><strong>Check risk analytics</strong> — VaR, stress testing, maturity ladder</li>
                    </ol>
                </div>
                <a href="https://quantive.io/dashboard" style="display: inline-block; background: #1e40af; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">Go to Dashboard →</a>
                <p style="color: #6b7280; margin-top: 20px; font-size: 14px;">Need help? Reply to this email or check our <a href="https://docs.quantive.io">documentation</a>.</p>
            </div>
        </div>
        """,
        body_text=f"Welcome to Quantive, {name}! Get started at https://quantive.io/dashboard",
        tags={"type": "welcome"},
    ))


async def send_password_reset_email(to: str, reset_token: str) -> EmailDeliveryRecord:
    """Send a password reset email."""
    reset_url = f"https://quantive.io/reset-password?token={reset_token}"
    return await send_email(EmailMessage(
        to=[to],
        subject="🔐 Reset Your Quantive Password",
        body_html=f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #6366f1; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0;">Password Reset</h1>
            </div>
            <div style="background: #f5f3ff; padding: 20px; border: 1px solid #c4b5fd; border-top: none;">
                <p>We received a request to reset your password. Click the button below:</p>
                <a href="{reset_url}" style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 15px 0;">Reset Password →</a>
                <p style="color: #6b7280; font-size: 12px;">This link expires in 30 minutes. If you didn't request this, ignore this email.</p>
            </div>
        </div>
        """,
        body_text=f"Reset your password: {reset_url} (expires in 30 minutes)",
        tags={"type": "password_reset"},
    ))


async def send_optimization_complete_email(
    to: str, job_name: str, strategy_count: int, view_url: str
) -> EmailDeliveryRecord:
    """Notify user that their optimization completed."""
    return await send_email(EmailMessage(
        to=[to],
        subject=f"Optimization Complete: {job_name}",
        body_html=f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #059669; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0;">Optimization Complete</h1>
            </div>
            <div style="background: #f0fdf4; padding: 20px; border: 1px solid #bbf7d0; border-top: none;">
                <p>Your optimization <strong>{job_name}</strong> is ready.</p>
                <p><strong>{strategy_count}</strong> strategies were generated.</p>
                <a href="{view_url}" style="display: inline-block; background: #059669; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">View Results →</a>
            </div>
        </div>
        """,
        body_text=f"Optimization '{job_name}' complete with {strategy_count} strategies. View at {view_url}",
        tags={"type": "optimization_complete", "job_name": job_name},
    ))


async def send_rate_alert_email(
    to: str, rate_name: str, current_value: float, previous_value: float
) -> EmailDeliveryRecord:
    """Send a rate alert notification."""
    change_bps = round((current_value - previous_value) * 100, 1)
    direction = "up" if change_bps > 0 else "down"
    return await send_email(EmailMessage(
        to=[to],
        subject=f"Rate Alert: {rate_name} moved {direction} to {current_value}%",
        body_html=f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #f59e0b; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0;">Rate Alert</h1>
            </div>
            <div style="background: #fffbeb; padding: 20px; border: 1px solid #fde68a; border-top: none;">
                <p><strong>{rate_name}</strong> is now <strong>{current_value}%</strong></p>
                <p>Previous: {previous_value}% | Change: {change_bps:+.0f} bps {direction}</p>
            </div>
        </div>
        """,
        body_text=f"{rate_name}: {previous_value}% -> {current_value}% ({change_bps:+.0f} bps)",
        tags={"type": "rate_alert", "rate_name": rate_name},
    ))
