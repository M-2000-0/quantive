"""Quantive Brain API endpoints for Layer 10 (Cross-Layer Reasoning).

Provides REST endpoints for:
- Refinancing risk assessment across the maturity ladder
- Debt profile diagnostics and crisis-timeline estimation
- Dangerous assumption identification
- Integrated cross-layer reasoning across all 9 layers
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from quantive.api.state import state
from quantive.models.instruments import Portfolio
from quantive.reasoning import (
    assess_refinancing_risk,
    diagnose_debt_profile,
    identify_dangerous_assumptions,
    cross_layer_reasoning,
    RefinancingRiskAssessment,
    DebtProfileDiagnosis,
    DangerousAssumptions,
    CrossLayerReasoning,
)


router = APIRouter(prefix="/reasoning", tags=["reasoning"])


class RiskScoreInput(BaseModel):
    entity_id: str = Field(..., description="Government/entity identifier")
    risk_scores: Dict[str, float] = Field(
        default_factory=dict, description="dimension -> 0-100 risk score"
    )


@router.get("/refinancing/{portfolio_id}")
def refinancing_risk(
    portfolio_id: str,
) -> Dict[str, Any]:
    """Assess refinancing risk for a portfolio's maturity ladder."""
    portfolio = state.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    result = assess_refinancing_risk(portfolio)
    return result.dict()


@router.get("/profile/{portfolio_id}")
def debt_profile(
    portfolio_id: str,
) -> Dict[str, Any]:
    """Diagnose why a debt profile is worsening."""
    portfolio = state.get_portfolio(portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    result = diagnose_debt_profile(portfolio)
    return result.dict()


@router.post("/dangerous-assumptions")
def dangerous_assumptions(payload: RiskScoreInput) -> Dict[str, Any]:
    """Identify the most dangerous assumptions for government finances.

    Accepts a map of risk scores (layer_name -> 0-100) plus an entity id.
    Uses in-memory assumptions from the institutional memory registry.
    """
    from quantive.models.government import db
    from quantive.models.government import VersionedAssumption

    assumptions = (
        db.query(VersionedAssumption)
        .filter(VersionedAssumption.entity_id == payload.entity_id)
        .all()
    )
    results = identify_dangerous_assumptions(
        payload.entity_id, assumptions, payload.risk_scores
    )
    return {
        "entity_id": payload.entity_id,
        "count": len(results),
        "dangerous_assumptions": [r.dict() for r in results],
    }


@router.post("/cross-layer")
def cross_layer(payload: RiskScoreInput) -> Dict[str, Any]:
    """Integrated reasoning across all layers for an entity/portfolio."""
    portfolio = state.get_portfolio(payload.entity_id)
    if portfolio is None:
        raise HTTPException(
            status_code=404,
            detail="No portfolio found for this entity - create one first",
        )
    from quantive.models.government import db
    from quantive.models.government import VersionedAssumption

    assumptions = (
        db.query(VersionedAssumption)
        .filter(VersionedAssumption.entity_id == payload.entity_id)
        .all()
    )
    result = cross_layer_reasoning(
        portfolio,
        payload.entity_id,
        assumptions,
        payload.risk_scores,
    )
    return result.dict()
