"""Risk aggregation and management endpoints for Layer 6 (National Risk Operating System)."""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from quantive.risk import (
    CyberRisk,
    CyberThreat,
    CyberVulnerability,
    FiscalRisk,
    FiscalPressure,
    SovereignRiskIndicator,
    ClimateRisk,
    ClimateImpact,
    ClimateScenario,
    InfrastructureRisk,
    AssetCriticality,
    FailureMode,
    GeopoliticalRisk,
    GeopoliticalEvent,
    AllianceRelationship,
    SupplyChainRisk,
    SupplyChainDisruption,
    RiskCategory,
    RiskSeverity,
    TrendDirection,
)
from quantive.api.state import state
from quantive.early_warning.indicators import (
    DEBT_TO_GDP_CONFIG,
    DEBT_SERVICE_CONFIG,
    LIQUIDITY_COVERAGE_RATIO_CONFIG,
    FOREIGN_RESERVE_COVERAGE_CONFIG,
    CDS_SPREAD_CONFIG,
    EXTERNAL_DEBT_RATIO_CONFIG,
    PRIMARY_BALANCE_CONFIG,
    TAX_REVENUE_Volatility_CONFIG,
    REVENUE_VOLATILITY_CONFIG,
    TAX_BASE_CONTRACTION_CONFIG,
    PENSION_FUNDING_RATIO_CONFIG,
    PENSION_DEMOGRAPHIC_RATIO_CONFIG,
)


router = APIRouter(prefix="/risk", tags=["risk"])


# ── Helper: merge risk scores from multiple sources ────────────────────────

def _merge_risk_scores(
    risk_assessments: List[dict],
    category_weights: Dict[RiskCategory, float],
) -> dict:
    """Merge multiple risk assessment dicts into a composite score."""
    if not risk_assessments:
        return {"overall": 0.0, "by_category": {}}

    # Weighted average by category
    weighted_sum = 0.0
    category_sums: Dict[RiskCategory, float] = {c: 0.0 for c in RiskCategory}
    category_counts: Dict[RiskCategory, int] = {c: 0 for c in RiskCategory}

    for ra in risk_assessments:
        overall = ra.get("overall_score", 0.0)
        cat = RiskCategory(ra.get("category", "fiscal"))
        weighted_sum += overall * category_weights.get(cat, 1.0)
        category_sums[cat] = category_sums.get(cat, 0.0) + overall
        category_counts[cat] = category_counts.get(cat, 0) + 1

    n = len(risk_assessments)
    composite = weighted_sum / n if n > 0 else 0.0

    by_category = {}
    for cat in RiskCategory:
        if category_counts[cat] > 0:
            by_category[cat] = round(category_sums[cat] / category_counts[cat], 2)
        else:
            by_category[cat] = 0.0

    return {"overall": round(composite, 2), "by_category": by_category}


# ── Cyber Risk Endpoints ──────────────────────────────────────────────────

@router.post("/cyber", status_code=201, response_model=CyberRisk)
def create_cyber_risk(request: CyberRisk) -> CyberRisk:
    """Create or update a cyber risk assessment."""
    risk_id = request.id or f"cyber-{uuid.uuid4().hex[:8]}"
    risk = CyberRisk(id=risk_id, **request.model_dump(exclude={"id"}))
    state.risk_assessments[risk.id] = risk.model_dump()
    return risk


@router.get("/cyber", response_model=List[CyberRisk])
def list_cyber_risks() -> List[CyberRisk]:
    """List all cyber risk assessments."""
    from quantive.risk import CyberRisk
    return [
        CyberRisk(**ra)
        for ra in state.risk_assessments.values()
        if ra.get("category") == RiskCategory.CYBER.value
    ]


@router.get("/cyber/summary")
def cyber_risk_summary() -> dict:
    """Get cyber risk summary for dashboard."""
    cyber_risks = [
        ra for ra in state.risk_assessments.values()
        if ra.get("category") == RiskCategory.CYBER.value
    ]
    if not cyber_risks:
        return {"overall": 0.0, "by_category": {c: 0.0 for c in RiskCategory}}

    weights = {RiskCategory.CYBER: 1.0}
    merged = _merge_risk_scores(cyber_risks, weights)
    return merged


