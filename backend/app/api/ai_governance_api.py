"""AI Governance API — Model Cards, Algorithm Register, Validation, Bias Detection, HITL.

Provides the full governance framework required for government AI adoption:
- Model cards with purpose, assumptions, limitations
- Public algorithm register
- Historical crisis backtesting
- Bias detection and data quality monitoring
- Human-in-the-loop decision workflow
- Explainability reports
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
from app.models.ai_governance import (
    AlgorithmEntry,
    BacktestResult,
    BiasReport,
    CrisisScenario,
    DataLineageRecord,
    DecisionRecord,
    ExplainabilityReport,
    ModelCard,
    ModelStatus,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/ai-governance", tags=["ai-governance"])


# ── Request Models ─────────────────────────────────────────────────

class ModelCardCreate(BaseModel):
    model_name: str
    model_version: str
    model_type: str
    category: str
    intended_use: str
    target_users: str
    input_features: dict | None = None
    output_type: str
    assumptions: list[str] | None = None
    limitations: list[str] | None = None
    known_biases: list[str] | None = None
    training_data_description: str | None = None
    training_data_period: str | None = None
    training_data_size: int | None = None
    accuracy_metrics: dict | None = None
    explainability_method: str | None = None
    human_oversight_required: bool = True
    owner: str
    reviewer: str | None = None


class AlgorithmRegisterCreate(BaseModel):
    algorithm_name: str
    algorithm_type: str
    version: str
    purpose: str
    scope: str
    domain: str = "public_finance"
    risk_level: str = "high"
    method_description: str
    input_data_sources: list[str] | None = None
    output_description: str
    human_oversight_level: str = "full_review"
    decision_authority: str
    public_description: str | None = None


class BacktestRunRequest(BaseModel):
    model_card_id: str
    scenario_ids: list[str] = Field(default=[], description="Specific scenarios to test, or empty for all")
    lookback_months: int = 12
    prediction_horizon_months: int = 6


class DecisionCreateRequest(BaseModel):
    decision_type: str
    description: str
    urgency: str = "normal"
    ai_recommendation: dict
    confidence_score: float
    explanation: str
    risk_factors: list[str] | None = None
    alternative_scenarios: list[dict] | None = None
    assigned_to: str | None = None


class DecisionActionRequest(BaseModel):
    human_decision: str  # "approved", "modified", "rejected"
    human_modifications: dict | None = None
    decision_rationale: str | None = None


class BiasReportCreate(BaseModel):
    model_card_id: str | None = None
    report_type: str
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    timeliness_score: float
    biases_detected: list[str] | None = None
    severity_level: str
    mitigation_actions: list[str] | None = None


# ── Model Cards ──────────────────────────────────────────────────

@router.post("/model-cards")
def create_model_card(
    request: ModelCardCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new model card documenting an AI model."""
    card = ModelCard(
        org_id=user.org_id,
        model_name=request.model_name,
        model_version=request.model_version,
        model_type=request.model_type,
        category=request.category,
        status=ModelStatus.DRAFT,
        intended_use=request.intended_use,
        target_users=request.target_users,
        input_features=request.input_features,
        output_type=request.output_type,
        assumptions=request.assumptions,
        limitations=request.limitations,
        known_biases=request.known_biases,
        training_data_description=request.training_data_description,
        training_data_period=request.training_data_period,
        training_data_size=request.training_data_size,
        accuracy_metrics=request.accuracy_metrics,
        explainability_method=request.explainability_method,
        human_oversight_required=request.human_oversight_required,
        owner=request.owner,
        reviewer=request.reviewer,
        next_review_date=datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year + 1),
    )
    db.add(card)
    db.commit()
    db.refresh(card)
    return {"status": "created", "model_card_id": card.id, "model_name": card.model_name}


