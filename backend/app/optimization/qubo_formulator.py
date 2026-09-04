"""QUBO Matrix Formulation for Public Debt Optimization.

Maps the debt structure (bond issuance splits across fixed/floating rates
and maturities) into a Quadratic Unconstrained Binary Optimization format:

    H(x) = x^T Q x + c^T x

Where:
    x = binary decision variables (which bonds to issue/retain)
    Q = quadratic interaction matrix (encodes pairwise constraints)
    c = linear cost vector (encodes individual bond costs)

Decision Variables:
    For each bond option (i, j) where i = maturity bucket, j = rate type:
    x_{i,j} = 1 if we issue/retain this bond, 0 otherwise

Maturity Buckets: [3M, 1Y, 2Y, 5Y, 7Y, 10Y, 15Y, 20Y, 30Y]
Rate Types: [Fixed, Floating, Inflation-Linked]
Total variables: 9 × 3 = 27 binary variables (manageable for QAOA)
"""

import math
from dataclasses import dataclass, field
from typing import Optional


# Maturity buckets in years
MATURITY_BUCKETS = [0.25, 1, 2, 5, 7, 10, 15, 20, 30]
MATURITY_LABELS = ["3M", "1Y", "2Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"]

# Rate types
RATE_TYPES = ["fixed", "floating", "inflation"]
N_MATURITIES = len(MATURITY_BUCKETS)
N_RATE_TYPES = len(RATE_TYPES)
N_VARIABLES = N_MATURITIES * N_RATE_TYPES


@dataclass
class QUBOProblem:
    """QUBO formulation for debt optimization."""
    Q: list[list[float]]  # NxN quadratic matrix
    c: list[float]        # Nx1 linear cost vector
    n_variables: int
    variable_map: dict    # Maps index to (maturity_label, rate_type)
    metadata: dict = field(default_factory=dict)


@dataclass
class DebtParameters:
    """Input parameters for QUBO formulation."""
    # Current portfolio
    current_allocations: list[dict]  # [{maturity_years, rate_type, coupon_rate, principal}]
    total_target_issuance: float     # Total new issuance target

    # Yield curve inputs
    yield_rates: dict[str, float]    # {"3M": 4.25, "1Y": 4.1, ...}
    swap_rates: dict[str, float]     # {"5Y": 3.9, "10Y": 4.0, ...}

    # Risk parameters
    max_single_maturity_pct: float = 25.0   # Max % in any single maturity
    max_floating_pct: float = 30.0          # Max % floating rate
    max_3yr_concentration_pct: float = 40.0 # Max % maturing within 3 years
    target_avg_maturity_years: float = 7.0  # Target weighted avg maturity
    min_diversification_score: float = 0.3  # Min Shannon entropy

    # Cost parameters
    issuance_cost_bps: float = 5.0          # Issuance cost in basis points
    rollover_cost_bps: float = 15.0         # Rollover/refinancing cost
    fx_hedge_cost_bps: float = 25.0         # FX hedging cost if foreign


def formulate_qubo(params: DebtParameters) -> QUBOProblem:
    """Construct the QUBO matrix from debt parameters.

    The objective function H(x) = x^T Q x + c^T x minimizes:
    1. Total interest cost (coupon payments)
    2. Refinancing risk (rollover concentration)
    3. Rate-type risk (floating rate exposure)
    4. Maturity concentration risk

    Subject to implicit constraints via penalty terms:
    - Sum of allocations = 1 (portfolio constraint)
    - Max concentration per maturity (penalty in Q)
    - Max floating rate share (penalty in Q)
    """
    n = N_VARIABLES
    Q = [[0.0] * n for _ in range(n)]
    c = [0.0] * n

    # Build variable map
    var_map = {}
    idx = 0
    for i, mat_label in enumerate(MATURITY_LABELS):
        for j, rate_type in enumerate(RATE_TYPES):
            var_map[idx] = {"maturity_label": mat_label, "maturity_years": MATURITY_BUCKETS[i], "rate_type": rate_type, "index": idx}
            idx += 1

    # ── Linear costs (c vector) ────────────────────────────────────────
    for k, info in var_map.items():
        mat_years = info["maturity_years"]
        rate_type = info["rate_type"]

        # Get yield rate for this maturity
        yield_rate = _get_yield_rate(mat_years, params.yield_rates)

        # Base cost: coupon rate + issuance cost
        if rate_type == "fixed":
            base_cost = yield_rate + params.issuance_cost_bps / 10000
        elif rate_type == "floating":
            base_cost = yield_rate * 0.95 + params.issuance_cost_bps / 10000  # Floating typically lower initially
        else:  # inflation
            base_cost = yield_rate * 0.9 + params.issuance_cost_bps / 10000 + 0.005  # IL spread

        # Rollover risk: shorter maturity = more frequent rollover
        rollover = params.rollover_cost_bps / 10000 * (1.0 / max(mat_years, 0.25))
        c[k] = base_cost + rollover * 0.1  # Small weight on rollover

    # ── Quadratic terms (Q matrix) ─────────────────────────────────────

    # Penalty 1: Maturity concentration (penalize large allocations to same bucket)
    concentration_penalty = 50.0  # High penalty
    for i in range(N_MATURITIES):
        for j in range(N_RATE_TYPES):
            idx1 = i * N_RATE_TYPES + j
            for j2 in range(N_RATE_TYPES):
                idx2 = i * N_RATE_TYPES + j2
                if idx1 != idx2:
                    Q[idx1][idx2] += concentration_penalty

    # Penalty 2: Floating rate concentration
    floating_penalty = 30.0
    floating_indices = [i * N_RATE_TYPES + 1 for i in range(N_MATURITIES)]
    for i, idx1 in enumerate(floating_indices):
        for idx2 in floating_indices[i + 1:]:
            Q[idx1][idx2] += floating_penalty

    # Penalty 3: Short-term concentration (maturities < 3 years)
    short_term_penalty = 40.0
    short_indices = []
    for i, mat in enumerate(MATURITY_BUCKETS):
        if mat <= 3:
            for j in range(N_RATE_TYPES):
                short_indices.append(i * N_RATE_TYPES + j)
    for i, idx1 in enumerate(short_indices):
        for idx2 in short_indices[i + 1:]:
            Q[idx1][idx2] += short_term_penalty

    # Penalty 4: Diversification bonus (reward spreading across maturities)
    diversification_bonus = -5.0  # Negative = reward
    all_indices = list(range(n))
    for i, idx1 in enumerate(all_indices):
        for idx2 in all_indices[i + 1:]:
            mat1 = var_map[idx1]["maturity_years"]
            mat2 = var_map[idx2]["maturity_years"]
            if abs(mat1 - mat2) > 5:  # Different maturity buckets
                Q[idx1][idx2] += diversification_bonus

    # Penalty 5: Portfolio balance constraint (sum of x should be ~1)
    balance_penalty = 100.0
    for i in range(n):
        for j in range(n):
            if i != j:
                Q[i][j] += balance_penalty
    for i in range(n):
        c[i] -= balance_penalty  # Offset to make sum=1 the minimum

    return QUBOProblem(
        Q=Q,
        c=c,
        n_variables=n,
        variable_map=var_map,
        metadata={
            "maturity_buckets": MATURITY_LABELS,
            "rate_types": RATE_TYPES,
            "penalties": {
                "concentration": concentration_penalty,
                "floating": floating_penalty,
                "short_term": short_term_penalty,
                "diversification": diversification_bonus,
                "balance": balance_penalty,
            },
        },
    )