# ── Fiscal Risk Endpoints ─────────────────────────────────────────────────

@router.post("/fiscal", status_code=201, response_model=FiscalRisk)
def create_fiscal_risk(request: FiscalRisk) -> FiscalRisk:
    """Create or update a fiscal risk assessment."""
    risk_id = request.id or f"fiscal-{uuid.uuid4().hex[:8]}"
    risk = FiscalRisk(id=risk_id, **request.model_dump(exclude={"id"}))
    state.risk_assessments[risk.id] = risk.model_dump()
    return risk


@router.get("/fiscal", response_model=List[FiscalRisk])
def list_fiscal_risks() -> List[FiscalRisk]:
    """List all fiscal risk assessments."""
    from quantive.risk import FiscalRisk
    return [
        FiscalRisk(**ra)
        for ra in state.risk_assessments.values()
        if ra.get("category") == RiskCategory.FISCAL.value
    ]


@router.get("/fiscal/summary")
def fiscal_risk_summary() -> dict:
    """Get fiscal risk summary for dashboard."""
    fiscal_risks = [
        ra for ra in state.risk_assessments.values()
        if ra.get("category") == RiskCategory.FISCAL.value
    ]
    weights = {RiskCategory.FISCAL: 1.0}
    merged = _merge_risk_scores(fiscal_risks, weights)
    return merged


# ── Climate Risk Endpoints ────────────────────────────────────────────────

@router.post("/climate", status_code=201, response_model=ClimateRisk)
def create_climate_risk(request: ClimateRisk) -> ClimateRisk:
    """Create or update a climate risk assessment."""
    risk_id = request.id or f"climate-{uuid.uuid4().hex[:8]}"
    risk = ClimateRisk(id=risk_id, **request.model_dump(exclude={"id"}))
    state.risk_assessments[risk.id] = risk.model_dump()
    return risk


@router.get("/climate", response_model=List[ClimateRisk])
def list_climate_risks() -> List[ClimateRisk]:
    """List all climate risk assessments."""
    from quantive.risk import ClimateRisk
    return [
        ClimateRisk(**ra)
        for ra in state.risk_assessments.values()
        if ra.get("category") == RiskCategory.CLIMATE.value
    ]


@router.get("/climate/summary")
def climate_risk_summary() -> dict:
    """Get climate risk summary for dashboard."""
    climate_risks = [
        ra for ra in state.risk_assessments.values()
        if ra.get("category") == RiskCategory.CLIMATE.value
    ]
    weights = {RiskCategory.CLIMATE: 1.0}
    merged = _merge_risk_scores(climate_risks, weights)
    return merged


# ── Infrastructure Risk Endpoints ──────────────────────────────────────────

@router.post("/infrastructure", status_code=201, response_model=InfrastructureRisk)
def create_infrastructure_risk(request: InfrastructureRisk) -> InfrastructureRisk:
    """Create or update an infrastructure risk assessment."""
    risk_id = request.id or f"infra-{uuid.uuid4().hex[:8]}"
    risk = InfrastructureRisk(id=risk_id, **request.model_dump(exclude={"id"}))
    state.risk_assessments[risk.id] = risk.model_dump()
    return risk


@router.get("/infrastructure", response_model=List[InfrastructureRisk])
def list_infrastructure_risks() -> List[InfrastructureRisk]:
    """List all infrastructure risk assessments."""
    from quantive.risk import InfrastructureRisk
    return [
        InfrastructureRisk(**ra)
        for ra in state.risk_assessments.values()
        if ra.get("category") == RiskCategory.INFRASTRUCTURE.value
    ]