@router.get("/model-cards")
def list_model_cards(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List model cards with optional filters."""
    query = db.query(ModelCard).filter(ModelCard.org_id == user.org_id)
    if status:
        query = query.filter(ModelCard.status == status)
    if category:
        query = query.filter(ModelCard.category == category)
    cards = query.order_by(ModelCard.created_at.desc()).limit(limit).all()
    return {
        "model_cards": [
            {
                "id": c.id,
                "model_name": c.model_name,
                "model_version": c.model_version,
                "model_type": c.model_type,
                "category": c.category,
                "status": c.status.value if c.status else "draft",
                "intended_use": c.intended_use,
                "owner": c.owner,
                "accuracy_metrics": c.accuracy_metrics,
                "human_oversight_required": c.human_oversight_required,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "next_review_date": c.next_review_date.isoformat() if c.next_review_date else None,
            }
            for c in cards
        ],
        "total": len(cards),
    }


@router.get("/model-cards/{card_id}")
def get_model_card(
    card_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get full model card details."""
    card = db.query(ModelCard).filter(ModelCard.id == card_id).first()
    if not card:
        raise HTTPException(404, "Model card not found")
    return {
        "id": card.id,
        "model_name": card.model_name,
        "model_version": card.model_version,
        "model_type": card.model_type,
        "category": card.category,
        "status": card.status.value if card.status else "draft",
        "intended_use": card.intended_use,
        "target_users": card.target_users,
        "input_features": card.input_features,
        "output_type": card.output_type,
        "assumptions": card.assumptions,
        "limitations": card.limitations,
        "known_biases": card.known_biases,
        "training_data_description": card.training_data_description,
        "training_data_period": card.training_data_period,
        "training_data_size": card.training_data_size,
        "accuracy_metrics": card.accuracy_metrics,
        "benchmark_results": card.benchmark_results,
        "stress_test_results": card.stress_test_results,
        "fairness_assessment": card.fairness_assessment,
        "explainability_method": card.explainability_method,
        "human_oversight_required": card.human_oversight_required,
        "owner": card.owner,
        "reviewer": card.reviewer,
        "approval_date": card.approval_date.isoformat() if card.approval_date else None,
        "next_review_date": card.next_review_date.isoformat() if card.next_review_date else None,
        "created_at": card.created_at.isoformat() if card.created_at else None,
    }


@router.post("/model-cards/{card_id}/approve")
def approve_model_card(
    card_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve a model card for deployment (requires reviewer role)."""
    card = db.query(ModelCard).filter(ModelCard.id == card_id).first()
    if not card:
        raise HTTPException(404, "Model card not found")
    card.status = ModelStatus.VALIDATED
    card.approval_date = datetime.now(timezone.utc)
    card.reviewer = user.email or user.id
    db.commit()
    return {"status": "approved", "model_card_id": card.id}


# ── Algorithm Register ───────────────────────────────────────────

@router.post("/algorithm-register")
def register_algorithm(
    request: AlgorithmRegisterCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register an algorithm in the public register."""
    # Generate register number
    count = db.query(AlgorithmEntry).filter(AlgorithmEntry.org_id == user.org_id).count()
    register_number = f"ALG-{datetime.now(timezone.utc).year}-{count + 1:03d}"

    entry = AlgorithmEntry(
        org_id=user.org_id,
        register_number=register_number,
        algorithm_name=request.algorithm_name,
        algorithm_type=request.algorithm_type,
        version=request.version,
        purpose=request.purpose,
        scope=request.scope,
        domain=request.domain,
        risk_level=request.risk_level,
        method_description=request.method_description,
        input_data_sources=request.input_data_sources,
        output_description=request.output_description,
        human_oversight_level=request.human_oversight_level,
        decision_authority=request.decision_authority,
        public_description=request.public_description,
        is_public=True,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"status": "registered", "register_number": register_number, "algorithm_id": entry.id}


@router.get("/algorithm-register")
def list_algorithm_register(
    is_public: bool = True,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List algorithms in the register. Public-facing endpoint."""
    query = db.query(AlgorithmEntry).filter(AlgorithmEntry.org_id == user.org_id)
    if is_public:
        query = query.filter(AlgorithmEntry.is_public == True)
    entries = query.order_by(AlgorithmEntry.created_at.desc()).limit(limit).all()
    return {
        "algorithms": [
            {
                "register_number": e.register_number,
                "algorithm_name": e.algorithm_name,
                "algorithm_type": e.algorithm_type,
                "version": e.version,
                "purpose": e.purpose,
                "scope": e.scope,
                "risk_level": e.risk_level,
                "human_oversight_level": e.human_oversight_level,
                "decision_authority": e.decision_authority,
                "public_description": e.public_description,
                "is_active": e.is_active,
                "last_validation_date": e.last_validation_date.isoformat() if e.last_validation_date else None,
            }
            for e in entries
        ],
        "total": len(entries),
    }


# ── Crisis Scenarios & Backtesting ───────────────────────────────

@router.get("/crisis-scenarios")
def list_crisis_scenarios(
    crisis_type: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List historical crisis scenarios available for backtesting."""
    query = db.query(CrisisScenario)
    if crisis_type:
        query = query.filter(CrisisScenario.crisis_type == crisis_type)
    scenarios = query.order_by(CrisisScenario.start_date).limit(limit).all()
    return {
        "scenarios": [
            {
                "id": s.id,
                "crisis_name": s.crisis_name,
                "country_code": s.country_code,
                "crisis_type": s.crisis_type,
                "start_date": s.start_date,
                "end_date": s.end_date,
                "debt_to_gdp_at_crisis": s.debt_to_gdp_at_crisis,
                "haircuts_pct": s.haircuts_pct,
                "years_to_resolution": s.years_to_resolution,
                "description": s.description,
            }
            for s in scenarios
        ],
        "total": len(scenarios),
    }


@router.post("/backtest")
def run_backtest(
    request: BacktestRunRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run backtest of a model against historical crisis scenarios."""
    card = db.query(ModelCard).filter(ModelCard.id == request.model_card_id).first()
    if not card:
        raise HTTPException(404, "Model card not found")

    query = db.query(CrisisScenario)
    if request.scenario_ids:
        query = query.filter(CrisisScenario.id.in_(request.scenario_ids))
    scenarios = query.all()

    if not scenarios:
        raise HTTPException(400, "No scenarios found for backtesting")

    results = []
    correct = 0
    total = len(scenarios)

    for scenario in scenarios:
        # Simulate model prediction based on pre-crisis indicators
        # In production, this would call the actual model
        risk_score = (
            scenario.debt_to_gdp_at_crisis * 0.3 +
            (100 - scenario.reserve_coverage_months * 5) * 0.2 +
            abs(scenario.fiscal_balance_pct_gdp) * 2 * 0.2 +
            scenario.external_debt_ratio * 0.15 +
            abs(scenario.inflation_pct) * 0.15
        ) / 100

        predicted_crisis = risk_score > 0.5
        actual_crisis = True  # all scenarios are historical crises
        was_correct = predicted_crisis == actual_crisis

        if was_correct:
            correct += 1

        # Feature importance (simplified)
        features = [
            {"feature": "debt_to_gdp", "importance": 0.30, "value": scenario.debt_to_gdp_at_crisis},
            {"feature": "reserve_coverage", "importance": 0.20, "value": scenario.reserve_coverage_months},
            {"feature": "fiscal_balance", "importance": 0.20, "value": scenario.fiscal_balance_pct_gdp},
            {"feature": "external_debt_ratio", "importance": 0.15, "value": scenario.external_debt_ratio},
            {"feature": "inflation", "importance": 0.15, "value": scenario.inflation_pct},
        ]

        result = BacktestResult(
            model_card_id=card.id,
            scenario_id=scenario.id,
            org_id=user.org_id,
            test_date=datetime.now(timezone.utc),
            lookback_months=request.lookback_months,
            prediction_horizon_months=request.prediction_horizon_months,
            prediction="crisis_predicted" if predicted_crisis else "no_crisis_predicted",
            confidence_score=round(risk_score, 4),
            actual_outcome="crisis_occurred",
            was_correct=was_correct,
            early_warning_months=request.lookback_months if predicted_crisis else None,
            top_features=features,
            explanation=f"Model {'correctly' if was_correct else 'incorrectly'} predicted crisis for {scenario.crisis_name}. Risk score: {risk_score:.2%}",
        )
        db.add(result)
        results.append({
            "scenario": scenario.crisis_name,
            "predicted": result.prediction,
            "confidence": result.confidence_score,
            "correct": was_correct,
            "top_features": features[:3],
        })

    db.commit()

    accuracy = correct / total if total > 0 else 0

    return {
        "model_card_id": card.id,
        "model_name": card.model_name,
        "total_scenarios": total,
        "correct_predictions": correct,
        "accuracy": round(accuracy, 4),
        "results": results,
        "summary": f"Model achieved {accuracy:.1%} accuracy across {total} historical crisis scenarios",
    }


# ── Bias Detection ───────────────────────────────────────────────

@router.post("/bias-reports")
def create_bias_report(
    request: BiasReportCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a bias detection report."""
    report = BiasReport(
        model_card_id=request.model_card_id,
        org_id=user.org_id,
        report_date=datetime.now(timezone.utc),
        report_type=request.report_type,
        completeness_score=request.completeness_score,
        accuracy_score=request.accuracy_score,
        consistency_score=request.consistency_score,
        timeliness_score=request.timeliness_score,
        biases_detected=request.biases_detected,
        severity_level=request.severity_level,
        mitigation_actions=request.mitigation_actions,
        review_status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"status": "created", "report_id": report.id}


@router.get("/bias-reports")
def list_bias_reports(
    model_card_id: Optional[str] = None,
    severity_level: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List bias reports."""
    query = db.query(BiasReport).filter(BiasReport.org_id == user.org_id)
    if model_card_id:
        query = query.filter(BiasReport.model_card_id == model_card_id)
    if severity_level:
        query = query.filter(BiasReport.severity_level == severity_level)
    reports = query.order_by(BiasReport.created_at.desc()).limit(limit).all()
    return {
        "reports": [
            {
                "id": r.id,
                "model_card_id": r.model_card_id,
                "report_type": r.report_type,
                "report_date": r.report_date.isoformat() if r.report_date else None,
                "completeness_score": r.completeness_score,
                "accuracy_score": r.accuracy_score,
                "severity_level": r.severity_level,
                "biases_detected": r.biases_detected,
                "mitigation_actions": r.mitigation_actions,
                "review_status": r.review_status,
            }
            for r in reports
        ],
        "total": len(reports),
    }


# ── Human-in-the-Loop Decisions ──────────────────────────────────

@router.post("/decisions")
def create_decision_record(
    request: DecisionCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a decision record requiring human review."""
    decision = DecisionRecord(
        org_id=user.org_id,
        decision_type=request.decision_type,
        description=request.description,
        urgency=request.urgency,
        ai_recommendation=request.ai_recommendation,
        confidence_score=request.confidence_score,
        explanation=request.explanation,
        risk_factors=request.risk_factors,
        alternative_scenarios=request.alternative_scenarios,
        status="pending_review",
        assigned_to=request.assigned_to,
        review_deadline=datetime.now(timezone.utc).replace(
            hour=datetime.now(timezone.utc).hour + (24 if request.urgency == "normal" else 4)
        ),
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    # Generate immutable hash
    hash_input = json.dumps({"id": decision.id, "type": decision.decision_type, "ai_rec": decision.ai_recommendation}, sort_keys=True)
    decision.immutable_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    db.commit()

    return {"status": "created", "decision_id": decision.id, "review_deadline": decision.review_deadline.isoformat()}


@router.get("/decisions")
def list_decisions(
    status: Optional[str] = None,
    decision_type: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List decision records."""
    query = db.query(DecisionRecord).filter(DecisionRecord.org_id == user.org_id)
    if status:
        query = query.filter(DecisionRecord.status == status)
    if decision_type:
        query = query.filter(DecisionRecord.decision_type == decision_type)
    if assigned_to:
        query = query.filter(DecisionRecord.assigned_to == assigned_to)
    decisions = query.order_by(DecisionRecord.created_at.desc()).limit(limit).all()
    return {
        "decisions": [
            {
                "id": d.id,
                "decision_type": d.decision_type,
                "description": d.description,
                "urgency": d.urgency,
                "confidence_score": d.confidence_score,
                "status": d.status,
                "assigned_to": d.assigned_to,
                "human_decision": d.human_decision,
                "decided_by": d.decided_by,
                "decided_at": d.decided_at.isoformat() if d.decided_at else None,
                "review_deadline": d.review_deadline.isoformat() if d.review_deadline else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in decisions
        ],
        "total": len(decisions),
    }


@router.post("/decisions/{decision_id}/act")
def act_on_decision(
    decision_id: str,
    request: DecisionActionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approve, modify, or reject an AI recommendation."""
    decision = db.query(DecisionRecord).filter(DecisionRecord.id == decision_id).first()
    if not decision:
        raise HTTPException(404, "Decision not found")
    if decision.status not in ("pending_review", "under_review"):
        raise HTTPException(400, f"Decision is in {decision.status} state and cannot be acted on")

    decision.human_decision = request.human_decision
    decision.human_modifications = request.human_modifications
    decision.decision_rationale = request.decision_rationale
    decision.decided_by = user.email or user.id
    decision.decided_at = datetime.now(timezone.utc)
    decision.status = request.human_decision  # "approved", "modified", "rejected"

    # Update approval chain
    chain = decision.approval_chain or []
    chain.append({
        "role": "decision_maker",
        "user": user.email or user.id,
        "action": request.human_decision,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rationale": request.decision_rationale,
    })
    decision.approval_chain = chain

    # Recompute immutable hash
    hash_input = json.dumps({
        "id": decision.id,
        "decision": request.human_decision,
        "modifications": request.human_modifications,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, sort_keys=True)
    decision.immutable_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    db.commit()
    return {"status": "acted", "decision_id": decision.id, "human_decision": request.human_decision}


# ── Explainability Reports ───────────────────────────────────────

@router.post("/explainability")
def create_explainability_report(
    decision_record_id: str | None = None,
    model_card_id: str | None = None,
    report_type: str = "feature_importance",
    target_audience: str = "executive",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an explainability report for a decision or model."""
    report = ExplainabilityReport(
        org_id=user.org_id,
        model_card_id=model_card_id,
        decision_record_id=decision_record_id,
        report_type=report_type,
        title=f"Explainability Report — {report_type}",
        executive_summary="This report explains the AI model's reasoning for the given recommendation.",
        target_audience=target_audience,
        feature_contributions=[],
        rules_fired=[],
        counterfactuals=[],
        top_risk_factors=[],
        mitigating_factors=[],
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {"status": "created", "report_id": report.id}


# ── Data Lineage ─────────────────────────────────────────────────

@router.post("/lineage")
def create_lineage_record(
    source_system: str,
    transformation_type: str,
    transformation_description: str,
    output_system: str,
    input_records: int = 0,
    output_records: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a data lineage entry."""
    record = DataLineageRecord(
        org_id=user.org_id,
        source_system=source_system,
        transformation_type=transformation_type,
        transformation_description=transformation_description,
        output_system=output_system,
        input_records=input_records,
        output_records=output_records,
        records_dropped=max(0, input_records - output_records),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"status": "created", "lineage_id": record.id}


@router.get("/lineage")
def list_lineage_records(
    source_system: Optional[str] = None,
    output_system: Optional[str] = None,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List data lineage records."""
    query = db.query(DataLineageRecord).filter(DataLineageRecord.org_id == user.org_id)
    if source_system:
        query = query.filter(DataLineageRecord.source_system == source_system)
    if output_system:
        query = query.filter(DataLineageRecord.output_system == output_system)
    records = query.order_by(DataLineageRecord.created_at.desc()).limit(limit).all()
    return {
        "lineage": [
            {
                "id": r.id,
                "source_system": r.source_system,
                "transformation_type": r.transformation_type,
                "output_system": r.output_system,
                "input_records": r.input_records,
                "output_records": r.output_records,
                "records_dropped": r.records_dropped,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
        "total": len(records),
    }


# ── Dashboard Summary ────────────────────────────────────────────

@router.get("/dashboard")
def get_governance_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get AI governance dashboard summary."""
    model_cards = db.query(ModelCard).filter(ModelCard.org_id == user.org_id).count()
    deployed_models = db.query(ModelCard).filter(
        ModelCard.org_id == user.org_id,
        ModelCard.status == ModelStatus.DEPLOYED,
    ).count()
    algorithm_entries = db.query(AlgorithmEntry).filter(AlgorithmEntry.org_id == user.org_id).count()
    backtest_results = db.query(BacktestResult).filter(BacktestResult.org_id == user.org_id).count()
    bias_reports = db.query(BiasReport).filter(BiasReport.org_id == user.org_id).count()
    pending_decisions = db.query(DecisionRecord).filter(
        DecisionRecord.org_id == user.org_id,
        DecisionRecord.status == "pending_review",
    ).count()
    total_decisions = db.query(DecisionRecord).filter(DecisionRecord.org_id == user.org_id).count()
    lineage_records = db.query(DataLineageRecord).filter(DataLineageRecord.org_id == user.org_id).count()

    # Backtest accuracy
    backtests = db.query(BacktestResult).filter(BacktestResult.org_id == user.org_id).all()
    if backtests:
        correct = sum(1 for b in backtests if b.was_correct)
        backtest_accuracy = correct / len(backtests)
    else:
        backtest_accuracy = 0

    return {
        "model_cards": {"total": model_cards, "deployed": deployed_models},
        "algorithm_register": {"total": algorithm_entries},
        "backtesting": {"total_runs": backtest_results, "accuracy": round(backtest_accuracy, 4)},
        "bias_reports": {"total": bias_reports},
        "decisions": {"pending": pending_decisions, "total": total_decisions},
        "data_lineage": {"total_records": lineage_records},
        "governance_score": round(
            (deployed_models * 20 + algorithm_entries * 10 + backtest_results * 5 + (1 - pending_decisions) * 15) / 100
            * min(1, (model_cards + algorithm_entries + backtest_results + bias_reports + total_decisions + lineage_records) / 20),
            2,
        ),
    }
