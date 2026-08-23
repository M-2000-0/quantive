from __future__ import annotations

from datetime import date

from quantive.orchestration import run_full_job, solve_problem, materialize_scenarios
from quantive.models.enums import Currency, RateType
from quantive.models.instruments import DebtInstrument, Portfolio, make_portfolio
from quantive.models.optimization import (
    OptimizationProblem, ScenarioConfiguration, SolverConfiguration,
    OptimizationObjective, default_constraints,
)
from quantive.models.enums import StrategyProfile
from quantive.models.results import OptimizationResult


def _small_portfolio() -> Portfolio:
    instruments = [
        DebtInstrument(id=f"i{i}", name=f"Bond {i}", currency=Currency.USD,
                       principal=20_000.0, coupon=0.04 + 0.001 * i,
                       maturity_date=date(2028 + i, 1, 1), issue_date=date(2025, 1, 1),
                       rate_type=RateType.FIXED)
        for i in range(5)
    ]
    return make_portfolio("small", "Small Test Portfolio", instruments)


def _small_problem(solver: str = "simulated_annealing") -> OptimizationProblem:
    return OptimizationProblem(
        id="small-problem", name="Small Problem",
        portfolio_id="small", financing_requirement=100_000.0,
        objectives=OptimizationObjective(),
        constraints=default_constraints(Currency.USD),
        scenarios=[],
        scenario_config=ScenarioConfiguration(monte_carlo_count=10, include_named=[]),
        solver_config=SolverConfiguration(solver=solver, time_limit_seconds=10),
        reference_currency=Currency.USD,
        profile=StrategyProfile.BEST_OVERALL,
    )


class TestOrchestration:
    def test_solve_problem(self):
        portfolio = _small_portfolio()
        problem = _small_problem()
        scenarios = materialize_scenarios(problem, seed=42)
        result = solve_problem(portfolio, problem, scenarios)
        assert isinstance(result, OptimizationResult)
        assert result.strategy is not None
        assert len(result.scenario_results) > 0

    def test_run_full_job_keys(self):
        portfolio = _small_portfolio()
        problem = _small_problem()
        out = run_full_job(portfolio, problem, scenario_seed=42)
        assert "result" in out
        assert "strategies" in out
        assert "benchmark" in out
        assert "stress" in out
        assert "scenarios" in out
        assert "spec" in out
        assert len(out["strategies"]) == 4
        assert out["benchmark"] is not None

    def test_run_full_job_strategies_feasible(self):
        portfolio = _small_portfolio()
        problem = _small_problem()
        out = run_full_job(portfolio, problem, scenario_seed=42)
        for s in out["strategies"]:
            assert s.allocation is not None

    def test_run_full_job_stress(self):
        portfolio = _small_portfolio()
        problem = _small_problem()
        out = run_full_job(portfolio, problem, scenario_seed=42)
        assert len(out["stress"]) == 4
        for sid, stress in out["stress"].items():
            assert stress is not None

    def test_materialize_scenarios(self):
        problem = _small_problem()
        scenarios = materialize_scenarios(problem, seed=42)
        assert len(scenarios) > 0

    def test_solve_deterministic(self):
        portfolio = _small_portfolio()
        problem = _small_problem()
        scenarios = materialize_scenarios(problem, seed=42)
        r1 = solve_problem(portfolio, problem, scenarios)
        r2 = solve_problem(portfolio, problem, scenarios)
        assert r1.strategy.objective_value == r2.strategy.objective_value

    def test_full_job_deterministic(self):
        portfolio = _small_portfolio()
        problem = _small_problem()
        out1 = run_full_job(portfolio, problem, scenario_seed=42)
        out2 = run_full_job(portfolio, problem, scenario_seed=42)
        assert out1["result"].strategy.objective_value == out2["result"].strategy.objective_value

    def test_result_has_scenario_results(self):
        portfolio = _small_portfolio()
        problem = _small_problem()
        scenarios = materialize_scenarios(problem, seed=42)
        result = solve_problem(portfolio, problem, scenarios)
        assert len(result.scenario_results) > 0
        for sr in result.scenario_results:
            assert sr.financing_cost is not None
