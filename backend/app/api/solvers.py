"""
Solvers API — Leaderboard and solver comparison endpoints.
=========================================================
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BenchmarkResult, OptimizationJob, User
from app.security import get_current_user

router = APIRouter(prefix="/api/solvers", tags=["solvers"])


class LeaderboardRow(BaseModel):
    solver_name: str
    solver_type: str
    execution_backend: str
    feasible: bool
    objective_value: float
    financing_cost: float
    risk_total: float
    runtime: float
    constraint_violations: int
    robustness: float
    compute_cost: float
    optimality_note: str
    rank: int


def _classify_solver(name: str) -> tuple[str, str]:
    """Return (solver_type, execution_backend) based on solver name."""
    name_lower = name.lower()
    if "milp" in name_lower or "cbc" in name_lower or "highs" in name_lower:
        return "exact", "classical"
    if "sa" in name_lower or "simulated" in name_lower:
        return "heuristic", "classical"
    if "qubo" in name_lower or "qaoa" in name_lower or "quantum" in name_lower:
        return "quantum", "quantum_simulator"
    return "unknown", "unknown"


@router.get("/leaderboard")
def solver_leaderboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """
    Ranked solver leaderboard across all completed benchmarks for the
    organization's optimization jobs.

    Returns solvers ranked by weighted score (lower objective value = better),
    with execution metadata and feasibility status.
    """
    # Get all completed jobs for this org
    job_ids = [
        j.id for j in
        db.query(OptimizationJob.id)
        .filter(OptimizationJob.org_id == user.org_id, OptimizationJob.status == "completed")
        .all()
    ]

    if not job_ids:
        return []

    # Get all benchmark results for these jobs
    benchmarks = (
        db.query(BenchmarkResult)
        .filter(BenchmarkResult.job_id.in_(job_ids))
        .order_by(BenchmarkResult.objective_value)
        .all()
    )

    if not benchmarks:
        return []

    # Aggregate by solver_name: take best (lowest objective) result per solver
    best_by_solver: dict[str, BenchmarkResult] = {}
    for b in benchmarks:
        if b.solver_name not in best_by_solver or b.objective_value < best_by_solver[b.solver_name].objective_value:
            best_by_solver[b.solver_name] = b

    # Build leaderboard rows
    rows = []
    for solver_name, b in best_by_solver.items():
        metrics = b.metrics or {}
        solver_type, execution_backend = _classify_solver(solver_name)

        rows.append({
            "solver_name": solver_name,
            "solver_type": solver_type,
            "execution_backend": execution_backend,
            "feasible": b.feasible,
            "objective_value": float(b.objective_value),
            "financing_cost": float(metrics.get("financing_cost", b.objective_value)),
            "risk_total": float(metrics.get("risk_total", 0)),
            "runtime": float(b.execution_time_seconds),
            "constraint_violations": int(metrics.get("constraint_violations", 0 if b.feasible else 1)),
            "robustness": float(metrics.get("robustness", 1.0 if b.feasible else 0.0)),
            "compute_cost": float(metrics.get("compute_cost", 0)),
            "optimality_note": metrics.get("optimality_note", "optimal" if b.feasible else "infeasible"),
            "rank": 0,
        })

    # Sort by objective value (ascending = better)
    rows.sort(key=lambda r: r["objective_value"])

    # Assign ranks
    for i, row in enumerate(rows):
        row["rank"] = i + 1

    return rows
