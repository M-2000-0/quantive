"""Immutable Audit Trail with Cryptographic Hash Chain.

Provides tamper-evident logging for all critical operations.
Every event is signed with a hash chain that makes modification detectable.

This addresses the "No Immutable Audit Trail" critical issue from
the Government Procurement Stress Test.
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AuditEventType(str, Enum):
    """Types of audit events."""
    # Authentication
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    PASSWORD_CHANGED = "password.changed"
    MFA_ENABLED = "mfa.enabled"
    MFA_DISABLED = "mfa.disabled"

    # Data mutations
    PORTFOLIO_CREATED = "portfolio.created"
    PORTFOLIO_UPDATED = "portfolio.updated"
    PORTFOLIO_DELETED = "portfolio.deleted"
    INSTRUMENT_CREATED = "instrument.created"
    INSTRUMENT_UPDATED = "instrument.updated"
    INSTRUMENT_DELETED = "instrument.deleted"

    # Optimization
    OPTIMIZATION_STARTED = "optimization.started"
    OPTIMIZATION_COMPLETED = "optimization.completed"
    OPTIMIZATION_FAILED = "optimization.failed"

    # Approvals
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"

    # Government
    GOV_ENTITY_CREATED = "gov_entity.created"
    GOV_ENTITY_UPDATED = "gov_entity.updated"
    FISCAL_RULE_CREATED = "fiscal_rule.created"
    FISCAL_RULE_EVALUATED = "fiscal_rule.evaluated"

    # Security
    SECURITY_EVENT = "security.event"
    ACCESS_DENIED = "access.denied"
    ANOMALY_DETECTED = "anomaly.detected"

    # System
    SYSTEM_CONFIG_CHANGED = "system.config.changed"
    DATA_EXPORTED = "data.exported"
    REPORT_GENERATED = "report.generated"


@dataclass
class AuditEvent:
    """A single audit event with cryptographic verification."""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    actor_id: str
    actor_email: str
    resource_type: str
    resource_id: str
    action: str
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None

    # Cryptographic fields
    previous_hash: str = ""
    event_hash: str = ""
    signature: str = ""


class ImmutableAuditTrail:
    """Cryptographically signed, tamper-evident audit trail."""

    def __init__(self, secret_key: str = ""):
        self._secret_key = secret_key or "quantive-audit-secret-key-change-in-production"
        self._events: list[AuditEvent] = []
        self._last_hash: str = "0" * 64  # Genesis hash

    def _compute_hash(self, event_data: str, previous_hash: str) -> str:
        """Compute SHA-256 hash of event data chained with previous hash."""
        combined = f"{previous_hash}:{event_data}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _compute_signature(self, event_hash: str) -> str:
        """Compute HMAC signature for the event hash."""
        return hashlib.sha256(
            f"{self._secret_key}:{event_hash}".encode()
        ).hexdigest()

    def record_event(
        self,
        event_type: AuditEventType,
        actor_id: str,
        actor_email: str,
        resource_type: str,
        resource_id: str,
        action: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditEvent:
        """Record an audit event with cryptographic signing."""
        event_id = f"evt-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{len(self._events):06d}"

        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            actor_id=actor_id,
            actor_email=actor_email,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            previous_hash=self._last_hash,
        )

        # Compute hash chain
        event_data = json.dumps({
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "actor_id": event.actor_id,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "action": event.action,
            "details": event.details,
            "previous_hash": event.previous_hash,
        }, sort_keys=True)

        event.event_hash = self._compute_hash(event_data, self._last_hash)
        event.signature = self._compute_signature(event.event_hash)
        self._last_hash = event.event_hash

        self._events.append(event)
        return event

    def verify_integrity(self) -> dict:
        """Verify the integrity of the entire audit trail."""
        issues = []
        current_hash = "0" * 64  # Genesis hash

        for i, event in enumerate(self._events):
            # Verify chain link
            if event.previous_hash != current_hash:
                issues.append({
                    "event_index": i,
                    "event_id": event.event_id,
                    "issue": "Chain broken: previous_hash mismatch",
                    "expected": current_hash,
                    "found": event.previous_hash,
                })

            # Recompute hash
            event_data = json.dumps({
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "actor_id": event.actor_id,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "action": event.action,
                "details": event.details,
                "previous_hash": event.previous_hash,
            }, sort_keys=True)

            expected_hash = self._compute_hash(event_data, current_hash)
            if event.event_hash != expected_hash:
                issues.append({
                    "event_index": i,
                    "event_id": event.event_id,
                    "issue": "Hash mismatch: event data may have been tampered",
                    "expected": expected_hash,
                    "found": event.event_hash,
                })

            # Verify signature
            expected_signature = self._compute_signature(event.event_hash)
            if event.signature != expected_signature:
                issues.append({
                    "event_index": i,
                    "event_id": event.event_id,
                    "issue": "Signature mismatch: event may have been forged",
                })

            current_hash = event.event_hash

        return {
            "total_events": len(self._events),
            "is_valid": len(issues) == 0,
            "issues": issues,
            "last_hash": self._last_hash,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_events(
        self,
        event_type: AuditEventType | None = None,
        actor_id: str | None = None,
        resource_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query audit events with filters."""
        events = self._events

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if actor_id:
            events = [e for e in events if e.actor_id == actor_id]
        if resource_type:
            events = [e for e in events if e.resource_type == resource_type]
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        return events[-limit:]

    def get_event_by_id(self, event_id: str) -> AuditEvent | None:
        """Get a specific event by ID."""
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None

    def export_events(self, format: str = "json") -> str:
        """Export audit events in specified format."""
        if format == "json":
            return json.dumps([
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
                    "previous_hash": e.previous_hash,
                    "event_hash": e.event_hash,
                    "signature": e.signature,
                }
                for e in self._events
            ], indent=2)
        elif format == "csv":
            headers = "event_id,event_type,timestamp,actor_id,resource_type,resource_id,action,event_hash"
            rows = [
                f"{e.event_id},{e.event_type.value},{e.timestamp.isoformat()},{e.actor_id},{e.resource_type},{e.resource_id},{e.action},{e.event_hash}"
                for e in self._events
            ]
            return "\n".join([headers] + rows)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_statistics(self) -> dict:
        """Get audit trail statistics."""
        event_types = {}
        actors = {}
        resources = {}

        for event in self._events:
            event_types[event.event_type.value] = event_types.get(event.event_type.value, 0) + 1
            actors[event.actor_id] = actors.get(event.actor_id, 0) + 1
            resources[event.resource_type] = resources.get(event.resource_type, 0) + 1

        return {
            "total_events": len(self._events),
            "events_by_type": event_types,
            "events_by_actor": actors,
            "events_by_resource": resources,
            "first_event": self._events[0].timestamp.isoformat() if self._events else None,
            "last_event": self._events[-1].timestamp.isoformat() if self._events else None,
        }


# Global audit trail instance
_audit_trail: ImmutableAuditTrail | None = None


def get_audit_trail() -> ImmutableAuditTrail:
    """Get the global audit trail instance."""
    global _audit_trail
    if _audit_trail is None:
        _audit_trail = ImmutableAuditTrail()
    return _audit_trail


def record_audit_event(
    event_type: AuditEventType,
    actor_id: str,
    actor_email: str,
    resource_type: str,
    resource_id: str,
    action: str,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditEvent:
    """Convenience function to record an audit event."""
    return get_audit_trail().record_event(
        event_type=event_type,
        actor_id=actor_id,
        actor_email=actor_email,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
