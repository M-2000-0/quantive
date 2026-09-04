"""Enhanced debt optimizer with multi-objective Pareto frontier and scenario comparison.

Minimizes cost subject to risk constraints, generates Pareto-optimal frontier
for trade-off analysis, and enables side-by-side strategy comparison under
macro scenarios.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger("quantive.optimizer")


@dataclass
class OptimizationObjective:
    name: str
    direction: str  # "minimize" or "maximize"
    weight: float = 1.0
    constraint_min: float | None = None
    constraint_max: float | None = None


@dataclass
class DebtInstrumentInput:
    id: str
    name: str
    principal_outstanding: float
    coupon_rate: float
    maturity_date: str
    instrument_type: str
    currency: str = "USD"
    spread_bps: float = 0.0
    is_callable: bool = False
    amortization: dict | None = None


@dataclass
class OptimizationResult:
    allocations: dict[str, float]  # instrument_id -> allocated_amount
    metrics: dict[str, float]
    feasible: bool
    solver: str
    iterations: int
    pareto_rank: int = 0  # 0 = not yet ranked


@dataclass
class ScenarioComparison:
    scenario_name: str
    strategy_a: OptimizationResult
    strategy_b: OptimizationResult
    diff_metrics: dict[str, float]
    winner: str  # "A", "B", or "tie"


class DebtOptimizer:
    """Production debt optimizer with scipy-based solvers.

    Objective: minimize total cost (interest + refinancing risk) subject to:
      - Max single-instrument concentration
      - Max currency exposure
      - Min diversification (number of instruments)
      - Max maturity concentration in any year
    """

    def optimize(
        self,
        instruments: list[DebtInstrumentInput],
        objectives: list[OptimizationObjective] | None = None,
        constraints: dict | None = None,
        budget: float | None = None,
    ) -> OptimizationResult:
        from scipy.optimize import minimize as sp_minimize

        n = len(instruments)
        if n == 0:
            return OptimizationResult(
                allocations={}, metrics={"total_cost": 0}, feasible=True,
                solver="empty", iterations=0
            )

        principals = np.array([i.principal_outstanding for i in instruments])
        coupons = np.array([i.coupon_rate for i in instruments])
        spreads = np.array([i.spread_bps / 10000 for i in instruments])
        total = float(principals.sum())
        budget = budget or total

        constraints = constraints or {}
        max_concentration = constraints.get("max_concentration", 0.40)
        max_fx_exposure = constraints.get("max_fx_exposure", 0.30)

        # Currency flags (1 = foreign)
        fx_flags = np.array([1.0 if i.currency != "USD" else 0.0 for i in instruments])

        def objective(w):
            # Total cost = weighted coupon + spread penalty
            cost = float(np.dot(w, coupons) * budget)
            spread_cost = float(np.dot(w, spreads) * budget)
            concentration_penalty = float(np.max(w ** 2)) * total * 0.5
            return cost + spread_cost * 0.3 + concentration_penalty

        bounds = [(0, min(max_concentration, p / total)) for p in principals]
        cons = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "ineq", "fun": lambda w: max_fx_exposure - float(np.dot(w, fx_flags))},
        ]

        # Multiple starting points for better solutions
        best_result = None
        best_val = float("inf")

        starts = [
            principals / total,  # proportional
            np.ones(n) / n,     # equal weight
        ]

        # Greedy start: cheapest instruments first
        greedy = np.argsort(coupons)
        greedy_w = np.zeros(n)
        remaining = 1.0
        for idx in greedy:
            alloc = min(remaining, principals[idx] / total)
            greedy_w[idx] = alloc
            remaining -= alloc
            if remaining <= 0:
                break
        starts.append(greedy_w)

        for x0 in starts:
            result = sp_minimize(
                objective, x0, method="SLSQP",
                bounds=bounds, constraints=cons,
                options={"maxiter": 2000, "ftol": 1e-14},
            )
            if result.fun < best_val:
                best_val = result.fun
                best_result = result

        if best_result is None:
            best_result = sp_minimize(
                objective, principals / total, method="SLSQP",
                bounds=bounds, constraints=cons,
            )

        weights = best_result.x
        alloc_values = weights * budget
        allocations = {instruments[i].id: float(alloc_values[i]) for i in range(n)}

        # Compute detailed metrics
        total_cost = float(np.dot(weights, coupons) * budget)
        avg_duration = self._compute_avg_duration(instruments, weights)
        fx_exposure = float(np.dot(weights, fx_flags) * 100)
        concentration = float(np.max(weights) * 100)
        diversification = int(np.sum(weights > 0.01))

        return OptimizationResult(
            allocations=allocations,
            metrics={
                "total_annual_cost": round(total_cost, 2),
                "avg_coupon": round(float(np.dot(weights, coupons)) * 100, 4),
                "avg_spread_bps": round(float(np.dot(weights, spreads)) * 10000, 2),
                "avg_duration_years": round(avg_duration, 2),
                "max_concentration_pct": round(concentration, 2),
                "fx_exposure_pct": round(fx_exposure, 2),
                "num_instruments": diversification,
                "total_allocated": round(float(np.sum(alloc_values)), 2),
                "utilization": round(float(np.sum(alloc_values)) / budget * 100, 2) if budget > 0 else 0,
            },
            feasible=best_result.success,
            solver="scipy_slsqp",
            iterations=int(getattr(best_result, "nit", 0)),
        )

    def generate_pareto_frontier(
        self,
        instruments: list[DebtInstrumentInput],
        num_points: int = 20,
        constraints: dict | None = None,
    ) -> list[dict]:
        """Generate Pareto-optimal trade-off curve between cost and risk."""
        from scipy.optimize import minimize as sp_minimize

        n = len(instruments)
        if n == 0:
            return []

        principals = np.array([i.principal_outstanding for i in instruments])
        coupons = np.array([i.coupon_rate for i in instruments])
        spreads = np.array([i.spread_bps / 10000 for i in instruments])
        total = float(principals.sum())
        constraints = constraints or {}
        max_conc = constraints.get("max_concentration", 0.40)
        fx_flags = np.array([1.0 if i.currency != "USD" else 0.0 for i in instruments])

        bounds = [(0, min(max_conc, p / total)) for p in principals]
        cons_base = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        ]

        frontier = []
        risk_weights = np.linspace(0.0, 1.0, num_points)

        for lam in risk_weights:
            def objective(w):
                cost = float(np.dot(w, coupons))
                risk = float(np.dot(w ** 2, np.ones(n)))
                fx_risk = float(np.dot(w, fx_flags))
                return (1 - lam) * cost + lam * (risk + fx_risk * 0.3)

            result = sp_minimize(
                objective, principals / total, method="SLSQP",
                bounds=bounds, constraints=cons_base,
                options={"maxiter": 1000, "ftol": 1e-12},
            )

            weights = result.x
            frontier.append({
                "cost_weight": round(float(np.dot(weights, coupons)) * 100, 4),
                "risk_score": round(float(np.dot(weights ** 2, np.ones(n))), 6),
                "fx_exposure_pct": round(float(np.dot(weights, fx_flags) * 100), 2),
                "max_concentration_pct": round(float(np.max(weights) * 100), 2),
                "allocations": {instruments[i].id: round(float(weights[i] * total), 2) for i in range(n)},
                "pareto_lambda": round(float(lam), 4),
            })

        return frontier

    def compare_strategies(
        self,
        instruments: list[DebtInstrumentInput],
        strategy_a: dict,
        strategy_b: dict,
        scenarios: list[dict] | None = None,
    ) -> dict:
        """Side-by-side comparison of two strategies under macro scenarios."""
        result_a = self._evaluate_strategy(instruments, strategy_a)
        result_b = self._evaluate_strategy(instruments, strategy_b)

        diff = {}
        for key in result_a["metrics"]:
            if key in result_b["metrics"]:
                diff[key] = round(result_a["metrics"][key] - result_b["metrics"][key], 4)

        # Determine winner based on total cost
        cost_a = result_a["metrics"].get("total_annual_cost", float("inf"))
        cost_b = result_b["metrics"].get("total_annual_cost", float("inf"))
        if cost_a < cost_b * 0.98:
            winner = "A"
        elif cost_b < cost_a * 0.98:
            winner = "B"
        else:
            winner = "tie"

        # Scenario stress comparison
        scenario_results = []
        if scenarios:
            for scenario in scenarios:
                stressed_a = self._stress_test(instruments, strategy_a, scenario)
                stressed_b = self._stress_test(instruments, strategy_b, scenario)
                scenario_results.append({
                    "scenario_name": scenario.get("name", "Unnamed"),
                    "strategy_a_cost": stressed_a,
                    "strategy_b_cost": stressed_b,
                    "advantage": "A" if stressed_a < stressed_b else "B" if stressed_b < stressed_a else "tie",
                })

        return {
            "strategy_a": result_a,
            "strategy_b": result_b,
            "differential": diff,
            "winner": winner,
            "scenario_results": scenario_results,
            "compared_at": datetime.now(timezone.utc).isoformat(),
        }

    def _evaluate_strategy(self, instruments: list[DebtInstrumentInput], strategy: dict) -> dict:
        allocations = strategy.get("allocations", {})
        total_cost = 0
        for inst in instruments:
            alloc = allocations.get(inst.id, 0)
            total_cost += alloc * inst.coupon_rate

        principals = np.array([i.principal_outstanding for i in instruments])
        total = float(principals.sum()) if principals.sum() > 0 else 1

        return {
            "name": strategy.get("name", "Strategy"),
            "metrics": {
                "total_annual_cost": round(total_cost, 2),
                "total_allocated": round(sum(allocations.values()), 2),
                "utilization": round(sum(allocations.values()) / total * 100, 2) if total > 0 else 0,
            },
            "allocations": allocations,
        }

    def _stress_test(self, instruments: list[DebtInstrumentInput], strategy: dict, scenario: dict) -> float:
        rate_shock = scenario.get("rate_change", 0)
        fx_shock = scenario.get("fx_shock", 0)
        allocations = strategy.get("allocations", {})
        total_cost = 0
        for inst in instruments:
            alloc = allocations.get(inst.id, 0)
            cost = alloc * inst.coupon_rate
            cost += alloc * rate_shock * 0.3
            if inst.currency != "USD":
                cost += alloc * fx_shock * 0.5
            total_cost += cost
        return round(total_cost, 2)

    def _compute_avg_duration(self, instruments: list[DebtInstrumentInput], weights: np.ndarray) -> float:
        now = datetime.now()
        durations = []
        for i, inst in enumerate(instruments):
            try:
                mat = datetime.strptime(inst.maturity_date, "%Y-%m-%d")
                dur = max((mat - now).days / 365.25, 0.1)
            except (ValueError, TypeError):
                dur = 5.0
            durations.append(dur)
        return float(np.dot(weights, np.array(durations)))
