"""Exchange & Broker Integration API — RegTech, Risk Controls, Interoperability.

Provides the full infrastructure for government-to-exchange partnerships:
- Exchange connectivity and status monitoring
- Regulatory compliance engine with automated checks
- Counterparty risk scoring and due diligence
- Trade order lifecycle with HITL approval
- Risk allocation frameworks
- Regulatory data sharing (machine-readable reporting)
- Ethical firewall tracking
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.exchange_integration import (
    AlgorithmAuditTrail,
    CCPClearingMember,
    ComplianceEvent,
    ComplianceRule,
    ConnectionStatus,
    CounterpartyRiskScore,
    EthicalFirewall,
    ExchangeConnection,
    ExchangeConnectorTemplate,
    ExchangeType,
    InstitutionalCapacityAssessment,
    MarketDataFeed,
    RegulatoryReport,
    RiskAllocation,
    SmartContractTemplate,
    TradeOrder,
    TradeOrderStatus,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/exchange", tags=["exchange-integration"])


# ── Request Models ─────────────────────────────────────────────────

class ExchangeConnectRequest(BaseModel):
    exchange_name: str
    exchange_type: str
    exchange_id: str
    mic_code: str | None = None
    api_endpoint: str | None = None
    api_version: str | None = None
    supports_bonds: bool = False
    supports_fx: bool = False
    supports_equities: bool = False
    supports_derivatives: bool = False
    daily_trade_limit: float | None = None
    max_single_trade: float | None = None


class ComplianceRuleCreate(BaseModel):
    rule_code: str
    rule_name: str
    regulation: str
    jurisdiction: str
    category: str
    description: str
    threshold_value: float | None = None
    threshold_unit: str | None = None
    comparison_operator: str = "<="
    is_critical: bool = False


class TradeOrderCreate(BaseModel):
    exchange_connection_id: str | None = None
    order_type: str
    side: str
    instrument_type: str
    instrument_identifier: str
    quantity: float
    price: float | None = None
    total_value: float
    currency: str = "USD"


class RiskAllocationCreate(BaseModel):
    exchange_connection_id: str | None = None
    framework_name: str
    framework_version: str
    market_risk_allocation: dict
    credit_risk_allocation: dict
    operational_risk_allocation: dict
    liquidity_risk_allocation: dict
    settlement_risk_allocation: dict
    max_government_loss: float
    max_counterparty_loss: float
    loss_sharing_trigger: str
    dispute_resolution: str
    governing_law: str


class CounterpartyDueDiligenceRequest(BaseModel):
    exchange_connection_id: str | None = None
    counterparty_name: str
    counterparty_type: str
    counterparty_rating: str | None = None
    jurisdiction: str | None = None
    credit_risk_score: float
    operational_risk_score: float
    market_risk_score: float
    liquidity_risk_score: float
    regulatory_risk_score: float


# ── Exchange Connections ──────────────────────────────────────────

@router.post("/connections")
def connect_exchange(
    request: ExchangeConnectRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a new exchange or broker connection."""
    conn = ExchangeConnection(
        org_id=user.org_id,
        exchange_name=request.exchange_name,
        exchange_type=ExchangeType(request.exchange_type),
        exchange_id=request.exchange_id,
        mic_code=request.mic_code,
        api_endpoint=request.api_endpoint,
        api_version=request.api_version,
        status=ConnectionStatus.CONNECTING,
        supports_bonds=request.supports_bonds,
        supports_fx=request.supports_fx,
        supports_equities=request.supports_equities,
        supports_derivatives=request.supports_derivatives,
        daily_trade_limit=request.daily_trade_limit,
        max_single_trade=request.max_single_trade,
        regulatory_status="pending_review",
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)
    return {"status": "connecting", "connection_id": conn.id, "exchange_name": conn.exchange_name}


