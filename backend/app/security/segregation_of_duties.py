"""Segregation of Duties Enforcement.

Core principle: No single person should be able to create, approve, execute,
and hide a financial action.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.sod")


class DutyRole:
    CREATOR = "creator"
    REVIEWER = "reviewer"
    APPROVER = "approver"
    EXECUTOR = "executor"
    AUDITOR = "auditor"


CONFLICTING_ROLES = {
    DutyRole.CREATOR: [DutyRole.APPROVER, DutyRole.AUDITOR],
    DutyRole.APPROVER: [DutyRole.CREATOR, DutyRole.EXECUTOR],
    DutyRole.EXECUTOR: [DutyRole.APPROVER, DutyRole.CREATOR],
    DutyRole.REVIEWER: [DutyRole.CREATOR],
    DutyRole.AUDITOR: [DutyRole.CREATOR, DutyRole.EXECUTOR, DutyRole.APPROVER],
}


class SegregationOfDuties:

    def __init__(self, db: Session):
        self.db = db

    def check_assignment(self, user_id, duty_role, transaction_id, existing_assignments):
        for existing_role, assigned_user in existing_assignments.items():
            if assigned_user == user_id:
                if existing_role == duty_role:
                    return {"allowed": False, "reason": f"User already holds {duty_role}", "conflict": existing_role}
                if duty_role in CONFLICTING_ROLES.get(existing_role, []):
                    return {"allowed": False, "reason": f"SoD violation: {existing_role} != {duty_role}", "conflict": existing_role}
        for conflict_role in CONFLICTING_ROLES.get(duty_role, []):
            if conflict_role in existing_assignments and existing_assignments[conflict_role] == user_id:
                return {"allowed": False, "reason": f"SoD violation: {conflict_role} != {duty_role}", "conflict": conflict_role}
        return {"allowed": True, "reason": "OK", "conflict": None}

    def record_assignment(self, user_id, duty_role, transaction_id, transaction_type, amount):
        from app.audit.database_audit import append_audit_entry
        return append_audit_entry(db=self.db, event_type="sod.assignment", resource_type="transaction",
            resource_id=transaction_id, action="assign",
            details={"user_id": user_id, "duty_role": duty_role, "tx_type": transaction_type, "amount": amount})

    def get_violations(self, org_id=None, days=30):
        from app.models import DatabaseAuditEntry
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = self.db.query(DatabaseAuditEntry).filter(DatabaseAuditEntry.event_type == "sod.assignment", DatabaseAuditEntry.created_at >= cutoff)
        if org_id:
            query = query.filter(DatabaseAuditEntry.org_id == org_id)
        entries = query.all()
        txns = {}
        for e in entries:
            d = e.details or {}
            txns.setdefault(e.resource_id, []).append({"user": d.get("user_id"), "role": d.get("duty_role")})
        violations = []
        for tx_id, assigns in txns.items():
            role_map = {}
            for a in assigns:
                r, u = a["role"], a["user"]
                if r in role_map and role_map[r] != u:
                    violations.append({"tx": tx_id, "type": "dual_assignment", "role": r, "severity": "high"})
                role_map[r] = u
            for ra, ua in role_map.items():
                for rb, ub in role_map.items():
                    if ra != rb and ua == ub and rb in CONFLICTING_ROLES.get(ra, []):
                        violations.append({"tx": tx_id, "type": "segregation_violation", "user": ua, "roles": [ra, rb], "severity": "critical"})
        return violations


def enforce_sod(db, user_id, duty_role, transaction_id, transaction_type, amount, existing=None):
    engine = SegregationOfDuties(db)
    check = engine.check_assignment(user_id, duty_role, transaction_id, existing or {})
    if not check["allowed"]:
        logger.warning("sod_violation", extra={"user": user_id, "role": duty_role, "tx": transaction_id})
        return check
    engine.record_assignment(user_id, duty_role, transaction_id, transaction_type, amount)
    return check