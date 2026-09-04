"""
Tax-Loss Harvesting Optimizer — Identify tax-efficient rebalancing opportunities.

Provides:
- Unrealized loss detection across all holdings
- Wash-sale rule warnings (30-day window)
- Harvesting candidate ranking by tax savings potential
- Tax-efficient rebalancing suggestions
- Annual tax savings estimation
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from app.market_data.cache import get_cache
from app.security import get_current_user
from typing import Optional
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

_optional_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if credentials is None:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(credentials.credentials)
        if payload:
            uid = payload.get("sub")
            return db.query(User).filter(User.id == uid).first()
    except Exception:
        pass
    return None


router = APIRouter(prefix="/api/tax-harvest", tags=["tax-loss-harvesting"])

# Tax brackets (2024 simplified)
SHORT_TERM_RATE = 0.32  # Ordinary income rate
LONG_TERM_RATE = 0.15   # Long-term capital gains rate
WASH_SALE_DAYS = 30     # IRS wash sale rule

# Tax lots loaded from database
_TAX_LOTS: dict[str, list[dict]] = {}

# Correlated substitutes for wash-sale-safe harvesting
_SUBSTITUTES = {
    "NVDA": {"replace_with": "SOXX", "reason": "Semiconductor ETF — maintains tech exposure"},
    "TSLA": {"replace_with": "DRIV", "reason": "EV & autonomous driving ETF"},
    "ARKK": {"replace_with": "ARKW", "reason": "ARK Next Generation Internet — similar mandate"},
    "TLT": {"replace_with": "VGLT", "reason": "Vanguard Long-Term Treasury — same duration"},
    "XOM": {"replace_with": "CVX", "reason": "Chevron — peer in same sector"},
    "INTC": {"replace_with": "AMD", "reason": "AMD — peer semiconductor stock"},
    "PYPL": {"replace_with": "SQ", "reason": "Block (Square) — fintech peer"},
    "SPY": {"replace_with": "VOO", "reason": "Vanguard S&P 500 — nearly identical"},
    "AAPL": {"replace_with": "QQQ", "reason": "NASDAQ 100 — heavy AAPL weight"},
    "MSFT": {"replace_with": "XLK", "reason": "Tech Select Sector — heavy MSFT weight"},
}


def _calculate_tax_impact(lot: dict) -> dict:
    """Calculate tax impact for a single lot."""
    cost = lot["shares"] * lot["cost_basis"]
    value = lot["shares"] * lot["current_price"]
    gain_loss = value - cost
    gain_loss_pct = (gain_loss / cost * 100) if cost else 0

    # Determine holding period
    purchase = datetime.strptime(lot["purchase_date"], "%Y-%m-%d")
    holding_days = (datetime.now() - purchase).days
    is_long_term = holding_days > 365

    # Tax rate
    tax_rate = LONG_TERM_RATE if is_long_term else SHORT_TERM_RATE

    # Tax impact
    tax_if_sold = gain_loss * tax_rate if gain_loss > 0 else 0
    tax_savings_if_loss = abs(gain_loss) * tax_rate if gain_loss < 0 else 0

    return {
        "unrealized_gain_loss": round(gain_loss, 2),
        "unrealized_gain_loss_pct": round(gain_loss_pct, 2),
        "holding_days": holding_days,
        "holding_period": "LONG_TERM" if is_long_term else "SHORT_TERM",
        "tax_rate": tax_rate,
        "tax_if_sold": round(max(tax_if_sold, 0), 2),
        "tax_savings_if_harvested": round(tax_savings_if_loss, 2),
    }


def _check_wash_sale(symbol: str, lots: list[dict]) -> dict:
    """Check for wash-sale rule violations."""
    # Check if any lots were purchased within 30 days
    recent_purchases = []
    now = datetime.now()
    cutoff = now - timedelta(days=WASH_SALE_DAYS)

    for lot in lots:
        if lot["symbol"] == symbol:
            purchase = datetime.strptime(lot["purchase_date"], "%Y-%m-%d")
            if purchase > cutoff:
                recent_purchases.append(lot)

    wash_sale_risk = len(recent_purchases) > 0
    substitute = _SUBSTITUTES.get(symbol, {})

    return {
        "wash_sale_risk": wash_sale_risk,
        "recent_purchases": len(recent_purchases),
        "days_since_last_purchase": min(
            [(now - datetime.strptime(l["purchase_date"], "%Y-%m-%d")).days for l in recent_purchases],
            default=999
        ),
        "recommended_substitute": substitute.get("replace_with"),
        "substitute_reason": substitute.get("reason"),
    }


@router.get("/positions")
def get_tax_positions(user=Depends(get_optional_user)):
    """Get all positions with tax lot analysis."""
    user_id = str(user.id) if user else "default"
    lots = _TAX_LOTS.get(user_id, [])

    positions = []
    total_gain = 0
    total_loss = 0
    total_potential_savings = 0

    for lot in lots:
        tax = _calculate_tax_impact(lot)
        wash = _check_wash_sale(lot["symbol"], lots)

        position = {
            **lot,
            "cost_total": round(lot["shares"] * lot["cost_basis"], 2),
            "market_value": round(lot["shares"] * lot["current_price"], 2),
            **tax,
            **wash,
        }
        positions.append(position)

        if tax["unrealized_gain_loss"] > 0:
            total_gain += tax["unrealized_gain_loss"]
        else:
            total_loss += abs(tax["unrealized_gain_loss"])
            total_potential_savings += tax["tax_savings_if_harvested"]

    # Sort by tax savings potential (biggest losses first)
    positions.sort(key=lambda p: p["unrealized_gain_loss"])

    return {
        "positions": positions,
        "summary": {
            "total_positions": len(positions),
            "total_unrealized_gains": round(total_gain, 2),
            "total_unrealized_losses": round(total_loss, 2),
            "net_position": round(total_gain - total_loss, 2),
            "total_potential_tax_savings": round(total_potential_savings, 2),
            "harvestable_positions": sum(1 for p in positions if p["unrealized_gain_loss"] < 0),
            "wash_sale_risks": sum(1 for p in positions if p["wash_sale_risk"]),
        },
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/candidates")
def get_harvesting_candidates(
    min_loss: float = Query(default=100.0, description="Minimum unrealized loss in $"),
    user=Depends(get_optional_user),
):
    """Get ranked harvesting candidates by tax savings potential."""
    user_id = str(user.id) if user else "default"
    lots = _TAX_LOTS.get(user_id, [])

    candidates = []
    for lot in lots:
        tax = _calculate_tax_impact(lot)
        wash = _check_wash_sale(lot["symbol"], lots)

        if tax["unrealized_gain_loss"] < -min_loss:
            candidates.append({
                "symbol": lot["symbol"],
                "name": lot["name"],
                "shares": lot["shares"],
                "cost_basis": lot["cost_basis"],
                "current_price": lot["current_price"],
                "unrealized_loss": round(abs(tax["unrealized_gain_loss"]), 2),
                "loss_pct": round(abs(tax["unrealized_gain_loss_pct"]), 2),
                "tax_savings": round(tax["tax_savings_if_harvested"], 2),
                "holding_period": tax["holding_period"],
                "holding_days": tax["holding_days"],
                "wash_sale_risk": wash["wash_sale_risk"],
                "recommended_substitute": wash["recommended_substitute"],
                "substitute_reason": wash["substitute_reason"],
                "priority_score": round(
                    tax["tax_savings_if_harvested"] * (0.5 if wash["wash_sale_risk"] else 1.0), 2
                ),
            })

    # Sort by priority (tax savings adjusted for wash sale risk)
    candidates.sort(key=lambda c: c["priority_score"], reverse=True)

    total_savings = sum(c["tax_savings"] for c in candidates)
    total_loss = sum(c["unrealized_loss"] for c in candidates)

    return {
        "candidates": candidates,
        "summary": {
            "total_candidates": len(candidates),
            "total_harvestable_loss": round(total_loss, 2),
            "total_potential_savings": round(total_savings, 2),
            "wash_sale_affected": sum(1 for c in candidates if c["wash_sale_risk"]),
        },
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/savings-estimate")
def estimate_annual_savings(user=Depends(get_optional_user)):
    """Estimate annual tax savings from optimal harvesting strategy."""
    user_id = str(user.id) if user else "default"
    lots = _TAX_LOTS.get(user_id, [])

    candidates = []
    for lot in lots:
        tax = _calculate_tax_impact(lot)
        wash = _check_wash_sale(lot["symbol"], lots)
        if tax["unrealized_gain_loss"] < -100:
            candidates.append({
                "symbol": lot["symbol"],
                "tax_savings": tax["tax_savings_if_harvested"],
                "wash_sale_risk": wash["wash_sale_risk"],
                "substitute": wash["recommended_substitute"],
            })

    # Optimal harvesting (no wash sales)
    no_wash = [c for c in candidates if not c["wash_sale_risk"]]
    optimal_savings = sum(c["tax_savings"] for c in no_wash)

    # Conservative (all candidates)
    conservative_savings = sum(c["tax_savings"] for c in candidates)

    # Quarterly breakdown
    quarterly = conservative_savings / 4

    return {
        "optimal_strategy": {
            "annual_savings": round(optimal_savings, 2),
            "positions_harvested": len(no_wash),
            "description": "Harvest only positions without wash-sale risk",
        },
        "conservative_strategy": {
            "annual_savings": round(conservative_savings, 2),
            "positions_harvested": len(candidates),
            "description": "Harvest all loss positions with substitute replacements",
        },
        "quarterly_breakdown": {
            "Q1": round(quarterly, 2),
            "Q2": round(quarterly, 2),
            "Q3": round(quarterly, 2),
            "Q4": round(quarterly, 2),
        },
        "tax_tips": [
            "Harvest losses before year-end to offset realized gains",
            "Use substitute securities to maintain market exposure while avoiding wash sales",
            "Prioritize short-term losses (worth more at higher ordinary income rates)",
            "Consider donating appreciated positions to charity to avoid capital gains entirely",
            "Track your cost basis carefully — some brokers use FIFO, others use specific identification",
        ],
        "estimated_at": datetime.now(timezone.utc).isoformat(),
    }
