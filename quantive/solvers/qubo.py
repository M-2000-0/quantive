"""Quantum-inspired solver: QUBO-encoded annealing.

The continuous allocation is encoded as a binary expansion of each decision
variable, producing a QUBO-structured energy landscape. The energy is
minimised by simulated annealing over the binary bits — a quantum-inspired
algorithm family (also the classical routine used by QPUs). This pathway is
labelled QUANTUM_INSPIRED with backend SIMULATOR.

The *core* energy (weighted cost, interest-rate and FX risk, and the
debt-capacity equality as a quadratic penalty) is a genuine quadratic form in
the bits; ``to_qubo_matrix()`` returns the exact ``Q`` matrix for that core.
Peak-year refinancing risk is a max (piecewise-linear) term and one-sided bound
constraints are one-sided (hinge) quadratic penalties evaluated over the binary
encoding — the standard practical treatment in QUBO-based discrete
optimization.

No quantum performance is fabricated: results are produced on a classical CPU
simulator, never claimed to come from real quantum hardware, and never assumed
superior to the classical solvers.
"""
from __future__ import annotations

from time import perf_counter
from typing import Dict, List

import numpy as np

from quantive.models.enums import ExecutionBackend, SolverType
from quantive.models.optimization import SolverConfiguration
from quantive.objectives.spec import ProblemSpec
from quantive.solvers.base import SolveResult, SolverInterface, allocation_from_vector, build_result
from quantive.solvers.common import ladder_initial, project_box_simplex
from quantive.solvers.repair import repair_feasibility


def _hinge(v: float) -> float:
    return max(0.0, v)


