"""Benchmark engine: run every solver on the same problem and rank the results."""
from __future__ import annotations

from typing import Dict, List, Optional

from quantive.benchmark.metrics import metric_row
from quantive.benchmark.ranking import DEFAULT_RANKING_WEIGHTS, rank
from quantive.models.instruments import Portfolio
from quantive.models.optimization import OptimizationProblem, SolverConfiguration
from quantive.models.results import BenchmarkResult
from quantive.objectives.spec import ProblemSpec, build_spec
from quantive.solvers.base import SolveResult
from quantive.solvers.registry import DEFAULT_SOLVER_ORDER, get_solver


def run_benchmark(
    portfolio: Portfolio,
    problem: OptimizationProblem,
    scenarios: List,
    solver_names: Optional[List[str]] = None,
    ranking_weights: Optional[Dict[str, float]] = None,
) -> BenchmarkResult:
    """Run all (or selected) solvers on a problem and produce a ranked benchmark."""
    solver_names = solver_names or DEFAULT_SOLVER_ORDER
    spec = build_spec(portfolio, problem, scenarios)
    config = problem.solver_config

    rows = []
    for name in solver_names:
        solver = get_solver(name)
        result = _solve_with_config(solver, spec, config)
        rows.append(metric_row(result, spec))

    result = rank(rows, ranking_weights or DEFAULT_RANKING_WEIGHTS,
                  financing_requirement=spec.financing_requirement)
    result.problem_id = problem.id
    return result


def _solve_with_config(solver, spec: ProblemSpec, config: SolverConfiguration) -> SolveResult:
    return solver.solve(spec, config)