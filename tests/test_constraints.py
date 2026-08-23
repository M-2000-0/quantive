"""Constraint evaluation tests."""
from __future__ import annotations

import numpy as np
import pytest

from quantive.models.results import ConstraintStatus


def test_feasible_proportional_allocation_is_violating(spec):
    # proportional-to-capacity violates foreign-currency / ladder constraints
    x = spec.capacity / spec.capacity.sum() * spec.financing_requirement
    feasible, n_viol, mag = spec.feasibility(x)
    assert feasible is False
    assert n_viol >= 1
    assert mag > 0
    assert spec.violation_magnitude(x) == pytest.approx(mag)


def test_debt_capacity_constraint(spec):
    x = np.zeros(spec.n_instruments)
    x[0] = spec.financing_requirement * 0.5
    statuses = spec.constraint_violations(x)
    debt = [s for s in statuses if s.name == "debt_capacity"][0]
    assert not debt.satisfied
    assert debt.violation == pytest.approx(spec.financing_requirement * 0.5)


def test_milp_solution_is_feasible(spec, problem):
    from quantive.solvers.registry import get_solver

    res = get_solver("milp").solve(spec, problem.solver_config)
    assert res.feasible
    statuses = res.constraint_status
    assert all(s.satisfied for s in statuses)
    assert sum(res.allocation.values()) == pytest.approx(spec.financing_requirement)


def test_all_constraints_reported(spec):
    statuses = spec.constraint_violations(np.ones(spec.n_instruments))
    names = {s.name for s in statuses}
    assert "debt_capacity" in names
    assert "instrument_capacity" in names
    assert "min_liquidity" in names
    assert any(n.startswith("refinancing_limit") for n in names)


def test_constraint_status_model():
    st = ConstraintStatus(name="x", satisfied=True, violation=0.0, detail="ok")
    assert st.satisfied is True


def test_custom_constraint(portfolio, problem, scenarios):
    from quantive.models.optimization import Constraint, ConstraintType
    from quantive.objectives.spec import build_spec

    custom = Constraint(
        type=ConstraintType.CUSTOM,
        name="esg_cap",
        parameters={"coefficients": {portfolio.instruments[0].id: 1.0}, "limit": 100.0},
    )
    p = problem.model_copy(deep=True)
    p.constraints = list(p.constraints) + [custom]
    cs = build_spec(portfolio, p, scenarios)
    x = np.zeros(cs.n_instruments)
    x[0] = 500.0
    statuses = cs.constraint_violations(x)
    esg = [s for s in statuses if s.name == "esg_cap"][0]
    assert not esg.satisfied
    assert esg.violation == pytest.approx(400.0)


def test_penalty_magnitude_matches_reporting(spec):
    x = np.zeros(spec.n_instruments)
    x[0] = spec.financing_requirement * 0.5
    from quantive.constraints.evaluators import penalty

    assert penalty(x, spec) == pytest.approx(spec.violation_magnitude(x) * spec.penalty)