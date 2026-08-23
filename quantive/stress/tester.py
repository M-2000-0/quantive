"""Stress testing: how a strategy behaves if the assumptions are wrong.

For a strategy allocation the engine evaluates every scenario in the working
set (named + Monte Carlo), producing a full cost distribution plus
scenario-conditional breach statistics:

* refinancing breach — in liquidity-stressed scenarios, near-term (<=3y)
  maturities exceed the amount that can plausibly be rolled over;
* liquidity breach — liquid assets available in a stressed scenario fall below
  a minimum coverage level;
* currency breach — foreign-currency debt service in a scenario exceeds the
  policy currency cap by a margin;
* constraint satisfaction rate — share of scenarios with no breaches, gated on
  structural feasibility.
"""
from __future__ import annotations


import numpy as np

from quantive.models.results import StressTestResult, Strategy
from quantive.objectives.costs import scenario_costs
from quantive.objectives.spec import ProblemSpec
from quantive.stress.bins import cost_histogram

NEAR_TERM_BUCKETS = (1, 2, 3)
LIQUIDITY_STRESS_THRESHOLD = 0.5
LIQUIDITY_COVERAGE_MIN = 0.05
CURRENCY_BREACH_MARGIN = 1.25


def stress_test(strategy: Strategy, spec: ProblemSpec) -> StressTestResult:
    """Run a strategy through the full scenario set."""
    x = np.array([strategy.allocation.get(iid, 0.0) for iid in spec.instrument_ids], dtype=float)
    R = spec.financing_requirement
    n_s = spec.n_scenarios

    costs = scenario_costs(x, spec.cost_matrix)  # (S,)
    foreign_cost = _foreign_cost_by_scenario(x, spec)  # (S,)
    liquid_amount = float(x[spec.is_liquid].sum())
    near_term = sum(
        float(x[spec.year_bucket == b].sum()) for b in NEAR_TERM_BUCKETS
    )

    refi_breaches = 0
    liquidity_breaches = 0
    currency_breaches = 0
    ok_scenarios = 0

    foreign_cap = spec.foreign_currency_limit_share if spec.foreign_currency_limit_share else 0.25

    for s in range(n_s):
        scen = spec.scenarios[s]
        liq = scen.liquidity_conditions
        breached = False
        # refinancing breach under liquidity stress
        if liq < LIQUIDITY_STRESS_THRESHOLD:
            rollover_capacity = liq * R
            if near_term > rollover_capacity:
                refi_breaches += 1
                breached = True
        # liquidity breach
        if liquid_amount * liq < LIQUIDITY_COVERAGE_MIN * R:
            liquidity_breaches += 1
            breached = True
        # currency breach
        if foreign_cost[s] > foreign_cap * R * CURRENCY_BREACH_MARGIN:
            currency_breaches += 1
            breached = True
        if not breached:
            ok_scenarios += 1

    satisfaction_rate = ok_scenarios / max(n_s, 1)
    structural_ok = spec.feasibility(x)[0]
    if not structural_ok:
        satisfaction_rate = min(satisfaction_rate, 0.0)

    pcts = {str(p): float(np.percentile(costs, p)) for p in (5, 25, 50, 75, 95)}
    return StressTestResult(
        strategy_id=strategy.id,
        scenario_count=n_s,
        avg_financing_cost=float(costs.mean()),
        worst_financing_cost=float(costs.max()),
        percentile_costs=pcts,
        refinancing_breaches=refi_breaches,
        liquidity_breaches=liquidity_breaches,
        currency_breaches=currency_breaches,
        interest_rate_exposure=float(x[spec.is_floating].sum()),
        constraint_satisfaction_rate=round(satisfaction_rate, 4),
        cost_distribution=cost_histogram(costs, 20),
    )


def _foreign_cost_by_scenario(x: np.ndarray, spec: ProblemSpec) -> np.ndarray:
    """Per-scenario foreign-currency debt service."""
    if spec.n_instruments == 0:
        return np.zeros(spec.n_scenarios)
    rows = [i for i in range(spec.n_instruments) if spec.is_foreign[i]]
    if not rows:
        return np.zeros(spec.n_scenarios)
    return spec.cost_matrix[rows, :].T @ x[rows]