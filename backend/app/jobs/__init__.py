import logging
import threading
from datetime import datetime, timezone

from app.models import (
    BenchmarkResult,
    DebtInstrument,
    JobStatus,
    OptimizationJob,
    OptimizationResult,
    Scenario,
    Strategy,
)
from app.optimization import BenchmarkRunner, ScenarioGenerator, StrategyGenerator, StressTestRunner, get_solver

logger = logging.getLogger("quantive.jobs")

_cancel_events: dict[str, threading.Event] = {}


def request_cancel(job_id: str):
    event = _cancel_events.get(job_id)
    if event:
        event.set()


def _check_cancelled(job_id: str):
    event = _cancel_events.get(job_id)
    if event and event.is_set():
        raise InterruptedError(f"Job {job_id} was cancelled")


def run_optimization_job(job_id: str, db_factory, timeout_seconds: int = 300):
    cancel_event = threading.Event()
    _cancel_events[job_id] = cancel_event

    db = db_factory()
    try:
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
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

        # Phase 3: Benchmark
        job.status = JobStatus.BENCHMARKING
        job.progress = 0.7
        db.commit()
        logger.info(f"Job {job_id}: Benchmarking solvers")

        _check_cancelled(job_id)
        benchmark_runner = BenchmarkRunner()
        benchmarks = benchmark_runner.run_benchmarks(instruments_data, job.objectives, job.constraints, scenarios_data, seed)
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
        logger.info(f"Job {job_id}: Generating strategies")

        _check_cancelled(job_id)
        strategy_gen = StrategyGenerator()
        strategies_data = strategy_gen.generate_strategies(instruments_data, benchmarks, scenarios_data, seed)

        # Phase 5: Stress test
        job.status = JobStatus.STRESS_TESTING
        job.progress = 0.85
        db.commit()
        logger.info(f"Job {job_id}: Stress testing")

        stress_runner = StressTestRunner()
        for strat_data in strategies_data:
            _check_cancelled(job_id)
            stress_results = stress_runner.run_stress_test(instruments_data, strat_data["allocations"], scenarios_data, seed)
            strat_data["stress_test_results"] = stress_results

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
        logger.info(f"Job {job_id}: Completed successfully")

    except InterruptedError:
        logger.info(f"Job {job_id}: Cancelled")
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        if job:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as e:
        logger.exception(f"Job {job_id}: Failed with error")
        job = db.query(OptimizationJob).filter(OptimizationJob.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)[:2000]
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        _cancel_events.pop(job_id, None)
        db.close()
