"""Multi-Level Approval Workflow Enforcement.

Ensures no action is taken without proper authorization.
Implements the "four-eyes principle" and configurable approval chains.

This addresses the "No Approval Workflow Implementation" critical issue
from the Government Procurement Stress Test.
"""

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ApprovalStatus(str, Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ApprovalLevel(str, Enum):
    """Levels of approval authority."""
    ANALYST = "analyst"
    MANAGER = "manager"
    DIRECTOR = "director"
    MINISTER = "minister"
    CABINET = "cabinet"


class TransactionType(str, Enum):
    """Types of transactions requiring approval."""
    OPTIMIZATION_RUN = "optimization_run"
    STRATEGY_RECOMMENDATION = "strategy_recommendation"
    DEBT_ISSUANCE = "debt_issuance"
    REFINANCING = "refinancing"
    HEDGE_EXECUTION = "hedge_execution"
    BUDGET_CHANGE = "budget_change"
    POLICY_CHANGE = "policy_change"
    DATA_EXPORT = "data_export"
    CONFIG_CHANGE = "config_change"


@dataclass
class ApprovalLevelConfig:
    """Configuration for an approval level."""
    level: ApprovalLevel
    required_role: str
    timeout_hours: int = 72
    escalation_contacts: list[str] = field(default_factory=list)
    auto_approve_conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalChain:
    """A complete approval chain for a transaction type."""
    transaction_type: TransactionType
    levels: list[ApprovalLevelConfig]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


@dataclass
class ApprovalRequest:
    """A request for approval."""
    request_id: str
    transaction_type: TransactionType
    transaction_id: str
    requester_id: str
    requester_email: str
    current_level: int
    required_levels: int
    status: ApprovalStatus
    created_at: datetime
    expires_at: datetime | None
    approvals: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ApprovalWorkflowEngine:
    """Enforces multi-level approval workflows."""

    def __init__(self):
        self._chains: dict[TransactionType, ApprovalChain] = {}
        self._requests: dict[str, ApprovalRequest] = {}
        self._setup_default_chains()

    def _setup_default_chains(self):
        """Set up default approval chains for government operations."""
        # Optimization run: Analyst → Manager
        self._chains[TransactionType.OPTIMIZATION_RUN] = ApprovalChain(
            transaction_type=TransactionType.OPTIMIZATION_RUN,
            levels=[
                ApprovalLevelConfig(level=ApprovalLevel.ANALYST, required_role="analyst", timeout_hours=24),
                ApprovalLevelConfig(level=ApprovalLevel.MANAGER, required_role="manager", timeout_hours=48),
            ],
        )

        # Strategy recommendation: Analyst → Manager → Director
        self._chains[TransactionType.STRATEGY_RECOMMENDATION] = ApprovalChain(
            transaction_type=TransactionType.STRATEGY_RECOMMENDATION,
            levels=[
                ApprovalLevelConfig(level=ApprovalLevel.ANALYST, required_role="analyst", timeout_hours=24),
                ApprovalLevelConfig(level=ApprovalLevel.MANAGER, required_role="manager", timeout_hours=48),
                ApprovalLevelConfig(level=ApprovalLevel.DIRECTOR, required_role="director", timeout_hours=72),
            ],
        )

        # Debt issuance: Manager → Director → Minister
        self._chains[TransactionType.DEBT_ISSUANCE] = ApprovalChain(
            transaction_type=TransactionType.DEBT_ISSUANCE,
            levels=[
                ApprovalLevelConfig(level=ApprovalLevel.MANAGER, required_role="manager", timeout_hours=24),
                ApprovalLevelConfig(level=ApprovalLevel.DIRECTOR, required_role="director", timeout_hours=48),
                ApprovalLevelConfig(level=ApprovalLevel.MINISTER, required_role="minister", timeout_hours=168),
            ],
        )

        # Refinancing: Manager → Director → Minister
        self._chains[TransactionType.REFINANCING] = ApprovalChain(
            transaction_type=TransactionType.REFINANCING,
            levels=[
                ApprovalLevelConfig(level=ApprovalLevel.MANAGER, required_role="manager", timeout_hours=24),
                ApprovalLevelConfig(level=ApprovalLevel.DIRECTOR, required_role="director", timeout_hours=48),
                ApprovalLevelConfig(level=ApprovalLevel.MINISTER, required_role="minister", timeout_hours=168),
            ],
        )

        # Hedge execution: Manager → Director
        self._chains[TransactionType.HEDGE_EXECUTION] = ApprovalChain(
            transaction_type=TransactionType.HEDGE_EXECUTION,
            levels=[
                ApprovalLevelConfig(level=ApprovalLevel.MANAGER, required_role="manager", timeout_hours=24),
                ApprovalLevelConfig(level=ApprovalLevel.DIRECTOR, required_role="director", timeout_hours=48),
            ],
        )

        # Policy change: Director → Minister → Cabinet
        self._chains[TransactionType.POLICY_CHANGE] = ApprovalChain(
            transaction_type=TransactionType.POLICY_CHANGE,
            levels=[
                ApprovalLevelConfig(level=ApprovalLevel.DIRECTOR, required_role="director", timeout_hours=48),
                ApprovalLevelConfig(level=ApprovalLevel.MINISTER, required_role="minister", timeout_hours=168),
                ApprovalLevelConfig(level=ApprovalLevel.CABINET, required_role="cabinet", timeout_hours=336),
            ],
        )

    def check_separation_of_duties(
        self,
        creator_id: str,
        approver_id: str,
    ) -> bool:
        """Verify that creator and approver are different people (four-eyes principle)."""
        return creator_id != approver_id

    def request_approval(
        self,
        transaction_type: TransactionType,
        transaction_id: str,
        requester_id: str,
        requester_email: str,
        metadata: dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        """Create a new approval request."""
        chain = self._chains.get(transaction_type)
        if not chain or not chain.is_active:
            raise ValueError(f"No active approval chain for {transaction_type.value}")

        request_id = f"apr-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"

        request = ApprovalRequest(
            request_id=request_id,
            transaction_type=transaction_type,
            transaction_id=transaction_id,
            requester_id=requester_id,
            requester_email=requester_email,
            current_level=0,
            required_levels=len(chain.levels),
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + __import__("datetime").timedelta(
                hours=sum(level.timeout_hours for level in chain.levels)
            ),
            metadata=metadata or {},
        )

        self._requests[request_id] = request
        return request

    def approve_request(
        self,
        request_id: str,
        approver_id: str,
        approver_email: str,
        approver_role: str,
        comments: str = "",
    ) -> ApprovalRequest:
        """Approve a request at the current level."""
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending")

        chain = self._chains.get(request.transaction_type)
        if not chain:
            raise ValueError(f"No approval chain for {request.transaction_type.value}")

        # Check separation of duties
        if not self.check_separation_of_duties(request.requester_id, approver_id):
            raise ValueError("Creator and approver must be different (four-eyes principle)")

        # Check role matches required level
        required_role = chain.levels[request.current_level].required_role
        if approver_role != required_role and approver_role != "admin":
            raise ValueError(f"Approver role {approver_role} does not match required {required_role}")

        # Record approval
        approval = {
            "approver_id": approver_id,
            "approver_email": approver_email,
            "approver_role": approver_role,
            "level": request.current_level,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "comments": comments,
        }
        request.approvals.append(approval)

        # Move to next level or complete
        request.current_level += 1
        if request.current_level >= request.required_levels:
            request.status = ApprovalStatus.APPROVED
        else:
            # Update expiry for next level
            next_level_timeout = chain.levels[request.current_level].timeout_hours
            request.expires_at = datetime.now(timezone.utc) + __import__("datetime").timedelta(
                hours=next_level_timeout
            )

        return request

    def deny_request(
        self,
        request_id: str,
        approver_id: str,
        approver_email: str,
        reason: str,
    ) -> ApprovalRequest:
        """Deny a request."""
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Request {request_id} is not pending")

        request.status = ApprovalStatus.DENIED
        request.approvals.append({
            "approver_id": approver_id,
            "approver_email": approver_email,
            "action": "denied",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        })

        return request

    def cancel_request(
        self,
        request_id: str,
        canceler_id: str,
    ) -> ApprovalRequest:
        """Cancel a request (only by requester or admin)."""
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")

        if request.requester_id != canceler_id:
            raise ValueError("Only the requester can cancel")

        request.status = ApprovalStatus.CANCELLED
        return request

    def get_pending_approvals(
        self,
        approver_role: str,
    ) -> list[ApprovalRequest]:
        """Get all pending approvals for a specific role."""
        pending = []
        for request in self._requests.values():
            if request.status != ApprovalStatus.PENDING:
                continue

            chain = self._chains.get(request.transaction_type)
            if not chain:
                continue

            required_role = chain.levels[request.current_level].required_role
            if required_role == approver_role or approver_role == "admin":
                pending.append(request)

        return pending

    def get_request_status(self, request_id: str) -> ApprovalRequest | None:
        """Get the status of an approval request."""
        return self._requests.get(request_id)

    def get_chain_config(self, transaction_type: TransactionType) -> ApprovalChain | None:
        """Get the approval chain configuration for a transaction type."""
        return self._chains.get(transaction_type)

    def list_chains(self) -> list[dict]:
        """List all configured approval chains."""
        chains = []
        for tx_type, chain in self._chains.items():
            chains.append({
                "transaction_type": tx_type.value,
                "levels": [
                    {
                        "level": level.level.value,
                        "required_role": level.required_role,
                        "timeout_hours": level.timeout_hours,
                    }
                    for level in chain.levels
                ],
                "is_active": chain.is_active,
            })
        return chains

    def get_statistics(self) -> dict:
        """Get approval workflow statistics."""
        total = len(self._requests)
        by_status = {}
        by_type = {}

        for request in self._requests.values():
            by_status[request.status.value] = by_status.get(request.status.value, 0) + 1
            by_type[request.transaction_type.value] = by_type.get(request.transaction_type.value, 0) + 1

        return {
            "total_requests": total,
            "by_status": by_status,
            "by_type": by_type,
            "active_chains": sum(1 for c in self._chains.values() if c.is_active),
        }


# Global approval engine instance
_approval_engine: ApprovalWorkflowEngine | None = None


def get_approval_engine() -> ApprovalWorkflowEngine:
    """Get the global approval workflow engine."""
    global _approval_engine
    if _approval_engine is None:
        _approval_engine = ApprovalWorkflowEngine()
    return _approval_engine
