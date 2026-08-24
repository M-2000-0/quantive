"""Portfolio analytics API endpoints."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Portfolio, User
from app.security import get_current_user

router = APIRouter(prefix="/api/portfolios", tags=["analytics"])


def _portfolio_to_quantive(portfolio: Portfolio):
    """Convert a database Portfolio to a quantive engine Portfolio for analytics."""
    from quantive.models.enums import Currency, RateType
    from quantive.models.instruments import DebtInstrument, Portfolio as QuantivePortfolio

    instruments = []
    for inst in portfolio.instruments:
        # Map instrument types
        inst_type_str = inst.instrument_type.value if hasattr(inst.instrument_type, 'value') else str(inst.instrument_type)
        rate_type = RateType.FLOATING if inst_type_str == "floating_rate_note" else RateType.FIXED

        try:
            ccy = Currency(inst.currency)
        except ValueError:
            ccy = Currency.USD

        instruments.append(DebtInstrument(
            id=inst.id,
            name=inst.name,
            currency=ccy,
            principal=inst.principal_outstanding,
            coupon=inst.coupon_rate,
            rate_type=rate_type,
            maturity_date=date.fromisoformat(inst.maturity_date),
            issue_date=date.fromisoformat(inst.issue_date),
            callable=inst.is_callable,
            liquidity=0.5,
            market_capacity=inst.principal_outstanding,
        ))

    try:
        ref_ccy = Currency.USD
    except ValueError:
        ref_ccy = Currency.USD

    return QuantivePortfolio(
        id=portfolio.id,
        name=portfolio.name,
        description=portfolio.description,
        reference_currency=ref_ccy,
        instruments=instruments,
    )


@router.get("/{portfolio_id}/analytics")
def get_portfolio_analytics(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get comprehensive portfolio analytics including duration, convexity, maturity profile, currency exposure."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from quantive.analytics import portfolio_analytics

    qp = _portfolio_to_quantive(portfolio)
    return portfolio_analytics(qp)


@router.get("/{portfolio_id}/analytics/duration")
def get_portfolio_duration(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get portfolio duration analytics (Macaulay, modified, effective)."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from quantive.analytics import portfolio_weighted_duration, instrument_durations

    qp = _portfolio_to_quantive(portfolio)
    return {
        "portfolio_duration": portfolio_weighted_duration(qp),
        "instrument_durations": instrument_durations(qp.instruments),
    }


@router.get("/{portfolio_id}/analytics/currency")
def get_portfolio_currency_exposure(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get detailed currency exposure analysis."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from quantive.analytics import currency_exposure

    qp = _portfolio_to_quantive(portfolio)
    return currency_exposure(qp.instruments)


@router.get("/{portfolio_id}/analytics/maturity")
def get_portfolio_maturity_profile(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get maturity profile and wall analysis."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from quantive.analytics import maturity_profile, maturity_wall_analysis

    qp = _portfolio_to_quantive(portfolio)
    return {
        "maturity_profile": maturity_profile(qp.instruments),
        "maturity_wall": maturity_wall_analysis(qp.instruments),
    }


@router.get("/{portfolio_id}/analytics/rate-type")
def get_portfolio_rate_type(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get fixed vs floating rate decomposition."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    from quantive.analytics import rate_type_decomposition

    qp = _portfolio_to_quantive(portfolio)
    return rate_type_decomposition(qp.instruments)
