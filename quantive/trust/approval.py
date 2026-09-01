"""Approval workflow — Pillar 6, Pillar 3.

Multi-level approval with separation of duties. No user can both create and approve.
Every recommendation must pass through approval before execution.
Tracks: who proposed, who approved, who rejected, conditions, expiry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Literal

from quantive.trust.audit import AuditTrail, ActionType


class ApprovalLevel(str, Enum):
    ANALYST = "analyst"
    MANAGER = "manager"
    DIRECTOR = "director"
    MINISTER = "minister"


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"


@dataclass
class ApprovalStep:
    level: ApprovalLevel
    required_approver: str | None = None
    actual_approver: str | None = None
    status: Literal["pending", "approved", "rejected", "skipped"] = "pending"
    timestamp: datetime | None = None
    conditions: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class Proposal:
    """A recommendation that requires approval before execution."""
    id: str
    title: str
    description: str
    created_by: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: ProposalStatus = ProposalStatus.DRAFT
    approval_steps: list[ApprovalStep] = field(default_factory=list)
    expires_at: datetime | None = None
    execution_result: dict | None = None
    metadata: dict = field(default_factory=dict)


class ApprovalWorkflow:
    """Multi-level approval with separation of duties enforcement.

    Workflow:
    1. Analyst creates proposal (DRAFT → PENDING)
    2. Manager reviews and approves/rejects
    3. Director reviews (if required)
    4. Minister reviews (if required for high-impact)
    5. Approved → can be executed

    Separation of duties:
    - Creator cannot approve their own proposal
    - Approver cannot be the executor
    """

    def __init__(
        self,
        audit: AuditTrail | None = None,
        levels: list[ApprovalLevel] | None = None,
        expiry_hours: int = 72,
    ) -> None:
        self.audit = audit or AuditTrail()
        self.levels = levels or [ApprovalLevel.ANALYST, ApprovalLevel.MANAGER]
        self.expiry_hours = expiry_hours
        self._proposals: dict[str, Proposal] = {}

    def create_proposal(
        self,
        *,
        proposal_id: str,
        title: str,
        description: str,
        created_by: str,
        approval_levels: list[ApprovalLevel] | None = None,
        expires_in_hours: int | None = None,
        metadata: dict | None = None,
    ) -> Proposal:
        """Create a new proposal in DRAFT status."""
        levels = approval_levels or self.levels
        steps = [ApprovalStep(level=level) for level in levels]

        proposal = Proposal(
            id=proposal_id,
            title=title,
            description=description,
            created_by=created_by,
            status=ProposalStatus.DRAFT,
            approval_steps=steps,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours or self.expiry_hours),
            metadata=metadata or {},
        )

        self._proposals[proposal_id] = proposal

        self.audit.record(
            actor=created_by,
            action=ActionType.CREATE,
            target_type="proposal",
            target_id=proposal_id,
            details={"title": title, "description": description},
        )

        return proposal

    def submit(self, proposal_id: str, submitted_by: str) -> Proposal:
        """Submit proposal for approval (DRAFT → PENDING)."""
        proposal = self._proposals[proposal_id]
        if proposal.status != ProposalStatus.DRAFT:
            raise ValueError(f"Cannot submit proposal in status {proposal.status.value}")

        proposal.status = ProposalStatus.PENDING

        self.audit.record(
            actor=submitted_by,
            action=ActionType.MODIFY,
            target_type="proposal",
            target_id=proposal_id,
            details={"status_change": "draft → pending"},
        )

        return proposal

    def approve(
        self,
        proposal_id: str,
        approver: str,
        level: ApprovalLevel,
        notes: str = "",
    ) -> Proposal:
        """Approve at a specific level. Cannot approve own proposal (separation of duties)."""
        proposal = self._proposals[proposal_id]

        if proposal.status not in (ProposalStatus.PENDING, ProposalStatus.DRAFT):
            raise ValueError(f"Cannot approve proposal in status {proposal.status.value}")

        if proposal.created_by == approver:
            raise PermissionError(
                f"Separation of duties: {approver} created this proposal and cannot approve it"
            )

        if proposal.expires_at and datetime.now(timezone.utc) > proposal.expires_at:
            proposal.status = ProposalStatus.EXPIRED
            raise ValueError("Proposal has expired")

        # find the step for this level
        step_found = False
        all_approved = True
        for step in proposal.approval_steps:
            if step.level == level:
                if step.status != "pending":
                    raise ValueError(f"Level {level.value} already {step.status}")
                step.actual_approver = approver
                step.status = "approved"
                step.timestamp = datetime.now(timezone.utc)
                step.notes = notes
                step_found = True
            if step.status != "approved" and step.status != "skipped":
                all_approved = False

        if not step_found:
            raise ValueError(f"Level {level.value} not in approval chain")

        self.audit.record(
            actor=approver,
            action=ActionType.APPROVE,
            target_type="proposal",
            target_id=proposal_id,
            details={"level": level.value, "notes": notes},
        )

        if all_approved:
            proposal.status = ProposalStatus.APPROVED
            self.audit.record(
                actor="system",
                action=ActionType.APPROVE,
                target_type="proposal",
                target_id=proposal_id,
                details={"status_change": "pending → approved", "all_levels_complete": True},
            )

        return proposal

    def reject(
        self,
        proposal_id: str,
        rejector: str,
        level: ApprovalLevel,
        reason: str = "",
    ) -> Proposal:
        """Reject at a specific level."""
        proposal = self._proposals[proposal_id]
        if proposal.status not in (ProposalStatus.PENDING, ProposalStatus.DRAFT):
            raise ValueError(f"Cannot reject proposal in status {proposal.status.value}")

        for step in proposal.approval_steps:
            if step.level == level:
                step.actual_approver = rejector
                step.status = "rejected"
                step.timestamp = datetime.now(timezone.utc)
                step.notes = reason
                break

        proposal.status = ProposalStatus.REJECTED

        self.audit.record(
            actor=rejector,
            action=ActionType.REJECT,
            target_type="proposal",
            target_id=proposal_id,
            details={"level": level.value, "reason": reason},
        )

        return proposal

    def mark_executed(self, proposal_id: str, executor: str, result: dict) -> Proposal:
        """Mark approved proposal as executed. Executor cannot be any approver."""
        proposal = self._proposals[proposal_id]
        if proposal.status != ProposalStatus.APPROVED:
            raise ValueError(f"Cannot execute proposal in status {proposal.status.value}")

        # separation: executor cannot be any approver
        for step in proposal.approval_steps:
            if step.actual_approver == executor:
                raise PermissionError(
                    f"Separation of duties: {executor} approved this proposal and cannot execute it"
                )

        proposal.status = ProposalStatus.EXECUTED
        proposal.execution_result = result

        self.audit.record(
            actor=executor,
            action=ActionType.EXECUTE,
            target_type="proposal",
            target_id=proposal_id,
            details={"result": result},
        )

        return proposal

    def get(self, proposal_id: str) -> Proposal | None:
        return self._proposals.get(proposal_id)

    def list_proposals(
        self,
        *,
        status: ProposalStatus | None = None,
        created_by: str | None = None,
    ) -> list[Proposal]:
        results = list(self._proposals.values())
        if status is not None:
            results = [p for p in results if p.status == status]
        if created_by is not None:
            results = [p for p in results if p.created_by == created_by]
        return results
