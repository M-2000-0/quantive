"""Immutable Audit Trail API endpoints.

Exposes audit trail verification, querying, and export
for government compliance and security requirements.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/immutable-audit", tags=["immutable-audit"])


# ── Request Models ─────────────────────────────────────────────────

class RecordEventRequest(BaseModel):
    event_type: str = Field(..., description="Event type (e.g., user.login, portfolio.created)")
    resource_type: str = Field(..., description="Resource type (e.g., portfolio, instrument)")
    resource_id: str = Field(..., description="Resource ID")
    action: str = Field(..., description="Action performed")
    details: dict | None = Field(default=None, description="Additional event details")
    ip_address: str | None = Field(default=None, max_length=45)
    user_agent: str | None = Field(default=None, max_length=500)


# ── API Endpoints ──────────────────────────────────────────────────

@router.post("/record")
def record_event(
    request: RecordEventRequest,
    user: User = Depends(get_current_user),
):
    """Record an audit event with cryptographic signing."""
    from quantive.trust.immutable_audit import (
        AuditEventType,
        record_audit_event,
    )

    # Map event type string to enum
    event_type_map = {e.value: e for e in AuditEventType}
    event_type = event_type_map.get(request.event_type)
    if not event_type:
        raise HTTPException(400, f"Invalid event type: {request.event_type}")

    event = record_audit_event(
        event_type=event_type,
        actor_id=user.id,
        actor_email=user.email,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        action=request.action,
        details=request.details,
        ip_address=request.ip_address,
        user_agent=request.user_agent,
    )

    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "timestamp": event.timestamp.isoformat(),
        "event_hash": event.event_hash,
        "signature": event.signature,
        "previous_hash": event.previous_hash,
        "message": "Event recorded with cryptographic signature",
    }


@router.get("/verify")
def verify_integrity(
    user: User = Depends(get_current_user),
):
    """Verify the integrity of the entire audit trail."""
    from quantive.trust.immutable_audit import get_audit_trail

    audit_trail = get_audit_trail()
    verification = audit_trail.verify_integrity()

    return verification


@router.get("/events")
def list_events(
    event_type: str | None = None,
    actor_id: str | None = None,
    resource_type: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    user: User = Depends(get_current_user),
):
    """List audit events with filters."""
    from quantive.trust.immutable_audit import (
        AuditEventType,
        get_audit_trail,
    )

    audit_trail = get_audit_trail()

    # Parse event type
    parsed_event_type = None
    if event_type:
        event_type_map = {e.value: e for e in AuditEventType}
        parsed_event_type = event_type_map.get(event_type)
        if not parsed_event_type:
            raise HTTPException(400, f"Invalid event type: {event_type}")

    # Parse timestamps
    parsed_start = None
    parsed_end = None
    if start_time:
        parsed_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if end_time:
        parsed_end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

    events = audit_trail.get_events(
        event_type=parsed_event_type,
        actor_id=actor_id,
        resource_type=resource_type,
        start_time=parsed_start,
        end_time=parsed_end,
        limit=limit,
    )

    return {
        "total": len(events),
        "events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type.value,
                "timestamp": e.timestamp.isoformat(),
                "actor_id": e.actor_id,
                "actor_email": e.actor_email,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "action": e.action,
                "details": e.details,
                "ip_address": e.ip_address,
                "event_hash": e.event_hash,
                "signature": e.signature,
            }
            for e in events
        ],
    }


@router.get("/events/{event_id}")
def get_event(
    event_id: str,
    user: User = Depends(get_current_user),
):
    """Get a specific audit event by ID."""
    from quantive.trust.immutable_audit import get_audit_trail

    audit_trail = get_audit_trail()
    event = audit_trail.get_event_by_id(event_id)

    if not event:
        raise HTTPException(404, "Event not found")

    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "timestamp": event.timestamp.isoformat(),
        "actor_id": event.actor_id,
        "actor_email": event.actor_email,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "action": event.action,
        "details": event.details,
        "ip_address": event.ip_address,
        "user_agent": event.user_agent,
        "previous_hash": event.previous_hash,
        "event_hash": event.event_hash,
        "signature": event.signature,
    }


@router.get("/export")
def export_events(
    format: str = Query("json", regex="^(json|csv)$"),
    user: User = Depends(get_current_user),
):
    """Export audit events in JSON or CSV format."""
    from quantive.trust.immutable_audit import get_audit_trail

    audit_trail = get_audit_trail()
    export_data = audit_trail.export_events(format=format)

    if format == "json":
        return {"data": export_data, "format": "json"}
    else:
        return {"data": export_data, "format": "csv"}


@router.get("/statistics")
def get_statistics(
    user: User = Depends(get_current_user),
):
    """Get audit trail statistics."""
    from quantive.trust.immutable_audit import get_audit_trail

    audit_trail = get_audit_trail()
    stats = audit_trail.get_statistics()

    return stats


@router.get("/chain/{event_id}")
def get_event_chain(
    event_id: str,
    depth: int = Query(10, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    """Get the hash chain for an event and its predecessors."""
    from quantive.trust.immutable_audit import get_audit_trail

    audit_trail = get_audit_trail()
    event = audit_trail.get_event_by_id(event_id)

    if not event:
        raise HTTPException(404, "Event not found")

    # Build chain
    chain = []
    current = event
    for _ in range(depth):
        chain.append({
            "event_id": current.event_id,
            "event_type": current.event_type.value,
            "timestamp": current.timestamp.isoformat(),
            "event_hash": current.event_hash,
            "previous_hash": current.previous_hash,
            "signature": current.signature,
        })

        # Find previous event
        if current.previous_hash == "0" * 64:
            break

        for e in audit_trail._events:
            if e.event_hash == current.previous_hash:
                current = e
                break
        else:
            break

    return {
        "event_id": event_id,
        "chain_depth": len(chain),
        "chain": chain,
        "is_complete": chain[-1]["previous_hash"] == "0" * 64,
    }
