"""
Portfolio Detail API — Rich portfolio view with computed metrics.
================================================================

Provides the data needed by the portfolio detail page: instrument table,
maturity ladder, summary stats, and currency breakdown.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import DebtInstrument, Portfolio, User
from app.security import get_current_user

router = APIRouter(prefix="/api/portfolio-detail", tags=["portfolio-detail"])


# ── Response Schemas ─────────────────────────────────────────────────

class InstrumentRow(BaseModel):
    id: str
    name: str
    instrument_type: str
    currency: str
    principal_outstanding: float
    coupon_rate: float
    maturity_date: str
    issue_date: str
    spread_bps: float
    years_to_maturity: float
    is_callable: bool


class CurrencyBreakdown(BaseModel):
    currency: str
    total_principal: float
    percentage: float
    instrument_count: int


class PortfolioSummary(BaseModel):
    total_principal: float
    instrument_count: int
    currency_count: int
    avg_maturity_years: float
    weighted_coupon_pct: float
    weighted_spread_bps: float
    callable_count: int


class PortfolioDetailResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    summary: PortfolioSummary
    instruments: list[InstrumentRow]
    maturity_distribution: list[dict]
    currency_breakdown: list[CurrencyBreakdown]


# ── Helpers ───────────────────────────────────────────────────────────

def _compute_summary(instruments: list[DebtInstrument]) -> PortfolioSummary:
    """Compute aggregated portfolio statistics."""
    if not instruments:
        return PortfolioSummary(
            total_principal=0, instrument_count=0, currency_count=0,
            avg_maturity_years=0, weighted_coupon_pct=0,
            weighted_spread_bps=0, callable_count=0,
        )

    now = datetime.now(timezone.utc)
    total_principal = 0.0
    weighted_coupon = 0.0
    weighted_spread = 0.0
    total_years = 0.0
    callable_count = 0

    for inst in instruments:
        principal = float(inst.principal_outstanding)
        total_principal += principal
        weighted_coupon += float(inst.coupon_rate) * principal
        weighted_spread += float(inst.spread_bps or 0) * principal
        callable_count += 1 if inst.is_callable else 0

        try:
            mat_date = datetime.strptime(inst.maturity_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            years_left = max(0, (mat_date - now).days / 365.25)
            total_years += years_left * principal
        except (ValueError, AttributeError):
            continue

    return PortfolioSummary(
        total_principal=round(total_principal, 2),
        instrument_count=len(instruments),
        currency_count=len({i.currency for i in instruments}),
        avg_maturity_years=round(total_years / total_principal, 2) if total_principal else 0,
        weighted_coupon_pct=round((weighted_coupon / total_principal) * 100, 3) if total_principal else 0,
        weighted_spread_bps=round(weighted_spread / total_principal, 1) if total_principal else 0,
        callable_count=callable_count,
    )


def _build_maturity_distribution(instruments: list[DebtInstrument]) -> list[dict]:
    """Group instruments by maturity year, sorted chronologically."""
    buckets: dict[int, dict] = {}
    for inst in instruments:
        try:
            year = int(inst.maturity_date.split("-")[0])
        except (ValueError, IndexError):
            continue
        if year not in buckets:
            buckets[year] = {"year": year, "count": 0, "total_principal": 0.0, "instruments": []}
        buckets[year]["count"] += 1
        buckets[year]["total_principal"] += float(inst.principal_outstanding)
        buckets[year]["instruments"].append(inst.name)

    return [
        {k: v for k, v in b.items() if k != "instruments"}
        for b in sorted(buckets.values(), key=lambda x: x["year"])
    ]


def _build_currency_breakdown(instruments: list[DebtInstrument]) -> list[CurrencyBreakdown]:
    """Aggregate by currency with counts and percentages."""
    ccy_data: dict[str, dict] = {}
    for inst in instruments:
        ccy = inst.currency
        if ccy not in ccy_data:
            ccy_data[ccy] = {"total_principal": 0.0, "count": 0}
        ccy_data[ccy]["total_principal"] += float(inst.principal_outstanding)
        ccy_data[ccy]["count"] += 1

    total = sum(d["total_principal"] for d in ccy_data.values()) or 1
    return sorted(
        [
            CurrencyBreakdown(
                currency=ccy,
                total_principal=round(data["total_principal"], 2),
                percentage=round((data["total_principal"] / total) * 100, 1),
                instrument_count=data["count"],
            )
            for ccy, data in ccy_data.items()
        ],
        key=lambda x: x.total_principal,
        reverse=True,
    )


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/{portfolio_id}")
def portfolio_detail(
    portfolio_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    sort_by: Optional[str] = Query(default=None, description="Sort field: maturity_date, principal_outstanding, coupon_rate, spread_bps"),
    sort_order: Optional[str] = Query(default="asc", description="asc or desc"),
    currency: Optional[str] = Query(default=None, description="Filter by currency code"),
) -> dict:
    """
    Full portfolio detail with instruments, summary metrics, maturity
    distribution, and currency breakdown.
    """
    portfolio = (
        db.query(Portfolio)
        .options(joinedload(Portfolio.instruments))
        .filter(Portfolio.id == portfolio_id, Portfolio.org_id == user.org_id)
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    instruments = list(portfolio.instruments)

    # Apply currency filter
    if currency:
        instruments = [i for i in instruments if i.currency.upper() == currency.upper()]

    # Apply sorting
    if sort_by:
        sort_key_map = {
            "maturity_date": lambda i: i.maturity_date,
            "principal_outstanding": lambda i: float(i.principal_outstanding),
            "coupon_rate": lambda i: float(i.coupon_rate),
            "spread_bps": lambda i: float(i.spread_bps or 0),
            "name": lambda i: i.name.lower(),
        }
        sort_fn = sort_key_map.get(sort_by)
        if sort_fn:
            instruments.sort(key=sort_fn, reverse=(sort_order == "desc"))

    now = datetime.now(timezone.utc)

    # Build instrument rows with years_to_maturity
    instrument_rows = []
    for inst in instruments:
        years_to_maturity = 0.0
        try:
            mat_date = datetime.strptime(inst.maturity_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            years_to_maturity = round(max(0, (mat_date - now).days / 365.25), 2)
        except (ValueError, AttributeError):
            pass

        instrument_rows.append(InstrumentRow(
            id=inst.id,
            name=inst.name,
            instrument_type=str(inst.instrument_type.value) if hasattr(inst.instrument_type, "value") else str(inst.instrument_type),
            currency=inst.currency,
            principal_outstanding=float(inst.principal_outstanding),
            coupon_rate=float(inst.coupon_rate),
            maturity_date=inst.maturity_date,
            issue_date=inst.issue_date,
            spread_bps=float(inst.spread_bps or 0),
            years_to_maturity=years_to_maturity,
            is_callable=inst.is_callable,
        ))

    summary = _compute_summary(instruments)

    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "description": portfolio.description,
        "created_at": portfolio.created_at.isoformat(),
        "updated_at": portfolio.updated_at.isoformat(),
        "summary": summary.model_dump(),
        "instruments": [r.model_dump() for r in instrument_rows],
        "maturity_distribution": _build_maturity_distribution(instruments),
        "currency_breakdown": [c.model_dump() for c in _build_currency_breakdown(instruments)],
    }
