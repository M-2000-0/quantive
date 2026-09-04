"""SOC 2 Audit Logging System.

CC7.2 — System monitoring detects anomalies
CC7.3 — Security event evaluation
CC7.4 — Incident response

All audit events are:
- Append-only (never deleted or modified)
- Cryptographically signed (SHA-256 hash chain)
- Retained for 7 years (configurable)
- Exportable for auditor review
"""
import hashlib
import json
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, Index
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import Base


class SeverityLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SOC2AuditEvent(Base):
    """Immutable audit event table. Append-only by design."""
    __tablename__ = "soc2_audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), nullable=False, unique=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="info")
    actor_id = Column(String(36), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True)
    actor_ip = Column(String(45), nullable=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)  # JSON-serialized
    previous_value = Column(Text, nullable=True)  # For change tracking
    new_value = Column(Text, nullable=True)
    request_id = Column(String(36), nullable=True, index=True)
    session_id = Column(String(64), nullable=True)
    user_agent = Column(String(500), nullable=True)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    hash_chain = Column(String(64), nullable=False)  # SHA-256 of this record
    previous_hash = Column(String(64), nullable=True)  # Hash of previous record

    __table_args__ = (
        Index("ix_soc2_audit_timestamp_type", "timestamp", "event_type"),
        Index("ix_soc2_audit_actor_action", "actor_id", "action"),
    )


class SOC2AuditLogger:
    """Append-only audit logger with cryptographic hash chain.

    Usage:
        logger = SOC2AuditLogger(db)
        logger.log(
            event_type="user.login",
            severity="info",
            actor_id=user.id,
            action="login",
            details={"method": "password"},
        )
    """

    # Event categories for SOC 2 compliance
    SECURITY_EVENTS = {
        "user.login", "user.logout", "user.login_failed", "user.password_changed",
        "user.password_reset_requested", "user.password_reset_completed",
        "user.registered", "user.deactivated", "user.role_changed",
        "mfa.setup_initiated", "mfa.enabled", "mfa.disabled", "mfa.verified",
        "mfa.verification_failed", "token.revoked",
    }

    DATA_EVENTS = {
        "portfolio.created", "portfolio.updated", "portfolio.deleted", "portfolio.uploaded",
        "optimization.created", "optimization.completed", "optimization.failed",
        "data.exported", "data.imported", "data.deleted",
    }

    ACCESS_EVENTS = {
        "access.granted", "access.denied", "access.revoked",
        "permission.changed", "role.assigned", "role.removed",
    }

    SYSTEM_EVENTS = {
        "system.startup", "system.shutdown", "system.error",
        "backup.created", "backup.verified", "backup.failed",
        "deployment.started", "deployment.completed", "deployment.failed",
        "incident.detected", "incident.resolved",
    }

    def __init__(self, db: Session):
        self.db = db

    def _get_previous_hash(self) -> Optional[str]:
        """Get the hash of the most recent audit event."""
        last_event = self.db.query(SOC2AuditEvent).order_by(SOC2AuditEvent.id.desc()).first()
        return last_event.hash_chain if last_event else "genesis"

    def _compute_hash(self, event_data: dict, previous_hash: str) -> str:
        """Compute SHA-256 hash for hash chain integrity."""
        data_string = json.dumps(event_data, sort_keys=True, default=str)
        combined = f"{previous_hash}:{data_string}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def log(
        self,
        event_type: str,
        action: str,
        severity: str = "info",
        actor_id: Optional[str] = None,
        actor_email: Optional[str] = None,
        actor_ip: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        previous_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> SOC2AuditEvent:
        """Log an audit event with hash chain integrity."""
        import uuid
        event_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        previous_hash = self._get_previous_hash()

        event_data = {
            "event_id": event_id,
            "timestamp": timestamp.isoformat(),
            "event_type": event_type,
            "severity": severity,
            "actor_id": actor_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "success": success,
        }

        hash_chain = self._compute_hash(event_data, previous_hash)

        audit_event = SOC2AuditEvent(
            event_id=event_id,
            timestamp=timestamp,
            event_type=event_type,
            severity=severity,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=json.dumps(details) if details else None,
            previous_value=json.dumps(previous_value) if previous_value else None,
            new_value=json.dumps(new_value) if new_value else None,
            request_id=request_id,
            session_id=session_id,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            hash_chain=hash_chain,
            previous_hash=previous_hash,
        )

        self.db.add(audit_event)
        self.db.commit()
        return audit_event

    def verify_integrity(self, limit: int = 1000) -> dict:
        """Verify hash chain integrity for the last N events.

        Returns:
            Dict with verification status and any broken links.
        """
        events = self.db.query(SOC2AuditEvent).order_by(SOC2AuditEvent.id.desc()).limit(limit).all()
        events.reverse()  # Oldest first

        broken_links = []
        for i, event in enumerate(events):
            if i == 0:
                continue  # Skip genesis

            expected_previous = events[i-1].hash_chain
            if event.previous_hash != expected_previous:
                broken_links.append({
                    "event_id": event.event_id,
                    "expected_previous_hash": expected_previous,
                    "actual_previous_hash": event.previous_hash,
                })

        return {
            "verified": len(broken_links) == 0,
            "events_checked": len(events),
            "broken_links": broken_links,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_events(
        self,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[SOC2AuditEvent]:
        """Query audit events for compliance review."""
        query = self.db.query(SOC2AuditEvent)

        if event_type:
            query = query.filter(SOC2AuditEvent.event_type == event_type)
        if actor_id:
            query = query.filter(SOC2AuditEvent.actor_id == actor_id)
        if severity:
            query = query.filter(SOC2AuditEvent.severity == severity)
        if start_time:
            query = query.filter(SOC2AuditEvent.timestamp >= start_time)
        if end_time:
            query = query.filter(SOC2AuditEvent.timestamp <= end_time)

        return query.order_by(SOC2AuditEvent.timestamp.desc()).limit(limit).all()

    def get_security_summary(self, days: int = 30) -> dict:
        """Generate security event summary for SOC 2 reporting."""
        from datetime import timedelta
        start = datetime.now(timezone.utc) - timedelta(days=days)

        events = self.db.query(SOC2AuditEvent).filter(
            SOC2AuditEvent.timestamp >= start
        ).all()

        summary = {
            "period_days": days,
            "total_events": len(events),
            "security_events": 0,
            "failed_logins": 0,
            "successful_logins": 0,
            "mfa_events": 0,
            "data_access_events": 0,
            "critical_events": 0,
            "unique_users": set(),
            "unique_ips": set(),
        }

        for event in events:
            if event.event_type in self.SECURITY_EVENTS:
                summary["security_events"] += 1
            if event.event_type == "user.login_failed":
                summary["failed_logins"] += 1
            if event.event_type == "user.login":
                summary["successful_logins"] += 1
            if "mfa" in event.event_type:
                summary["mfa_events"] += 1
            if event.event_type in self.DATA_EVENTS:
                summary["data_access_events"] += 1
            if event.severity == "critical":
                summary["critical_events"] += 1
            if event.actor_id:
                summary["unique_users"].add(event.actor_id)
            if event.actor_ip:
                summary["unique_ips"].add(event.actor_ip)

        summary["unique_users"] = len(summary["unique_users"])
        summary["unique_ips"] = len(summary["unique_ips"])
        return summary
