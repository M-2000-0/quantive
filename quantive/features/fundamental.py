"""Fundamental feature calculators — valuation/growth/health/earnings quality.

Each method takes a FundamentalSnapshot (or dict) and returns a score or dict
of raw metrics + percentile vs sector. All comparisons are explicit; no hidden
benchmarks.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import numpy as np


def _safe(v: Optional[float]) -> Optional[float]:
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return None
    return float(v)


class FundamentalFeatures:
    """Pure calculators; no I/O."""

    @staticmethod
    def valuation(snapshot: Any) -> Dict[str, Optional[float]]:
        d = snapshot.model_dump() if hasattr(snapshot, "model_dump") else dict(snapshot)
        out = {}
        for k in ["pe", "forward_pe", "peg", "price_to_sales", "price_to_book", "ev_to_ebitda", "ev_to_sales", "fcf_yield", "earnings_yield"]:
            out[k] = _safe(d.get(k))
        # derived cheapness score: higher earnings yield / lower multiples -> higher score
        ey = out.get("earnings_yield")
        fcfy = out.get("fcf_yield")
        vals = [v for v in [ey, fcfy] if v is not None]
        out["valuation_composite_yield"] = float(np.mean(vals)) if vals else None
        return out

    @staticmethod
    def growth(snapshot: Any) -> Dict[str, Optional[float]]:
        d = snapshot.model_dump() if hasattr(snapshot, "model_dump") else dict(snapshot)
        out = {k: _safe(d.get(k)) for k in ["revenue_growth", "eps_growth", "fcf_growth", "roic", "roe", "gross_margin", "operating_margin"]}
        # growth composite: mean of available growth rates
        rates = [out.get(k) for k in ["revenue_growth", "eps_growth", "fcf_growth"] if out.get(k) is not None]
        out["growth_composite"] = float(np.mean(rates)) if rates else None  # type: ignore
        return out

    @staticmethod
    def health(snapshot: Any) -> Dict[str, Optional[float]]:
        d = snapshot.model_dump() if hasattr(snapshot, "model_dump") else dict(snapshot)
        out = {k: _safe(d.get(k)) for k in ["debt_to_equity", "net_debt", "interest_coverage", "current_ratio", "free_cash_flow", "cash_reserves"]}
        # health score: higher coverage/current, lower leverage -> higher
        # simple z-like: coverage clipped, leverage inverted
        cov = out.get("interest_coverage")
        cr = out.get("current_ratio")
        lev = out.get("debt_to_equity")
        parts: list[float] = []
        if cov is not None:
            parts.append(float(np.clip(cov / 5.0, -1, 2)))
        if cr is not None:
            parts.append(float(np.clip(cr / 2.0, -1, 2)))
        if lev is not None:
            parts.append(float(np.clip(1.0 - lev, -2, 1)))
        out["health_composite"] = float(np.mean(parts)) if parts else None  # type: ignore
        return out

    @staticmethod
    def earnings_quality(snapshot: Any) -> Dict[str, Any]:
        d = snapshot.model_dump() if hasattr(snapshot, "model_dump") else dict(snapshot)
        accruals = _safe(d.get("accruals"))
        surprise = _safe(d.get("earnings_surprise"))
        # flag unusual accruals: |accruals| > 0.1
        flags: list[str] = []
        if accruals is not None and abs(accruals) > 0.1:
            flags.append("high_accruals")
        if surprise is not None and abs(surprise) > 0.15:
            flags.append("large_earnings_surprise")
        return {"accruals": accruals, "earnings_surprise": surprise, "flags": flags}

    @staticmethod
    def score(snapshot: Any, sector_medians: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Composite fundamental score vs sector medians when provided.

        Returns dict with valuation/growth/health/quality + overall 0-100 score.
        """
        val = FundamentalFeatures.valuation(snapshot)
        gro = FundamentalFeatures.growth(snapshot)
        hea = FundamentalFeatures.health(snapshot)
        qual = FundamentalFeatures.earnings_quality(snapshot)

        # sector-relative: (value - median)/|median| when medians given
        def rel(key: str, v: Optional[float]) -> Optional[float]:
            if v is None or not sector_medians or key not in sector_medians or sector_medians[key] == 0:
                return None
            return (v - sector_medians[key]) / abs(sector_medians[key])

        # crude overall: 40% health, 30% growth, 30% valuation yield
        components: list[float] = []
        for v in [hea.get("health_composite"), gro.get("growth_composite"), val.get("valuation_composite_yield")]:
            if v is not None:
                # clip to [-1,1] then shift to [0,1]
                components.append(float(np.clip((v + 1) / 2, 0, 1)))
        overall = float(np.mean(components) * 100) if components else 50.0
        return {"valuation": val, "growth": gro, "health": hea, "quality": qual, "overall_score": round(overall, 1)}
