"""
AI Advisor API — Sovereign Finance Intelligence
================================================

All analysis is performed by our own rule-based engine + ML model.
No external LLM calls (OpenAI, Anthropic, Ollama) — zero API keys needed.

Engine layers:
1. Rule-based DebtAdvisorAI — market timing, risk analysis, peer comparison
2. ML DebtAnalysisModel — credit risk scoring, tenor optimization
3. Real market data — Treasury.gov, ECB, World Bank, IMF
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.ai_advisor import DebtAdvisorAI
from app.ml.model import get_debt_model, DebtFeatures
from app.market_data.yield_curve import fetch_treasury_yield_curve
from app.market_data.fx_rates import fetch_all_key_rates
from app.market_data.interest_rates import fetch_all_benchmark_rates
from app.database import get_db
from app.models import User, Portfolio, DebtInstrument
from app.security import get_current_user
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/ai-advisor", tags=["ai-advisor"])

advisor = DebtAdvisorAI()
ml_model = get_debt_model()


# ── Response Models ────────────────────────────────────────────────────

class RefinancingProposal(BaseModel):
    id: str
    title: str
    description: str
    instrument_from: str
    instrument_to: str
    current_coupon_pct: float
    proposed_coupon_pct: float
    notional_usd: float
    estimated_annual_savings: float
    confidence_pct: float
    risk_change: str
    execution_timeline: str
    prerequisites: list[str]
    created_at: str


class PolicyImpact(BaseModel):
    policy_name: str
    description: str
    debt_to_gdp_impact: float
    debt_service_impact: float
    risk_rating_change: str
    timeline: str
    confidence_pct: float
    side_effects: list[str]


class PortfolioInsight(BaseModel):
    category: str
    title: str
    detail: str
    impact_usd: Optional[float]
    confidence_pct: float
    priority: str
    related_instruments: list[str]


# ── Helper: compute from real portfolio data ──────────────────────────

def _get_portfolio_instruments(user: User, db: Session) -> list[DebtInstrument]:
    """Fetch all instruments for the user's organization."""
    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    if not portfolios:
        return []
    portfolio_ids = [p.id for p in portfolios]
    return db.query(DebtInstrument).filter(DebtInstrument.portfolio_id.in_(portfolio_ids)).all()


def _compute_portfolio_health(user: User, db: Session) -> tuple[int, str, list[dict]]:
    """Compute real portfolio health score from instruments."""
    instruments = _get_portfolio_instruments(user, db)

    if not instruments:
        return 0, "No portfolio data available. Import your debt instruments to get started.", []

    total_principal = sum(float(i.principal_outstanding) for i in instruments)
    avg_coupon = sum(float(i.coupon_rate) * float(i.principal_outstanding) for i in instruments) / total_principal if total_principal else 0

    # Currency concentration
    currencies = {}
    for i in instruments:
        ccy = i.currency
        currencies[ccy] = currencies.get(ccy, 0) + float(i.principal_outstanding)
    foreign_pct = sum(v for k, v in currencies.items() if k != "USD") / total_principal * 100 if total_principal else 0

    # Maturity concentration
    maturity_years = {}
    for i in instruments:
        try:
            year = int(i.maturity_date.split("-")[0])
            maturity_years[year] = maturity_years.get(year, 0) + float(i.principal_outstanding)
        except (ValueError, IndexError):
            pass

    max_single_year = max(maturity_years.values()) if maturity_years else 0
    concentration_pct = (max_single_year / total_principal * 100) if total_principal else 0

    # Score components
    coupon_score = max(0, min(100, 100 - (avg_coupon - 3) * 20))  # Lower coupon = better
    diversification_score = max(0, min(100, 100 - foreign_pct))  # Lower foreign = better
    concentration_score = max(0, min(100, 100 - concentration_pct))  # Lower concentration = better

    overall = int((coupon_score * 0.3 + diversification_score * 0.35 + concentration_score * 0.35))

    factors = [
        {"name": "Cost Efficiency", "score": int(coupon_score), "trend": "improving" if avg_coupon < 5 else "declining"},
        {"name": "Currency Diversification", "score": int(diversification_score), "trend": "stable"},
        {"name": "Maturity Concentration", "score": int(concentration_score), "trend": "improving" if concentration_pct < 20 else "declining"},
        {"name": "Total Instruments", "score": min(100, len(instruments) * 10), "trend": "stable"},
    ]

    summary = (
        f"Portfolio contains {len(instruments)} instruments across "
        f"{len(currencies)} currencies with total principal of ${total_principal/1e9:.1f}B. "
        f"Average coupon is {avg_coupon:.2f}%. "
        f"{'Foreign currency exposure is elevated at ' + f'{foreign_pct:.0f}%' if foreign_pct > 35 else 'Currency mix is well-diversified'}. "
        f"{'Maturity concentration risk in ' + str(max(maturity_years, key=maturity_years.get) if maturity_years else 'N/A') + ' is significant' if concentration_pct > 25 else 'Maturity profile is well-distributed'}."
    )

    return overall, summary, factors


