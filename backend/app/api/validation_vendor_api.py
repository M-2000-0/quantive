"""Independent Validation & Vendor Risk API.

Endpoints:
  POST   /api/validation/independent          - Create validation
  GET    /api/validation/independent          - List validations
  PATCH  /api/validation/independent/{id}/sign-off  - Sign off validation

  POST   /api/validation/vendors              - Create vendor assessment
  GET    /api/validation/vendors              - List vendor assessments
  GET    /api/validation/vendors/{id}         - Get vendor detail

  GET    /api/validation/dashboard            - Validation & vendor dashboard
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import get_db
from app.security import get_current_user
from app.models.validation_vendor import (
    IndependentValidation, ValidationStatus, ValidationType, SignOffRole,
    VendorRiskAssessment, VendorCriticality, VendorStatus, VendorCategory,
)

router = APIRouter(prefix="/api/validation", tags=["Validation & Vendor Risk"])


# --- Schemas ---

class ValidationCreateRequest(BaseModel):
    org_id: str
    validation_name: str
    validation_type: str
    model_name: str
    model_version: str
    description: str | None = None

class SignOffRequest(BaseModel):
    sign_off_by: str
    sign_off_role: str
    notes: str | None = None

class VendorCreateRequest(BaseModel):
    org_id: str
    vendor_name: str
    vendor_category: str
    description: str | None = None
    criticality: str = "medium"


# --- Independent Validation ---

@router.post("/independent")
def create_validation(req: ValidationCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    val = IndependentValidation(
        org_id=req.org_id, validation_name=req.validation_name,
        validation_type=ValidationType(req.validation_type),
        model_name=req.model_name, model_version=req.model_version,
        description=req.description, status=ValidationStatus.PENDING,
    )
    db.add(val)
    db.commit()
    db.refresh(val)
    return {"id": val.id, "status": val.status.value, "message": "Validation created"}


@router.get("/independent")
def list_validations(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(IndependentValidation)
    if org_id:
        q = q.filter(IndependentValidation.org_id == org_id)
    items = q.order_by(IndependentValidation.created_at.desc()).all()
    return {
        "validations": [
            {
                "id": v.id, "validation_name": v.validation_name,
                "validation_type": v.validation_type.value, "status": v.status.value,
                "model_name": v.model_name, "model_version": v.model_version,
                "out_of_sample_sharpe": v.out_of_sample_sharpe,
                "sharpe_degradation_pct": v.sharpe_degradation_pct,
                "max_drawdown_pct": v.max_drawdown_pct,
                "is_champion": v.is_champion, "is_challenger": v.is_challenger,
                "sign_off_by": v.sign_off_by, "sign_off_date": v.sign_off_date.isoformat() if v.sign_off_date else None,
                "next_validation_date": v.next_validation_date.isoformat() if v.next_validation_date else None,
            }
            for v in items
        ],
        "total": len(items),
    }


@router.patch("/independent/{validation_id}/sign-off")
def sign_off_validation(validation_id: str, req: SignOffRequest, db=Depends(get_db), user=Depends(get_current_user)):
    val = db.query(IndependentValidation).filter(IndependentValidation.id == validation_id).first()
    if not val:
        raise HTTPException(status_code=404, detail="Validation not found")
    val.status = ValidationStatus.PASSED
    val.sign_off_by = req.sign_off_by
    val.sign_off_role = SignOffRole(req.sign_off_role)
    val.sign_off_date = datetime.now(timezone.utc)
    val.sign_off_notes = req.notes
    db.commit()
    return {"id": val.id, "status": val.status.value, "message": "Validation signed off"}


# --- Vendor Risk ---

@router.post("/vendors")
def create_vendor(req: VendorCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    vendor = VendorRiskAssessment(
        org_id=req.org_id, vendor_name=req.vendor_name,
        vendor_category=VendorCategory(req.vendor_category),
        description=req.description,
        criticality=VendorCriticality(req.criticality),
        status=VendorStatus.ONBOARDED,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return {"id": vendor.id, "status": vendor.status.value, "message": "Vendor assessment created"}


@router.get("/vendors")
def list_vendors(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(VendorRiskAssessment)
    if org_id:
        q = q.filter(VendorRiskAssessment.org_id == org_id)
    items = q.order_by(VendorRiskAssessment.created_at.desc()).all()
    return {
        "vendors": [
            {
                "id": v.id, "vendor_name": v.vendor_name,
                "vendor_category": v.vendor_category.value,
                "status": v.status.value, "criticality": v.criticality.value,
                "due_diligence_completed": v.due_diligence_completed,
                "due_diligence_score": v.due_diligence_score,
                "soc2_type_ii": v.soc2_type_ii, "iso27001_certified": v.iso27001_certified,
                "actual_uptime_pct": v.actual_uptime_pct,
                "sla_breaches_ytd": v.sla_breaches_ytd,
                "overall_risk_score": v.overall_risk_score,
                "security_risk_score": v.security_risk_score,
                "incidents_ytd": v.incidents_ytd,
                "next_review_date": v.next_review_date.isoformat() if v.next_review_date else None,
            }
            for v in items
        ],
        "total": len(items),
    }


@router.get("/vendors/{vendor_id}")
def get_vendor(vendor_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    v = db.query(VendorRiskAssessment).filter(VendorRiskAssessment.id == vendor_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return {
        "id": v.id, "vendor_name": v.vendor_name,
        "vendor_category": v.vendor_category.value,
        "status": v.status.value, "criticality": v.criticality.value,
        "description": v.description,
        "due_diligence_completed": v.due_diligence_completed,
        "due_diligence_score": v.due_diligence_score,
        "soc2_type_ii": v.soc2_type_ii, "iso27001_certified": v.iso27001_certified,
        "open_vulnerabilities": v.open_vulnerabilities,
        "critical_vulnerabilities": v.critical_vulnerabilities,
        "sla_uptime_pct": v.sla_uptime_pct, "actual_uptime_pct": v.actual_uptime_pct,
        "sla_breaches_ytd": v.sla_breaches_ytd,
        "sub_processors": v.sub_processors,
        "fourth_party_risk": v.fourth_party_risk,
        "incident_response_plan": v.incident_response_plan,
        "business_continuity_plan": v.business_continuity_plan,
        "gdpr_compliant": v.gdpr_compliant,
        "overall_risk_score": v.overall_risk_score,
        "security_risk_score": v.security_risk_score,
        "operational_risk_score": v.operational_risk_score,
        "compliance_risk_score": v.compliance_risk_score,
        "financial_risk_score": v.financial_risk_score,
        "incidents_ytd": v.incidents_ytd,
        "escalations_ytd": v.escalations_ytd,
    }


# --- Dashboard ---

@router.get("/dashboard")
def validation_dashboard(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q_val = db.query(IndependentValidation)
    q_ven = db.query(VendorRiskAssessment)
    if org_id:
        q_val = q_val.filter(IndependentValidation.org_id == org_id)
        q_ven = q_ven.filter(VendorRiskAssessment.org_id == org_id)

    validations = q_val.all()
    vendors = q_ven.all()

    passed = sum(1 for v in validations if v.status == ValidationStatus.PASSED)
    failed = sum(1 for v in validations if v.status == ValidationStatus.FAILED)
    pending = sum(1 for v in validations if v.status == ValidationStatus.PENDING)
    signed_off = sum(1 for v in validations if v.sign_off_by)

    critical_vendors = sum(1 for v in vendors if v.criticality == VendorCriticality.CRITICAL)
    active_vendors = sum(1 for v in vendors if v.status == VendorStatus.ACTIVE)
    dd_complete = sum(1 for v in vendors if v.due_diligence_completed)
    avg_risk = sum(v.overall_risk_score for v in vendors) / len(vendors) if vendors else 0
    avg_uptime = sum(v.actual_uptime_pct for v in vendors if v.actual_uptime_pct) / max(1, sum(1 for v in vendors if v.actual_uptime_pct))

    return {
        "validations": {
            "total": len(validations), "passed": passed, "failed": failed,
            "pending": pending, "signed_off": signed_off,
        },
        "vendors": {
            "total": len(vendors), "critical": critical_vendors,
            "active": active_vendors, "dd_complete": dd_complete,
            "avg_risk_score": round(avg_risk, 1), "avg_uptime_pct": round(avg_uptime, 2),
        },
        "recent_validations": [
            {"id": v.id, "name": v.validation_name, "type": v.validation_type.value,
             "status": v.status.value, "model": v.model_name}
            for v in validations[:5]
        ],
        "high_risk_vendors": [
            {"id": v.id, "name": v.vendor_name, "category": v.vendor_category.value,
             "risk_score": v.overall_risk_score, "criticality": v.criticality.value}
            for v in sorted(vendors, key=lambda x: x.overall_risk_score, reverse=True)[:5]
        ],
    }
