"""Approval Workflow API — Multi-level approval chain endpoints.

Endpoints:
- POST /api/approvals/request — Create approval request
- POST /api/approvals/{id}/decide — Submit approval decision
- GET /api/approvals/{id} — Get approval status
- GET /api/approvals/pending — List pending approvals
- GET /api/approvals/check — Check if transaction needs approval
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models import User
from app.security import get_current_user
from app.security.approval_workflow import ApprovalWorkflowEngine

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class ApprovalRequestCreate(BaseModel):
    transaction_type: str
    transaction_id: str
    amount: float
    currency: str = "USD"
    metadata: Optional[dict] = None


class ApprovalDecisionSubmit(BaseModel):
    decision: str  # "approved" or "rejected"
    comment: Optional[str] = None


@router.post("/request")
def create_approval_request(
    data: ApprovalRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Create an approval request for a transaction."""
    engine = ApprovalWorkflowEngine(db)
    org_id = getattr(user, 'org_id', None)

    # Check if approval is required
    if not engine.requires_approval(data.transaction_type, data.amount, org_id):
        return {
            "requires_approval": False,
            "message": "Transaction is below approval threshold",
            "auto_approved": True,
        }

    req = engine.create_approval_request(
        transaction_type=data.transaction_type,
        transaction_id=data.transaction_id,
        amount=data.amount,
        created_by=str(user.id),
        org_id=org_id or "default",
        currency=data.currency,
        metadata=data.metadata,
    )

    if req is None:
        return {"requires_approval": False, "auto_approved": True}

    return {
        "requires_approval": True,
        "request_id": req.id,
        "required_approvals": req.required_approvals,
        "deadline": req.deadline.isoformat() if req.deadline else None,
        "message": f"Transaction requires {req.required_approvals} approval(s)",
    }


@router.post("/{request_id}/decide")
def submit_decision(
    request_id: int,
    data: ApprovalDecisionSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request: Request = None,
):
    """Submit an approval decision."""
    engine = ApprovalWorkflowEngine(db)
    ip_address = request.client.host if request and request.client else None

    result = engine.submit_decision(
        request_id=request_id,
        approver_id=str(user.id),
        approver_email=getattr(user, 'email', ''),
        approver_role=getattr(user, 'role', 'analyst'),
        decision=data.decision,
        comment=data.comment,
        ip_address=ip_address,
    )

    return result


@router.get("/{request_id}")
def get_approval_status(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the full status of an approval request."""
    engine = ApprovalWorkflowEngine(db)
    status = engine.get_request_status(request_id)
    if not status:
        return {"error": "Approval request not found"}
    return status


@router.get("/")
def list_pending_approvals(
    status: str = Query("pending", description="Filter by status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List approval requests."""
    from app.security.approval_workflow import ApprovalRequest, ApprovalDecision
    query = db.query(ApprovalRequest)
    if status != "all":
        query = query.filter(ApprovalRequest.status == status)
    requests = query.order_by(ApprovalRequest.created_at.desc()).limit(50).all()

    return {
        "requests": [
            {
                "id": r.id,
                "transaction_type": r.transaction_type,
                "amount": r.transaction_amount,
                "status": r.status,
                "created_by": r.created_by,
                "required_approvals": r.required_approvals,
                "current_approvals": r.current_approvals,
                "deadline": r.deadline.isoformat() if r.deadline else None,
            }
            for r in requests
        ]
    }


@router.get("/check")
def check_approval_required(
    transaction_type: str = Query(...),
    amount: float = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Check if a transaction requires approval."""
    engine = ApprovalWorkflowEngine(db)
    org_id = getattr(user, 'org_id', None)
    required = engine.get_required_approvals(transaction_type, amount, org_id)

    return {
        "requires_approval": required > 0,
        "required_approvals": required,
        "thresholds": {
            "four_eyes": engine.FOUR_EYES_THRESHOLD,
            "six_eyes": engine.SIX_EYES_THRESHOLD,
            "eight_eyes": engine.EIGHT_EYES_THRESHOLD,
            "auto_approve": engine.MAX_AUTO_APPROVE,
        },
        "amount": amount,
        "transaction_type": transaction_type,
    }
