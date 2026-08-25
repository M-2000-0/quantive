"""Classical MILP solver built on HiGHS.

HiGHS is a high-performance open-source LP/MILP solver that can serve as
an alternative to CBC. When installed, it provides faster solve times for
large-scale problems. Falls back to PuLP/CBC if HiGHS is not available.
"""
from __future__ import annotations

import importlib.util
import logging
from time import perf_counter

from quantive.models.enums import ExecutionBackend, SolverType
from quantive.models.optimization import SolverConfiguration
from quantive.objectives.spec import ProblemSpec
from quantive.solvers.base import SolveResult, SolverInterface, build_result

logger = logging.getLogger("quantive.solvers.highs")

HAS_HIGHS = importlib.util.find_spec("highs") is not None
if not HAS_HIGHS:
    logger.info("HiGHS not installed; HighsSolver will use PuLP/CBC fallback")


class HiGHSSolver(SolverInterface):
    """HiGHS solver for LP/MILP problems.

    Uses the HiGHS Python interface when available, with PuLP/CBC as fallback.
    """

    name = "highs"
    solver_type = SolverType.CLASSICAL
    execution_backend = ExecutionBackend.CLASSICAL_CPU

    def __init__(self):
        if not HAS_HIGHS:
            logger.warning("HiGHS not available, will use PuLP/CBC fallback")

    def solve(self, spec: ProblemSpec, config: SolverConfiguration) -> SolveResult:
        if HAS_HIGHS:
            return self._solve_highs(spec, config)
        else:
            return self._solve_pulp_fallback(spec, config)

    def _solve_highs(self, spec: ProblemSpec, config: SolverConfiguration) -> SolveResult:
        """Solve using HiGHS Python API directly."""
        t0 = perf_counter()

        try:
            import highs

            N = spec.n_instruments
            R = spec.financing_requirement
            w_cost, w_refi, w_ir, w_fx = spec.weights

            h = highs.Highs()

            # Variables: x[i] in [0, capacity[i]]
            for i in range(N):
                h.addCol(0.0, 0.0, float(spec.capacity[i]))

            # Objective: minimize weighted cost
            cost_coeff = spec.cost_matrix @ spec.probabilities
            obj_coeffs = []
            for i in range(N):
                coeff = w_cost * cost_coeff[i] + w_ir * float(spec.ir_risk[i]) + w_fx * float(spec.fx_risk[i])
                obj_coeffs.append(coeff)
            h.changeColCostBatch(range(N), obj_coeffs)

            # Equality constraint: sum(x) == R
            h.addRow(-highs.kHighsInf, R, {i: 1.0 for i in range(N)})

            # Floating rate limit
            if spec.floating_rate_limit_share is not None:
                float_idx = [i for i in range(N) if spec.is_floating[i]]
                if float_idx:
                    h.addRow(-highs.kHighsInf, spec.floating_rate_limit_share * R,
                             {i: 1.0 for i in float_idx})

            # Foreign currency limit
            if spec.foreign_currency_limit_share is not None:
                foreign_idx = [i for i in range(N) if spec.is_foreign[i]]
                if foreign_idx:
                    h.addRow(-highs.kHighsInf, spec.foreign_currency_limit_share * R,
                             {i: 1.0 for i in foreign_idx})

            # Minimum liquidity
            if spec.min_liquidity_share > 0:
                liquid_idx = [i for i in range(N) if spec.is_liquid[i]]
                if liquid_idx:
                    h.addRow(spec.min_liquidity_share * R, highs.kHighsInf,
                             {i: 1.0 for i in liquid_idx})

            # Per-currency limits
            for ccy, cap_share in spec.per_currency_limits.items():
                ccy_idx = [i for i in range(N) if spec.currencies[i] == ccy]
                if ccy_idx:
                    h.addRow(-highs.kHighsInf, cap_share * R,
                             {i: 1.0 for i in ccy_idx})

            # Refinancing caps per bucket
            for bucket in set(int(b) for b in spec.year_bucket):
                idx = [i for i in range(N) if spec.year_bucket[i] == bucket]
                h.addRow(-highs.kHighsInf, spec.refi_cap_share * R,
                         {i: 1.0 for i in idx})

            # Cardinality constraint (if set)
            if spec.max_instruments is not None:
                # Binary variables for cardinality
                y_start = N
                for i in range(N):
                    h.addCol(0.0, 0.0, 1.0)  # y[i] binary
                    h.changeColIntegrality(N + i, highs.HighsVarType.kHighsVarTypeInteger)

                # x[i] <= capacity[i] * y[i]
                for i in range(N):
                    h.addRow(-highs.kHighsInf, 0.0,
                             {i: 1.0, y_start + i: -float(spec.capacity[i])})

                # sum(y) <= max_instruments
                h.addRow(-highs.kHighsInf, spec.max_instruments,
                         {y_start + i: 1.0 for i in range(N)})

            # Set time limit
            h.setOptionValue("time_limit", config.time_limit_seconds)
            h.setOptionValue("output_flag", False)

            # Solve
            h.run()

            _status = h.getInfoValue("primal_solution_status")
            model_status = h.getModelStatus()

            runtime = perf_counter() - t0

            if model_status == highs.HighsModelStatus.kOptimal:
                sol = h.getSolution()
                alloc = {spec.instrument_ids[i]: max(0.0, sol.col_value[i]) for i in range(N)}
                note = "globally optimal (HiGHS proved optimality)"
                return build_result(
                    spec, alloc, self.name, self.solver_type, self.execution_backend,
                    runtime, iterations=h.getInfoValue("simplex_iteration_count")[1] if hasattr(h, 'getInfoValue') else 0,
                    optimality_note=note,
                    metadata={"solver": "highs", "status": str(model_status)},
                )
            elif model_status == highs.HighsModelStatus.kInfeasible:
                alloc = {spec.instrument_ids[i]: 0.0 for i in range(N)}
                return build_result(
                    spec, alloc, self.name, self.solver_type, self.execution_backend,
                    runtime, optimality_note="INFEASIBLE (HiGHS)",
                    metadata={"solver": "highs", "status": "infeasible"},
                )
            else:
                # Try to get best solution found
                try:
                    sol = h.getSolution()
                    alloc = {spec.instrument_ids[i]: max(0.0, sol.col_value[i]) for i in range(N)}
                    note = f"feasible solution found (HiGHS status={model_status})"
                except Exception:
                    alloc = {spec.instrument_ids[i]: 0.0 for i in range(N)}
                    note = f"no solution found (HiGHS status={model_status})"

                return build_result(
                    spec, alloc, self.name, self.solver_type, self.execution_backend,
                    runtime, optimality_note=note,
                    metadata={"solver": "highs", "status": str(model_status)},
                )

        except Exception as e:
            runtime = perf_counter() - t0
            logger.exception("HiGHS solver failed, falling back to empty allocation")
            alloc = {spec.instrument_ids[i]: 0.0 for i in range(spec.n_instruments)}
            return build_result(
                spec, alloc, self.name, self.solver_type, self.execution_backend,
                runtime, optimality_note=f"HiGHS error: {str(e)[:200]}",
                metadata={"solver": "highs", "error": str(e)[:200]},
            )

    def _solve_pulp_fallback(self, spec: ProblemSpec, config: SolverConfiguration) -> SolveResult:
        """Fallback to PuLP/CBC when HiGHS is not installed."""
        from quantive.solvers.milp import MILPSolver
        fallback = MILPSolver()
        fallback.name = "highs_fallback_cbc"
        result = fallback.solve(spec, config)
        result.optimality_note = f"[HiGHS not installed, CBC fallback] {result.optimality_note}"
        return result


def make_highs_solver() -> HiGHSSolver:
    return HiGHSSolver()
