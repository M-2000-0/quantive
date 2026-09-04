"""Quantive Policy Engine - Central Policy Registry and Enforcement."""

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.policy")


POLICIES = {
    "data_classification": {"version": "1.0", "effective": "2026-08-28", "owner": "security_lead",
        "summary": "All customer data classified as public/internal/confidential/restricted/regulated."},
    "segregation_of_duties": {"version": "1.0", "effective": "2026-08-28", "owner": "security_lead",
        "summary": "No single person can create, approve, execute, and hide a financial action."},
    "backup_recovery": {"version": "1.0", "effective": "2026-08-28", "owner": "technical_lead",
        "summary": "Backups independent from system, tested restoration, documented RPO/RTO."},
    "incident_response": {"version": "1.0", "effective": "2026-08-28", "owner": "incident_commander",
        "summary": "Immediate halt on suspected breach. Preserve evidence. Notify customer."},
    "marketing_claims": {"version": "1.0", "effective": "2026-08-28", "owner": "contract_owner",
        "summary": "All claims truthful, supportable, approved. No bug-free/guaranteed/production-ready claims."},
    "personnel": {"version": "1.0", "effective": "2026-08-28", "owner": "technical_lead",
        "summary": "NDA, acceptable-use, security training before access. Annual refresh."},
    "contract_approval": {"version": "1.0", "effective": "2026-08-28", "owner": "contract_owner",
        "summary": "Every contract reviewed for scope, data, security, IP, warranties, liability."},
    "product_release": {"version": "1.0", "effective": "2026-08-28", "owner": "technical_lead",
        "summary": "Version number, change record, test results, rollback, named approver required."},
    "records_evidence": {"version": "1.0", "effective": "2026-08-28", "owner": "security_lead",
        "summary": "Preserve proposals, tests, releases, logs, contracts. No destruction on dispute."},
    "emergency_halt": {"version": "1.0", "effective": "2026-08-28", "owner": "incident_commander",
        "summary": "Global circuit breaker. 6 reasons. Halts all operations."},
    "data_provenance": {"version": "1.0", "effective": "2026-08-28", "owner": "security_lead",
        "summary": "Track source, import, transformation for every dataset."},
    "financial_validation": {"version": "1.0", "effective": "2026-08-28", "owner": "technical_lead",
        "summary": "Decimal precision, range checks, optimization result validation."},
}


class PolicyEngine:

    def __init__(self, db: Session):
        self.db = db

    def check_policy(self, policy_name: str) -> dict:
        policy = POLICIES.get(policy_name)
        if not policy:
            return {"status": "unknown", "policy": policy_name}
        return {"status": "active", "policy": policy_name, **policy}

    def list_policies(self) -> list[dict]:
        return [{"name": k, **v} for k, v in POLICIES.items()]

    def log_policy_check(self, policy_name: str, resource_type: str, resource_id: str, result: str, user_id: str):
        from app.audit.database_audit import append_audit_entry
        append_audit_entry(db=self.db, event_type="policy.check", resource_type=resource_type,
            resource_id=resource_id, action="policy_check",
            details={"policy": policy_name, "result": result, "user_id": user_id})