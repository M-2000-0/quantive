"""API endpoints for ESG/Green Bond optimization."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DebtInstrument, Portfolio, User
from app.security import get_current_user

router = APIRouter(prefix="/api/esg", tags=["esg-green"])


@router.get("/score/{portfolio_id}")
def get_esg_scores(
    portfolio_id: str,
    country_code: str = "US",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Score all instruments in a portfolio on ESG metrics."""
    from app.esg_optimizer import ESGScoringEngine

    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id == portfolio_id
    ).all()

    instruments_data = [
        {
            "id": inst.id,
            "name": inst.name,
            "instrument_type": inst.instrument_type.value if hasattr(inst.instrument_type, 'value') else inst.instrument_type,
            "currency": inst.currency,
            "principal_outstanding": inst.principal_outstanding,
            "coupon_rate": inst.coupon_rate,
            "maturity_date": inst.maturity_date,
            "issue_date": inst.issue_date,
            "spread_bps": inst.spread_bps,
        }
        for inst in instruments
    ]

    engine = ESGScoringEngine(instruments_data, country_code=country_code)
    return engine.score_instruments()


@router.get("/carbon-scenarios/{country_code}")
def get_carbon_scenarios(country_code: str):
    """Get carbon price impact scenarios for a country."""
    from app.esg_optimizer import CARBON_INTENSITY, CARBON_PRICE_SCENARIOS, COUNTRY_ESG_SCORES

    country = country_code.upper()
    esg = COUNTRY_ESG_SCORES.get(country, {})
    intensity = CARBON_INTENSITY.get(country, 200)

    scenarios = {}
    for name, price in CARBON_PRICE_SCENARIOS.items():
        scenarios[name] = {
            "carbon_price_per_tonne": price,
            "country_carbon_intensity": intensity,
            "annual_cost_per_billion_debt": round(intensity * price / 1e6, 2),
        }

    return {
        "country": country,
        "esg": esg,
        "carbon_intensity": intensity,
        "scenarios": scenarios,
    }


@router.post("/optimize-constraints")
def add_esg_constraints(
    base_constraints: dict = {},
    esg_config: dict = {},
    user: User = Depends(get_current_user),
):
    """Merge ESG constraints into optimization constraints."""
    from app.esg_optimizer import ESGConstrainedOptimizer

    enhanced = ESGConstrainedOptimizer.add_esg_constraints(base_constraints, esg_config)
    return {"enhanced_constraints": enhanced}


@router.get("/green-criteria")
def get_green_bond_criteria():
    """Get ICMA Green Bond Principles eligibility criteria."""
    from app.esg_optimizer import GREEN_BOND_CRITERIA
    return GREEN_BOND_CRITERIA


@router.get("/country-scores")
def get_all_country_esg_scores():
    """Get ESG scores for all tracked countries."""
    from app.esg_optimizer import COUNTRY_ESG_SCORES
    return COUNTRY_ESG_SCORES