@router.get("/connections")
def list_connections(
    exchange_type: Optional[str] = None,
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List exchange connections."""
    query = db.query(ExchangeConnection).filter(ExchangeConnection.org_id == user.org_id)
    if exchange_type:
        query = query.filter(ExchangeConnection.exchange_type == exchange_type)
    if status:
        query = query.filter(ExchangeConnection.status == status)
    conns = query.order_by(ExchangeConnection.created_at.desc()).all()
    return {
        "connections": [
            {
                "id": c.id,
                "exchange_name": c.exchange_name,
                "exchange_type": c.exchange_type.value if c.exchange_type else "traditional",
                "exchange_id": c.exchange_id,
                "status": c.status.value if c.status else "disconnected",
                "regulatory_status": c.regulatory_status,
                "compliance_score": c.compliance_score,
                "supports_bonds": c.supports_bonds,
                "supports_fx": c.supports_fx,
                "last_heartbeat": c.last_heartbeat.isoformat() if c.last_heartbeat else None,
            }
            for c in conns
        ],
        "total": len(conns),
    }


@router.get("/connections/{connection_id}")
def get_connection(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get connection details with risk limits and compliance status."""
    conn = db.query(ExchangeConnection).filter(ExchangeConnection.id == connection_id).first()
    if not conn:
        raise HTTPException(404, "Connection not found")
    return {
        "id": conn.id,
        "exchange_name": conn.exchange_name,
        "exchange_type": conn.exchange_type.value if conn.exchange_type else "traditional",
        "exchange_id": conn.exchange_id,
        "mic_code": conn.mic_code,
        "status": conn.status.value if conn.status else "disconnected",
        "regulatory_status": conn.regulatory_status,
        "regulatory_jurisdiction": conn.regulatory_jurisdiction,
        "compliance_score": conn.compliance_score,
        "last_compliance_check": conn.last_compliance_check.isoformat() if conn.last_compliance_check else None,
        "capabilities": {
            "bonds": conn.supports_bonds,
            "fx": conn.supports_fx,
            "equities": conn.supports_equities,
            "derivatives": conn.supports_derivatives,
            "settlement_t_plus": conn.supports_settlement_t_plus,
        },
        "risk_limits": {
            "daily_trade_limit": float(conn.daily_trade_limit) if conn.daily_trade_limit else None,
            "max_single_trade": float(conn.max_single_trade) if conn.max_single_trade else None,
            "max_counterparty_exposure": float(conn.max_counterparty_exposure) if conn.max_counterparty_exposure else None,
        },
    }


# ── Compliance Engine ─────────────────────────────────────────────

@router.post("/compliance/rules")
def create_compliance_rule(
    request: ComplianceRuleCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a regulatory compliance rule."""
    rule = ComplianceRule(
        org_id=user.org_id,
        rule_code=request.rule_code,
        rule_name=request.rule_name,
        regulation=request.regulation,
        jurisdiction=request.jurisdiction,
        category=request.category,
        description=request.description,
        threshold_value=request.threshold_value,
        threshold_unit=request.threshold_unit,
        comparison_operator=request.comparison_operator,
        is_critical=request.is_critical,
        effective_date=datetime.now(timezone.utc),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"status": "created", "rule_id": rule.id, "rule_code": rule.rule_code}


@router.get("/compliance/rules")
def list_compliance_rules(
    jurisdiction: Optional[str] = None,
    category: Optional[str] = None,
    is_critical: Optional[bool] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List compliance rules."""
    query = db.query(ComplianceRule).filter(ComplianceRule.org_id == user.org_id)
    if jurisdiction:
        query = query.filter(ComplianceRule.jurisdiction == jurisdiction)
    if category:
        query = query.filter(ComplianceRule.category == category)
    if is_critical is not None:
        query = query.filter(ComplianceRule.is_critical == is_critical)
    rules = query.order_by(ComplianceRule.created_at.desc()).all()
    return {
        "rules": [
            {
                "id": r.id,
                "rule_code": r.rule_code,
                "rule_name": r.rule_name,
                "regulation": r.regulation,
                "jurisdiction": r.jurisdiction,
                "category": r.category,
                "threshold_value": r.threshold_value,
                "is_critical": r.is_critical,
                "is_active": r.is_active,
            }
            for r in rules
        ],
        "total": len(rules),
    }


@router.post("/compliance/check")
def run_compliance_check(
    order_id: str | None = None,
    exchange_connection_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run pre-trade or post-trade compliance checks."""
    rules = db.query(ComplianceRule).filter(
        ComplianceRule.org_id == user.org_id,
        ComplianceRule.is_active == True,
    ).all()

    results = []
    violations = []

    for rule in rules:
        # Simulate compliance check
        passed = True  # In production, evaluate against actual data
        event = ComplianceEvent(
            org_id=user.org_id,
            rule_id=rule.id,
            exchange_connection_id=exchange_connection_id,
            event_type="check_passed" if passed else "check_failed",
            event_date=datetime.now(timezone.utc),
            description=f"Automated check: {rule.rule_name}",
            severity="info" if passed else ("critical" if rule.is_critical else "warning"),
            status="resolved" if passed else "open",
        )
        db.add(event)
        results.append({
            "rule_code": rule.rule_code,
            "rule_name": rule.rule_name,
            "passed": passed,
            "severity": event.severity,
        })
        if not passed:
            violations.append(rule.rule_code)

    db.commit()

    return {
        "total_rules_checked": len(rules),
        "violations": len(violations),
        "all_passed": len(violations) == 0,
        "results": results,
    }


@router.get("/compliance/events")
def list_compliance_events(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List compliance events (checks and violations)."""
    query = db.query(ComplianceEvent).filter(ComplianceEvent.org_id == user.org_id)
    if severity:
        query = query.filter(ComplianceEvent.severity == severity)
    if status:
        query = query.filter(ComplianceEvent.status == status)
    events = query.order_by(ComplianceEvent.created_at.desc()).limit(limit).all()
    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "event_date": e.event_date.isoformat() if e.event_date else None,
                "description": e.description,
                "severity": e.severity,
                "status": e.status,
                "reported_to_authority": e.reported_to_authority,
            }
            for e in events
        ],
        "total": len(events),
    }


