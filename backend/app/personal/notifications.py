"""Tax notification system — alerts for time-sensitive financial actions.

Generates notifications for estimated tax deadlines, year-end planning,
withholding adjustments, and deduction opportunities.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta, date
from typing import Optional

from sqlalchemy.orm import Session

from app.personal.models import ComplianceAlert, PersonalProfile, ProfileFact, Transaction
from app.personal.compliance import analyze_withholding


# Notification types with templates
NOTIFICATION_TEMPLATES = {
    "estimated_tax_q1": {
        "title": "Q1 Estimated Tax Due",
        "message": "Your Q1 estimated tax payment of ${amount} is due on April 15.",
        "days_before": [14, 7, 3, 1],
        "severity": "critical",
    },
    "estimated_tax_q2": {
        "title": "Q2 Estimated Tax Due",
        "message": "Your Q2 estimated tax payment of ${amount} is due on June 15.",
        "days_before": [14, 7, 3, 1],
        "severity": "critical",
    },
    "estimated_tax_q3": {
        "title": "Q3 Estimated Tax Due",
        "message": "Your Q3 estimated tax payment of ${amount} is due on September 15.",
        "days_before": [14, 7, 3, 1],
        "severity": "critical",
    },
    "estimated_tax_q4": {
        "title": "Q4 Estimated Tax Due",
        "message": "Your Q4 estimated tax payment of ${amount} is due on January 15.",
        "days_before": [14, 7, 3, 1],
        "severity": "critical",
    },
    "withholding_adjustment": {
        "title": "Withholding Adjustment Available",
        "message": "Your withholding is ${direction} by ${amount}. Adjust your W-4 to improve cash flow.",
        "days_before": [0],
        "severity": "info",
    },
    "year_end_planning": {
        "title": "Year-End Tax Planning Window",
        "message": "You have ${days} days left to optimize your ${year} taxes. ${action_count} opportunities available.",
        "days_before": [60, 30, 14, 7],
        "severity": "warning",
    },
    "tax_sprint_launch": {
        "title": "Tax Sprint Mode Activated",
        "message": "November 1st — Tax Sprint begins! ${action_count} moves available, ${total_potential} in potential savings.",
        "days_before": [0],
        "severity": "info",
    },
    "deduction_detected": {
        "title": "New Deduction Detected",
        "message": "We found a potential ${category} deduction of ${amount}. Estimated savings: ${savings}.",
        "days_before": [0],
        "severity": "info",
    },
    "filing_deadline": {
        "title": "Tax Filing Deadline Approaching",
        "message": "Your tax filing is due on ${deadline}. ${status}",
        "days_before": [30, 14, 7, 3, 1],
        "severity": "critical",
    },
    "safe_harbor_check": {
        "title": "Safe Harbor Payment Check",
        "message": "To avoid underpayment penalties, ensure you've paid at least ${amount} by year-end.",
        "days_before": [60, 30, 14],
        "severity": "warning",
    },
}

# Estimated tax deadlines by quarter
QUARTERLY_DEADLINES = [
    {"quarter": "Q1", "month": 4, "day": 15, "template_key": "estimated_tax_q1"},
    {"quarter": "Q2", "month": 6, "day": 15, "template_key": "estimated_tax_q2"},
    {"quarter": "Q3", "month": 9, "day": 15, "template_key": "estimated_tax_q3"},
    {"quarter": "Q4", "month": 1, "day": 15, "template_key": "estimated_tax_q4", "next_year": True},
]

# Filing deadlines
FILING_DEADLINES = [
    {"label": "Individual return", "month": 4, "day": 15},
    {"label": "S-Corp / Partnership", "month": 3, "day": 15},
    {"label": "Extension deadline", "month": 10, "day": 15},
]

# Year-end planning windows
YEAR_END_WINDOWS = [
    {"days_before": 60, "label": "Planning window opens"},
    {"days_before": 30, "label": "One month remaining"},
    {"days_before": 14, "label": "Two weeks left"},
    {"days_before": 7, "label": "Final week"},
]


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_facts(user_id: str, db: Session) -> dict:
    """Load all profile facts into a dict."""
    facts: dict[str, str] = {}
    for f in db.query(ProfileFact).filter(ProfileFact.user_id == user_id).all():
        facts[f.key] = f.value
    return facts


def _estimate_quarterly_payment(user_id: str, db: Session) -> int:
    """Estimate quarterly payment amount from withholding analysis."""
    try:
        analysis = analyze_withholding(user_id, db)
        return analysis.get("quarterly_payment_needed", 0)
    except Exception:
        return 0


def _format_cents(amount_cents: int) -> str:
    """Format cents as a dollar string."""
    return f"{amount_cents / 100:,.0f}"


def _notif_id() -> str:
    return f"notif_{uuid.uuid4().hex[:12]}"


def check_deadlines(user_id: str, db: Session, tax_year: int = 2026) -> list[dict]:
    """Check all upcoming deadlines and return those within notification window.

    Returns:
        List of deadline dicts with type, date, severity, and message.
    """
    today = _today()
    now = _now()
    facts = _get_facts(user_id, db)
    quarterly_payment = _estimate_quarterly_payment(user_id, db)
    deadlines: list[dict] = []

    # ── Estimated Tax Deadlines ───────────────────────────────────────
    for q in QUARTERLY_DEADLINES:
        year = tax_year + 1 if q.get("next_year") else tax_year
        deadline = date(year, q["month"], q["day"])
        days_until = (deadline - today).days

        if days_until < 0:
            continue

        template = NOTIFICATION_TEMPLATES[q["template_key"]]
        for trigger_days in template["days_before"]:
            if days_until <= trigger_days:
                message = template["message"].replace("${amount}", _format_cents(quarterly_payment))
                deadlines.append({
                    "type": q["template_key"],
                    "date": deadline.isoformat(),
                    "days_until": days_until,
                    "severity": template["severity"],
                    "title": template["title"],
                    "message": message,
                    "quarter": q["quarter"],
                })
                break

    # ── Filing Deadline ───────────────────────────────────────────────
    for fd in FILING_DEADLINES:
        deadline = date(tax_year + 1, fd["month"], fd["day"])
        days_until = (deadline - today).days

        if days_until < 0:
            continue

        template = NOTIFICATION_TEMPLATES["filing_deadline"]
        for trigger_days in template["days_before"]:
            if days_until <= trigger_days:
                status_msg = "File soon to avoid late filing penalties."
                if days_until <= 3:
                    status_msg = "URGENT: File immediately or request an extension."
                message = template["message"].replace("${deadline}", deadline.strftime("%B %d, %Y"))
                message = message.replace("${status}", status_msg)
                deadlines.append({
                    "type": "filing_deadline",
                    "date": deadline.isoformat(),
                    "days_until": days_until,
                    "severity": template["severity"],
                    "title": f"Filing Deadline — {fd['label']}",
                    "message": message,
                })
                break

    # ── Year-End Planning Windows ─────────────────────────────────────
    year_end = date(tax_year, 12, 31)
    days_to_year_end = (year_end - today).days

    if 0 <= days_to_year_end <= 60:
        # Get opportunity count from sprint
        from app.personal.tax_sprint import get_sprint_actions
        try:
            actions = get_sprint_actions(user_id, db, tax_year)
            action_count = len(actions)
            total_savings = sum(a["estimated_savings"] for a in actions)
        except Exception:
            action_count = 0
            total_savings = 0

        template = NOTIFICATION_TEMPLATES["year_end_planning"]
        for trigger_days in template["days_before"]:
            if days_to_year_end <= trigger_days:
                message = template["message"]
                message = message.replace("${days}", str(days_to_year_end))
                message = message.replace("${year}", str(tax_year))
                message = message.replace("${action_count}", str(action_count))
                deadlines.append({
                    "type": "year_end_planning",
                    "date": year_end.isoformat(),
                    "days_until": days_to_year_end,
                    "severity": template["severity"],
                    "title": template["title"],
                    "message": message,
                })
                break

    # ── Tax Sprint Launch ─────────────────────────────────────────────
    sprint_start = date(tax_year, 11, 1)
    if today == sprint_start:
        from app.personal.tax_sprint import get_sprint_actions
        try:
            actions = get_sprint_actions(user_id, db, tax_year)
            action_count = len(actions)
            total_savings = sum(a["estimated_savings"] for a in actions)
        except Exception:
            action_count = 0
            total_savings = 0

        template = NOTIFICATION_TEMPLATES["tax_sprint_launch"]
        message = template["message"]
        message = message.replace("${action_count}", str(action_count))
        message = message.replace("${total_potential}", _format_cents(total_savings))
        deadlines.append({
            "type": "tax_sprint_launch",
            "date": sprint_start.isoformat(),
            "days_until": 0,
            "severity": template["severity"],
            "title": template["title"],
            "message": message,
        })

    # ── Safe Harbor Check ─────────────────────────────────────────────
    if facts.get("income_sources") and today.month >= 9:
        withholding = analyze_withholding(user_id, db)
        shortfall = withholding.get("shortfall", 0)
        if shortfall > 1000_00:
            template = NOTIFICATION_TEMPLATES["safe_harbor_check"]
            for trigger_days in template["days_before"]:
                days_to_ye = (year_end - today).days
                if days_to_ye <= trigger_days:
                    message = template["message"].replace(
                        "${amount}", _format_cents(shortfall)
                    )
                    deadlines.append({
                        "type": "safe_harbor_check",
                        "date": year_end.isoformat(),
                        "days_until": days_to_ye,
                        "severity": template["severity"],
                        "title": template["title"],
                        "message": message,
                    })
                    break

    # Deduplicate by type
    seen = set()
    unique: list[dict] = []
    for d in deadlines:
        key = (d["type"], d["date"])
        if key not in seen:
            seen.add(key)
            unique.append(d)

    return unique


def generate_notifications(user_id: str, db: Session, tax_year: int = 2026) -> list[dict]:
    """Generate all active notifications for a user.

    Returns:
        List of notification dicts with id, type, title, message, severity,
        action_url, days_until, and created_at.
    """
    deadlines = check_deadlines(user_id, db, tax_year)
    now = _now()

    notifications: list[dict] = []

    for deadline in deadlines:
        # Map type to action URL
        action_urls = {
            "estimated_tax_q1": "/personal/compliance",
            "estimated_tax_q2": "/personal/compliance",
            "estimated_tax_q3": "/personal/compliance",
            "estimated_tax_q4": "/personal/compliance",
            "withholding_adjustment": "/personal/compliance",
            "year_end_planning": "/personal/sprint",
            "tax_sprint_launch": "/personal/sprint",
            "deduction_detected": "/personal/opportunities",
            "filing_deadline": "/personal/compliance",
            "safe_harbor_check": "/personal/compliance",
        }

        notifications.append({
            "id": _notif_id(),
            "type": deadline["type"],
            "title": deadline["title"],
            "message": deadline["message"],
            "severity": deadline["severity"],
            "action_url": action_urls.get(deadline["type"], "/personal/compliance"),
            "days_until": deadline["days_until"],
            "created_at": now.isoformat(),
        })

    # ── Deduction Detection Alerts ────────────────────────────────────
    today = _today()
    year_start = f"{today.year}-01-01"

    # Check for recent uncategorized transactions that might be deductions
    recent_txns = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= year_start,
        Transaction.tax_tag == "deductible",
        Transaction.excluded == False,
    ).all()

    if recent_txns:
        # Group by category for summary
        categories: dict[str, int] = {}
        for t in recent_txns:
            cat = t.category or "general"
            categories[cat] = categories.get(cat, 0) + t.amount

        for cat, total in categories.items():
            if total > 50_00:  # Only alert for $50+ deductions
                facts = _get_facts(user_id, db)
                # Rough savings estimate based on marginal rate
                marginal_rate = 0.22
                try:
                    analysis = analyze_withholding(user_id, db)
                    marginal_rate = analysis.get("marginal_rate", 0.22)
                except Exception:
                    pass

                savings = int(total * marginal_rate)
                template = NOTIFICATION_TEMPLATES["deduction_detected"]
                message = template["message"]
                message = message.replace("${category}", cat)
                message = message.replace("${amount}", _format_cents(total))
                message = message.replace("${savings}", _format_cents(savings))

                notifications.append({
                    "id": _notif_id(),
                    "type": "deduction_detected",
                    "title": template["title"],
                    "message": message,
                    "severity": "info",
                    "action_url": "/personal/transactions",
                    "days_until": 0,
                    "created_at": now.isoformat(),
                })

    return notifications


def get_notification_summary(user_id: str, db: Session) -> dict:
    """Get a summary of notification status for the user.

    Returns:
        Dict with unread_count, critical_count, next_deadline, and recent_notifications.
    """
    notifications = generate_notifications(user_id, db)

    # Find next deadline
    upcoming = [n for n in notifications if n["days_until"] > 0]
    upcoming.sort(key=lambda n: n["days_until"])
    next_deadline = None
    if upcoming:
        nxt = upcoming[0]
        next_deadline = {
            "type": nxt["type"],
            "date": nxt["message"].split(" on ")[-1].rstrip(".") if " on " in nxt["message"] else "",
            "days": nxt["days_until"],
        }

    # Recent notifications (all generated ones)
    recent = sorted(notifications, key=lambda n: n["days_until"])[:10]

    return {
        "unread_count": len(notifications),
        "critical_count": sum(1 for n in notifications if n["severity"] == "critical"),
        "next_deadline": next_deadline,
        "recent_notifications": recent,
    }


def mark_notification_read(notification_id: str, user_id: str, db: Session) -> bool:
    """Mark a notification as read/acknowledged.

    In this implementation, notifications are generated on-the-fly from
    deadline calculations. This function creates a ComplianceAlert with
    acknowledged=True as a record that the user has seen the notification.

    Args:
        notification_id: The notification ID (notif_xxx).
        user_id: The user's ID.
        db: Database session.

    Returns:
        True if successfully marked, False if notification_id format is invalid.
    """
    if not notification_id.startswith("notif_"):
        return False

    # Extract the action type from the notification ID
    # Since notifications are ephemeral, record acknowledgment as a compliance alert
    alert = ComplianceAlert(
        user_id=user_id,
        alert_type="notification_acknowledged",
        severity="info",
        title=f"Notification acknowledged: {notification_id}",
        description=f"User acknowledged notification {notification_id}",
        acknowledged=True,
    )
    db.add(alert)
    db.commit()
    return True
