"""Outcome-Based Pricing API endpoints.

Exposes pricing calculator, ROI reports, and pilot proposals
to replace the legacy subscription pricing model.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


# ── Request/Response Models ────────────────────────────────────────

class PortfolioProfileRequest(BaseModel):
    total_debt_outstanding: float = Field(..., gt=0, description="Total sovereign debt in USD")
    annual_issuance: float = Field(..., ge=0, description="Annual new debt issuance in USD")
    currency: str = Field(default="USD", max_length=3)
    debt_to_gdp: float = Field(default=0.0, ge=0, le=200)
    weighted_avg_maturity: float = Field(default=0.0, ge=0)
    weighted_avg_coupon: float = Field(default=0.0, ge=0, le=50)
    fx_exposure_pct: float = Field(default=0.0, ge=0, le=100)
    floating_rate_pct: float = Field(default=0.0, ge=0, le=100)


class QuoteRequest(BaseModel):
    portfolio: PortfolioProfileRequest
    term: str = Field(default="annual", description="Contract term")
    model: str = Field(default="basis_points", description="Pricing model")
    custom_rates: dict | None = Field(default=None, description="Custom rate overrides")


class PilotRequest(BaseModel):
    portfolio: PortfolioProfileRequest
    country_name: str = Field(..., min_length=2, max_length=255)
    contact_name: str = Field(..., min_length=2, max_length=255)
    contact_email: str = Field(..., min_length=5)
    use_case_description: str = Field(default="", max_length=2000)


# ── API Endpoints ──────────────────────────────────────────────────

@router.post("/calculate")
def calculate_quote(
    request: QuoteRequest,
    user: User = Depends(get_current_user),
):
    """Calculate an outcome-based pricing quote."""
    from quantive.government.outcome_pricing import (
        ContractTerm,
        OutcomePricingEngine,
        PricingModel,
        PortfolioProfile,
    )

    engine = OutcomePricingEngine()

    portfolio = PortfolioProfile(
        total_debt_outstanding=request.portfolio.total_debt_outstanding,
        annual_issuance=request.portfolio.annual_issuance,
        currency=request.portfolio.currency,
        debt_to_gdp=request.portfolio.debt_to_gdp,
        weighted_avg_maturity=request.portfolio.weighted_avg_maturity,
        weighted_avg_coupon=request.portfolio.weighted_avg_coupon,
        fx_exposure_pct=request.portfolio.fx_exposure_pct,
        floating_rate_pct=request.portfolio.floating_rate_pct,
    )

    term_map = {
        "pilot_12m": ContractTerm.PILOT_12M,
        "annual": ContractTerm.ANNUAL,
        "multi_year_3": ContractTerm.MULTI_YEAR_3,
        "multi_year_5": ContractTerm.MULTI_YEAR_5,
        "multi_year_10": ContractTerm.MULTI_YEAR_10,
    }
    term = term_map.get(request.term, ContractTerm.ANNUAL)

    model_map = {
        "basis_points": PricingModel.BASIS_POINTS,
        "risk_reduction": PricingModel.RISK_REDUCTION,
        "hybrid": PricingModel.HYBRID,
    }
    model = model_map.get(request.model, PricingModel.BASIS_POINTS)

    quote = engine.calculate_quote(
        portfolio=portfolio,
        term=term,
        model=model,
        custom_rates=request.custom_rates,
    )

    return {
        "quote": {
            "model": quote.model.value,
            "term": quote.term.value,
            "base_fee_annual": quote.base_fee_annual,
            "outcome_fee_annual": quote.outcome_fee_annual,
            "total_fee_annual": quote.total_fee_annual,
            "total_fee_term": quote.total_fee_term,
            "roi_ratio": quote.roi_ratio,
            "cost_per_basis_point": quote.cost_per_basis_point,
            "legacy_cost_comparison": quote.legacy_cost_comparison,
            "competitor_comparison": quote.competitor_comparison,
        },
        "savings_estimate": {
            "financing_cost_savings_bps": quote.savings_estimate.financing_cost_savings_bps,
            "refinancing_savings_usd": quote.savings_estimate.refinancing_savings_usd,
            "risk_reduction_bps": quote.savings_estimate.risk_reduction_bps,
            "total_annual_savings_usd": quote.savings_estimate.total_annual_savings_usd,
            "confidence_level": quote.savings_estimate.confidence_level,
        },
    }


@router.post("/roi-report")
def generate_roi_report(
    request: QuoteRequest,
    user: User = Depends(get_current_user),
):
    """Generate a comprehensive ROI report."""
    from quantive.government.outcome_pricing import (
        ContractTerm,
        OutcomePricingEngine,
        PricingModel,
        PortfolioProfile,
    )

    engine = OutcomePricingEngine()

    portfolio = PortfolioProfile(
        total_debt_outstanding=request.portfolio.total_debt_outstanding,
        annual_issuance=request.portfolio.annual_issuance,
        currency=request.portfolio.currency,
        debt_to_gdp=request.portfolio.debt_to_gdp,
    )

    term_map = {
        "pilot_12m": ContractTerm.PILOT_12M,
        "annual": ContractTerm.ANNUAL,
        "multi_year_3": ContractTerm.MULTI_YEAR_3,
        "multi_year_5": ContractTerm.MULTI_YEAR_5,
        "multi_year_10": ContractTerm.MULTI_YEAR_10,
    }
    term = term_map.get(request.term, ContractTerm.ANNUAL)

    quote = engine.calculate_quote(portfolio=portfolio, term=term)
    roi_report = engine.generate_roi_report(quote)

    return roi_report


@router.post("/pilot-proposal")
def generate_pilot_proposal(
    request: PilotRequest,
    user: User = Depends(get_current_user),
):
    """Generate a 12-month free pilot proposal."""
    from quantive.government.outcome_pricing import (
        OutcomePricingEngine,
        PortfolioProfile,
    )

    engine = OutcomePricingEngine()

    portfolio = PortfolioProfile(
        total_debt_outstanding=request.portfolio.total_debt_outstanding,
        annual_issuance=request.portfolio.annual_issuance,
        currency=request.portfolio.currency,
        debt_to_gdp=request.portfolio.debt_to_gdp,
    )

    proposal = engine.generate_pilot_proposal(portfolio)
    proposal["contact"] = {
        "name": request.contact_name,
        "email": request.contact_email,
    }
    proposal["use_case"] = request.use_case_description

    return proposal


@router.get("/tiers")
def get_pricing_tiers():
    """Get available pricing tiers and their parameters."""
    from quantive.government.outcome_pricing import BASIS_POINTS_TIERS, TERM_DISCOUNTS

    return {
        "tiers": BASIS_POINTS_TIERS,
        "term_discounts": {k.value: v for k, v in TERM_DISCOUNTS.items()},
        "legacy_comparison": {
            "bloomberg_terminal_per_seat": 24_000,
            "consultant_annual": 500_000,
            "internal_model_cost": 800_000,
        },
    }


@router.get("/compare-models")
def compare_pricing_models(
    total_debt: float = Query(..., gt=0, description="Total debt in USD"),
    annual_issuance: float = Query(..., ge=0, description="Annual issuance in USD"),
):
    """Compare different pricing models side-by-side."""
    from quantive.government.outcome_pricing import (
        ContractTerm,
        OutcomePricingEngine,
        PortfolioProfile,
    )

    engine = OutcomePricingEngine()
    portfolio = PortfolioProfile(
        total_debt_outstanding=total_debt,
        annual_issuance=annual_issuance,
    )

    models = {}
    for term in [
        ContractTerm.ANNUAL,
        ContractTerm.MULTI_YEAR_3,
        ContractTerm.MULTI_YEAR_5,
        ContractTerm.MULTI_YEAR_10,
    ]:
        quote = engine.calculate_quote(portfolio=portfolio, term=term)
        models[term.value] = {
            "annual_fee": quote.total_fee_annual,
            "term_fee": quote.total_fee_term,
            "roi": quote.roi_ratio,
            "savings": quote.savings_estimate.total_annual_savings_usd,
        }

    return {
        "portfolio": {
            "total_debt": total_debt,
            "annual_issuance": annual_issuance,
        },
        "models": models,
        "recommendation": "multi_year_5" if total_debt > 10_000_000_000 else "annual",
    }
