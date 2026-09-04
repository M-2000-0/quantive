"""Demo tracking service — manages demo requests, scheduling, and outcomes."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.management.demo")

# Demo outcome statuses
DEMO_STATUSES = ["requested", "scheduled", "completed", "converted", "lost", "no_show"]


def get_demo_pipeline(db: Session, org_id: str) -> dict:
    """Get demo pipeline overview."""
    from app.models.support import SupportTicket

    demos = db.query(SupportTicket).filter(
        SupportTicket.org_id == org_id,
        SupportTicket.category == "feature_request",
    ).all()

    pipeline = {status: [] for status in DEMO_STATUSES}
    for d in demos:
        status = d.status if d.status in DEMO_STATUSES else "requested"
        pipeline[status].append({
            "id": d.id,
            "subject": d.subject,
            "description": d.description[:150],
            "priority": d.priority,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        })

    return {
        "total": len(demos),
        "by_status": {k: len(v) for k, v in pipeline.items()},
        "pipeline": pipeline,
    }


def create_demo_request(
    db: Session,
    org_id: str,
    user_id: str,
    subject: str,
    description: str,
    preferred_date: Optional[str] = None,
) -> dict:
    """Create a new demo request."""
    from app.models.support import SupportMessage, SupportTicket

    ticket = SupportTicket(
        org_id=org_id,
        user_id=user_id,
        subject=f"Demo Request: {subject}",
        description=description,
        category="feature_request",
        priority="medium",
        status="open",
    )
    db.add(ticket)
    db.flush()

    if preferred_date:
        msg = SupportMessage(
            ticket_id=ticket.id,
            user_id=user_id,
            content=f"Preferred demo date: {preferred_date}",
            is_internal=False,
        )
        db.add(msg)

    db.commit()
    db.refresh(ticket)

    return {
        "id": ticket.id,
        "subject": ticket.subject,
        "status": "requested",
    }


def update_demo_status(
    db: Session,
    ticket_id: str,
    org_id: str,
    new_status: str,
    notes: Optional[str] = None,
) -> dict:
    """Update demo status through the pipeline."""
    from app.models.support import SupportTicket

    if new_status not in DEMO_STATUSES:
        return {"error": f"Invalid status. Must be one of: {DEMO_STATUSES}"}

    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.org_id == org_id,
    ).first()

    if not ticket:
        return {"error": "Demo request not found"}

    ticket.status = new_status
    if notes:
        ticket.resolution_notes = notes
    db.commit()

    return {
        "id": ticket_id,
        "status": new_status,
        "notes": notes,
    }


def get_demo_analytics(db: Session, org_id: str) -> dict:
    """Get demo conversion analytics."""
    from app.models.support import SupportTicket

    demos = db.query(SupportTicket).filter(
        SupportTicket.org_id == org_id,
        SupportTicket.category == "feature_request",
    ).all()

    total = len(demos)
    completed = sum(1 for d in demos if d.status == "completed")
    converted = sum(1 for d in demos if d.status == "converted")
    lost = sum(1 for d in demos if d.status == "lost")
    no_show = sum(1 for d in demos if d.status == "no_show")

    return {
        "total_demos": total,
        "completed": completed,
        "converted": converted,
        "lost": lost,
        "no_show": no_show,
        "conversion_rate": round(converted / max(completed, 1) * 100, 1),
        "completion_rate": round(completed / max(total, 1) * 100, 1),
    }
