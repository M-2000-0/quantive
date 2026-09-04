"""
Portfolio Aggregator — Multi-portfolio unified view.

Provides:
- Aggregate all portfolios into a single performance dashboard
- Cross-portfolio allocation analysis
- Combined P&L and performance metrics
- Portfolio comparison view
"""
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, Request
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
    token = None
    if credentials:
        token = credentials.credentials
    else:
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


router = APIRouter(prefix="/api/portfolio-agg", tags=["portfolio-aggregator"])


_aggregate_history: list[dict] = []


def _load_all_portfolios(user_id: str) -> list[dict]:
    """Load all portfolios and their holdings from the database."""
    from app.database import SessionLocal
    from app.models import Portfolio, DebtInstrument, User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        portfolios = db.query(Portfolio).filter(
            Portfolio.org_id == user.org_id
        ).all()

        result = []
        for portfolio in portfolios:
            instruments = db.query(DebtInstrument).filter(
                DebtInstrument.portfolio_id == portfolio.id
            ).all()

            holdings = []
            for inst in instruments:
                asset_class = inst.instrument_type.value if hasattr(inst.instrument_type, 'value') else str(inst.instrument_type)
                principal = float(inst.principal_outstanding)
                coupon = float(inst.coupon_rate)
                # Estimate current value with accrued interest approximation
                current_value = principal * (1 + coupon * 0.5)
                holdings.append({
                    "symbol": inst.name[:12].upper().replace(" ", "-"),
                    "name": inst.name,
                    "shares": 1,
                    "current_price": current_value,
                    "cost_basis": principal,
                    "asset_class": asset_class,
                    "currency": inst.currency,
                })

            result.append({
                "id": portfolio.id,
                "name": portfolio.name,
                "description": getattr(portfolio, 'description', '') or '',
                "holdings": holdings,
            })
        return result
    except Exception as e:
        print(f"Error loading portfolios from DB: {e}")
        return []
    finally:
        db.close()


def _calc_portfolio_metrics(holdings: list[dict]) -> dict:
    """Calculate metrics for a single portfolio."""
    total_value = sum(h["shares"] * h["current_price"] for h in holdings)
    total_cost = sum(h["shares"] * h["cost_basis"] for h in holdings)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

    # Asset allocation
    allocations = {}
    for h in holdings:
        ac = h["asset_class"]
        val = h["shares"] * h["current_price"]
        allocations[ac] = allocations.get(ac, 0) + val
    allocations = {k: round(v / total_value * 100, 2) if total_value else 0 for k, v in allocations.items()}

    # Top performers
    performers = sorted(
        [{"symbol": h["symbol"], "pnl_pct": round((h["current_price"] - h["cost_basis"]) / h["cost_basis"] * 100, 2)}
         for h in holdings],
        key=lambda x: x["pnl_pct"], reverse=True
    )

    return {
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "holdings_count": len(holdings),
        "allocations": allocations,
        "top_performer": performers[0] if performers else None,
        "worst_performer": performers[-1] if performers else None,
    }