def decode_solution(x: list[int], problem: QUBOProblem, total_issuance: float) -> dict:
    """Decode binary QUBO solution into actionable debt issuance plan.

    Args:
        x: Binary vector (0 or 1) from QAOA/VQE measurement
        problem: The QUBO problem formulation
        total_issuance: Total amount to issue

    Returns:
        Structured issuance plan with amounts, risks, and recommendations
    """
    selected = []
    for k in range(problem.n_variables):
        if x[k] == 1:
            info = problem.variable_map[k]
            selected.append(info)

    if not selected:
        return {"error": "No bonds selected", "allocations": []}

    # Equal-weight allocation among selected options
    weight_per = 1.0 / len(selected)

    allocations = []
    for info in selected:
        amount = total_issuance * weight_per
        yield_rate = info["maturity_years"]  # Use as proxy
        allocations.append({
            "maturity_label": info["maturity_label"],
            "maturity_years": info["maturity_years"],
            "rate_type": info["rate_type"],
            "amount": round(amount, 0),
            "weight_pct": round(weight_per * 100, 1),
        })

    # Compute portfolio metrics
    total_weight = sum(a["weight_pct"] for a in allocations)
    floating_pct = sum(a["weight_pct"] for a in allocations if a["rate_type"] == "floating")
    short_term_pct = sum(a["weight_pct"] for a in allocations if a["maturity_years"] <= 3)
    avg_maturity = sum(a["maturity_years"] * a["weight_pct"] / total_weight for a in allocations)

    return {
        "allocations": allocations,
        "portfolio_metrics": {
            "num_options_selected": len(selected),
            "floating_rate_pct": round(floating_pct, 1),
            "short_term_pct": round(short_term_pct, 1),
            "weighted_avg_maturity_years": round(avg_maturity, 2),
        },
        "total_issuance": total_issuance,
    }


def evaluate_cost(x: list[int], problem: QUBOProblem) -> float:
    """Evaluate the QUBO cost function H(x) = x^T Q x + c^T x."""
    n = problem.n_variables
    cost = 0.0

    # Linear term: c^T x
    for i in range(n):
        cost += problem.c[i] * x[i]

    # Quadratic term: x^T Q x
    for i in range(n):
        for j in range(n):
            cost += x[i] * problem.Q[i][j] * x[j]

    return cost


def generate_sample_x(problem: QUBOProblem, selection_rate: float = 0.3) -> list[int]:
    """Generate a random binary solution vector for testing."""
    import random
    return [1 if random.random() < selection_rate else 0 for _ in range(problem.n_variables)]


def _get_yield_rate(maturity_years: float, yield_rates: dict[str, float]) -> float:
    """Look up yield rate for a given maturity, with interpolation."""
    # Try exact match first
    for label, rate in yield_rates.items():
        if _label_to_years(label) == maturity_years:
            return rate

    # Linear interpolation
    sorted_rates = sorted(
        [(_label_to_years(label), rate) for label, rate in yield_rates.items()],
        key=lambda x: x[0],
    )

    if not sorted_rates:
        return 0.05  # Default 5%

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
    """Convert maturity label to years."""
    label = label.upper().strip()
    mapping = {
        "3M": 0.25, "6M": 0.5, "1Y": 1, "2Y": 2, "3Y": 3,
        "5Y": 5, "7Y": 7, "10Y": 10, "15Y": 15, "20Y": 20, "30Y": 30,
    }
    return mapping.get(label, 5.0)
