"""Regulatory Compliance and Explainable AI API.

Endpoints:
  POST /api/regulatory/certifications                    - Create certification
  GET  /api/regulatory/certifications                    - List certifications
  POST /api/regulatory/certifications/{id}/conformity    - Run conformity assessment
  POST /api/regulatory/certifications/{id}/renew         - Renew certification

  POST /api/regulatory/impact-assessments               - Create impact assessment
  GET  /api/regulatory/impact-assessments               - List impact assessments
  POST /api/regulatory/impact-assessments/{id}/validate  - Independent validation

  POST /api/regulatory/stress-tests                      - Run stress test
  GET  /api/regulatory/stress-tests                      - List stress tests

  POST /api/regulatory/settlements                       - Create settlement
  GET  /api/regulatory/settlements                       - List settlements
  POST /api/regulatory/settlements/{id}/reconcile        - Reconcile settlement

  POST /api/regulatory/disclosures                       - Create disclosure
  GET  /api/regulatory/disclosures                       - List disclosures
  POST /api/regulatory/disclosures/{id}/publish          - Publish disclosure

  GET  /api/regulatory/dashboard                         - Compliance dashboard
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.database import get_db
from app.security import get_current_user
from app.models.regulatory_compliance import (
    RegulatoryCertification,
    CertificationStatus,
    CertificationType,
    AlgorithmicImpactAssessment,
    ImpactSeverity,
    ValidationStatus,
    StressTest,
    StressTestType,
    StressTestResultStatus,
    CrossBorderSettlement,
    SettlementStatus,
    SettlementNetwork,
    ExplainabilityDisclosure,
    DisclosureType,
    DisclosureStatus,
)

router = APIRouter(prefix="/api/regulatory", tags=["Regulatory Compliance"])


# --- Schemas ---

class CertificationCreateRequest(BaseModel):
    org_id: str
    certification_name: str
    certification_type: str
    issuing_authority: str
    jurisdiction: str
    certification_number: str | None = None
    notes: str | None = None

class ConformityAssessmentRequest(BaseModel):
    assessment_result: str
    findings: list[dict] | None = None
    data_quality_score: float = 0.0
    data_lineage_verified: bool = False
    traceability_enabled: bool = False
    decision_logging_enabled: bool = False
    audit_trail_completeness: float = 0.0

class ImpactAssessmentCreateRequest(BaseModel):
    org_id: str
    model_card_id: str | None = None
    assessment_name: str
    model_name: str
    model_version: str
    assessor_name: str
    assessor_organization: str
    impact_severity: str
    risk_score: float
    systemic_risk_score: float = 0.0
    market_impact_score: float = 0.0

class ValidationRequest(BaseModel):
    independent_validator: str
    validation_status: str
    findings: list[dict] | None = None

class StressTestCreateRequest(BaseModel):
    org_id: str
    test_name: str
    test_type: str
    scenario_name: str
    shock_magnitude_pct: float
    duration_days: int = 1
    interest_rate_shock_bps: float = 0.0
    fx_shock_pct: float = 0.0
    equity_shock_pct: float = 0.0
    credit_spread_shock_bps: float = 0.0
    affected_markets: list[str] | None = None
    executed_by: str | None = None

class SettlementCreateRequest(BaseModel):
    org_id: str
    exchange_connection_id: str | None = None
    settlement_reference: str
    settlement_network: str
    origin_jurisdiction: str
    destination_jurisdiction: str
    origin_currency: str
    destination_currency: str
    amount_origin: float
    exchange_rate: float
    counterparty_name: str | None = None

class DisclosureCreateRequest(BaseModel):
    org_id: str
    model_card_id: str | None = None
    disclosure_type: str
    title: str
    target_audience: str
    language: str = "en"
    executive_summary: str | None = None
    methodology_description: str | None = None


# --- 1. Regulatory Certifications ---

@router.post("/certifications")
def create_certification(req: CertificationCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    cert = RegulatoryCertification(
        org_id=req.org_id,
        certification_name=req.certification_name,
        certification_type=CertificationType(req.certification_type),
        issuing_authority=req.issuing_authority,
        jurisdiction=req.jurisdiction,
        certification_number=req.certification_number,
        status=CertificationStatus.IN_PROGRESS,
        notes=req.notes,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return {"id": cert.id, "status": cert.status.value, "message": "Certification created"}


@router.get("/certifications")
def list_certifications(
    org_id: str = Query(None),
    status: str = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    q = db.query(RegulatoryCertification)
    if org_id:
        q = q.filter(RegulatoryCertification.org_id == org_id)
    if status:
        q = q.filter(RegulatoryCertification.status == CertificationStatus(status))
    certs = q.order_by(RegulatoryCertification.created_at.desc()).all()
    return {
        "certifications": [
            {
                "id": c.id, "certification_name": c.certification_name,
                "certification_type": c.certification_type.value,
                "issuing_authority": c.issuing_authority,
                "jurisdiction": c.jurisdiction, "status": c.status.value,
                "compliance_score": c.compliance_score,
                "data_quality_score": c.data_quality_score,
                "data_lineage_verified": c.data_lineage_verified,
                "traceability_enabled": c.traceability_enabled,
                "decision_logging_enabled": c.decision_logging_enabled,
                "audit_trail_completeness": c.audit_trail_completeness,
                "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
            }
            for c in certs
        ],
        "total": len(certs),
    }


@router.post("/certifications/{cert_id}/conformity")
def run_conformity_assessment(
    cert_id: str,
    req: ConformityAssessmentRequest,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    cert = db.get(RegulatoryCertification, cert_id)
    if not cert:
        raise HTTPException(404, "Certification not found")
    cert.conformity_assessment_date = datetime.now(timezone.utc)
    cert.conformity_assessment_result = req.assessment_result
    cert.conformity_findings = req.findings
    cert.data_quality_score = req.data_quality_score
    cert.data_lineage_verified = req.data_lineage_verified
    cert.traceability_enabled = req.traceability_enabled
    cert.decision_logging_enabled = req.decision_logging_enabled
    cert.audit_trail_completeness = req.audit_trail_completeness
    if req.assessment_result == "pass":
        cert.status = CertificationStatus.CERTIFIED
        cert.compliance_score = min(100, cert.data_quality_score * 0.3 + cert.audit_trail_completeness * 0.4 + 30)
    elif req.assessment_result == "conditional_pass":
        cert.status = CertificationStatus.UNDER_REVIEW
        cert.compliance_score = cert.data_quality_score * 0.3 + cert.audit_trail_completeness * 0.4 + 15
    else:
        cert.status = CertificationStatus.SUSPENDED
        cert.compliance_score = cert.data_quality_score * 0.3 + cert.audit_trail_completeness * 0.4
    db.commit()
    return {"id": cert.id, "status": cert.status.value, "compliance_score": cert.compliance_score}


@router.post("/certifications/{cert_id}/renew")
def renew_certification(cert_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    cert = db.get(RegulatoryCertification, cert_id)
    if not cert:
        raise HTTPException(404, "Certification not found")
    cert.status = CertificationStatus.IN_PROGRESS
    cert.renewal_date = datetime.now(timezone.utc)
    db.commit()
    return {"id": cert.id, "status": cert.status.value, "message": "Renewal initiated"}


# --- 2. Algorithmic Impact Assessments ---

@router.post("/impact-assessments")
def create_impact_assessment(req: ImpactAssessmentCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    aia = AlgorithmicImpactAssessment(
        org_id=req.org_id,
        model_card_id=req.model_card_id,
        assessment_name=req.assessment_name,
        model_name=req.model_name,
        model_version=req.model_version,
        assessor_name=req.assessor_name,
        assessor_organization=req.assessor_organization,
        impact_severity=ImpactSeverity(req.impact_severity),
        risk_score=req.risk_score,
        systemic_risk_score=req.systemic_risk_score,
        market_impact_score=req.market_impact_score,
        validation_status=ValidationStatus.PENDING,
    )
    db.add(aia)
    db.commit()
    db.refresh(aia)
    return {"id": aia.id, "status": "created", "risk_score": aia.risk_score}


@router.get("/impact-assessments")
def list_impact_assessments(
    org_id: str = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    q = db.query(AlgorithmicImpactAssessment)
    if org_id:
        q = q.filter(AlgorithmicImpactAssessment.org_id == org_id)
    items = q.order_by(AlgorithmicImpactAssessment.created_at.desc()).all()
    return {
        "impact_assessments": [
            {
                "id": a.id, "assessment_name": a.assessment_name,
                "model_name": a.model_name, "model_version": a.model_version,
                "assessor_name": a.assessor_name,
                "assessor_organization": a.assessor_organization,
                "impact_severity": a.impact_severity.value,
                "risk_score": a.risk_score,
                "validation_status": a.validation_status.value,
                "independent_validator": a.independent_validator,
                "kill_switch_enabled": a.kill_switch_enabled,
                "human_oversight_required": a.human_oversight_required,
                "model_accuracy": a.model_accuracy,
                "model_bias_score": a.model_bias_score,
            }
            for a in items
        ],
        "total": len(items),
    }


@router.post("/impact-assessments/{aia_id}/validate")
def validate_assessment(
    aia_id: str,
    req: ValidationRequest,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    aia = db.get(AlgorithmicImpactAssessment, aia_id)
    if not aia:
        raise HTTPException(404, "Impact assessment not found")
    aia.independent_validator = req.independent_validator
    aia.validation_status = ValidationStatus(req.validation_status)
    aia.validation_date = datetime.now(timezone.utc)
    aia.validation_findings = req.findings
    db.commit()
    return {"id": aia.id, "validation_status": aia.validation_status.value}


# --- 3. Stress Tests ---

@router.post("/stress-tests")
def create_stress_test(req: StressTestCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    st = StressTest(
        org_id=req.org_id,
        test_name=req.test_name,
        test_type=StressTestType(req.test_type),
        scenario_name=req.scenario_name,
        shock_magnitude_pct=req.shock_magnitude_pct,
        duration_days=req.duration_days,
        interest_rate_shock_bps=req.interest_rate_shock_bps,
        fx_shock_pct=req.fx_shock_pct,
        equity_shock_pct=req.equity_shock_pct,
        credit_spread_shock_bps=req.credit_spread_shock_bps,
        affected_markets=req.affected_markets,
        executed_by=req.executed_by,
        status=StressTestResultStatus.IN_PROGRESS,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    return {"id": st.id, "status": st.result.value, "message": "Stress test initiated"}


@router.get("/stress-tests")
def list_stress_tests(
    org_id: str = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    q = db.query(StressTest)
    if org_id:
        q = q.filter(StressTest.org_id == org_id)
    tests = q.order_by(StressTest.created_at.desc()).all()
    return {
        "stress_tests": [
            {
                "id": t.id, "test_name": t.test_name,
                "test_type": t.test_type.value,
                "scenario_name": t.scenario_name,
                "shock_magnitude_pct": t.shock_magnitude_pct,
                "result": t.result.value,
                "portfolio_impact_pct": t.portfolio_impact_pct,
                "max_drawdown_pct": t.max_drawdown_pct,
                "flash_crash_threshold_bps": t.flash_crash_threshold_bps,
                "circuit_breaker_triggered": t.circuit_breaker_triggered,
                "execution_date": t.execution_date.isoformat() if t.execution_date else None,
            }
            for t in tests
        ],
        "total": len(tests),
    }


# --- 4. Cross-Border Settlements ---

@router.post("/settlements")
def create_settlement(req: SettlementCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    amt_dest = req.amount_origin * req.exchange_rate
    spread = 2.5
    settlement = CrossBorderSettlement(
        org_id=req.org_id,
        exchange_connection_id=req.exchange_connection_id,
        settlement_reference=req.settlement_reference,
        settlement_network=SettlementNetwork(req.settlement_network),
        origin_jurisdiction=req.origin_jurisdiction,
        destination_jurisdiction=req.destination_jurisdiction,
        origin_currency=req.origin_currency,
        destination_currency=req.destination_currency,
        amount_origin=req.amount_origin,
        amount_destination=amt_dest,
        exchange_rate=req.exchange_rate,
        fx_spread_bps=spread,
        counterparty_name=req.counterparty_name,
        status=SettlementStatus.PENDING,
    )
    db.add(settlement)
    db.commit()
    db.refresh(settlement)
    return {"id": settlement.id, "status": settlement.status.value, "amount_destination": amt_dest}


@router.get("/settlements")
def list_settlements(
    org_id: str = Query(None),
    status: str = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    q = db.query(CrossBorderSettlement)
    if org_id:
        q = q.filter(CrossBorderSettlement.org_id == org_id)
    if status:
        q = q.filter(CrossBorderSettlement.status == SettlementStatus(status))
    items = q.order_by(CrossBorderSettlement.created_at.desc()).all()
    return {
        "settlements": [
            {
                "id": s.id, "settlement_reference": s.settlement_reference,
                "settlement_network": s.settlement_network.value,
                "origin_jurisdiction": s.origin_jurisdiction,
                "destination_jurisdiction": s.destination_jurisdiction,
                "origin_currency": s.origin_currency,
                "destination_currency": s.destination_currency,
                "amount_origin": s.amount_origin,
                "amount_destination": s.amount_destination,
                "exchange_rate": s.exchange_rate,
                "status": s.status.value,
                "compliance_checks_passed": s.compliance_checks_passed,
                "aml_screening_passed": s.aml_screening_passed,
                "blockchain_tx_hash": s.blockchain_tx_hash,
            }
            for s in items
        ],
        "total": len(items),
    }


@router.post("/settlements/{sid}/reconcile")
def reconcile_settlement(sid: str, db=Depends(get_db), user=Depends(get_current_user)):
    s = db.get(CrossBorderSettlement, sid)
    if not s:
        raise HTTPException(404, "Settlement not found")
    s.status = SettlementStatus.RECONCILED
    s.reconciliation_status = "reconciled"
    s.confirmation_timestamp = datetime.now(timezone.utc)
    db.commit()
    return {"id": s.id, "status": s.status.value, "message": "Settlement reconciled"}


# --- 5. Explainability Disclosures ---

@router.post("/disclosures")
def create_disclosure(req: DisclosureCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    disc = ExplainabilityDisclosure(
        org_id=req.org_id,
        model_card_id=req.model_card_id,
        disclosure_type=DisclosureType(req.disclosure_type),
        title=req.title,
        target_audience=req.target_audience,
        language=req.language,
        executive_summary=req.executive_summary,
        methodology_description=req.methodology_description,
        status=DisclosureStatus.DRAFT,
    )
    db.add(disc)
    db.commit()
    db.refresh(disc)
    return {"id": disc.id, "status": disc.status.value, "message": "Disclosure created"}


@router.get("/disclosures")
def list_disclosures(
    org_id: str = Query(None),
    disclosure_type: str = Query(None),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    q = db.query(ExplainabilityDisclosure)
    if org_id:
        q = q.filter(ExplainabilityDisclosure.org_id == org_id)
    if disclosure_type:
        q = q.filter(ExplainabilityDisclosure.disclosure_type == DisclosureType(disclosure_type))
    items = q.order_by(ExplainabilityDisclosure.created_at.desc()).all()
    return {
        "disclosures": [
            {
                "id": d.id, "title": d.title,
                "disclosure_type": d.disclosure_type.value,
                "target_audience": d.target_audience,
                "status": d.status.value,
                "version": d.version,
                "language": d.language,
                "publication_date": d.publication_date.isoformat() if d.publication_date else None,
                "executive_summary": d.executive_summary,
            }
            for d in items
        ],
        "total": len(items),
    }


@router.post("/disclosures/{disc_id}/publish")
def publish_disclosure(disc_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    disc = db.get(ExplainabilityDisclosure, disc_id)
    if not disc:
        raise HTTPException(404, "Disclosure not found")
    disc.status = DisclosureStatus.PUBLISHED
    disc.publication_date = datetime.now(timezone.utc)
    db.commit()
    return {"id": disc.id, "status": disc.status.value, "message": "Disclosure published"}


# --- Dashboard ---

@router.get("/dashboard")
def regulatory_dashboard(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q_cert = db.query(RegulatoryCertification)
    q_aia = db.query(AlgorithmicImpactAssessment)
    q_st = db.query(StressTest)
    q_set = db.query(CrossBorderSettlement)
    q_disc = db.query(ExplainabilityDisclosure)
    if org_id:
        q_cert = q_cert.filter(RegulatoryCertification.org_id == org_id)
        q_aia = q_aia.filter(AlgorithmicImpactAssessment.org_id == org_id)
        q_st = q_st.filter(StressTest.org_id == org_id)
        q_set = q_set.filter(CrossBorderSettlement.org_id == org_id)
        q_disc = q_disc.filter(ExplainabilityDisclosure.org_id == org_id)

    certs = q_cert.all()
    aias = q_aia.all()
    tests = q_st.all()
    settlements = q_set.all()
    disclosures = q_disc.all()

    certified_count = sum(1 for c in certs if c.status == CertificationStatus.CERTIFIED)
    validated_count = sum(1 for a in aias if a.validation_status == ValidationStatus.PASSED)
    passed_tests = sum(1 for t in tests if t.result == StressTestResultStatus.PASSED)
    settled_count = sum(1 for s in settlements if s.status == SettlementStatus.SETTLED)
    published_count = sum(1 for d in disclosures if d.status == DisclosureStatus.PUBLISHED)

    avg_compliance = sum(c.compliance_score for c in certs) / len(certs) if certs else 0
    avg_risk = sum(a.risk_score for a in aias) / len(aias) if aias else 0

    return {
        "total_certifications": len(certs),
        "certified": certified_count,
        "total_impact_assessments": len(aias),
        "validated": validated_count,
        "total_stress_tests": len(tests),
        "passed_tests": passed_tests,
        "total_settlements": len(settlements),
        "settled": settled_count,
        "total_disclosures": len(disclosures),
        "published": published_count,
        "avg_compliance_score": round(avg_compliance, 1),
        "avg_risk_score": round(avg_risk, 1),
        "certifications": [
            {"id": c.id, "name": c.certification_name, "type": c.certification_type.value,
             "status": c.status.value, "score": c.compliance_score, "jurisdiction": c.jurisdiction}
            for c in certs
        ],
        "recent_assessments": [
            {"id": a.id, "name": a.assessment_name, "model": a.model_name,
             "severity": a.impact_severity.value, "risk": a.risk_score,
             "validation": a.validation_status.value}
            for a in aias[:5]
        ],
        "recent_stress_tests": [
            {"id": t.id, "name": t.test_name, "type": t.test_type.value,
             "result": t.result.value, "impact": t.portfolio_impact_pct}
            for t in tests[:5]
        ],
        "recent_settlements": [
            {"id": s.id, "reference": s.settlement_reference,
             "network": s.settlement_network.value, "status": s.status.value,
             "amount": s.amount_origin}
            for s in settlements[:5]
        ],
    }