@router.get("/aggregate")
def get_aggregate_view(user=Depends(get_optional_user)):
    """Get unified view across all portfolios."""
    user_id = str(user.id) if user else "default"
    portfolios = _load_all_portfolios(user_id)

    # Calculate per-portfolio metrics
    portfolio_metrics = []
    all_holdings = []
    for p in portfolios:
        metrics = _calc_portfolio_metrics(p["holdings"])
        portfolio_metrics.append({
            "id": p["id"],
            "name": p["name"],
            "description": p["description"],
            **metrics,
        })
        all_holdings.extend([{**h, 'portfolio': p['name']} for h in p['holdings']])

    # Aggregate totals
    total_value = sum(pm["total_value"] for pm in portfolio_metrics)
    total_cost = sum(pm["total_cost"] for pm in portfolio_metrics)
    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

    # Cross-portfolio allocation
    combined_alloc = {}
    for pm in portfolio_metrics:
        for ac, pct in pm["allocations"].items():
            weight = pm["total_value"] / total_value if total_value else 0
            combined_alloc[ac] = combined_alloc.get(ac, 0) + pct * weight
    combined_alloc = {k: round(v, 2) for k, v in sorted(combined_alloc.items(), key=lambda x: x[1], reverse=True)}

    # Concentration analysis
    symbol_values = {}
    for h in all_holdings:
        sym = h["symbol"]
        val = h["shares"] * h["current_price"]
        symbol_values[sym] = symbol_values.get(sym, 0) + val
    top_holdings = sorted(
        [{"symbol": s, "value": round(v, 2), "pct": round(v / total_value * 100, 2) if total_value else 0}
         for s, v in symbol_values.items()],
        key=lambda x: x["value"], reverse=True
    )[:10]

    # Risk metrics
    pnl_values = [pm["total_pnl_pct"] for pm in portfolio_metrics]
    volatility = round(float(np.std(pnl_values)), 2) if len(pnl_values) > 1 else 0

    return {
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "portfolio_count": len(portfolios),
        "total_holdings": sum(pm["holdings_count"] for pm in portfolio_metrics),
        "portfolios": portfolio_metrics,
        "combined_allocation": combined_alloc,
        "top_holdings": top_holdings,
        "concentration_risk": "HIGH" if top_holdings and top_holdings[0]["pct"] > 25 else "MODERATE" if top_holdings and top_holdings[0]["pct"] > 15 else "LOW",
        "volatility_score": volatility,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/compare")
def compare_portfolios(user=Depends(get_optional_user)):
    """Compare individual portfolio performance side by side."""
    user_id = str(user.id) if user else "default"
    portfolios = _load_all_portfolios(user_id)
    comparison = []

    for p in portfolios:
        metrics = _calc_portfolio_metrics(p["holdings"])
        comparison.append({
            "id": p["id"],
            "name": p["name"],
            "value": metrics["total_value"],
            "return_pct": metrics["total_pnl_pct"],
            "pnl": metrics["total_pnl"],
            "holdings": metrics["holdings_count"],
            "top_performer": metrics["top_performer"],
            "risk_level": "AGGRESSIVE" if metrics["total_pnl_pct"] > 15 else "MODERATE" if metrics["total_pnl_pct"] > 5 else "CONSERVATIVE",
        })

    comparison.sort(key=lambda x: x["return_pct"], reverse=True)

    return {
        "comparison": comparison,
        "best_performer": comparison[0]["name"] if comparison else None,
        "worst_performer": comparison[-1]["name"] if comparison else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/holdings")
def get_all_holdings(user=Depends(get_optional_user)):
    """Get all holdings across all portfolios in a unified view."""
    user_id = str(user.id) if user else "default"
    portfolios = _load_all_portfolios(user_id)
    all_holdings = []
    symbol_map = {}

    for p in portfolios:
        for h in p["holdings"]:
            sym = h["symbol"]
            val = h["shares"] * h["current_price"]
            pnl_pct = round((h["current_price"] - h["cost_basis"]) / h["cost_basis"] * 100, 2) if h["cost_basis"] else 0

            if sym in symbol_map:
                symbol_map[sym]["total_shares"] += h["shares"]
                symbol_map[sym]["total_value"] += val
                symbol_map[sym]["portfolios"].append(p["name"])
            else:
                symbol_map[sym] = {
                    "symbol": sym,
                    "total_shares": h["shares"],
                    "total_value": val,
                    "current_price": h["current_price"],
                    "cost_basis": h["cost_basis"],
                    "pnl_pct": pnl_pct,
                    "asset_class": h["asset_class"],
                    "portfolios": [p["name"]],
                }

    total_value = sum(h["total_value"] for h in symbol_map.values())
    holdings_list = sorted(
        [{**h, "total_value": round(h["total_value"], 2), "pct_of_total": round(h["total_value"] / total_value * 100, 2) if total_value else 0}
         for h in symbol_map.values()],
        key=lambda x: x["total_value"], reverse=True
    )

    return {
        "holdings": holdings_list,
        "total_value": round(total_value, 2),
        "unique_symbols": len(holdings_list),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
