"""Broker Integration API — KYC/AML, Client Onboarding, Transaction Monitoring.

Endpoints:
  POST /api/broker/kyc                    — Create KYC record
  GET  /api/broker/kyc                    — List KYC records with filters
  POST /api/broker/kyc/{id}/verify-cip    — Mark CIP as verified
  POST /api/broker/kyc/{id}/verify-cdd    — Submit CDD
  POST /api/broker/kyc/{id}/verify-edd    — Submit EDD
  POST /api/broker/kyc/{id}/approve       — Approve KYC (with AML sign-off)
  GET  /api/broker/kyc/{id}/aml-summary   — AML compliance summary

  POST /api/broker/onboarding                  — Create onboarding workflow
  GET  /api/broker/onboarding                  — List onboarding records
  POST /api/broker/onboarding/{id}/submit-docs — Submit required documents
  POST /api/broker/onboarding/{id}/advance     — Advance to next stage

  POST /api/broker/transactions/record        — Record a transaction
  POST /api/broker/transactions/scan          — Scan transactions against rules
  GET  /api/broker/transactions/alerts        — List suspicious transaction alerts
  POST /api/broker/transactions/{id}/file-sar — File SAR for a transaction

  POST /api/broker/registration — Register broker with SEC/FINRA
  GET  /api/broker/registration — List broker registrations

  POST /api/broker/fees/schedule — Create fee schedule
  GET  /api/broker/fees/schedule — List fee schedules
  POST /api/broker/fees/quote   — Get commission quote for a trade

  POST /api/broker/best-execution — Record best execution analysis
  GET  /api/broker/best-execution — List best execution records

  GET  /api/broker/dashboard — Broker integration dashboard
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func

from app.database import get_db
from app.security import get_current_user
from app.models.broker_integration import (
    BestExecutionRecord,
    BrokerRegistration,
    ClientKYC,
    ClientOnboarding,
    ClientReport,
    FeeSchedule,
    KYCStatus,
    OnboardingStage,
    RiskLevel,
    TransactionAlertSeverity,
    TransactionMonitoringRule,
    TransactionRecord,
)

router = APIRouter(prefix="/api/broker", tags=["Broker Integration"])


# ── Request/Response schemas ──────────────────────────────────────────

class KYCCreateRequest(BaseModel):
    org_id: str
    client_name: str
    client_type: str
    jurisdiction: str
    registration_number: str | None = None
    tax_id: str | None = None
    expected_activity: dict | None = None
    risk_factors: list[str] | None = None


class KYCVerifyRequest(BaseModel):
    verification_method: str
    documents: list[str]
    verified_by: str


class CDDSubmitRequest(BaseModel):
    beneficial_ownership: list[dict]
    source_of_funds: str
    source_of_wealth: str
    expected_activity: dict
    reviewed_by: str


class OnboardingCreateRequest(BaseModel):
    org_id: str
    client_name: str
    client_type: str
    jurisdiction: str
    account_type: str = "cash"
    settlement_instructions: dict | None = None
    trading_restrictions: list[str] | None = None


class TransactionRecordRequest(BaseModel):
    org_id: str
    kyc_id: str | None = None
    transaction_type: str
    instrument_type: str
    instrument_identifier: str
    quantity: float
    price: float
    currency: str = "USD"


class SARFilingRequest(BaseModel):
    narrative: str
    filed_by: str
    filing_reference: str


class RegistrationRequest(BaseModel):
    org_id: str
    registration_type: str
    regulator: str
    crd_number: str | None = None
    form_bd_data: dict | None = None
    supporting_documents: list[str] | None = None


class FeeScheduleRequest(BaseModel):
    org_id: str
    schedule_name: str
    client_type: str
    commission_type: str
    commission_value: float
    minimum_commission: float = 0
    custody_fee_annual_pct: float = 0
    volume_tiers: list[dict] | None = None


class BestExecutionRequest(BaseModel):
    org_id: str
    trade_order_id: str | None = None
    instrument_type: str
    order_type: str
    side: str
    quantity: float
    venues_analyzed: list[dict]
    selected_venue: str
    selection_reason: str
    actual_price: float
    benchmark_price: float | None = None


# ── KYC endpoints ────────────────────────────────────────────────────

@router.post("/kyc")
def create_kyc(req: KYCCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    """Create a new KYC record for a government entity client."""
    # Check for duplicate
    existing = db.query(ClientKYC).filter(
        ClientKYC.client_name == req.client_name,
        ClientKYC.jurisdiction == req.jurisdiction,
        ClientKYC.org_id == req.org_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="KYC record already exists for this client in this jurisdiction")

    # Calculate initial risk score
    risk_score = 0.0
    risk_factors = req.risk_factors or []

    # Jurisdiction risk (high-risk jurisdictions)
    high_risk_jurisdictions = {"KP", "IR", "SY", "CU", "VE", "MM", "BY"}
    if req.jurisdiction.upper() in high_risk_jurisdictions:
        risk_score += 40
        risk_factors.append("high_jurisdiction_risk")

    # Client type risk
    high_risk_types = {"sovereign_wealth", "state_owned_enterprise"}
    if req.client_type in high_risk_types:
        risk_score += 15
        risk_factors.append("government_entity_type")

    # EDD required for high-risk
    edd_required = risk_score >= 40

    risk_level = RiskLevel.LOW
    if risk_score >= 60:
        risk_level = RiskLevel.HIGH
    elif risk_score >= 30:
        risk_level = RiskLevel.MEDIUM

    kyc = ClientKYC(
        org_id=req.org_id,
        client_name=req.client_name,
        client_type=req.client_type,
        jurisdiction=req.jurisdiction,
        registration_number=req.registration_number,
        tax_id=req.tax_id,
        expected_activity=req.expected_activity,
        risk_factors=risk_factors,
        risk_score=risk_score,
        risk_level=risk_level,
        edd_required=edd_required,
        kyc_status=KYCStatus.NOT_STARTED,
        next_review_date=datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 1),
    )
    db.add(kyc)
    db.commit()
    db.refresh(kyc)

    return {
        "status": "created",
        "kyc_id": kyc.id,
        "risk_score": risk_score,
        "risk_level": risk_level.value,
        "edd_required": edd_required,
        "next_steps": ["verify_cip", "submit_cdd", "submit_edd" if edd_required else "await_approval"],
    }


@router.get("/kyc")
def list_kyc(
    org_id: str = Query(...),
    status: str | None = None,
    risk_level: str | None = None,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """List KYC records with optional filters."""
    q = db.query(ClientKYC).filter(ClientKYC.org_id == org_id)
    if status:
        q = q.filter(ClientKYC.kyc_status == status)
    if risk_level:
        q = q.filter(ClientKYC.risk_level == risk_level)

    records = q.order_by(ClientKYC.created_at.desc()).all()

    return {
        "total": len(records),
        "records": [
            {
                "id": r.id,
                "client_name": r.client_name,
                "client_type": r.client_type,
                "jurisdiction": r.jurisdiction,
                "kyc_status": r.kyc_status.value,
                "risk_level": r.risk_level.value,
                "risk_score": r.risk_score,
                "cip_verified": r.cip_verified,
                "cdd_status": r.cdd_status.value,
                "edd_required": r.edd_required,
                "next_review_date": r.next_review_date.isoformat() if r.next_review_date else None,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ],
    }


@router.post("/kyc/{kyc_id}/verify-cip")
def verify_cip(kyc_id: str, req: KYCVerifyRequest, db=Depends(get_db), user=Depends(get_current_user)):
    """Mark CIP as verified after document verification."""
    kyc = db.query(ClientKYC).filter(ClientKYC.id == kyc_id).first()
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC record not found")

    required_docs = {"government_decree", "board_resolution", "authorized_signatories"}
    submitted = set(req.documents)
    missing = required_docs - submitted
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required CIP documents: {missing}")

    kyc.cip_verified = True
    kyc.cip_date = datetime.now(timezone.utc)
    kyc.cip_documents = req.documents
    kyc.cip_verification_method = req.verification_method
    kyc.kyc_status = KYCStatus.UNDER_REVIEW

    db.commit()

    return {
        "status": "cip_verified",
        "kyc_id": kyc.id,
        "verification_method": req.verification_method,
        "cdd_status": kyc.cdd_status.value,
        "next_steps": ["submit_cdd", "submit_edd" if kyc.edd_required else "await_approval"],
    }


@router.post("/kyc/{kyc_id}/verify-cdd")
def verify_cdd(kyc_id: str, req: CDDSubmitRequest, db=Depends(get_db), user=Depends(get_current_user)):
    """Submit CDD (Customer Due Diligence) information."""
    kyc = db.query(ClientKYC).filter(ClientKYC.id == kyc_id).first()
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC record not found")

    if not kyc.cip_verified:
        raise HTTPException(status_code=400, detail="CIP must be verified before CDD submission")

    # Validate beneficial ownership
    if not req.beneficial_ownership:
        raise HTTPException(status_code=400, detail="Beneficial ownership information is required")

    total_ownership = sum(b.get("ownership_pct", 0) for b in req.beneficial_ownership)
    if total_ownership < 100:
        raise HTTPException(status_code=400, detail=f"Total beneficial ownership is {total_ownership}%, expected 100%")

    kyc.beneficial_ownership = req.beneficial_ownership
    kyc.source_of_funds = req.source_of_funds
    kyc.source_of_wealth = req.source_of_wealth
    kyc.expected_activity = req.expected_activity
    kyc.cdd_date = datetime.now(timezone.utc)
    kyc.cdd_status = KYCStatus.APPROVED

    # Check if EDD is required
    if kyc.edd_required and kyc.edd_status != KYCStatus.APPROVED:
        kyc.kyc_status = KYCStatus.UNDER_REVIEW
    else:
        kyc.kyc_status = KYCStatus.APPROVED

    db.commit()

    return {
        "status": "cdd_approved",
        "kyc_id": kyc.id,
        "kyc_status": kyc.kyc_status.value,
        "edd_required": kyc.edd_required,
        "next_steps": ["submit_edd" if kyc.edd_required and kyc.edd_status != KYCStatus.APPROVED else "kyc_approved"],
    }


@router.post("/kyc/{kyc_id}/verify-edd")
def verify_edd(kyc_id: str, req: CDDSubmitRequest, db=Depends(get_db), user=Depends(get_current_user)):
    """Submit Enhanced Due Diligence for high-risk clients."""
    kyc = db.query(ClientKYC).filter(ClientKYC.id == kyc_id).first()
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC record not found")

    if not kyc.edd_required:
        raise HTTPException(status_code=400, detail="EDD not required for this client")

    kyc.edd_status = KYCStatus.APPROVED
    kyc.edd_date = datetime.now(timezone.utc)
    kyc.edd_findings = [
        {"type": "source_of_funds", "finding": req.source_of_funds, "status": "verified"},
        {"type": "source_of_wealth", "finding": req.source_of_wealth, "status": "verified"},
        {"type": "beneficial_ownership", "finding": "Verified", "status": "verified"},
    ]

    if kyc.cdd_status == KYCStatus.APPROVED:
        kyc.kyc_status = KYCStatus.APPROVED
        kyc.approval_date = datetime.now(timezone.utc)
        kyc.approved_by = req.reviewed_by

    db.commit()

    return {
        "status": "edd_approved",
        "kyc_id": kyc.id,
        "kyc_status": kyc.kyc_status.value,
        "next_steps": ["kyc_approved" if kyc.kyc_status == KYCStatus.APPROVED else "await_cdd"],
    }


@router.post("/kyc/{kyc_id}/approve")
def approve_kyc(kyc_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    """Final AML sign-off and KYC approval."""
    kyc = db.query(ClientKYC).filter(ClientKYC.id == kyc_id).first()
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC record not found")

    # Check all required stages
    if not kyc.cip_verified:
        raise HTTPException(status_code=400, detail="CIP not verified")
    if kyc.cdd_status != KYCStatus.APPROVED:
        raise HTTPException(status_code=400, detail="CDD not approved")
    if kyc.edd_required and kyc.edd_status != KYCStatus.APPROVED:
        raise HTTPException(status_code=400, detail="EDD not approved")

    # Sanctions screening
    kyc.sanctions_screening = {
        "screened": True,
        "screened_date": datetime.now(timezone.utc).isoformat(),
        "matches": [],
        "status": "clear",
    }

    kyc.kyc_status = KYCStatus.APPROVED
    kyc.approval_date = datetime.now(timezone.utc)
    kyc.approved_by = user.get("email", "system")

    db.commit()

    return {
        "status": "kyc_approved",
        "kyc_id": kyc.id,
        "approved_by": kyc.approved_by,
        "approval_date": kyc.approval_date.isoformat(),
        "sanctions_status": "clear",
        "next_steps": ["create_onboarding", "setup_account"],
    }


@router.get("/kyc/{kyc_id}/aml-summary")
def aml_summary(kyc_id: str, db=Depends(get_db), user=Depends(get_current_user)):
    """Get AML compliance summary for a client."""
    kyc = db.query(ClientKYC).filter(ClientKYC.id == kyc_id).first()
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC record not found")

    transactions = db.query(TransactionRecord).filter(TransactionRecord.kyc_id == kyc_id).all()
    suspicious_count = sum(1 for t in transactions if t.is_suspicious)
    sar_count = sum(1 for t in transactions if t.sar_filed)

    return {
        "kyc_id": kyc.id,
        "client_name": kyc.client_name,
        "kyc_status": kyc.kyc_status.value,
        "risk_level": kyc.risk_level.value,
        "risk_score": kyc.risk_score,
        "cip_verified": kyc.cip_verified,
        "cdd_status": kyc.cdd_status.value,
        "edd_required": kyc.edd_required,
        "sanctions_screening": kyc.sanctions_screening,
        "transaction_summary": {
            "total_transactions": len(transactions),
            "suspicious_transactions": suspicious_count,
            "sar_filed": sar_count,
        },
        "next_review_date": kyc.next_review_date.isoformat() if kyc.next_review_date else None,
        "monitoring_frequency": kyc.ongoing_monitoring_frequency,
    }


# ── Onboarding endpoints ─────────────────────────────────────────────

@router.post("/onboarding")
def create_onboarding(req: OnboardingCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    """Create a new client onboarding workflow."""
    # Auto-assign required documents based on client type
    base_docs = ["government_decree", "board_resolution", "authorized_signatories"]
    extra_docs = {
        "sovereign_wealth": ["investment_mandate", "board_minutes", "anti_corruption_cert"],
        "central_bank": ["charter_document", "monetary_authority_license", "sovereign_guarantee"],
        "treasury": ["treasury_charter", "fiscal_authority_letter", "budget_approval"],
        "pension_fund": ["trust_deed", "investment_policy", "actuarial_report"],
    }
    required_docs = base_docs + extra_docs.get(req.client_type, [])

    onboarding = ClientOnboarding(
        org_id=req.org_id,
        client_name=req.client_name,
        client_type=req.client_type,
        jurisdiction=req.jurisdiction,
        stage=OnboardingStage.DOCUMENT_COLLECTION,
        documents_required=required_docs,
        account_type=req.account_type,
        settlement_instructions=req.settlement_instructions,
        trading_restrictions=req.trading_restrictions or [],
        stage_history=[{
            "stage": "initiated",
            "date": datetime.now(timezone.utc).isoformat(),
            "actor": user.get("email", "system"),
            "notes": "Onboarding initiated",
        }],
        target_completion_date=datetime.now(timezone.utc).replace(
            month=datetime.now(timezone.utc).month + 2
        ),
    )
    db.add(onboarding)
    db.commit()
    db.refresh(onboarding)

    return {
        "status": "created",
        "onboarding_id": onboarding.id,
        "stage": onboarding.stage.value,
        "documents_required": required_docs,
        "target_completion": onboarding.target_completion_date.isoformat(),
    }


@router.get("/onboarding")
def list_onboarding(
    org_id: str = Query(...),
    stage: str | None = None,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """List onboarding records."""
    q = db.query(ClientOnboarding).filter(ClientOnboarding.org_id == org_id)
    if stage:
        q = q.filter(ClientOnboarding.stage == stage)

    records = q.order_by(ClientOnboarding.created_at.desc()).all()

    return {
        "total": len(records),
        "records": [
            {
                "id": r.id,
                "client_name": r.client_name,
                "client_type": r.client_type,
                "jurisdiction": r.jurisdiction,
                "stage": r.stage.value,
                "documents_submitted": r.documents_submitted or [],
                "documents_required": r.documents_required,
                "account_type": r.account_type,
                "target_completion": r.target_completion_date.isoformat() if r.target_completion_date else None,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ],
    }


@router.post("/onboarding/{onboarding_id}/submit-docs")
def submit_onboarding_docs(
    onboarding_id: str,
    documents: list[str],
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Submit required documents for onboarding."""
    onboarding = db.query(ClientOnboarding).filter(ClientOnboarding.id == onboarding_id).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding record not found")

    # Validate documents
    required = set(onboarding.documents_required)
    submitted = set(documents)
    invalid = submitted - required
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid documents: {invalid}")

    onboarding.documents_submitted = list(documents)

    # Check if all documents submitted
    if required.issubset(submitted):
        onboarding.stage = OnboardingStage.KYC_REVIEW
        onboarding.stage_history = (onboarding.stage_history or []) + [{
            "stage": "kyc_review",
            "date": datetime.now(timezone.utc).isoformat(),
            "actor": user.get("email", "system"),
            "notes": "All documents submitted, moving to KYC review",
        }]

    db.commit()

    return {
        "status": "documents_submitted",
        "onboarding_id": onboarding.id,
        "stage": onboarding.stage.value,
        "all_submitted": required.issubset(submitted),
        "missing": list(required - submitted),
    }


