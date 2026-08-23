"""Stress testing tests."""
from __future__ import annotations

import numpy as np

from quantive.models.enums import StrategyProfile
from quantive.stress.tester import stress_test
from quantive.strategies import solve_profile


def test_stress_returns_full_metrics(portfolio, problem, scenarios, spec):
    strategy = solve_profile(portfolio, problem, StrategyProfile.BEST_OVERALL, scenarios, "milp")
    st = stress_test(strategy, spec)
    assert st.scenario_count == spec.n_scenarios
    assert st.avg_financing_cost > 0
    assert st.worst_financing_cost >= st.avg_financing_cost
    assert set(st.percentile_costs) == {"5", "25", "50", "75", "95"}
    assert st.constraint_satisfaction_rate <= 1.0
    assert len(st.cost_distribution) > 0


def test_stress_percentile_ordering(portfolio, problem, scenarios, spec):
    strategy = solve_profile(portfolio, problem, StrategyProfile.BEST_OVERALL, scenarios, "milp")
    st = stress_test(strategy, spec)
    p5, p50, p95 = st.percentile_costs["5"], st.percentile_costs["50"], st.percentile_costs["95"]
    assert p5 <= p50 <= p95


def test_stress_worst_exceeds_tail_of_distribution(portfolio, problem, scenarios, spec):
    strategy = solve_profile(portfolio, problem, StrategyProfile.BEST_OVERALL, scenarios, "milp")
    st = stress_test(strategy, spec)
    assert st.worst_financing_cost >= st.percentile_costs["95"]


def test_stress_mc_distribution(portfolio, problem, scenarios, spec):
    strategy = solve_profile(portfolio, problem, StrategyProfile.BEST_OVERALL, scenarios, "milp")

    import copy

    cfg = copy.deepcopy(problem.scenario_config)
    cfg.monte_carlo_count = 2000
    from quantive.scenarios.engine import ScenarioEngine
    from quantive.objectives.spec import build_spec

    mc_scenarios = ScenarioEngine(3).materialize(cfg)
    mc_spec = build_spec(portfolio, problem, mc_scenarios)
    st = stress_test(strategy, mc_spec)
    assert st.scenario_count == 2006
    assert st.avg_financing_cost > 0


def test_liquidity_shock_generates_breaches(portfolio, problem, scenarios, spec):
    """A strategy with high near-term rollover should breach under liquidity stress."""
    # build an artificial strategy concentrated in short maturities
    x = np.zeros(spec.n_instruments)
    short = np.flatnonzero(spec.year_bucket <= 2)
    per = spec.financing_requirement / len(short)
    for i in short:
        x[i] = min(per, spec.capacity[i])
    x = x / x.sum() * spec.financing_requirement
    from quantive.solvers.heuristic import project_box_simplex

    x = project_box_simplex(x, spec.capacity, spec.financing_requirement)
    from quantive.models.results import Strategy

    strategy = Strategy(id="short", name="Short Maturities", allocation={
        spec.instrument_ids[i]: float(x[i]) for i in range(spec.n_instruments)
    })
    st = stress_test(strategy, spec)
    assert st.refinancing_breaches >= 1


def test_stress_satisfaction_rate_reflects_breaches(portfolio, problem, scenarios, spec):
    strategy = solve_profile(portfolio, problem, StrategyProfile.BEST_OVERALL, scenarios, "milp")
    st = stress_test(strategy, spec)
    total_breaches = st.refinancing_breaches + st.liquidity_breaches + st.currency_breaches
    if total_breaches > 0:
        assert st.constraint_satisfaction_rate < 1.0