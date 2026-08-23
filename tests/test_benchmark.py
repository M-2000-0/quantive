"""Benchmark and ranking tests."""
from __future__ import annotations

import pytest

from quantive.benchmark.engine import run_benchmark
from quantive.benchmark.ranking import rank
from quantive.models.results import BenchmarkResult, BenchmarkRow


def test_benchmark_runs_all_solvers(portfolio, problem, scenarios):
    bench = run_benchmark(portfolio, problem, scenarios)
    assert len(bench.rows) == 3
    for row in bench.rows:
        assert row.objective_value > 0
        assert row.runtime >= 0
        assert row.compute_cost >= 0


def test_benchmark_feasibility_reported(portfolio, problem, scenarios):
    bench = run_benchmark(portfolio, problem, scenarios)
    assert all(row.feasible for row in bench.rows)


def test_benchmark_ranking_order(portfolio, problem, scenarios):
    bench = run_benchmark(portfolio, problem, scenarios)
    rows = bench.ranked_rows()
    assert rows[0].rank == 1
    assert rows[-1].rank == len(rows)
    # ranks are unique
    assert len({r.rank for r in rows}) == len(rows)


def test_benchmark_milp_best_overall(portfolio, problem, scenarios):
    bench = run_benchmark(portfolio, problem, scenarios)
    rows = bench.ranked_rows()
    assert rows[0].solver == "milp_cbc"
    assert "objective_value" in rows[0].best_for


def test_ranking_feasibility_gate():
    rows = [
        BenchmarkRow(solver="A", solver_type="classical", execution_backend="classical_cpu", feasible=True,
                     objective_value=10, financing_cost=10, risk_total=10, runtime=1,
                     constraint_violations=0, robustness_worst_cost=10, compute_cost=1, rank=0),
        BenchmarkRow(solver="B", solver_type="classical", execution_backend="classical_cpu", feasible=False,
                     objective_value=5, financing_cost=5, risk_total=5, runtime=0.1,
                     constraint_violations=3, robustness_worst_cost=5, compute_cost=0.1, rank=0),
    ]
    result = rank(rows)
    assert result.rows[1].rank > result.rows[0].rank


def test_normalization_lower_is_better_inverts():
    from quantive.benchmark.ranking import _normalize

    assert _normalize([10.0, 20.0, 30.0], lower_better=True) == pytest.approx([1.0, 0.5, 0.0])
    assert _normalize([10.0, 20.0, 30.0], lower_better=False) == pytest.approx([0.0, 0.5, 1.0])


def test_custom_ranking_weights(portfolio, problem, scenarios):
    # runtime-only ranking should pick the fastest feasible solver
    weights = {"runtime": 1.0, "objective_value": 0.0}
    bench = run_benchmark(portfolio, problem, scenarios, ranking_weights=weights)
    rows = bench.ranked_rows()
    fastest = min(bench.rows, key=lambda r: r.runtime)
    assert rows[0].solver == fastest.solver


def test_benchmark_model_serializable():
    b = BenchmarkResult(problem_id="p", ranking_weights={"objective_value": 1.0})
    data = b.model_dump()
    assert data["problem_id"] == "p"


def test_benchmark_robustness_metric_present(portfolio, problem, scenarios):
    bench = run_benchmark(portfolio, problem, scenarios)
    for row in bench.rows:
        assert row.robustness_worst_cost > 0
        assert row.constraint_violation_magnitude >= 0