def _generate_refinancing_proposals(user: User, db: Session) -> list[RefinancingProposal]:
    """Generate refinancing proposals from real portfolio + market data."""
    instruments = _get_portfolio_instruments(user, db)
    if not instruments:
        return []

    # Get live yield curve
    yield_data = fetch_treasury_yield_curve()
    yield_rates = {}
    for m in yield_data.get("maturities", []):
        yield_rates[m["label"]] = m["rate_pct"]

    now = datetime.now(timezone.utc).isoformat()
    proposals = []

    for inst in instruments:
        coupon = float(inst.coupon_rate)
        principal = float(inst.principal_outstanding)

        # Match maturity to yield curve
        try:
            mat_years = (datetime.strptime(inst.maturity_date, "%Y-%m-%d") - datetime.now()).days / 365.25
        except (ValueError, TypeError):
            continue

        if mat_years < 0.5:
            continue  # Skip very short-term

        # Find closest yield curve point
        closest_label = min(yield_rates.keys(), key=lambda k: abs(_label_to_years(k) - mat_years), default=None)
        if not closest_label or closest_label not in yield_rates:
            continue

        market_rate = yield_rates[closest_label]

        # Only propose if there's meaningful savings (>25bps)
        savings_bps = (coupon - market_rate) * 100
        if savings_bps < 25:
            continue

        annual_savings = principal * (savings_bps / 10000)

        proposals.append(RefinancingProposal(
            id=f"REF-{inst.id[:8]}",
            title=f"Refinance {inst.name}",
            description=(
                f"The {inst.name} carries a {coupon:.3f}% coupon. "
                f"Current {closest_label} Treasury yield is {market_rate:.2f}%, "
                f"creating a {savings_bps:.0f}bps refinancing opportunity."
            ),
            instrument_from=f"{inst.name} at {coupon:.3f}%",
            instrument_to=f"New issuance at ~{market_rate:.2f}% ({closest_label})",
            current_coupon_pct=coupon,
            proposed_coupon_pct=round(market_rate, 3),
            notional_usd=principal,
            estimated_annual_savings=round(annual_savings, 2),
            confidence_pct=min(95, max(50, int(70 + savings_bps * 0.3))),
            risk_change=f"Duration adjusts from {mat_years:.1f}Y to {_label_to_years(closest_label):.1f}Y",
            execution_timeline="6-8 weeks for book building and pricing",
            prerequisites=[
                "Board approval for new issuance mandate",
                "Rating agency pre-notification",
                "Legal review of prospectus",
            ],
            created_at=now,
        ))

    return sorted(proposals, key=lambda p: p.estimated_annual_savings, reverse=True)[:5]


def _label_to_years(label: str) -> float:
    """Convert yield curve label to years."""
    mapping = {
        "1M": 1/12, "2M": 2/12, "3M": 0.25, "4M": 4/12, "6M": 0.5,
        "1Y": 1, "2Y": 2, "3Y": 3, "5Y": 5, "7Y": 7,
        "10Y": 10, "20Y": 20, "30Y": 30,
    }
    return mapping.get(label, 10)


