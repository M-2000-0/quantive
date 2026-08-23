"""Heuristic solver: simulated annealing with a box-simplex projection.

Works directly on the continuous allocation vector. Constraints enter as
penalty terms (soft constraints); the algorithm searches for low-cost,
near-feasible allocations. The reported objective and feasibility are always
evaluated canonically against the same ``ProblemSpec`` used by the other
solvers.
"""
from __future__ import annotations

from time import perf_counter

import numpy as np

from quantive.models.enums import ExecutionBackend, SolverType
from quantive.models.optimization import SolverConfiguration
from quantive.objectives.spec import ProblemSpec
from quantive.solvers.base import SolveResult, SolverInterface, allocation_from_vector, build_result
from quantive.solvers.common import ladder_initial, project_box_simplex
from quantive.solvers.repair import repair_feasibility


class SimulatedAnnealingSolver(SolverInterface):
    name = "simulated_annealing"
    solver_type = SolverType.HEURISTIC
    execution_backend = ExecutionBackend.CLASSICAL_CPU

    def __init__(self):
        pass

    def _energy(self, spec: ProblemSpec, x: np.ndarray) -> float:
        """Objective + penalty for constraint violations."""
        obj = spec.objective_value(x)
        viol = spec.violation_magnitude(x)
        return obj + spec.penalty * viol

    def _initial(self, spec: ProblemSpec) -> np.ndarray:
        return ladder_initial(spec)

    def solve(self, spec: ProblemSpec, config: SolverConfiguration) -> SolveResult:
        t0 = perf_counter()
        rng = np.random.default_rng(config.seed)
        caps = spec.capacity
        N = spec.n_instruments
        R = spec.financing_requirement

        x = self._initial(spec)
        best_x = x.copy()
        best_e = self._energy(spec, x)
        cur_e = best_e
        temp = config.annealing_initial_temp
        cooling = config.annealing_cooling_rate
        evals = 0

        sigma = max(50.0, R / 40.0)
        for it in range(config.anneal_iterations):
            # exact-sum pairwise move (preserves sum(x) == R by construction)
            i = int(rng.integers(0, N))
            j = int(rng.integers(0, N - 1))
            if j >= i:
                j += 1
            delta = float(rng.normal(0.0, sigma * (0.4 + temp)))

            old_i, old_j = x[i], x[j]
            xi_new = min(max(old_i + delta, 0.0), caps[i])
            used = xi_new - old_i
            xj_new = min(max(old_j - used, 0.0), caps[j])
            x[i], x[j] = xi_new, xj_new

            # repair any clamping residue (keeps the allocation box-feasible)
            residue = (xi_new + xj_new) - (old_i + old_j)
            if residue > 1e-9:
                take = min(residue, caps[i] - x[i])
                x[i] += take
                if residue - take > 1e-9:
                    x[j] += min(residue - take, caps[j] - x[j])
            elif residue < -1e-9:
                take = min(-residue, x[i])
                x[i] -= take
                if -residue - take > 1e-9:
                    x[j] -= min(-residue - take, x[j])

            new_e = self._energy(spec, x)
            evals += 1
            if new_e <= cur_e or rng.random() < np.exp((cur_e - new_e) / max(temp, 1e-12)):
                cur_e = new_e
                if new_e < best_e:
                    best_x = x.copy()
                    best_e = new_e
            else:
                x[i], x[j] = old_i, old_j
            temp *= cooling
            if temp < 1e-6:
                temp = 1e-6

        runtime = perf_counter() - t0
        # polish: project best onto feasible box-simplex, then deterministic repair
        best_x = repair_feasibility(spec, project_box_simplex(best_x, caps, R))
        alloc = allocation_from_vector(spec, best_x)
        return build_result(
            spec, alloc, self.name, self.solver_type, self.execution_backend,
            runtime, iterations=config.anneal_iterations, objective_evaluations=evals,
            optimality_note="heuristic: no global optimality guarantee; repaired to feasibility",
            metadata={"final_temperature": temp},
        )


def make_annealing_solver() -> SimulatedAnnealingSolver:
    return SimulatedAnnealingSolver()