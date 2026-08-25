"""Narrative Engine and Country Data API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OptimizationJob, Portfolio, Strategy, User
from app.security import get_current_user

router = APIRouter(prefix="/api/narrative", tags=["narrative"])


@router.get("/report/{job_id}")
def generate_narrative_report(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a board-ready narrative report from optimization results."""
    job = db.query(OptimizationJob).filter(
        OptimizationJob.id == job_id, OptimizationJob.org_id == user.org_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Optimization not found")

    portfolio = db.query(Portfolio).filter(Portfolio.id == job.portfolio_id).first()
    strategies = db.query(Strategy).filter(Strategy.job_id == job_id).order_by(Strategy.rank).all()

    instruments_data = [
        {
            "name": inst.name,
            "instrument_type": inst.instrument_type.value if hasattr(inst.instrument_type, "value") else inst.instrument_type,
            "currency": inst.currency,
            "principal_outstanding": inst.principal_outstanding,
            "coupon_rate": inst.coupon_rate,
            "maturity_date": inst.maturity_date,
            "spread_bps": inst.spread_bps,
        }
        for inst in (portfolio.instruments if portfolio else [])
    ]

    portfolio_data = {
        "name": portfolio.name if portfolio else "Unknown",
        "instruments": instruments_data,
    }

    strategies_data = [
        {
            "name": s.name,
            "description": s.description,
            "rank": s.rank,
            "metrics": s.metrics,
            "stress_test_results": s.stress_test_results,
        }
        for s in strategies
    ]

    from app.narrative_engine import generate_narrative_report as gen_report
    report = gen_report(portfolio_data, strategies_data)

    return report


# ── Country Data Endpoints ──────────────────────────────────────────────

country_router = APIRouter(prefix="/api/countries", tags=["countries"])


@country_router.get("")
def list_countries(
    region: str = Query(default=None),
    group: str = Query(default=None),
    min_rating: str = Query(default=None),
):
    """List all sovereign country profiles with optional filters."""
    from app.country_data import list_countries as list_c
    countries = list_c(region=region, group=group, min_rating=min_rating)
    return {"countries": [c.to_dict() for c in countries], "total": len(countries)}


@country_router.get("/stats")
def get_global_stats():
    """Get global sovereign debt statistics."""
    from app.country_data import get_global_stats as stats
    return stats()


@country_router.get("/{code}")
def get_country(code: str):
    """Get a specific country's sovereign debt profile."""
    from app.country_data import get_country as get_c
    country = get_c(code)
    if not country:
        raise HTTPException(status_code=404, detail=f"Country {code} not found")
    return country.to_dict()


@country_router.get("/{code}/compare")
def compare_with_peers(
    code: str,
    group: str = Query(default=None),
):
    """Compare a country with its peers."""
    from app.country_data import compare_countries, get_peer_group
    peers = get_peer_group(code, group=group)
    all_codes = [code] + [p.code for p in peers[:5]]
    return compare_countries(all_codes)


# ── What-If Playground ──────────────────────────────────────────────────

whatif_router = APIRouter(prefix="/api/whatif", tags=["what-if"])


@whatif_router.post("/analyze")
def whatif_analyze(
    adjustments: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Analyze impact of portfolio adjustments.

    Body:
    {
        "portfolio_id": "string",
        "adjustments": [
            {"instrument_id": "string", "action": "increase|decrease|remove", "amount": 5000000000},
            {"new_issuance": {"currency": "USD", "amount": 10000000000, "tenor_years": 10, "coupon_rate": 0.045}}
        ]
    }
    """
    portfolio_id = adjustments.get("portfolio_id")
    adj_list = adjustments.get("adjustments", [])

    if not portfolio_id:
        raise HTTPException(status_code=400, detail="portfolio_id is required")

    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Calculate current metrics
    instruments = list(portfolio.instruments)
    total_before = sum(i.principal_outstanding for i in instruments)
    weighted_coupon_before = sum(
        i.coupon_rate * i.principal_outstanding for i in instruments
    ) / total_before if total_before else 0

    # Apply adjustments (simulated)
    new_total = total_before
    new_coupon_weighted = sum(i.coupon_rate * i.principal_outstanding for i in instruments)
    adjustments_detail = []

    for adj in adj_list:
        action = adj.get("action")
        amount = adj.get("amount", 0)

        if action == "new_issuance":
            new_total += amount
            coupon = adj.get("coupon_rate", 0.05)
            new_coupon_weighted += coupon * amount
            adjustments_detail.append({
                "type": "new_issuance",
                "amount": amount,
                "coupon_rate": coupon,
                "tenor_years": adj.get("tenor_years", 10),
                "impact": f"Added ${amount:,.0f} at {coupon*100:.2f}%",
            })
        elif action == "increase":
            new_total += amount
            # Assume average coupon for simplicity
            avg_c = weighted_coupon_before / total_before if total_before else 0.05
            new_coupon_weighted += avg_c * amount
            adjustments_detail.append({
                "type": "increase",
                "amount": amount,
                "impact": f"Increased by ${amount:,.0f}",
            })
        elif action == "decrease":
            new_total -= amount
            avg_c = weighted_coupon_before / total_before if total_before else 0.05
            new_coupon_weighted -= avg_c * amount
            adjustments_detail.append({
                "type": "decrease",
                "amount": amount,
                "impact": f"Reduced by ${amount:,.0f}",
            })

    new_weighted_coupon = new_coupon_weighted / new_total if new_total else 0
    cost_change = new_coupon_weighted - weighted_coupon_before

    # Currency exposure after adjustments
    ccy_before = {}
    for i in instruments:
        ccy = i.currency
        ccy_before[ccy] = ccy_before.get(ccy, 0) + i.principal_outstanding

    return {
        "before": {
            "total_principal": total_before,
            "weighted_coupon_pct": weighted_coupon_before * 100,
            "annual_cost": weighted_coupon_before * total_before,
            "num_instruments": len(instruments),
            "currency_breakdown": {k: {"amount": v, "pct": v / total_before * 100} for k, v in ccy_before.items()} if total_before else {},
        },
        "after": {
            "total_principal": new_total,
            "weighted_coupon_pct": new_weighted_coupon * 100,
            "annual_cost": new_weighted_coupon * new_total,
            "num_instruments": len(instruments) + sum(1 for a in adj_list if a.get("action") == "new_issuance"),
        },
        "impact": {
            "total_change": new_total - total_before,
            "total_change_pct": (new_total - total_before) / total_before * 100 if total_before else 0,
            "coupon_change_bps": (new_weighted_coupon - weighted_coupon_before) * 10000,
            "annual_cost_change": cost_change,
            "annual_cost_change_pct": cost_change / (weighted_coupon_before * total_before) * 100 if total_before and weighted_coupon_before else 0,
        },
        "adjustments": adjustments_detail,
        "recommendation": (
            "This adjustment improves the portfolio's cost profile." if cost_change < 0 else
            "This adjustment increases financing costs but may improve other metrics." if cost_change > 0 else
            "No change in financing costs."
        ),
    }