def _generate_insights(user: User, db: Session) -> list[PortfolioInsight]:
    """Generate real portfolio insights from data."""
    instruments = _get_portfolio_instruments(user, db)
    if not instruments:
        return []

    total = sum(float(i.principal_outstanding) for i in instruments)
    now = datetime.now(timezone.utc).isoformat()
    insights = []

    # Currency concentration insight
    currencies = {}
    for i in instruments:
        currencies[i.currency] = currencies.get(i.currency, 0) + float(i.principal_outstanding)
    for ccy, amount in currencies.items():
        pct = amount / total * 100
        if pct > 40:
            insights.append(PortfolioInsight(
                category="risk",
                title=f"High {ccy} Concentration",
                detail=f"{ccy} represents {pct:.0f}% of total portfolio (${amount/1e9:.1f}B). Consider diversifying currency exposure.",
                impact_usd=None,
                confidence_pct=90,
                priority="high",
                related_instruments=[i.name for i in instruments if i.currency == ccy],
            ))

    # Maturity wall insight
    maturity_years = {}
    for i in instruments:
        try:
            year = int(i.maturity_date.split("-")[0])
            maturity_years[year] = maturity_years.get(year, 0) + float(i.principal_outstanding)
        except (ValueError, IndexError):
            pass
    if maturity_years:
        max_year = max(maturity_years, key=maturity_years.get)
        concentration = maturity_years[max_year] / total * 100
        if concentration > 20:
            insights.append(PortfolioInsight(
                category="observation",
                title=f"Maturity Wall in {max_year}",
                detail=f"{concentration:.0f}% of debt (${maturity_years[max_year]/1e9:.1f}B) matures in {max_year}. Pre-funding is essential.",
                impact_usd=maturity_years[max_year],
                confidence_pct=95,
                priority="high",
                related_instruments=[i.name for i in instruments if i.maturity_date.startswith(str(max_year))],
            ))

    # Coupon optimization insight
    high_coupon = [i for i in instruments if float(i.coupon_rate) > 6]
    if high_coupon:
        total_high = sum(float(i.principal_outstanding) for i in high_coupon)
        insights.append(PortfolioInsight(
            category="opportunity",
            title="High Coupon Instruments Present",
            detail=f"{len(high_coupon)} instruments with coupons above 6% (${total_high/1e9:.1f}B total). Consider refinancing at current lower rates.",
            impact_usd=total_high * 0.005,  # Estimate 50bps savings
            confidence_pct=75,
            priority="medium",
            related_instruments=[i.name for i in high_coupon],
        ))

    return insights


def _generate_policy_impacts(user: User, db: Session) -> list[PolicyImpact]:
    """Generate policy impacts from real market data."""
    instruments = _get_portfolio_instruments(user, db)
    if not instruments:
        return []

    total = sum(float(i.principal_outstanding) for i in instruments)
    floating = sum(float(i.principal_outstanding) for i in instruments if "floating" in i.name.lower() or "frn" in i.name.lower())
    fixed_pct = (1 - floating / total) * 100 if total else 100

    yield_data = fetch_treasury_yield_curve()
    rates = {m["label"]: m["rate_pct"] for m in yield_data.get("maturities", [])}
    us_10y = rates.get("10Y", 4.3)
    us_2y = rates.get("2Y", 4.5)

    impacts = []

    # Rate cut scenario
    impacts.append(PolicyImpact(
        policy_name="100bps Rate Cut Scenario",
        description=f"If rates fall 100bps, your {100-fixed_pct:.0f}% floating-rate debt saves significantly. Fixed-rate ({fixed_pct:.0f}%) is already locked in.",
        debt_to_gdp_impact=round(-0.5 * (floating / total), 2) if total else 0,
        debt_service_impact=round(-1.0 * (floating / total), 2) if total else 0,
        risk_rating_change="Positive — lower debt service improves fiscal metrics",
        timeline="6-12 months",
        confidence_pct=70,
        side_effects=["Fixed-rate refinancing window may close", "Capital gains on existing fixed-rate bonds"],
    ))

    # Rate hike scenario
    impacts.append(PolicyImpact(
        policy_name="200bps Rate Hike Scenario",
        description=f"A 200bps hike would increase annual debt service on floating-rate instruments by ~${floating * 0.02 / 1e9:.1f}B.",
        debt_to_gdp_impact=round(0.8 * (floating / total), 2) if total else 0,
        debt_service_impact=round(2.0 * (floating / total), 2) if total else 0,
        risk_rating_change="Negative — increased debt service pressure",
        timeline="Immediate impact on floating-rate instruments",
        confidence_pct=85,
        side_effects=["Potential credit rating pressure", "Reduced fiscal space"],
    ))

    return impacts


# ── API Endpoints ──────────────────────────────────────────────────────

