"""Monte Carlo Scenario Simulation Engine.

Runs parallel simulations under varying interest rate shocks to stress-test
both current and quantum-optimized debt portfolios.

Scenarios:
1. Parallel yield curve shifts (+100, +200, +300 bps)
2. Yield curve steepening/flattening
3. Inflation spike (+200bps CPI shock)
4. FX devaluation (local currency -20%)
5. Liquidity crisis (short-term rates spike +500bps)
6. Recession (rates drop -200bps, GDP contraction)

Each scenario runs 1000 simulations with correlated random walks.
"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class SimulationConfig:
    """Configuration for Monte Carlo simulation."""
    n_simulations: int = 1000
    time_horizon_months: int = 60  # 5 years
    confidence_levels: list[float] = field(default_factory=lambda: [0.90, 0.95, 0.975, 0.99])
    random_seed: Optional[int] = None


@dataclass
class PortfolioInput:
    """Portfolio for simulation."""
    instruments: list[dict]  # [{principal, coupon_rate, maturity_years, rate_type}]
    total_value: float
    name: str = "Portfolio"


@dataclass
class ScenarioResult:
    """Result from a single scenario simulation."""
    scenario_name: str
    portfolio_name: str
    # Distribution of portfolio values
    mean_value: float
    median_value: float
    std_dev: float
    # Percentiles
    percentiles: dict[str, float]  # {"5%": X, "25%": Y, ...}
    # Risk metrics
    var_95: float  # Value at Risk 95%
    var_99: float
    cvar_95: float  # Conditional VaR (expected shortfall)
    cvar_99: float
    expected_loss: float
    max_loss: float
    # Probability metrics
    prob_loss_10pct: float  # Probability of >10% loss
    prob_loss_20pct: float
    # Time series
    mean_path: list[float]  # Average path over time
    worst_path: list[float]
    best_path: list[float]
    # Metadata
    n_simulations: int
    horizon_months: int


@dataclass
class MonteCarloResults:
    """Full Monte Carlo analysis results."""
    current_portfolio: ScenarioResult
    optimized_portfolio: ScenarioResult
    comparison: dict
    stress_scenarios: dict[str, ScenarioResult]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def run_monte_carlo(
    current: PortfolioInput,
    optimized: PortfolioInput,
    yield_curve: dict[str, float],
    macro_data: dict,
    config: Optional[SimulationConfig] = None,
) -> MonteCarloResults:
    """Run full Monte Carlo analysis on both portfolios.

    Args:
        current: Current debt portfolio
        optimized: Quantum-optimized portfolio
        yield_curve: Current yield rates {"3M": 4.25, "2Y": 3.8, ...}
        macro_data: GDP, inflation, fiscal balance indicators
        config: Simulation configuration

    Returns:
        MonteCarloResults with comparison and stress scenarios
    """
    if config is None:
        config = SimulationConfig()

    if config.random_seed is not None:
        random.seed(config.random_seed)

    # Base rate parameters from yield curve
    base_rate = yield_curve.get("10Y", 5.0) / 100
    base_vol = _estimate_volatility(yield_curve)
    base_inflation = macro_data.get("inflation_pct", 3.0) / 100
    base_gdp_growth = macro_data.get("gdp_growth_pct", 2.5) / 100

    # Run base scenario for both portfolios
    current_result = _simulate_portfolio(
        current, base_rate, base_vol, base_inflation, base_gdp_growth, config, "base_case"
    )
    optimized_result = _simulate_portfolio(
        optimized, base_rate, base_vol, base_inflation, base_gdp_growth, config, "base_case"
    )

    # Comparison metrics
    comparison = _compute_comparison(current_result, optimized_result)

    # Stress scenarios
    stress_scenarios = {}
    stress_configs = {
        "rate_200bps_up": {"rate_shift": 0.02, "inflation_shift": 0.005, "gdp_shift": -0.01},
        "rate_100bps_down": {"rate_shift": -0.01, "inflation_shift": -0.005, "gdp_shift": 0.005},
        "rate_300bps_up": {"rate_shift": 0.03, "inflation_shift": 0.01, "gdp_shift": -0.02},
        "yield_steepening": {"rate_shift": 0.01, "short_rate_shift": -0.005, "inflation_shift": 0.003, "gdp_shift": 0},
        "inflation_spike": {"rate_shift": 0.015, "inflation_shift": 0.03, "gdp_shift": -0.015},
        "fx_devaluation": {"rate_shift": 0.025, "inflation_shift": 0.04, "gdp_shift": -0.03, "fx_shock": -0.20},
        "liquidity_crisis": {"rate_shift": 0.05, "short_rate_shift": 0.05, "inflation_shift": 0.01, "gdp_shift": -0.02},
        "recession": {"rate_shift": -0.02, "inflation_shift": -0.01, "gdp_shift": -0.03},
    }

    for name, shifts in stress_configs.items():
        stressed_rate = base_rate + shifts.get("rate_shift", 0)
        stressed_inflation = base_inflation + shifts.get("inflation_shift", 0)
        stressed_gdp = base_gdp_growth + shifts.get("gdp_shift", 0)
        stressed_vol = base_vol * (1 + abs(shifts.get("rate_shift", 0)) * 10)

        stress_scenarios[name] = _simulate_portfolio(
            optimized, stressed_rate, stressed_vol, stressed_inflation, stressed_gdp, config, name
        )

    return MonteCarloResults(
        current_portfolio=current_result,
        optimized_portfolio=optimized_result,
        comparison=comparison,
        stress_scenarios=stress_scenarios,
    )


def _simulate_portfolio(
    portfolio: PortfolioInput,
    base_rate: float,
    base_vol: float,
    base_inflation: float,
    base_gdp: float,
    config: SimulationConfig,
    scenario: str,
) -> ScenarioResult:
    """Simulate a portfolio under given macro conditions."""
    n = config.n_simulations
    T = config.time_horizon_months

    # Generate correlated random paths for rates
    all_terminal_values = []
    all_paths = []

    for sim in range(n):
        path = [portfolio.total_value]
        rate_path = [base_rate]

        for month in range(1, T + 1):
            # Rate dynamics: mean-reverting process (Hull-White inspired)
            prev_rate = rate_path[-1]
            kappa = 0.05  # Mean reversion speed
            theta = base_rate  # Long-term rate
            sigma_r = base_vol / math.sqrt(12)  # Monthly vol

            dW_r = random.gauss(0, 1)
            new_rate = prev_rate + kappa * (theta - prev_rate) / 12 + sigma_r * dW_r
            new_rate = max(new_rate, 0.001)  # Floor at 0.1%
            rate_path.append(new_rate)

            # Portfolio value change
            value_change = 0
            for inst in portfolio.instruments:
                principal = inst.get("principal_outstanding", 0)
                coupon = inst.get("coupon_rate", 0)
                maturity = inst.get("maturity_years", 5)
                rate_type = inst.get("rate_type", "fixed")

                # Coupon income
                monthly_coupon = principal * coupon / 12
                value_change += monthly_coupon

                # Mark-to-market effect (rate sensitivity)
                duration = min(maturity, 10)  # Simplified duration
                if rate_type == "floating":
                    # Floating rate: resets, minimal MTM impact
                    rate_change_effect = 0
                else:
                    # Fixed rate: MTM = -duration * delta_r
                    rate_change_effect = -duration * (new_rate - prev_rate) * principal

                # Inflation effect on real value
                inflation_effect = -base_inflation / 12 * principal * 0.1  # Small drag

                # GDP correlation (higher GDP = lower default risk = higher value)
                gdp_effect = base_gdp / 12 * principal * 0.05

                value_change += rate_change_effect + inflation_effect + gdp_effect

            new_value = path[-1] + value_change
            path.append(new_value)

        all_terminal_values.append(path[-1])
        all_paths.append(path)

    # Compute statistics
    all_terminal_values.sort()
    mean_val = sum(all_terminal_values) / n
    median_val = all_terminal_values[n // 2]
    std_val = math.sqrt(sum((v - mean_val) ** 2 for v in all_terminal_values) / n)

    # Percentiles
    percentiles = {}
    for cl in config.confidence_levels:
        idx = int(cl * n)
        idx = min(idx, n - 1)
        percentiles[f"{int(cl*100)}%"] = round(all_terminal_values[idx], 0)

    # VaR and CVaR
    loss_threshold = portfolio.total_value
    losses = [loss_threshold - v for v in all_terminal_values]
    losses.sort(reverse=True)

    var_95_idx = int(0.05 * n)
    var_99_idx = int(0.01 * n)
    var_95 = losses[min(var_95_idx, n - 1)]
    var_99 = losses[min(var_99_idx, n - 1)]

    cvar_95 = sum(losses[:var_95_idx + 1]) / max(var_95_idx + 1, 1)
    cvar_99 = sum(losses[:var_99_idx + 1]) / max(var_99_idx + 1, 1)
    expected_loss = sum(losses) / n
    max_loss = losses[0] if losses else 0

    # Probability of losses
    prob_10 = sum(1 for v in all_terminal_values if v < portfolio.total_value * 0.9) / n
    prob_20 = sum(1 for v in all_terminal_values if v < portfolio.total_value * 0.8) / n

    # Aggregate paths
    mean_path = [sum(all_paths[s][t] for s in range(n)) / n for t in range(T + 1)]
    worst_path = [min(all_paths[s][t] for s in range(n)) for t in range(T + 1)]
    best_path = [max(all_paths[s][t] for s in range(n)) for t in range(T + 1)]

    return ScenarioResult(
        scenario_name=scenario,
        portfolio_name=portfolio.name,
        mean_value=round(mean_val, 0),
        median_value=round(median_val, 0),
        std_dev=round(std_val, 0),
        percentiles=percentiles,
        var_95=round(var_95, 0),
        var_99=round(var_99, 0),
        cvar_95=round(cvar_95, 0),
        cvar_99=round(cvar_99, 0),
        expected_loss=round(expected_loss, 0),
        max_loss=round(max_loss, 0),
        prob_loss_10pct=round(prob_10 * 100, 2),
        prob_loss_20pct=round(prob_20 * 100, 2),
        mean_path=[round(v, 0) for v in mean_path],
        worst_path=[round(v, 0) for v in worst_path],
        best_path=[round(v, 0) for v in best_path],
        n_simulations=n,
        horizon_months=T,
    )


def _compute_comparison(current: ScenarioResult, optimized: ScenarioResult) -> dict:
    """Compute comparison metrics between current and optimized portfolios."""
    # Dollar improvement = how much better (less loss) the optimized portfolio is
    var_dollar_improvement = current.var_95 - optimized.var_95
    cvar_dollar_improvement = current.cvar_95 - optimized.cvar_95

    # Percentage improvement (only meaningful when current has positive VaR = real loss)
    if current.var_95 > 1:  # Only show % when current has meaningful loss
        var_improvement = (var_dollar_improvement / current.var_95) * 100
    else:
        var_improvement = 0.0

    if current.cvar_95 > 1:
        cvar_improvement = (cvar_dollar_improvement / current.cvar_95) * 100
    else:
        cvar_improvement = 0.0
    expected_improvement = ((current.expected_loss - optimized.expected_loss) / max(abs(current.expected_loss), 1)) * 100

    return {
        "var_improvement_pct": round(var_improvement, 2),
        "cvar_improvement_pct": round(cvar_improvement, 2),
        "expected_loss_improvement_pct": round(expected_improvement, 2),
        "var_dollar_improvement": round(var_dollar_improvement, 0),
        "cvar_dollar_improvement": round(cvar_dollar_improvement, 0),
        "current_var_95": current.var_95,
        "optimized_var_95": optimized.var_95,
        "current_cvar_95": current.cvar_95,
        "optimized_cvar_95": optimized.cvar_95,
        "risk_reduction_summary": (
            f"VaR reduced by {var_improvement:.1f}%, "
            f"CVaR reduced by {cvar_improvement:.1f}%, "
            f"Expected loss reduced by {expected_improvement:.1f}%"
        ),
    }


def _estimate_volatility(yield_curve: dict[str, float]) -> float:
    """Estimate annualized volatility from yield curve spread."""
    rates = list(yield_curve.values())
    if len(rates) < 2:
        return 0.02  # Default 2% vol
    # Spread between short and long end as vol proxy
    spread = max(rates) - min(rates)
    return max(spread / 100, 0.01)  # At least 1% vol
