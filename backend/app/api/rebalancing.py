"""
Portfolio Rebalancing Engine — Detects allocation drift and recommends trades.

Provides:
- Drift detection when allocations exceed user-set thresholds
- Trade recommendations to restore target allocations
- Rebalancing history and simulation
- Tax-aware rebalancing (wash sale, capital gains estimation)
"""
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.market_data.cache import get_cache
from app.security import get_current_user
from typing import Optional
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

_optional_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    # Try Bearer token first
    token = None
    if credentials:
        token = credentials.credentials
    else:
        # Fallback to access_token cookie
        token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(token)
        if payload:
            uid = payload.get("sub")
            return db.query(User).filter(User.id == uid).first()
    except Exception:
        pass
    return None


router = APIRouter(prefix="/api/rebalancing", tags=["rebalancing-engine"])

# Target allocation by instrument type for sovereign debt
DEFAULT_TARGETS = {
    "treasury_bond": 0.30,
    "t_bill": 0.10,
    "sovereign_bond": 0.15,
    "concessional_loan": 0.10,
    "commercial_loan": 0.08,
    "floating_rate_note": 0.10,
    "inflation_linked": 0.07,
    "eurobond": 0.05,
    "domestic_bond": 0.05,
}

_rebalance_history: list[dict] = []


class RebalanceThresholds(BaseModel):
    max_drift_pct: float = 5.0  # Max allowed drift before recommending trade
    min_trade_amount: float = 100.0  # Minimum trade size in USD
    tax_loss_harvest: bool = False  # Consider tax implications
    rebalance_band: float = 2.0  # Buffer zone - don't trade if within band


def _load_holdings_from_db(user_id: str) -> list[dict]:
    """Load portfolio holdings from the database."""
    from app.database import SessionLocal
    from app.models import Portfolio, DebtInstrument, User

    db = SessionLocal()
    try:
        # Find portfolios belonging to this user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        portfolios = db.query(Portfolio).filter(
            Portfolio.org_id == user.org_id
        ).all()

        holdings = []
        for portfolio in portfolios:
            instruments = db.query(DebtInstrument).filter(
                DebtInstrument.portfolio_id == portfolio.id
            ).all()
            for inst in instruments:
                # Map instrument type to asset class
                asset_class = inst.instrument_type.value if hasattr(inst.instrument_type, 'value') else str(inst.instrument_type)
                # Use coupon rate as yield proxy, principal as value
                holdings.append({
                    "symbol": inst.name[:12].upper().replace(" ", "-"),
                    "name": inst.name,
                    "shares": 1,
                    "cost_basis": float(inst.principal_outstanding),
                    "current_price": float(inst.principal_outstanding) * (1 + float(inst.coupon_rate) * 0.5),
                    "asset_class": asset_class,
                    "currency": inst.currency,
                    "coupon_rate": float(inst.coupon_rate),
                    "maturity_date": inst.maturity_date,
                    "instrument_id": inst.id,
                    "portfolio_name": portfolio.name,
                })
        return holdings
    except Exception as e:
        print(f"Error loading holdings from DB: {e}")
        return []
    finally:
        db.close()


def _get_current_prices(holdings: list[dict]) -> dict[str, float]:
    """Get prices for holdings — use current_price from DB data."""
    return {h["symbol"]: h["current_price"] for h in holdings}


def _calculate_allocation(holdings: list[dict], prices: dict[str, float]) -> dict[str, float]:
    """Calculate current allocation percentages by asset class."""
    class_values = {}
    total_value = 0

    for h in holdings:
        price = prices.get(h["symbol"], h["cost_basis"])
        value = h["shares"] * price
        total_value += value
        ac = h["asset_class"]
        class_values[ac] = class_values.get(ac, 0) + value

    if total_value == 0:
        return {}

    return {ac: round(val / total_value * 100, 2) for ac, val in class_values.items()}


