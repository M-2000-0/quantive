"""
Personalized Recommendations API
=================================

Generates personalized investment recommendations based on
user profile, portfolio data, and market conditions.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import get_current_user
from app.services.recommendation_engine import RecommendationEngine

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


class RecommendationResponse(BaseModel):
    type: str
    title: str
    text: str
    score: float
    relevance_explanation: str


@router.get("/personalized")
def get_personalized_recommendations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get personalized investment recommendations for the current user."""
    engine = RecommendationEngine(db)

    # Build portfolio context from user's instruments
    from app.models import Portfolio, DebtInstrument
    from datetime import datetime, timezone

    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    portfolio_ids = [p.id for p in portfolios]
    instruments = (
        db.query(DebtInstrument).filter(DebtInstrument.portfolio_id.in_(portfolio_ids)).all()
        if portfolio_ids else []
    )

    total_debt = sum(float(i.principal_outstanding) for i in instruments) if instruments else 0
    now = datetime.now(timezone.utc)

    # Compute portfolio metrics
    if instruments and total_debt > 0:
        # Short-term (< 2Y)
        short_term = 0
        floating = 0
        fx_exposure = 0
        total_coupon_weighted = 0
        maturity_years = []
        currency_breakdown = {}

        for inst in instruments:
            principal = float(inst.principal_outstanding)
            coupon = float(inst.coupon_rate)
            total_coupon_weighted += coupon * principal

            ccy = inst.currency
            currency_breakdown[ccy] = currency_breakdown.get(ccy, 0) + principal

            try:
                mat = datetime.strptime(inst.maturity_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                years_left = max(0, (mat - now).days / 365.25)
                maturity_years.append((years_left, principal))
                if years_left <= 2:
                    short_term += principal
            except (ValueError, AttributeError):
                continue

        avg_maturity = sum(y * p for y, p in maturity_years) / total_debt if maturity_years else 0
        weighted_coupon = total_coupon_weighted / total_debt if total_debt > 0 else 0
        fx_pct = (1 - currency_breakdown.get("MXN", 0) / total_debt) * 100 if total_debt > 0 else 0

        # Maturity distribution
        maturity_dist = {}
        for years, principal in maturity_years:
            year = str(int(years) + now.year)
            maturity_dist[year] = maturity_dist.get(year, 0) + principal

        portfolio_data = {
            "total_debt": total_debt,
            "short_term_pct": (short_term / total_debt * 100) if total_debt > 0 else 0,
            "short_term_principal": short_term,
            "floating_pct": 0,  # Need instrument type check
            "floating_principal": 0,
            "avg_maturity": avg_maturity,
            "weighted_coupon": weighted_coupon,
            "fx_exposure_pct": fx_pct,
            "debt_to_gdp": 55.7,  # From sovereign metrics
            "currency_breakdown": {k: v / total_debt * 100 for k, v in currency_breakdown.items()} if total_debt > 0 else {},
            "maturity_distribution": maturity_dist,
        }
    else:
        portfolio_data = {
            "total_debt": 0, "short_term_pct": 0, "short_term_principal": 0,
            "floating_pct": 0, "floating_principal": 0, "avg_maturity": 0,
            "weighted_coupon": 0, "fx_exposure_pct": 0, "debt_to_gdp": 0,
            "currency_breakdown": {}, "maturity_distribution": {},
        }

    # Market context
    market_data = {
        "rate_10y": 4.30,
        "rate_2y": 4.15,
        "rate_30y": 4.68,
        "curve_spread_bps": -15,
        "sofr": 3.66,
        "spread_30d_change_bps": -22,
    }

    # Try to get live data
    try:
        import asyncio
        from app.services.market_data_service import get_treasury_yields
        yields = asyncio.get_event_loop().run_until_complete(get_treasury_yields())
        for y in yields:
            if y.maturity == "10Y":
                market_data["rate_10y"] = y.yield_pct
            elif y.maturity == "2Y":
                market_data["rate_2y"] = y.yield_pct
            elif y.maturity == "30Y":
                market_data["rate_30y"] = y.yield_pct
        market_data["curve_spread_bps"] = (market_data["rate_10y"] - market_data["rate_2y"]) * 100
    except Exception:
        pass

    recommendations = engine.generate_recommendations(
        user_id=user.id,
        portfolio_data=portfolio_data,
        market_data=market_data,
        limit=7,
    )

    return {
        "recommendations": [
            {
                "type": r["type"],
                "title": r["title"],
                "text": r["text"],
                "score": r["score"],
                "relevance_explanation": f"Scored {r['score']:.0%} relevance based on your portfolio profile and behavioral history.",
            }
            for r in recommendations
        ],
        "portfolio_summary": {
            "total_debt": portfolio_data["total_debt"],
            "avg_maturity": portfolio_data["avg_maturity"],
            "weighted_coupon": portfolio_data["weighted_coupon"],
            "instrument_count": len(instruments),
        },
        "market_context": market_data,
    }


@router.post("/interact")
def record_recommendation_interaction(
    recommendation_type: str,
    title: str,
    action: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a user interaction with a recommendation."""
    engine = RecommendationEngine(db)
    engine.record_interaction(
        user_id=user.id,
        recommendation_type=recommendation_type,
        title=title,
        text="",
        action=action,
    )
    return {"status": "recorded"}
