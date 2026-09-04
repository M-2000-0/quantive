"""Immutable Audit Trail — Cryptographic hash chain for tamper-evident logging.

Every audit event is linked to the previous event via a cryptographic hash.
This creates a chain that cannot be modified without breaking the chain.

Chain structure:
    event[0].hash = SHA256(event[0].data + "GENESIS")
    event[1].hash = SHA256(event[1].data + event[0].hash)
    event[n].hash = SHA256(event[n].data + event[n-1].hash)

To verify integrity:
    For each event, recompute hash from data + previous hash.
    If any hash doesn't match, the chain has been tampered with.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey, Index
from sqlalchemy.orm import Session

from app.database import Base

logger = logging.getLogger("quantive.audit.immutable")


class ImmutableAuditEvent(Base):
    """Immutable audit event with cryptographic hash chain."""
    __tablename__ = "immutable_audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence_number = Column(Integer, nullable=False, unique=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    actor_id = Column(String, nullable=True)
    actor_email = Column(String, nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    org_id = Column(String, nullable=True)
    data_json = Column(Text, nullable=False)  # Serialized event data
    metadata_json = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    previous_hash = Column(String(64), nullable=False)  # SHA-256 of previous event
    event_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 of this event
    signature = Column(Text, nullable=True)  # HSM signature (optional)

    __table_args__ = (
        Index("idx_immutable_audit_org_timestamp", "org_id", "timestamp"),
        Index("idx_immutable_audit_hash", "event_hash"),
    )


GENESIS_HASH = "0" * 64  # SHA-256 of nothing — used for first event


def _compute_event_hash(data: dict, previous_hash: str) -> str:
    """Compute SHA-256 hash of event data + previous hash."""
    # Canonicalize JSON for deterministic hashing
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    payload = f"{canonical}{previous_hash}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ImmutableAuditTrail:
    """Immutable audit trail with cryptographic hash chain."""

    def __init__(self, db: Session):
        self.db = db

    def get_last_hash(self, org_id: Optional[str] = None) -> str:
        """Get the hash of the most recent event in the chain."""
        query = self.db.query(ImmutableAuditEvent)
        if org_id:
            query = query.filter(ImmutableAuditEvent.org_id == org_id)
        last_event = query.order_by(ImmutableAuditEvent.sequence_number.desc()).first()
        return last_event.event_hash if last_event else GENESIS_HASH

    def get_next_sequence(self, org_id: Optional[str] = None) -> int:
        """Get the next sequence number."""
        query = self.db.query(ImmutableAuditEvent)
        if org_id:
            query = query.filter(ImmutableAuditEvent.org_id == org_id)
        last_event = query.order_by(ImmutableAuditEvent.sequence_number.desc()).first()
        return (last_event.sequence_number + 1) if last_event else 0

    def record_event(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        org_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        actor_email: Optional[str] = None,
        data: Optional[dict] = None,
        metadata: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> ImmutableAuditEvent:
        """Record an immutable audit event with hash chain."""
        previous_hash = self.get_last_hash(org_id)
        sequence = self.get_next_sequence(org_id)

        event_data = {
            "sequence": sequence,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "org_id": org_id,
            "actor_id": actor_id,
            "actor_email": actor_email,
            "data": data or {},
            "ip_address": ip_address,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        event_hash = _compute_event_hash(event_data, previous_hash)

        event = ImmutableAuditEvent(
            sequence_number=sequence,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            org_id=org_id,
            actor_id=actor_id,
            actor_email=actor_email,
            data_json=json.dumps(event_data, default=str),
            metadata_json=json.dumps(metadata, default=str) if metadata else None,
            ip_address=ip_address,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )

        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        logger.info(
            "immutable_audit_event",
            extra={
                "sequence": sequence,
                "action": action,
                "resource_type": resource_type,
                "hash": event_hash[:16] + "...",
            },
        )

        return event

    def verify_chain(self, org_id: Optional[str] = None) -> dict:
        """Verify the integrity of the entire audit chain.

        Returns:
            {
                "valid": bool,
                "events_checked": int,
                "first_event": int,
                "last_event": int,
                "first_timestamp": str,
                "last_timestamp": str,
                "broken_at": int | None,  # Sequence number where chain breaks
                "error": str | None,
            }
        """
        query = self.db.query(ImmutableAuditEvent)
        if org_id:
            query = query.filter(ImmutableAuditEvent.org_id == org_id)
        events = query.order_by(ImmutableAuditEvent.sequence_number.asc()).all()

        if not events:
            return {
                "valid": True,
                "events_checked": 0,
                "first_event": 0,
                "last_event": 0,
                "first_timestamp": None,
                "last_timestamp": None,
                "broken_at": None,
                "error": None,
            }

        previous_hash = GENESIS_HASH
        broken_at = None

        for event in events:
            # Verify link to previous event
            if event.previous_hash != previous_hash:
                broken_at = event.sequence_number
                break

            # Verify event hash
            event_data = json.loads(event.data_json)
            expected_hash = _compute_event_hash(event_data, previous_hash)
            if event.event_hash != expected_hash:
                broken_at = event.sequence_number
                break

            previous_hash = event.event_hash

        return {
            "valid": broken_at is None,
            "events_checked": len(events),
            "first_event": events[0].sequence_number,
            "last_event": events[-1].sequence_number,
            "first_timestamp": events[0].timestamp.isoformat() if events[0].timestamp else None,
            "last_timestamp": events[-1].timestamp.isoformat() if events[-1].timestamp else None,
            "broken_at": broken_at,
            "error": f"Chain broken at sequence {broken_at}" if broken_at else None,
        }

    def export_event(self, sequence_number: int) -> Optional[dict]:
        """Export a single audit event with full chain context."""
        event = self.db.query(ImmutableAuditEvent).filter(
            ImmutableAuditEvent.sequence_number == sequence_number
        ).first()
        if not event:
            return None

        return {
            "sequence_number": event.sequence_number,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "actor_id": event.actor_id,
            "actor_email": event.actor_email,
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "org_id": event.org_id,
            "data": json.loads(event.data_json),
            "metadata": json.loads(event.metadata_json) if event.metadata_json else None,
            "ip_address": event.ip_address,
            "previous_hash": event.previous_hash,
            "event_hash": event.event_hash,
            "signature": event.signature,
        }

    def export_chain(self, org_id: Optional[str] = None, limit: int = 1000) -> list[dict]:
        """Export audit chain for compliance/parliamentary investigation."""
        query = self.db.query(ImmutableAuditEvent)
        if org_id:
            query = query.filter(ImmutableAuditEvent.org_id == org_id)
        events = query.order_by(ImmutableAuditEvent.sequence_number.asc()).limit(limit).all()

        return [self.export_event(e.sequence_number) for e in events if e]


def record_immutable_event(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    org_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    actor_email: Optional[str] = None,
    data: Optional[dict] = None,
    metadata: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> ImmutableAuditEvent:
    """Convenience function to record an immutable audit event."""
    trail = ImmutableAuditTrail(db)
    return trail.record_event(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        org_id=org_id,
        actor_id=actor_id,
        actor_email=actor_email,
        data=data,
        metadata=metadata,
        ip_address=ip_address,
    )


def verify_audit_chain(db: Session, org_id: Optional[str] = None) -> dict:
    """Convenience function to verify the audit chain."""
    trail = ImmutableAuditTrail(db)
    return trail.verify_chain(org_id)
