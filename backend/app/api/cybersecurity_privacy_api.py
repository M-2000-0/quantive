"""Cybersecurity, Privacy, and Interoperability API.

Endpoints:
  POST /api/security/monitoring                 - Create regulatory monitoring
  GET  /api/security/monitoring                 - List monitoring

  POST /api/security/cybersecurity              - Create cybersecurity control
  GET  /api/security/cybersecurity              - List cybersecurity controls

  POST /api/security/privacy                    - Create privacy policy
  GET  /api/security/privacy                    - List privacy policies

  POST /api/security/interoperability           - Create interoperability standard
  GET  /api/security/interoperability           - List interoperability standards

  GET  /api/security/dashboard                  - Security dashboard
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import get_db
from app.security import get_current_user
from app.models.cybersecurity_privacy import (
    RegulatoryMonitoring, MonitoringStatus, AlertSeverity,
    CybersecurityControl, SecurityControlType, SecurityStatus,
    DataPrivacyCompliance, PrivacyFramework, DataClassification,
    InteroperabilityStandard, InteroperabilityFramework, ComplianceStandardStatus,
)

router = APIRouter(prefix="/api/security", tags=["Cybersecurity and Privacy"])


# --- Schemas ---

class MonitoringCreateRequest(BaseModel):
    org_id: str
    monitor_name: str
    description: str | None = None
    target_model_name: str | None = None
    target_model_version: str | None = None
    signal_types: list[str] | None = None
    sampling_interval_seconds: int = 60
    metrics_tracked: list[str] | None = None
    accuracy_threshold: float = 0.85
    latency_threshold_ms: float = 100.0
    drift_threshold_pct: float = 5.0

class CybersecurityCreateRequest(BaseModel):
    org_id: str
    control_name: str
    control_type: str
    description: str | None = None
    encryption_algorithm: str | None = None
    key_length_bits: int | None = None
    key_rotation_days: int | None = None
    adversarial_testing_frequency: str | None = None
    attack_types_defended: list[str] | None = None

class PrivacyCreateRequest(BaseModel):
    org_id: str
    policy_name: str
    framework: str
    description: str | None = None
    data_types: list[str] | None = None
    data_classification: str = "confidential"
    jurisdictions: list[str] | None = None
    encryption_required: bool = True
    data_retention_days: int = 365

class InteroperabilityCreateRequest(BaseModel):
    org_id: str
    standard_name: str
    framework: str
    description: str | None = None
    jurisdictions: list[str] | None = None
    asset_types: list[str] | None = None
    exchange_venues: list[str] | None = None
    aml_kyc_standard: str | None = None
    settlement_systems: list[str] | None = None


# --- 1. Real-Time Regulatory Monitoring ---

@router.post("/monitoring")
def create_monitoring(req: MonitoringCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    monitor = RegulatoryMonitoring(
        org_id=req.org_id, monitor_name=req.monitor_name,
        description=req.description,
        target_model_name=req.target_model_name,
        target_model_version=req.target_model_version,
        signal_types=req.signal_types or ["accuracy", "latency", "drift"],
        sampling_interval_seconds=req.sampling_interval_seconds,
        metrics_tracked=req.metrics_tracked or ["accuracy", "latency", "drift", "throughput"],
        accuracy_threshold=req.accuracy_threshold,
        latency_threshold_ms=req.latency_threshold_ms,
        drift_threshold_pct=req.drift_threshold_pct,
        status=MonitoringStatus.ACTIVE,
    )
    db.add(monitor)
    db.commit()
    db.refresh(monitor)
    return {"id": monitor.id, "status": monitor.status.value, "message": "Monitoring created"}


@router.get("/monitoring")
def list_monitoring(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(RegulatoryMonitoring)
    if org_id:
        q = q.filter(RegulatoryMonitoring.org_id == org_id)
    items = q.order_by(RegulatoryMonitoring.created_at.desc()).all()
    return {
        "monitoring": [
            {
                "id": m.id, "monitor_name": m.monitor_name,
                "status": m.status.value,
                "target_model_name": m.target_model_name,
                "sampling_interval_seconds": m.sampling_interval_seconds,
                "accuracy_threshold": m.accuracy_threshold,
                "latency_threshold_ms": m.latency_threshold_ms,
                "drift_threshold_pct": m.drift_threshold_pct,
                "current_accuracy": m.current_accuracy,
                "current_latency_ms": m.current_latency_ms,
                "current_drift_pct": m.current_drift_pct,
                "total_signals_captured": m.total_signals_captured,
                "total_alerts_fired": m.total_alerts_fired,
            }
            for m in items
        ],
        "total": len(items),
    }


# --- 2. Cybersecurity Controls ---

@router.post("/cybersecurity")
def create_cybersecurity_control(req: CybersecurityCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    ctrl = CybersecurityControl(
        org_id=req.org_id, control_name=req.control_name,
        control_type=SecurityControlType(req.control_type),
        description=req.description,
        encryption_algorithm=req.encryption_algorithm,
        key_length_bits=req.key_length_bits,
        key_rotation_days=req.key_rotation_days,
        adversarial_testing_frequency=req.adversarial_testing_frequency,
        attack_types_defended=req.attack_types_defended,
        status=SecurityStatus.IN_PROGRESS,
    )
    db.add(ctrl)
    db.commit()
    db.refresh(ctrl)
    return {"id": ctrl.id, "status": ctrl.status.value, "message": "Control created"}


@router.get("/cybersecurity")
def list_cybersecurity_controls(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(CybersecurityControl)
    if org_id:
        q = q.filter(CybersecurityControl.org_id == org_id)
    items = q.order_by(CybersecurityControl.created_at.desc()).all()
    return {
        "controls": [
            {
                "id": c.id, "control_name": c.control_name,
                "control_type": c.control_type.value, "status": c.status.value,
                "encryption_algorithm": c.encryption_algorithm,
                "key_length_bits": c.key_length_bits,
                "adversarial_robustness_score": c.adversarial_robustness_score,
                "model_integrity_verification": c.model_integrity_verification,
                "security_score": c.security_score,
                "vulnerabilities_found": c.vulnerabilities_found,
                "vulnerabilities_remediated": c.vulnerabilities_remediated,
            }
            for c in items
        ],
        "total": len(items),
    }


# --- 3. Data Privacy Compliance ---

@router.post("/privacy")
def create_privacy_policy(req: PrivacyCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    policy = DataPrivacyCompliance(
        org_id=req.org_id, policy_name=req.policy_name,
        framework=PrivacyFramework(req.framework),
        description=req.description,
        data_types=req.data_types,
        data_classification=DataClassification(req.data_classification),
        jurisdictions=req.jurisdictions,
        encryption_required=req.encryption_required,
        data_retention_days=req.data_retention_days,
        is_compliant=False,
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return {"id": policy.id, "framework": policy.framework.value, "message": "Privacy policy created"}


@router.get("/privacy")
def list_privacy_policies(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(DataPrivacyCompliance)
    if org_id:
        q = q.filter(DataPrivacyCompliance.org_id == org_id)
    items = q.order_by(DataPrivacyCompliance.created_at.desc()).all()
    return {
        "policies": [
            {
                "id": p.id, "policy_name": p.policy_name,
                "framework": p.framework.value,
                "data_classification": p.data_classification.value,
                "is_compliant": p.is_compliant,
                "encryption_required": p.encryption_required,
                "anonymization_required": p.anonymization_required,
                "data_retention_days": p.data_retention_days,
                "right_to_erasure": p.right_to_erasure,
                "breach_notification_hours": p.breach_notification_hours,
                "dpia_completed": p.dpia_completed,
                "privacy_score": p.privacy_score,
            }
            for p in items
        ],
        "total": len(items),
    }


# --- 4. Interoperability Standards ---

@router.post("/interoperability")
def create_interoperability_standard(req: InteroperabilityCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    standard = InteroperabilityStandard(
        org_id=req.org_id, standard_name=req.standard_name,
        framework=InteroperabilityFramework(req.framework),
        description=req.description,
        jurisdictions=req.jurisdictions,
        asset_types=req.asset_types,
        exchange_venues=req.exchange_venues,
        aml_kyc_standard=req.aml_kyc_standard,
        settlement_systems=req.settlement_systems,
        status=ComplianceStandardStatus.PLANNED,
    )
    db.add(standard)
    db.commit()
    db.refresh(standard)
    return {"id": standard.id, "status": standard.status.value, "message": "Standard created"}


@router.get("/interoperability")
def list_interoperability_standards(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(InteroperabilityStandard)
    if org_id:
        q = q.filter(InteroperabilityStandard.org_id == org_id)
    items = q.order_by(InteroperabilityStandard.created_at.desc()).all()
    return {
        "standards": [
            {
                "id": s.id, "standard_name": s.standard_name,
                "framework": s.framework.value, "status": s.status.value,
                "jurisdictions": s.jurisdictions,
                "asset_types": s.asset_types,
                "aml_kyc_standard": s.aml_kyc_standard,
                "settlement_systems": s.settlement_systems,
                "compatibility_score": s.compatibility_score,
                "messages_processed": s.messages_processed,
                "error_rate_pct": s.error_rate_pct,
            }
            for s in items
        ],
        "total": len(items),
    }


# --- Dashboard ---

@router.get("/dashboard")
def security_dashboard(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q_mon = db.query(RegulatoryMonitoring)
    q_sec = db.query(CybersecurityControl)
    q_pri = db.query(DataPrivacyCompliance)
    q_int = db.query(InteroperabilityStandard)
    if org_id:
        q_mon = q_mon.filter(RegulatoryMonitoring.org_id == org_id)
        q_sec = q_sec.filter(CybersecurityControl.org_id == org_id)
        q_pri = q_pri.filter(DataPrivacyCompliance.org_id == org_id)
        q_int = q_int.filter(InteroperabilityStandard.org_id == org_id)

    monitors = q_mon.all()
    controls = q_sec.all()
    policies = q_pri.all()
    standards = q_int.all()

    active_monitors = sum(1 for m in monitors if m.status == MonitoringStatus.ACTIVE)
    compliant_controls = sum(1 for c in controls if c.status == SecurityStatus.COMPLIANT)
    compliant_policies = sum(1 for p in policies if p.is_compliant)
    supported_standards = sum(1 for s in standards if s.status == ComplianceStandardStatus.SUPPORTED)

    avg_security_score = sum(c.security_score for c in controls) / len(controls) if controls else 0
    avg_privacy_score = sum(p.privacy_score for p in policies) / len(policies) if policies else 0
    avg_compatibility = sum(s.compatibility_score for s in standards) / len(standards) if standards else 0

    total_vulns = sum(c.vulnerabilities_found for c in controls)
    total_remediated = sum(c.vulnerabilities_remediated for c in controls)

    return {
        "monitoring": {"total": len(monitors), "active": active_monitors},
        "cybersecurity": {"total": len(controls), "compliant": compliant_controls, "total_vulnerabilities": total_vulns, "remediated": total_remediated},
        "privacy": {"total": len(policies), "compliant": compliant_policies},
        "interoperability": {"total": len(standards), "supported": supported_standards},
        "scores": {"security": round(avg_security_score, 1), "privacy": round(avg_privacy_score, 1), "compatibility": round(avg_compatibility, 1)},
        "recent_alerts": [
            {"id": m.id, "name": m.monitor_name, "status": m.status.value,
             "accuracy": m.current_accuracy, "latency": m.current_latency_ms}
            for m in monitors[:5]
        ],
    }
