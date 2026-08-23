"""Benchmark metrics.

Comparable metrics per solver, always evaluated on the canonical objective and
constraints of the same ``ProblemSpec``.
"""
from __future__ import annotations

import numpy as np

from quantive.models.results import BenchmarkRow
from quantive.objectives.spec import ProblemSpec
from quantive.solvers.base import SolveResult
from quantive.stress.tester import stress_test


def metric_row(solver_result: SolveResult, spec: ProblemSpec) -> BenchmarkRow:
    """Build a ``BenchmarkRow`` from a solver result plus stress metrics."""
    x = np.array([solver_result.allocation.get(iid, 0.0) for iid in spec.instrument_ids], dtype=float)
    feasible, n_viol, total_viol = spec.feasibility(x)
    st = stress_test(_as_strategy(solver_result), spec)
    compute_cost = float(
        (solver_result.objective_evaluations or 0) if solver_result.objective_evaluations else solver_result.runtime
    )
    risk_total = float(
        spec.interest_rate_risk(x) + spec.currency_risk(x) + spec.refinancing_risk(x)
    )
    return BenchmarkRow(
        solver=solver_result.solver,
        solver_type=solver_result.solver_type,
        execution_backend=solver_result.execution_backend,
        feasible=feasible,
        objective_value=solver_result.objective_value,
        financing_cost=solver_result.financing_cost,
        risk_total=risk_total,
        runtime=solver_result.runtime,
        constraint_violations=n_viol,
        constraint_violation_magnitude=total_viol,
        robustness_worst_cost=st.worst_financing_cost,
        compute_cost=compute_cost,
        optimality_note=solver_result.optimality_note,
    )


def _as_strategy(solver_result: SolveResult):
    from quantive.models.results import Strategy

    return Strategy(
        id=f"{solver_result.solver}-stress",
        name=solver_result.solver,
        allocation=solver_result.allocation,
        objective_value=solver_result.objective_value,
        feasible=solver_result.feasible,
    )