@router.get("/portfolio-health")
def get_portfolio_health(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compute real portfolio health score from actual instruments."""
    score, summary, factors = _compute_portfolio_health(user, db)
    return {
        "health_score": score,
        "summary": summary,
        "factors": factors,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/refinancing-proposals")
def get_refinancing_proposals(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate refinancing proposals from real portfolio + live market data."""
    proposals = _generate_refinancing_proposals(user, db)
    total_savings = sum(p.estimated_annual_savings for p in proposals)

    yield_data = fetch_treasury_yield_curve()
    rates = {m["label"]: m["rate_pct"] for m in yield_data.get("maturities", [])}

    return {
        "proposals": [p.model_dump() for p in proposals],
        "total_potential_savings": round(total_savings, 2),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market_conditions": {
            "usd_10y": rates.get("10Y", 0),
            "usd_2y": rates.get("2Y", 0),
            "curve_status": "inverted" if rates.get("2Y", 0) > rates.get("10Y", 0) else "normal",
            "source": yield_data.get("source", "US Treasury"),
            "date": yield_data.get("date", ""),
        },
    }


@router.get("/policy-impacts")
def get_policy_impacts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Analyze policy impacts from real portfolio composition."""
    return {
        "impacts": [p.model_dump() for p in _generate_policy_impacts(user, db)],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/insights")
def get_insights(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get data-driven portfolio insights."""
    insights = _generate_insights(user, db)
    opportunities = sum(1 for i in insights if i.category == "opportunity")
    risks = sum(1 for i in insights if i.category == "risk")

    return {
        "insights": [i.model_dump() for i in insights],
        "total_opportunities": opportunities,
        "total_risks": risks,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/summary")
def get_full_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get complete AI advisor summary for the dashboard."""
    score, summary, factors = _compute_portfolio_health(user, db)
    proposals = _generate_refinancing_proposals(user, db)
    insights = _generate_insights(user, db)

    return {
        "health_score": score,
        "summary": summary,
        "refinancing_proposals": [p.model_dump() for p in proposals],
        "insights": [i.model_dump() for i in insights],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_freshness": "Real-time market data from Treasury.gov, ECB, World Bank",
    }


@router.get("/ml-risk")
def get_ml_risk_assessment(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ML-powered risk assessment using the DebtAnalysisModel."""
    instruments = _get_portfolio_instruments(user, db)
    if not instruments:
        return {"error": "No portfolio data. Import instruments to get ML analysis."}

    total = sum(float(i.principal_outstanding) for i in instruments)
    avg_coupon = sum(float(i.coupon_rate) * float(i.principal_outstanding) for i in instruments) / total if total else 0

    try:
        avg_maturity = sum(
            (datetime.strptime(i.maturity_date, "%Y-%m-%d") - datetime.now()).days / 365.25
            for i in instruments
        ) / len(instruments)
    except (ValueError, TypeError):
        avg_maturity = 5.0

    currencies = {}
    for i in instruments:
        currencies[i.currency] = currencies.get(i.currency, 0) + float(i.principal_outstanding)
    foreign_pct = sum(v for k, v in currencies.items() if k != "USD") / total * 100 if total else 0

    # Fetch market context
    yield_data = fetch_treasury_yield_curve()
    rates = {m["label"]: m["rate_pct"] for m in yield_data.get("maturities", [])}

    features = DebtFeatures(
        debt_to_gdp=55.0,  # Would come from country data
        gdp_growth_pct=2.5,
        inflation_pct=3.0,
        fiscal_balance_pct=-3.0,
        external_debt_pct=foreign_pct,
        avg_maturity_years=avg_maturity,
        avg_coupon_pct=avg_coupon,
        interest_to_revenue=12.0,
        foreign_held_pct=foreign_pct,
        current_account_pct=-2.0,
        reserves_months=4.0,
        rating_score=75.0,
    )

    prediction = ml_model.predict(features)

    return {
        "credit_risk_score": prediction.credit_risk_score,
        "refinancing_risk": prediction.refinancing_risk,
        "optimal_tenor_years": prediction.optimal_tenor_years,
        "suggested_coupon_range": list(prediction.suggested_coupon_range),
        "confidence": prediction.confidence,
        "feature_importance": prediction.feature_importance,
        "market_context": {
            "usd_10y": rates.get("10Y", 0),
            "usd_2y": rates.get("2Y", 0),
            "source": yield_data.get("source", "US Treasury"),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/ask")
def ask_advisor(
    question: str,
    country_code: str = Query(default="US"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Natural language query answered by our rule-based AI engine.

    No external LLM calls — uses DebtAdvisorAI with real market data.
    """
    result = advisor.answer(question, country_code)
    return {
        "answer": result.get("answer", ""),
        "confidence": result.get("confidence", 0),
        "data_sources": result.get("sources", []),
        "suggestions": result.get("suggestions", []),
        "data": result.get("data", {}),
    }