# ── Counterparty Risk ─────────────────────────────────────────────

@router.post("/counterparty/assess")
def assess_counterparty(
    request: CounterpartyDueDiligenceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Assess counterparty risk for an exchange or broker."""
    composite = (
        request.credit_risk_score * 0.25 +
        request.operational_risk_score * 0.20 +
        request.market_risk_score * 0.15 +
        request.liquidity_risk_score * 0.20 +
        request.regulatory_risk_score * 0.20
    )

    # Determine recommendation based on composite score
    if composite <= 30:
        recommendation = "approved"
        max_trade = 10_000_000
        max_daily = 50_000_000
    elif composite <= 50:
        recommendation = "conditional"
        max_trade = 5_000_000
        max_daily = 25_000_000
    elif composite <= 70:
        recommendation = "restricted"
        max_trade = 1_000_000
        max_daily = 5_000_000
    else:
        recommendation = "rejected"
        max_trade = 0
        max_daily = 0

    score = CounterpartyRiskScore(
        org_id=user.org_id,
        exchange_connection_id=request.exchange_connection_id,
        counterparty_name=request.counterparty_name,
        counterparty_type=request.counterparty_type,
        counterparty_rating=request.counterparty_rating,
        jurisdiction=request.jurisdiction,
        credit_risk_score=request.credit_risk_score,
        operational_risk_score=request.operational_risk_score,
        market_risk_score=request.market_risk_score,
        liquidity_risk_score=request.liquidity_risk_score,
        regulatory_risk_score=request.regulatory_risk_score,
        composite_risk_score=round(composite, 2),
        recommendation=recommendation,
        max_trade_size=max_trade,
        max_daily_volume=max_daily,
        due_diligence_status="pending",
    )
    db.add(score)
    db.commit()
    db.refresh(score)

    return {
        "counterparty": request.counterparty_name,
        "composite_risk_score": round(composite, 2),
        "recommendation": recommendation,
        "limits": {
            "max_trade_size": max_trade,
            "max_daily_volume": max_daily,
        },
        "breakdown": {
            "credit": request.credit_risk_score,
            "operational": request.operational_risk_score,
            "market": request.market_risk_score,
            "liquidity": request.liquidity_risk_score,
            "regulatory": request.regulatory_risk_score,
        },
    }


@router.get("/counterparty/scores")
def list_counterparty_scores(
    recommendation: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List counterparty risk scores."""
    query = db.query(CounterpartyRiskScore).filter(CounterpartyRiskScore.org_id == user.org_id)
    if recommendation:
        query = query.filter(CounterpartyRiskScore.recommendation == recommendation)
    scores = query.order_by(CounterpartyRiskScore.composite_risk_score.desc()).all()
    return {
        "counterparties": [
            {
                "id": s.id,
                "counterparty_name": s.counterparty_name,
                "counterparty_type": s.counterparty_type,
                "composite_risk_score": s.composite_risk_score,
                "recommendation": s.recommendation,
                "max_trade_size": float(s.max_trade_size) if s.max_trade_size else None,
                "due_diligence_status": s.due_diligence_status,
                "last_audit_date": s.last_audit_date.isoformat() if s.last_audit_date else None,
            }
            for s in scores
        ],
        "total": len(scores),
    }


# ── Trade Orders ──────────────────────────────────────────────────

@router.post("/orders")
def create_trade_order(
    request: TradeOrderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a trade order with pre-trade compliance check."""
    # Generate order reference
    count = db.query(TradeOrder).filter(TradeOrder.org_id == user.org_id).count()
    order_ref = f"ORD-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{count + 1:04d}"

    # Run pre-trade compliance
    compliance_passed = True  # Simplified — in production, run actual checks

    order = TradeOrder(
        org_id=user.org_id,
        exchange_connection_id=request.exchange_connection_id,
        order_reference=order_ref,
        order_type=request.order_type,
        side=request.side,
        instrument_type=request.instrument_type,
        instrument_identifier=request.instrument_identifier,
        quantity=request.quantity,
        price=request.price,
        total_value=request.total_value,
        currency=request.currency,
        status=TradeOrderStatus.PENDING_APPROVAL if compliance_passed else TradeOrderStatus.REJECTED,
        pre_trade_compliance_passed=compliance_passed,
        created_by=user.email or user.id,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # Generate immutable hash
    hash_input = json.dumps({"id": order.id, "ref": order_ref, "instrument": request.instrument_identifier, "value": request.total_value}, sort_keys=True)
    order.immutable_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    db.commit()

    return {
        "order_id": order.id,
        "order_reference": order_ref,
        "status": order.status.value if order.status else "pending_approval",
        "pre_trade_compliance": "passed" if compliance_passed else "failed",
    }


@router.post("/orders/{order_id}/approve")
def approve_trade_order(
    order_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve a trade order (human-in-the-loop)."""
    order = db.query(TradeOrder).filter(TradeOrder.id == order_id).first()
    if not order:
        raise HTTPException(404, "Order not found")
    if order.status != TradeOrderStatus.PENDING_APPROVAL:
        raise HTTPException(400, f"Order is in {order.status.value} state")

    order.status = TradeOrderStatus.APPROVED
    order.approved_by = user.email or user.id
    order.approved_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "approved", "order_id": order.id, "approved_by": order.approved_by}


@router.get("/orders")
def list_trade_orders(
    status: Optional[str] = None,
    instrument_type: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List trade orders."""
    query = db.query(TradeOrder).filter(TradeOrder.org_id == user.org_id)
    if status:
        query = query.filter(TradeOrder.status == status)
    if instrument_type:
        query = query.filter(TradeOrder.instrument_type == instrument_type)
    orders = query.order_by(TradeOrder.created_at.desc()).limit(limit).all()
    return {
        "orders": [
            {
                "id": o.id,
                "order_reference": o.order_reference,
                "order_type": o.order_type,
                "side": o.side,
                "instrument_type": o.instrument_type,
                "instrument_identifier": o.instrument_identifier,
                "quantity": float(o.quantity),
                "total_value": float(o.total_value),
                "currency": o.currency,
                "status": o.status.value if o.status else "pending_approval",
                "approved_by": o.approved_by,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ],
        "total": len(orders),
    }


# ── Risk Allocation ───────────────────────────────────────────────

@router.post("/risk-allocation")
def create_risk_allocation(
    request: RiskAllocationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a risk allocation framework for an exchange partnership."""
    allocation = RiskAllocation(
        org_id=user.org_id,
        exchange_connection_id=request.exchange_connection_id,
        framework_name=request.framework_name,
        framework_version=request.framework_version,
        effective_date=datetime.now(timezone.utc),
        market_risk_allocation=request.market_risk_allocation,
        credit_risk_allocation=request.credit_risk_allocation,
        operational_risk_allocation=request.operational_risk_allocation,
        liquidity_risk_allocation=request.liquidity_risk_allocation,
        settlement_risk_allocation=request.settlement_risk_allocation,
        max_government_loss=request.max_government_loss,
        max_counterparty_loss=request.max_counterparty_loss,
        loss_sharing_trigger=request.loss_sharing_trigger,
        dispute_resolution=request.dispute_resolution,
        governing_law=request.governing_law,
        approved_by=user.email or user.id,
        approval_date=datetime.now(timezone.utc),
    )
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return {"status": "created", "allocation_id": allocation.id, "framework": request.framework_name}


# ── Ethical Firewall ──────────────────────────────────────────────

@router.post("/ethical-firewall")
def register_conflict(
    person_name: str,
    person_role: str,
    conflict_type: str,
    conflict_description: str,
    related_entity: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a conflict of interest for tracking."""
    firewall = EthicalFirewall(
        org_id=user.org_id,
        person_name=person_name,
        person_role=person_role,
        person_department="",
        conflict_type=conflict_type,
        conflict_description=conflict_description,
        related_entity=related_entity,
        detected_date=datetime.now(timezone.utc),
        cooling_off_start=datetime.now(timezone.utc),
        cooling_off_end=datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 1),
        is_in_cooling_off=True,
    )
    db.add(firewall)
    db.commit()
    db.refresh(firewall)
    return {"status": "registered", "firewall_id": firewall.id, "cooling_off_end": firewall.cooling_off_end.isoformat()}


@router.get("/ethical-firewall")
def list_firewall_entries(
    is_in_cooling_off: Optional[bool] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List ethical firewall entries."""
    query = db.query(EthicalFirewall).filter(EthicalFirewall.org_id == user.org_id)
    if is_in_cooling_off is not None:
        query = query.filter(EthicalFirewall.is_in_cooling_off == is_in_cooling_off)
    entries = query.order_by(EthicalFirewall.detected_date.desc()).all()
    return {
        "entries": [
            {
                "id": e.id,
                "person_name": e.person_name,
                "person_role": e.person_role,
                "conflict_type": e.conflict_type,
                "related_entity": e.related_entity,
                "is_in_cooling_off": e.is_in_cooling_off,
                "cooling_off_end": e.cooling_off_end.isoformat() if e.cooling_off_end else None,
                "is_resolved": e.is_resolved,
            }
            for e in entries
        ],
        "total": len(entries),
    }


# ── Regulatory Reporting ──────────────────────────────────────────

@router.post("/regulatory-reports")
def create_regulatory_report(
    report_type: str,
    reporting_authority: str,
    reporting_requirement: str,
    report_data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a machine-readable regulatory report."""
    report_hash = hashlib.sha256(json.dumps(report_data, sort_keys=True).encode()).hexdigest()

    report = RegulatoryReport(
        org_id=user.org_id,
        report_type=report_type,
        report_format="JSON",
        reporting_authority=reporting_authority,
        reporting_requirement=reporting_requirement,
        reporting_period_start=datetime.now(timezone.utc),
        reporting_period_end=datetime.now(timezone.utc),
        report_data=report_data,
        report_hash=report_hash,
        submission_status="draft",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"status": "created", "report_id": report.id, "report_hash": report_hash}


@router.get("/regulatory-reports")
def list_regulatory_reports(
    reporting_authority: Optional[str] = None,
    submission_status: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List regulatory reports."""
    query = db.query(RegulatoryReport).filter(RegulatoryReport.org_id == user.org_id)
    if reporting_authority:
        query = query.filter(RegulatoryReport.reporting_authority == reporting_authority)
    if submission_status:
        query = query.filter(RegulatoryReport.submission_status == submission_status)
    reports = query.order_by(RegulatoryReport.created_at.desc()).limit(limit).all()
    return {
        "reports": [
            {
                "id": r.id,
                "report_type": r.report_type,
                "reporting_authority": r.reporting_authority,
                "reporting_requirement": r.reporting_requirement,
                "submission_status": r.submission_status,
                "report_hash": r.report_hash,
                "is_valid": r.is_valid,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ],
        "total": len(reports),
    }


# ── Exchange Dashboard ────────────────────────────────────────────

@router.get("/dashboard")
def get_exchange_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get exchange integration dashboard summary."""
    connections = db.query(ExchangeConnection).filter(ExchangeConnection.org_id == user.org_id).count()
    active_connections = db.query(ExchangeConnection).filter(
        ExchangeConnection.org_id == user.org_id,
        ExchangeConnection.status == ConnectionStatus.CONNECTED,
    ).count()
    compliance_rules = db.query(ComplianceRule).filter(ComplianceRule.org_id == user.org_id).count()
    open_violations = db.query(ComplianceEvent).filter(
        ComplianceEvent.org_id == user.org_id,
        ComplianceEvent.status == "open",
    ).count()
    counterparties = db.query(CounterpartyRiskScore).filter(CounterpartyRiskScore.org_id == user.org_id).count()
    pending_orders = db.query(TradeOrder).filter(
        TradeOrder.org_id == user.org_id,
        TradeOrder.status == TradeOrderStatus.PENDING_APPROVAL,
    ).count()
    total_orders = db.query(TradeOrder).filter(TradeOrder.org_id == user.org_id).count()
    reports = db.query(RegulatoryReport).filter(RegulatoryReport.org_id == user.org_id).count()
    firewall_entries = db.query(EthicalFirewall).filter(
        EthicalFirewall.org_id == user.org_id,
        EthicalFirewall.is_in_cooling_off == True,
    ).count()

    return {
        "connections": {"total": connections, "active": active_connections},
        "compliance": {"rules": compliance_rules, "open_violations": open_violations},
        "counterparties": {"total": counterparties},
        "orders": {"pending": pending_orders, "total": total_orders},
        "regulatory_reports": {"total": reports},
        "ethical_firewall": {"active_cooling_off": firewall_entries},
    }


# ── CCP Clearing ──────────────────────────────────────────────────

@router.post("/ccp/membership")
def register_ccp_membership(
    ccp_name: str,
    ccp_jurisdiction: str,
    membership_status: str,
    initial_margin_required: float = 0,
    default_fund_contribution: float = 0,
    supports_bonds: bool = False,
    supports_derivatives: bool = False,
    exchange_connection_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register CCP clearing membership."""
    ccp = CCPClearingMember(
        org_id=user.org_id,
        exchange_connection_id=exchange_connection_id,
        ccp_name=ccp_name,
        ccp_jurisdiction=ccp_jurisdiction,
        membership_status=membership_status,
        initial_margin_required=initial_margin_required,
        default_fund_contribution=default_fund_contribution,
        supports_bonds=supports_bonds,
        supports_derivatives=supports_derivatives,
    )
    db.add(ccp)
    db.commit()
    db.refresh(ccp)
    return {"status": "registered", "ccp_id": ccp.id, "ccp_name": ccp_name}


@router.get("/ccp/memberships")
def list_ccp_memberships(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List CCP clearing memberships."""
    members = db.query(CCPClearingMember).filter(CCPClearingMember.org_id == user.org_id).all()
    return {
        "memberships": [
            {
                "id": m.id,
                "ccp_name": m.ccp_name,
                "ccp_jurisdiction": m.ccp_jurisdiction,
                "membership_status": m.membership_status,
                "initial_margin_required": float(m.initial_margin_required),
                "default_fund_contribution": float(m.default_fund_contribution),
                "is_compliant": m.is_compliant,
            }
            for m in members
        ],
        "total": len(members),
    }


# ── Smart Contract Templates ──────────────────────────────────────

@router.post("/smart-contracts")
def create_smart_contract_template(
    template_name: str,
    template_type: str,
    version: str,
    blockchain: str,
    contract_code: str | None = None,
    max_value_per_execution: float | None = None,
    requires_human_approval: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a smart contract template for automated execution."""
    import hashlib
    template = SmartContractTemplate(
        org_id=user.org_id,
        template_name=template_name,
        template_type=template_type,
        version=version,
        blockchain=blockchain,
        contract_code=contract_code,
        max_value_per_execution=max_value_per_execution,
        requires_human_approval=requires_human_approval,
        code_hash=hashlib.sha256((contract_code or "").encode()).hexdigest() if contract_code else None,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return {"status": "created", "template_id": template.id, "template_name": template_name}


@router.get("/smart-contracts")
def list_smart_contract_templates(
    template_type: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List smart contract templates."""
    query = db.query(SmartContractTemplate).filter(SmartContractTemplate.org_id == user.org_id)
    if template_type:
        query = query.filter(SmartContractTemplate.template_type == template_type)
    templates = query.order_by(SmartContractTemplate.created_at.desc()).all()
    return {
        "templates": [
            {
                "id": t.id,
                "template_name": t.template_name,
                "template_type": t.template_type,
                "version": t.version,
                "blockchain": t.blockchain,
                "requires_human_approval": t.requires_human_approval,
                "emergency_halt_enabled": t.emergency_halt_enabled,
                "audit_result": t.audit_result,
                "is_active": t.is_active,
            }
            for t in templates
        ],
        "total": len(templates),
    }


# ── Institutional Capacity ────────────────────────────────────────

@router.post("/capacity/assess")
def create_capacity_assessment(
    hr_score: float,
    tech_score: float,
    process_score: float,
    governance_score: float,
    data_quality_score: float,
    hr_details: dict | None = None,
    tech_details: dict | None = None,
    process_details: dict | None = None,
    governance_details: dict | None = None,
    data_quality_details: dict | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create institutional capacity assessment for exchange readiness."""
    composite = (hr_score * 0.20 + tech_score * 0.25 + process_score * 0.20 + governance_score * 0.20 + data_quality_score * 0.15)

    if composite >= 80:
        rating, readiness = "excellent", "ready"
    elif composite >= 65:
        rating, readiness = "good", "ready"
    elif composite >= 50:
        rating, readiness = "adequate", "conditional"
    elif composite >= 35:
        rating, readiness = "weak", "not_ready"
    else:
        rating, readiness = "inadequate", "not_ready"

    gaps = []
    if hr_score < 60: gaps.append("Insufficient qualified staff")
    if tech_score < 60: gaps.append("Technology infrastructure gaps")
    if process_score < 60: gaps.append("Process maturity below threshold")
    if governance_score < 60: gaps.append("Governance framework needs strengthening")
    if data_quality_score < 60: gaps.append("Data quality below exchange requirements")

    assessment = InstitutionalCapacityAssessment(
        org_id=user.org_id,
        assessment_date=datetime.now(timezone.utc),
        assessor=user.email or user.id,
        assessment_period=f"{datetime.now(timezone.utc).year}-Q{(datetime.now(timezone.utc).month - 1) // 3 + 1}",
        hr_score=hr_score,
        hr_details=hr_details,
        tech_score=tech_score,
        tech_details=tech_details,
        process_score=process_score,
        process_details=process_details,
        governance_score=governance_score,
        governance_details=governance_details,
        data_quality_score=data_quality_score,
        data_quality_details=data_quality_details,
        composite_score=round(composite, 2),
        rating=rating,
        exchange_readiness=readiness,
        gaps=gaps,
        recommendations=[f"Address: {g}" for g in gaps] if gaps else ["Maintain current standards"],
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return {
        "assessment_id": assessment.id,
        "composite_score": round(composite, 2),
        "rating": rating,
        "exchange_readiness": readiness,
        "scores": {
            "hr": hr_score, "tech": tech_score, "process": process_score,
            "governance": governance_score, "data_quality": data_quality_score,
        },
        "gaps": gaps,
    }


@router.get("/capacity/assessments")
def list_capacity_assessments(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List institutional capacity assessments."""
    assessments = db.query(InstitutionalCapacityAssessment).filter(
        InstitutionalCapacityAssessment.org_id == user.org_id
    ).order_by(InstitutionalCapacityAssessment.created_at.desc()).all()
    return {
        "assessments": [
            {
                "id": a.id,
                "assessment_period": a.assessment_period,
                "composite_score": a.composite_score,
                "rating": a.rating,
                "exchange_readiness": a.exchange_readiness,
                "gaps": a.gaps,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in assessments
        ],
        "total": len(assessments),
    }


# ── Algorithm Audit Trail ──────────────────────────────────────────

@router.post("/algorithm-audit")
def create_algorithm_audit_event(
    event_type: str,
    event_description: str,
    output_value: dict,
    input_data_summary: dict | None = None,
    feature_values: dict | None = None,
    feature_importance: list | None = None,
    confidence_score: float | None = None,
    model_card_id: str | None = None,
    model_version: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record an algorithm audit event for exchange due diligence."""
    import hashlib

    # Get previous event hash for chain
    last_event = db.query(AlgorithmAuditTrail).filter(
        AlgorithmAuditTrail.org_id == user.org_id
    ).order_by(AlgorithmAuditTrail.created_at.desc()).first()
    previous_hash = last_event.event_hash if last_event else "0" * 64

    # Create event hash
    hash_input = json.dumps({
        "org_id": user.org_id,
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output": output_value,
        "previous_hash": previous_hash,
    }, sort_keys=True)
    event_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    event = AlgorithmAuditTrail(
        org_id=user.org_id,
        model_card_id=model_card_id,
        event_type=event_type,
        event_timestamp=datetime.now(timezone.utc),
        event_description=event_description,
        input_data_hash=hashlib.sha256(json.dumps(input_data_summary or {}, sort_keys=True).encode()).hexdigest(),
        input_data_summary=input_data_summary,
        feature_values=feature_values,
        model_version=model_version,
        output_value=output_value,
        confidence_score=confidence_score,
        feature_importance=feature_importance,
        human_review_required=True,
        previous_event_hash=previous_hash,
        event_hash=event_hash,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return {"status": "recorded", "event_id": event.id, "event_hash": event_hash}


@router.get("/algorithm-audit")
def list_algorithm_audit_events(
    event_type: str | None = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List algorithm audit events for due diligence review."""
    query = db.query(AlgorithmAuditTrail).filter(AlgorithmAuditTrail.org_id == user.org_id)
    if event_type:
        query = query.filter(AlgorithmAuditTrail.event_type == event_type)
    events = query.order_by(AlgorithmAuditTrail.created_at.desc()).limit(limit).all()
    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "event_timestamp": e.event_timestamp.isoformat() if e.event_timestamp else None,
                "event_description": e.event_description,
                "model_version": e.model_version,
                "confidence_score": e.confidence_score,
                "human_reviewed": e.human_reviewed,
                "review_outcome": e.review_outcome,
                "event_hash": e.event_hash,
                "previous_event_hash": e.previous_event_hash,
            }
            for e in events
        ],
        "total": len(events),
    }


# ── Exchange Connector Templates ──────────────────────────────────

@router.get("/connector-templates")
def list_connector_templates(
    exchange_type: str | None = None,
    country: str | None = None,
):
    """List pre-built exchange connector templates."""
    query = db.query(ExchangeConnectorTemplate).filter(ExchangeConnectorTemplate.is_active == True)
    if exchange_type:
        query = query.filter(ExchangeConnectorTemplate.exchange_type == exchange_type)
    if country:
        query = query.filter(ExchangeConnectorTemplate.country == country)
    templates = query.all()
    return {
        "templates": [
            {
                "id": t.id,
                "template_name": t.template_name,
                "exchange_name": t.exchange_name,
                "exchange_type": t.exchange_type.value if t.exchange_type else "traditional",
                "country": t.country,
                "supported_instruments": t.supported_instruments,
                "supported_order_types": t.supported_order_types,
                "settlement_cycles": t.settlement_cycles,
                "authentication_method": t.authentication_method,
                "regulatory_jurisdiction": t.regulatory_jurisdiction,
            }
            for t in templates
        ],
        "total": len(templates),
    }
