import threading

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import app.database as database_module
from app.config import get_settings
from app.database import get_db
from app.jobs import request_cancel, run_optimization_job
from app.models import (
    BenchmarkResult,
    JobStatus,
    OptimizationJob,
    OptimizationResult,
    Portfolio,
    Strategy,
    User,
    UserRole,
)
from app.pagination import (
    FilterQuery,
    PaginationQuery,
    apply_filters,
    create_paginated_response,
    paginate_query,
)
from app.schemas import (
    BenchmarkResponse,
    OptimizationCreate,
    OptimizationResponse,
    OptimizationResultResponse,
    StrategyResponse,
)
from app.security import get_current_user, log_audit_event

settings = get_settings()

router = APIRouter(prefix="/api/optimizations", tags=["optimizations"])


@router.get("")
def list_optimizations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    pagination: PaginationQuery = Depends(),
    filters: FilterQuery = Depends(),
):
    query = db.query(OptimizationJob).filter(OptimizationJob.org_id == user.org_id)

    # Apply filters
    query = apply_filters(query, filters, OptimizationJob)

    # Search in name
    items, total = paginate_query(
        query,
        limit=pagination.limit,
        offset=pagination.offset,
        cursor=pagination.cursor,
        search=pagination.search,
        search_fields=["name"],
        sort_by=pagination.sort_by or "created_at",
        sort_order=pagination.sort_order,
        model=OptimizationJob,
    )

    return create_paginated_response(
        items=items,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
        serializer=lambda j: OptimizationResponse.model_validate(j).model_dump(mode="json"),
    )


@router.post("", response_model=OptimizationResponse, status_code=201)
def create_optimization(data: OptimizationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role == UserRole.VIEWER:
        raise HTTPException(status_code=403, detail="Viewers cannot create optimizations")

    portfolio = db.query(Portfolio).filter(
        Portfolio.id == data.portfolio_id, Portfolio.org_id == user.org_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    constraints = data.constraints
    max_budget = constraints.get("max_budget")
    if max_budget and max_budget <= 0:
        raise HTTPException(status_code=422, detail="max_budget must be positive")
    max_single_instrument_pct = constraints.get("max_single_instrument_pct")
    if max_single_instrument_pct and (max_single_instrument_pct <= 0 or max_single_instrument_pct > 1):
        raise HTTPException(status_code=422, detail="max_single_instrument_pct must be between 0 and 1")

    scenario_config = data.scenario_config or {}
    if not scenario_config.get("num_scenarios"):
        scenario_config["num_scenarios"] = settings.DEFAULT_SCENARIO
    if scenario_config.get("num_scenarios", 0) > settings.MAX_SCENARIO:
        raise HTTPException(
            status_code=422,
            detail=f"num_scenarios cannot exceed {settings.MAX_SCENARIO}",
        )

    job = OptimizationJob(
        portfolio_id=data.portfolio_id,
        org_id=user.org_id,
        created_by=user.id,
        name=data.name.strip(),
        status=JobStatus.QUEUED,
        optimization_type=data.optimization_type,
        objectives=data.objectives,
        constraints=data.constraints,
        solver_config=data.solver_config or {"solvers": ["greedy", "mean_variance", "scenario_based"]},
        scenario_config=scenario_config,
        random_seed=data.random_seed,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    log_audit_event(db, user, "optimization.created", "optimization", job.id)

    def _run():
        def factory():
            return database_module.SessionLocal()
        run_optimization_job(job.id, factory)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return OptimizationResponse.model_validate(job)


@router.get("/{job_id}", response_model=OptimizationResponse)
def get_optimization(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(OptimizationJob).filter(
        OptimizationJob.id == job_id, OptimizationJob.org_id == user.org_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Optimization job not found")
    return OptimizationResponse.model_validate(job)


@router.delete("/{job_id}", status_code=204)
def cancel_optimization(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(OptimizationJob).filter(
        OptimizationJob.id == job_id, OptimizationJob.org_id == user.org_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Optimization job not found")
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
        raise HTTPException(status_code=400, detail="Cannot cancel a finished job")

    job.status = JobStatus.CANCELLED
    job.completed_at = None
    db.commit()
    request_cancel(job_id)
    log_audit_event(db, user, "optimization.cancelled", "optimization", job.id)


@router.get("/{job_id}/strategies", response_model=list[StrategyResponse])
def get_strategies(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(OptimizationJob).filter(
        OptimizationJob.id == job_id, OptimizationJob.org_id == user.org_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Optimization job not found")
    strategies = db.query(Strategy).filter(Strategy.job_id == job_id).order_by(Strategy.rank).all()
    return [StrategyResponse.model_validate(s) for s in strategies]


@router.get("/{job_id}/benchmarks", response_model=list[BenchmarkResponse])
def get_benchmarks(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(OptimizationJob).filter(
        OptimizationJob.id == job_id, OptimizationJob.org_id == user.org_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Optimization job not found")
    benchmarks = db.query(BenchmarkResult).filter(BenchmarkResult.job_id == job_id).all()
    return [BenchmarkResponse.model_validate(b) for b in benchmarks]


@router.get("/{job_id}/results", response_model=list[OptimizationResultResponse])
def get_results(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(OptimizationJob).filter(
        OptimizationJob.id == job_id, OptimizationJob.org_id == user.org_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Optimization job not found")
    results = db.query(OptimizationResult).filter(OptimizationResult.job_id == job_id).all()
    return [OptimizationResultResponse.model_validate(r) for r in results]


@router.get("/{job_id}/report")
def get_report(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(OptimizationJob).filter(
        OptimizationJob.id == job_id, OptimizationJob.org_id == user.org_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Optimization job not found")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Optimization not completed yet")

    strategies = db.query(Strategy).filter(Strategy.job_id == job_id).order_by(Strategy.rank).all()
    benchmarks = db.query(BenchmarkResult).filter(BenchmarkResult.job_id == job_id).all()
    results = db.query(OptimizationResult).filter(OptimizationResult.job_id == job_id).all()

    portfolio = db.query(Portfolio).filter(Portfolio.id == job.portfolio_id).first()

    report = {
        "job_id": job.id,
        "job_name": job.name,
        "status": job.status.value,
        "optimization_type": job.optimization_type.value if hasattr(job.optimization_type, 'value') else job.optimization_type,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "random_seed": job.random_seed,
        "model_version": job.model_version,
        "portfolio": {
            "name": portfolio.name if portfolio else "Unknown",
            "num_instruments": len(portfolio.instruments) if portfolio else 0,
        },
        "strategies": [
            {
                "name": s.name,
                "description": s.description,
                "rank": s.rank,
                "metrics": s.metrics,
                "stress_test_results": s.stress_test_results,
            }
            for s in strategies
        ],
        "benchmarks": [
            {
                "solver_name": b.solver_name,
                "execution_time_seconds": b.execution_time_seconds,
                "objective_value": b.objective_value,
                "feasible": b.feasible,
                "iterations": b.iterations,
                "metrics": b.metrics,
            }
            for b in benchmarks
        ],
        "summary": results[0].metrics if results else {},
    }

    log_audit_event(db, user, "report.generated", "optimization", job.id)
    return report
