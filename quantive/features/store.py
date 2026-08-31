"""Feature Store — registry with name/source/timestamp/method/lookback/norm/missing policy.

Every feature has a stable identifier so models, backtests, and explanations
can reference the exact calculation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Literal, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class Normalization(str, Enum):
    NONE = "none"
    ZSCORE = "zscore"
    MINMAX = "minmax"
    RANK = "rank"


class MissingPolicy(str, Enum):
    DROP = "drop"
    FORWARD_FILL = "ffill"
    MEAN = "mean"
    ZERO = "zero"


class Feature(BaseModel):
    """Feature definition — immutable descriptor."""

    name: str = Field(..., description="Stable feature key, e.g. 'rsi_14'")
    source: str = Field(..., description="Data source / engine, e.g. 'technical'")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    calculation_method: str = Field(..., description="Human-readable method, e.g. 'RSI Wilder 14'")
    lookback_period: Optional[int] = Field(None, description="Lookback in bars/days")
    normalization: Normalization = Normalization.NONE
    missing_value_policy: MissingPolicy = MissingPolicy.DROP
    description: str = ""
    tags: list[str] = Field(default_factory=list)

    def label(self) -> str:
        return f"{self.name} [{self.source}/{self.calculation_method}]"


class FeatureStore:
    """Registry + computation cache for features.

    Usage:
        store = FeatureStore()
        store.register(Feature(name="sma_20", ...))
        df_feat = store.compute(df, ["sma_20","rsi_14"])
    """

    def __init__(self):
        self._registry: dict[str, Feature] = {}
        self._computors: dict[str, Callable[[pd.DataFrame], pd.Series]] = {}

    # -- registry -----------------------------------------------------------
    def register(self, feature: Feature, computor: Optional[Callable[[pd.DataFrame], pd.Series]] = None) -> None:
        if feature.name in self._registry:
            raise ValueError(f"Feature {feature.name!r} already registered")
        self._registry[feature.name] = feature
        if computor:
            self._computors[feature.name] = computor

    def get(self, name: str) -> Feature:
        if name not in self._registry:
            raise KeyError(f"Feature {name!r} not registered")
        return self._registry[name]

    def list_features(self, source: Optional[str] = None, tag: Optional[str] = None) -> list[Feature]:
        out = list(self._registry.values())
        if source:
            out = [f for f in out if f.source == source]
        if tag:
            out = [f for f in out if tag in f.tags]
        return out

    # -- computation --------------------------------------------------------
    def compute(self, df: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
        """Compute requested features, applying normalization + missing policy per feature.

        df must contain OHLCV columns. Returns df with added feature columns.
        """
        out = df.copy()
        for name in feature_names:
            feat = self.get(name)
            comp = self._computors.get(name)
            if comp is None:
                raise KeyError(f"No computor registered for feature {name!r}")
            series = comp(out)
            # normalization
            if feat.normalization == Normalization.ZSCORE:
                mu, sigma = series.mean(), series.std()
                series = (series - mu) / sigma if sigma and sigma != 0 else series * 0
            elif feat.normalization == Normalization.MINMAX:
                mn, mx = series.min(), series.max()
                series = (series - mn) / (mx - mn) if mx != mn else series * 0
            elif feat.normalization == Normalization.RANK:
                series = series.rank(pct=True)
            # missing policy
            if feat.missing_value_policy == MissingPolicy.FORWARD_FILL:
                series = series.ffill()
            elif feat.missing_value_policy == MissingPolicy.MEAN:
                series = series.fillna(series.mean())
            elif feat.missing_value_policy == MissingPolicy.ZERO:
                series = series.fillna(0)
            elif feat.missing_value_policy == MissingPolicy.DROP:
                pass  # caller decides
            out[name] = series
        return out

    def feature_importance_frame(self, importances: dict[str, float]) -> pd.DataFrame:
        """Build a sorted importance table for explainability (e.g. SHAP)."""
        rows = []
        for name, imp in importances.items():
            feat = self._registry.get(name)
            rows.append({
                "feature": name,
                "importance": float(imp),
                "source": feat.source if feat else "unknown",
                "method": feat.calculation_method if feat else "",
            })
        df = pd.DataFrame(rows).sort_values("importance", ascending=False).reset_index(drop=True)
        return df
