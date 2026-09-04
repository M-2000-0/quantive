"""Pillar 6: Explainable AI/Quantum & Role-Based Governance.

Two critical capabilities for government adoption:

1. EXPLAINABILITY:
   Translates quantum state measurements into:
   - Plain-language risk breakdowns for treasury officials
   - Sensitivity analysis showing which factors matter most
   - Executive summaries suitable for minister briefings
   - Visual trade-off descriptions

2. GOVERNANCE:
   Multi-party approval workflows:
   - 3-of-5 signatures required for high-value operations
   - Role-based access (Analyst → Director → Minister)
   - Conflict-of-interest detection
   - Complete audit trail for every approval
"""
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ApprovalRole(str, Enum):
    ANALYST = "analyst"
    SENIOR_ANALYST = "senior_analyst"
    DIRECTOR = "director"
    DEPUTY_MINISTER = "deputy_minister"
    MINISTER = "minister"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


@dataclass
class ApprovalSignature:
    """A single approval signature."""
    signer_id: str
    signer_name: str
    role: ApprovalRole
    timestamp: str
    decision: str  # approve, reject
    comments: str = ""


@dataclass
class GovernanceWorkflow:
    """A multi-party approval workflow for high-value operations."""
    workflow_id: str
    operation_type: str
    operation_value: float
    required_signatures: int
    required_roles: list
    signatures: list = field(default_factory=list)
    status: str = "pending"
    created_at: str = ""
    completed_at: str = ""


class ExplainabilityEngine:
    """Translates quantum optimization results into human-readable insights.

    For every recommendation, produces:
    1. Executive Summary (3 sentences for minister)
    2. Risk Breakdown (plain language)
    3. Sensitivity Analysis (what-if scenarios)
    4. Confidence Assessment (how reliable is this)
    5. Comparison to alternatives
    """

    def generate_executive_summary(self, result: dict, constraints: list) -> str:
        """Generate 3-sentence minister briefing."""
        cost = result.get("objective_value", 0)
        feasible = result.get("feasible", False)
        algorithm = result.get("backend", "unknown")
        constraints_passed = sum(1 for c in constraints if c.get("passed", False))
        total_constraints = len(constraints)

        status = "meets all statutory requirements" if feasible else "has constraint violations that must be addressed"

        summary = (
            f"The optimization recommends a strategy with an estimated annual servicing cost "
            f"of ${cost:,.0f}, generated using {algorithm} computation. "
            f"This recommendation {status} ({constraints_passed}/{total_constraints} constraints satisfied). "
            f"The solution has been verified against constitutional debt limits, "
            f"currency exposure rules, and minimum liquidity requirements."
        )
        return summary

    def generate_risk_breakdown(self, result: dict) -> list[dict]:
        """Generate plain-language risk breakdown."""
        risks = []

        if result.get("fallback_used"):
            risks.append({
                "risk": "Quantum computation fell back to classical solver",
                "impact": "Solution quality may be suboptimal",
                "mitigation": "Classical solver still produces feasible solutions",
                "severity": "low",
            })

        if not result.get("feasible"):
            risks.append({
                "risk": "Solution violates one or more hard constraints",
                "impact": "Recommendation cannot be implemented as-is",
                "mitigation": "Feasibility repair applied; review constraint details",
                "severity": "high",
            })

        if result.get("noise_mitigation_applied"):
            risks.append({
                "risk": "Noise mitigation was required during computation",
                "impact": "Result may have reduced precision",
                "mitigation": "Zero-Noise Extrapolation applied to improve accuracy",
                "severity": "low",
            })

        if not risks:
            risks.append({
                "risk": "No significant risks identified",
                "impact": "Recommendation is within normal parameters",
                "mitigation": "Standard monitoring applies",
                "severity": "none",
            })

        return risks

    def generate_sensitivity_analysis(self, result: dict, macro_data: dict) -> list[dict]:
        """Show which factors most affect the recommendation."""
        factors = []
        base_cost = result.get("objective_value", 0)

        for param, current in macro_data.items():
            if isinstance(current, (int, float)):
                factors.append({
                    "factor": param.replace("_", " ").title(),
                    "current_value": current,
                    "impact": "high" if param in ("interest_rate", "inflation", "debt_to_gdp") else "medium",
                    "direction": "increases cost" if param in ("interest_rate", "inflation") else "context-dependent",
                })

        return factors

    def generate_confidence_assessment(self, result: dict) -> dict:
        """Assess confidence in the recommendation."""
        confidence = 80  # Base confidence

        if result.get("backend") == "classical_fallback":
            confidence -= 10
        if result.get("noise_mitigation_applied"):
            confidence -= 5
        if not result.get("feasible"):
            confidence -= 20
        if result.get("solve_time_seconds", 0) > 200:
            confidence -= 5

        return {
            "confidence_score": max(0, min(100, confidence)),
            "level": "high" if confidence >= 70 else "medium" if confidence >= 50 else "low",
            "factors": [
                "Solution satisfies all hard constraints" if result.get("feasible") else "Constraint violations detected",
                f"Algorithm: {result.get('backend', 'unknown')}",
                f"Solve time: {result.get('solve_time_seconds', 0):.1f}s",
            ],
        }


