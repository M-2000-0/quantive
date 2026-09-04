"""Release Management - Version tracking, approval gates, rollback."""

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.release")


ENVIRONMENTS = ["laboratory", "demonstration", "pilot", "staging", "production"]


class ReleaseGate:
    def __init__(self, db):
        self.db = db

    def can_promote(self, version: str, from_env: str, to_env: str) -> dict:
        if to_env == "production":
            gates = [
                "Testing against agreed acceptance criteria documented",
                "Independent backup verification completed",
                "Access-control review completed",
                "Logging validation completed",
                "Incident-response readiness confirmed",
                "Insurance confirmation obtained",
                "Contract approval completed",
                "Written customer acceptance received",
            ]
            return {"version": version, "from": from_env, "to": to_env,
                "gates_required": gates, "status": "pending",
                "message": "All gates must be completed before production promotion"}
        return {"version": version, "from": from_env, "to": to_env, "status": "allowed",
            "message": "Non-production promotion allowed with approval"}

    def create_release_record(self, version: str, environment: str, approver: str, changes: list[str],
            test_results: str, known_issues: list[str], rollback_method: str) -> dict:
        from app.audit.database_audit import append_audit_entry
        entry = append_audit_entry(db=self.db, event_type="release.created",
            resource_type="release", resource_id=version, action="create",
            details={"version": version, "environment": environment, "approver": approver,
                "changes": changes, "test_results": test_results,
                "known_issues": known_issues, "rollback_method": rollback_method})
        return {"version": version, "environment": environment, "status": "recorded",
            "timestamp": datetime.now(timezone.utc).isoformat()}