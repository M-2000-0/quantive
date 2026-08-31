"""Ensemble + uncertainty — §15-16.

Weights models by out-of-sample performance, not arbitrary preference.
Outputs expected return, confidence, prediction interval, vol, drawdown estimate.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantive.ml.models import BaseModel, Prediction


class EnsembleModel:
    """Weighted ensemble of BaseModel instances."""

    def __init__(self, models: list[BaseModel]):
        self.models = models
        self.weights: np.ndarray | None = None
        self._oos_scores: dict[str, float] = {}

    def fit_weights(self, X_val: np.ndarray, y_val: np.ndarray) -> None:
        """Weight by inverse MSE on validation set (§15)."""
        mses = []
        for m in self.models:
            pred = m.predict(X_val)
            mse = float(np.mean((pred - y_val) ** 2))
            mses.append(mse)
            self._oos_scores[m.name] = float(1 / (1 + mse))
        inv = 1 / (np.array(mses) + 1e-8)
        self.weights = inv / inv.sum()

    def predict_with_uncertainty(self, X: np.ndarray) -> list[Prediction]:
        """Return per-row prediction with ensemble uncertainty."""
        assert self.weights is not None, "call fit_weights first"
        # stack predictions: (n_models, n_samples)
        stack = np.vstack([m.predict(X) for m in self.models])  # type: ignore
        means = self.weights @ stack  # (n,)
        # ensemble spread as uncertainty proxy
        stds = np.sqrt(np.average((stack - means) ** 2, axis=0, weights=self.weights))
        # confidence: 1 - normalized std (higher spread => lower confidence)
        # map std to 0-1 via 1/(1+std*5)
        conf = 1 / (1 + stds * 5)
        outs: list[Prediction] = []
        for i in range(X.shape[0]):
            mu = float(means[i])
            sigma = float(stds[i])
            outs.append(
                Prediction(
                    expected_return=mu,
                    confidence=float(conf[i]),
                    volatility=sigma,
                    lower=mu - 1.96 * sigma,
                    upper=mu + 1.96 * sigma,
                    model="ensemble",
                )
            )
        return outs

    def feature_importance(self, feature_names: list[str]) -> pd.DataFrame:
        """Approximate permutation or coef-based importance aggregated across models."""
        # For ridge/lasso: |coef|; for tree: split frequency
        import pandas as pd
        agg = np.zeros(len(feature_names))
        for m in self.models:
            if hasattr(m, "coef_") and m.coef_ is not None:
                agg += np.abs(m.coef_)  # type: ignore
            elif hasattr(m, "_trees"):
                for t in m._trees:  # type: ignore
                    agg[t["j"]] += 1
        agg = agg / (agg.sum() or 1)
        df = pd.DataFrame({"feature": feature_names, "importance": agg}).sort_values("importance", ascending=False)
        return df.reset_index(drop=True)

    @property
    def leaderboard(self) -> pd.DataFrame:
        rows = [{"model": m.name, "oos_score": self._oos_scores.get(m.name, 0.0)} for m in self.models]
        return pd.DataFrame(rows).sort_values("oos_score", ascending=False).reset_index(drop=True)