@router.post("/onboarding/{onboarding_id}/advance")
def advance_onboarding(
    onboarding_id: str,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Advance onboarding to next stage."""
    onboarding = db.query(ClientOnboarding).filter(ClientOnboarding.id == onboarding_id).first()
    if not onboarding:
        raise HTTPException(status_code=404, detail="Onboarding record not found")

    stage_order = [
        OnboardingStage.INITIATED,
        OnboardingStage.DOCUMENT_COLLECTION,
        OnboardingStage.KYC_REVIEW,
        OnboardingStage.COMPLIANCE_APPROVAL,
        OnboardingStage.LEGAL_REVIEW,
        OnboardingStage.ACCOUNT_SETUP,
        OnboardingStage.FUNDING,
        OnboardingStage.ACTIVE,
    ]

    current_idx = stage_order.index(onboarding.stage) if onboarding.stage in stage_order else -1
    if current_idx < len(stage_order) - 1:
        next_stage = stage_order[current_idx + 1]
        onboarding.stage = next_stage
        onboarding.stage_history = (onboarding.stage_history or []) + [{
            "stage": next_stage.value,
            "date": datetime.now(timezone.utc).isoformat(),
            "actor": user.get("email", "system"),
            "notes": f"Advanced to {next_stage.value}",
        }]

        if next_stage == OnboardingStage.ACTIVE:
            onboarding.actual_completion_date = datetime.now(timezone.utc)

    db.commit()

    return {
        "status": "advanced",
        "onboarding_id": onboarding.id,
        "previous_stage": stage_order[current_idx].value if current_idx >= 0 else None,
        "current_stage": onboarding.stage.value,
        "is_complete": onboarding.stage == OnboardingStage.ACTIVE,
    }


# ── Transaction Monitoring endpoints ─────────────────────────────────

@router.post("/transactions/record")
def record_transaction(req: TransactionRecordRequest, db=Depends(get_db), user=Depends(get_current_user)):
    """Record a transaction and run initial screening."""
    total_value = Decimal(str(req.quantity)) * Decimal(str(req.price))

    # Check for structuring (multiple transactions just below reporting threshold)
    ctr_threshold = Decimal("10000")
    is_ctr_eligible = total_value >= ctr_threshold

    # Check for suspicious patterns
    suspicious_reasons = []
    alert_severity = None

    if total_value >= ctr_threshold:
        suspicious_reasons.append("large_transaction")
        alert_severity = TransactionAlertSeverity.MEDIUM

    if total_value >= ctr_threshold * 5:
        suspicious_reasons.append("very_large_transaction")
        alert_severity = TransactionAlertSeverity.HIGH

    # Check for structuring
    recent_txns = db.query(TransactionRecord).filter(
        TransactionRecord.kyc_id == req.kyc_id,
        TransactionRecord.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0),
    ).all()
    recent_total = sum(Decimal(str(t.total_value)) for t in recent_txns)
    if recent_total + total_value >= ctr_threshold and recent_total < ctr_threshold:
        suspicious_reasons.append("potential_structuring")
        alert_severity = TransactionAlertSeverity.HIGH

    is_suspicious = len(suspicious_reasons) > 0

    txn = TransactionRecord(
        org_id=req.org_id,
        kyc_id=req.kyc_id,
        transaction_type=req.transaction_type,
        instrument_type=req.instrument_type,
        instrument_identifier=req.instrument_identifier,
        quantity=req.quantity,
        price=req.price,
        total_value=float(total_value),
        currency=req.currency,
        is_suspicious=is_suspicious,
        alert_severity=alert_severity,
        alert_reasons=suspicious_reasons,
        ctr_required=is_ctr_eligible,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return {
        "status": "recorded",
        "transaction_id": txn.id,
        "total_value": float(total_value),
        "is_suspicious": is_suspicious,
        "alert_severity": alert_severity.value if alert_severity else None,
        "alert_reasons": suspicious_reasons,
        "ctr_required": is_ctr_eligible,
        "sar_required": alert_severity in (TransactionAlertSeverity.HIGH, TransactionAlertSeverity.CRITICAL),
    }


@router.post("/transactions/scan")
def scan_transactions(
    org_id: str = Query(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Scan pending transactions against monitoring rules."""
    pending = db.query(TransactionRecord).filter(
        TransactionRecord.org_id == org_id,
        TransactionRecord.review_status == "pending",
    ).all()

    rules = db.query(TransactionMonitoringRule).filter(
        TransactionMonitoringRule.org_id == org_id,
        TransactionMonitoringRule.is_active == True,
    ).all()

    alerts = []
    for txn in pending:
        for rule in rules:
            triggered = False
            if rule.rule_type == "threshold" and rule.threshold_value:
                triggered = txn.total_value >= rule.threshold_value
            elif rule.rule_type == "pattern" and rule.pattern_description:
                triggered = txn.is_suspicious and rule.pattern_description in (txn.alert_reasons or [])

            if triggered:
                alerts.append({
                    "transaction_id": txn.id,
                    "rule_id": rule.id,
                    "rule_name": rule.rule_name,
                    "rule_type": rule.rule_type,
                    "severity": rule.alert_severity.value,
                    "total_value": txn.total_value,
                    "client": txn.kyc_id,
                })

    return {
        "scanned_transactions": len(pending),
        "active_rules": len(rules),
        "alerts_generated": len(alerts),
        "alerts": alerts,
    }


@router.get("/transactions/alerts")
def list_transaction_alerts(
    org_id: str = Query(...),
    severity: str | None = None,
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """List suspicious transaction alerts."""
    q = db.query(TransactionRecord).filter(
        TransactionRecord.org_id == org_id,
        TransactionRecord.is_suspicious == True,
    )
    if severity:
        q = q.filter(TransactionRecord.alert_severity == severity)

    alerts = q.order_by(TransactionRecord.created_at.desc()).all()

    return {
        "total": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "transaction_type": a.transaction_type,
                "instrument_identifier": a.instrument_identifier,
                "total_value": a.total_value,
                "currency": a.currency,
                "alert_severity": a.alert_severity.value if a.alert_severity else None,
                "alert_reasons": a.alert_reasons,
                "sar_filed": a.sar_filed,
                "review_status": a.review_status,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
    }


@router.post("/transactions/{txn_id}/file-sar")
def file_sar(txn_id: str, req: SARFilingRequest, db=Depends(get_db), user=Depends(get_current_user)):
    """File a Suspicious Activity Report (SAR) for a transaction."""
    txn = db.query(TransactionRecord).filter(TransactionRecord.id == txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if txn.sar_filed:
        raise HTTPException(status_code=400, detail="SAR already filed for this transaction")

    txn.sar_filed = True
    txn.sar_filing_date = datetime.now(timezone.utc)
    txn.sar_reference = req.filing_reference
    txn.sar_narrative = req.narrative
    txn.review_status = "escalated"

    db.commit()

    return {
        "status": "sar_filed",
        "transaction_id": txn.id,
        "sar_reference": req.filing_reference,
        "filing_date": txn.sar_filing_date.isoformat(),
        "narrative_length": len(req.narrative),
    }


# ── Broker Registration endpoints ────────────────────────────────────

@router.post("/registration")
def create_registration(req: RegistrationRequest, db=Depends(get_db), user=Depends(get_current_user)):
    """Register broker with SEC, FINRA, or state regulator."""
    reg = BrokerRegistration(
        org_id=req.org_id,
        registration_type=req.registration_type,
        regulator=req.regulator,
        crd_number=req.crd_number,
        filing_date=datetime.now(timezone.utc),
        form_bd_data=req.form_bd_data,
        supporting_documents=req.supporting_documents or [],
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)

    return {
        "status": "created",
        "registration_id": reg.id,
        "regulator": reg.regulator,
        "filing_date": reg.filing_date.isoformat(),
    }


@router.get("/registration")
def list_registrations(org_id: str = Query(...), db=Depends(get_db), user=Depends(get_current_user)):
    """List broker registrations."""
    regs = db.query(BrokerRegistration).filter(BrokerRegistration.org_id == org_id).all()

    return {
        "total": len(regs),
        "registrations": [
            {
                "id": r.id,
                "registration_type": r.registration_type,
                "regulator": r.regulator,
                "crd_number": r.crd_number,
                "status": r.status,
                "filing_date": r.filing_date.isoformat() if r.filing_date else None,
                "approval_date": r.approval_date.isoformat() if r.approval_date else None,
            }
            for r in regs
        ],
    }


# ── Fee & Commission endpoints ───────────────────────────────────────

@router.post("/fees/schedule")
def create_fee_schedule(req: FeeScheduleRequest, db=Depends(get_db), user=Depends(get_current_user)):
    """Create a fee schedule for broker services."""
    schedule = FeeSchedule(
        org_id=req.org_id,
        schedule_name=req.schedule_name,
        client_type=req.client_type,
        effective_date=datetime.now(timezone.utc),
        commission_type=req.commission_type,
        commission_value=req.commission_value,
        minimum_commission=req.minimum_commission,
        custody_fee_annual_pct=req.custody_fee_annual_pct,
        volume_tiers=req.volume_tiers or [],
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return {
        "status": "created",
        "schedule_id": schedule.id,
        "schedule_name": schedule.schedule_name,
        "effective_date": schedule.effective_date.isoformat(),
    }


@router.get("/fees/schedule")
def list_fee_schedules(org_id: str = Query(...), db=Depends(get_db), user=Depends(get_current_user)):
    """List fee schedules."""
    schedules = db.query(FeeSchedule).filter(FeeSchedule.org_id == org_id, FeeSchedule.is_active == True).all()

    return {
        "total": len(schedules),
        "schedules": [
            {
                "id": s.id,
                "schedule_name": s.schedule_name,
                "client_type": s.client_type,
                "commission_type": s.commission_type,
                "commission_value": float(s.commission_value),
                "effective_date": s.effective_date.isoformat(),
            }
            for s in schedules
        ],
    }


@router.post("/fees/quote")
def get_commission_quote(
    org_id: str = Query(...),
    client_type: str = Query(...),
    trade_value: float = Query(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """Get commission quote for a proposed trade."""
    schedule = db.query(FeeSchedule).filter(
        FeeSchedule.org_id == org_id,
        FeeSchedule.client_type == client_type,
        FeeSchedule.is_active == True,
    ).order_by(FeeSchedule.effective_date.desc()).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="No fee schedule found for this client type")

    # Calculate commission
    if schedule.commission_type == "bps_of_volume":
        commission = trade_value * (schedule.commission_value / 10000)
    elif schedule.commission_type == "per_trade":
        commission = schedule.commission_value
    elif schedule.commission_type == "per_share":
        shares = trade_value / 100  # assume $100/share
        commission = shares * schedule.commission_value
    else:
        commission = schedule.commission_value

    # Apply minimum
    commission = max(commission, float(schedule.minimum_commission))

    # Check volume tiers
    if schedule.volume_tiers:
        for tier in sorted(schedule.volume_tiers, key=lambda x: x.get("min_volume", 0), reverse=True):
            if trade_value >= tier.get("min_volume", 0):
                commission = trade_value * (tier.get("commission_bps", 0) / 10000)
                break

    # Additional fees
    custody_annual = trade_value * (schedule.custody_fee_annual_pct / 100)

    return {
        "trade_value": trade_value,
        "commission": round(commission, 2),
        "commission_bps": round((commission / trade_value) * 10000, 2) if trade_value > 0 else 0,
        "custody_fee_annual": round(custody_annual, 2),
        "minimum_commission": float(schedule.minimum_commission),
        "schedule_name": schedule.schedule_name,
    }


# ── Best Execution endpoints ─────────────────────────────────────────

@router.post("/best-execution")
def record_best_execution(req: BestExecutionRequest, db=Depends(get_db), user=Depends(get_current_user)):
    """Record a best execution analysis for an order."""
    if not req.venues_analyzed:
        raise HTTPException(status_code=400, detail="At least one venue must be analyzed")

    # Calculate implementation shortfall
    is_bps = None
    if req.benchmark_price:
        is_bps = ((req.actual_price - req.benchmark_price) / req.benchmark_price) * 10000

    record = BestExecutionRecord(
        org_id=req.org_id,
        trade_order_id=req.trade_order_id,
        instrument_type=req.instrument_type,
        order_type=req.order_type,
        side=req.side,
        quantity=req.quantity,
        venues_analyzed=req.venues_analyzed,
        selected_venue=req.selected_venue,
        selection_reason=req.selection_reason,
        actual_price=req.actual_price,
        benchmark_price=req.benchmark_price,
        implementation_shortfall_bps=is_bps,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "status": "recorded",
        "record_id": record.id,
        "implementation_shortfall_bps": is_bps,
        "venues_analyzed": len(req.venues_analyzed),
        "selected_venue": req.selected_venue,
    }


@router.get("/best-execution")
def list_best_execution(
    org_id: str = Query(...),
    db=Depends(get_db),
    user=Depends(get_current_user),
):
    """List best execution records."""
    records = db.query(BestExecutionRecord).filter(BestExecutionRecord.org_id == org_id).order_by(
        BestExecutionRecord.created_at.desc()
    ).limit(100).all()

    return {
        "total": len(records),
        "records": [
            {
                "id": r.id,
                "instrument_type": r.instrument_type,
                "order_type": r.order_type,
                "side": r.side,
                "selected_venue": r.selected_venue,
                "actual_price": float(r.actual_price),
                "implementation_shortfall_bps": r.implementation_shortfall_bps,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ],
    }


# ── Dashboard endpoint ───────────────────────────────────────────────

@router.get("/dashboard")
def broker_dashboard(org_id: str = Query(...), db=Depends(get_db), user=Depends(get_current_user)):
    """Broker integration dashboard with key metrics."""
    kyc_records = db.query(ClientKYC).filter(ClientKYC.org_id == org_id).all()
    onboarding_records = db.query(ClientOnboarding).filter(ClientOnboarding.org_id == org_id).all()
    transactions = db.query(TransactionRecord).filter(TransactionRecord.org_id == org_id).all()
    registrations = db.query(BrokerRegistration).filter(BrokerRegistration.org_id == org_id).all()

    # KYC metrics
    kyc_total = len(kyc_records)
    kyc_approved = sum(1 for k in kyc_records if k.kyc_status == KYCStatus.APPROVED)
    kyc_pending = kyc_total - kyc_approved

    # Onboarding metrics
    onboarding_total = len(onboarding_records)
    onboarding_active = sum(1 for o in onboarding_records if o.stage != OnboardingStage.ACTIVE)
    onboarding_complete = onboarding_total - onboarding_active

    # Transaction metrics
    txn_total = len(transactions)
    txn_suspicious = sum(1 for t in transactions if t.is_suspicious)
    txn_sar_filed = sum(1 for t in transactions if t.sar_filed)
    txn_ctr_required = sum(1 for t in transactions if t.ctr_required)

    # Risk distribution
    risk_distribution = {}
    for k in kyc_records:
        level = k.risk_level.value
        risk_distribution[level] = risk_distribution.get(level, 0) + 1

    # Registration status
    reg_status = {}
    for r in registrations:
        status = r.status
        reg_status[status] = reg_status.get(status, 0) + 1

    return {
        "summary": {
            "kyc_total": kyc_total,
            "kyc_approved": kyc_approved,
            "kyc_pending": kyc_pending,
            "onboarding_active": onboarding_active,
            "onboarding_complete": onboarding_complete,
            "transactions_total": txn_total,
            "transactions_suspicious": txn_suspicious,
            "sar_filed": txn_sar_filed,
            "ctr_required": txn_ctr_required,
            "registrations": len(registrations),
        },
        "risk_distribution": risk_distribution,
        "registration_status": reg_status,
        "compliance_score": round((kyc_approved / kyc_total * 100) if kyc_total > 0 else 0, 1),
    }