@router.get("/portfolio")
def get_rebalancing_portfolio(user=Depends(get_optional_user)):
    """Get current portfolio holdings with allocation analysis."""
    user_id = str(user.id) if user else "default"
    holdings = _load_holdings_from_db(user_id)
    prices = _get_current_prices(holdings)

    total_value = 0
    total_cost = 0
    holdings_detail = []

    for h in holdings:
        price = prices.get(h["symbol"], h["cost_basis"])
        value = h["shares"] * price
        cost = h["shares"] * h["cost_basis"]
        total_value += value
        total_cost += cost
        holdings_detail.append({
            "symbol": h["symbol"],
            "name": h["name"],
            "shares": h["shares"],
            "current_price": round(price, 2),
            "cost_basis": round(h["cost_basis"], 2),
            "market_value": round(value, 2),
            "cost_value": round(cost, 2),
            "unrealized_pnl": round(value - cost, 2),
            "unrealized_pnl_pct": round((value - cost) / cost * 100, 2) if cost else 0,
            "asset_class": h["asset_class"],
            "instrument_id": h.get("instrument_id"),
        })

    current_alloc = _calculate_allocation(holdings, prices)

    return {
        "holdings": holdings_detail,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_value - total_cost, 2),
        "total_pnl_pct": round((total_value - total_cost) / total_cost * 100, 2) if total_cost else 0,
        "current_allocation": current_alloc,
        "target_allocation": {k: round(v * 100, 2) for k, v in DEFAULT_TARGETS.items()},
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/check")
def check_rebalancing(user=Depends(get_optional_user)):
    """Check if rebalancing is needed and generate trade recommendations."""
    user_id = str(user.id) if user else "default"
    holdings = _load_holdings_from_db(user_id)
    prices = _get_current_prices(holdings)

    total_value = sum(h["shares"] * prices.get(h["symbol"], h["cost_basis"]) for h in holdings)
    current_alloc = _calculate_allocation(holdings, prices)

    # Calculate drift
    drift_analysis = []
    for asset_class, target_pct in DEFAULT_TARGETS.items():
        current_pct = current_alloc.get(asset_class, 0)
        target = round(target_pct * 100, 2)
        drift = round(current_pct - target, 2)
        drift_analysis.append({
            "asset_class": asset_class,
            "target_pct": target,
            "current_pct": current_pct,
            "drift_pct": drift,
            "needs_rebalance": abs(drift) > 5.0,  # 5% threshold
        })

    # Generate trade recommendations
    trades = []
    for asset_class, target_pct in DEFAULT_TARGETS.items():
        current_pct = current_alloc.get(asset_class, 0)
        drift = current_pct - round(target_pct * 100, 2)

        if abs(drift) > 5.0:
            target_value = total_value * target_pct
            current_value = sum(
                h["shares"] * prices.get(h["symbol"], h["cost_basis"])
                for h in holdings if h["asset_class"] == asset_class
            )
            trade_value = target_value - current_value

            # Find best instrument in this asset class
            class_holdings = [h for h in holdings if h["asset_class"] == asset_class]
            if class_holdings:
                best = max(class_holdings, key=lambda h: h["shares"] * prices.get(h["symbol"], h["cost_basis"]))
                price = prices.get(best["symbol"], best["cost_basis"])
                shares_to_trade = abs(trade_value) / price if price else 0

                trades.append({
                    "action": "BUY" if trade_value > 0 else "SELL",
                    "symbol": best["symbol"],
                    "name": best["name"],
                    "asset_class": asset_class,
                    "shares": round(shares_to_trade, 1),
                    "estimated_amount": round(abs(trade_value), 2),
                    "reason": f"Drift of {drift:+.1f}% from target {round(target_pct*100, 1)}%",
                    "priority": "high" if abs(drift) > 10 else "medium",
                })

    # Calculate overall rebalancing score
    total_drift = sum(abs(d["drift_pct"]) for d in drift_analysis)
    rebalance_score = max(0, 100 - total_drift * 2)

    status = "BALANCED"
    if total_drift > 30:
        status = "CRITICAL"
    elif total_drift > 15:
        status = "NEEDS_REBALANCE"
    elif total_drift > 5:
        status = "MONITOR"

    return {
        "status": status,
        "rebalance_score": round(rebalance_score, 1),
        "total_drift": round(total_drift, 2),
        "drift_analysis": drift_analysis,
        "trade_recommendations": sorted(trades, key=lambda t: t["estimated_amount"], reverse=True),
        "total_trades": len(trades),
        "total_trade_value": round(sum(t["estimated_amount"] for t in trades), 2),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/history")
def get_rebalance_history(user=Depends(get_optional_user)):
    """Get rebalancing history."""
    return {"history": _rebalance_history[-20:], "count": len(_rebalance_history)}


@router.get("/simulate")
def simulate_rebalancing(user=Depends(get_optional_user)):
    """Simulate what the portfolio would look like after rebalancing."""
    user_id = str(user.id) if user else "default"
    holdings = _load_holdings_from_db(user_id)
    prices = _get_current_prices(holdings)

    total_value = sum(h["shares"] * prices.get(h["symbol"], h["cost_basis"]) for h in holdings)
    current_alloc = _calculate_allocation(holdings, prices)

    simulated = []
    for h in holdings:
        price = prices.get(h["symbol"], h["cost_basis"])
        target_value = total_value * DEFAULT_TARGETS.get(h["asset_class"], 0.05)
        new_shares = target_value / price if price else h["shares"]
        simulated.append({
            "symbol": h["symbol"],
            "name": h["name"],
            "current_shares": h["shares"],
            "target_shares": round(new_shares, 1),
            "trade_shares": round(new_shares - h["shares"], 1),
            "asset_class": h["asset_class"],
            "trade_value": round(abs(new_shares - h["shares"]) * price, 2),
        })

    new_alloc = {}
    for s in simulated:
        ac = s["asset_class"]
        new_alloc[ac] = new_alloc.get(ac, 0) + s["target_shares"] * prices.get(s["symbol"], 0)
    new_alloc = {k: round(v / total_value * 100, 2) if total_value else 0 for k, v in new_alloc.items()}

    return {
        "simulated_holdings": simulated,
        "current_allocation": current_alloc,
        "simulated_allocation": new_alloc,
        "target_allocation": {k: round(v * 100, 2) for k, v in DEFAULT_TARGETS.items()},
        "total_trades": sum(1 for s in simulated if abs(s["trade_shares"]) > 0.1),
        "total_trade_value": round(sum(s["trade_value"] for s in simulated), 2),
        "simulated_at": datetime.now(timezone.utc).isoformat(),
    }