@router.get("/infrastructure/summary")
def infrastructure_risk_summary() -> dict:
    """Get infrastructure risk summary for dashboard."""
    infra_risks = [
        ra for ra in state.risk_assessments.values()
        if ra.get("category") == RiskCategory.INFRASTRUCTURE.value
    ]
    weights = {RiskCategory.INFRASTRUCTURE: 1.0}
    merged = _merge_risk_scores(infra_risks, weights)
    return merged


# ── Geopolitical Risk Endpoints ────────────────────────────────────────────

@router.post("/geopolitical", status_code=201, response_model=GeopoliticalRisk)
def create_geopolitical_risk(request: GeopoliticalRisk) -> GeopoliticalRisk:
    """Create or update a geopolitical risk assessment."""
    risk_id = request.id or f"geo-{uuid.uuid4().hex[:8]}"
    risk = GeopoliticalRisk(id=risk_id, **request.model_dump(exclude={"id"}))
    state.risk_assessments[risk.id] = risk.model_dump()
    return risk


@router.get("/geopolitical", response_model=List[GeopoliticalRisk])
def list_geopolitical_risks() -> List[GeopoliticalRisk]:
    """List all geopolitical risk assessments."""
    from quantive.risk import GeopoliticalRisk
    return [
        GeopoliticalRisk(**ra)
        for ra in state.risk_assessments.values()
        if ra.get("category") == RiskCategory.GEOPOLITICAL.value
    ]


@router.get("/geopolitical/summary")
def geopolitical_risk_summary() -> dict:
    """Get geopolitical risk summary for dashboard."""
    geo_risks = [
        ra for ra in state.risk_assessments.values()
        if ra.get("category") == RiskCategory.GEOPOLITICAL.value
    ]
    weights = {RiskCategory.GEOPOLITICAL: 1.0}
    merged = _merge_risk_scores(geo_risks, weights)
    return merged


# ── Supply Chain Risk Endpoints ────────────────────────────────────────────

@router.post("/supply-chain", status_code=201, response_model=SupplyChainRisk)
def create_supply_chain_risk(request: SupplyChainRisk) -> SupplyChainRisk:
    """Create or update a supply chain risk assessment."""
    risk_id = request.id or f"sc-{uuid.uuid4().hex[:8]}"
    risk = SupplyChainRisk(id=risk_id, **request.model_dump(exclude={"id"}))
    state.risk_assessments[risk.id] = risk.model_dump()
    return risk


@router.get("/supply-chain", response_model=List[SupplyChainRisk])
def list_supply_chain_risks() -> List[SupplyChainRisk]:
    """List all supply chain risk assessments."""
    from quantive.risk import SupplyChainRisk
    return [
        SupplyChainRisk(**ra)
        for ra in state.risk_assessments.values()
        if ra.get("category") == RiskCategory.SUPPLY_CHAIN.value
    ]


@router.get("/supply-chain/summary")
def supply_chain_risk_summary() -> dict:
    """Get supply chain risk summary for dashboard."""
    sc_risks = [
        ra for ra in state.risk_assessments.values()
        if ra.get("category") == RiskCategory.SUPPLY_CHAIN.value
    ]
    weights = {RiskCategory.SUPPLY_CHAIN: 1.0}
    merged = _merge_risk_scores(sc_risks, weights)
    return merged


# ── Aggregated Risk Dashboard Endpoint ─────────────────────────────────────

