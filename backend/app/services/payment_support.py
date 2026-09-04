"""Payment support service — refund processing, billing disputes, payment issues."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.support.payment")


def get_payment_issues(db: Session, org_id: str, status: Optional[str] = None) -> list[dict]:
    """Get payment-related support issues for an org."""
    from app.models.support import SupportTicket

    q = db.query(SupportTicket).filter(
        SupportTicket.org_id == org_id,
        SupportTicket.category == "billing",
    )
    if status:
        q = q.filter(SupportTicket.status == status)

    tickets = q.order_by(SupportTicket.created_at.desc()).limit(50).all()
    return [{
        "id": t.id,
        "subject": t.subject,
        "description": t.description[:200],
        "status": t.status,
        "priority": t.priority,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    } for t in tickets]


def process_refund_request(
    db: Session,
    ticket_id: str,
    org_id: str,
    amount: float,
    reason: str,
    processed_by: str,
) -> dict:
    """Process a refund request — creates resolution record."""
    from app.models.support import SupportMessage, SupportTicket

    ticket = db.query(SupportTicket).filter(
        SupportTicket.id == ticket_id,
        SupportTicket.org_id == org_id,
    ).first()

    if not ticket:
        return {"error": "Ticket not found"}

    # Add resolution message
    msg = SupportMessage(
        ticket_id=ticket_id,
        user_id=processed_by,
        content=f"Refund of ${amount:.2f} processed. Reason: {reason}",
        is_internal=False,
        is_ai_generated=False,
    )
    db.add(msg)
    ticket.status = "resolved"
    ticket.resolution_notes = f"Refund ${amount:.2f} — {reason}"
    db.commit()

    logger.info(f"Refund processed: ticket={ticket_id}, amount=${amount:.2f}")

    return {
        "ticket_id": ticket_id,
        "refund_amount": amount,
        "reason": reason,
        "status": "processed",
    }


def get_billing_summary(db: Session, org_id: str) -> dict:
    """Get billing health summary for an org."""
    from app.models.support import SupportTicket

    total_billing = db.query(SupportTicket).filter(
        SupportTicket.org_id == org_id,
        SupportTicket.category == "billing",
    ).count()

    open_billing = db.query(SupportTicket).filter(
        SupportTicket.org_id == org_id,
        SupportTicket.category == "billing",
        SupportTicket.status.in_(["open", "in_progress"]),
    ).count()

    urgent_billing = db.query(SupportTicket).filter(
        SupportTicket.org_id == org_id,
        SupportTicket.category == "billing",
        SupportTicket.priority == "urgent",
        SupportTicket.status.in_(["open", "in_progress"]),
    ).count()

    return {
        "total_billing_issues": total_billing,
        "open_billing_issues": open_billing,
        "urgent_billing_issues": urgent_billing,
        "resolution_rate": round((1 - open_billing / max(total_billing, 1)) * 100, 1),
    }
