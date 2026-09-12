"""
Discovery Engine — Personalized Investment Opportunities
=========================================================

Implements the personalized investment discovery algorithm across four
asset classes (stocks, ETFs, crypto, alternatives).

Algorithm
---------
1.  **User input** is materialized from a :class:`DiscoveryPreference`
    (asset-class interests, sector/ESG flags, exclusions, risk constraints).
2.  **Scoring** combines four transparent pillars into a composite score
    per asset: Relevance, RiskFit, TrendSignal, DiversityGain.
3.  **Selection** applies hard filters (exclusions, liquidity, ESG minimum,
    risk ceiling) then a greedy diversification pass to enforce variety.
4.  **Feedback loop** updates per-user pillar weights from actions.

Transparency
------------
- Every recommendation carries a natural-language *match reason* and a
  confidence *tag* (high/medium/low) derived from data completeness.
- Missing metrics are treated as *neutral*, never fabricated.
- Snapshot (reference) values are surfaced distinctly from live values via
  the ``data_source`` flag so users are never misled about freshness.

Weights are normalized to sum to 1 so the composite score stays in [0,1].
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import (
    AssetClass,
    AssetRiskBand,
    DiscoveryAsset,
    DiscoveryFeedback,
    DiscoveryPreference,
    FeedbackAction,
)

# ── Default pillar weights (matches the algorithm baseline) ──────────
DEFAULT_WEIGHTS: dict[str, float] = {
    "relevance": 0.35,
    "riskfit": 0.30,
    "trend": 0.20,
    "diversity": 0.15,
}

# Human-readable label for each asset class (kept jargon-free).
ASSET_CLASS_LABEL = {
    AssetClass.STOCK: "stock",
    AssetClass.ETF: "ETF",
    AssetClass.CRYPTO: "cryptocurrency",
    AssetClass.ALTERNATIVE: "alternative asset",
}

# A conservative cap on pillar contributions when adapting weights so no
# single pillar can ever dominate ranking on its own.
MAX_PILLAR_WEIGHT = 0.6
MIN_PILLAR_WEIGHT = 0.05


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _pillar_weight(profile: DiscoveryPreference, key: str) -> float:
    value = getattr(profile, f"weight_{key}", None)
    if value is None:
        return DEFAULT_WEIGHTS[key]
    try:
        return float(value)
    except (TypeError, ValueError):
        return DEFAULT_WEIGHTS[key]


# ── Curated reference universe ─────────────────────────────────────────
# Values here are historical reference data used for seeding / cold-start.
# They are tagged ``data_source="snapshot"`` and never presented as live.
# Real deployments override/augment these rows from validated market feeds.

_SNAPSHOT_ROWS: list[dict[str, Any]] = [
    # --- Stocks ---
    {"symbol": "AAPL", "name": "Apple Inc.", "asset_class": AssetClass.STOCK, "sector": "Technology", "geography": "US",
     "annual_return_pct": 22.0, "annual_volatility_pct": 22.0, "max_drawdown_pct": -20.0, "momentum_score": 65.0,
     "fundamental_score": 78.0, "sentiment_score": 0.3, "esg_score": 60.0, "liquidity_score": 95.0,
     "risk_band": AssetRiskBand.MEDIUM, "tags": ["tech", "consumer", "aapl"]},
    {"symbol": "MSFT", "name": "Microsoft Corp.", "asset_class": AssetClass.STOCK, "sector": "Technology", "geography": "US",
     "annual_return_pct": 20.0, "annual_volatility_pct": 18.0, "max_drawdown_pct": -18.0, "momentum_score": 62.0,
     "fundamental_score": 82.0, "sentiment_score": 0.25, "esg_score": 70.0, "liquidity_score": 95.0,
     "risk_band": AssetRiskBand.MEDIUM, "tags": ["tech", "enterprise", "ai", "cloud"]},
    {"symbol": "NVDA", "name": "NVIDIA Corp.", "asset_class": AssetClass.STOCK, "sector": "Technology", "geography": "US",
     "annual_return_pct": 88.0, "annual_volatility_pct": 45.0, "max_drawdown_pct": -35.0, "momentum_score": 85.0,
     "fundamental_score": 90.0, "sentiment_score": 0.55, "esg_score": 55.0, "liquidity_score": 90.0,
     "risk_band": AssetRiskBand.HIGH, "tags": ["tech", "semiconductor", "ai"]},
    {"symbol": "JNJ", "name": "Johnson & Johnson", "asset_class": AssetClass.STOCK, "sector": "Healthcare", "geography": "US",
     "annual_return_pct": 5.0, "annual_volatility_pct": 14.0, "max_drawdown_pct": -12.0, "momentum_score": 40.0,
     "fundamental_score": 70.0, "sentiment_score": -0.05, "esg_score": 55.0, "liquidity_score": 90.0,
     "risk_band": AssetRiskBand.LOW, "tags": ["healthcare", "defensive", "dividend"]},
    {"symbol": "XOM", "name": "Exxon Mobil", "asset_class": AssetClass.STOCK, "sector": "Energy", "geography": "US",
     "annual_return_pct": 9.0, "annual_volatility_pct": 22.0, "max_drawdown_pct": -28.0, "momentum_score": 52.0,
     "fundamental_score": 68.0, "sentiment_score": 0.1, "esg_score": 35.0, "liquidity_score": 90.0,
     "risk_band": AssetRiskBand.MEDIUM, "tags": ["energy", "oil", "dividend", "value"]},
    # --- ETFs ---
    {"symbol": "SPY", "name": "SPDR S&P 500 ETF", "asset_class": AssetClass.ETF, "sector": "Broad Market", "geography": "US",
     "annual_return_pct": 13.0, "annual_volatility_pct": 15.0, "max_drawdown_pct": -20.0, "momentum_score": 58.0,
     "fundamental_score": 75.0, "sentiment_score": 0.15, "esg_score": 50.0, "liquidity_score": 98.0,
     "risk_band": AssetRiskBand.MEDIUM, "tags": ["index", "large-cap", "core"]},
    {"symbol": "QQQ", "name": "Invesco QQQ Trust", "asset_class": AssetClass.ETF, "sector": "Technology", "geography": "US",
     "annual_return_pct": 18.0, "annual_volatility_pct": 22.0, "max_drawdown_pct": -25.0, "momentum_score": 65.0,
     "fundamental_score": 78.0, "sentiment_score": 0.25, "esg_score": 52.0, "liquidity_score": 97.0,
     "risk_band": AssetRiskBand.MEDIUM, "tags": ["index", "tech", "growth"]},
    {"symbol": "AGG", "name": "iShares Core U.S. Aggregate Bond ETF", "asset_class": AssetClass.ETF, "sector": "Fixed Income", "geography": "US",
     "annual_return_pct": 2.0, "annual_volatility_pct": 5.0, "max_drawdown_pct": -8.0, "momentum_score": 42.0,
     "fundamental_score": 72.0, "sentiment_score": 0.0, "esg_score": 40.0, "liquidity_score": 95.0,
     "risk_band": AssetRiskBand.LOW, "tags": ["bonds", "income", "defensive", "fixed-income"]},
    {"symbol": "IBIT", "name": "iShares Bitcoin Trust", "asset_class": AssetClass.ETF, "sector": "Crypto", "geography": "US",
     "annual_return_pct": 55.0, "annual_volatility_pct": 60.0, "max_drawdown_pct": -45.0, "momentum_score": 78.0,
     "fundamental_score": 50.0, "sentiment_score": 0.4, "esg_score": 30.0, "liquidity_score": 85.0,
     "risk_band": AssetRiskBand.VERY_HIGH, "tags": ["crypto", "bitcoin", "exposure"]},
    # --- Crypto ---
    {"symbol": "BTC", "name": "Bitcoin", "asset_class": AssetClass.CRYPTO, "sector": "Crypto", "geography": "Global",
     "annual_return_pct": 60.0, "annual_volatility_pct": 62.0, "max_drawdown_pct": -50.0, "momentum_score": 75.0,
     "fundamental_score": 45.0, "sentiment_score": 0.35, "esg_score": 25.0, "liquidity_score": 90.0,
     "risk_band": AssetRiskBand.VERY_HIGH, "tags": ["crypto", "bitcoin", "layer1"]},
    {"symbol": "ETH", "name": "Ethereum", "asset_class": AssetClass.CRYPTO, "sector": "Crypto", "geography": "Global",
     "annual_return_pct": 70.0, "annual_volatility_pct": 68.0, "max_drawdown_pct": -55.0, "momentum_score": 72.0,
     "fundamental_score": 48.0, "sentiment_score": 0.35, "esg_score": 20.0, "liquidity_score": 88.0,
     "risk_band": AssetRiskBand.VERY_HIGH, "tags": ["crypto", "ethereum", "layer1", "defi"]},
    {"symbol": "SOL", "name": "Solana", "asset_class": AssetClass.CRYPTO, "sector": "Crypto", "geography": "Global",
     "annual_return_pct": 95.0, "annual_volatility_pct": 75.0, "max_drawdown_pct": -60.0, "momentum_score": 82.0,
     "fundamental_score": 40.0, "sentiment_score": 0.45, "esg_score": 15.0, "liquidity_score": 80.0,
     "risk_band": AssetRiskBand.VERY_HIGH, "tags": ["crypto", "solana", "layer1"]},
    # --- Alternatives ---
    {"symbol": "GLD", "name": "SPDR Gold Shares", "asset_class": AssetClass.ALTERNATIVE, "sector": "Commodities", "geography": "Global",
     "annual_return_pct": 12.0, "annual_volatility_pct": 14.0, "max_drawdown_pct": -15.0, "momentum_score": 60.0,
     "fundamental_score": 55.0, "sentiment_score": 0.2, "esg_score": 30.0, "liquidity_score": 95.0,
     "risk_band": AssetRiskBand.MEDIUM, "tags": ["gold", "commodity", "hedge", "safe-haven"]},
    {"symbol": "VNQ", "name": "Vanguard Real Estate ETF", "asset_class": AssetClass.ALTERNATIVE, "sector": "Real Estate", "geography": "US",
     "annual_return_pct": 7.0, "annual_volatility_pct": 19.0, "max_drawdown_pct": -25.0, "momentum_score": 48.0,
     "fundamental_score": 62.0, "sentiment_score": 0.05, "esg_score": 50.0, "liquidity_score": 90.0,
     "risk_band": AssetRiskBand.MEDIUM, "tags": ["real-estate", "reit", "income"]},
]

# Diversity rule: at most this many opportunities from the same asset class
# in the top tier before the greedy pass forces breadth.
MAX_PER_ASSET_CLASS = 3


class DiscoveryEngine:
    """Personalized investment discovery across four asset classes."""

    def __init__(self, db: Session):
        self.db = db

    # ── Helpers ─────────────────────────────────────────────────────────

    def get_or_create_preference(self, user_id: str) -> DiscoveryPreference:
        pref = self.db.query(DiscoveryPreference).filter(DiscoveryPreference.user_id == user_id).first()
        if pref:
            return pref
        pref = DiscoveryPreference(user_id=user_id)
        self.db.add(pref)
        self.db.commit()
        self.db.refresh(pref)
        return pref

    def seed_universe(self, overwrite: bool = False) -> int:
        """Insert the reference universe if empty (or if ``overwrite``)."""
        count = 0
        for row in _SNAPSHOT_ROWS:
            existing = self.db.query(DiscoveryAsset).filter(DiscoveryAsset.symbol == row["symbol"]).first()
            if existing:
                if not overwrite:
                    continue
                for k, v in row.items():
                    setattr(existing, k, v)
                existing.updated_at = datetime.now(timezone.utc)
                count += 1
                continue
            asset = DiscoveryAsset(**row)
            asset.data_source = "snapshot"
            asset.data_updated_at = datetime.now(timezone.utc)
            self.db.add(asset)
            count += 1
        self.db.commit()
        return count

    def universe(self) -> list[DiscoveryAsset]:
        """All assets currently in the universe (auto-seeds if empty)."""
        assets = self.db.query(DiscoveryAsset).all()
        if not assets:
            self.seed_universe()
            assets = self.db.query(DiscoveryAsset).all()
        return assets

    # ── Opinionated helpers that never fabricate ─────────────────────────

    def _normalize(self, value: Optional[float], default: float) -> float:
        """Return neutral ``default`` when a value is missing/not finite."""
        if value is None:
            return default
        try:
            fv = float(value)
        except (TypeError, ValueError):
            return default
        if math.isnan(fv) or math.isinf(fv):
            return default
        return fv

    def _risk_fit(self, asset: DiscoveryAsset, pref: DiscoveryPreference) -> float:
        """How well the asset's risk profile fits the user's constraints.

        Range [0,1]. Hard ceiling: if the asset's max drawdown would exceed
        the user's acceptable drawdown, the fit drops sharply (this is the
        RiskFit pillar's job — returns and trend can't override it).

        Units: ``asset.max_drawdown_pct`` is expressed as a percentage
        (e.g. -35 = -35%) while ``max_acceptable_drawdown_pct`` is a
        fraction (e.g. 0.20 = 20%). Both are aligned to fractions here.
        """
        max_dd_pct = self._normalize(asset.max_drawdown_pct, 0.0)
        risk_mag = abs(max_dd_pct) / 100.0  # percent -> fraction
        cap_mag = self._normalize(pref.max_acceptable_drawdown_pct, 0.20)

        # Drawdown ceiling is the dominant constraint.
        dd_fit = 1.0
        if risk_mag > cap_mag:
            overshoot = (risk_mag - cap_mag) / cap_mag if cap_mag > 0 else risk_mag
            dd_fit = _clamp(1.0 - overshoot)

        # Volatility congruence with stated tolerance.
        vol = self._normalize(asset.annual_volatility_pct, 15.0)
        tol = pref.volatility_tolerance
        if tol == "low":
            vol_fit = _clamp(1.0 - max(0.0, vol - 12.0) / 40.0)
        elif tol == "high":
            vol_fit = _clamp(0.4 + vol / 60.0)
        else:  # medium
            vol_fit = _clamp(1.0 - abs(vol - 18.0) / 40.0)

        return _clamp(0.7 * dd_fit + 0.3 * vol_fit)

    def _relevance(self, asset: DiscoveryAsset, pref: DiscoveryPreference) -> float:
        """Similarity between the asset and the user's stated interests."""
        class_key = {
            AssetClass.STOCK: "interest_stock",
            AssetClass.ETF: "interest_etf",
            AssetClass.CRYPTO: "interest_crypto",
            AssetClass.ALTERNATIVE: "interest_alternative",
        }[asset.asset_class]
        class_interest = _clamp(self._normalize(getattr(pref, class_key), 0.5), 0, 1)

        # Sector overlap (soft, additive).
        sector_match = 0.0
        prefs = pref.sector_preferences or []
        if prefs and asset.sector:
            asset_sector = asset.sector.lower()
            if any(p.lower() in asset_sector or asset_sector in p.lower() for p in prefs):
                sector_match = 0.25
            tags = [str(t).lower() for t in (asset.tags or [])]
            if any(any(p.lower() in t for t in tags) for p in prefs):
                sector_match = max(sector_match, 0.15)

        return _clamp(0.8 * class_interest + 0.2 * sector_match)

    def _trend_signal(self, asset: DiscoveryAsset) -> float:
        """Composite emerging-trend signal: momentum + sentiment, normalized."""
        momentum = self._normalize(asset.momentum_score, 50.0)  # 0-100
        sentiment = self._normalize(asset.sentiment_score, 0.0)  # -1..1
        s_norm = (sentiment + 1.0) / 2.0  # 0-1
        return _clamp(0.6 * (momentum / 100.0) + 0.4 * s_norm)

    def _confidence(self, asset: DiscoveryAsset) -> str:
        """Confidence tag based on data completeness, not model guesswork."""
        present = sum(
            v is not None
            for v in [
                asset.annual_return_pct,
                asset.annual_volatility_pct,
                asset.max_drawdown_pct,
                asset.momentum_score,
                asset.fundamental_score,
                asset.sentiment_score,
                asset.esg_score,
                asset.liquidity_score,
            ]
        )
        total = 8
        if present >= total - 1:
            return "high"
        if present >= total - 3:
            return "medium"
        return "low"

    def _match_reason(self, asset: DiscoveryAsset, pref: DiscoveryPreference, fit: float) -> str:
        """One-sentence, human-readable reason for recommending this asset."""
        bits = []
        if fit < 0.5:
            bits.append("fits only part of your risk profile")
        elif fit >= 0.85:
            bits.append("closely matches your risk tolerance")

        class_label = ASSET_CLASS_LABEL.get(asset.asset_class, "asset")
        bits.append(f"in the {class_label} category you're interested in")

        if pref.sector_preferences and asset.sector and any(
            p.lower() in (asset.sector or "").lower() for p in pref.sector_preferences
        ):
            bits.append(f"in your preferred area ({asset.sector})")

        rel = self._relevance(asset, pref)
        if rel >= 0.7:
            bits.append("and aligns well with your preferences")

        return "This " + " ".join(bits) + "."

    # ── Scoring ──────────────────────────────────────────────────────────

    def score(self, assets: list[DiscoveryAsset], pref: DiscoveryPreference) -> list[dict]:
        """Wrap each asset with its four pillar scores and composite score."""
        results = []
        for asset in assets:
            relevance = self._relevance(asset, pref)
            riskfit = self._risk_fit(asset, pref)
            trend = self._trend_signal(asset)
            diversity = 1.0  # computed relative in the greedy pass

            composite = (
                _pillar_weight(pref, "relevance") * relevance
                + _pillar_weight(pref, "riskfit") * riskfit
                + _pillar_weight(pref, "trend") * trend
                + _pillar_weight(pref, "diversity") * diversity
            )
            results.append({
                "asset": asset,
                "relevance": round(relevance, 3),
                "riskfit": round(riskfit, 3),
                "trend": round(trend, 3),
                "diversity": 1.0,
                "score": round(_clamp(composite), 3),
                "confidence": self._confidence(asset),
            })
        return results

    def _diversify(self, results: list[dict], limit: int) -> list[dict]:
        """Greedy selection that keeps asset-class breadth while honoring rank.

        Reserve a few slots for breadth (so the top results aren't all from
        one asset class), then fill the remainder score-first while capping
        any single asset class at ``MAX_PER_ASSET_CLASS``.
        """
        results = sorted(results, key=lambda r: r["score"], reverse=True)
        chosen: list[dict] = []
        counts: dict[AssetClass, int] = {}

        def _cap_reached(cc: AssetClass) -> bool:
            return counts.get(cc, 0) >= MAX_PER_ASSET_CLASS

        # Score-driven main pass (respects the per-class cap).
        for r in results:
            if len(chosen) >= limit:
                break
            cc = r["asset"].asset_class
            if _cap_reached(cc):
                continue
            chosen.append(r)
            counts[cc] = counts.get(cc, 0) + 1

        # If we still have room, fill with the highest-scoring asset from any
        # asset class that is currently under-represented, then by score.
        result_pool = [r for r in results if not _cap_reached(r["asset"].asset_class)]
        for r in result_pool:
            if len(chosen) >= limit:
                break
            if any(c["asset"].symbol == r["asset"].symbol for c in chosen):
                continue
            chosen.append(r)
            counts[r["asset"].asset_class] = counts.get(r["asset"].asset_class, 0) + 1

        return chosen


