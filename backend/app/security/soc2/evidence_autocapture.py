"""SOC 2 Automatic Evidence Capture.
Hooks into all SOC 2 modules to automatically collect evidence on every event.
No manual evidence collection needed.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from app.security.soc2.evidence_collector import ComplianceEvidenceCollector
from app.security.soc2.audit_log import SOC2AuditLogger
from app.security.soc2.access_control import AccessControlManager
from app.security.soc2.change_management import ChangeManagementController
from app.security.soc2.incident_response import IncidentResponseManager
from app.security.soc2.vendor_risk import VendorRiskManager


class EvidenceAutoCapture:
    """Automatically captures SOC 2 evidence from all module events."""

    def __init__(self, db):
        self.db = db
        self.collector = ComplianceEvidenceCollector(db)

    def after_audit_event(self, event) -> dict:
        criterion = self._map_event_to_criterion(event.event_type)
        return self.collector.collect_evidence(
            criterion=criterion,
            category="audit_log",
            title=f"Audit Event: {event.event_type}",
            description=f"Event {event.event_id} at {event.timestamp}",
            data={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "severity": event.severity,
                "actor_id": event.actor_id,
                "action": event.action,
                "success": event.success,
                "hash_chain": event.hash_chain,
            },
            collected_by=event.actor_id or "system",
        )

    def after_access_change(self, entry, action: str) -> dict:
        return self.collector.collect_evidence(
            criterion="CC6.3",
            category="access_review",
            title=f"Access {action}: {entry.user_id}",
            description=f"Access {action} for {entry.resource_type}",
            data={
                "user_id": entry.user_id,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "permission": entry.permission,
                "granted_by": entry.granted_by,
                "justification": entry.justification,
                "action": action,
            },
            collected_by=entry.granted_by,
        )

    def after_access_review(self, review) -> dict:
        return self.collector.collect_evidence(
            criterion="CC6.1",
            category="access_review",
            title=f"Quarterly Access Review",
            description=f"Reviewed {review.total_users_reviewed} users",
            data={
                "reviewer_id": review.reviewer_id,
                "total_users_reviewed": review.total_users_reviewed,
                "access_revoked": review.access_revoked,
                "findings": review.findings,
            },
            collected_by=review.reviewer_id,
        )

    def after_change_request(self, record) -> dict:
        return self.collector.collect_evidence(
            criterion="CC8.1",
            category="change_record",
            title=f"Change Request: {record.change_id}",
            description=f"Type: {record.change_type}",
            data={
                "change_id": record.change_id,
                "change_type": record.change_type,
                "description": record.description,
                "requested_by": record.requested_by,
                "risk_level": record.risk_level,
                "status": record.status,
            },
            collected_by=record.requested_by,
        )

    def after_incident(self, record) -> dict:
        return self.collector.collect_evidence(
            criterion="CC7.3",
            category="incident",
            title=f"Incident: {record.title}",
            description=f"Severity: {record.severity}",
            data={
                "incident_id": record.incident_id,
                "severity": record.severity,
                "status": record.status,
                "root_cause": record.root_cause,
            },
            collected_by=record.detected_by or "system",
        )

    def after_vendor_assessment(self, assessment) -> dict:
        return self.collector.collect_evidence(
            criterion="CC9.2",
            category="vendor_assessment",
            title=f"Vendor Assessment: {assessment.vendor_id}",
            description=f"Risk score: {assessment.risk_score}",
            data={
                "vendor_id": assessment.vendor_id,
                "risk_score": assessment.risk_score,
                "findings": assessment.findings,
            },
            collected_by=assessment.assessed_by,
        )

    def after_password_change(self, user_id: str) -> dict:
        return self.collector.collect_evidence(
            criterion="CC6.1",
            category="access_review",
            title=f"Password Changed: {user_id}",
            description=f"User {user_id} changed password",
            data={"user_id": user_id, "action": "password_change"},
            collected_by=user_id,
        )

    def after_role_change(self, user_id, old_role, new_role, changed_by) -> dict:
        return self.collector.collect_evidence(
            criterion="CC6.3",
            category="access_review",
            title=f"Role Changed: {user_id}",
            description=f"{old_role} to {new_role}",
            data={"user_id": user_id, "old_role": old_role, "new_role": new_role},
            collected_by=changed_by,
        )

    def _map_event_to_criterion(self, event_type: str) -> str:
        mapping = {
            "user.login": "CC6.1",
            "user.logout": "CC6.1",
            "user.login_failed": "CC6.1",
            "user.password_changed": "CC6.1",
            "user.registered": "CC6.1",
            "user.deactivated": "CC6.1",
            "user.role_changed": "CC6.3",
            "mfa.enabled": "CC6.2",
            "mfa.disabled": "CC6.2",
            "access.granted": "CC6.3",
            "access.denied": "CC6.3",
            "access.revoked": "CC6.3",
            "portfolio.created": "CC7.2",
            "portfolio.updated": "CC7.2",
            "portfolio.deleted": "CC7.2",
            "data.exported": "CC6.7",
            "backup.created": "CC7.5",
            "backup.verified": "CC7.5",
            "deployment.started": "CC8.1",
            "deployment.completed": "CC8.1",
            "incident.detected": "CC7.3",
            "incident.resolved": "CC7.4",
        }
        return mapping.get(event_type, "CC7.2")
