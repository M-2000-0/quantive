"""IMF Compliance & Explainability API Endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.explainability import ExplainabilityEngine
from app.imf_compliance import IMFComplianceEngine

router = APIRouter(prefix="/api/compliance", tags=["compliance"])
explain_router = APIRouter(prefix="/api/explain", tags=["explainability"])


# ── IMF Compliance Endpoints ──────────────────────────────────────────


@router.get("/dsa/{country_code}")
def get_debt_sustainability(country_code: str):
    """Generate a Debt Sustainability Analysis report for a country.
    
    Required by the IMF for all lending programs.
    Follows the IMF-World Bank Debt Sustainability Framework (DSF).
    """
    try:
        engine = IMFComplianceEngine()
        dsa = engine.generate_dsa(country_code.upper())
        return {"success": True, "data": dsa.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DSA generation failed: {str(e)}")


@router.get("/mtds/{country_code}")
def get_medium_term_strategy(country_code: str):
    """Generate a Medium-Term Debt Strategy report (3-5 year plan).
    
    Forward-looking debt management plan required by IMF/World Bank.
    """
    try:
        engine = IMFComplianceEngine()
        mtds = engine.generate_mtds(country_code.upper())
        return {"success": True, "data": mtds.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MTDS generation failed: {str(e)}")


@router.get("/gfs/{country_code}")
def get_government_finance_stats(country_code: str):
    """Generate Government Finance Statistics data.
    
    Standardized fiscal data following the IMF GFS Manual.
    """
    try:
        engine = IMFComplianceEngine()
        gfs = engine.generate_gfs(country_code.upper())
        return {"success": True, "data": gfs}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GFS generation failed: {str(e)}")


@router.get("/debt-ceiling/{country_code}")
def get_debt_ceiling_analysis(country_code: str):
    """Generate debt ceiling analysis.
    
    Analysis of whether current debt levels are sustainable
    and recommendations for legal debt limits.
    """
    try:
        engine = IMFComplianceEngine()
        result = engine.generate_debt_ceiling(country_code.upper())
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debt ceiling analysis failed: {str(e)}")


@router.get("/reports/{country_code}")
def get_all_compliance_reports(country_code: str):
    """Generate all compliance reports for a country in one call.
    
    Returns DSA, MTDS, GFS, and debt ceiling analysis.
    """
    try:
        engine = IMFComplianceEngine()
        code = country_code.upper()
        return {
            "success": True,
            "data": {
                "dsa": engine.generate_dsa(code).to_dict(),
                "mtds": engine.generate_mtds(code).to_dict(),
                "gfs": engine.generate_gfs(code),
                "debt_ceiling": engine.generate_debt_ceiling(code),
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


# ── Explainability Endpoints ──────────────────────────────────────────


class ExplainRequest(BaseModel):
    strategy: dict
    portfolio_data: dict
    country_code: str = "US"


@explain_router.post("/strategy")
def explain_strategy_recommendation(req: ExplainRequest):
    """Generate an explainability report for an optimization strategy.
    
    Shows WHY a strategy was recommended with:
    - Factor importance ranking
    - Step-by-step decision trail
    - Counterfactual analysis ("what if X were different?")
    - Confidence and uncertainty assessment
    """
    try:
        engine = ExplainabilityEngine()
        report = engine.explain_recommendation(
            strategy=req.strategy,
            portfolio_data=req.portfolio_data,
            country_code=req.country_code,
        )
        return {"success": True, "data": report.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Explanation generation failed: {str(e)}")


@explain_router.get("/methodology")
def get_methodology():
    """Return the optimization methodology documentation.
    
    Explains the multi-solver approach, scenario generation,
    and validation process for full transparency.
    """
    return {
        "success": True,
        "data": {
            "optimization": {
                "title": "Multi-Objective Sovereign Debt Optimization",
                "description": (
                    "Quantive uses three independent optimization solvers to ensure "
                    "robustness. All three must converge within 5% for results to be "
                    "considered reliable."
                ),
                "solvers": [
                    {
                        "name": "Mixed-Integer Linear Programming (MILP)",
                        "engine": "CBC via SciPy",
                        "strength": "Global optimum for linear constraints",
                        "weakness": "Cannot handle non-linear risk objectives",
                        "use_case": "Primary solver for deterministic optimization",
                    },
                    {
                        "name": "Simulated Annealing (SA)",
                        "engine": "Custom implementation",
                        "strength": "Handles non-linear objectives and complex constraints",
                        "weakness": "No guarantee of global optimum",
                        "use_case": "Risk-adjusted optimization with non-linear objectives",
                    },
                    {
                        "name": "QUBO (Quantum-Inspired)",
                        "engine": "D-Wave Inspired Binary Quadratic Model",
                        "strength": "Quantum-ready architecture for future hardware",
                        "weakness": "Approximate solution for large problems",
                        "use_case": "Alternative validation and future quantum deployment",
                    },
                ],
                "validation": "Cross-solver convergence check (5% tolerance)",
            },
            "scenario_generation": {
                "title": "Monte Carlo Scenario Engine",
                "description": "Generates 10,000 market scenarios for robust risk assessment.",
                "factors": ["Interest rates", "Inflation", "GDP growth", "FX rates", "Credit spreads"],
                "model": "Geometric Brownian Motion with Mean Reversion",
                "calibration": "Historical data from 2000-2024",
            },
            "risk_metrics": {
                "title": "Risk Quantification Framework",
                "metrics": [
                    {"name": "Value at Risk (VaR)", "confidence": "95% and 99%", "horizon": "1-year"},
                    {"name": "Conditional VaR (CVaR)", "confidence": "95% and 99%", "horizon": "1-year"},
                    {"name": "Refinancing Risk", "description": "Concentration of maturities in near-term windows"},
                    {"name": "Interest Rate Risk", "description": "Sensitivity of portfolio value to rate changes"},
                    {"name": "Currency Risk", "description": "FX exposure across foreign-currency instruments"},
                ],
            },
            "data_sources": [
                "US Treasury Department (yield curves)",
                "European Central Bank (ECB rates)",
                "Federal Reserve Bank of New York (SOFR)",
                "World Bank (country fundamentals)",
                "Bloomberg/Refinitiv (historical market data)",
            ],
        },
    }
