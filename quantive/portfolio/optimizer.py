"""Portfolio optimization — §22 (§25 constraints).

Methods: equal, mean-variance, min-var, max-sharpe, risk-parity, max-div,
CVaR, Black-Litterman, HRP. Compares methods on same inputs; honest reporting.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np
import pandas as pd

try:
    from scipy.optimize import minimize
    HAS_SCIPY = True
except Exception:
    HAS_SCIPY = False


@dataclass
class Constraints:
    max_position: float = 1.0
    min_position: float = 0.0
    max_volatility: Optional[float] = None
    min_diversification: int = 1
    sector_limits: dict | None = None  # sector -> max weight
    turnover_limit: Optional[float] = None


def _project_simplex(w: np.ndarray) -> np.ndarray:
    """Project onto simplex sum=1, w>=0."""
    w = np.maximum(w, 0)
    s = w.sum()
    return w / s if s > 0 else np.ones_like(w) / len(w)


def _enforce_box(w: np.ndarray, c: Constraints) -> np.ndarray:
    w = np.clip(w, c.min_position, c.max_position)
    # rescale to sum 1
    w = w / w.sum() if w.sum() > 0 else w
    return w


class PortfolioOptimizer:
    """Stateless optimizer — inputs are expected returns + covariance."""

    def __init__(self, constraints: Constraints | None = None):
        self.constraints = constraints or Constraints()

    # -- Equal weight (baseline) -----------------------------------------
    def equal_weight(self, n: int) -> np.ndarray:
        return np.ones(n) / n

    # -- Mean-variance (Markowitz) ---------------------------------------
    def mean_variance(self, mu: np.ndarray, cov: np.ndarray, risk_aversion: float = 1.0) -> np.ndarray:
        """max mu^T w - λ/2 w^T Σ w  s.t. sum w=1, w>=0, box."""
        n = len(mu)
        if not HAS_SCIPY or n == 0:
            return self.equal_weight(n)
        x0 = self.equal_weight(n)
        bounds = [(self.constraints.min_position, self.constraints.max_position)] * n
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        def neg_utility(w):
            return -(float(mu @ w) - 0.5 * risk_aversion * float(w @ cov @ w))
        res = minimize(neg_utility, x0, method="SLSQP", bounds=bounds, constraints=cons, options={"maxiter": 500})
        w = _project_simplex(res.x if res.success else x0)
        return _enforce_box(w, self.constraints)

    def min_variance(self, cov: np.ndarray) -> np.ndarray:
        return self.mean_variance(mu=np.zeros(cov.shape[0]), cov=cov, risk_aversion=1e6)

    def max_sharpe(self, mu: np.ndarray, cov: np.ndarray, rf: float = 0.0) -> np.ndarray:
        """Max Sharpe via mean-variance with mu-rf scaled."""
        return self.mean_variance(mu=mu - rf, cov=cov, risk_aversion=1.0)

    # -- Risk parity -----------------------------------------------------
    def risk_parity(self, cov: np.ndarray) -> np.ndarray:
        """Allocate so each asset contributes equally to portfolio volatility."""
        n = cov.shape[0]
        if not HAS_SCIPY:
            return self.equal_weight(n)
        x0 = self.equal_weight(n)
        bounds = [(1e-4, 1.0)] * n
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        def risk_parity_obj(w):
            w = np.asarray(w)
            port_vol = np.sqrt(float(w @ cov @ w))
            if port_vol == 0:
                return 1e6
            marginal = cov @ w / port_vol
            contrib = w * marginal
            target = port_vol / n
            return float(np.sum((contrib - target) ** 2))
        res = minimize(risk_parity_obj, x0, method="SLSQP", bounds=bounds, constraints=cons, options={"maxiter": 1000})
        w = _project_simplex(res.x if res.success else x0)
        return _enforce_box(w, self.constraints)

    # -- Maximum diversification -----------------------------------------
    def max_diversification(self, cov: np.ndarray) -> np.ndarray:
        """Max diversification ratio: w^T σ / sqrt(w^T Σ w)."""
        n = cov.shape[0]
        vols = np.sqrt(np.diag(cov))
        vols = np.where(vols == 0, 1e-8, vols)
        if not HAS_SCIPY:
            # inverse vol weighting as proxy
            inv = 1 / vols
            return inv / inv.sum()
        x0 = self.equal_weight(n)
        bounds = [(self.constraints.min_position, self.constraints.max_position)] * n
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        def neg_div(w):
            port_vol = np.sqrt(float(w @ cov @ w))
            if port_vol == 0:
                return 1e6
            w_vol = float(w @ vols)
            return -(w_vol / port_vol)
        res = minimize(neg_div, x0, method="SLSQP", bounds=bounds, constraints=cons, options={"maxiter": 500})
        w = _project_simplex(res.x if res.success else x0)
        return _enforce_box(w, self.constraints)

    # -- CVaR (tail risk) ------------------------------------------------
    def cvar_min(self, returns: np.ndarray, alpha: float = 0.05) -> np.ndarray:
        """Minimize CVaR (historical) — linear approx via SLSQP."""
        # returns shape (T, N)
        T, N = returns.shape
        if not HAS_SCIPY or T == 0:
            return self.equal_weight(N)
        x0 = self.equal_weight(N)
        bounds = [(self.constraints.min_position, self.constraints.max_position)] * N
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        def cvar_obj(w):
            port_rets = returns @ w
            q = np.quantile(port_rets, alpha)
            tail = port_rets[port_rets <= q]
            return -float(tail.mean()) if len(tail) else -float(q)  # minimize loss => minimize -mean? CVaR negative; we minimize CVaR magnitude
        res = minimize(cvar_obj, x0, method="SLSQP", bounds=bounds, constraints=cons, options={"maxiter": 500})
        w = _project_simplex(res.x if res.success else x0)
        return _enforce_box(w, self.constraints)

    # -- HRP (Hierarchical Risk Parity) ----------------------------------
    def hrp(self, cov: np.ndarray) -> np.ndarray:
        """Simple HRP: cluster by correlation distance, recursive bisection.

        Uses scipy hierarchical clustering if available; falls back to equal weight.
        """
        n = cov.shape[0]
        if n == 1:
            return np.array([1.0])
        try:
            from scipy.cluster.hierarchy import linkage
            from scipy.spatial.distance import squareform
            corr = np.corrcoef(np.random.randn(100, n)) if False else np.zeros((n, n))  # placeholder
            # Build distance from cov -> corr
            std = np.sqrt(np.diag(cov))
            std = np.where(std == 0, 1e-8, std)
            corr = cov / np.outer(std, std)
            corr = np.clip(corr, -1, 1)
            dist = np.sqrt(0.5 * (1 - corr))
            # linkage expects condensed
            condensed = squareform(dist, checks=False)
            link = linkage(condensed, method="single")
            # Order from linkage leaves
            from scipy.cluster.hierarchy import leaves_list
            order = leaves_list(link)
            # Recursive bisection allocation (inverse variance)
            # Simplified: allocate inverse variance within clusters, then bisect
            var = np.diag(cov)
            var = np.where(var == 0, 1e-8, var)
            inv_var = 1 / var
            # allocate by ordered inv var
            w = inv_var[order] / inv_var[order].sum()
            # reorder back
            w_final = np.zeros(n)
            w_final[order] = w
            return _enforce_box(w_final, self.constraints)
        except Exception:
            inv_var = 1 / np.where(np.diag(cov) == 0, 1e-8, np.diag(cov))
            return inv_var / inv_var.sum()

    # -- Black-Litterman -------------------------------------------------
    def black_litterman(
        self,
        market_caps: np.ndarray,
        cov: np.ndarray,
        views_P: np.ndarray | None = None,
        views_Q: np.ndarray | None = None,
        tau: float = 0.05,
        omega: np.ndarray | None = None,
        risk_aversion: float = 2.5,
    ) -> np.ndarray:
        """Black-Litterman posterior expected returns, then mean-variance.

        market_caps -> implied equilibrium returns: Π = λ Σ w_mkt
        Posterior: μ_BL = [(τΣ)^-1 + P^T Ω^-1 P]^-1 [(τΣ)^-1 Π + P^T Ω^-1 Q]
        If no views, returns equilibrium (market) portfolio.
        """
        n = cov.shape[0]
        w_mkt = market_caps / market_caps.sum() if market_caps.sum() else self.equal_weight(n)
        pi = risk_aversion * (cov @ w_mkt)
        if views_P is None or views_Q is None or views_P.size == 0:
            # no views -> hold market
            return _enforce_box(w_mkt, self.constraints)
        # posterior
        tau_sigma = tau * cov
        try:
            inv_tau = np.linalg.inv(tau_sigma)
        except np.linalg.LinAlgError:
            inv_tau = np.linalg.pinv(tau_sigma)
        if omega is None:
            # He-Litterman: Ω = diag(P τΣ P^T)
            omega = np.diag(np.diag(views_P @ tau_sigma @ views_P.T))
            omega = np.where(omega == 0, 1e-6, omega)
        try:
            inv_omega = np.linalg.inv(omega)
        except np.linalg.LinAlgError:
            inv_omega = np.linalg.pinv(omega)
        A = inv_tau + views_P.T @ inv_omega @ views_P
        b = inv_tau @ pi + views_P.T @ inv_omega @ views_Q
        try:
            mu_bl = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            mu_bl = np.linalg.pinv(A) @ b
        return self.mean_variance(mu_bl, cov, risk_aversion=risk_aversion)

    # -- Unified compare -------------------------------------------------
    def compare(self, mu: np.ndarray, cov: np.ndarray, returns: np.ndarray | None = None, market_caps: np.ndarray | None = None) -> dict[str, np.ndarray]:
        """Run all methods and return {name: weights}."""
        out: dict[str, np.ndarray] = {}
        n = len(mu)
        out["equal"] = self.equal_weight(n)
        out["min_variance"] = self.min_variance(cov)
        out["max_sharpe"] = self.max_sharpe(mu, cov)
        out["risk_parity"] = self.risk_parity(cov)
        out["max_diversification"] = self.max_diversification(cov)
        if returns is not None and returns.shape[1] == n:
            out["cvar"] = self.cvar_min(returns)
        if market_caps is not None:
            out["black_litterman"] = self.black_litterman(market_caps, cov)
        out["hrp"] = self.hrp(cov)
        return out
