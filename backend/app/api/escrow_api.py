"""Source Code Escrow API endpoints.

Exposes escrow agreement management for government contracts.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/escrow", tags=["escrow"])


class EscrowPartyModel(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(..., description="depositor, beneficiary, or escrow_agent")
    address: str = Field(..., min_length=10)
    contact_name: str = Field(..., min_length=2)
    contact_email: str = Field(..., min_length=5)
    contact_phone: str = Field(default="")


class CreateAgreementRequest(BaseModel):
    depositor: EscrowPartyModel
    beneficiary: EscrowPartyModel
    escrow_agent: EscrowPartyModel
    software_description: str = Field(..., min_length=10)
    version: str = Field(..., min_length=1)
    repository_url: str = Field(..., min_length=10)


class ReleaseTriggerRequest(BaseModel):
    condition: str = Field(..., description="Release condition")
    evidence: str = Field(..., min_length=20)


class UpdateSourceRequest(BaseModel):
    version: str = Field(..., min_length=1)
    commit_hash: str = Field(..., min_length=7)
    changelog: str = Field(..., min_length=10)


@router.post("/agreements")
def create_agreement(
    request: CreateAgreementRequest,
    user: User = Depends(get_current_user),
):
    """Create a new escrow agreement."""
    from quantive.government.escrow import EscrowParty, get_escrow_manager

    manager = get_escrow_manager()

    depositor = EscrowParty(
        name=request.depositor.name,
        role=request.depositor.role,
        address=request.depositor.address,
        contact_name=request.depositor.contact_name,
        contact_email=request.depositor.contact_email,
        contact_phone=request.depositor.contact_phone,
    )

    beneficiary = EscrowParty(
        name=request.beneficiary.name,
        role=request.beneficiary.role,
        address=request.beneficiary.address,
        contact_name=request.beneficiary.contact_name,
        contact_email=request.beneficiary.contact_email,
        contact_phone=request.beneficiary.contact_phone,
    )

    escrow_agent = EscrowParty(
        name=request.escrow_agent.name,
        role=request.escrow_agent.role,
        address=request.escrow_agent.address,
        contact_name=request.escrow_agent.contact_name,
        contact_email=request.escrow_agent.contact_email,
        contact_phone=request.escrow_agent.contact_phone,
    )

    agreement = manager.create_agreement(
        depositor=depositor,
        beneficiary=beneficiary,
        escrow_agent=escrow_agent,
        software_description=request.software_description,
        version=request.version,
        repository_url=request.repository_url,
    )

    return {
        "agreement_id": agreement.agreement_id,
        "status": agreement.status.value,
        "depositor": agreement.depositor.name,
        "beneficiary": agreement.beneficiary.name,
        "escrow_agent": agreement.escrow_agent.name,
        "software": agreement.software_description,
        "version": agreement.version,
        "effective_date": agreement.effective_date.isoformat(),
    }


@router.get("/agreements")
def list_agreements(user: User = Depends(get_current_user)):
    """List all escrow agreements."""
    from quantive.government.escrow import get_escrow_manager

    manager = get_escrow_manager()
    agreements = manager.list_agreements()

    return {
        "agreements": [
            {
                "agreement_id": a.agreement_id,
                "status": a.status.value,
                "depositor": a.depositor.name,
                "beneficiary": a.beneficiary.name,
                "software": a.software_description,
                "version": a.version,
                "effective_date": a.effective_date.isoformat(),
            }
            for a in agreements
        ],
        "total": len(agreements),
    }


@router.get("/agreements/{agreement_id}")
def get_agreement(
    agreement_id: str,
    user: User = Depends(get_current_user),
):
    """Get an escrow agreement."""
    from quantive.government.escrow import get_escrow_manager

    manager = get_escrow_manager()
    status = manager.get_agreement_status(agreement_id)

    if not status:
        raise HTTPException(404, "Agreement not found")

    return status


@router.post("/agreements/{agreement_id}/trigger")
def trigger_release(
    agreement_id: str,
    request: ReleaseTriggerRequest,
    user: User = Depends(get_current_user),
):
    """Trigger release of escrowed source code."""
    from quantive.government.escrow import ReleaseCondition, get_escrow_manager

    manager = get_escrow_manager()

    condition_map = {
        "bankruptcy": ReleaseCondition.BANKRUPTCY,
        "insolvency": ReleaseCondition.INSOLVENCY,
        "abandonment": ReleaseCondition.ABANDONMENT,
        "material_breach": ReleaseCondition.MATERIAL_BREACH,
        "failure_to_maintain": ReleaseCondition.FAILURE_TO_MAINTAIN,
    }

    condition = condition_map.get(request.condition)
    if not condition:
        raise HTTPException(400, f"Invalid condition: {request.condition}")

    try:
        result = manager.trigger_release(
            agreement_id=agreement_id,
            condition=condition,
            evidence=request.evidence,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return result


@router.post("/agreements/{agreement_id}/update")
def update_source_code(
    agreement_id: str,
    request: UpdateSourceRequest,
    user: User = Depends(get_current_user),
):
    """Record a source code update."""
    from quantive.government.escrow import get_escrow_manager

    manager = get_escrow_manager()

    try:
        result = manager.update_source_code(
            agreement_id=agreement_id,
            version=request.version,
            commit_hash=request.commit_hash,
            changelog=request.changelog,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return result


@router.get("/agreements/{agreement_id}/document")
def get_agreement_document(
    agreement_id: str,
    user: User = Depends(get_current_user),
):
    """Generate escrow agreement document."""
    from quantive.government.escrow import get_escrow_manager

    manager = get_escrow_manager()
    agreement = manager.get_agreement(agreement_id)

    if not agreement:
        raise HTTPException(404, "Agreement not found")

    document = manager.generate_agreement_document(agreement)

    return {"document": document, "format": "text"}
