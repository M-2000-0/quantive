"""
Scenario Comparison API
========================
Side-by-side strategy comparison under multiple macro scenarios.
Compares restructuring proposals, optimizations, and stress tests.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


# ── Request / Response Models ──────────────────────────────────────────

class ScenarioInput(BaseModel):
    name: str
    description: str = ""
    rate_shock_bps: float = 0.0
    fx_shock_pct: float = 0.0
    gdp_growth_pct: float = 2.5
    spread_bps: float = 0.0
    commodity_shock_pct: float = 0.0
    equity_shock_pct: float = 0.0


class ScenarioComparisonRequest(BaseModel):
    base_debt: float = 500e9
    base_gdp: float = 1000e9
    base_debt_service_ratio: float = 15.0
    scenarios: list[ScenarioInput]


class ScenarioResult(BaseModel):
    name: str
    description: str
    debt_to_gdp: float
    debt_service_ratio: float
    interest_cost_change_pct: float
    fx_impact: float
    recession_probability: float
    risk_score: str  # low, medium, high, critical
    status: str  # compliant, warning, breach


class ScenarioComparisonResponse(BaseModel):
    base_case: ScenarioResult
    scenarios: list[ScenarioResult]
    recommendation: str
    best_scenario: str
    worst_scenario: str


# ── Scenario Engine ────────────────────────────────────────────────────

def _compute_scenario(base: ScenarioInput, base_debt: float, base_gdp: float,
                      base_dsr: float) -> ScenarioResult:
    """Compute the impact of a macro scenario on debt metrics."""
    import math

    debt_to_gdp = (base_debt / base_gdp) * 100
    interest_cost_change = 0.0
    fx_impact = 0.0

    # Rate shock: +100bps on rates → higher debt service cost
    if base.rate_shock_bps != 0:
        rate_effect = base.rate_shock_bps / 10000  # Convert bps to decimal
        interest_cost_change = rate_effect * (base_debt / base_gdp) * 100
        debt_to_gdp += interest_cost_change * 0.3  # Gradual pass-through

    # FX shock: currency depreciation increases external debt burden in local currency
    if base.fx_shock_pct != 0:
        fx_effect = abs(base.fx_shock_pct) / 100
        # Assume 40% of debt is external
        fx_impact = fx_effect * 0.4 * (base_debt / base_gdp) * 100
        debt_to_gdp += fx_impact

    # GDP growth: lower growth → higher debt-to-GDP
    growth_drag = (2.5 - base.gdp_growth_pct) / 100  # Deviation from baseline
    if growth_drag > 0:
        debt_to_gdp += growth_drag * debt_to_gdp * 0.5

    # Spread widening: increases cost of new issuance
    if base.spread_bps != 0:
        spread_effect = base.spread_bps / 10000
        interest_cost_change += spread_effect * (base_debt / base_gdp) * 0.2 * 100

    # Debt service ratio
    dsr = base_dsr * (1 + interest_cost_change / 100)
    if base.fx_shock_pct < 0:
        dsr *= (1 + abs(base.fx_shock_pct) / 200)

    # Recession probability (simplified model)
    recession_prob = 0.05  # Base 5%
    if base.rate_shock_bps > 200:
        recession_prob += 0.15
    if base.fx_shock_pct < -10:
        recession_prob += 0.10
    if base.equity_shock_pct < -20:
        recession_prob += 0.15
    if base.gdp_growth_pct < 0:
        recession_prob += 0.20
    recession_prob = min(recession_prob, 0.95)

    # Risk scoring
    if debt_to_gdp > 90 or dsr > 30:
        risk_score = "critical"
    elif debt_to_gdp > 70 or dsr > 25:
        risk_score = "high"
    elif debt_to_gdp > 50 or dsr > 20:
        risk_score = "medium"
    else:
        risk_score = "low"

    # Compliance status (Maastricht-style: 60% debt-to-GDP, 25% DSR)
    if debt_to_gdp > 60 or dsr > 25:
        status = "breach"
    elif debt_to_gdp > 54 or dsr > 22.5:
        status = "warning"
    else:
        status = "compliant"

    return ScenarioResult(
        name=base.name,
        description=base.description,
        debt_to_gdp=round(debt_to_gdp, 2),
        debt_service_ratio=round(dsr, 2),
        interest_cost_change_pct=round(interest_cost_change, 2),
        fx_impact=round(fx_impact, 2),
        recession_probability=round(recession_prob, 3),
        risk_score=risk_score,
        status=status,
    )


# ── API Endpoints ──────────────────────────────────────────────────────

@router.post("/compare", response_model=ScenarioComparisonResponse)
def compare_scenarios(request: ScenarioComparisonRequest):
    """Compare multiple macro scenarios side by side."""
    if not request.scenarios:
        raise HTTPException(status_code=400, detail="At least one scenario required")

    base_case = _compute_scenario(
        ScenarioInput(name="Base Case", gdp_growth_pct=2.5),
        request.base_debt, request.base_gdp, request.base_debt_service_ratio,
    )

    results = [
        _compute_scenario(s, request.base_debt, request.base_gdp, request.base_debt_service_ratio)
        for s in request.scenarios
    ]

    all_cases = [base_case] + results
    best = min(all_cases, key=lambda x: x.debt_to_gdp)
    worst = max(all_cases, key=lambda x: x.debt_to_gdp)

    # Generate recommendation
    breach_count = sum(1 for c in all_cases if c.status == "breach")
    if breach_count == 0:
        recommendation = "All scenarios remain within fiscal rule thresholds. No immediate action required."
    elif breach_count <= 1:
        recommendation = f"1 scenario breaches fiscal rules. Review contingency measures and ensure adequate reserves."
    else:
        recommendation = f"{breach_count} scenarios breach fiscal rules. Immediate risk mitigation recommended: consider debt restructuring, spending review, or revenue measures."

    return ScenarioComparisonResponse(
        base_case=base_case,
        scenarios=results,
        recommendation=recommendation,
        best_scenario=best.name,
        worst_scenario=worst.name,
    )


@router.get("/presets")
def get_scenario_presets():
    """Return common pre-built scenario templates."""
    return {
        "presets": [
            {
                "name": "Global Financial Crisis 2008",
                "description": "Severe global recession with credit freeze",
                "rate_shock_bps": 300,
                "fx_shock_pct": -15,
                "gdp_growth_pct": -3.0,
                "spread_bps": 500,
                "equity_shock_pct": -45,
                "commodity_shock_pct": -25,
            },
            {
                "name": "COVID-19 Pandemic",
                "description": "Global pandemic with lockdowns and supply disruption",
                "rate_shock_bps": -200,
                "fx_shock_pct": -8,
                "gdp_growth_pct": -5.0,
                "spread_bps": 200,
                "equity_shock_pct": -30,
                "commodity_shock_pct": -15,
            },
            {
                "name": "Interest Rate Spike",
                "description": "Rapid monetary tightening, 400bps rate increase",
                "rate_shock_bps": 400,
                "fx_shock_pct": 5,
                "gdp_growth_pct": 0.5,
                "spread_bps": 150,
                "equity_shock_pct": -20,
                "commodity_shock_pct": -10,
            },
            {
                "name": "Currency Crisis",
                "description": "Emerging market currency collapse",
                "rate_shock_bps": 500,
                "fx_shock_pct": -30,
                "gdp_growth_pct": -2.0,
                "spread_bps": 800,
                "equity_shock_pct": -35,
                "commodity_shock_pct": 10,
            },
            {
                "name": "Stagflation",
                "description": "High inflation with stagnant growth",
                "rate_shock_bps": 250,
                "fx_shock_pct": -5,
                "gdp_growth_pct": 0.2,
                "spread_bps": 100,
                "equity_shock_pct": -15,
                "commodity_shock_pct": 30,
            },
            {
                "name": "Commodity Boom",
                "description": "Favorable terms of trade for commodity exporters",
                "rate_shock_bps": 50,
                "fx_shock_pct": 8,
                "gdp_growth_pct": 4.5,
                "spread_bps": -50,
                "equity_shock_pct": 10,
                "commodity_shock_pct": 40,
            },
        ]
    }
