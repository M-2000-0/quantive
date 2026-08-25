"""Orchestration: ties scenarios, solvers, strategies, benchmarking and stress
testing into a single pipeline for a problem."""
from __future__ import annotations

from typing import Dict, List, Optional

from quantive.benchmark.engine import run_benchmark
from quantive.models.instruments import Portfolio
from quantive.models.optimization import OptimizationProblem
from quantive.models.results import (
    OptimizationResult,
    ScenarioResult,
    StressTestResult,
)
from quantive.objectives.costs import scenario_costs
from quantive.objectives.spec import ProblemSpec, build_spec
from quantive.scenarios.engine import ScenarioEngine
from quantive.solvers.base import SolveResult
from quantive.solvers.registry import get_solver
from quantive.stress.tester import stress_test
from quantive.strategies import generate_strategies, strategy_from_result

# AuditLogger is optional and provided by the backend application.
# Importing from app.audit.logger is not available in the core quantive package.
# When running via the backend FastAPI app, the logger is injected separately.
AuditLogger = None


def materialize_scenarios(problem: OptimizationProblem,
                          seed: Optional[int] = None) -> List:
    engine = ScenarioEngine(seed=seed if seed is not None else problem.solver_config.seed)
    return engine.materialize(problem.scenario_config)


def solve_problem(
    portfolio: Portfolio,
    problem: OptimizationProblem,
    scenarios: List,
) -> OptimizationResult:
    """Run the problem's configured solver and return the canonical result."""
    spec = build_spec(portfolio, problem, scenarios)
    solver = get_solver(problem.solver_config.solver)
    result = solver.solve(spec, problem.solver_config)

    strategy = strategy_from_result(problem, problem.profile, result)

    scenario_results = _scenario_results(spec, result)
    return OptimizationResult(
        id=f"result-{problem.id}",
        problem_id=problem.id,
        profile=problem.profile,
        strategy=strategy,
        scenario_results=scenario_results,
        runtime=result.runtime,
        solver=result.solver,
        solver_type=result.solver_type,
        execution_backend=result.execution_backend,
        iterations=result.iterations,
        objective_evaluations=result.objective_evaluations,
        optimality_note=result.optimality_note,
        metadata={
            "n_instruments": spec.n_instruments,
            "n_scenarios": spec.n_scenarios,
            "profile": problem.profile.value,
            "objective_weights": list(problem.objectives.as_tuple),
            "allocation": result.allocation,
        },
    )


def _scenario_results(spec: ProblemSpec, result: SolveResult) -> List[ScenarioResult]:
    x = _vector(spec, result.allocation)
    costs = scenario_costs(x, spec.cost_matrix)
    out = []
    for s in range(spec.n_scenarios):
        scen = spec.scenarios[s]
        viol = _scenario_violations(spec, x, scen)
        out.append(
            ScenarioResult(
                scenario_id=scen.id,
                scenario_name=scen.name,
                probability=float(spec.probabilities[s]),
                financing_cost=float(costs[s]),
                effective_interest_rate=float(costs[s]) / spec.financing_requirement if spec.financing_requirement else 0.0,
                violations=viol,
            )
        )
    return out


def _vector(spec: ProblemSpec, allocation: Dict[str, float]):
    import numpy as np

    return np.array([allocation.get(iid, 0.0) for iid in spec.instrument_ids], dtype=float)


def _scenario_violations(spec: ProblemSpec, x, scen) -> int:
    """Structural violations of the strategy in a scenario (liquidity-scaled)."""
    count = 0
    R = spec.financing_requirement
    if spec.min_liquidity_share > 0:
        liq_available = float(x[spec.is_liquid].sum()) * scen.liquidity_conditions
        if liq_available < spec.min_liquidity_share * R:
            count += 1
    if spec.foreign_currency_limit_share is not None:
        foreign = float(x[spec.is_foreign].sum())
        if foreign > spec.foreign_currency_limit_share * R:
            count += 1
    return count


def run_full_job(
    portfolio: Portfolio,
    problem: OptimizationProblem,
    scenario_seed: Optional[int] = None,
) -> Dict:
    """Execute the complete pipeline for one problem.

    Returns a dict with ``result``, ``strategies``, ``benchmark``, ``stress``
    and ``scenarios``.
    """
    scenarios = materialize_scenarios(problem, seed=scenario_seed)
    result = solve_problem(portfolio, problem, scenarios)

    strategies = generate_strategies(
        portfolio, problem, scenarios, solver_name=problem.solver_config.solver
    )
    benchmark = run_benchmark(portfolio, problem, scenarios)

    spec = build_spec(portfolio, problem, scenarios)
    stress: Dict[str, StressTestResult] = {}
    for strategy in strategies:
        stress[strategy.id] = stress_test(strategy, spec)

    if AuditLogger is not None:
        AuditLogger.log_optimization_complete(
            result_id=result.id,
            user=getattr(problem, "owner", None),
            feasible=result.strategy.feasible,
            objective_value=result.strategy.objective_value,
            runtime=result.runtime,
        )

    return {
        "result": result,
        "strategies": strategies,
        "benchmark": benchmark,
        "stress": stress,
        "scenarios": scenarios,
        "spec": spec,
        "portfolio": portfolio,
        "problem": problem,
    }