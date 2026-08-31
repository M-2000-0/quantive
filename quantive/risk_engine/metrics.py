"""Pure risk metric calculations — no I/O, tested independently."""
from __future__ import annotations

import numpy as np
import pandas as pd


class RiskMetrics:
    """Namespace for risk calculations on return series / weights."""

    @staticmethod
    def volatility(returns: np.ndarray, annualize: int = 252) -> float:
        return float(np.std(returns, ddof=1) * np.sqrt(annualize)) if len(returns) > 1 else 0.0

    @staticmethod
    def downside_deviation(returns: np.ndarray, annualize: int = 252) -> float:
        downside = returns[returns < 0]
        if len(downside) == 0:
            return 0.0
        return float(np.std(downside, ddof=1) * np.sqrt(annualize))

    @staticmethod
    def sharpe(returns: np.ndarray, rf: float = 0.0, annualize: int = 252) -> float:
        if len(returns) < 2:
            return 0.0
        excess = returns - rf / annualize
        vol = np.std(excess, ddof=1) * np.sqrt(annualize)
        if vol == 0:
            return 0.0
        return float(np.mean(excess) * annualize / vol)

    @staticmethod
    def sortino(returns: np.ndarray, rf: float = 0.0, annualize: int = 252) -> float:
        dd = RiskMetrics.downside_deviation(returns, annualize)
        if dd == 0:
            return 0.0
        return float(np.mean(returns - rf / annualize) * annualize / dd)

    @staticmethod
    def max_drawdown(cumulative: np.ndarray) -> float:
        """Max DD from cumulative value series (e.g. cumprod(1+ret))."""
        if len(cumulative) == 0:
            return 0.0
        peak = np.maximum.accumulate(cumulative)
        dd = (cumulative - peak) / np.where(peak != 0, peak, 1)
        return float(np.min(dd))

    @staticmethod
    def var(returns: np.ndarray, alpha: float = 0.05) -> float:
        """Historical VaR (negative number)."""
        if len(returns) == 0:
            return 0.0
        return float(np.quantile(returns, alpha))

    @staticmethod
    def cvar(returns: np.ndarray, alpha: float = 0.05) -> float:
        """Historical CVaR (expected shortfall)."""
        if len(returns) == 0:
            return 0.0
        v = RiskMetrics.var(returns, alpha)
        tail = returns[returns <= v]
        return float(tail.mean()) if len(tail) else v

    @staticmethod
    def beta(asset_returns: np.ndarray, market_returns: np.ndarray) -> float:
        if len(asset_returns) < 2 or len(market_returns) < 2:
            return 0.0
        n = min(len(asset_returns), len(market_returns))
        a, m = asset_returns[-n:], market_returns[-n:]
        cov = np.cov(a, m, ddof=1)[0, 1]
        var_m = np.var(m, ddof=1)
        return float(cov / var_m) if var_m != 0 else 0.0

    @staticmethod
    def correlation_matrix(returns_df: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
        return returns_df.corr(method=method)

    @staticmethod
    def concentration(weights: np.ndarray) -> dict:
        """HHI + top-N concentration."""
        w = np.asarray(weights, dtype=float)
        w = w[w > 1e-12]
        if len(w) == 0:
            return {"hhi": 0.0, "top1": 0.0, "top5": 0.0, "effective_n": 0.0}
        hhi = float(np.sum(w**2))
        w_sorted = np.sort(w)[::-1]
        return {
            "hhi": hhi,
            "top1": float(w_sorted[0]),
            "top5": float(w_sorted[:5].sum()),
            "effective_n": float(1 / hhi) if hhi else 0.0,
        }
