"""Strategy generation: distinct, feasible strategies across objective profiles.

Each profile yields a genuinely different feasible allocation by re-weighting
the objective and (for the robust profile) switching to a minimax objective.
All strategies are evaluated against the same canonical objective and
constraints.
"""
from __future__ import annotations

from typing import List, Optional


from quantive.models.enums import StrategyProfile
from quantive.models.instruments import Portfolio
from quantive.models.optimization import (
    NamedStrategyProfiles,
    OptimizationProblem,
)
from quantive.models.results import Strategy
from quantive.objectives.spec import build_spec
from quantive.solvers.base import SolveResult
from quantive.solvers.registry import get_solver

_PROFILES = (
    StrategyProfile.BEST_OVERALL,
    StrategyProfile.LOWEST_RISK,
    StrategyProfile.LOWEST_COST,
    StrategyProfile.STRESS_RESILIENT,
)


def strategy_from_result(
    problem: OptimizationProblem,
    profile: StrategyProfile,
    solve_result: SolveResult,
    description: Optional[str] = None,
) -> Strategy:
    return Strategy(
        id=f"strategy-{profile.value}",
        name=_profile_name(profile),
        description=description or NamedStrategyProfiles.PROFILES[profile][1],
        profile=profile,
        allocation=solve_result.allocation,
        objective_value=solve_result.objective_value,
        financing_cost=solve_result.financing_cost,
        risk_metrics=solve_result.risk_metrics,
        constraint_status=solve_result.constraint_status,
        objective_decomposition=solve_result.objective_decomposition,
        feasible=solve_result.feasible,
        solver=solve_result.solver,
        solver_type=solve_result.solver_type,
        execution_backend=solve_result.execution_backend,
    )


def _profile_name(profile: StrategyProfile) -> str:
    return {
        StrategyProfile.BEST_OVERALL: "Best Overall",
        StrategyProfile.LOWEST_RISK: "Lowest Risk",
        StrategyProfile.LOWEST_COST: "Lowest Financing Cost",
        StrategyProfile.STRESS_RESILIENT: "Most Stress Resilient",
    }[profile]


def _clone_for_profile(problem: OptimizationProblem, profile: StrategyProfile) -> OptimizationProblem:
    objectives, _ = NamedStrategyProfiles.PROFILES[profile]
    return problem.model_copy(
        update={
            "profile": profile,
            "objectives": objectives,
            "constraints": problem.constraints,
            "id": f"{problem.id}-{profile.value}",
            "solver_config": problem.solver_config,
        }
    )


def solve_profile(
    portfolio: Portfolio,
    problem: OptimizationProblem,
    profile: StrategyProfile,
    scenarios: List,
    solver_name: Optional[str] = None,
) -> Strategy:
    """Solve one profile and return the corresponding strategy."""
    solver_name = solver_name or problem.solver_config.solver
    cloned = _clone_for_profile(problem, profile)
    spec = build_spec(portfolio, cloned, scenarios)
    solver = get_solver(solver_name)
    result = solver.solve(spec, cloned.solver_config)
    return strategy_from_result(cloned, profile, result)


def generate_strategies(
    portfolio: Portfolio,
    problem: OptimizationProblem,
    scenarios: List,
    solver_name: Optional[str] = None,
    profiles: Optional[List[StrategyProfile]] = None,
) -> List[Strategy]:
    """Generate the full set of distinct strategies."""
    solver_name = solver_name or problem.solver_config.solver
    selected = profiles or list(_PROFILES)
    strategies: List[Strategy] = []
    for profile in selected:
        strategies.append(solve_profile(portfolio, problem, profile, scenarios, solver_name))
    return strategies