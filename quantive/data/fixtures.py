"""Reproducible demo fixtures: portfolio, optimization problem, scenarios.

These fixtures power demos, documentation examples and the SDK test-suite.
Everything is deterministic; ``demo_portfolio(seed=...)`` regenerates an
identical portfolio for the same seed.
"""
from __future__ import annotations

from typing import Any, List

from quantive.data.synthetic import SyntheticPortfolioGenerator
from quantive.models.instruments import Portfolio
from quantive.models.optimization import (
    EconomicScenario,
    OptimizationObjective,
    OptimizationProblem,
    SolverConfiguration,
    default_constraints,
)

DEMO_PORTFOLIO_ID = "demo-portfolio"

# Reporting unit is millions of USD. CBC/numerical stability is best when the
# model magnitudes stay below ~1e10; using a 120M raise keeps the demo problem
# robustly solvable while remaining a realistic small-sovereign scale.
DEMO_FINANCING_REQUIREMENT = 120_000_000.0


def named_scenarios(ids: Any = None) -> List[EconomicScenario]:
    """Return the canonical named economic scenarios.

    Deferred import avoids a load-time dependency between ``data`` and
    ``scenarios`` (``scenarios.definitions`` itself imports ``data.synthetic``).
    """
    from quantive.scenarios.definitions import named_scenarios as _named
    return _named(ids)


def demo_portfolio(seed: int = 42) -> Portfolio:
    """Build the deterministic demonstration portfolio."""
    return SyntheticPortfolioGenerator(seed=seed).portfolio(
        portfolio_id=DEMO_PORTFOLIO_ID,
        name="Sovereign Debt Demo Portfolio",
    )


def default_solver_config() -> SolverConfiguration:
    """Default solver configuration used by the demo problem."""
    return SolverConfiguration()


def build_default_problem() -> OptimizationProblem:
    """Build the default demo optimization problem."""
    return OptimizationProblem(
        id="demo-problem",
        name="Sovereign Debt Optimization (Demo)",
        portfolio_id=DEMO_PORTFOLIO_ID,
        financing_requirement=DEMO_FINANCING_REQUIREMENT,
        objectives=OptimizationObjective(),
        constraints=default_constraints(),
        scenarios=named_scenarios(),
        solver_config=default_solver_config(),
    )


def load_demo_dataset() -> dict:
    """Load the full demo dataset (portfolio + problem + scenarios)."""
    return {
        "portfolio": demo_portfolio(),
        "problem": build_default_problem(),
        "scenarios": named_scenarios(),
    }