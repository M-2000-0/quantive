"""Personnel, Contractor, and Confidentiality Policy Tracking."""

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.personnel")


REQUIRED_AGREEMENTS = [
    "confidentiality",
    "invention_assignment",
    "acceptable_use",
    "security_policy",
    "data_handling",
]

REQUIRED_TRAINING = [
    "phishing_awareness",
    "credential_management",
    "data_classification",
    "incident_reporting",
    "prohibited_promises",
    "change_control",
    "customer_communications",
]


class PersonnelTracker:

    def __init__(self, db):
        self.db = db

    def check_access_readiness(self, person_id: str, agreements_signed: list[str], training_completed: list[str]) -> dict:
        missing_agreements = [a for a in REQUIRED_AGREEMENTS if a not in agreements_signed]
        missing_training = [t for t in REQUIRED_TRAINING if t not in training_completed]
        ready = len(missing_agreements) == 0 and len(missing_training) == 0
        return {"person_id": person_id, "access_ready": ready,
            "missing_agreements": missing_agreements, "missing_training": missing_training,
            "message": "Access approved" if ready else f"Cannot grant access: missing {len(missing_agreements)} agreements, {len(missing_training)} training"}

    def log_access_grant(self, person_id: str, role: str, granted_by: str):
        from app.audit.database_audit import append_audit_entry
        append_audit_entry(db=self.db, event_type="personnel.access_granted",
            resource_type="person", resource_id=person_id, action="grant",
            details={"role": role, "granted_by": granted_by})

    def log_access_revocation(self, person_id: str, reason: str, revoked_by: str):
        from app.audit.database_audit import append_audit_entry
        append_audit_entry(db=self.db, event_type="personnel.access_revoked",
            resource_type="person", resource_id=person_id, action="revoke",
            details={"reason": reason, "revoked_by": revoked_by})

    def check_vendor_readiness(self, vendor_id: str, agreements: list[str]) -> dict:
        required = ["confidentiality", "security_obligations", "incident_notification"]
        missing = [a for a in required if a not in agreements]
        return {"vendor_id": vendor_id, "ready": len(missing) == 0, "missing": missing}