"""Scenario engine tests."""
from __future__ import annotations

import pytest

from quantive.models.optimization import ScenarioConfiguration
from quantive.scenarios.definitions import named_scenarios
from quantive.scenarios.engine import ScenarioEngine


def test_named_scenarios_all_present():
    ids = {s.id for s in named_scenarios()}
    assert {"base", "high_interest", "low_interest", "high_inflation", "fx_shock", "liquidity_shock"} <= ids


def test_named_scenarios_probabilities_sum_to_one():
    total = sum(s.probability for s in named_scenarios())
    assert total == pytest.approx(1.0)


def test_monte_carlo_deterministic_with_seed():
    e1 = ScenarioEngine(seed=7)
    e2 = ScenarioEngine(seed=7)
    a = e1.monte_carlo(50, seed=7)
    b = e2.monte_carlo(50, seed=7)
    assert len(a) == 50
    assert [s.id for s in a] == [s.id for s in b]
    assert all(s.interest_rate_shock == o.interest_rate_shock for s, o in zip(a, b))


def test_monte_carlo_differs_across_seeds():
    a = ScenarioEngine(1).monte_carlo(20, seed=1)
    b = ScenarioEngine(2).monte_carlo(20, seed=2)
    assert a[0].interest_rate_shock != pytest.approx(b[0].interest_rate_shock, abs=1e-12)


def test_monte_carlo_domestic_fx_always_one():
    mc = ScenarioEngine().monte_carlo(30)
    assert all(s.fx_shocks["USD"] == 1.0 for s in mc)


def test_monte_carlo_fx_mean_approximately_one():
    mc = ScenarioEngine().monte_carlo(2000)
    eur = [s.fx_shocks["EUR"] for s in mc]
    import numpy as np

    assert np.mean(eur) == pytest.approx(1.0, abs=0.02)


def test_monte_carlo_liquidity_bounded():
    mc = ScenarioEngine().monte_carlo(500)
    assert all(0.15 <= s.liquidity_conditions <= 1.0 for s in mc)


def test_materialize_10000_scenarios_fast():
    import time

    config = ScenarioConfiguration(monte_carlo_count=10_000, monte_carlo_seed=99)
    t0 = time.time()
    scenarios = ScenarioEngine(99).materialize(config)
    dt = time.time() - t0
    assert len(scenarios) == 10_006
    assert dt < 5.0


def test_materialize_named_only():
    config = ScenarioConfiguration(monte_carlo_count=0)
    scenarios = ScenarioEngine().materialize(config)
    assert len(scenarios) == 6


def test_materialize_deterministic():
    config = ScenarioConfiguration(monte_carlo_count=100, monte_carlo_seed=5)
    a = ScenarioEngine(5).materialize(config)
    b = ScenarioEngine(5).materialize(config)
    assert [s.id for s in a] == [s.id for s in b]


def test_shocks_within_expected_range():
    mc = ScenarioEngine().monte_carlo(2000)
    shocks = [abs(s.interest_rate_shock) for s in mc]
    assert max(shocks) < 0.08  # 99.99% of ~150bp-std draws
    assert min(shocks) >= 0.0