"""API endpoints for government entity management, fiscal rules, and enhanced optimization."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    DebtInstrument,
    OptimizationJob,
    Organization,
    Portfolio,
    User,
    UserRole,
)
from app.models.government import (
    AssumptionCategory,
    CLType,
    ContingentLiability,
    EntityType,
    FiscalRule,
    FiscalRuleEvaluation,
    GovernmentEntity,
    RuleType,
    TransferLink,
    TransferType,
    VersionedAssumption,
)
from app.models.institutional_memory import (
    compute_audit_hash,
    migrate_knowledge_to_database,
    get_cross_administration_knowledge,
    get_policy_rationale,
    register_assumption,
    transition_administration,
)
from app.optimization.enhanced_optimizer import (
    DebtInstrumentInput,
    DebtOptimizer,
)
from app.optimization.exporters import CSVExporter, DSAExporter, MTDSExporter
from app.optimization.fiscal_rules import (
    ComplianceReport,
    ConsolidatedViewEngine,
    FiscalRuleEngine,
    RuleInput,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/government", tags=["government"])

optimizer = DebtOptimizer()
fiscal_engine = FiscalRuleEngine()
consolidated_engine = ConsolidatedViewEngine()
mtds_exporter = MTDSExporter()
dsa_exporter = DSAExporter()
csv_exporter = CSVExporter()


# ── Entity Hierarchy ────────────────────────────────────────────────

@router.get("/entities")
def list_entities(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entities = db.query(GovernmentEntity).filter(
        GovernmentEntity.org_id == user.org_id
    ).all()
    return [_entity_to_dict(e) for e in entities]


@router.post("/entities")
def create_entity(
    name: str,
    entity_type: EntityType,
    parent_id: str | None = None,
    gdp_local: float | None = None,
    population: int | None = None,
    currency: str = "USD",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entity = GovernmentEntity(
        org_id=user.org_id,
        parent_id=parent_id,
        name=name,
        entity_type=entity_type,
        gdp_local=gdp_local,
        population=population,
        currency=currency,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return _entity_to_dict(entity)


@router.get("/entities/{entity_id}")
def get_entity(
    entity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entity = db.query(GovernmentEntity).filter(
        GovernmentEntity.id == entity_id,
        GovernmentEntity.org_id == user.org_id,
    ).first()
    if not entity:
        raise HTTPException(404, "Entity not found")
    return _entity_to_dict(entity)


@router.get("/entities/{entity_id}/drilldown")
def entity_drilldown(
    entity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Drill down into an entity: instruments, CLs, transfers, rules."""
    entity = db.query(GovernmentEntity).filter(
        GovernmentEntity.id == entity_id,
        GovernmentEntity.org_id == user.org_id,
    ).first()
    if not entity:
        raise HTTPException(404, "Entity not found")

    # Get portfolios linked to this entity
    entity_portfolios = db.query(EntityPortfolio).filter(
        EntityPortfolio.entity_id == entity_id
    ).all()

    instruments = []
    for ep in entity_portfolios:
        portfolio = db.query(Portfolio).filter(Portfolio.id == ep.portfolio_id).first()
        if portfolio:
            insts = db.query(DebtInstrument).filter(
                DebtInstrument.portfolio_id == portfolio.id
            ).all()
            instruments.extend([_instrument_to_dict(i) for i in insts])

    cls = db.query(ContingentLiability).filter(
        ContingentLiability.entity_id == entity_id
    ).all()

    transfers = db.query(TransferLink).filter(
        TransferLink.entity_id == entity_id
    ).all()

    rules = db.query(FiscalRule).filter(
        FiscalRule.entity_id == entity_id
    ).all()

    children = db.query(GovernmentEntity).filter(
        GovernmentEntity.parent_id == entity_id
    ).all()

    return {
        "entity": _entity_to_dict(entity),
        "instruments": instruments,
        "contingent_liabilities": [_cl_to_dict(cl) for cl in cls],
        "transfers": [_transfer_to_dict(t) for t in transfers],
        "fiscal_rules": [_rule_to_dict(r) for r in rules],
        "children": [_entity_to_dict(c) for c in children],
        "children_count": len(children),
    }


