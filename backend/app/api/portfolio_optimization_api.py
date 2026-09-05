"""
Portfolio Optimization API (Modern Portfolio Theory)

Endpoints:
  POST /api/v1/optimizer/run           — Run MPT optimization
  GET  /api/v1/optimizer/universe      — Get default asset universe
  POST /api/v1/optimizer/custom        — Optimize custom asset list
  GET  /api/v1/optimizer/correlation   — Get correlation matrix
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

router = APIRouter(prefix="/optimizer", tags=["portfolio-optimization"])


def _get_user(request: Request, db: Session):
    token = request.cookies.get("access_token", "")
    if not token:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(token)
        if payload:
            return db.query(User).filter(User.id == payload.get("sub")).first()
    except Exception:
        pass
    return None


class OptimizeRequest(BaseModel):
    n_simulations: int = 10000
    max_weight: float = 0.40
    min_weight: float = 0.0
    risk_free_rate: float = 0.04
    include_crypto: bool = True
    include_bonds: bool = True
    include_commodities: bool = True
    target_return: Optional[float] = None


class CustomAssetRequest(BaseModel):
    assets: list  # [{symbol, name, asset_class, return, risk}]
    n_simulations: int = 10000
    max_weight: float = 0.40
    risk_free_rate: float = 0.04


@router.post("/run")
def run_optimization(data: OptimizeRequest, request: Request):
    """Run MPT optimization with the default asset universe."""
    from app.services.portfolio_optimizer import (
        PortfolioOptimizer,
        DEFAULT_OPTIMIZATION_UNIVERSE,
    )

    # Filter universe based on preferences
    universe = DEFAULT_OPTIMIZATION_UNIVERSE.copy()
    if not data.include_crypto:
        universe = [a for a in universe if a["asset_class"] != "crypto"]
    if not data.include_bonds:
        universe = [a for a in universe if a["asset_class"] != "bond"]
    if not data.include_commodities:
        universe = [a for a in universe if a["asset_class"] != "commodity"]

    if len(universe) < 2:
        return {"error": "Need at least 2 assets for optimization"}

    assets = [{"symbol": a["symbol"], "name": a["name"], "asset_class": a["asset_class"]} for a in universe]
    returns = [a["return"] for a in universe]

    optimizer = PortfolioOptimizer(
        assets, returns,
        risk_free_rate=data.risk_free_rate,
    )

    result = optimizer.optimize(
        n_simulations=data.n_simulations,
        max_weight=data.max_weight,
        min_weight=data.min_weight,
        target_return=data.target_return,
    )

    result["universe_size"] = len(universe)
    return result


@router.get("/universe")
def get_universe(request: Request):
    """Get the default asset universe for optimization."""
    from app.services.portfolio_optimizer import DEFAULT_OPTIMIZATION_UNIVERSE

    return {
        "assets": DEFAULT_OPTIMIZATION_UNIVERSE,
        "total": len(DEFAULT_OPTIMIZATION_UNIVERSE),
        "asset_classes": list(set(a["asset_class"] for a in DEFAULT_OPTIMIZATION_UNIVERSE)),
    }


@router.post("/custom")
def optimize_custom(data: CustomAssetRequest, request: Request):
    """Optimize a custom list of assets."""
    from app.services.portfolio_optimizer import PortfolioOptimizer

    if len(data.assets) < 2:
        return {"error": "Need at least 2 assets for optimization"}

    assets = [{"symbol": a.get("symbol", ""), "name": a.get("name", ""), "asset_class": a.get("asset_class", "stock")} for a in data.assets]
    returns = [a.get("return", 0.10) for a in data.assets]

    optimizer = PortfolioOptimizer(
        assets, returns,
        risk_free_rate=data.risk_free_rate,
    )

    result = optimizer.optimize(
        n_simulations=data.n_simulations,
        max_weight=data.max_weight,
    )

    result["custom_assets"] = data.assets
    return result


@router.get("/correlation")
def get_correlation(request: Request):
    """Get the correlation matrix for the default universe."""
    from app.services.portfolio_optimizer import PortfolioOptimizer, DEFAULT_OPTIMIZATION_UNIVERSE

    universe = DEFAULT_OPTIMIZATION_UNIVERSE
    assets = [{"symbol": a["symbol"], "name": a["name"], "asset_class": a["asset_class"]} for a in universe]
    returns = [a["return"] for a in universe]

    optimizer = PortfolioOptimizer(assets, returns)

    return {
        "symbols": [a["symbol"] for a in universe],
        "correlation_matrix": optimizer.correlation_matrix,
        "volatilities": [round(v * 100, 2) for v in optimizer.volatilities],
    }
