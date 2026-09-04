"""Anti-Collusion Detection Engine."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import Counter, defaultdict

from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.collusion")


class AntiCollusionDetector:

    def __init__(self, db: Session):
        self.db = db

    def detect_mutual_approvals(self, org_id=None, days=90, min_count=3):
        from app.models import DatabaseAuditEntry
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        q = self.db.query(DatabaseAuditEntry).filter(DatabaseAuditEntry.event_type.in_(["approval.approved", "sod.assignment"]), DatabaseAuditEntry.created_at >= cutoff)
        if org_id:
            q = q.filter(DatabaseAuditEntry.org_id == org_id)
        entries = q.all()
        pairs = Counter()
        for e in entries:
            d = e.details or {}
            uid = d.get("user_id") or d.get("approver_id")
            tx = e.resource_id
            if uid:
                pairs[(tx, uid)] = uid
        tx_users = defaultdict(list)
        for (tx, uid) in pairs:
            tx_users[tx].append(uid)
        mutual = Counter()
        for tx, users in tx_users.items():
            for i, u1 in enumerate(users):
                for u2 in users[i+1:]:
                    key = tuple(sorted([u1, u2]))
                    mutual[key] += 1
        alerts = []
        for (u1, u2), count in mutual.items():
            if count >= min_count:
                alerts.append({"user_pair": [u1, u2], "mutual_approvals": count, "severity": "high" if count >= 5 else "medium", "type": "mutual_approval_pattern"})
        return alerts

    def detect_off_hours_activity(self, org_id=None, days=30):
        from app.models import DatabaseAuditEntry
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        q = self.db.query(DatabaseAuditEntry).filter(DatabaseAuditEntry.event_type.in_(["approval.approved", "optimization.execute"]), DatabaseAuditEntry.created_at >= cutoff)
        if org_id:
            q = q.filter(DatabaseAuditEntry.org_id == org_id)
        entries = q.all()
        alerts = []
        for e in entries:
            hour = e.timestamp.hour
            if hour < 6 or hour > 22:
                d = e.details or {}
                alerts.append({"user": d.get("user_id") or d.get("approver_id"), "timestamp": e.timestamp.isoformat(), "hour": hour, "event": e.event_type, "severity": "medium"})
        return alerts

    def detect_assumption_manipulation(self, org_id=None, days=30):
        from app.models import DatabaseAuditEntry
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        q = self.db.query(DatabaseAuditEntry).filter(DatabaseAuditEntry.event_type == "assumption.update", DatabaseAuditEntry.created_at >= cutoff)
        if org_id:
            q = q.filter(DatabaseAuditEntry.org_id == org_id)
        entries = q.all()
        user_changes = defaultdict(list)
        for e in entries:
            d = e.details or {}
            uid = d.get("user_id")
            field = d.get("field")
            if uid and field:
                user_changes[(uid, field)].append({"old": d.get("old_value"), "new": d.get("new_value"), "time": e.timestamp.isoformat()})
        alerts = []
        for (uid, field), changes in user_changes.items():
            if len(changes) >= 3:
                alerts.append({"user": uid, "field": field, "change_count": len(changes), "changes": changes[-5:], "severity": "high", "type": "repeated_assumption_change"})
        return alerts

    def get_full_report(self, org_id=None, days=90):
        return {
            "mutual_approvals": self.detect_mutual_approvals(org_id, days),
            "off_hours_activity": self.detect_off_hours_activity(org_id, days),
            "assumption_manipulation": self.detect_assumption_manipulation(org_id, days),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }