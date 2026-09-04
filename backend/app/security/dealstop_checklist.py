"""Deal-Stop Checklist - Hard blocks before any customer contract."""

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.dealstop")


CHECKLIST_ITEMS = [
    {"id": "entity", "question": "Is the company properly formed and authorized to contract?", "category": "legal", "required": True},
    {"id": "customer_contract", "question": "Is the customer contracting with the company rather than an individual owner?", "category": "legal", "required": True},
    {"id": "attorney_review", "question": "Has a technology attorney reviewed the agreement?", "category": "legal", "required": True},
    {"id": "insurance_confirmed", "question": "Has an insurance broker confirmed applicable coverage in writing?", "category": "insurance", "required": True},
    {"id": "production_isolated", "question": "Is the system isolated from production data?", "category": "security", "required": True},
    {"id": "backups_verified", "question": "Are customer backups independent and verified?", "category": "operations", "required": True},
    {"id": "data_classified", "question": "Are permitted data and prohibited data written down?", "category": "data", "required": True},
    {"id": "acceptance_criteria", "question": "Are objective acceptance criteria documented?", "category": "technical", "required": True},
    {"id": "rollback_plan", "question": "Is there a rollback and incident-response plan?", "category": "operations", "required": True},
    {"id": "claims_accurate", "question": "Are marketing and technical claims accurate and approved?", "category": "compliance", "required": True},
    {"id": "terms_negotiated", "question": "Are liability cap, indemnity, warranty, data, security, and termination terms negotiated?", "category": "legal", "required": True},
    {"id": "experimental_acknowledged", "question": "Has the customer acknowledged the system experimental status?", "category": "compliance", "required": True},
]


class DealStopChecker:

    def __init__(self, db: Session):
        self.db = db

    def get_checklist(self) -> list[dict]:
        return CHECKLIST_ITEMS

    def evaluate(self, checklist_responses: dict) -> dict:
        """Evaluate checklist responses. Returns pass/fail with details."""
        passed = []
        failed = []
        warnings = []

        for item in CHECKLIST_ITEMS:
            response = checklist_responses.get(item["id"])
            if response is None:
                failed.append({"id": item["id"], "question": item["question"],
                    "status": "not_answered", "severity": "critical" if item["required"] else "warning"})
            elif response == False or response == "no":
                failed.append({"id": item["id"], "question": item["question"],
                    "status": "no", "severity": "critical" if item["required"] else "warning"})
            elif response == True or response == "yes":
                passed.append({"id": item["id"], "question": item["question"], "status": "yes"})
            else:
                warnings.append({"id": item["id"], "question": item["question"],
                    "status": "unclear", "response": str(response)})

        critical_failures = [f for f in failed if f["severity"] == "critical"]
        deal_allowed = len(critical_failures) == 0

        result = {
            "deal_allowed": deal_allowed,
            "total_items": len(CHECKLIST_ITEMS),
            "passed": len(passed),
            "failed": len(failed),
            "warnings": len(warnings),
            "critical_failures": critical_failures,
            "passed_items": passed,
            "failed_items": failed,
            "warning_items": warnings,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

        if not deal_allowed:
            logger.warning("DEAL BLOCKED: %d critical failures", len(critical_failures))
            for f in critical_failures:
                logger.warning("  BLOCKED: %s - %s", f["id"], f["question"])

        from app.audit.database_audit import append_audit_entry
        append_audit_entry(db=self.db, event_type="dealstop.evaluation",
            resource_type="deal", resource_id="evaluation", action="evaluate",
            details={"deal_allowed": deal_allowed, "passed": len(passed),
                "failed": len(failed), "critical_failures": [f["id"] for f in critical_failures]})

        return result