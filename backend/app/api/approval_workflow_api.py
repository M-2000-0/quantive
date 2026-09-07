"""Approval Workflow API endpoints.

Exposes multi-level approval workflow management for government operations.
Enforces the "four-eyes principle" and configurable approval chains.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/approval-workflow", tags=["approval-workflow"])


# ── Request Models ─────────────────────────────────────────────────

class ApprovalRequestModel(BaseModel):
    transaction_type: str = Field(..., description="Transaction type requiring approval")
    transaction_id: str = Field(..., description="ID of the transaction to approve")
    metadata: dict | None = Field(default=None, description="Additional context")


class ApprovalActionModel(BaseModel):
    comments: str = Field(default="", max_length=2000)


class DenialModel(BaseModel):
    reason: str = Field(..., min_length=10, max_length=2000)


# ── API Endpoints ──────────────────────────────────────────────────

@router.post("/request")
def request_approval(
    request: ApprovalRequestModel,
    user: User = Depends(get_current_user),
):
    """Create a new approval request."""
    from quantive.trust.approval_workflow import (
        TransactionType,
        get_approval_engine,
    )

    engine = get_approval_engine()

    # Map transaction type
    tx_type_map = {e.value: e for e in TransactionType}
    tx_type = tx_type_map.get(request.transaction_type)
    if not tx_type:
        raise HTTPException(400, f"Invalid transaction type: {request.transaction_type}")

    try:
        approval_request = engine.request_approval(
            transaction_type=tx_type,
            transaction_id=request.transaction_id,
            requester_id=user.id,
            requester_email=user.email,
            metadata=request.metadata,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "request_id": approval_request.request_id,
        "transaction_type": approval_request.transaction_type.value,
        "transaction_id": approval_request.transaction_id,
        "current_level": approval_request.current_level,
        "required_levels": approval_request.required_levels,
        "status": approval_request.status.value,
        "expires_at": approval_request.expires_at.isoformat() if approval_request.expires_at else None,
        "message": "Approval request created. Awaiting review.",
    }


@router.post("/{request_id}/approve")
def approve_request(
    request_id: str,
    body: ApprovalActionModel,
    user: User = Depends(get_current_user),
):
    """Approve a request at the current level."""
    from quantive.trust.approval_workflow import get_approval_engine

    engine = get_approval_engine()

    try:
        approved = engine.approve_request(
            request_id=request_id,
            approver_id=user.id,
            approver_email=user.email,
            approver_role=user.role,
            comments=body.comments,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "request_id": approved.request_id,
        "status": approved.status.value,
        "current_level": approved.current_level,
        "required_levels": approved.required_levels,
        "approvals_count": len(approved.approvals),
        "message": "Approved" if approved.status.value == "approved" else "Level approved, awaiting next level",
    }


@router.post("/{request_id}/deny")
def deny_request(
    request_id: str,
    body: DenialModel,
    user: User = Depends(get_current_user),
):
    """Deny an approval request."""
    from quantive.trust.approval_workflow import get_approval_engine

    engine = get_approval_engine()

    try:
        denied = engine.deny_request(
            request_id=request_id,
            approver_id=user.id,
            approver_email=user.email,
            reason=body.reason,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "request_id": denied.request_id,
        "status": denied.status.value,
        "message": "Request denied",
    }


@router.post("/{request_id}/cancel")
def cancel_request(
    request_id: str,
    user: User = Depends(get_current_user),
):
    """Cancel a pending approval request."""
    from quantive.trust.approval_workflow import get_approval_engine

    engine = get_approval_engine()

    try:
        cancelled = engine.cancel_request(
            request_id=request_id,
            canceler_id=user.id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return {
        "request_id": cancelled.request_id,
        "status": cancelled.status.value,
        "message": "Request cancelled",
    }


@router.get("/pending")
def get_pending_approvals(
    role: str | None = Query(None, description="Filter by role"),
    user: User = Depends(get_current_user),
):
    """Get all pending approvals for the current user's role."""
    from quantive.trust.approval_workflow import get_approval_engine

    engine = get_approval_engine()
    target_role = role or user.role
    pending = engine.get_pending_approvals(approver_role=target_role)

    return {
        "total": len(pending),
        "requests": [
            {
                "request_id": r.request_id,
                "transaction_type": r.transaction_type.value,
                "transaction_id": r.transaction_id,
                "requester_id": r.requester_id,
                "current_level": r.current_level,
                "required_levels": r.required_levels,
                "created_at": r.created_at.isoformat(),
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in pending
        ],
    }


@router.get("/request/{request_id}")
def get_request_status(
    request_id: str,
    user: User = Depends(get_current_user),
):
    """Get the status of an approval request."""
    from quantive.trust.approval_workflow import get_approval_engine

    engine = get_approval_engine()
    request = engine.get_request_status(request_id)

    if not request:
        raise HTTPException(404, "Request not found")

    return {
        "request_id": request.request_id,
        "transaction_type": request.transaction_type.value,
        "transaction_id": request.transaction_id,
        "requester_id": request.requester_id,
        "current_level": request.current_level,
        "required_levels": request.required_levels,
        "status": request.status.value,
        "created_at": request.created_at.isoformat(),
        "expires_at": request.expires_at.isoformat() if request.expires_at else None,
        "approvals": request.approvals,
        "metadata": request.metadata,
    }


@router.get("/chains")
def list_approval_chains(
    user: User = Depends(get_current_user),
):
    """List all configured approval chains."""
    from quantive.trust.approval_workflow import get_approval_engine

    engine = get_approval_engine()
    chains = engine.list_chains()

    return {"chains": chains}


@router.get("/chains/{transaction_type}")
def get_chain_config(
    transaction_type: str,
    user: User = Depends(get_current_user),
):
    """Get the approval chain configuration for a transaction type."""
    from quantive.trust.approval_workflow import (
        TransactionType,
        get_approval_engine,
    )

    engine = get_approval_engine()

    tx_type_map = {e.value: e for e in TransactionType}
    tx_type = tx_type_map.get(transaction_type)
    if not tx_type:
        raise HTTPException(400, f"Invalid transaction type: {transaction_type}")

    chain = engine.get_chain_config(tx_type)
    if not chain:
        raise HTTPException(404, "No approval chain configured")

    return {
        "transaction_type": chain.transaction_type.value,
        "levels": [
            {
                "level": level.level.value,
                "required_role": level.required_role,
                "timeout_hours": level.timeout_hours,
            }
            for level in chain.levels
        ],
        "is_active": chain.is_active,
    }


@router.get("/statistics")
def get_statistics(
    user: User = Depends(get_current_user),
):
    """Get approval workflow statistics."""
    from quantive.trust.approval_workflow import get_approval_engine

    engine = get_approval_engine()
    stats = engine.get_statistics()

    return stats
