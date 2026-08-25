"""Scheduled Reports and Notification API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models import User, UserRole
from app.security import get_current_user, require_role

router = APIRouter(prefix="/api/reports", tags=["scheduled-reports"])


class ScheduledReportCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    report_type: str = Field(..., pattern="^(weekly_summary|monthly_portfolio|risk_assessment|custom)$")
    schedule: str = Field(..., pattern="^(daily|weekly|monthly)$")
    recipients: list[str] = Field(..., min_length=1)
    portfolio_id: Optional[str] = None


@router.get("/scheduled")
def list_scheduled_reports(user: User = Depends(get_current_user)):
    """List all scheduled reports for the user's org."""
    from app.scheduled_reports import list_scheduled_reports as list_reports
    reports = list_reports(org_id=user.org_id)
    return {"reports": [
        {
            "id": r.id, "name": r.name, "report_type": r.report_type,
            "schedule": r.schedule, "recipients": r.recipients,
            "enabled": r.enabled, "last_run": r.last_run,
            "next_run": r.next_run, "created_at": r.created_at,
        }
        for r in reports
    ], "total": len(reports)}


@router.post("/scheduled", status_code=201)
def create_scheduled_report(
    data: ScheduledReportCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a scheduled report. Admin only."""
    from app.scheduled_reports import create_scheduled_report as create_report
    report = create_report(
        name=data.name,
        report_type=data.report_type,
        schedule=data.schedule,
        recipients=data.recipients,
        portfolio_id=data.portfolio_id,
        org_id=user.org_id,
        created_by=user.id,
    )
    return {
        "id": report.id, "name": report.name, "report_type": report.report_type,
        "schedule": report.schedule, "recipients": report.recipients,
        "enabled": report.enabled, "created_at": report.created_at,
    }


@router.delete("/scheduled/{report_id}", status_code=204)
def delete_scheduled_report(
    report_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete a scheduled report. Admin only."""
    from app.scheduled_reports import delete_scheduled_report as delete_report
    if not delete_report(report_id):
        raise HTTPException(status_code=404, detail="Report not found")


# ── Email Preview ────────────────────────────────────────────────────────

@router.get("/templates")
def list_email_templates():
    """List available email templates."""
    from app.scheduled_reports import TEMPLATES
    return {"templates": [
        {"name": t.name, "subject": t.subject}
        for t in TEMPLATES.values()
    ]}


@router.post("/preview")
def preview_email(
    template_name: str,
    variables: dict = {},
):
    """Preview a rendered email template."""
    from app.scheduled_reports import render_template
    try:
        rendered = render_template(template_name, variables)
        return rendered
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Notification Rules ──────────────────────────────────────────────────

notification_router = APIRouter(prefix="/api/notifications/rules", tags=["notification-rules"])


class NotificationRuleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    trigger_type: str = Field(..., pattern="^(rate_threshold|optimization_complete|risk_change|schedule)$")
    conditions: dict = Field(default_factory=dict)
    channels: list[str] = Field(default=["in_app"])
    recipients: list[str] = Field(default_factory=list)


@notification_router.get("")
def list_rules(user: User = Depends(get_current_user)):
    """List notification rules."""
    from app.scheduled_reports import list_notification_rules
    rules = list_notification_rules()
    return {"rules": [
        {
            "id": r.id, "name": r.name, "trigger_type": r.trigger_type,
            "conditions": r.conditions, "channels": r.channels,
            "recipients": r.recipients, "enabled": r.enabled,
        }
        for r in rules
    ]}


@notification_router.post("", status_code=201)
def create_rule(
    data: NotificationRuleCreate,
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Create a notification rule. Admin only."""
    from app.scheduled_reports import create_notification_rule
    rule = create_notification_rule(
        name=data.name,
        trigger_type=data.trigger_type,
        conditions=data.conditions,
        channels=data.channels,
        recipients=data.recipients,
    )
    return {
        "id": rule.id, "name": rule.name, "trigger_type": rule.trigger_type,
        "conditions": rule.conditions, "channels": rule.channels,
        "recipients": rule.recipients, "enabled": rule.enabled,
    }


@notification_router.delete("/{rule_id}", status_code=204)
def delete_rule(
    rule_id: str,
    user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Delete a notification rule. Admin only."""
    from app.scheduled_reports import delete_notification_rule
    if not delete_notification_rule(rule_id):
        raise HTTPException(status_code=404, detail="Rule not found")
