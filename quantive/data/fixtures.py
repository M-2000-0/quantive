"""Reproducible fixtures for the demonstration dataset and default problem."""
from __future__ import annotations

from typing import Dict, List, Optional

from quantive.data.synthetic import generate_synthetic_portfolio
from quantive.models.enums import Currency, StrategyProfile
from quantive.models.instruments import Portfolio
from quantive.models.optimization import (
    Constraint,
    EconomicScenario,
    OptimizationObjective,
    OptimizationProblem,
    ScenarioConfiguration,
    SolverConfiguration,
    default_constraints,
)

DEMO_PORTFOLIO_ID = "synthetic-demo"
DEMO_FINANCING_REQUIREMENT = 120_000.0  # 120bn reporting-currency units


def named_scenarios() -> List[EconomicScenario]:
    """The six canonical named scenarios."""
    return [
        EconomicScenario(
            id="base",
            name="Base Case",
            probability=0.40,
            interest_rate_shock=0.0,
            inflation_shock=0.0,
            fx_shocks={},
            liquidity_conditions=1.0,
        ),
        EconomicScenario(
            id="high_interest",
            name="High Interest Rates",
            probability=0.15,
            interest_rate_shock=0.020,
            inflation_shock=0.010,
            fx_shocks={"EUR": 1.05, "GBP": 1.06, "JPY": 1.04, "CHF": 1.05, "CAD": 1.03, "AUD": 1.07, "BRL": 1.10},
            liquidity_conditions=0.80,
        ),
        EconomicScenario(
            id="low_interest",
            name="Low Interest Rates",
            probability=0.10,
            interest_rate_shock=-0.015,
            inflation_shock=-0.005,
            fx_shocks={"EUR": 0.97, "GBP": 0.96, "JPY": 0.98, "CHF": 0.97, "CAD": 0.99, "AUD": 0.94, "BRL": 0.90},
            liquidity_conditions=0.95,
        ),
        EconomicScenario(
            id="high_inflation",
            name="High Inflation",
            probability=0.10,
            interest_rate_shock=0.010,
            inflation_shock=0.030,
            fx_shocks={"EUR": 1.04, "GBP": 1.05, "JPY": 1.03, "CHF": 1.04, "CAD": 1.02, "AUD": 1.06, "BRL": 1.12},
            liquidity_conditions=0.85,
        ),
        EconomicScenario(
            id="fx_shock",
            name="FX Shock",
            probability=0.10,
            interest_rate_shock=0.005,
            inflation_shock=0.005,
            fx_shocks={"EUR": 1.08, "GBP": 1.10, "JPY": 1.06, "CHF": 1.08, "CAD": 1.12, "AUD": 1.15, "BRL": 1.25},
            liquidity_conditions=0.75,
        ),
        EconomicScenario(
            id="liquidity_shock",
            name="Liquidity Shock",
            probability=0.15,
            interest_rate_shock=0.010,
            inflation_shock=0.008,
            fx_shocks={"EUR": 1.04, "GBP": 1.05, "JPY": 1.03, "CHF": 1.04, "CAD": 1.02, "AUD": 1.06, "BRL": 1.10},
            liquidity_conditions=0.30,
        ),
    ]


def demo_portfolio(seed: int = 42) -> Portfolio:
    """Deterministic synthetic demonstration portfolio (75 instruments)."""
    return generate_synthetic_portfolio(
        seed=seed,
        portfolio_id=DEMO_PORTFOLIO_ID,
        name="Synthetic Demonstration Portfolio",
    )


def default_solver_config(**overrides) -> SolverConfiguration:
    cfg = SolverConfiguration()
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


def build_default_problem(
    problem_id: str = "demo-problem",
    name: str = "Synthetic Sovereign Debt Optimization",
    financing_requirement: float = DEMO_FINANCING_REQUIREMENT,
    profile: StrategyProfile = StrategyProfile.BEST_OVERALL,
    objectives: Optional[OptimizationObjective] = None,
    constraints: Optional[List[Constraint]] = None,
    portfolio_id: str = DEMO_PORTFOLIO_ID,
    reference_currency: Currency = Currency.USD,
    scenario_config: Optional[ScenarioConfiguration] = None,
    solver_config: Optional[SolverConfiguration] = None,
) -> OptimizationProblem:
    from quantive.models.optimization import NamedStrategyProfiles

    if objectives is None:
        objectives, _ = NamedStrategyProfiles.PROFILES[profile]
    return OptimizationProblem(
        id=problem_id,
        name=name,
        portfolio_id=portfolio_id,
        financing_requirement=financing_requirement,
        objectives=objectives,
        constraints=constraints if constraints is not None else default_constraints(reference_currency),
        scenarios=named_scenarios(),
        scenario_config=scenario_config or ScenarioConfiguration(include_named=[s.id for s in named_scenarios()]),
        solver_config=solver_config or default_solver_config(),
        reference_currency=reference_currency,
        profile=profile,
    )


def load_demo_dataset() -> Dict:
    """Return the demo portfolio and default problem as a single payload."""
    return {
        "portfolio": demo_portfolio(),
        "problem": build_default_problem(),
        "scenarios": named_scenarios(),
    }