@router.get("/aggregate/{entity_id}")
def aggregate_risk(
    entity_id: str,
    entity_type: str = "government",
    weights: Optional[Dict[str, float]] = None,
) -> dict:
    """Aggregate all risk types for a given entity.

    Args:
        entity_id: Identifier of the government/portfolio entity
        entity_type: Type of entity (government or portfolio)
        weights: Optional per-category weights (default: equal weighting)
    """
    if weights is None:
        weights = {
            RiskCategory.CYBER: 1.0,
            RiskCategory.FISCAL: 1.0,
            RiskCategory.CLIMATE: 1.0,
            RiskCategory.INFRASTRUCTURE: 1.0,
            RiskCategory.GEOPOLITICAL: 1.0,
            RiskCategory.SUPPLY_CHAIN: 1.0,
        }

    # Collect all risk assessments for this entity
    entity_risks: Dict[RiskCategory, List[dict]] = {cat: [] for cat in RiskCategory}

    for ra in state.risk_assessments.values():
        cat = RiskCategory(ra.get("category", "fiscal"))
        if ra.get("entity_id") == entity_id and ra.get("entity_type") == entity_type:
            entity_risks[cat].append(ra)

    # Merge per category
    by_category = {}
    overall_weighted = 0.0
    total_weight = 0.0

    for cat, category_weight in weights.items():
        risks = entity_risks.get(cat, [])
        if risks:
            merged = _merge_risk_scores(risks, {cat: category_weight})
            by_category[cat] = merged["overall"]
            overall_weighted += merged["overall"] * category_weight
            total_weight += category_weight
        else:
            by_category[cat] = 0.0

    overall = round(overall_weighted / total_weight, 2) if total_weight > 0 else 0.0

    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "overall_score": overall,
        "by_category": by_category,
        "category_counts": {
            cat: len(entity_risks.get(cat, [])) for cat in RiskCategory
        },
    }


# ── Early Warning Integration Endpoint ──────────────────────────────────────

@router.get("/early-warning/{entity_id}")
def early_warning_integration(
    entity_id: str,
) -> dict:
    """Integrate risk assessments with the early warning system (Layer 5).

    Returns risk signals that should trigger early warning alerts.
    """
    from quantive.risk import RiskSeverity, TrendDirection

    entity_risks = [
        ra for ra in state.risk_assessments.values()
        if ra.get("entity_id") == entity_id
    ]

    signals = []

    for ra in entity_risks:
        cat = RiskCategory(ra.get("category", "fiscal"))
        score = ra.get("overall_score", 0.0)

        # Map risk score to warning signal
        if cat == RiskCategory.FISCAL and score > 70:
            severity = RiskSeverity.CRITICAL
            trend = _determine_trend(ra)
            signals.append({
                "id": f"ew-{cat.value}-{ra.get('id', 'unknown')}",
                "name": f"{cat.value.upper()} Risk Elevated",
                "category": cat.value,
                "indicator": f"Overall {cat.value} risk score: {score}",
                "currentValue": score,
                "threshold": 70.0,
                "unit": "score",
                "direction": "above_danger",
                "status": severity.value,
                "trend": trend.value,
                "description": f"{cat.value.upper()} risk above warning threshold for {entity_id}",
                "lastUpdated": ra.get("last_assessed", "").isoformat() if ra.get("last_assessed") else "",
            })
        elif cat == RiskCategory.CYBER and score > 75:
            severity = RiskSeverity.HIGH
            trend = TrendDirection.DETERIORATING
            signals.append({
                "id": f"ew-{cat.value}-{ra.get('id', 'unknown')}",
                "name": f"{cat.value.upper()} Risk Elevated",
                "category": cat.value,
                "indicator": f"Overall {cat.value} risk score: {score}",
                "currentValue": score,
                "threshold": 75.0,
                "unit": "score",
                "direction": "above_danger",
                "status": severity.value,
                "trend": trend.value,
                "description": f"{cat.value.upper()} risk above alert threshold for {entity_id}",
                "lastUpdated": ra.get("last_assessed", "").isoformat() if ra.get("last_assessed") else "",
            })
        # Add similar handling for other categories...

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    signals.sort(key=lambda s: severity_order.get(s["status"], 99))

    return {
        "entity_id": entity_id,
        "signals": signals,
        "total_signals": len(signals),
        "critical_signals": len([s for s in signals if s["status"] == "critical"]),
    }


def _determine_trend(ra: dict) -> TrendDirection:
    """Determine trend direction from risk assessment history."""
    # Simplified: check if score has been increasing or decreasing
    # In a full implementation, would compare with historical assessments
    return TrendDirection.STABLE