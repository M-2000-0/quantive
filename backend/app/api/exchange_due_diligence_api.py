"""Exchange Due Diligence API - Pre-Trade Controls, Simulation, Surveillance, Proof of Reserve.

Endpoints:
  POST /api/due-diligence/pre-trade-controls         - Create pre-trade control
  GET  /api/due-diligence/pre-trade-controls         - List pre-trade controls

  POST /api/due-diligence/simulations                - Create simulation environment
  GET  /api/due-diligence/simulations                - List simulation environments

  POST /api/due-diligence/surveillance               - List surveillance alerts
  POST /api/due-diligence/surveillance/{id}/resolve  - Resolve alert

  POST /api/due-diligence/proof-of-reserve           - Create proof of reserve
  GET  /api/due-diligence/proof-of-reserve           - List proofs of reserve

  POST /api/due-diligence/decision-logs              - Create decision log
  GET  /api/due-diligence/decision-logs              - List decision logs

  GET  /api/due-diligence/dashboard                  - Due diligence dashboard
"""

from datetime import datetime, timezone
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func

from app.database import get_db
from app.security import get_current_user
from app.models.exchange_due_diligence import (
    PreTradeControl, ControlType, ControlStatus,
    SimulationEnvironment, SimulationStatus,
    MarketSurveillance, SurveillanceAlertType, SurveillanceSeverity, SurveillanceStatus,
    ProofOfReserve, ReserveChain, ReserveStatus,
    DecisionLog, DecisionType,
)

router = APIRouter(prefix="/api/due-diligence", tags=["Exchange Due Diligence"])


# --- Schemas ---

class PreTradeControlCreateRequest(BaseModel):
    org_id: str
    exchange_connection_id: str | None = None
    control_name: str
    control_type: str
    description: str | None = None
    max_value: float
    warning_threshold_pct: float = 80.0
    currency: str = "USD"
    time_window_minutes: int = 60
    price_collar_upper_pct: float | None = None
    price_collar_lower_pct: float | None = None
    self_trade_enabled: bool = True
    reject_on_breach: bool = True

class SimulationCreateRequest(BaseModel):
    org_id: str
    environment_name: str
    description: str | None = None
    exchange_venue: str
    instrument_types: list[str] | None = None
    historical_period: str | None = None
    starting_capital: float = 10000000.0
    simulated_latency_ms: float = 50.0
    slippage_bps: float = 2.0

class SurveillanceResolveRequest(BaseModel):
    assigned_to: str
    resolution: str
    reported_to_authority: bool = False
    authority_reference: str | None = None

class ProofOfReserveCreateRequest(BaseModel):
    org_id: str
    reserve_name: str
    custodian_name: str
    jurisdiction: str
    total_reserves: float
    total_liabilities: float
    currency: str = "USD"
    chain: str | None = None
    zero_knowledge_proof: bool = False

class DecisionLogCreateRequest(BaseModel):
    org_id: str
    exchange_connection_id: str | None = None
    model_card_id: str | None = None
    decision_type: str
    decision_id: str
    instrument_type: str | None = None
    instrument_identifier: str | None = None
    action: str
    side: str | None = None
    quantity: float | None = None
    price: float | None = None
    model_name: str | None = None
    model_version: str | None = None
    confidence_score: float = 0.0
    feature_contributions: list[dict] | None = None
    shap_values: dict | None = None
    explanation_text: str | None = None
    human_review_required: bool = False


def sha256_hash(data: str) -> str:
    return sha256(data.encode()).hexdigest()


# --- 1. Pre-Trade Controls ---

