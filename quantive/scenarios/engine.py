"""Scenario generation engine.

Supports named scenarios plus deterministic Monte-Carlo generation. When a
seed is supplied, generation is fully reproducible.

Second-order effects model nonlinear interactions between shocks (e.g., rate
hikes amplified by low liquidity, FX contagion under stress). Regime-switching
models capture distinct market states with different parameter characteristics.

Policy what-if analysis extends scenario generation to include fiscal and
regulatory policy shocks (tax changes, spending adjustments, regulatory
relief, subsidy modifications) with deterministic impact multipliers.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from quantive.data.synthetic import FX_VOLATILITY
from quantive.models.optimization import EconomicScenario, ScenarioConfiguration
from quantive.scenarios.definitions import named_scenarios, _policy_shock_multiplier
from quantive.scenarios.regime import EXPANSION, NORMAL, STRESS, CRISIS, Regime, RegimeSwitchingEngine

# Distribution parameters for Monte-Carlo shock generation.
_IR_SHOCK_STD = 0.015      # annualized, ~150bp
_INFLATION_STD = 0.010
_FX_CROSS_CORR = 0.35      # correlation between currency log-moves
_FX_IR_CORR = 0.20         # correlation between currency log-move and rate shock
_IR_INF_CORR = 0.70
_LIQ_IR_CORR = 0.50        # rates up -> liquidity tightens
_LIQ_STRESS_SENSITIVITY = 0.35

# Second-order effect coefficients (nonlinear interaction terms)
_SECOND_ORDER_COEFFS = {
    "rate_liq_interaction": 0.4,     # rate shock * liquidity stress multiplier
    "fx_rate_interaction": 0.25,     # fx shock * rate shock amplification
    "inf_rate_interaction": 0.30,    # inflation * rate shock feedback
}


class ScenarioEngine:
    """Builds named and Monte-Carlo scenario sets.

    The engine is deterministic for a fixed ``seed``: the same inputs always
    produce the same scenarios. Second-order effects model nonlinear
    interactions between shocks.
    """

    def __init__(self, seed: int = 42):
        self._seed = seed
        self._regime_engine = RegimeSwitchingEngine(seed=seed)

    # -- Named scenarios -----------------------------------------------------
    def named(self, ids: Optional[List[str]] = None) -> List[EconomicScenario]:
        return named_scenarios(ids)

    # -- Monte Carlo with second-order effects -------------------------------
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

    def _apply_second_order(self, scenario: EconomicScenario, base_ir: float, base_inf: float) -> EconomicScenario:
        """Apply second-order nonlinear effects to a scenario.

        Interactions:
        - Rate * Liquidity: tight liquidity amplifies rate shock impact
        - FX * Rate: FX moves compound rate exposure
        - Inflation * Rate: real rate feedback loop
        """
        liquidity = scenario.liquidity_conditions
        fx_shocks = scenario.fx_shocks or {}

        # Rate shock amplified by low liquidity
        amplified_ir = base_ir * (1.0 + _SECOND_ORDER_COEFFS["rate_liq_interaction"] * (1.0 - liquidity))

        # FX shock interaction with rate shock (average, not sum, to preserve mean ~1)
        fx_deltas = []
        for c, shock in fx_shocks.items():
            if c != "USD":
                fx_deltas.append(_SECOND_ORDER_COEFFS["fx_rate_interaction"] * (shock - 1.0) * abs(amplified_ir))
        fx_multiplier = 1.0 + (sum(fx_deltas) / len(fx_deltas) if fx_deltas else 0.0)

        # Inflation real-rate feedback
        real_rate = amplified_ir - base_inf
        adjusted_inf = base_inf * (1.0 + _SECOND_ORDER_COEFFS["inf_rate_interaction"] * max(0, -real_rate) / 0.05)

        # Preserve USD at exactly 1.0 (domestic leg)
        adjusted_fx = {}
        for c, shock in fx_shocks.items():
            if c == "USD":
                adjusted_fx[c] = 1.0
            else:
                adjusted_fx[c] = round(shock * fx_multiplier, 6)
        return EconomicScenario(
            id=scenario.id,
            name=scenario.name,
            probability=scenario.probability,
            interest_rate_shock=round(amplified_ir, 6),
            inflation_shock=round(adjusted_inf, 6),
            fx_shocks=adjusted_fx,
            liquidity_conditions=round(liquidity, 4),
        )

    def monte_carlo(self, count: int, seed: Optional[int] = None,
                    currencies: Optional[List[str]] = None,
                    use_second_order: bool = True,
                    use_regime: bool = False) -> List[EconomicScenario]:
        """Generate ``count`` correlated Monte-Carlo scenarios.

        Each scenario is equally weighted. Shocks are drawn from a correlated
        Gaussian model; FX shocks are log-normal (mean ~1.0) so a shock of 1.1
        means the foreign currency appreciated 10% against the reporting
        currency (costlier for the borrower).

        Second-order nonlinear effects can be enabled for realistic shock
        amplification. Regime-switching can model distinct market states.
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

            base_scenario = EconomicScenario(
                id=f"{prefix}-{i:05d}",
                name=f"Monte Carlo #{i}",
                probability=1.0 / count,
                interest_rate_shock=ir,
                inflation_shock=inf,
                fx_shocks=fx,
                liquidity_conditions=round(liquidity, 4),
            )

            # Apply second-order effects if enabled
            final_scenario = self._apply_second_order(base_scenario, ir, inf) if use_second_order else base_scenario

            scenarios.append(final_scenario)

        return scenarios

    # -- Regime-switching scenarios -----------------------------------------
    def regime_switching(self, count: int, currencies: Optional[List[str]] = None) -> List[EconomicScenario]:
        """Generate regime-switching scenarios using the regime model.

        Each scenario samples a market regime first, then draws shocks from
        that regime's parameter distribution, capturing expansion/recession/crisis
        state transitions.
        """
        return self._regime_engine.generate(count, currencies=currencies)

    # -- Policy what-if analysis -----------------------------------------------
    def policy_what_if(self, policy_type: str, intensity: float = 1.0,
                       base_scenario: Optional[EconomicScenario] = None) -> EconomicScenario:
        """Generate a policy what-if scenario.

        Supports policy types:
        - ``tax-cut``: Reduce tax rate by ``intensity`` percentage points
        - ``spending-cut``: Reduce government spending by ``intensity`` percentage points
        - ``regulatory-relief``: Reduce regulatory burden by ``intensity`` percentage points
        - ``subsidy-increase``: Increase subsidies by ``intensity`` percentage points

        Returns a new ``EconomicScenario`` with appropriate shocks applied.
        """
        # Use base scenario or named base case
        if base_scenario is None:
            base_scenario = self.named([NamedScenarioIds.BASE])[0]

        # Get policy impact multipliers
        multipliers = _policy_shock_multiplier(policy_type)

        # Determine shock parameters based on policy type
        ir_shock = 0.0
        inf_shock = 0.0
        fx_shocks: Dict[str, float] = {}
        liquidity = 1.0

        if policy_type.startswith("tax-cut"):
            # Tax cuts mildly stimulate growth, may increase inflation slightly
            ir_shock = -intensity * 0.5  # Small rate cut effect
            inf_shock = intensity * 0.3  # Slight inflationary pressure from increased demand
            liquidity = 1.0 + intensity * 0.1  # Improved liquidity with economic growth
        elif policy_type.startswith("spending-cut"):
            # Spending cuts reduce inflation but may slow growth
            ir_shock = 0.0
            inf_shock = -intensity * 0.4  # Reduced inflationary pressure
            liquidity = 1.0 - intensity * 0.1  # Slightly tighter liquidity
        elif policy_type.startswith("regulatory"):
            # Regulatory relief stimulates growth without inflation
            ir_shock = -intensity * 0.3
            inf_shock = intensity * 0.1  # Mild inflation from increased activity
            liquidity = 1.0  # Neutral liquidity impact
        elif policy_type.startswith("subsidy"):
            # Subsidy increases can stimulate growth but may increase inflation
            ir_shock = -intensity * 0.4
            inf_shock = intensity * 0.35  # Subsidy-driven inflationary pressure
            liquidity = 1.0 + intensity * 0.05
        else:
            ir_shock = 0.0
            inf_shock = 0.0
            liquidity = 1.0

        # Apply multipliers to core shocks
        ir_shock *= intensity
        inf_shock *= intensity

        # Build fx_shocks - policy scenarios typically have no FX impact
        # unless specifically modeled

        new_scenario = EconomicScenario(
            id=f"policy-{policy_type}-{intensity}",
            name=f"Policy What-If: {policy_type.replace('-', ' ').title()} ({intensity*100:.0f}%)",
            probability=base_scenario.probability,
            interest_rate_shock=round(ir_shock, 6),
            inflation_shock=round(inf_shock, 6),
            fx_shocks=fx_shocks,
            liquidity_conditions=round(liquidity, 4),
        )

        # Apply second-order effects and multipliers
        final_scenario = self._apply_second_order(new_scenario, ir_shock, inf_shock)

        # Store policy multipliers in the scenario for frontend consumption
        # Attach macro-economic dimension impacts
        dimension_multipliers = policy_dimension_multipliers(policy_type, intensity)
        debt_multipliers = policy_debt_multipliers(policy_type, intensity)

        # Compute impact values from multipliers
        budget_impact = round(dimension_multipliers.get("budget_impact", 0.0) * intensity * 100, 2)
        gdp_impact = round(dimension_multipliers.get("gdp_impact", 0.0) * intensity * 100, 2)
        debt_impact = round(debt_multipliers.get("debt", 0.0) * intensity * 100, 2)
        inflation_impact = round(dimension_multipliers.get("inflation_impact", 0.0) * intensity * 100, 2)
        employment_impact = round(dimension_multipliers.get("employment_impact", 0.0) * intensity * 100, 2)

        # Attach policy dimension impacts via __dict__ for frontend consumption
        # EconomicScenario uses dataclass fields, so we add extra data via instance dict
        final_scenario.__dict__['_policy_dimensions'] = {
            'budget_impact': budget_impact,
            'gdp_impact': gdp_impact,
            'debt_impact': debt_impact,
            'inflation_impact': inflation_impact,
            'employment_impact': employment_impact,
            'policy_type': policy_type,
            'intensity': intensity,
        }

        return final_scenario

    # -- Materialization -----------------------------------------------------
    def materialize(self, config: ScenarioConfiguration,
                    use_second_order: bool = True,
                    use_regime: bool = False) -> List[EconomicScenario]:
        """Build the full working scenario set for a problem.

        Named scenarios are always included. Additional Monte-Carlo or regime
        scenarios respect the ``monte_carlo_count`` and seed settings.
        """
        scenarios = self.named(config.include_named)
        if config.monte_carlo_count > 0:
            mc = self.monte_carlo(
                config.monte_carlo_count,
                seed=config.monte_carlo_seed,
                use_second_order=use_second_order,
                use_regime=False,
            )
            scenarios = scenarios + mc
        if use_regime:
            regimes = self.regime_switching(config.monte_carlo_count or 10)
            scenarios = scenarios + regimes
        return scenarios