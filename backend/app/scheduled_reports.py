"""Scheduled Reports and Email Notification System.

Provides report scheduling, email templates, and notification delivery.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class EmailTemplate:
    """Email notification template."""
    name: str
    subject: str
    body_html: str
    body_text: str


# ── Email Templates ──────────────────────────────────────────────────────

TEMPLATES = {
    "optimization_complete": EmailTemplate(
        name="Optimization Complete",
        subject="✅ Optimization Complete: {job_name}",
        body_html="""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #1e40af; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 20px;">Quantive Optimization Complete</h1>
            </div>
            <div style="background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0; border-top: none;">
                <p>Your optimization <strong>{job_name}</strong> has completed successfully.</p>
                <div style="background: white; padding: 15px; border-radius: 6px; margin: 15px 0; border: 1px solid #e2e8f0;">
                    <p style="margin: 5px 0;"><strong>Status:</strong> ✅ Completed</p>
                    <p style="margin: 5px 0;"><strong>Strategies:</strong> {strategy_count}</p>
                    <p style="margin: 5px 0;"><strong>Scenarios:</strong> {scenario_count:,}</p>
                    <p style="margin: 5px 0;"><strong>Duration:</strong> {duration}</p>
                </div>
                <a href="{view_url}" style="display: inline-block; background: #1e40af; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">View Results →</a>
            </div>
        </div>
        """,
        body_text="Optimization '{job_name}' completed. {strategy_count} strategies found. View at {view_url}",
    ),
    "rate_alert": EmailTemplate(
        name="Rate Alert",
        subject="⚡ Rate Alert: {alert_type} — {rate_name} is now {rate_value}%",
        body_html="""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #f59e0b; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 20px;">⚡ Rate Alert</h1>
            </div>
            <div style="background: #fffbeb; padding: 20px; border: 1px solid #fde68a; border-top: none;">
                <p><strong>{rate_name}</strong> has moved to <strong>{rate_value}%</strong></p>
                <p>Previous: {previous_value}% | Change: {change_bps} bps</p>
                <p>This may affect your portfolio's debt service costs.</p>
            </div>
        </div>
        """,
        body_text="{rate_name} is now {rate_value}% (was {previous_value}%, change {change_bps} bps)",
    ),
    "weekly_summary": EmailTemplate(
        name="Weekly Summary",
        subject="📊 Weekly Portfolio Summary — {date}",
        body_html="""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #059669; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 20px;">📊 Weekly Summary</h1>
            </div>
            <div style="background: #f0fdf4; padding: 20px; border: 1px solid #bbf7d0; border-top: none;">
                <h2 style="margin-top: 0;">Portfolio Highlights</h2>
                <div style="background: white; padding: 15px; border-radius: 6px; border: 1px solid #e2e8f0;">
                    <p style="margin: 5px 0;"><strong>Total Principal:</strong> {total_principal}</p>
                    <p style="margin: 5px 0;"><strong>Weighted Coupon:</strong> {weighted_coupon}%</p>
                    <p style="margin: 5px 0;"><strong>Active Optimizations:</strong> {active_optimizations}</p>
                    <p style="margin: 5px 0;"><strong>Risk Score:</strong> {risk_score}/10</p>
                </div>
                <h3>Market Highlights</h3>
                <p>US 10Y: {us_10y}% | SOFR: {sofr}% | VIX: {vix}</p>
            </div>
        </div>
        """,
        body_text="Weekly Summary: Total Principal {total_principal}, Coupon {weighted_coupon}%, Risk {risk_score}/10",
    ),
    "password_reset": EmailTemplate(
        name="Password Reset",
        subject="🔐 Password Reset Request",
        body_html="""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #6366f1; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 20px;">Password Reset</h1>
            </div>
            <div style="background: #f5f3ff; padding: 20px; border: 1px solid #c4b5fd; border-top: none;">
                <p>You requested a password reset. Click below to set a new password:</p>
                <a href="{reset_url}" style="display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 15px 0;">Reset Password →</a>
                <p style="color: #6b7280; font-size: 12px;">This link expires in 30 minutes. If you didn't request this, ignore this email.</p>
            </div>
        </div>
        """,
        body_text="Password reset requested. Link: {reset_url} (expires in 30 minutes)",
    ),
    "report_scheduled": EmailTemplate(
        name="Scheduled Report Ready",
        subject="📄 Your scheduled report is ready: {report_name}",
        body_html="""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #0891b2; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 20px;">📄 Report Ready</h1>
            </div>
            <div style="background: #ecfeff; padding: 20px; border: 1px solid #a5f3fc; border-top: none;">
                <p>Your scheduled report <strong>{report_name}</strong> is ready for download.</p>
                <a href="{download_url}" style="display: inline-block; background: #0891b2; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 15px 0;">Download Report →</a>
            </div>
        </div>
        """,
        body_text="Your scheduled report '{report_name}' is ready. Download at {download_url}",
    ),
}


def render_template(template_name: str, variables: dict) -> dict:
    """Render an email template with variables.

    Returns:
        {"subject": str, "body_html": str, "body_text": str}
    """
    template = TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"Template '{template_name}' not found")

    return {
        "subject": template.subject.format(**variables),
        "body_html": template.body_html.format(**variables),
        "body_text": template.body_text.format(**variables),
    }


def generate_email_hash(email_content: dict) -> str:
    """Generate a unique hash for an email (for deduplication)."""
    content_str = json.dumps(email_content, sort_keys=True)
    return hashlib.sha256(content_str.encode()).hexdigest()[:16]


@dataclass
class ScheduledReport:
    """A scheduled report configuration."""
    id: str
    name: str
    report_type: str  # "weekly_summary", "monthly_portfolio", "risk_assessment"
    schedule: str  # "daily", "weekly", "monthly"
    recipients: list[str]
    portfolio_id: Optional[str] = None
    org_id: Optional[str] = None
    created_by: Optional[str] = None
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# In-memory store (swap for database in production)
_scheduled_reports: dict[str, ScheduledReport] = {}


def create_scheduled_report(
    name: str,
    report_type: str,
    schedule: str,
    recipients: list[str],
    portfolio_id: Optional[str] = None,
    org_id: Optional[str] = None,
    created_by: Optional[str] = None,
) -> ScheduledReport:
    """Create a new scheduled report."""
    import uuid
    report_id = str(uuid.uuid4())
    report = ScheduledReport(
        id=report_id,
        name=name,
        report_type=report_type,
        schedule=schedule,
        recipients=recipients,
        portfolio_id=portfolio_id,
        org_id=org_id,
        created_by=created_by,
    )
    _scheduled_reports[report_id] = report
    return report


def list_scheduled_reports(org_id: Optional[str] = None) -> list[ScheduledReport]:
    """List scheduled reports for an org."""
    reports = list(_scheduled_reports.values())
    if org_id:
        reports = [r for r in reports if r.org_id == org_id]
    return reports


def delete_scheduled_report(report_id: str) -> bool:
    """Delete a scheduled report."""
    if report_id in _scheduled_reports:
        del _scheduled_reports[report_id]
        return True
    return False


# ── Notification System ──────────────────────────────────────────────────

@dataclass
class NotificationRule:
    """A rule that triggers notifications."""
    id: str
    name: str
    trigger_type: str  # "rate_threshold", "optimization_complete", "risk_change", "schedule"
    conditions: dict
    channels: list[str]  # ["email", "in_app", "webhook"]
    recipients: list[str]
    enabled: bool = True


_notification_rules: dict[str, NotificationRule] = {}


def create_notification_rule(
    name: str,
    trigger_type: str,
    conditions: dict,
    channels: list[str],
    recipients: list[str],
) -> NotificationRule:
    """Create a notification rule."""
    import uuid
    rule = NotificationRule(
        id=str(uuid.uuid4()),
        name=name,
        trigger_type=trigger_type,
        conditions=conditions,
        channels=channels,
        recipients=recipients,
    )
    _notification_rules[rule.id] = rule
    return rule


def check_rate_alerts(rate_name: str, current_value: float, previous_value: float) -> list[dict]:
    """Check if any rate alert rules should fire."""
    alerts = []
    for rule in _notification_rules.values():
        if rule.trigger_type != "rate_threshold" or not rule.enabled:
            continue
        if rule.conditions.get("rate_name") != rate_name:
            continue
        threshold = rule.conditions.get("threshold_bps", 25)
        change_bps = abs(current_value - previous_value) * 100
        if change_bps >= threshold:
            alerts.append({
                "rule": rule,
                "rate_name": rate_name,
                "current_value": current_value,
                "previous_value": previous_value,
                "change_bps": change_bps,
            })
    return alerts


def list_notification_rules(org_id: Optional[str] = None) -> list[NotificationRule]:
    """List notification rules."""
    return list(_notification_rules.values())


def delete_notification_rule(rule_id: str) -> bool:
    """Delete a notification rule."""
    if rule_id in _notification_rules:
        del _notification_rules[rule_id]
        return True
    return False
