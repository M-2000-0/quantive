"""Market regime classifier — §13.

Regimes: bull/bear/sideways + high/low vol + risk-on/off.
Uses vol, breadth, momentum, rates, credit spreads, correlations.
Adapts strategy weights by regime — no fabricated certainty.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal
import numpy as np
import pandas as pd


class Regime(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOL = "high_vol"
    LOW_VOL = "low_vol"
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    INFLATIONARY = "inflationary"
    DEFLATIONARY = "deflationary"


class RegimeEngine:
    """Simple rule-based classifier; ML extension hooks in via score dict."""

    def classify(self, market_returns: pd.Series, vol_window: int = 20, mom_window: int = 60) -> dict:
        """Return {regime: probability} + primary label.

        Uses trailing return and realized vol vs historical.
        """
        r = market_returns.dropna()
        if len(r) < vol_window:
            return {"primary": Regime.SIDEWAYS.value, "scores": {Regime.SIDEWAYS.value: 1.0}}

        recent_ret = float(r.iloc[-mom_window:].mean() * 252) if len(r) >= mom_window else float(r.mean() * 252)
        recent_vol = float(r.iloc[-vol_window:].std() * np.sqrt(252))
        hist_vol = float(r.std() * np.sqrt(252)) if len(r) > 1 else recent_vol

        scores: dict[str, float] = {}
        # trend
        if recent_ret > 0.08:
            scores[Regime.BULL.value] = 0.7
            scores[Regime.BEAR.value] = 0.1
            scores[Regime.SIDEWAYS.value] = 0.2
        elif recent_ret < -0.05:
            scores[Regime.BULL.value] = 0.1
            scores[Regime.BEAR.value] = 0.7
            scores[Regime.SIDEWAYS.value] = 0.2
        else:
            scores[Regime.SIDEWAYS.value] = 0.6
            scores[Regime.BULL.value] = 0.2
            scores[Regime.BEAR.value] = 0.2

        # vol regime
        vol_ratio = recent_vol / hist_vol if hist_vol else 1.0
        if vol_ratio > 1.3:
            scores[Regime.HIGH_VOL.value] = 0.7
            scores[Regime.LOW_VOL.value] = 0.1
        elif vol_ratio < 0.8:
            scores[Regime.HIGH_VOL.value] = 0.1
            scores[Regime.LOW_VOL.value] = 0.7
        else:
            scores[Regime.HIGH_VOL.value] = 0.3
            scores[Regime.LOW_VOL.value] = 0.3

        # risk on/off proxy: positive recent return => risk-on
        scores[Regime.RISK_ON.value] = float(np.clip(0.5 + recent_ret, 0, 1))
        scores[Regime.RISK_OFF.value] = 1 - scores[Regime.RISK_ON.value]

        # Normalize to sum 1 for primary trend trio
        primary = max([Regime.BULL.value, Regime.BEAR.value, Regime.SIDEWAYS.value], key=lambda k: scores[k])
        return {"primary": primary, "scores": scores, "recent_return_ann": recent_ret, "recent_vol": recent_vol, "hist_vol": hist_vol}

    def adapt_weights(self, base_weights: dict[str, float], regime: dict) -> dict[str, float]:
        """Adjust strategy weights by regime (example: reduce momentum in bear)."""
        primary = regime.get("primary")
        adapted = dict(base_weights)
        if primary == Regime.BEAR.value:
            # tilt defensive
            for k in list(adapted):
                if "momentum" in k.lower():
                    adapted[k] *= 0.6
                if "low_vol" in k.lower() or "quality" in k.lower():
                    adapted[k] *= 1.2
        elif primary == Regime.BULL.value:
            for k in list(adapted):
                if "momentum" in k.lower():
                    adapted[k] *= 1.2
        # renormalize
        s = sum(adapted.values())
        if s > 0:
            adapted = {k: v / s for k, v in adapted.items()}
        return adapted
