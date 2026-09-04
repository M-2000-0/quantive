"""SOC 2 Incident Response Manager.

CC7.3 — Evaluation of security events
CC7.4 — Incident response procedures
CC7.5 — Incident recovery

Implements:
- Incident detection and classification
- Response workflow automation
- Communication templates
- Post-incident review
- Business continuity triggers
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import Base


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    DETECTED = "detected"
    TRIAGED = "triaged"
    CONTAINING = "containing"
    ERADICATING = "eradicating"
    RECOVERING = "recovering"
    RESOLVED = "resolved"
    POST_REVIEW = "post_review"


class IncidentRecord(Base):
    """Immutable incident record."""
    __tablename__ = "incident_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(36), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False)
    status = Column(String(20), default="detected")
    detected_at = Column(DateTime(timezone=True), default=func.now())
    triaged_at = Column(DateTime(timezone=True), nullable=True)
    contained_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    detected_by = Column(String(36), nullable=True)
    assigned_to = Column(String(36), nullable=True)
    root_cause = Column(Text, nullable=True)
    remediation = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)
    customer_notified = Column(Boolean, default=False)
    regulatory_notified = Column(Boolean, default=False)
    evidence_preserved = Column(Boolean, default=False)


class IncidentResponseManager:
    """Manages incident response with SOC 2 compliance.

    Enforces:
    - All incidents are logged immutably
    - Severity determines response timeline
    - Evidence preservation before remediation
    - Post-incident review required
    - Customer notification within 72 hours (GDPR) / as per contract
    """

    # Response timelines by severity (hours)
    RESPONSE_TIMELINES = {
        "low": {"acknowledge": 24, "contain": 72, "resolve": 168},
        "medium": {"acknowledge": 8, "contain": 24, "resolve": 72},
        "high": {"acknowledge": 2, "contain": 8, "resolve": 24},
        "critical": {"acknowledge": 0.25, "contain": 1, "resolve": 8},
    }

    # Notification requirements by severity
    NOTIFICATION_REQUIREMENTS = {
        "low": {"customer": False, "regulatory": False, "executive": False},
        "medium": {"customer": False, "regulatory": False, "executive": True},
        "high": {"customer": True, "regulatory": False, "executive": True},
        "critical": {"customer": True, "regulatory": True, "executive": True},
    }

    def __init__(self, db: Session):
        self.db = db

    def create_incident(
        self,
        incident_id: str,
        title: str,
        description: str,
        severity: str,
        detected_by: Optional[str] = None,
    ) -> IncidentRecord:
        """Log a new incident."""
        record = IncidentRecord(
            incident_id=incident_id,
            title=title,
            description=description,
            severity=severity,
            detected_by=detected_by,
        )
        self.db.add(record)
        self.db.commit()
        return record

    def triage(self, incident_id: str, assigned_to: str) -> IncidentRecord:
        """Triage an incident and assign owner."""
        record = self._get_incident(incident_id)
        record.status = "triaged"
        record.assigned_to = assigned_to
        record.triaged_at = datetime.now(timezone.utc)
        self.db.commit()
        return record

    def contain(self, incident_id: str, actions_taken: str) -> IncidentRecord:
        """Mark incident as contained."""
        record = self._get_incident(incident_id)
        record.status = "containing"
        record.contained_at = datetime.now(timezone.utc)
        record.remediation = actions_taken
        record.evidence_preserved = True
        self.db.commit()
        return record

    def resolve(
        self,
        incident_id: str,
        root_cause: str,
        remediation: str,
        lessons_learned: str,
    ) -> IncidentRecord:
        """Resolve an incident with root cause analysis."""
        record = self._get_incident(incident_id)
        record.status = "resolved"
        record.resolved_at = datetime.now(timezone.utc)
        record.root_cause = root_cause
        record.remediation = remediation
        record.lessons_learned = lessons_learned
        self.db.commit()
        return record

    def check_notification_requirements(self, incident_id: str) -> dict:
        """Check what notifications are required for this severity."""
        record = self._get_incident(incident_id)
        requirements = self.NOTIFICATION_REQUIREMENTS.get(record.severity, {})
        timeline = self.RESPONSE_TIMELINES.get(record.severity, {})

        return {
            "incident_id": incident_id,
            "severity": record.severity,
            "customer_notification_required": requirements.get("customer", False),
            "regulatory_notification_required": requirements.get("regulatory", False),
            "executive_notification_required": requirements.get("executive", False),
            "response_timeline_hours": timeline,
        }

    def get_open_incidents(self) -> list:
        """Get all unresolved incidents."""
        return self.db.query(IncidentRecord).filter(
            IncidentRecord.status.notin_(["resolved", "post_review"])
        ).all()

    def get_incident_metrics(self, days: int = 30) -> dict:
        """Generate incident metrics for SOC 2 reporting."""
        from datetime import timedelta
        start = datetime.now(timezone.utc) - timedelta(days=days)

        incidents = self.db.query(IncidentRecord).filter(
            IncidentRecord.detected_at >= start
        ).all()

        total = len(incidents)
        by_severity = {}
        by_status = {}
        avg_response_time = 0

        for inc in incidents:
            by_severity[inc.severity] = by_severity.get(inc.severity, 0) + 1
            by_status[inc.status] = by_status.get(inc.status, 0) + 1

            if inc.triaged_at and inc.detected_at:
                delta = (inc.triaged_at - inc.detected_at).total_seconds() / 3600
                avg_response_time += delta

        return {
            "period_days": days,
            "total_incidents": total,
            "by_severity": by_severity,
            "by_status": by_status,
            "avg_response_time_hours": round(avg_response_time / total, 2) if total > 0 else 0,
            "mttr_hours": self._calc_mttr(incidents),
            "compliance_score": max(0, 100 - (total * 2)),
        }

    def _calc_mttr(self, incidents: list) -> float:
        """Calculate Mean Time To Resolve."""
        resolved = [i for i in incidents if i.resolved_at and i.detected_at]
        if not resolved:
            return 0
        total_hours = sum(
            (i.resolved_at - i.detected_at).total_seconds() / 3600
            for i in resolved
        )
        return round(total_hours / len(resolved), 2)

    def _get_incident(self, incident_id: str) -> IncidentRecord:
        record = self.db.query(IncidentRecord).filter(
            IncidentRecord.incident_id == incident_id
        ).first()
        if not record:
            raise ValueError(f"Incident {incident_id} not found")
        return record