class QUBOSolver(SolverInterface):
    name = "qubo_annealing"
    solver_type = SolverType.QUANTUM_INSPIRED
    execution_backend = ExecutionBackend.SIMULATOR

    def __init__(self):
        pass

    # -- encoding helpers ----------------------------------------------------
    @staticmethod
    def _steps(caps: np.ndarray, bits: int) -> np.ndarray:
        denom = 2 ** bits - 1
        return caps / denom

    # -- energy ---------------------------------------------------------------
    def _energy_from_aggregates(
        self,
        spec: ProblemSpec,
        lin: float,
        buckets: Dict[int, float],
        currencies: Dict[str, float],
        flt: float,
        liq: float,
        total: float,
        penalty_q: float,
    ) -> float:
        w_cost, w_refi, w_ir, w_fx = spec.weights
        R = spec.financing_requirement
        e = lin

        # canonical refinancing risk (peak-year maturing amount)
        e += w_refi * max(buckets.values(), default=0.0)

        # squared soft penalties (one-sided for bounds, two-sided for equality)
        d = total - R
        e += penalty_q * d * d
        if spec.floating_rate_limit_share is not None:
            v = _hinge(flt - spec.floating_rate_limit_share * R)
            e += penalty_q * v * v
        if spec.foreign_currency_limit_share is not None:
            foreign = sum(v for c, v in currencies.items() if c != spec.portfolio.reference_currency.value)
            v = _hinge(foreign - spec.foreign_currency_limit_share * R)
            e += penalty_q * v * v
        for ccy, cap in spec.per_currency_limits.items():
            v = _hinge(currencies.get(ccy, 0.0) - cap * R)
            e += penalty_q * v * v
        if spec.min_liquidity_share > 0:
            v = _hinge(spec.min_liquidity_share * R - liq)
            e += penalty_q * v * v
        for bucket, share in spec.target_maturity_share.items():
            v = _hinge(buckets.get(bucket, 0.0) - spec.refi_cap_share * R)
            e += penalty_q * v * v
            v = _hinge(buckets.get(bucket, 0.0) - spec.concentration_max_share * R)
            e += penalty_q * v * v
        return e

    @staticmethod
    def _penalty_q(spec: ProblemSpec) -> float:
        """Squared-penalty scale chosen so a ~1% violation dominates the objective."""
        R = spec.financing_requirement
        return max(1.0, spec.penalty * 100.0 / R)

    # -- QUBO matrix ------------------------------------------------------------
    def to_qubo_matrix(self, spec: ProblemSpec, config: SolverConfiguration) -> np.ndarray:
        """Exact dense Q matrix for the polynomial core of the energy.

        q is the flattened bit vector of length N*B; E(q) = q^T Q q (symmetric
        Q, binary q). Includes the weighted cost + interest-rate risk + FX risk
        (linear) plus the squared debt-capacity penalty (quadratic). The
        peak-year refinancing-risk term is a max (piecewise-linear) term and is
        therefore not part of this quadratic core — the annealer evaluates it
        directly from the bucket aggregates. One-sided bound penalties are also
        hinge terms evaluated by the annealer, not in this matrix.
        """
        B = config.qubo_bits
        N = spec.n_instruments
        nb = N * B
        Q = np.zeros((nb, nb))
        R = spec.financing_requirement
        w_cost, _w_refi, _w_ir, _w_fx = spec.weights
        steps = self._steps(spec.capacity, B)
        cost_coeff = spec.cost_matrix @ spec.probabilities
        lin_coeff = w_cost * cost_coeff + _w_ir * spec.ir_risk + _w_fx * spec.fx_risk

        # per-bit coefficients: bit (i, b) -> coefficient on q
        coef = np.zeros(nb)
        for i in range(N):
            for b in range(B):
                coef[i * B + b] = steps[i] * (2 ** b)

        # linear terms (diagonal, q^2 == q for binary)
        Q += np.diag(coef * lin_coeff.repeat(B))

        # quadratic expansion of the debt-capacity penalty:
        #   penalty * (sum(coef_j q_j) - R)^2
        terms: List[tuple[float, float, np.ndarray]] = [
            (spec.penalty, R, np.arange(nb)),
        ]

        for weight, target, idx in terms:
            c = coef[idx]
            # linear: c_j^2 - 2*target*c_j
            Q[idx, idx] += weight * (c * c - 2.0 * target * c)
            # quadratic pairs: 2*c_j*c_k q_j q_k  ->  Q[j,k]=Q[k,j]=c_j*c_k
            outer = np.outer(c, c)
            Q[np.ix_(idx, idx)] += weight * outer
            # the outer product also lands c_j^2 on the diagonal; remove the
            # double count (the c_j^2 linear term is already accounted above)
            Q[idx, idx] -= weight * c * c
        return Q

    # -- main solve ------------------------------------------------------------
    def solve(self, spec: ProblemSpec, config: SolverConfiguration) -> SolveResult:
        t0 = perf_counter()
        rng = np.random.default_rng(config.seed)
        B = config.qubo_bits
        N = spec.n_instruments
        R = spec.financing_requirement
        caps = spec.capacity
        steps = self._steps(caps, B)
        maxq = 2 ** B - 1

        # initial ladder allocation, encoded to bits
        x0 = ladder_initial(spec)
        q_ints = np.clip(np.round(x0 / steps), 0, maxq).astype(int)
        x = q_ints.astype(float) * steps

        # aggregates
        total = float(x.sum())
        buckets: Dict[int, float] = {}
        currencies: Dict[str, float] = {}
        flt = 0.0
        liq = 0.0
        w_cost, _w_refi, w_ir, w_fx = spec.weights
        cost_coeff = spec.cost_matrix @ spec.probabilities
        lin = float(np.dot(x, w_cost * cost_coeff + w_ir * spec.ir_risk + w_fx * spec.fx_risk))
        for i in range(N):
            b = int(spec.year_bucket[i])
            buckets[b] = buckets.get(b, 0.0) + x[i]
            ccy = spec.currencies[i]
            currencies[ccy] = currencies.get(ccy, 0.0) + x[i]
            if spec.is_floating[i]:
                flt += x[i]
            if spec.is_liquid[i]:
                liq += x[i]

        def energy_cur() -> float:
            return self._energy_from_aggregates(spec, lin, buckets, currencies, flt, liq, total, penalty_q)

        penalty_q = self._penalty_q(spec)
        best_x = x.copy()
        best_e = energy_cur()
        cur_e = best_e
        temp = config.annealing_initial_temp
        cooling = config.annealing_cooling_rate
        evals = 0

        for it in range(config.anneal_iterations):
            i = int(rng.integers(0, N))
            b = int(rng.integers(0, B))
            delta = steps[i] * (2 ** b)
            sign = 1 if q_ints[i] + (2 ** b) <= maxq else -1
            if rng.random() < 0.5 and q_ints[i] - (2 ** b) >= 0:
                sign = -1
            if sign > 0 and q_ints[i] + (2 ** b) > maxq:
                continue
            if sign < 0 and q_ints[i] - (2 ** b) < 0:
                continue
            d = sign * delta

            # apply candidate move
            x[i] += d
            q_ints[i] += int(sign * (2 ** b))
            total += d
            bucket = int(spec.year_bucket[i])
            buckets[bucket] = buckets.get(bucket, 0.0) + d
            ccy = spec.currencies[i]
            currencies[ccy] = currencies.get(ccy, 0.0) + d
            if spec.is_floating[i]:
                flt += d
            if spec.is_liquid[i]:
                liq += d
            lin += d * (w_cost * cost_coeff[i] + w_ir * spec.ir_risk[i] + w_fx * spec.fx_risk[i])

            new_e = self._energy_from_aggregates(spec, lin, buckets, currencies, flt, liq, total, penalty_q)
            evals += 1
            accept = new_e <= cur_e or rng.random() < np.exp((cur_e - new_e) / max(temp, 1e-12))
            if accept:
                cur_e = new_e
                if new_e < best_e:
                    best_x = x.copy()
                    best_e = new_e
            else:
                # revert
                x[i] -= d
                q_ints[i] -= int(sign * (2 ** b))
                total -= d
                buckets[bucket] = buckets.get(bucket, 0.0) - d
                currencies[ccy] = currencies.get(ccy, 0.0) - d
                if spec.is_floating[i]:
                    flt -= d
                if spec.is_liquid[i]:
                    liq -= d
                lin -= d * (w_cost * cost_coeff[i] + w_ir * spec.ir_risk[i] + w_fx * spec.fx_risk[i])
            temp *= cooling
            if temp < 1e-6:
                temp = 1e-6

        runtime = perf_counter() - t0
        # repair: project to box-simplex and deterministically restore feasibility
        best_x = repair_feasibility(spec, project_box_simplex(best_x, caps, R))
        alloc = allocation_from_vector(spec, best_x)
        return build_result(
            spec, alloc, self.name, self.solver_type, self.execution_backend,
            runtime, iterations=config.anneal_iterations, objective_evaluations=evals,
            optimality_note=(
                "quantum-inspired annealing on a classical simulator with "
                "deterministic classical repair; no global optimality guarantee"
            ),
            metadata={
                "encoding": "binary_expansion",
                "bits_per_variable": B,
                "bit_count": N * B,
                "energy": "QUBO-structured (see docs/solver-interface.md)",
                "execution": "SIMULATOR (classical CPU)",
                "post_processing": "classical feasibility repair",
            },
        )


def make_qubo_solver() -> QUBOSolver:
    return QUBOSolver()