import logging
import threading
import uuid
from datetime import datetime, timezone

import numpy as np

from app.job_store import get_singleton_job_store
from app.models import (
    BenchmarkResult,
    DebtInstrument,
    JobStatus,
    OptimizationResult,
    Scenario,
    Strategy,
)
from app.models import (
    OptimizationJob as JobModel,
)
from app.optimization import BenchmarkRunner, ScenarioGenerator, StrategyGenerator, StressTestRunner, get_solver

logger = logging.getLogger("quantive.jobs")

# Get the job store instance
_job_store = get_singleton_job_store()

# Keep legacy cancel events for backwards compatibility
_cancel_events: dict[str, threading.Event] = {}


def _to_native(obj):
    if isinstance(obj, dict):
        return {k: _to_native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_native(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def request_cancel(job_id: str):
    # Use the job store
    _job_store.request_cancel(job_id)
    # Also set legacy event for in-process cancellation
    event = _cancel_events.get(job_id)
    if event:
        event.set()


def _check_cancelled(job_id: str):
    # Check both job store and legacy events
    if _job_store.is_cancelled(job_id):
        raise InterruptedError(f"Job {job_id} was cancelled")
    event = _cancel_events.get(job_id)
    if event and event.is_set():
        raise InterruptedError(f"Job {job_id} was cancelled")


def run_optimization_job(job_id: str, db_factory, timeout_seconds: int = 300):
    # Register cancel event for in-process cancellation
    cancel_event = threading.Event()
    _cancel_events[job_id] = cancel_event

    # Update job store with progress
    _job_store.update_job_progress(job_id, "running", 0.0)

    db = db_factory()
    try:
        job = db.query(JobModel).filter(JobModel.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        job.progress = 0.0
        db.commit()

        instruments = db.query(DebtInstrument).filter(
            DebtInstrument.portfolio_id == job.portfolio_id
        ).all()
        instruments_data = [
            {
                "id": inst.id,
                "name": inst.name,
                "instrument_type": inst.instrument_type.value if hasattr(inst.instrument_type, 'value') else inst.instrument_type,
                "currency": inst.currency,
                "principal_outstanding": inst.principal_outstanding,
                "coupon_rate": inst.coupon_rate,
                "maturity_date": inst.maturity_date,
                "issue_date": inst.issue_date,
                "spread_bps": inst.spread_bps,
            }
            for inst in instruments
        ]

        if not instruments_data:
            job.status = JobStatus.FAILED
            job.error_message = "No instruments found in portfolio"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        seed = job.random_seed

        # Phase 1: Generate scenarios
        job.status = JobStatus.SCENARIO_GENERATION
        job.progress = 0.1
        db.commit()
        _job_store.update_job_progress(job_id, "scenario_generation", 0.1)
        logger.info(f"Job {job_id}: Generating scenarios")

        scenario_config = job.scenario_config or {}
        if not scenario_config.get("num_scenarios"):
            scenario_config["num_scenarios"] = 10000
        generator = ScenarioGenerator(seed=seed)
        scenarios_data = generator.generate_all_scenarios(scenario_config)

        n_scenarios = scenarios_data["num_scenarios"]
        for i in range(min(100, n_scenarios)):
            _check_cancelled(job_id)
            scenario = Scenario(
                job_id=job_id,
                name=f"Scenario {i + 1}",
                scenario_config={"index": i},
                market_shocks={
                    "rate": float(scenarios_data["interest_rates"][i, -1]),
                    "inflation": float(scenarios_data["inflation"][i, -1]),
                },
                probability=1.0 / n_scenarios,
            )
            db.add(scenario)
        db.commit()

        _check_cancelled(job_id)

        # Phase 2: Run solvers
        job.status = JobStatus.SOLVING
        job.progress = 0.3
        db.commit()
        _job_store.update_job_progress(job_id, "solving", 0.3)
        logger.info(f"Job {job_id}: Running solvers")

        solver_names = job.solver_config.get("solvers", ["greedy", "mean_variance", "scenario_based"])
        all_results = {}
        for solver_name in solver_names:
            _check_cancelled(job_id)
            solver = get_solver(solver_name)
            result = solver.solve(instruments_data, job.objectives, job.constraints, scenarios_data, seed)
            all_results[solver_name] = result

        job.progress = 0.6
        db.commit()
        _job_store.update_job_progress(job_id, "solving", 0.6)

        # Phase 3: Benchmark
        job.status = JobStatus.BENCHMARKING
        job.progress = 0.7
        db.commit()
        _job_store.update_job_progress(job_id, "benchmarking", 0.7)
        logger.info(f"Job {job_id}: Benchmarking solvers")

        _check_cancelled(job_id)
        benchmark_runner = BenchmarkRunner()
        benchmarks = benchmark_runner.run_benchmarks(instruments_data, job.objectives, job.constraints, scenarios_data, seed)
        benchmarks = _to_native(benchmarks)
        for bm in benchmarks:
            bench_result = BenchmarkResult(
                job_id=job_id,
                solver_name=bm["solver_name"],
                execution_time_seconds=bm["execution_time_seconds"],
                objective_value=bm["objective_value"],
                feasible=bm["feasible"],
                iterations=bm["iterations"],
                metrics=bm["metrics"],
            )
            db.add(bench_result)
        db.commit()

        # Phase 4: Generate strategies
        job.progress = 0.8
        db.commit()
        _job_store.update_job_progress(job_id, "benchmarking", 0.8)
        logger.info(f"Job {job_id}: Generating strategies")

        _check_cancelled(job_id)
        strategy_gen = StrategyGenerator()
        strategies_data = strategy_gen.generate_strategies(instruments_data, benchmarks, scenarios_data, seed)

        # Phase 5: Stress test
        job.status = JobStatus.STRESS_TESTING
        job.progress = 0.85
        db.commit()
        _job_store.update_job_progress(job_id, "stress_testing", 0.85)
        logger.info(f"Job {job_id}: Stress testing")

        stress_runner = StressTestRunner()
        for strat_data in strategies_data:
            _check_cancelled(job_id)
            stress_results = stress_runner.run_stress_test(instruments_data, strat_data["allocations"], scenarios_data, seed)
            strat_data["stress_test_results"] = stress_results
            strat_data = _to_native(strat_data)

            strategy = Strategy(
                job_id=job_id,
                name=strat_data["name"],
                description=strat_data["description"],
                allocations=strat_data["allocations"],
                metrics=strat_data["metrics"],
                stress_test_results=strat_data["stress_test_results"],
                rank=strat_data["rank"],
            )
            db.add(strategy)
        db.commit()

        # Phase 6: Save results
        all_results = _to_native(all_results)
        best_solver = min(all_results.items(), key=lambda x: x[1]["objective_value"])
        result_record = OptimizationResult(
            job_id=job_id,
            strategy_id=None,
            metrics={
                "best_solver": best_solver[0],
                "objective_value": best_solver[1]["objective_value"],
                "num_scenarios": n_scenarios,
                "num_instruments": len(instruments_data),
                "benchmarks": benchmarks,
            },
            allocation=best_solver[1].get("allocations", {}),
        )
        db.add(result_record)

        job.status = JobStatus.COMPLETED
        job.progress = 1.0
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        _job_store.complete_job(job_id, result={"status": "completed"})
        logger.info(f"Job {job_id}: Completed successfully")

    except InterruptedError:
        logger.info(f"Job {job_id}: Cancelled")
        job = db.query(JobModel).filter(JobModel.id == job_id).first()
        if job:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
        _job_store.complete_job(job_id, error="Cancelled")
    except Exception as e:
        logger.exception(f"Job {job_id}: Failed with error")
        job = db.query(JobModel).filter(JobModel.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)[:2000]
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
        _job_store.complete_job(job_id, error=str(e)[:2000])
    finally:
        _cancel_events.pop(job_id, None)
        db.close()


# ---------------------------------------------------------------------------
# Lightweight in-memory runtime jobs.
# Used by app.main demo/background endpoints (`JOBS`, `create_job`, `get_job`).
# The DB-backed pipeline above remains the production path for /api/optimizations.
# ---------------------------------------------------------------------------


class RuntimeJob:
    """Minimal runtime handle for background demo jobs."""

    def __init__(self, job_id: str, **config):
        self.id = job_id
        self.status = "pending"
        self.result = None
        self.error = None
        self.config = config

    def to_dict(self) -> dict:
        return {
            "job_id": self.id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


RUNTIME_JOBS: dict = {}

# Alias consumed by app.main (`from app.jobs import JOBS`).
JOBS = RUNTIME_JOBS


def create_job(job_id=None, **config) -> RuntimeJob:
    """Register a lightweight runtime job and return it."""
    if job_id is None:
        job_id = str(uuid.uuid4())
    job = RuntimeJob(job_id, **config)
    RUNTIME_JOBS[job_id] = job
    return job


def get_job(job_id):
    """Return a runtime job by id, or None."""
    return RUNTIME_JOBS.get(job_id)


# Name compatibility: app.main imports OptimizationJob from this module for
# runtime jobs; the SQLAlchemy DB model is imported above as JobModel.
OptimizationJob = RuntimeJob