@router.post("/pre-trade-controls")
def create_pre_trade_control(req: PreTradeControlCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    ctrl = PreTradeControl(
        org_id=req.org_id, exchange_connection_id=req.exchange_connection_id,
        control_name=req.control_name, control_type=ControlType(req.control_type),
        description=req.description, max_value=req.max_value,
        warning_threshold_pct=req.warning_threshold_pct, currency=req.currency,
        time_window_minutes=req.time_window_minutes,
        price_collar_upper_pct=req.price_collar_upper_pct,
        price_collar_lower_pct=req.price_collar_lower_pct,
        self_trade_enabled=req.self_trade_enabled,
        reject_on_breach=req.reject_on_breach,
        status=ControlStatus.ACTIVE,
    )
    db.add(ctrl)
    db.commit()
    db.refresh(ctrl)
    return {"id": ctrl.id, "status": ctrl.status.value, "message": "Pre-trade control created"}


@router.get("/pre-trade-controls")
def list_pre_trade_controls(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(PreTradeControl)
    if org_id:
        q = q.filter(PreTradeControl.org_id == org_id)
    items = q.order_by(PreTradeControl.created_at.desc()).all()
    return {
        "pre_trade_controls": [
            {
                "id": c.id, "control_name": c.control_name,
                "control_type": c.control_type.value, "status": c.status.value,
                "max_value": c.max_value, "currency": c.currency,
                "warning_threshold_pct": c.warning_threshold_pct,
                "reject_on_breach": c.reject_on_breach,
                "total_checks": c.total_checks, "total_breaches": c.total_breaches,
                "self_trade_enabled": c.self_trade_enabled,
            }
            for c in items
        ],
        "total": len(items),
    }


# --- 2. Simulation Environments ---

@router.post("/simulations")
def create_simulation(req: SimulationCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    sim = SimulationEnvironment(
        org_id=req.org_id, environment_name=req.environment_name,
        description=req.description, exchange_venue=req.exchange_venue,
        instrument_types=req.instrument_types, historical_period=req.historical_period,
        starting_capital=req.starting_capital, simulated_latency_ms=req.simulated_latency_ms,
        slippage_bps=req.slippage_bps, status=SimulationStatus.CREATED,
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)
    return {"id": sim.id, "status": sim.status.value, "message": "Simulation created"}


@router.get("/simulations")
def list_simulations(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(SimulationEnvironment)
    if org_id:
        q = q.filter(SimulationEnvironment.org_id == org_id)
    items = q.order_by(SimulationEnvironment.created_at.desc()).all()
    return {
        "simulations": [
            {
                "id": s.id, "environment_name": s.environment_name,
                "exchange_venue": s.exchange_venue, "status": s.status.value,
                "starting_capital": s.starting_capital,
                "simulated_latency_ms": s.simulated_latency_ms,
                "total_trades": s.total_trades, "total_pnl": s.total_pnl,
                "sharpe_ratio": s.sharpe_ratio, "max_drawdown_pct": s.max_drawdown_pct,
                "win_rate_pct": s.win_rate_pct,
                "kill_switch_triggered": s.kill_switch_triggered,
            }
            for s in items
        ],
        "total": len(items),
    }


# --- 3. Market Surveillance ---

@router.get("/surveillance")
def list_surveillance_alerts(org_id: str = Query(None), severity: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(MarketSurveillance)
    if org_id:
        q = q.filter(MarketSurveillance.org_id == org_id)
    if severity:
        q = q.filter(MarketSurveillance.severity == SurveillanceSeverity(severity))
    items = q.order_by(MarketSurveillance.detected_at.desc()).all()
    return {
        "alerts": [
            {
                "id": a.id, "alert_type": a.alert_type.value,
                "severity": a.severity.value, "status": a.status.value,
                "title": a.title, "description": a.description,
                "instrument_identifier": a.instrument_identifier,
                "confidence_score": a.confidence_score,
                "price_at_detection": a.price_at_detection,
                "volume_at_detection": a.volume_at_detection,
                "assigned_to": a.assigned_to,
                "detected_at": a.detected_at.isoformat() if a.detected_at else None,
            }
            for a in items
        ],
        "total": len(items),
    }


@router.post("/surveillance/{alert_id}/resolve")
def resolve_surveillance_alert(alert_id: str, req: SurveillanceResolveRequest, db=Depends(get_db), user=Depends(get_current_user)):
    alert = db.get(MarketSurveillance, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = SurveillanceStatus.RESOLVED
    alert.assigned_to = req.assigned_to
    alert.resolution = req.resolution
    alert.reported_to_authority = req.reported_to_authority
    alert.authority_reference = req.authority_reference
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": alert.id, "status": alert.status.value, "message": "Alert resolved"}


# --- 4. Proof of Reserve ---

@router.post("/proof-of-reserve")
def create_proof_of_reserve(req: ProofOfReserveCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    ratio = (req.total_reserves / req.total_liabilities * 100) if req.total_liabilities > 0 else 100.0
    por = ProofOfReserve(
        org_id=req.org_id, reserve_name=req.reserve_name,
        custodian_name=req.custodian_name, jurisdiction=req.jurisdiction,
        total_reserves=req.total_reserves, total_liabilities=req.total_liabilities,
        reserve_ratio_pct=ratio, excess_reserves=req.total_reserves - req.total_liabilities,
        currency=req.currency,
        chain=ReserveChain(req.chain) if req.chain else None,
        zero_knowledge_proof=req.zero_knowledge_proof,
        status=ReserveStatus.PENDING,
    )
    db.add(por)
    db.commit()
    db.refresh(por)
    return {"id": por.id, "status": por.status.value, "reserve_ratio_pct": ratio}


@router.get("/proof-of-reserve")
def list_proofs_of_reserve(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(ProofOfReserve)
    if org_id:
        q = q.filter(ProofOfReserve.org_id == org_id)
    items = q.order_by(ProofOfReserve.created_at.desc()).all()
    return {
        "proofs": [
            {
                "id": p.id, "reserve_name": p.reserve_name,
                "custodian_name": p.custodian_name, "jurisdiction": p.jurisdiction,
                "total_reserves": p.total_reserves, "total_liabilities": p.total_liabilities,
                "reserve_ratio_pct": p.reserve_ratio_pct, "status": p.status.value,
                "chain": p.chain.value if p.chain else None,
                "zero_knowledge_proof": p.zero_knowledge_proof,
                "attestation_service": p.attestation_service,
            }
            for p in items
        ],
        "total": len(items),
    }


# --- 5. Decision Logs ---

@router.post("/decision-logs")
def create_decision_log(req: DecisionLogCreateRequest, db=Depends(get_db), user=Depends(get_current_user)):
    total_value = (req.quantity or 0) * (req.price or 0)
    event_hash = sha256_hash(f"{req.decision_id}{req.decision_type}{req.action}{datetime.now(timezone.utc).isoformat()}")
    prev_hash = sha256_hash("previous")
    dl = DecisionLog(
        org_id=req.org_id, exchange_connection_id=req.exchange_connection_id,
        model_card_id=req.model_card_id,
        decision_type=DecisionType(req.decision_type),
        decision_id=req.decision_id,
        instrument_type=req.instrument_type,
        instrument_identifier=req.instrument_identifier,
        action=req.action, side=req.side,
        quantity=req.quantity, price=req.price,
        total_value=total_value,
        model_name=req.model_name, model_version=req.model_version,
        confidence_score=req.confidence_score,
        feature_contributions=req.feature_contributions,
        shap_values=req.shap_values,
        explanation_text=req.explanation_text,
        human_review_required=req.human_review_required,
        pre_trade_checks_passed=True,
        event_hash=event_hash, previous_event_hash=prev_hash,
    )
    db.add(dl)
    db.commit()
    db.refresh(dl)
    return {"id": dl.id, "event_hash": dl.event_hash, "message": "Decision logged"}


@router.get("/decision-logs")
def list_decision_logs(org_id: str = Query(None), decision_type: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q = db.query(DecisionLog)
    if org_id:
        q = q.filter(DecisionLog.org_id == org_id)
    if decision_type:
        q = q.filter(DecisionLog.decision_type == DecisionType(decision_type))
    items = q.order_by(DecisionLog.decision_timestamp.desc()).all()
    return {
        "decision_logs": [
            {
                "id": d.id, "decision_type": d.decision_type.value,
                "decision_id": d.decision_id,
                "instrument_type": d.instrument_type,
                "instrument_identifier": d.instrument_identifier,
                "action": d.action, "side": d.side,
                "quantity": d.quantity, "price": d.price,
                "total_value": d.total_value,
                "model_name": d.model_name,
                "confidence_score": d.confidence_score,
                "feature_contributions": d.feature_contributions,
                "shap_values": d.shap_values,
                "explanation_text": d.explanation_text,
                "pre_trade_checks_passed": d.pre_trade_checks_passed,
                "human_review_required": d.human_review_required,
                "human_reviewed": d.human_reviewed,
                "event_hash": d.event_hash,
                "tamper_evident": d.tamper_evident,
                "decision_timestamp": d.decision_timestamp.isoformat() if d.decision_timestamp else None,
            }
            for d in items
        ],
        "total": len(items),
    }


# --- Dashboard ---

@router.get("/dashboard")
def due_diligence_dashboard(org_id: str = Query(None), db=Depends(get_db), user=Depends(get_current_user)):
    q_ctrl = db.query(PreTradeControl)
    q_sim = db.query(SimulationEnvironment)
    q_surv = db.query(MarketSurveillance)
    q_por = db.query(ProofOfReserve)
    q_dl = db.query(DecisionLog)
    if org_id:
        q_ctrl = q_ctrl.filter(PreTradeControl.org_id == org_id)
        q_sim = q_sim.filter(SimulationEnvironment.org_id == org_id)
        q_surv = q_surv.filter(MarketSurveillance.org_id == org_id)
        q_por = q_por.filter(ProofOfReserve.org_id == org_id)
        q_dl = q_dl.filter(DecisionLog.org_id == org_id)

    controls = q_ctrl.all()
    sims = q_sim.all()
    alerts = q_surv.all()
    reserves = q_por.all()
    decisions = q_dl.all()

    active_controls = sum(1 for c in controls if c.status == ControlStatus.ACTIVE)
    breached_controls = sum(1 for c in controls if c.status == ControlStatus.BREACHED)
    open_alerts = sum(1 for a in alerts if a.status in (SurveillanceStatus.OPEN, SurveillanceStatus.INVESTIGATING))
    critical_alerts = sum(1 for a in alerts if a.severity == SurveillanceSeverity.CRITICAL and a.status != SurveillanceStatus.RESOLVED)
    verified_reserves = sum(1 for r in reserves if r.status == ReserveStatus.VERIFIED)
    human_reviewed = sum(1 for d in decisions if d.human_reviewed)
    total_breaches = sum(c.total_breaches for c in controls)

    return {
        "pre_trade_controls": {"total": len(controls), "active": active_controls, "breached": breached_controls, "total_breaches": total_breaches},
        "simulations": {"total": len(sims), "completed": sum(1 for s in sims if s.status == SimulationStatus.COMPLETED)},
        "surveillance": {"total": len(alerts), "open": open_alerts, "critical": critical_alerts},
        "proof_of_reserves": {"total": len(reserves), "verified": verified_reserves},
        "decision_logs": {"total": len(decisions), "human_reviewed": human_reviewed, "with_shap": sum(1 for d in decisions if d.shap_values)},
        "recent_alerts": [
            {"id": a.id, "type": a.alert_type.value, "severity": a.severity.value,
             "title": a.title, "status": a.status.value}
            for a in alerts[:5]
        ],
        "recent_decisions": [
            {"id": d.id, "type": d.decision_type.value, "action": d.action,
             "instrument": d.instrument_identifier, "confidence": d.confidence_score,
             "human_reviewed": d.human_reviewed}
            for d in decisions[:5]
        ],
    }
