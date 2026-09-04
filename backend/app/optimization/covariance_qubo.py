"""Covariance-Weighted QUBO — Risk-Aware Debt Optimization.

Extends the basic QUBO with covariance-aware risk terms:

    H(x) = sum_i c_i * x_i + alpha * sum_{i,j} Cov(i,j) * x_i * x_j + lambda * (sum_i x_i - B)^2

Where:
    c_i = cost vector (coupon + issuance + rollover costs)
    Cov(i,j) = yield curve covariance matrix element
    alpha = risk aversion parameter
    B = budget constraint (total issuance)
    x_i = binary allocation to maturity/rate bucket
"""

import math
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CovarianceQUBOProblem:
    """Covariance-weighted QUBO formulation."""
    Q: list[list[float]]  # NxN quadratic matrix
    c: list[float]        # Nx1 linear cost vector
    n_variables: int
    variable_map: dict
    risk_aversion: float
    budget: float
    metadata: dict = field(default_factory=dict)


MATURITY_BUCKETS = [0.25, 1, 2, 5, 7, 10, 15, 20, 30]
MATURITY_LABELS = ["3M", "1Y", "2Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"]
RATE_TYPES = ["fixed", "floating", "inflation"]
N_MATURITIES = len(MATURITY_BUCKETS)
N_RATE_TYPES = len(RATE_TYPES)
N_VARIABLES = N_MATURITIES * N_RATE_TYPES


