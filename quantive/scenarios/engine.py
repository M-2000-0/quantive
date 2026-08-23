"""Scenario generation engine.

Supports named scenarios plus deterministic Monte-Carlo generation. When a
seed is supplied, generation is fully reproducible.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from quantive.data.synthetic import FX_VOLATILITY
from quantive.models.optimization import EconomicScenario, ScenarioConfiguration
from quantive.scenarios.definitions import named_scenarios

# Distribution parameters for Monte-Carlo shock generation.
_IR_SHOCK_STD = 0.015      # annualized, ~150bp
_INFLATION_STD = 0.010
_FX_CROSS_CORR = 0.35      # correlation between currency log-moves
_FX_IR_CORR = 0.20         # correlation between currency log-move and rate shock
_IR_INF_CORR = 0.70
_LIQ_IR_CORR = 0.50        # rates up -> liquidity tightens
_LIQ_STRESS_SENSITIVITY = 0.35


class ScenarioEngine:
    """Builds named and Monte-Carlo scenario sets.

    The engine is deterministic for a fixed ``seed``: the same inputs always
    produce the same scenarios.
    """

    def __init__(self, seed: int = 42):
        self._seed = seed

    # -- Named scenarios -----------------------------------------------------
    def named(self, ids: Optional[List[str]] = None) -> List[EconomicScenario]:
        return named_scenarios(ids)

    # -- Monte Carlo ---------------------------------------------------------
    def _covariance(self, currencies: List[str]) -> np.ndarray:
        """Covariance matrix over [ir, inflation, liquidity, fx...]."""
        n_fx = len(currencies)
        n = 3 + n_fx
        cov = np.zeros((n, n))
        # variances
        cov[0, 0] = _IR_SHOCK_STD ** 2
        cov[1, 1] = _INFLATION_STD ** 2
        cov[2, 2] = 1.0  # liquidity latent factor (standard normal)
        for i, c in enumerate(currencies):
            cov[3 + i, 3 + i] = FX_VOLATILITY[c] ** 2
        # correlations
        cov[0, 1] = cov[1, 0] = _IR_INF_CORR * _IR_SHOCK_STD * _INFLATION_STD
        cov[0, 2] = cov[2, 0] = _LIQ_IR_CORR * _IR_SHOCK_STD * 1.0
        for i in range(n_fx):
            cov[0, 3 + i] = cov[3 + i, 0] = _FX_IR_CORR * _IR_SHOCK_STD * FX_VOLATILITY[currencies[i]]
        for i in range(n_fx):
            for j in range(i + 1, n_fx):
                corr = _FX_CROSS_CORR * FX_VOLATILITY[currencies[i]] * FX_VOLATILITY[currencies[j]]
                cov[3 + i, 3 + j] = cov[3 + j, 3 + i] = corr
        return cov

    def monte_carlo(self, count: int, seed: Optional[int] = None,
                    currencies: Optional[List[str]] = None) -> List[EconomicScenario]:
        """Generate ``count`` correlated Monte-Carlo scenarios.

        Each scenario is equally weighted. Shocks are drawn from a correlated
        Gaussian model; FX shocks are log-normal (mean ~1.0) so a shock of 1.1
        means the foreign currency appreciated 10% against the reporting
        currency (costlier for the borrower).
        """
        if count <= 0:
            return []
        rng = np.random.default_rng(self._seed if seed is None else seed)
        currencies = currencies or sorted(FX_VOLATILITY.keys())
        cov = self._covariance(currencies)
        z = rng.multivariate_normal(np.zeros(cov.shape[0]), cov, size=count)

        scenarios: List[EconomicScenario] = []
        prefix = "mc"
        for i in range(count):
            ir = float(z[i, 0])
            inf = float(z[i, 1])
            liq_z = float(z[i, 2])
            liquidity = float(np.clip(1.0 - _LIQ_STRESS_SENSITIVITY * max(0.0, liq_z), 0.15, 1.0))
            fx: Dict[str, float] = {}
            for j, c in enumerate(currencies):
                if c == "USD":
                    fx[c] = 1.0
                else:
                    vol = FX_VOLATILITY[c]
                    log_move = float(z[i, 3 + j])
                    # bias-adjust so E[fx_shock] ~= 1.0
                    fx[c] = float(np.exp(log_move - 0.5 * vol * vol))
            scenarios.append(
                EconomicScenario(
                    id=f"{prefix}-{i:05d}",
                    name=f"Monte Carlo #{i}",
                    probability=1.0 / count,
                    interest_rate_shock=ir,
                    inflation_shock=inf,
                    fx_shocks=fx,
                    liquidity_conditions=round(liquidity, 4),
                )
            )
        return scenarios

    # -- Materialization -----------------------------------------------------
    def materialize(self, config: ScenarioConfiguration) -> List[EconomicScenario]:
        """Build the full working scenario set for a problem."""
        scenarios = self.named(config.include_named)
        if config.monte_carlo_count > 0:
            mc = self.monte_carlo(
                config.monte_carlo_count,
                seed=config.monte_carlo_seed,
            )
            scenarios = scenarios + mc
        return scenarios