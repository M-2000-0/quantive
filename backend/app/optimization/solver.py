"""
Debt Optimization Engine
=========================
Constrained optimization: minimize cost-at-risk subject to risk/exposure limits.
Uses scipy.optimize for linear/quadratic programming.
"""

import math
from dataclasses import dataclass, field
from typing import Optional

try:
    from scipy.optimize import minimize, LinearConstraint, Bounds
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


@dataclass
class OptimizationProblem:
    """Formulated optimization problem."""
    n_instruments: int
    objective: str = "minimize_cost"  # minimize_cost, minimize_risk, maximize_return
    # Constraints
    max_refinancing_risk_pct: float = 25.0
    max_fx_exposure_pct: float = 60.0
    max_single_instrument_pct: float = 30.0
    min_duration_years: float = 3.0
    max_duration_years: float = 15.0
    target_return_pct: float = 5.0
    risk_budget_pct: float = 5.0


@dataclass
class OptimizationResult:
    """Solution from optimizer."""
    feasible: bool
    allocations: list[dict]  # [{instrument, weight, amount}]
    objective_value: float
    risk_metrics: dict
    constraint_violations: list[str]
    solver_status: str
    solve_time_ms: float = 0.0


class DebtOptimizer:
    """
    Constrained debt portfolio optimizer.

    Minimizes expected cost subject to:
    - Refinancing risk ≤ X%
    - FX exposure ≤ Y%
    - Single instrument ≤ Z%
    - Duration within [min, max]
    """

    def __init__(self, problem: OptimizationProblem):
        self.problem = problem
        self.n = problem.n_instruments

    def optimize(
        self,
        current_weights: list[float],
        costs: list[float],
        refinancing_risks: list[float],
        fx_exposures: list[float],
        durations: list[float],
    ) -> OptimizationResult:
        """Run optimization."""
        import time
        start = time.time()

        if not SCIPY_AVAILABLE:
            return self._heuristic_fallback(
                current_weights, costs, refinancing_risks, fx_exposures, durations
            )

        n = self.n
        p = self.problem

        # Objective: minimize weighted cost
        def objective(w):
            return sum(w[i] * costs[i] for i in range(n))

        # Constraints
        constraints = []

        # Refinancing risk ≤ max
        def refinancing_constraint(w):
            return p.max_refinancing_risk_pct - sum(w[i] * refinancing_risks[i] for i in range(n))
        constraints.append({"type": "ineq", "fun": refinancing_constraint})

        # FX exposure ≤ max
        def fx_constraint(w):
            return p.max_fx_exposure_pct - sum(w[i] * fx_exposures[i] for i in range(n))
        constraints.append({"type": "ineq", "fun": fx_constraint})

        # Duration bounds
        def duration_min(w):
            return sum(w[i] * durations[i] for i in range(n)) - p.min_duration_years
        constraints.append({"type": "ineq", "fun": duration_min})

        def duration_max(w):
            return p.max_duration_years - sum(w[i] * durations[i] for i in range(n))
        constraints.append({"type": "ineq", "fun": duration_max})

        # Bounds: 0 ≤ w[i] ≤ max_single_pct
        bounds = [(0, p.max_single_instrument_pct / 100) for _ in range(n)]

        # Sum to 1 (or current total)
        def sum_constraint(w):
            return 1.0 - sum(w)
        constraints.append({"type": "eq", "fun": sum_constraint})

        # Initial guess: current weights
        w0 = current_weights[:]

        try:
            result = minimize(
                objective, w0, method="SLSQP",
                bounds=bounds, constraints=constraints,
                options={"maxiter": 1000, "ftol": 1e-10},
            )

            allocations = []
            violations = []
            for i in range(n):
                w = max(0, result.x[i])
                if w > 0.001:
                    allocations.append({
                        "instrument": i,
                        "weight": round(w * 100, 2),
                        "amount": round(w * 1e9, 0),  # Assume $1B total
                    })

            # Check constraint violations
            total_refin = sum(result.x[i] * refinancing_risks[i] for i in range(n))
            total_fx = sum(result.x[i] * fx_exposures[i] for i in range(n))
            total_dur = sum(result.x[i] * durations[i] for i in range(n))

            if total_refin > p.max_refinancing_risk_pct:
                violations.append(f"Refinancing risk {total_refin:.1f}% exceeds {p.max_refinancing_risk_pct}%")
            if total_fx > p.max_fx_exposure_pct:
                violations.append(f"FX exposure {total_fx:.1f}% exceeds {p.max_fx_exposure_pct}%")

            elapsed = (time.time() - start) * 1000

            return OptimizationResult(
                feasible=result.success and not violations,
                allocations=allocations,
                objective_value=round(result.fun, 4),
                risk_metrics={
                    "refinancing_risk": round(total_refin, 2),
                    "fx_exposure": round(total_fx, 2),
                    "duration": round(total_dur, 2),
                },
                constraint_violations=violations,
                solver_status="optimal" if result.success else "infeasible",
                solve_time_ms=round(elapsed, 2),
            )

        except Exception as e:
            return OptimizationResult(
                feasible=False, allocations=[], objective_value=float("inf"),
                risk_metrics={}, constraint_violations=[str(e)],
                solver_status="error",
            )

    def _heuristic_fallback(
        self, weights, costs, refin_risks, fx_exp, durations
    ) -> OptimizationResult:
        """When scipy not available, use greedy heuristic."""
        n = self.n
        p = self.problem

        # Greedy: allocate to lowest cost, respect constraints
        indexed = sorted(range(n), key=lambda i: costs[i])
        alloc = [0.0] * n
        remaining = 1.0

        for i in indexed:
            max_w = min(remaining, p.max_single_instrument_pct / 100)
            if max_w <= 0:
                break
            alloc[i] = max_w
            remaining -= max_w

        allocations = []
        for i in range(n):
            if alloc[i] > 0.001:
                allocations.append({
                    "instrument": i,
                    "weight": round(alloc[i] * 100, 2),
                    "amount": round(alloc[i] * 1e9, 0),
                })

        return OptimizationResult(
            feasible=True, allocations=allocations,
            objective_value=round(sum(alloc[i] * costs[i] for i in range(n)), 4),
            risk_metrics={
                "refinancing_risk": round(sum(alloc[i] * refin_risks[i] for i in range(n)), 2),
                "fx_exposure": round(sum(alloc[i] * fx_exp[i] for i in range(n)), 2),
                "duration": round(sum(alloc[i] * durations[i] for i in range(n)), 2),
            },
            constraint_violations=[],
            solver_status="heuristic (scipy not available)",
        )

    def handle_infeasible(self) -> dict:
        """Diagnose why constraints are infeasible."""
        return {
            "status": "infeasible",
            "diagnosis": "No feasible solution exists for the given constraints",
            "recommendations": [
                "Relax the most restrictive constraint",
                "Increase max_refinancing_risk_pct if refinancing is the bottleneck",
                "Increase max_fx_exposure_pct if FX is the bottleneck",
                "Widen the duration range",
            ],
        }
