"""Conflict of Interest Detection."""

import logging
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.coi")


class ConflictOfInterestDetector:

    def __init__(self, db: Session):
        self.db = db

    def detect_self_review(self, org_id=None, days=90):
        from app.models import DatabaseAuditEntry
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        q = self.db.query(DatabaseAuditEntry).filter(DatabaseAuditEntry.event_type.in_(["data.create", "approval.approved"]), DatabaseAuditEntry.created_at >= cutoff)
        if org_id:
            q = q.filter(DatabaseAuditEntry.org_id == org_id)
        entries = q.all()
        creator_of = {}
        alerts = []
        for e in entries:
            d = e.details or {}
            uid = d.get("user_id") or d.get("created_by") or d.get("approver_id")
            if e.event_type == "data.create":
                creator_of[e.resource_id] = uid
            elif e.event_type == "approval.approved":
                if e.resource_id in creator_of and creator_of[e.resource_id] == uid:
                    alerts.append({"user": uid, "resource": e.resource_id, "type": "self_review", "severity": "critical", "timestamp": e.timestamp.isoformat()})
        return alerts

    def detect_department_self_review(self, org_id=None, days=90):
        from app.models import DatabaseAuditEntry
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        q = self.db.query(DatabaseAuditEntry).filter(DatabaseAuditEntry.event_type == "approval.approved", DatabaseAuditEntry.created_at >= cutoff)
        if org_id:
            q = q.filter(DatabaseAuditEntry.org_id == org_id)
        entries = q.all()
        dept_approvals = defaultdict(list)
        for e in entries:
            d = e.details or {}
            dept = d.get("department")
            uid = d.get("approver_id")
            if dept and uid:
                dept_approvals[dept].append(uid)
        alerts = []
        for dept, users in dept_approvals.items():
            if len(set(users)) == 1 and len(users) >= 3:
                alerts.append({"department": dept, "single_approver": users[0], "approval_count": len(users), "type": "department_self_review", "severity": "high"})
        return alerts

    def get_full_report(self, org_id=None, days=90):
        return {
            "self_review": self.detect_self_review(org_id, days),
            "department_self_review": self.detect_department_self_review(org_id, days),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }