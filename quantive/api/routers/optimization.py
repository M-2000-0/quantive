"""Optimization endpoints (problem lifecycle, async runs, results)."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException

from quantive.api.schemas import OptimizationProblemCreate, RunResponse
from quantive.api.state import state
from quantive.models.enums import JobStatus
from quantive.models.optimization import (
    EconomicScenario,
    NamedStrategyProfiles,
    OptimizationProblem,
    ScenarioConfiguration,
    SolverConfiguration,
    default_constraints,
)
from quantive.models.results import BenchmarkResult, Strategy
from quantive.orchestration import run_full_job
from quantive.scenarios.engine import ScenarioEngine

router = APIRouter(prefix="/optimization", tags=["optimization"])


def _problem_payload(problem_id: str) -> dict:
    run = state.get_run(problem_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"optimization {problem_id!r} has not been run")
    return run


@router.post("", status_code=201)
def create_optimization(request: OptimizationProblemCreate) -> OptimizationProblem:
    portfolio = state.get_portfolio(request.portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail=f"portfolio {request.portfolio_id!r} not found")
    problem_id = request.problem_id or f"problem-{uuid.uuid4().hex[:8]}"
    objectives = request.objectives or NamedStrategyProfiles.PROFILES[request.profile][0]
    constraints = request.constraints if request.constraints is not None else default_constraints(portfolio.reference_currency)
    scenario_config = request.scenario_config or ScenarioConfiguration()
    solver_config = request.solver_config
    problem = OptimizationProblem(
        id=problem_id,
        name=request.name,
        portfolio_id=portfolio.id,
        financing_requirement=request.financing_requirement,
        objectives=objectives,
        constraints=constraints,
        scenarios=ScenarioEngine(seed=solver_config.seed if solver_config else 42).named(
            scenario_config.include_named
        ),
        scenario_config=scenario_config,
        solver_config=solver_config or SolverConfiguration(),
        reference_currency=portfolio.reference_currency,
        profile=request.profile,
    )
    state.add_problem(problem)
    return problem


@router.get("")
def list_optimizations() -> List[OptimizationProblem]:
    return list(state.problems.values())


@router.get("/{problem_id}")
def get_optimization(problem_id: str) -> OptimizationProblem:
    problem = state.get_problem(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail=f"optimization {problem_id!r} not found")
    return problem


@router.post("/{problem_id}/run", status_code=202)
def run_optimization(
    problem_id: str,
    timeout: int = 300,
) -> RunResponse:
    """Run an optimization problem.

    Args:
        problem_id: Identifier of the problem to run
        timeout: Maximum seconds allowed for the optimization (default: 300s,
                 overridden by QUANTIVE_JOB_TIMEOUT env var)
    """
    problem = state.get_problem(problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail=f"optimization {problem_id!r} has not been run")
    portfolio = state.get_portfolio(problem.portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail=f"portfolio {problem.portfolio_id!r} not found")

    job = state.jobs.submit(run_full_job, portfolio, problem, timeout=timeout)
    return RunResponse(job_id=job.id, problem_id=problem_id, status=job.status.value)


@router.post("/{problem_id}/run/{job_id}/cancel", status_code=200)
def cancel_optimization(problem_id: str, job_id: str) -> Dict[str, str]:
    """Request cancellation of a running optimization job."""
    job = state.jobs.cancel(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job {job_id!r} not found")
    if job.status.value == "cancelled":
        return {"status": "cancelled", "message": "Job was successfully cancelled"}
    elif job.status.value == "timed_out":
        return {"status": "timed_out", "message": "Job exceeded time limit"}
    return {"status": job.status.value, "message": "Job cancellation requested"}


@router.get("/{problem_id}/results")
def get_results(problem_id: str) -> dict:
    payload = _problem_payload(problem_id)
    return {"result": payload["result"], "job_status": payload.get("job_status", "completed")}


@router.get("/{problem_id}/strategies")
def get_strategies(problem_id: str) -> List[Strategy]:
    payload = _problem_payload(problem_id)
    return payload["strategies"]


@router.get("/{problem_id}/benchmark")
def get_benchmark(problem_id: str) -> BenchmarkResult:
    payload = _problem_payload(problem_id)
    return payload["benchmark"]


@router.get("/{problem_id}/stress")
def get_stress(problem_id: str) -> dict:
    payload = _problem_payload(problem_id)
    return {k: v for k, v in payload["stress"].items()}


@router.get("/{problem_id}/scenarios")
def get_scenarios(problem_id: str, limit: Optional[int] = None) -> List[EconomicScenario]:
    payload = _problem_payload(problem_id)
    scenarios = payload["scenarios"]
    if limit is not None and limit >= 0:
        scenarios = scenarios[:limit]
    return scenarios


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"job {job_id!r} not found")
    info = job.to_dict()
    if job.status == JobStatus.COMPLETED and job.result is not None:
        result = job.result
        problem_id = result["problem"].id
        state.set_run(problem_id, {**result, "job_status": "completed"})
    return info