def formulate_covariance_qubo(
    yield_rates: dict[str, float],
    covariance_matrix: list[list[float]],
    total_issuance: float,
    risk_aversion: float = 10.0,
    issuance_cost_bps: float = 5.0,
    rollover_cost_bps: float = 15.0,
    max_floating_pct: float = 0.30,
    max_short_term_pct: float = 0.40,
) -> CovarianceQUBOProblem:
    """Formulate QUBO with covariance-weighted risk terms.

    Args:
        yield_rates: Current yield curve {"3M": 0.042, "10Y": 0.040, ...}
        covariance_matrix: NxN covariance matrix of yield rate changes
        total_issuance: Total debt to issue
        risk_aversion: Weight on risk term (alpha)
        issuance_cost_bps: Issuance cost in basis points
        rollover_cost_bps: Rollover cost in basis points
        max_floating_pct: Maximum floating rate allocation
        max_short_term_pct: Maximum short-term allocation

    Returns:
        CovarianceQUBOProblem ready for quantum/classical solver
    """
    n = N_VARIABLES
    Q = [[0.0] * n for _ in range(n)]
    c = [0.0] * n

    # Build variable map
    var_map = {}
    idx = 0
    for i, mat_label in enumerate(MATURITY_LABELS):
        for j, rate_type in enumerate(RATE_TYPES):
            var_map[idx] = {
                "maturity_label": mat_label,
                "maturity_years": MATURITY_BUCKETS[i],
                "rate_type": rate_type,
            }
            idx += 1

    # ── Linear costs (c vector) ──────────────────────────────────────
    for k, info in var_map.items():
        mat_years = info["maturity_years"]
        rate_type = info["rate_type"]

        # Yield rate for this maturity
        yield_rate = _interpolate_yield(mat_years, yield_rates)

        # Base cost: coupon + issuance + rollover
        if rate_type == "fixed":
            base_cost = yield_rate + issuance_cost_bps / 10000
        elif rate_type == "floating":
            base_cost = yield_rate * 0.95 + issuance_cost_bps / 10000
        else:  # inflation
            base_cost = yield_rate * 0.9 + issuance_cost_bps / 10000 + 0.005

        rollover = rollover_cost_bps / 10000 * (1.0 / max(mat_years, 0.25))
        c[k] = base_cost + rollover * 0.1

    # ── Quadratic terms (Q matrix) ───────────────────────────────────

    # Term 1: Covariance-weighted risk (the key innovation)
    # Map maturity indices to covariance matrix indices
    cov_indices = _map_to_covariance_indices()

    for i in range(n):
        for j in range(n):
            ci = cov_indices.get(i, 0)
            cj = cov_indices.get(j, 0)

            # Scale covariance by risk aversion
            if ci < len(covariance_matrix) and cj < len(covariance_matrix[ci]):
                cov_term = covariance_matrix[ci][cj]
            else:
                cov_term = 0.0

            Q[i][j] += risk_aversion * cov_term

    # Term 2: Budget constraint penalty
    # (sum_i x_i - B)^2 = sum_i x_i^2 + 2*sum_{i<j} x_i*x_j - 2B*sum_i x_i + B^2
    # For binary x, x_i^2 = x_i, so:
    # = sum_i x_i + 2*sum_{i<j} x_i*x_j - 2B*sum_i x_i + B^2
    lambda_budget = 100.0  # Budget constraint penalty
    for i in range(n):
        c[i] += lambda_budget * (1 - 2 * total_issuance)
        for j in range(i + 1, n):
            Q[i][j] += 2 * lambda_budget

    # Term 3: Floating rate concentration penalty
    floating_penalty = 50.0
    floating_indices = [i * N_RATE_TYPES + 1 for i in range(N_MATURITIES)]
    for i, idx1 in enumerate(floating_indices):
        for idx2 in floating_indices[i + 1:]:
            Q[idx1][idx2] += floating_penalty

    # Term 4: Short-term concentration penalty
    short_penalty = 40.0
    short_indices = []
    for i, mat in enumerate(MATURITY_BUCKETS):
        if mat <= 3:
            for j in range(N_RATE_TYPES):
                short_indices.append(i * N_RATE_TYPES + j)
    for i, idx1 in enumerate(short_indices):
        for idx2 in short_indices[i + 1:]:
            Q[idx1][idx2] += short_penalty

    # Term 5: Diversification reward
    div_reward = -5.0
    for i in range(n):
        for j in range(i + 1, n):
            mat_i = MATURITY_BUCKETS[i // N_RATE_TYPES]
            mat_j = MATURITY_BUCKETS[j // N_RATE_TYPES]
            if abs(mat_i - mat_j) > 5:
                Q[i][j] += div_reward

    return CovarianceQUBOProblem(
        Q=Q, c=c, n_variables=n, variable_map=var_map,
        risk_aversion=risk_aversion, budget=total_issuance,
        metadata={
            "maturity_labels": MATURITY_LABELS,
            "rate_types": RATE_TYPES,
            "risk_aversion": risk_aversion,
            "budget": total_issuance,
        },
    )


def solve_covariance_qubo(problem: CovarianceQUBOProblem) -> dict:
    """Solve the QUBO using simulated annealing (classical)."""
    n = problem.n_variables
    best_x = [0] * n
    best_cost = float("inf")

    # Simulated annealing
    temperature = 1.0
    cooling = 0.995
    iterations = 10000

    current_x = [random.choice([0, 1]) for _ in range(n)]
    current_cost = _evaluate_qubo(current_x, problem)

    for _ in range(iterations):
        # Random flip
        flip_idx = random.randint(0, n - 1)
        current_x[flip_idx] = 1 - current_x[flip_idx]
        new_cost = _evaluate_qubo(current_x, problem)

        # Accept or reject
        delta = new_cost - current_cost
        if delta < 0 or random.random() < math.exp(-delta / max(temperature, 0.001)):
            current_cost = new_cost
        else:
            current_x[flip_idx] = 1 - current_x[flip_idx]  # Revert

        if current_cost < best_cost:
            best_cost = current_cost
            best_x = current_x[:]

        temperature *= cooling

    # Decode solution
    selected = []
    for k in range(n):
        if best_x[k] == 1:
            selected.append(problem.variable_map[k])

    return {
        "selected_options": selected,
        "n_selected": len(selected),
        "objective_value": round(best_cost, 6),
        "binary_solution": best_x,
    }


def _evaluate_qubo(x: list[int], problem: CovarianceQUBOProblem) -> float:
    """Evaluate H(x) = x^T Q x + c^T x."""
    n = problem.n_variables
    cost = 0.0
    for i in range(n):
        cost += problem.c[i] * x[i]
        for j in range(n):
            cost += x[i] * problem.Q[i][j] * x[j]
    return cost


def _interpolate_yield(maturity_years: float, yield_rates: dict[str, float]) -> float:
    """Interpolate yield rate for a given maturity."""
    sorted_rates = sorted(
        [(_label_to_years(label), rate) for label, rate in yield_rates.items()],
        key=lambda x: x[0],
    )
    if not sorted_rates:
        return 0.05
    if maturity_years <= sorted_rates[0][0]:
        return sorted_rates[0][1]
    if maturity_years >= sorted_rates[-1][0]:
        return sorted_rates[-1][1]
    for i in range(len(sorted_rates) - 1):
        x0, y0 = sorted_rates[i]
        x1, y1 = sorted_rates[i + 1]
        if x0 <= maturity_years <= x1:
            t = (maturity_years - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return sorted_rates[-1][1]


def _label_to_years(label: str) -> float:
    mapping = {"3M": 0.25, "6M": 0.5, "1Y": 1, "2Y": 2, "3Y": 3, "5Y": 5, "7Y": 7, "10Y": 10, "20Y": 20, "30Y": 30}
    return mapping.get(label, 5.0)


def _map_to_covariance_indices() -> dict[int, int]:
    """Map QUBO variable indices to covariance matrix indices."""
    mapping = {}
    for i in range(N_MATURITIES):
        for j in range(N_RATE_TYPES):
            qubo_idx = i * N_RATE_TYPES + j
            mapping[qubo_idx] = i  # Map to maturity bucket
    return mapping
