"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from quantive.data.fixtures import build_default_problem, demo_portfolio, named_scenarios
from quantive.models.instruments import Portfolio
from quantive.models.optimization import OptimizationProblem
from quantive.objectives.spec import build_spec
from quantive.scenarios.engine import ScenarioEngine


@pytest.fixture(scope="session")
def portfolio() -> Portfolio:
    return demo_portfolio(seed=42)


@pytest.fixture(scope="session")
def problem() -> OptimizationProblem:
    return build_default_problem()


@pytest.fixture(scope="session")
def scenarios() -> list:
    return named_scenarios()


@pytest.fixture(scope="session")
def spec(portfolio, problem, scenarios):
    return build_spec(portfolio, problem, scenarios)


@pytest.fixture()
def seeded_engine():
    return ScenarioEngine(seed=12345)