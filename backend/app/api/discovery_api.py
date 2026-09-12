"""
Discovery API — Personalized Investment Opportunities
=======================================================

Exposes the personalized investment discovery algorithm:

- ``GET  /api/discovery/opportunities`` — personalized recommendations
  across stocks, ETFs, crypto, and alternative assets, grouped into tiers.
- ``POST /api/discovery/feedback``       — record a user interaction that
  feeds the iterative personalization loop.
- ``GET  /api/discovery/assets``         — the curated opportunity universe
  (optionally filtered by asset class).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AssetClass,
    DiscoveryAsset,
    FeedbackAction,
    User,
)
from app.security import get_current_user
from app.services.discovery_engine import (
    DiscoveryEngine,
    FeedbackLoop,
    assign_tiers,
)

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


# ── Schemas ───────────────────────────────────────────────────────────

class OpportunityOut(BaseModel):
    symbol: str
    name: str
    asset_class: str
    sector: Optional[str] = None
    geography: Optional[str] = None

    # Pillar breakdown (transparency: why did this rank here?)
    relevance: float
    riskfit: float
    trend: float
    diversity: float
    score: float
    risk_band: Optional[str] = None

    # Key comparison metrics
    annual_return_pct: Optional[float] = None
    annual_volatility_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    esg_score: Optional[float] = None
    sentiment_score: Optional[float] = None

    # Explainability
    match_reason: str = ""
    confidence: str = "medium"
    tier: str = "worth_exploring"
    data_source: str = "snapshot"


class OpportunitiesResponse(BaseModel):
    opportunities: list[OpportunityOut]
    tiers: dict[str, list[str]]  # tier name -> symbols
    user_interest: dict[str, float]  # asset class -> interest (0-1)
    profile_weights: dict[str, float]  # pillar -> weight
    count: int


class FeedbackIn(BaseModel):
    asset_symbol: str
    action: FeedbackAction
    reason: Optional[str] = None
    surfaced_rank: Optional[int] = Field(None, ge=1, le=15)
    score_at_surface: Optional[float] = Field(None, ge=0, le=1)


class FeedbackOut(BaseModel):
    status: str
    asset_symbol: str
    action: str
    updated_weights: dict[str, float]


class AssetOut(BaseModel):
    symbol: str
    name: str
    asset_class: str
    sector: Optional[str] = None
    geography: Optional[str] = None
    annual_return_pct: Optional[float] = None
    annual_volatility_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    momentum_score: Optional[float] = None
    fundamental_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    esg_score: Optional[float] = None
    liquidity_score: Optional[float] = None
    risk_band: Optional[str] = None
    tags: list[str] = []
    data_source: str = "snapshot"


# ── Endpoints ──────────────────────────────────────────────────────────

def _to_opportunity(result: dict, rank: int) -> OpportunityOut:
    asset: DiscoveryAsset = result["asset"]
    a = asset.to_dict()
    return OpportunityOut(
        symbol=a["symbol"],
        name=a["name"],
        asset_class=a["asset_class"],
        sector=a["sector"],
        geography=a["geography"],
        relevance=result["relevance"],
        riskfit=result["riskfit"],
        trend=result["trend"],
        diversity=result["diversity"],
        score=result["score"],
        risk_band=a["risk_band"],
        annual_return_pct=a["annual_return_pct"],
        annual_volatility_pct=a["annual_volatility_pct"],
        max_drawdown_pct=a["max_drawdown_pct"],
        esg_score=a["esg_score"],
        sentiment_score=a["sentiment_score"],
        match_reason=result.get("match_reason", ""),
        confidence=result.get("confidence", "medium"),
        tier=result.get("tier", "worth_exploring"),
        data_source=a["data_source"],
    )


@router.get("/opportunities", response_model=OpportunitiesResponse)
def get_opportunities(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=3, le=15),
    asset_class: Optional[AssetClass] = Query(None, description="Filter to one asset class"),
):
    """Return personalized investment opportunities for the current user."""
    engine = DiscoveryEngine(db)
    pref = engine.get_or_create_preference(user.id)

    assets = engine.universe()
    if asset_class is not None:
        assets = [a for a in assets if a.asset_class == asset_class]

    # Apply hard filters.
    excluded = set(pref.exclusions or [])
    min_esg = pref.min_esg_score
    results = []
    for a in assets:
        if a.symbol in excluded or a.name in excluded:
            continue
        if min_esg is not None and (a.esg_score is None or _floor(a.esg_score) < min_esg):
            continue
        results.append(a)

    scored = engine.score(results, pref)
    selected = engine._diversify(scored, limit)
    selected = assign_tiers(selected)

    # Attach human-readable match reasons.
    for r in selected:
        r["match_reason"] = engine._match_reason(r["asset"], pref, r["riskfit"])

    opportunities = [
        _to_opportunity(r, idx)
        for idx, r in enumerate(selected, start=1)
    ]

    tiers: dict[str, list[str]] = {
        "strong_match": [],
        "worth_exploring": [],
        "stretch_opportunity": [],
    }
    for o in opportunities:
        tiers[o.tier].append(o.symbol)

    return OpportunitiesResponse(
        opportunities=opportunities,
        tiers=tiers,
        user_interest={
            "stock": pref.interest_stock,
            "etf": pref.interest_etf,
            "crypto": pref.interest_crypto,
            "alternative": pref.interest_alternative,
        },
        profile_weights={
            "relevance": pref.weight_relevance,
            "riskfit": pref.weight_riskfit,
            "trend": pref.weight_trend,
            "diversity": pref.weight_diversity,
        },
        count=len(opportunities),
    )


@router.post("/feedback", response_model=FeedbackOut)
def record_feedback(
    payload: FeedbackIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a user interaction that refines future suggestions."""
    engine = DiscoveryEngine(db)
    asset = db.query(DiscoveryAsset).filter(DiscoveryAsset.symbol == payload.asset_symbol).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Unknown asset symbol: {payload.asset_symbol}")

    pref = engine.get_or_create_preference(user.id)
    loop = FeedbackLoop()
    loop.record(
        db,
        user_id=user.id,
        pref=pref,
        asset=asset,
        action=payload.action,
        reason=payload.reason,
        surfaced_rank=payload.surfaced_rank,
        score_at_surface=payload.score_at_surface,
    )
    return FeedbackOut(
        status="recorded",
        asset_symbol=asset.symbol,
        action=payload.action.value if hasattr(payload.action, "value") else str(payload.action),
        updated_weights={
            "relevance": pref.weight_relevance,
            "riskfit": pref.weight_riskfit,
            "trend": pref.weight_trend,
            "diversity": pref.weight_diversity,
        },
    )


@router.get("/assets", response_model=list[AssetOut])
def list_assets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    asset_class: Optional[AssetClass] = Query(None),
):
    """List the curated discovery universe (optionally filtered by class)."""
    engine = DiscoveryEngine(db)
    assets = engine.universe()
    if asset_class is not None:
        assets = [a for a in assets if a.asset_class == asset_class]
    out: list[AssetOut] = []
    for a in assets:
        d = a.to_dict()
        out.append(AssetOut(**{k: v for k, v in d.items() if k in AssetOut.model_fields}))
    return out


def _floor(value: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