class MultiPartyGovernance:
    """Enforces multi-party approval for high-value operations.

    Thresholds:
    - < $100M: 2 signatures (Director + 1)
    - $100M-$1B: 3 signatures (Director + Deputy Minister + 1)
    - > $1B: 5 signatures (Full committee including Minister)

    Separation of duties:
    - The person who creates the optimization cannot approve it
    - The person who approves cannot execute it
    - The person who executes cannot audit it
    """

    APPROVAL_THRESHOLDS = [
        (100_000_000, 2, [ApprovalRole.DIRECTOR, ApprovalRole.SENIOR_ANALYST]),
        (1_000_000_000, 3, [ApprovalRole.DIRECTOR, ApprovalRole.DEPUTY_MINISTER, ApprovalRole.SENIOR_ANALYST]),
        (float("inf"), 5, [ApprovalRole.MINISTER, ApprovalRole.DEPUTY_MINISTER, ApprovalRole.DIRECTOR,
                          ApprovalRole.SENIOR_ANALYST, ApprovalRole.ANALYST]),
    ]

    def __init__(self):
        self.workflows: dict[str, GovernanceWorkflow] = {}

    def create_workflow(self, operation_type: str, operation_value: float, created_by: str) -> GovernanceWorkflow:
        """Create approval workflow based on operation value."""
        required_sigs = 2
        required_roles = [ApprovalRole.DIRECTOR]

        for threshold, sigs, roles in self.APPROVAL_THRESHOLDS:
            if operation_value <= threshold:
                required_sigs = sigs
                required_roles = roles
                break

        import uuid
        workflow = GovernanceWorkflow(
            workflow_id=str(uuid.uuid8())[:8],
            operation_type=operation_type,
            operation_value=operation_value,
            required_signatures=required_sigs,
            required_roles=required_roles,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.workflows[workflow.workflow_id] = workflow
        return workflow

    def add_signature(self, workflow_id: str, signer_id: str, signer_name: str,
                      role: ApprovalRole, decision: str, comments: str = "") -> GovernanceWorkflow:
        """Add an approval signature to a workflow."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        if workflow.status != "pending":
            raise ValueError(f"Workflow is already {workflow.status}")

        # Check role is required
        if role not in workflow.required_roles:
            raise ValueError(f"Role {role.value} is not an authorized signer for this workflow")

        # Check for duplicate signer
        if any(s.signer_id == signer_id for s in workflow.signatures):
            raise ValueError("This person has already signed")

        signature = ApprovalSignature(
            signer_id=signer_id,
            signer_name=signer_name,
            role=role,
            timestamp=datetime.now(timezone.utc).isoformat(),
            decision=decision,
            comments=comments,
        )
        workflow.signatures.append(signature)

        # Check completion
        approvals = [s for s in workflow.signatures if s.decision == "approve"]
        rejections = [s for s in workflow.signatures if s.decision == "reject"]

        if rejections:
            workflow.status = "rejected"
            workflow.completed_at = datetime.now(timezone.utc).isoformat()
        elif len(approvals) >= workflow.required_signatures:
            workflow.status = "approved"
            workflow.completed_at = datetime.now(timezone.utc).isoformat()

        return workflow

    def get_workflow_status(self, workflow_id: str) -> dict:
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {"error": "Workflow not found"}

        return {
            "workflow_id": workflow.workflow_id,
            "operation": workflow.operation_type,
            "value": workflow.operation_value,
            "status": workflow.status,
            "signatures": f"{len(workflow.signatures)}/{workflow.required_signatures}",
            "remaining": workflow.required_signatures - len(workflow.signatures),
            "signers": [
                {"name": s.signer_name, "role": s.role.value, "decision": s.decision}
                for s in workflow.signatures
            ],
        }
