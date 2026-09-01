"""Trust foundation — Pillars 2, 3, 5, 6, 9.

Audit trail, approval workflows, assumption tracking, recommendation explainability.

Every recommendation in Quantive passes through this layer before reaching users.
"""
from quantive.trust.audit import AuditTrail, AuditEntry, ActionType
from quantive.trust.approval import ApprovalWorkflow, Proposal, ApprovalLevel, ProposalStatus
from quantive.trust.assumptions import AssumptionRegistry, Assumption, AssumptionSet
from quantive.trust.explainability import (
    ExplainabilityEngine,
    ExplainableRecommendation,
    DataSource,
    Risk,
    Alternative,
    AssumptionRef,
)

__all__ = [
    "AuditTrail", "AuditEntry", "ActionType",
    "ApprovalWorkflow", "Proposal", "ApprovalLevel", "ProposalStatus",
    "AssumptionRegistry", "Assumption", "AssumptionSet",
    "ExplainabilityEngine", "ExplainableRecommendation",
    "DataSource", "Risk", "Alternative", "AssumptionRef",
]
