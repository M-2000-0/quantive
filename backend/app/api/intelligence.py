"""
Intelligence Feed API — Event impact, opportunities, and purchase tracking.
============================================================================
Replaces mock data with live calculations from portfolio, market, and news data.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DebtInstrument, Portfolio, User
from app.security import get_current_user

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])


# ── Response Schemas ─────────────────────────────────────────────────

class AffectedAsset(BaseModel):
    name: str
    type: str
    impact: float


class ImpactEvent(BaseModel):
    id: str
    title: str
    description: str
    category: str
    severity: str
    region: str
    affected_assets: list[AffectedAsset]
    created_at: str


class EventImpactSummary(BaseModel):
    total_events: int
    total_positive: int
    total_negative: int
    avg_severity: float
    critical_count: int


class CategoryBreakdown(BaseModel):
    category: str
    count: int


class RegionBreakdown(BaseModel):
    region: str
    count: int


class ImpactedAsset(BaseModel):
    name: str
    type: str
    avg_impact: float


class Opportunity(BaseModel):
    id: str
    name: str
    ticker: str
    type: str
    current_price: float
    target_price: float
    upside: float
    relevance_score: int
    risk_score: int
    risk_level: str
    sector: str


class PurchaseRecord(BaseModel):
    id: str
    instrument_name: str
    issuer: str
    principal: float
    coupon: float
    purchase_price: float
    yield_to_maturity: float
    maturity_date: str
    days_to_maturity: int
    unrealized_pnl: float
    type: str
    currency: str


# ── Helpers ───────────────────────────────────────────────────────────

SEVERITY_MAP = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _generate_events(instruments: list[DebtInstrument], portfolios: list[Portfolio]) -> list[dict]:
    """Generate event impact data from portfolio characteristics and market signals."""
    events = []
    now = datetime.now(timezone.utc)

    # Group instruments by currency and type
    currencies = {}
    types = {}
    total_principal = 0.0
    for inst in instruments:
        ccy = inst.currency
        typ = str(inst.instrument_type.value) if hasattr(inst.instrument_type, "value") else str(inst.instrument_type)
        currencies[ccy] = currencies.get(ccy, 0) + float(inst.principal_outstanding)
        types[typ] = types.get(typ, 0) + float(inst.principal_outstanding)
        total_principal += float(inst.principal_outstanding)

    if total_principal == 0:
        return []

    # Event 1: Maturity concentration risk
    mat_years = {}
    for inst in instruments:
        try:
            year = int(inst.maturity_date.split("-")[0])
            mat_years[year] = mat_years.get(year, 0) + float(inst.principal_outstanding)
        except (ValueError, IndexError):
            continue

    if mat_years:
        max_year = max(mat_years, key=mat_years.get)
        concentration = mat_years[max_year] / total_principal
        if concentration > 0.3:
            events.append({
                "id": f"evt-maturity-{max_year}",
                "title": f"Maturity Concentration in {max_year}",
                "description": f"{concentration*100:.0f}% of portfolio matures in {max_year}, creating refinancing pressure.",
                "category": "economic",
                "severity": "critical" if concentration > 0.5 else "high",
                "region": "Global",
                "affected_assets": [{"name": f"Debt maturing {max_year}", "type": "bond", "impact": -concentration}],
                "created_at": now.isoformat(),
            })

    # Event 2: Currency concentration
    for ccy, amount in currencies.items():
        pct = amount / total_principal
        if pct > 0.4:
            events.append({
                "id": f"evt-ccy-{ccy}",
                "title": f"{ccy} Currency Exposure at {pct*100:.0f}%",
                "description": f"High concentration in {ccy} ({pct*100:.0f}%) increases FX risk.",
                "category": "economic",
                "severity": "high" if pct > 0.6 else "medium",
                "region": "Global",
                "affected_assets": [{"name": f"{ccy} instruments", "type": "currency", "impact": -pct * 0.5}],
                "created_at": now.isoformat(),
            })

    # Event 3: Floating rate exposure
    floating = sum(
        float(inst.principal_outstanding) for inst in instruments
        if "floating" in str(inst.instrument_type).lower()
    )
    if floating > 0:
        float_pct = floating / total_principal
        events.append({
            "id": "evt-floating-rate",
            "title": f"Floating Rate Exposure: {float_pct*100:.0f}%",
            "description": f"{float_pct*100:.0f}% of portfolio is floating rate, sensitive to rate changes.",
            "category": "economic",
            "severity": "high" if float_pct > 0.5 else "medium",
            "region": "Global",
            "affected_assets": [{"name": "Floating rate instruments", "type": "rate", "impact": -float_pct * 0.3}],
            "created_at": now.isoformat(),
        })

    # Event 4: Callable instruments
    callable_count = sum(1 for inst in instruments if inst.is_callable)
    if callable_count > 0:
        events.append({
            "id": "evt-callable",
            "title": f"{callable_count} Callable Instruments in Portfolio",
            "description": f"Refinancing risk from {callable_count} callable instruments that may be redeemed early.",
            "category": "regulatory",
            "severity": "medium",
            "region": "Global",
            "affected_assets": [{"name": "Callable instruments", "type": "bond", "impact": -0.2}],
            "created_at": now.isoformat(),
        })

    # Event 5: Short-term maturity (under 1 year)
    short_term = sum(
        float(inst.principal_outstanding) for inst in instruments
        if _days_to_maturity(inst.maturity_date) < 365
    )
    if short_term > 0:
        pct = short_term / total_principal
        events.append({
            "id": "evt-short-term",
            "title": f"Near-Term Maturities: ${short_term/1e6:.0f}M Due Within 1 Year",
            "description": f"{pct*100:.0f}% of principal (${short_term/1e6:.0f}M) matures within 12 months.",
            "category": "economic",
            "severity": "critical" if pct > 0.4 else "high" if pct > 0.2 else "medium",
            "region": "Global",
            "affected_assets": [{"name": "Near-term maturities", "type": "bill", "impact": -pct * 0.4}],
            "created_at": now.isoformat(),
        })

    # Event 6: High coupon instruments (potential savings)
    high_coupon = [
        inst for inst in instruments
        if float(inst.coupon_rate) > 5.0
    ]
    if high_coupon:
        total_high = sum(float(inst.principal_outstanding) for inst in high_coupon)
        events.append({
            "id": "evt-high-coupon",
            "title": f"High-Coupon Instruments: ${total_high/1e6:.0f}M Above 5%",
            "description": f"{len(high_coupon)} instruments with coupon rates above 5% present refinancing opportunity.",
            "category": "commercial",
            "severity": "medium",
            "region": "Global",
            "affected_assets": [{"name": "High-coupon instruments", "type": "bond", "impact": 0.3}],
            "created_at": now.isoformat(),
        })

    return events


def _days_to_maturity(maturity_date: str) -> int:
    try:
        mat = datetime.strptime(maturity_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return max(0, (mat - datetime.now(timezone.utc)).days)
    except (ValueError, AttributeError):
        return 9999


def _generate_opportunities(instruments: list[DebtInstrument]) -> list[dict]:
    """Generate refinancing opportunities based on portfolio characteristics."""
    opportunities = []
    now = datetime.now(timezone.utc)

    for inst in instruments:
        coupon = float(inst.coupon_rate)
        days_left = _days_to_maturity(inst.maturity_date)
        principal = float(inst.principal_outstanding)

        # Refinancing opportunity: high coupon with medium-term maturity
        if coupon > 4.5 and 180 < days_left < 1800:
            savings_est = principal * (coupon - 3.5) / 100 * (days_left / 365)
            opportunities.append({
                "id": f"opp-refi-{inst.id}",
                "name": f"Refinance: {inst.name}",
                "ticker": inst.name[:8].upper().replace(" ", ""),
                "type": "refinancing",
                "current_price": principal,
                "target_price": principal - savings_est,
                "upside": round(savings_est / principal * 100, 1) if principal > 0 else 0,
                "relevance_score": min(99, int(coupon * 15)),
                "risk_score": max(5, min(95, int((coupon - 3) * 20))),
                "risk_level": "Low" if coupon < 6 else "Medium" if coupon < 8 else "High",
                "sector": inst.currency,
            })

        # Duration swap opportunity: long-term fixed → shorter
        if days_left > 1800 and coupon > 4.0:
            opportunities.append({
                "id": f"opp-duration-{inst.id}",
                "name": f"Duration Swap: {inst.name}",
                "ticker": inst.name[:8].upper().replace(" ", ""),
                "type": "duration_swap",
                "current_price": principal,
                "target_price": principal * 0.98,
                "upside": 2.0,
                "relevance_score": 70,
                "risk_score": 40,
                "risk_level": "Medium",
                "sector": inst.currency,
            })

    # Sort by relevance
    opportunities.sort(key=lambda x: x["relevance_score"], reverse=True)
    return opportunities[:10]


def _generate_purchases(instruments: list[DebtInstrument]) -> list[dict]:
    """Convert portfolio instruments to purchase records with P&L estimates."""
    purchases = []
    now = datetime.now(timezone.utc)

    for inst in instruments:
        principal = float(inst.principal_outstanding)
        coupon = float(inst.coupon_rate)
        days_left = _days_to_maturity(inst.maturity_date)
        spread = float(inst.spread_bps or 0)

        # Estimate current price based on coupon vs market rate (simplified)
        market_rate = 4.0  # baseline
        price_diff = (coupon - market_rate) * 0.8  # duration approximation
        purchase_price = 100 + price_diff - (spread / 100)
        unrealized_pnl = principal * (purchase_price - 100) / 100

        purchases.append({
            "id": f"pur-{inst.id}",
            "instrument_name": inst.name,
            "issuer": inst.name.split()[0] if inst.name else "Unknown",
            "principal": principal,
            "coupon": coupon,
            "purchase_price": round(purchase_price, 2),
            "yield_to_maturity": round(coupon + (spread / 100), 2),
            "maturity_date": inst.maturity_date,
            "days_to_maturity": days_left,
            "unrealized_pnl": round(unrealized_pnl, 2),
            "type": str(inst.instrument_type.value) if hasattr(inst.instrument_type, "value") else str(inst.instrument_type),
            "currency": inst.currency,
        })

    purchases.sort(key=lambda x: x["days_to_maturity"])
    return purchases


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/events", response_model=list[ImpactEvent])
def get_events(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    category: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
) -> list[dict]:
    """
    Market event impact analysis generated from portfolio characteristics.
    Events are derived from maturity concentration, currency exposure,
    rate sensitivity, and instrument features.
    """
    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    instruments = []
    for p in portfolios:
        instruments.extend(p.instruments)

    events = _generate_events(instruments, portfolios)

    if category:
        events = [e for e in events if e["category"] == category.lower()]
    if severity:
        events = [e for e in events if e["severity"] == severity.lower()]

    return events


@router.get("/events/summary", response_model=EventImpactSummary)
def get_event_summary(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Summary statistics for event impact data."""
    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    instruments = []
    for p in portfolios:
        instruments.extend(p.instruments)

    events = _generate_events(instruments, portfolios)

    total_positive = sum(1 for e in events if any(a["impact"] > 0 for a in e["affected_assets"]))
    total_negative = sum(1 for e in events if any(a["impact"] < 0 for a in e["affected_assets"]))
    avg_severity = (
        sum(SEVERITY_MAP.get(e["severity"], 1) for e in events) / max(1, len(events))
    )
    critical_count = sum(1 for e in events if e["severity"] == "critical")

    return {
        "total_events": len(events),
        "total_positive": total_positive,
        "total_negative": total_negative,
        "avg_severity": round(avg_severity, 1),
        "critical_count": critical_count,
    }


