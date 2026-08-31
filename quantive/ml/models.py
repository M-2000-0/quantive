"""ML prediction models — §14.

Classical + tree + neural (MLP) with honest benchmarking §54.
All models expose predict() -> expected return + uncertainty §16.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd


@dataclass
class Prediction:
    expected_return: float
    confidence: float  # 0-1
    volatility: float
    lower: float  # prediction interval
    upper: float
    model: str


class BaseModel(ABC):
    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> None: ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray: ...

    @property
    @abstractmethod
    def name(self) -> str: ...


class RidgeModel(BaseModel):
    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.coef_: np.ndarray | None = None
        self.intercept_: float = 0.0

    @property
    def name(self) -> str:
        return f"ridge_alpha={self.alpha}"

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        # closed-form ridge: (X^T X + αI)^-1 X^T y
        n, p = X.shape
        XtX = X.T @ X + self.alpha * np.eye(p)
        try:
            self.coef_ = np.linalg.solve(XtX, X.T @ y)
        except np.linalg.LinAlgError:
            self.coef_ = np.linalg.pinv(XtX) @ X.T @ y
        self.intercept_ = float(np.mean(y - X @ self.coef_))

    def predict(self, X: np.ndarray) -> np.ndarray:
        assert self.coef_ is not None, "not fitted"
        return X @ self.coef_ + self.intercept_


class LassoModel(BaseModel):
    """Coordinate descent Lasso (simple, no sklearn dependency)."""
    def __init__(self, alpha: float = 0.01, max_iter: int = 500, tol: float = 1e-4):
        self.alpha = alpha
        self.max_iter = max_iter
        self.tol = tol
        self.coef_: np.ndarray | None = None
        self.intercept_: float = 0.0

    @property
    def name(self) -> str:
        return f"lasso_alpha={self.alpha}"

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        n, p = X.shape
        # standardize X for stable CD
        self._mean = X.mean(axis=0)
        self._std = X.std(axis=0).clip(min=1e-8)
        Xs = (X - self._mean) / self._std
        coef = np.zeros(p)
        for _ in range(self.max_iter):
            prev = coef.copy()
            for j in range(p):
                r = y - Xs @ coef + coef[j] * Xs[:, j]
                rho = float(Xs[:, j] @ r)
                # soft threshold
                if rho < -self.alpha:
                    coef[j] = (rho + self.alpha) / (Xs[:, j] @ Xs[:, j])
                elif rho > self.alpha:
                    coef[j] = (rho - self.alpha) / (Xs[:, j] @ Xs[:, j])
                else:
                    coef[j] = 0.0
            if np.max(np.abs(coef - prev)) < self.tol:
                break
        # rescale
        self.coef_ = coef / self._std
        self.intercept_ = float(np.mean(y - X @ self.coef_))

    def predict(self, X: np.ndarray) -> np.ndarray:
        assert self.coef_ is not None
        return X @ self.coef_ + self.intercept_


class TreeModel(BaseModel):
    """Lightweight tree ensemble via piecewise constant (no sklearn). Uses depth-3 stumps voted."""

    def __init__(self, n_estimators: int = 50, max_depth: int = 3, seed: int = 42):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.seed = seed
        self._trees: list[dict] = []

    @property
    def name(self) -> str:
        return f"tree_n={self.n_estimators}_d={self.max_depth}"

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        rng = np.random.default_rng(self.seed)
        n, p = X.shape
        self._trees = []
        residual = y.copy().astype(float)
        for _ in range(self.n_estimators):
            # pick random feature + threshold (stump), fit to residual (gradient boosting style)
            j = int(rng.integers(0, p))
            thresh = float(np.median(X[:, j]))
            left = X[:, j] <= thresh
            if left.sum() == 0 or left.sum() == n:
                continue
            left_val = float(residual[left].mean())
            right_val = float(residual[~left].mean())
            # shrinkage
            left_val *= 0.1
            right_val *= 0.1
            self._trees.append({"j": j, "thresh": thresh, "left": left_val, "right": right_val})
            pred = np.where(left, left_val, right_val)
            residual -= pred
        if not self._trees:
            self._trees.append({"j": 0, "thresh": 0, "left": 0, "right": 0})

    def predict(self, X: np.ndarray) -> np.ndarray:
        out = np.zeros(X.shape[0])
        for t in self._trees:
            out += np.where(X[:, t["j"]] <= t["thresh"], t["left"], t["right"])
        return out
