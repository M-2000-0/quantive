"""
Performance Attribution Engine — Decompose portfolio returns.

Provides:
- Return attribution by asset class, sector, and security
- Contribution analysis (what drove returns)
- Time-series performance comparison
- Information ratio, alpha, and tracking error
- Brinson-style allocation and selection attribution
"""
from datetime import datetime, timezone
from typing import Optional

import numpy as np
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


router = APIRouter(prefix="/api/performance", tags=["performance-attribution"])


# Simulated portfolio performance data
_PORTFOLIO_HISTORY = [
    {"month": "2025-10", "portfolio_return": 3.2, "benchmark_return": 2.8},
    {"month": "2025-11", "portfolio_return": -1.5, "benchmark_return": -2.1},
    {"month": "2025-12", "portfolio_return": 4.1, "benchmark_return": 3.5},
    {"month": "2026-01", "portfolio_return": -0.8, "benchmark_return": -1.2},
    {"month": "2026-02", "portfolio_return": 2.5, "benchmark_return": 2.0},
    {"month": "2026-03", "portfolio_return": 5.3, "benchmark_return": 4.8},
    {"month": "2026-04", "portfolio_return": -2.1, "benchmark_return": -3.0},
    {"month": "2026-05", "portfolio_return": 1.8, "benchmark_return": 1.5},
    {"month": "2026-06", "portfolio_return": 3.7, "benchmark_return": 3.2},
    {"month": "2026-07", "portfolio_return": -0.3, "benchmark_return": -0.8},
    {"month": "2026-08", "portfolio_return": 2.9, "benchmark_return": 2.4},
]

# Asset class contribution data
_ASSET_CONTRIBUTIONS = {
    "us_large_cap": {"weight": 0.35, "return": 12.5, "contribution": 4.38, "benchmark_weight": 0.40, "benchmark_return": 10.8},
    "us_small_cap": {"weight": 0.10, "return": 8.2, "contribution": 0.82, "benchmark_weight": 0.08, "benchmark_return": 7.5},
    "intl_developed": {"weight": 0.15, "return": 6.8, "contribution": 1.02, "benchmark_weight": 0.18, "benchmark_return": 5.9},
    "emerging_markets": {"weight": 0.10, "return": 11.3, "contribution": 1.13, "benchmark_weight": 0.08, "benchmark_return": 9.8},
    "fixed_income": {"weight": 0.20, "return": 4.5, "contribution": 0.90, "benchmark_weight": 0.20, "benchmark_return": 4.2},
    "alternatives": {"weight": 0.05, "return": 7.8, "contribution": 0.39, "benchmark_weight": 0.03, "benchmark_return": 6.5},
    "commodities": {"weight": 0.05, "return": 15.2, "contribution": 0.76, "benchmark_weight": 0.03, "benchmark_return": 12.0},
}

# Individual security contributions
_SECURITY_CONTRIBUTIONS = [
    {"symbol": "NVDA", "name": "NVIDIA", "weight": 0.08, "return": 45.2, "contribution": 3.62, "sector": "technology"},
    {"symbol": "AAPL", "name": "Apple", "weight": 0.06, "return": 18.5, "contribution": 1.11, "sector": "technology"},
    {"symbol": "MSFT", "name": "Microsoft", "weight": 0.05, "return": 22.1, "contribution": 1.11, "sector": "technology"},
    {"symbol": "AMZN", "name": "Amazon", "weight": 0.04, "return": 15.8, "contribution": 0.63, "sector": "technology"},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "weight": 0.03, "return": 8.2, "contribution": 0.25, "sector": "healthcare"},
    {"symbol": "VWO", "name": "Emerging Markets", "weight": 0.10, "return": 11.3, "contribution": 1.13, "sector": "emerging"},
    {"symbol": "GLD", "name": "Gold ETF", "weight": 0.03, "return": 28.5, "contribution": 0.86, "sector": "commodities"},
    {"symbol": "TLT", "name": "20+ Year Bonds", "weight": 0.10, "return": 3.2, "contribution": 0.32, "sector": "fixed_income"},
    {"symbol": "SPY", "name": "S&P 500 ETF", "weight": 0.15, "return": 10.8, "contribution": 1.62, "sector": "us_equity"},
    {"symbol": "QQQ", "name": "NASDAQ 100 ETF", "weight": 0.08, "return": 14.5, "contribution": 1.16, "sector": "technology"},
    {"symbol": "VEA", "name": "Developed Markets", "weight": 0.15, "return": 6.8, "contribution": 1.02, "sector": "intl_equity"},
    {"symbol": "ARKK", "name": "ARK Innovation", "weight": 0.02, "return": -8.5, "contribution": -0.17, "sector": "alternatives"},
]


