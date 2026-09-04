"""Fraud Risk Scoring for Workflows."""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.fraud")


class FraudRiskScorer:

    def __init__(self, db: Session):
        self.db = db

    def score_workflow(self, transaction_id, creator_id, approvers, amount, org_id=None):
        score = 0
        factors = []

        # Factor 1: Single person in multiple roles
        all_users = [creator_id] + approvers
        unique = set(all_users)
        if len(unique) < len(all_users):
            score += 40
            factors.append("duplicate_users_in_chain")

        # Factor 2: High amount without sufficient approvals
        if amount > 50_000_000 and len(approvers) < 3:
            score += 25
            factors.append("insufficient_approvals_for_amount")

        # Factor 3: Same person approves repeatedly
        from collections import Counter
        counts = Counter(approvers)
        for user, count in counts.items():
            if count >= 2:
                score += 15 * (count - 1)
                factors.append(f"user_{user[:8]}_approves_{count}_times")

        # Factor 4: No independent reviewer
        if len(set(approvers)) < 2:
            score += 20
            factors.append("no_independent_review")

        risk_level = "low" if score < 20 else "medium" if score < 50 else "high" if score < 80 else "critical"

        return {
            "transaction_id": transaction_id,
            "fraud_risk_score": min(score, 100),
            "risk_level": risk_level,
            "factors": factors,
            "control_strength": self._assess_controls(approvers, amount),
            "audit_coverage": self._assess_audit_coverage(transaction_id),
            "assessed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _assess_controls(self, approvers, amount):
        if len(approvers) >= 4 and amount > 500_000_000:
            return "maximum"
        elif len(approvers) >= 3 and amount > 50_000_000:
            return "high"
        elif len(approvers) >= 2:
            return "standard"
        elif len(approvers) >= 1:
            return "basic"
        return "none"

    def _assess_audit_coverage(self, transaction_id):
        from app.models import DatabaseAuditEntry
        count = self.db.query(DatabaseAuditEntry).filter(DatabaseAuditEntry.resource_id == transaction_id).count()
        if count >= 5:
            return "complete"
        elif count >= 3:
            return "good"
        elif count >= 1:
            return "partial"
        return "none"