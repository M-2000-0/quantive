"""Immutable Audit API — Tamper-evident audit trail endpoints.

Endpoints:
- GET /api/immutable-audit/verify — Verify chain integrity
- GET /api/immutable-audit/events — List audit events
- GET /api/immutable-audit/events/{sequence} — Get specific event
- GET /api/immutable-audit/export — Export chain for compliance
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import get_current_user
from app.security.immutable_audit import ImmutableAuditTrail

router = APIRouter(prefix="/api/immutable-audit", tags=["immutable-audit"])


@router.get("/verify")
def verify_chain(
    org_id: str = Query(None, description="Filter by organization"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Verify the integrity of the immutable audit chain."""
    trail = ImmutableAuditTrail(db)
    return trail.verify_chain(org_id=org_id or getattr(user, 'org_id', None))


@router.get("/events")
def list_events(
    org_id: str = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List immutable audit events."""
    trail = ImmutableAuditTrail(db)
    from app.security.immutable_audit import ImmutableAuditEvent
    query = db.query(ImmutableAuditEvent)
    if org_id or getattr(user, 'org_id', None):
        query = query.filter(ImmutableAuditEvent.org_id == (org_id or user.org_id))
    events = query.order_by(ImmutableAuditEvent.sequence_number.desc()).offset(offset).limit(limit).all()
    return {
        "events": [
            {
                "sequence": e.sequence_number,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "actor_email": e.actor_email,
                "event_hash": e.event_hash[:16] + "...",
            }
            for e in events
        ],
        "total": query.count(),
    }


@router.get("/events/{sequence_number}")
def get_event(
    sequence_number: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific immutable audit event with full details."""
    trail = ImmutableAuditTrail(db)
    event = trail.export_event(sequence_number)
    if not event:
        return {"error": "Event not found"}
    return event


@router.get("/export")
def export_chain(
    org_id: str = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Export the full audit chain for compliance/parliamentary investigation."""
    trail = ImmutableAuditTrail(db)
    return {
        "chain": trail.export_chain(org_id=org_id or getattr(user, 'org_id', None), limit=limit),
        "verification": trail.verify_chain(org_id=org_id or getattr(user, 'org_id', None)),
    }
