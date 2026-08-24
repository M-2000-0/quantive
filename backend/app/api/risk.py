"""Risk Probabilities API — Investment indicators and risk analysis.

Provides endpoints for:
- Risk summary with probability distributions
- Investment scenarios ("Invest $X → Get $Y back")
- VaR/CVaR at multiple confidence levels
- Risk score with factor breakdown and recommendations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DebtInstrument, Portfolio, User
from app.risk_probabilities import RiskProbabilityEngine, get_risk_summary
from app.security import get_current_user

router = APIRouter(prefix="/api/portfolios", tags=["risk"])


@router.get("/{portfolio_id}/risk-summary")
def get_portfolio_risk_summary(
    portfolio_id: str,
    time_horizon_months: int = Query(default=12, ge=1, le=60, description="Analysis horizon in months"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get comprehensive risk summary with investment indicators.

    Returns:
    - Risk score (1-10) with factor breakdown
    - Probability indicators for different outcomes
    - Concrete investment scenarios (e.g., "Invest $1M → Get $1.05M")
    - VaR/CVaR at 95% and 99% confidence
    - Actionable recommendations
    """
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id == portfolio_id,
    ).all()

    portfolio_value = sum(inst.principal_outstanding for inst in instruments)

    instruments_data = [
        {
            "id": inst.id,
            "name": inst.name,
            "instrument_type": inst.instrument_type.value if hasattr(inst.instrument_type, "value") else str(inst.instrument_type),
            "currency": inst.currency,
            "principal_outstanding": inst.principal_outstanding,
            "coupon_rate": inst.coupon_rate,
            "maturity_date": inst.maturity_date,
            "issue_date": inst.issue_date,
            "spread_bps": inst.spread_bps,
        }
        for inst in instruments
    ]

    return get_risk_summary(portfolio_value, instruments_data, time_horizon_months)


@router.get("/{portfolio_id}/investment-scenarios")
def get_investment_scenarios(
    portfolio_id: str,
    investment_amount: float = Query(default=1_000_000, gt=0, description="Investment amount in USD"),
    time_horizon_months: int = Query(default=12, ge=1, le=60),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get investment scenarios for a specific amount.

    Shows what a user can expect: "Invest $1M → Get $1.05M back with 80% confidence"

    Query params:
    - investment_amount: How much to invest (default $1M)
    - time_horizon_months: How long (default 12 months)
    """
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id == portfolio_id,
    ).all()

    instruments_data = [
        {
            "instrument_type": inst.instrument_type.value if hasattr(inst.instrument_type, "value") else str(inst.instrument_type),
            "currency": inst.currency,
            "principal_outstanding": inst.principal_outstanding,
            "coupon_rate": inst.coupon_rate,
            "maturity_date": inst.maturity_date,
            "spread_bps": inst.spread_bps,
        }
        for inst in instruments
    ]

    engine = RiskProbabilityEngine()
    scenarios = engine.calculate_investment_scenarios(
        portfolio_value=sum(i.principal_outstanding for i in instruments),
        instruments=instruments_data,
        time_horizon_months=time_horizon_months,
        investment_amounts=[investment_amount],
    )

    return {
        "investment_amount": investment_amount,
        "time_horizon_months": time_horizon_months,
        "scenarios": [s.to_dict() for s in scenarios],
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


@router.get("/{portfolio_id}/risk-score")
def get_risk_score(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the portfolio risk score with factor breakdown.

    Returns a 1-10 score with:
    - Factor contributions (maturity, spread, floating, currency, concentration)
    - Plain-English description
    - Actionable recommendations
    """
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id == portfolio_id,
    ).all()

    instruments_data = [
        {
            "instrument_type": inst.instrument_type.value if hasattr(inst.instrument_type, "value") else str(inst.instrument_type),
            "currency": inst.currency,
            "principal_outstanding": inst.principal_outstanding,
            "coupon_rate": inst.coupon_rate,
            "maturity_date": inst.maturity_date,
            "spread_bps": inst.spread_bps,
        }
        for inst in instruments
    ]

    engine = RiskProbabilityEngine()
    score = engine.calculate_risk_score(instruments_data)

    return score.to_dict()


@router.get("/{portfolio_id}/var")
def get_var_analysis(
    portfolio_id: str,
    confidence: float = Query(default=0.95, ge=0.90, le=0.999),
    time_horizon_days: int = Query(default=252, ge=1, le=2520),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Value-at-Risk and Conditional VaR analysis.

    Shows maximum expected loss at a given confidence level.
    """
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id == portfolio_id,
    ).all()

    portfolio_value = sum(inst.principal_outstanding for inst in instruments)

    instruments_data = [
        {
            "instrument_type": inst.instrument_type.value if hasattr(inst.instrument_type, "value") else str(inst.instrument_type),
            "currency": inst.currency,
            "principal_outstanding": inst.principal_outstanding,
            "coupon_rate": inst.coupon_rate,
            "maturity_date": inst.maturity_date,
            "spread_bps": inst.spread_bps,
        }
        for inst in instruments
    ]

    engine = RiskProbabilityEngine()
    var_data = engine.calculate_var(
        portfolio_value, instruments_data,
        confidence_levels=[confidence],
        time_horizon_days=time_horizon_days,
    )

    return {
        "portfolio_value": portfolio_value,
        "var_analysis": var_data,
    }
