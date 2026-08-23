"""Classical MILP solver built on PuLP + CBC.

The linear formulation is documented in ``docs/optimization-model.md``. CBC
establishes global optimality for linear programs; when integer variables
(cardinality, minimum bucket concentration) are present, CBC proves optimality
with branch-and-bound or reports the best bound.
"""
from __future__ import annotations

from time import perf_counter

import pulp

from quantive.models.enums import ExecutionBackend, SolverType
from quantive.models.optimization import SolverConfiguration
from quantive.objectives.spec import ProblemSpec
from quantive.solvers.base import SolveResult, SolverInterface, build_result


class MILPSolver(SolverInterface):
    name = "milp_cbc"
    solver_type = SolverType.CLASSICAL
    execution_backend = ExecutionBackend.CLASSICAL_CPU

    def solve(self, spec: ProblemSpec, config: SolverConfiguration) -> SolveResult:
        t0 = perf_counter()
        N = spec.n_instruments
        R = spec.financing_requirement
        w_cost, w_refi, w_ir, w_fx = spec.weights

        model = pulp.LpProblem("quantive_debt", pulp.LpMinimize)
        x = {
            i: pulp.LpVariable(f"x_{i}", lowBound=0, upBound=float(spec.capacity[i]))
            for i in range(N)
        }

        # --- objective terms ------------------------------------------------
        terms = []
        if spec.robust:
            z = pulp.LpVariable("worst_case_cost", lowBound=0)
            for s in range(spec.n_scenarios):
                model += (
                    pulp.lpSum(spec.cost_matrix[i, s] * x[i] for i in range(N)) <= z,
                    f"robust_s{s}",
                )
            terms.append(w_cost * z)
        else:
            cost_coeff = spec.cost_matrix @ spec.probabilities  # (I,) expected cost per unit
            terms.append(w_cost * pulp.lpSum(cost_coeff[i] * x[i] for i in range(N)))

        terms.append(w_ir * pulp.lpSum(float(spec.ir_risk[i]) * x[i] for i in range(N)))
        terms.append(w_fx * pulp.lpSum(float(spec.fx_risk[i]) * x[i] for i in range(N)))

        # refinancing risk: peak-year maturing amount (epigraph)
        peak = pulp.LpVariable("peak_maturity", lowBound=0)
        for bucket in set(int(b) for b in spec.year_bucket):
            expr = pulp.lpSum(x[i] for i in range(N) if spec.year_bucket[i] == bucket)
            model += expr <= peak, f"peak_y{bucket}"
        terms.append(w_refi * peak)

        model += pulp.lpSum(terms)

        # --- constraints ------------------------------------------------------
        model += pulp.lpSum(x[i] for i in range(N)) == R, "debt_capacity"

        # refinancing / concentration caps per bucket
        for bucket in set(int(b) for b in spec.year_bucket):
            idx = [i for i in range(N) if spec.year_bucket[i] == bucket]
            model += pulp.lpSum(x[i] for i in idx) <= spec.refi_cap_share * R, f"refi_cap_y{bucket}"
            model += pulp.lpSum(x[i] for i in idx) <= spec.concentration_max_share * R, f"conc_max_y{bucket}"

        # minimum maturity concentration (if set): active buckets >= min share
        if spec.concentration_min_share > 0:
            min_val = spec.concentration_min_share * R
            for bucket in set(int(b) for b in spec.year_bucket):
                y = pulp.LpVariable(f"y_active_{bucket}", cat="Binary")
                idx = [i for i in range(N) if spec.year_bucket[i] == bucket]
                expr = pulp.lpSum(x[i] for i in idx)
                model += expr >= min_val * y, f"conc_min_lo_y{bucket}"
                model += expr <= R * y, f"conc_min_hi_y{bucket}"

        # floating-rate limit
        if spec.floating_rate_limit_share is not None:
            idx = [i for i in range(N) if spec.is_floating[i]]
            model += pulp.lpSum(x[i] for i in idx) <= spec.floating_rate_limit_share * R, "floating_limit"

        # currency limits
        if spec.foreign_currency_limit_share is not None:
            idx = [i for i in range(N) if spec.is_foreign[i]]
            model += pulp.lpSum(x[i] for i in idx) <= spec.foreign_currency_limit_share * R, "foreign_currency_limit"
        for ccy, cap_share in spec.per_currency_limits.items():
            idx = [i for i in range(N) if spec.currencies[i] == ccy]
            model += pulp.lpSum(x[i] for i in idx) <= cap_share * R, f"currency_limit_{ccy}"

        # minimum liquidity
        if spec.min_liquidity_share > 0:
            idx = [i for i in range(N) if spec.is_liquid[i]]
            model += pulp.lpSum(x[i] for i in idx) >= spec.min_liquidity_share * R, "min_liquidity"

        # cardinality cap
        if spec.max_instruments is not None:
            y = {i: pulp.LpVariable(f"y_{i}", cat="Binary") for i in range(N)}
            for i in range(N):
                model += x[i] <= float(spec.capacity[i]) * y[i], f"card_hi_{i}"
            model += pulp.lpSum(y[i] for i in range(N)) <= spec.max_instruments, "max_instruments"

        # custom linear constraints
        for k, cst in enumerate(spec.custom_constraints):
            expr = pulp.LpAffineExpression()
            for iid, coeff in cst.get("weights", {}).items():
                if iid in spec.instrument_ids:
                    expr += coeff * x[spec.instrument_ids.index(iid)]
            limit = cst.get("limit")
            if limit is not None:
                model += expr <= limit, f"custom_{k}"

        solver = pulp.PULP_CBC_CMD(timeLimit=max(1, int(config.time_limit_seconds)), msg=False)
        model.solve(solver)

        status = pulp.LpStatus[model.status]
        runtime = perf_counter() - t0
        iterations = model.solverModel and getattr(model.solverModel, "num_iterations", None)

        if status in ("Optimal", "Feasible") and any(x[i].value() is not None for i in range(N)):
            alloc = {spec.instrument_ids[i]: max(0.0, float(x[i].value())) for i in range(N)}
            if status == "Optimal":
                note = "globally optimal (CBC proved optimality)"
            else:
                note = "feasible solution found; optimality not proven (time limit reached)"
            return build_result(
                spec, alloc, self.name, self.solver_type, self.execution_backend,
                runtime, iterations=iterations, optimality_note=note,
                metadata={"status": status, "model_status": model.status},
            )

        # Infeasible or unstarted: return empty allocation
        alloc = {spec.instrument_ids[i]: 0.0 for i in range(N)}
        return build_result(
            spec, alloc, self.name, self.solver_type, self.execution_backend,
            runtime, optimality_note=f"INFEASIBLE (status={status})",
            metadata={"status": status, "model_status": model.status},
        )


def make_milp_solver() -> MILPSolver:
    return MILPSolver()