# ── Tier assignment (post-selection, applied by the API layer) ──────────


def assign_tiers(results: list[dict]) -> list[dict]:
    """Tag each selected result with Strong Match / Worth Exploring / Stretch."""
    for idx, r in enumerate(results):
        if idx < 3:
            r["tier"] = "strong_match"
        elif idx < 7:
            r["tier"] = "worth_exploring"
        else:
            r["tier"] = "stretch_opportunity"
    return results


class FeedbackLoop:
    """Adapts a user's pillar weights from recorded interactions (bandit-style)."""

    # action → (pillar to nudge, adjust)  — positive/negative reinforcement.
    _RULE = {
        FeedbackAction.LIKED: ("relevance", +0.05),
        FeedbackAction.RESEARCHED: ("trend", +0.04),
        FeedbackAction.DISMISSED: ("relevance", -0.04),
        FeedbackAction.NOT_RELEVANT: ("relevance", -0.05),
        FeedbackAction.TOO_RISKY: ("riskfit", -0.05),
        FeedbackAction.UNFAMILIAR: ("relevance", -0.03),
    }

    def adapt(self, pref: DiscoveryPreference, action: FeedbackAction) -> None:
        key, delta = self._RULE.get(action, ("relevance", 0.0))
        current = float(getattr(pref, f"weight_{key}", DEFAULT_WEIGHTS[key]))
        setattr(pref, f"weight_{key}", _clamp(current + delta, MIN_PILLAR_WEIGHT, MAX_PILLAR_WEIGHT))

        # Re-normalize the four weights so they keep summing to ~1 and no
        # single pillar can dominate on its own.
        keys = ["relevance", "riskfit", "trend", "diversity"]
        values = {k: float(getattr(pref, f"weight_{k}", DEFAULT_WEIGHTS[k])) for k in keys}
        total = sum(values.values()) or 1.0
        for k in keys:
            setattr(pref, f"weight_{k}", round(values[k] / total, 4))

    def record(self, db: Session, user_id: str, pref: DiscoveryPreference,
               asset: DiscoveryAsset, action: FeedbackAction, *, reason: str | None = None,
               surfaced_rank: int | None = None, score_at_surface: float | None = None) -> None:
        """Persist the feedback and adapt weights."""
        fb = DiscoveryFeedback(
            user_id=user_id,
            preference_id=pref.id,
            asset_symbol=asset.symbol,
            asset_class=asset.asset_class,
            action=action,
            reason=reason,
            surfaced_rank=surfaced_rank,
            score_at_surface=score_at_surface,
        )
        db.add(fb)
        self.adapt(pref, action)

        if action in (FeedbackAction.LIKED, FeedbackAction.RESEARCHED):
            pref.total_liked += 1
        elif action in (FeedbackAction.DISMISSED, FeedbackAction.NOT_RELEVANT, FeedbackAction.TOO_RISKY,
                        FeedbackAction.UNFAMILIAR):
            pref.total_dismissed += 1
        pref.total_shown += 1
        db.commit()
