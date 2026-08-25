"""API endpoints for Rating Agency Simulator."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/ratings", tags=["rating-simulator"])


class RatingShock(BaseModel):
    gdp_per_capita: Optional[float] = Field(None, description="GDP per capita override")
    gdp_growth: Optional[float] = Field(None, description="GDP growth %")
    inflation: Optional[float] = Field(None, description="Inflation rate %")
    unemployment: Optional[float] = Field(None, description="Unemployment rate %")
    debt_to_gdp: Optional[float] = Field(None, description="Debt/GDP ratio")
    deficit_to_gdp: Optional[float] = Field(None, description="Fiscal deficit/GDP")
    primary_balance: Optional[float] = Field(None, description="Primary balance/GDP")
    reserves_months: Optional[float] = Field(None, description="Import cover in months")
    current_account_pct: Optional[float] = Field(None, description="Current account/GDP")
    institutions_score: Optional[float] = Field(None, description="Institutional quality 0-100")
    rule_of_law: Optional[float] = Field(None, description="Rule of law 0-100")
    political_stability: Optional[float] = Field(None, description="Political stability 0-100")


@router.get("/simulate/{country_code}")
def simulate_ratings(
    country_code: str,
    user: User = Depends(get_current_user),
):
    """Simulate sovereign ratings for a country with current fundamentals."""
    from app.rating_simulator import RatingSimulatorEngine

    engine = RatingSimulatorEngine(country_code)
    return engine.simulate_all()


@router.post("/simulate/{country_code}")
def simulate_ratings_with_shocks(
    country_code: str,
    shocks: RatingShock,
    user: User = Depends(get_current_user),
):
    """Simulate sovereign ratings with applied economic shocks."""
    from app.rating_simulator import RatingSimulatorEngine

    shock_dict = {k: v for k, v in shocks.model_dump().items() if v is not None}
    engine = RatingSimulatorEngine(country_code)
    return engine.simulate_all(shocks=shock_dict)


@router.get("/scale")
def get_rating_scales():
    """Get the rating scales for all three agencies."""
    from app.rating_simulator import FITCH_SCALE, MOODYS_SCALE, SP_SCALE
    return {
        "sp": SP_SCALE,
        "moodys": MOODYS_SCALE,
        "fitch": FITCH_SCALE,
    }


@router.get("/country/{country_code}")
def get_country_rating_data(country_code: str):
    """Get the current rating data for a country."""
    from app.rating_simulator import COUNTRY_RATING_DATA

    data = COUNTRY_RATING_DATA.get(country_code.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"No data for country: {country_code}")
    return {"country": country_code.upper(), "data": data}


@router.get("/countries")
def list_available_countries():
    """List all countries with rating data."""
    from app.rating_simulator import COUNTRY_RATING_DATA
    countries = []
    for code, data in COUNTRY_RATING_DATA.items():
        countries.append({
            "code": code,
            "sp_rating": data.get("sp_rating"),
            "moodys_rating": data.get("moodys_rating"),
            "fitch_rating": data.get("fitch_rating"),
            "gdp_per_capita": data.get("gdp_per_capita"),
            "debt_to_gdp": data.get("debt_to_gdp"),
        })
    return countries


@router.post("/what-if/{country_code}")
def what_if_rating(
    country_code: str,
    shocks: RatingShock,
    user: User = Depends(get_current_user),
):
    """What-if analysis: how would specific changes affect ratings?"""
    from app.rating_simulator import RatingSimulatorEngine

    shock_dict = {k: v for k, v in shocks.model_dump().items() if v is not None}
    engine = RatingSimulatorEngine(country_code)
    result = engine.simulate_all(shocks=shock_dict)

    # Add comparison
    baseline = engine.simulate_all()
    changes = {}
    for agency in ["sp", "moodys", "fitch"]:
        changes[agency] = {
            "before": baseline["simulated_ratings"][agency],
            "after": result["simulated_ratings"][agency],
            "direction": result["rating_changes"][agency],
        }

    return {
        "country": country_code.upper(),
        "shocks_applied": shock_dict,
        "baseline": baseline["simulated_ratings"],
        "simulated": result["simulated_ratings"],
        "changes": changes,
        "assessments": result["assessments"],
        "key_drivers": result["key_drivers"],
    }
