"""API endpoints for Maturity Ladder, Cash Flow Projection, and Refinancing Recommendations."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DebtInstrument, Portfolio, User
from app.security import get_current_user

router = APIRouter(prefix="/api/maturity", tags=["maturity-ladder"])


@router.get("/ladder/{portfolio_id}")
def get_maturity_ladder(
    portfolio_id: str,
    horizon_years: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Build the maturity ladder for a portfolio."""
    from app.maturity_ladder import MaturityLadderEngine

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

    engine = MaturityLadderEngine(instruments_data, horizon_years=horizon_years)
    return engine.build_ladder()


@router.get("/cashflow/{portfolio_id}")
def get_cash_flow_projection(
    portfolio_id: str,
    horizon_years: int = 15,
    annual_budget: float = 0.0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Project annual cash flows for a portfolio."""
    from app.maturity_ladder import CashFlowProjectionEngine

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

    engine = CashFlowProjectionEngine(instruments_data, horizon_years=horizon_years, annual_budget=annual_budget)
    return engine.project()


@router.get("/recommendations/{portfolio_id}")
def get_refinancing_recommendations(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get refinancing recommendations based on maturity and cash flow analysis."""
    from app.maturity_ladder import (
        CashFlowProjectionEngine,
        MaturityLadderEngine,
        generate_refinancing_recommendations,
    )

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

    ladder = MaturityLadderEngine(instruments_data).build_ladder()
    cashflow = CashFlowProjectionEngine(instruments_data).project()
    recommendations = generate_refinancing_recommendations(ladder, cashflow)

    return {
        "portfolio_id": portfolio_id,
        "maturity_ladder_summary": {
            "total_debt": ladder["total_debt"],
            "smoothness_score": ladder["smoothness_score"],
            "walls": ladder["maturity_walls"],
            "avg_years_to_maturity": ladder["average_years_to_maturity"],
        },
        "cashflow_summary": cashflow["summary"],
        "recommendations": recommendations,
    }


@router.post("/analyze/{portfolio_id}")
def full_maturity_analysis(
    portfolio_id: str,
    horizon_years: int = 20,
    annual_budget: float = 0.0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full maturity analysis: ladder + cash flow + recommendations in one call."""
    from app.maturity_ladder import (
        CashFlowProjectionEngine,
        MaturityLadderEngine,
        generate_refinancing_recommendations,
    )

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

    ladder = MaturityLadderEngine(instruments_data, horizon_years=horizon_years).build_ladder()
    cashflow = CashFlowProjectionEngine(instruments_data, horizon_years=horizon_years, annual_budget=annual_budget).project()
    recommendations = generate_refinancing_recommendations(ladder, cashflow)

    return {
        "maturity_ladder": ladder,
        "cash_flow_projection": cashflow,
        "recommendations": recommendations,
    }
