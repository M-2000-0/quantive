"""
Risk Parity Optimizer - Equal risk contribution portfolio construction.

Provides:
- Risk parity weight calculation (equal risk contribution)
- Volatility targeting for each asset class
- Correlation matrix analysis
- Risk contribution breakdown
- Comparison: traditional vs risk parity allocation
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


router = APIRouter(prefix="/api/risk-parity", tags=["risk-parity"])

# Asset class volatility estimates (annualized)
ASSET_VOLATILITY = {
    "us_equity": 0.16,
    "intl_equity": 0.18,
    "emerging_markets": 0.22,
    "real_estate": 0.14,
    "commodities": 0.18,
    "treasury_long": 0.12,
    "treasury_short": 0.04,
    "high_yield_bonds": 0.08,
    "tips": 0.06,
    "gold": 0.15,
}

# Correlation matrix (simplified)
CORRELATION_MATRIX = {
    ("us_equity", "us_equity"): 1.00,
    ("us_equity", "intl_equity"): 0.75,
    ("us_equity", "emerging_markets"): 0.65,
    ("us_equity", "real_estate"): 0.60,
    ("us_equity", "commodities"): 0.25,
    ("us_equity", "treasury_long"): -0.30,
    ("us_equity", "treasury_short"): -0.10,
    ("us_equity", "high_yield_bonds"): 0.65,
    ("us_equity", "tips"): 0.10,
    ("us_equity", "gold"): 0.05,
    ("intl_equity", "intl_equity"): 1.00,
    ("intl_equity", "emerging_markets"): 0.80,
    ("intl_equity", "commodities"): 0.30,
    ("intl_equity", "treasury_long"): -0.20,
    ("emerging_markets", "emerging_markets"): 1.00,
    ("commodities", "commodities"): 1.00,
    ("commodities", "gold"): 0.60,
    ("treasury_long", "treasury_long"): 1.00,
    ("treasury_long", "treasury_short"): 0.85,
    ("treasury_short", "treasury_short"): 1.00,
    ("high_yield_bonds", "high_yield_bonds"): 1.00,
    ("high_yield_bonds", "us_equity"): 0.65,
    ("tips", "tips"): 1.00,
    ("gold", "gold"): 1.00,
    ("real_estate", "real_estate"): 1.00,
}


def _get_correlation(a: str, b: str) -> float:
    """Get correlation between two asset classes."""
    if a == b:
        return 1.0
    return CORRELATION_MATRIX.get((a, b), CORRELATION_MATRIX.get((b, a), 0.3))


def _calculate_risk_parity_weights() -> dict:
    """Calculate risk parity weights using iterative method."""
    assets = list(ASSET_VOLATILITY.keys())
    n = len(assets)
    vols = np.array([ASSET_VOLATILITY[a] for a in assets])

    # Build covariance matrix
    cov = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            corr = _get_correlation(assets[i], assets[j])
            cov[i][j] = corr * vols[i] * vols[j]

    # Iterative risk parity (简单的逆波动率方法)
    inv_vols = 1.0 / vols
    weights = inv_vols / inv_vols.sum()

    # Calculate risk contributions
    portfolio_vol = np.sqrt(weights @ cov @ weights)
    marginal_risk = cov @ weights
    risk_contributions = weights * marginal_risk / portfolio_vol

    # Normalize to equal risk contribution
    risk_parity_weights = risk_contributions / risk_contributions.sum()

    return {
        "assets": assets,
        "weights": {a: round(float(w) * 100, 2) for a, w in zip(assets, risk_parity_weights)},
        "volatilities": {a: round(float(v) * 100, 2) for a, v in zip(assets, vols)},
        "risk_contributions": {a: round(float(rc) * 100, 2) for a, rc in zip(assets, risk_contributions)},
        "portfolio_volatility": round(float(portfolio_vol) * 100, 2),
    }


@router.get("/allocation")
def get_risk_parity_allocation(user=Depends(get_optional_user)):
    """Get risk parity optimal allocation."""
    result = _calculate_risk_parity_weights()

    # Traditional 60/40 comparison
    traditional = {
        "us_equity": 60.0,
        "treasury_long": 25.0,
        "intl_equity": 10.0,
        "commodities": 5.0,
    }

    # Calculate traditional risk contributions
    assets = result["assets"]
    vols = np.array([ASSET_VOLATILITY[a] for a in assets])
    n = len(assets)
    trad_weights = np.array([traditional.get(a, 0) / 100 for a in assets])
    cov = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            corr = _get_correlation(assets[i], assets[j])
            cov[i][j] = corr * vols[i] * vols[j]
    trad_vol = np.sqrt(trad_weights @ cov @ trad_weights)
    trad_marginal = cov @ trad_weights
    trad_risk_contrib = trad_weights * trad_marginal / trad_vol

    return {
        "risk_parity": result,
        "traditional_60_40": {
            "weights": {a: round(float(w) * 100, 2) for a, w in zip(assets, trad_weights) if w > 0},
            "risk_contributions": {a: round(float(rc) * 100, 2) for a, rc in zip(assets, trad_risk_contrib) if rc > 0.001},
            "portfolio_volatility": round(float(trad_vol) * 100, 2),
        },
        "comparison": {
            "risk_parity_vol": result["portfolio_volatility"],
            "traditional_vol": round(float(trad_vol) * 100, 2),
            "vol_reduction": round((1 - result["portfolio_volatility"] / (float(trad_vol) * 100)) * 100, 1),
            "risk_parity_diversification": "HIGH" if max(result["risk_contributions"].values()) < 20 else "MODERATE",
            "traditional_diversification": "LOW" if max([float(rc) for rc in trad_risk_contrib if rc > 0.001]) > 40 else "MODERATE",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/correlation")
def get_correlation_matrix(user=Depends(get_optional_user)):
    """Get the correlation matrix between asset classes."""
    assets = list(ASSET_VOLATILITY.keys())
    matrix = []

    for a in assets:
        row = {}
        for b in assets:
            row[b] = round(_get_correlation(a, b), 2)
        matrix.append({"asset": a, "correlations": row})

    # Find highest and lowest correlations
    pairs = []
    for i, a in enumerate(assets):
        for j, b in enumerate(assets):
            if i < j:
                pairs.append({"pair": f"{a} / {b}", "correlation": _get_correlation(a, b)})
    pairs.sort(key=lambda x: x["correlation"])

    return {
        "matrix": matrix,
        "assets": assets,
        "most_correlated": pairs[-3:],
        "least_correlated": pairs[:3],
        "best_hedges": [p for p in pairs if p["correlation"] < -0.1],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/volatility-target")
def volatility_targeting(
    target_vol: float = Query(default=10.0, description="Target portfolio volatility (%)"),
    user=Depends(get_optional_user),
):
    """Get volatility-targeted allocation."""
    result = _calculate_risk_parity_weights()
    current_vol = result["portfolio_volatility"]

    # Scale weights to target volatility
    scale_factor = target_vol / current_vol if current_vol > 0 else 1.0
    scaled_weights = {a: round(w * scale_factor, 2) for a, w in result["weights"].items()}
    cash_allocation = max(0, 100 - sum(scaled_weights.values()))

    return {
        "target_volatility": target_vol,
        "current_volatility": current_vol,
        "scale_factor": round(scale_factor, 3),
        "weights": scaled_weights,
        "cash_allocation": round(cash_allocation, 2),
        "expected_volatility": round(target_vol, 2),
        "description": f"Portfolio scaled to {target_vol}% target volatility. {round(cash_allocation, 1)}% in cash/reserves.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/stress-test")
def stress_test(user=Depends(get_optional_user)):
    """Stress test risk parity vs traditional allocation."""
    result = _calculate_risk_parity_weights()

    scenarios = [
        {"name": "2008 Financial Crisis", "us_equity": -0.37, "intl_equity": -0.43, "treasury_long": 0.20, "gold": 0.05, "commodities": -0.36, "high_yield_bonds": -0.26},
        {"name": "2020 COVID Crash", "us_equity": -0.34, "intl_equity": -0.33, "treasury_long": 0.15, "gold": 0.08, "commodities": -0.20, "high_yield_bonds": -0.15},
        {"name": "Rising Rates 2022", "us_equity": -0.19, "intl_equity": -0.15, "treasury_long": -0.31, "gold": -0.03, "commodities": 0.15, "high_yield_bonds": -0.10},
        {"name": "Stagflation", "us_equity": -0.20, "intl_equity": -0.15, "treasury_long": -0.10, "gold": 0.20, "commodities": 0.25, "high_yield_bonds": -0.15},
        {"name": "Deflationary Recession", "us_equity": -0.30, "intl_equity": -0.28, "treasury_long": 0.25, "gold": 0.10, "commodities": -0.15, "high_yield_bonds": -0.20},
    ]

    assets = result["assets"]
    rp_weights = np.array([result["weights"][a] / 100 for a in assets])
    trad_weights_dict = {"us_equity": 0.60, "treasury_long": 0.25, "intl_equity": 0.10, "commodities": 0.05}
    trad_weights = np.array([trad_weights_dict.get(a, 0) for a in assets])

    stress_results = []
    for scenario in scenarios:
        rp_impact = sum(rp_weights[i] * scenario.get(assets[i], 0) for i in range(len(assets)))
        trad_impact = sum(trad_weights[i] * scenario.get(assets[i], 0) for i in range(len(assets)))
        stress_results.append({
            "scenario": scenario["name"],
            "risk_parity_impact": round(float(rp_impact) * 100, 2),
            "traditional_impact": round(float(trad_impact) * 100, 2),
            "advantage": round(float(trad_impact - rp_impact) * 100, 2),
        })

    avg_rp = np.mean([s["risk_parity_impact"] for s in stress_results])
    avg_trad = np.mean([s["traditional_impact"] for s in stress_results])

    return {
        "scenarios": stress_results,
        "summary": {
            "avg_risk_parity_impact": round(float(avg_rp), 2),
            "avg_traditional_impact": round(float(avg_trad), 2),
            "risk_parity_advantage": round(float(avg_trad - avg_rp), 2),
            "worst_case_rp": round(min(s["risk_parity_impact"] for s in stress_results), 2),
            "worst_case_traditional": round(min(s["traditional_impact"] for s in stress_results), 2),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