@router.get("/attribution")
def get_performance_attribution(user=Depends(get_optional_user)):
    """Get full performance attribution breakdown."""
    # Calculate totals
    total_contribution = sum(s["contribution"] for s in _SECURITY_CONTRIBUTIONS)
    total_weight = sum(s["weight"] for s in _SECURITY_CONTRIBUTIONS)
    avg_return = sum(s["weight"] * s["return"] for s in _SECURITY_CONTRIBUTIONS) / total_weight if total_weight else 0

    # Sector grouping
    sectors = {}
    for s in _SECURITY_CONTRIBUTIONS:
        sec = s["sector"]
        if sec not in sectors:
            sectors[sec] = {"weight": 0, "contribution": 0, "securities": []}
        sectors[sec]["weight"] += s["weight"]
        sectors[sec]["contribution"] += s["contribution"]
        sectors[sec]["securities"].append(s["symbol"])

    sector_list = [
        {"sector": k, "weight": round(v["weight"], 3), "contribution": round(v["contribution"], 2), "securities": v["securities"]}
        for k, v in sorted(sectors.items(), key=lambda x: x[1]["contribution"], reverse=True)
    ]

    # Top/bottom contributors
    sorted_securities = sorted(_SECURITY_CONTRIBUTIONS, key=lambda s: s["contribution"], reverse=True)

    return {
        "portfolio_return": round(total_contribution, 2),
        "portfolio_return_pct": round(avg_return, 2),
        "benchmark_return_pct": 9.2,
        "alpha": round(avg_return - 9.2, 2),
        "total_securities": len(_SECURITY_CONTRIBUTIONS),
        "sector_breakdown": sector_list,
        "top_contributors": sorted_securities[:5],
        "bottom_contributors": sorted_securities[-3:],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/monthly")
def get_monthly_attribution(user=Depends(get_optional_user)):
    """Get monthly return attribution over time."""
    months = _PORTFOLIO_HISTORY

    # Calculate cumulative returns
    cum_portfolio = 1.0
    cum_benchmark = 1.0
    cumulative = []

    for m in months:
        cum_portfolio *= (1 + m["portfolio_return"] / 100)
        cum_benchmark *= (1 + m["benchmark_return"] / 100)
        cumulative.append({
            "month": m["month"],
            "portfolio_return": m["portfolio_return"],
            "benchmark_return": m["benchmark_return"],
            "excess_return": round(m["portfolio_return"] - m["benchmark_return"], 2),
            "cumulative_portfolio": round((cum_portfolio - 1) * 100, 2),
            "cumulative_benchmark": round((cum_benchmark - 1) * 100, 2),
        })

    # Summary stats
    portfolio_returns = [m["portfolio_return"] for m in months]
    benchmark_returns = [m["benchmark_return"] for m in months]
    excess_returns = [m["portfolio_return"] - m["benchmark_return"] for m in months]

    avg_excess = np.mean(excess_returns)
    tracking_error = np.std(excess_returns)
    information_ratio = avg_excess / tracking_error if tracking_error else 0

    winning_months = sum(1 for e in excess_returns if e > 0)

    return {
        "monthly_data": cumulative,
        "summary": {
            "total_months": len(months),
            "cumulative_portfolio_return": round((cum_portfolio - 1) * 100, 2),
            "cumulative_benchmark_return": round((cum_benchmark - 1) * 100, 2),
            "total_excess_return": round((cum_portfolio - 1 - (cum_benchmark - 1)) * 100, 2),
            "avg_monthly_excess": round(float(avg_excess), 2),
            "tracking_error": round(float(tracking_error), 2),
            "information_ratio": round(float(information_ratio), 2),
            "winning_months": winning_months,
            "win_rate": round(winning_months / len(months) * 100, 1),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/brinson")
def get_brinson_attribution(user=Depends(get_optional_user)):
    """Brinson-style allocation and selection attribution."""
    results = []
    total_allocation_effect = 0
    total_selection_effect = 0
    total_interaction = 0

    for name, data in _ASSET_CONTRIBUTIONS.items():
        wp = data["weight"]       # Portfolio weight
        wb = data["benchmark_weight"]  # Benchmark weight
        rp = data["return"]       # Portfolio return
        rb = data["benchmark_return"]  # Benchmark return

        # Brinson decomposition
        allocation = (wp - wb) * rb
        selection = wb * (rp - rb)
        interaction = (wp - wb) * (rp - rb)

        total_allocation_effect += allocation
        total_selection_effect += selection
        total_interaction += interaction

        results.append({
            "asset_class": name,
            "portfolio_weight": round(wp * 100, 2),
            "benchmark_weight": round(wb * 100, 2),
            "portfolio_return": round(rp, 2),
            "benchmark_return": round(rb, 2),
            "allocation_effect": round(allocation, 3),
            "selection_effect": round(selection, 3),
            "interaction_effect": round(interaction, 3),
            "total_effect": round(allocation + selection + interaction, 3),
        })

    results.sort(key=lambda r: r["total_effect"], reverse=True)

    return {
        "brinson_results": results,
        "summary": {
            "total_allocation_effect": round(total_allocation_effect, 3),
            "total_selection_effect": round(total_selection_effect, 3),
            "total_interaction": round(total_interaction, 3),
            "total_active_return": round(total_allocation_effect + total_selection_effect + total_interaction, 3),
            "primary_driver": "selection" if abs(total_selection_effect) > abs(total_allocation_effect) else "allocation",
        },
        "interpretation": {
            "allocation": f"Overweighting/underweighting asset classes contributed {round(total_allocation_effect, 2)}% to active return",
            "selection": f"Security selection within asset classes contributed {round(total_selection_effect, 2)}% to active return",
            "interaction": f"Combined weight-return effects contributed {round(total_interaction, 2)}% to active return",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/risk-metrics")
def get_risk_metrics(user=Depends(get_optional_user)):
    """Calculate portfolio risk metrics."""
    portfolio_returns = [m["portfolio_return"] for m in _PORTFOLIO_HISTORY]
    benchmark_returns = [m["benchmark_return"] for m in _PORTFOLIO_HISTORY]

    # Annualize (multiply by 12)
    avg_return = np.mean(portfolio_returns) * 12
    volatility = np.std(portfolio_returns) * np.sqrt(12)
    sharpe = (avg_return - 4.0) / (volatility * 100) if volatility else 0  # 4% risk-free

    # Max drawdown
    cumulative = [1.0]
    for r in portfolio_returns:
        cumulative.append(cumulative[-1] * (1 + r / 100))
    peak = cumulative[0]
    max_drawdown = 0
    for val in cumulative:
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        if dd > max_drawdown:
            max_drawdown = dd

    # Sortino (downside deviation)
    negative_returns = [r for r in portfolio_returns if r < 0]
    downside_dev = np.std(negative_returns) * np.sqrt(12) if negative_returns else 0
    sortino = (avg_return - 4.0) / (downside_dev * 100) if downside_dev else 0

    # Tracking error vs benchmark
    excess = [p - b for p, b in zip(portfolio_returns, benchmark_returns)]
    tracking_error = np.std(excess) * np.sqrt(12)
    info_ratio = np.mean(excess) * 12 / (tracking_error * 100) if tracking_error else 0

    return {
        "annualized_return": round(float(avg_return), 2),
        "annualized_volatility": round(float(volatility * 100), 2),
        "sharpe_ratio": round(float(sharpe), 2),
        "sortino_ratio": round(float(sortino), 2),
        "max_drawdown": round(float(max_drawdown * 100), 2),
        "tracking_error": round(float(tracking_error * 100), 2),
        "information_ratio": round(float(info_ratio), 2),
        "calmar_ratio": round(float(avg_return / (max_drawdown * 100)) if max_drawdown else 0, 2),
        "beta": 1.12,
        "alpha_annual": 2.8,
        "best_month": round(max(portfolio_returns), 2),
        "worst_month": round(min(portfolio_returns), 2),
        "positive_months": sum(1 for r in portfolio_returns if r > 0),
        "negative_months": sum(1 for r in portfolio_returns if r < 0),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
