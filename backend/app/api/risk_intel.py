"""Risk Intelligence API — Sanctions, Liquidity, Political, Contagion Risk Endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.contagion_risk import ContagionRiskModel
from app.liquidity_risk import LiquidityRiskModel
from app.political_risk import PoliticalRiskModel
from app.sanctions import SanctionsScreeningEngine

router = APIRouter(prefix="/api/risk-intel", tags=["risk-intelligence"])


# ── Sanctions Screening ──────────────────────────────────────────────

class SanctionScreenRequest(BaseModel):
    instruments: list[dict] = []
    counterparties: list[dict] = []
    constraints: dict = {}


@router.post("/sanctions/screen")
def screen_for_sanctions(req: SanctionScreenRequest):
    """Screen instruments and counterparties against global sanctions lists.

    Checks OFAC SDN, EU Consolidated, and UN Security Council lists.
    Returns blocking decision with full audit trail.
    """
    try:
        engine = SanctionsScreeningEngine()
        result = engine.screen_optimization_request({
            "instruments": req.instruments,
            "counterparties": req.counterparties,
            "constraints": req.constraints,
        })
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sanctions screening failed: {str(e)}")


@router.get("/sanctions/country/{country_code}")
def screen_country_sanctions(country_code: str):
    """Screen a country against all sanctions lists."""
    try:
        engine = SanctionsScreeningEngine()
        matches = engine.screen_country(country_code.upper())
        blocked = any(m.severity == "blocked" for m in matches)
        return {
            "success": True,
            "data": {
                "country_code": country_code.upper(),
                "blocked": blocked,
                "matches": [
                    {"list": m.list_name, "severity": m.severity, "reason": m.reason, "program": m.program}
                    for m in matches
                ],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sanctions/entity/{entity_name}")
def screen_entity_sanctions(entity_name: str, country: Optional[str] = None):
    """Screen an entity (bank, issuer, counterparty) against sanctions lists."""
    try:
        engine = SanctionsScreeningEngine()
        matches = engine.screen_entity(entity_name, country)
        return {
            "success": True,
            "data": {
                "entity": entity_name,
                "country": country,
                "matches": [
                    {"list": m.list_name, "severity": m.severity, "reason": m.reason, "score": m.score}
                    for m in matches
                ],
                "blocked": any(m.severity == "blocked" for m in matches),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Liquidity Risk ───────────────────────────────────────────────────

class LiquidityRequest(BaseModel):
    instruments: list[dict]


@router.post("/liquidity/portfolio")
def analyze_portfolio_liquidity(req: LiquidityRequest):
    """Analyze liquidity risk for a portfolio of instruments.

    Returns bid-ask spreads, market depth, days to liquidate,
    liquidity-adjusted VaR, and market impact costs.
    """
    try:
        model = LiquidityRiskModel()
        result = model.analyze_portfolio(req.instruments)
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Liquidity analysis failed: {str(e)}")


@router.post("/liquidity/stress-test")
def liquidity_stress_test(req: LiquidityRequest, scenario: str = "global"):
    """Run liquidity stress test under crisis scenarios.

    Scenarios: global, em_crises, rate_shock, geopolitical
    """
    try:
        model = LiquidityRiskModel()
        result = model.stress_test_liquidity(req.instruments, scenario)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Liquidity stress test failed: {str(e)}")


# ── Political Risk ───────────────────────────────────────────────────

@router.get("/political/{country_code}")
def get_political_risk(country_code: str):
    """Get political risk profile for a country.

    Includes regime stability, government change risk, capital controls,
    expropriation risk, conflict risk, and sanctions exposure.
    """
    try:
        model = PoliticalRiskModel()
        result = model.analyze_country(country_code.upper())
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Political risk analysis failed: {str(e)}")


@router.post("/political/portfolio")
def portfolio_political_risk(req: LiquidityRequest):
    """Assess political risk for a portfolio based on country exposures."""
    try:
        model = PoliticalRiskModel()
        result = model.portfolio_political_risk(req.instruments)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portfolio political risk failed: {str(e)}")


# ── Contagion Risk ───────────────────────────────────────────────────

@router.post("/contagion/cascade")
def simulate_cascade(
    trigger_country: str,
    req: LiquidityRequest,
    severity_bps: float = 500,
):
    """Simulate a default cascade from a trigger country.

    Shows which countries would be affected, through which channels,
    and the total portfolio impact.
    """
    try:
        model = ContagionRiskModel()
        result = model.simulate_cascade(trigger_country.upper(), req.instruments, severity_bps)
        return {"success": True, "data": result.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cascade simulation failed: {str(e)}")


@router.get("/contagion/linkages/{country_code}")
def get_contagion_linkages(country_code: str):
    """Get all contagion linkages for a country."""
    try:
        model = ContagionRiskModel()
        links = model.get_linkages(country_code.upper())
        return {
            "success": True,
            "data": {
                "country": country_code.upper(),
                "linkages": [link.to_dict() for link in links],
                "total_linkages": len(links),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/contagion/systemic")
def systemic_risk(req: LiquidityRequest):
    """Assess overall systemic/contagion risk for a portfolio."""
    try:
        model = ContagionRiskModel()
        result = model.systemic_risk_assessment(req.instruments)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Systemic risk assessment failed: {str(e)}")