# ── Consolidated View ───────────────────────────────────────────────

@router.get("/consolidated")
def consolidated_view(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Build consolidated public-sector debt view with rollup."""
    entities = db.query(GovernmentEntity).filter(
        GovernmentEntity.org_id == user.org_id
    ).all()

    instruments_by_entity = {}
    cls_by_entity = {}
    transfers_by_entity = {}

    for ent in entities:
        # Instruments
        entity_portfolios = db.query(EntityPortfolio).filter(
            EntityPortfolio.entity_id == ent.id
        ).all()
        insts = []
        for ep in entity_portfolios:
            portfolio = db.query(Portfolio).filter(Portfolio.id == ep.portfolio_id).first()
            if portfolio:
                db_insts = db.query(DebtInstrument).filter(
                    DebtInstrument.portfolio_id == portfolio.id
                ).all()
                insts.extend([_instrument_to_dict(i) for i in db_insts])
        instruments_by_entity[ent.id] = insts

        # CLs
        cls = db.query(ContingentLiability).filter(
            ContingentLiability.entity_id == ent.id
        ).all()
        cls_by_entity[ent.id] = [_cl_to_dict(cl) for cl in cls]

        # Transfers
        transfers = db.query(TransferLink).filter(
            TransferLink.entity_id == ent.id
        ).all()
        transfers_by_entity[ent.id] = [_transfer_to_dict(t) for t in transfers]

    entity_dicts = [_entity_to_dict(e) for e in entities]
    tree = consolidated_engine.build_consolidated_tree(
        entity_dicts, instruments_by_entity, cls_by_entity, transfers_by_entity
    )
    rollups = [consolidated_engine.compute_rollup(s) for s in tree]

    return {
        "tree": [_summary_to_dict(s) for s in tree],
        "rollups": rollups,
        "total_public_sector_debt": sum(r["total_public_sector_debt"] for r in rollups),
        "total_contingent_liabilities": sum(r["contingent_liability_exposure"] for r in rollups),
        "entities_count": len(entities),
    }


# ── Fiscal Rules ────────────────────────────────────────────────────

@router.get("/entities/{entity_id}/fiscal-rules")
def list_fiscal_rules(
    entity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rules = db.query(FiscalRule).filter(FiscalRule.entity_id == entity_id).all()
    return [_rule_to_dict(r) for r in rules]


@router.post("/entities/{entity_id}/fiscal-rules")
def create_fiscal_rule(
    entity_id: str,
    name: str,
    rule_type: RuleType,
    threshold_value: float,
    threshold_unit: str,
    is_hard_limit: bool = True,
    statute_reference: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rule = FiscalRule(
        entity_id=entity_id,
        name=name,
        rule_type=rule_type,
        threshold_value=threshold_value,
        threshold_unit=threshold_unit,
        is_hard_limit=is_hard_limit,
        statute_reference=statute_reference,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_to_dict(rule)


@router.post("/entities/{entity_id}/evaluate-rules")
def evaluate_fiscal_rules(
    entity_id: str,
    entity_data: RuleInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Evaluate all fiscal rules for an entity against provided data."""
    rules = db.query(FiscalRule).filter(FiscalRule.entity_id == entity_id).all()
    rule_dicts = [_rule_to_dict(r) for r in rules]

    report = fiscal_engine.evaluate(rule_dicts, entity_data)

    # Persist evaluations
    for rule_result in report.rules:
        evaluation = FiscalRuleEvaluation(
            rule_id=rule_result.rule_id,
            current_value=rule_result.current_value,
            threshold_value=rule_result.threshold_value,
            headroom=rule_result.headroom,
            headroom_pct=rule_result.headroom_pct,
            severity=rule_result.severity,
            evaluation_context={"entity_data": entity_data.__dict__ if hasattr(entity_data, '__dict__') else {}},
        )
        db.add(evaluation)
    db.commit()

    return {
        "entity_id": report.entity_id,
        "entity_name": report.entity_name,
        "evaluated_at": report.evaluated_at,
        "overall_severity": report.overall_severity,
        "total_rules": report.total_rules,
        "passing": report.passing,
        "warnings": report.warnings,
        "breaches": report.breaches,
        "rules": [
            {
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "rule_type": r.rule_type,
                "current_value": r.current_value,
                "threshold_value": r.threshold_value,
                "headroom": r.headroom,
                "headroom_pct": r.headroom_pct,
                "severity": r.severity,
                "message": r.message,
                "is_hard_limit": r.is_hard_limit,
            }
            for r in report.rules
        ],
    }


# ── Contingent Liabilities ──────────────────────────────────────────

@router.get("/entities/{entity_id}/contingent-liabilities")
def list_contingent_liabilities(
    entity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cls = db.query(ContingentLiability).filter(
        ContingentLiability.entity_id == entity_id
    ).all()
    return [_cl_to_dict(cl) for cl in cls]


@router.post("/entities/{entity_id}/contingent-liabilities")
def create_contingent_liability(
    entity_id: str,
    name: str,
    cl_type: CLType,
    exposure_amount: float,
    probability_of_call: float = 0.0,
    counterparty: str | None = None,
    is_national_guarantee: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    expected_loss = exposure_amount * probability_of_call
    cl = ContingentLiability(
        entity_id=entity_id,
        name=name,
        cl_type=cl_type,
        exposure_amount=exposure_amount,
        probability_of_call=probability_of_call,
        expected_loss=expected_loss,
        counterparty=counterparty,
        is_national_guarantee=is_national_guarantee,
    )
    db.add(cl)
    db.commit()
    db.refresh(cl)
    return _cl_to_dict(cl)


# ── Transfers ───────────────────────────────────────────────────────

@router.get("/entities/{entity_id}/transfers")
def list_transfers(
    entity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transfers = db.query(TransferLink).filter(
        TransferLink.entity_id == entity_id
    ).all()
    return [_transfer_to_dict(t) for t in transfers]


@router.post("/entities/{entity_id}/transfers")
def create_transfer(
    entity_id: str,
    source_entity_id: str,
    transfer_type: TransferType,
    annual_amount: float,
    covers_debt_service_pct: float = 0.0,
    is_statutory: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transfer = TransferLink(
        entity_id=entity_id,
        source_entity_id=source_entity_id,
        transfer_type=transfer_type,
        annual_amount=annual_amount,
        covers_debt_service_pct=covers_debt_service_pct,
        is_statutory=is_statutory,
    )
    db.add(transfer)
    db.commit()
    db.refresh(transfer)
    return _transfer_to_dict(transfer)


# ── Versioned Assumptions ──────────────────────────────────────────

@router.get("/entities/{entity_id}/assumptions")
def list_assumptions(
    entity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assumptions = db.query(VersionedAssumption).filter(
        VersionedAssumption.entity_id == entity_id
    ).order_by(VersionedAssumption.version.desc()).all()
    return [_assumption_to_dict(a) for a in assumptions]


@router.post("/entities/{entity_id}/assumptions")
def create_assumption(
    entity_id: str,
    name: str,
    category: AssumptionCategory,
    value: float,
    unit: str,
    source: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assumption = VersionedAssumption(
        entity_id=entity_id,
        name=name,
        category=category,
        value=value,
        unit=unit,
        source=source,
        version=1,
        is_current=True,
        changed_by=user.id,
    )
    db.add(assumption)
    db.commit()
    db.refresh(assumption)
    return _assumption_to_dict(assumption)


@router.put("/assumptions/{assumption_id}")
def update_assumption(
    assumption_id: str,
    new_value: float,
    change_reason: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Version an assumption: mark old as not current, create new version."""
    old = db.query(VersionedAssumption).filter(
        VersionedAssumption.id == assumption_id
    ).first()
    if not old:
        raise HTTPException(404, "Assumption not found")

    old.is_current = False
    new_version = old.version + 1

    new_assumption = VersionedAssumption(
        entity_id=old.entity_id,
        name=old.name,
        category=old.category,
        value=new_value,
        unit=old.unit,
        source=old.source,
        version=new_version,
        is_current=True,
        changed_by=user.id,
        change_reason=change_reason,
        previous_value=old.value,
    )
    db.add(new_assumption)
    db.commit()
    db.refresh(new_assumption)
    return _assumption_to_dict(new_assumption)


# ── Administrative Transition Tracking ──────────────────────────────
@router.post("/entities/{entity_id}/transition")
def trigger_administrative_transition(
    entity_id: str,
    new_administration: str,
    new_minister: str,
    trigger: str = "handover",
    departing_minister: str | None = None,
    assumptions_to_review: list[str] | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger administrative transition tracking.

    When admins change, automatically generates risks, active initiatives,
    unresolved issues, and upcoming deadlines based on previous assumptions.
    """
    result = transition_administration(
        entity_id=entity_id,
        new_administration=new_administration,
        new_minister=new_minister,
        trigger=trigger,
        departing_minister=departing_minister,
        assumptions_to_review=assumptions_to_review,
        metadata={"changed_by": user.id},
    )
    return {
        "entity_id": entity_id,
        "new_administration": new_administration,
        "new_minister": new_minister,
        "trigger": trigger,
        "transition_records_created": len(result),
        "message": "Administrative transition tracking activated. Risks, initiatives, and deadlines auto-generated.",
    }


@router.get("/entities/{entity_id}/policy-rationale")
def policy_rationale(
    entity_id: str,
    assumption_name: str | None = None,
    category: AssumptionCategory | None = None,
    include_history: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Query: 'Why was this policy chosen?' with full audit trail.

    Returns complete historical context for a policy decision including:
    - All assumption versions and their values over time
    - Administrative context at each change
    - Associated risks and initiatives
    - Unresolved issues carried forward
    - Upcoming deadlines tied to the assumption
    - Audit hashes for immutability verification
    """
    rationale = get_policy_rationale(
        entity_id=entity_id,
        assumption_name=assumption_name,
        category=category,
        include_history=include_history,
    )
    return {"entity_id": entity_id, "rationale": rationale}


@router.get("/entities/{entity_id}/cross-administration-knowledge")
def cross_administration_knowledge(
    entity_id: str,
    include_archived: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve knowledge persisted across administrations.

    Returns all knowledge entries for this entity across all administrations,
    enabling new administrators to understand historical context without
    reinventing the wheel.
    """
    knowledge = get_cross_administration_knowledge(
        entity_id=entity_id,
        include_archived=include_archived,
    )
    return {"entity_id": entity_id, "knowledge": knowledge}


@router.post("/entities/{entity_id}/knowledge-migrate")
def migrate_knowledge(
    entity_id: str,
    from_administration: str,
    to_administration: str,
    assumptions_to_migrate: list[str] | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Migrate knowledge from one administration to another.

    Ensures cross-administration access by marking assumptions as
    migrated and creating new entries in the current administration.
    """
    result = migrate_knowledge_to_database(
        entity_id=entity_id,
        from_administration=from_administration,
        to_administration=to_administration,
        assumptions_to_migrate=assumptions_to_migrate,
    )
    return {
        "entity_id": entity_id,
        "from_administration": from_administration,
        "to_administration": to_administration,
        "migrated_count": result["migrated_count"],
        "message": "Knowledge migration complete. Cross-administration access restored.",
    }


# ── Enhanced Optimizer ──────────────────────────────────────────────

@router.post("/optimize")
def run_optimization(
    portfolio_id: str,
    objective: str = "minimize_cost",
    max_concentration: float = 0.40,
    max_fx_exposure: float = 0.30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run enhanced debt optimization on a portfolio."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.org_id == user.org_id,
    ).first()
    if not portfolio:
        raise HTTPException(404, "Portfolio not found")

    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id == portfolio_id
    ).all()

    if not instruments:
        raise HTTPException(400, "No instruments in portfolio")

    debt_instruments = [
        DebtInstrumentInput(
            id=i.id,
            name=i.name,
            principal_outstanding=float(i.principal_outstanding),
            coupon_rate=float(i.coupon_rate),
            maturity_date=i.maturity_date,
            instrument_type=i.instrument_type.value if hasattr(i.instrument_type, 'value') else str(i.instrument_type),
            currency=i.currency,
            spread_bps=float(i.spread_bps or 0),
        )
        for i in instruments
    ]

    result = optimizer.optimize(
        debt_instruments,
        constraints={
            "max_concentration": max_concentration,
            "max_fx_exposure": max_fx_exposure,
        },
    )

    return {
        "portfolio_id": portfolio_id,
        "objective": objective,
        "allocations": result.allocations,
        "metrics": result.metrics,
        "feasible": result.feasible,
        "solver": result.solver,
        "iterations": result.iterations,
    }


@router.post("/pareto")
def pareto_frontier(
    portfolio_id: str,
    num_points: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate Pareto frontier for cost vs risk trade-off."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.org_id == user.org_id,
    ).first()
    if not portfolio:
        raise HTTPException(404, "Portfolio not found")

    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id == portfolio_id
    ).all()

    debt_instruments = [
        DebtInstrumentInput(
            id=i.id, name=i.name,
            principal_outstanding=float(i.principal_outstanding),
            coupon_rate=float(i.coupon_rate),
            maturity_date=i.maturity_date,
            instrument_type=str(i.instrument_type.value if hasattr(i.instrument_type, 'value') else i.instrument_type),
            currency=i.currency,
            spread_bps=float(i.spread_bps or 0),
        )
        for i in instruments
    ]

    frontier = optimizer.generate_pareto_frontier(debt_instruments, num_points=min(num_points, 50))

    return {
        "portfolio_id": portfolio_id,
        "frontier_points": len(frontier),
        "frontier": frontier,
    }


@router.post("/compare")
def compare_strategies(
    portfolio_id: str,
    strategy_a: dict,
    strategy_b: dict,
    scenarios: list[dict] | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Side-by-side comparison of two strategies."""
    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id == portfolio_id
    ).all()

    debt_instruments = [
        DebtInstrumentInput(
            id=i.id, name=i.name,
            principal_outstanding=float(i.principal_outstanding),
            coupon_rate=float(i.coupon_rate),
            maturity_date=i.maturity_date,
            instrument_type=str(i.instrument_type.value if hasattr(i.instrument_type, 'value') else i.instrument_type),
            currency=i.currency,
            spread_bps=float(i.spread_bps or 0),
        )
        for i in instruments
    ]

    comparison = optimizer.compare_strategies(debt_instruments, strategy_a, strategy_b, scenarios)
    return comparison


# ── Exports ─────────────────────────────────────────────────────────

@router.get("/entities/{entity_id}/export/mtds")
def export_mtds(
    entity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entity = db.query(GovernmentEntity).filter(
        GovernmentEntity.id == entity_id,
        GovernmentEntity.org_id == user.org_id,
    ).first()
    if not entity:
        raise HTTPException(404, "Entity not found")

    entity_portfolios = db.query(EntityPortfolio).filter(
        EntityPortfolio.entity_id == entity_id
    ).all()
    instruments = []
    for ep in entity_portfolios:
        insts = db.query(DebtInstrument).filter(
            DebtInstrument.portfolio_id == ep.portfolio_id
        ).all()
        instruments.extend([_instrument_to_dict(i) for i in insts])

    portfolio_data = {
        "entity": _entity_to_dict(entity),
        "instruments": instruments,
    }
    return mtds_exporter.export(portfolio_data)


@router.get("/entities/{entity_id}/export/dsa")
def export_dsa(
    entity_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entity = db.query(GovernmentEntity).filter(
        GovernmentEntity.id == entity_id,
        GovernmentEntity.org_id == user.org_id,
    ).first()
    if not entity:
        raise HTTPException(404, "Entity not found")

    entity_portfolios = db.query(EntityPortfolio).filter(
        EntityPortfolio.entity_id == entity_id
    ).all()
    instruments = []
    for ep in entity_portfolios:
        insts = db.query(DebtInstrument).filter(
            DebtInstrument.portfolio_id == ep.portfolio_id
        ).all()
        instruments.extend([_instrument_to_dict(i) for i in insts])

    portfolio_data = {
        "entity": _entity_to_dict(entity),
        "instruments": instruments,
    }
    return dsa_exporter.export(portfolio_data)


@router.get("/entities/{entity_id}/export/csv")
def export_csv(
    entity_id: str,
    export_type: str = "instruments",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entity = db.query(GovernmentEntity).filter(
        GovernmentEntity.id == entity_id,
        GovernmentEntity.org_id == user.org_id,
    ).first()
    if not entity:
        raise HTTPException(404, "Entity not found")

    if export_type == "instruments":
        entity_portfolios = db.query(EntityPortfolio).filter(
            EntityPortfolio.entity_id == entity_id
        ).all()
        instruments = []
        for ep in entity_portfolios:
            insts = db.query(DebtInstrument).filter(
                DebtInstrument.portfolio_id == ep.portfolio_id
            ).all()
            instruments.extend([_instrument_to_dict(i) for i in insts])
        return {"csv": csv_exporter.instruments_to_csv(instruments), "filename": f"{entity.name}_instruments.csv"}

    return {"error": "Unknown export type"}


# ── Helper serializers ──────────────────────────────────────────────

def _entity_to_dict(e) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "entity_type": e.entity_type.value if hasattr(e.entity_type, 'value') else str(e.entity_type),
        "parent_id": e.parent_id,
        "population": e.population,
        "gdp_local": float(e.gdp_local) if e.gdp_local else None,
        "currency": e.currency,
        "iso_code": e.iso_code,
        "metadata_json": e.metadata_json,
    }


def _instrument_to_dict(i) -> dict:
    return {
        "id": i.id,
        "name": i.name,
        "instrument_type": i.instrument_type.value if hasattr(i.instrument_type, 'value') else str(i.instrument_type),
        "currency": i.currency,
        "principal_outstanding": float(i.principal_outstanding),
        "coupon_rate": float(i.coupon_rate),
        "maturity_date": i.maturity_date,
        "issue_date": i.issue_date,
        "spread_bps": float(i.spread_bps or 0),
    }


def _cl_to_dict(cl) -> dict:
    return {
        "id": cl.id,
        "name": cl.name,
        "cl_type": cl.cl_type.value if hasattr(cl.cl_type, 'value') else str(cl.cl_type),
        "exposure_amount": float(cl.exposure_amount),
        "probability_of_call": float(cl.probability_of_call),
        "expected_loss": float(cl.expected_loss),
        "counterparty": cl.counterparty,
        "is_national_guarantee": cl.is_national_guarantee,
        "maturity_date": cl.maturity_date,
    }


def _transfer_to_dict(t) -> dict:
    return {
        "id": t.id,
        "source_entity_id": t.source_entity_id,
        "transfer_type": t.transfer_type.value if hasattr(t.transfer_type, 'value') else str(t.transfer_type),
        "annual_amount": float(t.annual_amount),
        "covers_debt_service_pct": float(t.covers_debt_service_pct),
        "is_statutory": t.is_statutory,
    }


def _rule_to_dict(r) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "rule_type": r.rule_type.value if hasattr(r.rule_type, 'value') else str(r.rule_type),
        "threshold_value": float(r.threshold_value),
        "threshold_unit": r.threshold_unit,
        "is_hard_limit": r.is_hard_limit,
        "statute_reference": r.statute_reference,
    }


def _assumption_to_dict(a) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "category": a.category.value if hasattr(a.category, 'value') else str(a.category),
        "value": float(a.value),
        "unit": a.unit,
        "source": a.source,
        "version": a.version,
        "is_current": a.is_current,
        "changed_by": a.changed_by,
        "change_reason": a.change_reason,
        "previous_value": float(a.previous_value) if a.previous_value is not None else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _summary_to_dict(s) -> dict:
    return {
        "entity_id": s.entity_id,
        "entity_name": s.entity_name,
        "entity_type": s.entity_type,
        "direct_debt": s.direct_debt,
        "contingent_liability_exposure": s.contingent_liability_exposure,
        "contingent_liability_expected_loss": s.contingent_liability_expected_loss,
        "guaranteed_by_national": s.guaranteed_by_national,
        "net_debt": s.net_debt,
        "total_public_sector_debt": s.total_public_sector_debt,
        "transfers_received": s.transfers_received,
        "self_funded_debt_service_pct": s.self_funded_debt_service_pct,
        "instrument_count": s.instrument_count,
        "children": [_summary_to_dict(c) for c in s.children],
    }