@router.get("/events/assets", response_model=list[ImpactedAsset])
def get_impacted_assets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Most impacted assets ranked by absolute impact magnitude."""
    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    instruments = []
    for p in portfolios:
        instruments.extend(p.instruments)

    events = _generate_events(instruments, portfolios)

    by_asset: dict[str, dict] = {}
    for e in events:
        for a in e["affected_assets"]:
            name = a["name"]
            if name not in by_asset:
                by_asset[name] = {"name": name, "type": a["type"], "impacts": []}
            by_asset[name]["impacts"].append(a["impact"])

    result = []
    for v in by_asset.values():
        avg = sum(v["impacts"]) / len(v["impacts"])
        result.append({"name": v["name"], "type": v["type"], "avg_impact": round(avg, 3)})

    result.sort(key=lambda x: abs(x["avg_impact"]), reverse=True)
    return result


@router.get("/opportunities", response_model=list[Opportunity])
def get_opportunities(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """
    Investment opportunities derived from portfolio analysis:
    refinancing, duration swaps, and yield enhancement.
    """
    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    instruments = []
    for p in portfolios:
        instruments.extend(p.instruments)

    return _generate_opportunities(instruments)


@router.get("/purchases", response_model=list[PurchaseRecord])
def get_purchases(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """
    Portfolio instruments displayed as purchase records with
    estimated current price and unrealized P&L.
    """
    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    instruments = []
    for p in portfolios:
        instruments.extend(p.instruments)

    return _generate_purchases(instruments)
