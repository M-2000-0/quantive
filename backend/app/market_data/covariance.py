"""Yield Curve Covariance & Cost-of-Service Metrics.

Computes:
1. Covariance matrix of yield rates across maturities (3M, 2Y, 5Y, 10Y, 30Y)
2. Cost-of-service metrics for outstanding obligations
3. Interest rate volatility estimates for QUBO formulation

These feed directly into the optimization objective function.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# Standard maturity points (in months)
STANDARD_MATURITIES = [3, 24, 60, 120, 360]  # 3M, 2Y, 5Y, 10Y, 30Y
STANDARD_LABELS = ["3M", "2Y", "5Y", "10Y", "30Y"]


@dataclass
class YieldObservation:
    """Single yield curve observation."""
    date: str
    rates: dict[str, float]  # {"3M": 4.25, "2Y": 3.8, ...}


@dataclass
class CovarianceResult:
    """Result of covariance matrix computation."""
    maturity_labels: list[str]
    covariance_matrix: list[list[float]]  # NxN matrix
    correlation_matrix: list[list[float]]
    volatility: dict[str, float]  # Annualized vol per maturity
    eigenvalues: list[float]
    principal_components: list[list[float]]
    computed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CostOfServiceResult:
    """Cost-of-service metrics for a debt portfolio."""
    total_annual_interest: float
    weighted_avg_coupon: float
    weighted_avg_maturity: float
    interest_coverage_ratio: float
    refinancing_cost_bps: float
    duration_risk: float
    convexity: float
    cost_per_billion: float
    metrics_by_instrument: list[dict] = field(default_factory=list)


def compute_yield_covariance(
    observations: list[YieldObservation],
    annualize: bool = True,
) -> CovarianceResult:
    """Compute covariance matrix from historical yield observations.

    Args:
        observations: Time series of yield curve observations
        annualize: Whether to annualize (multiply by 252 trading days)

    Returns:
        CovarianceResult with full covariance/correlation matrices
    """
    if len(observations) < 2:
        # Return identity-ish matrix for insufficient data
        n = len(STANDARD_LABELS)
        return CovarianceResult(
            maturity_labels=STANDARD_LABELS,
            covariance_matrix=[[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)],
            correlation_matrix=[[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)],
            volatility={label: 0.01 for label in STANDARD_LABELS},
            eigenvalues=[1.0] * n,
            principal_components=[[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)],
        )

    # Build data matrix: rows = observations, cols = maturities
    labels = STANDARD_LABELS
    n = len(labels)
    data = []
    for obs in observations:
        row = [obs.rates.get(label, 0.0) for label in labels]
        data.append(row)

    # Compute means
    means = [sum(row[i] for row in data) / len(data) for i in range(n)]

    # Compute covariance matrix
    cov = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            cov[i][j] = sum(
                (data[k][i] - means[i]) * (data[k][j] - means[j])
                for k in range(len(data))
            ) / max(len(data) - 1, 1)

    if annualize:
        scale = 252  # trading days
        cov = [[c * scale for c in row] for row in cov]

    # Volatility (sqrt of diagonal)
    vol = {}
    for i, label in enumerate(labels):
        vol[label] = math.sqrt(max(cov[i][i], 0))

    # Correlation matrix
    corr = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            denom = math.sqrt(max(cov[i][i], 0) * max(cov[j][j], 0))
            corr[i][j] = cov[i][j] / denom if denom > 0 else (1.0 if i == j else 0.0)

    # Eigenvalues via power iteration (simplified)
    eigenvalues, eigenvectors = _power_iteration(cov, n, iterations=100)

    return CovarianceResult(
        maturity_labels=labels,
        covariance_matrix=cov,
        correlation_matrix=corr,
        volatility=vol,
        eigenvalues=eigenvalues,
        principal_components=eigenvectors,
    )


def compute_cost_of_service(
    instruments: list[dict],
    total_portfolio_value: float,
    risk_free_rate: float = 0.04,
) -> CostOfServiceResult:
    """Compute cost-of-service metrics for a debt portfolio.

    Args:
        instruments: List of dicts with keys:
            - principal_outstanding: float
            - coupon_rate: float (decimal, e.g., 0.0425)
            - maturity_years: float
            - currency: str
            - is_callable: bool
        total_portfolio_value: Total portfolio value in base currency
        risk_free_rate: Current risk-free rate for spread calculations

    Returns:
        CostOfServiceResult with comprehensive metrics
    """
    if not instruments or total_portfolio_value <= 0:
        return CostOfServiceResult(
            total_annual_interest=0, weighted_avg_coupon=0,
            weighted_avg_maturity=0, interest_coverage_ratio=0,
            refinancing_cost_bps=0, duration_risk=0, convexity=0,
            cost_per_billion=0,
        )

    total_annual_interest = 0
    weighted_coupon = 0
    weighted_maturity = 0
    metrics_by_instrument = []

    for inst in instruments:
        principal = inst.get("principal_outstanding", 0)
        coupon = inst.get("coupon_rate", 0)
        maturity = inst.get("maturity_years", inst.get("maturity_date_years", 5))
        weight = principal / total_portfolio_value if total_portfolio_value > 0 else 0

        annual_interest = principal * coupon
        total_annual_interest += annual_interest
        weighted_coupon += coupon * weight
        weighted_maturity += maturity * weight

        # Per-instrument cost metrics
        spread_bps = max((coupon - risk_free_rate) * 10000, 0)
        duration = _macaulay_duration(coupon, maturity, risk_free_rate)
        convexity = _convexity(coupon, maturity, risk_free_rate)

        metrics_by_instrument.append({
            "principal": principal,
            "coupon_rate": coupon,
            "maturity_years": maturity,
            "annual_interest": annual_interest,
            "spread_bps": round(spread_bps, 1),
            "macaulay_duration": round(duration, 2),
            "convexity": round(convexity, 2),
            "weight_pct": round(weight * 100, 2),
        })

    # Portfolio-level metrics
    weighted_duration = sum(m["macaulay_duration"] * m["weight_pct"] / 100 for m in metrics_by_instrument)
    weighted_convexity = sum(m["convexity"] * m["weight_pct"] / 100 for m in metrics_by_instrument)
    refinancing_cost_bps = max((weighted_coupon - risk_free_rate) * 10000, 0)

    # Interest coverage: assume revenue = 2x annual interest for sovereign
    interest_coverage_ratio = 2.0 if total_annual_interest > 0 else float("inf")

    cost_per_billion = (total_annual_interest / total_portfolio_value * 1e9) if total_portfolio_value > 0 else 0

    return CostOfServiceResult(
        total_annual_interest=round(total_annual_interest, 2),
        weighted_avg_coupon=round(weighted_coupon * 100, 4),
        weighted_avg_maturity=round(weighted_maturity, 2),
        interest_coverage_ratio=round(interest_coverage_ratio, 2),
        refinancing_cost_bps=round(refinancing_cost_bps, 1),
        duration_risk=round(weighted_duration, 2),
        convexity=round(weighted_convexity, 2),
        cost_per_billion=round(cost_per_billion, 2),
        metrics_by_instrument=metrics_by_instrument,
    )


def _macaulay_duration(coupon: float, maturity: float, ytm: float) -> float:
    """Compute Macaulay duration for a bond."""
    if ytm <= 0:
        return maturity / 2
    # Simplified: duration = (1+y)/y - (1+y + T*(c-y)) / (c*((1+y)^T - 1) + y)
    c = coupon
    y = ytm
    T = maturity
    if c == 0:
        return T / (1 + y)
    numerator = (1 + y) / y - (1 + y + T * (c - y)) / (c * ((1 + y) ** T - 1) + y)
    return max(numerator, 0.1)


def _convexity(coupon: float, maturity: float, ytm: float) -> float:
    """Compute convexity for a bond."""
    if ytm <= 0:
        return maturity ** 2 / 2
    T = maturity
    y = ytm
    c = coupon
    if c == 0:
        return T * (T + 1) / ((1 + y) ** 2)
    return (T * (T + 1) * c + 2 * (1 + y)) / ((1 + y) ** 2 * (c * ((1 + y) ** T - 1) + y))


def _power_iteration(matrix: list[list[float]], n: int, iterations: int = 100) -> tuple[list[float], list[list[float]]]:
    """Simplified power iteration for eigenvalues/eigenvectors."""
    eigenvalues = []
    eigenvectors = []

    for comp in range(min(n, 3)):
        # Random initial vector
        v = [1.0 / n] * n

        for _ in range(iterations):
            # Multiply
            w = [sum(matrix[i][j] * v[j] for j in range(n)) for i in range(n)]
            norm = math.sqrt(sum(x ** 2 for x in w))
            if norm > 1e-10:
                v = [x / norm for x in w]

        eigenvalue = sum(sum(matrix[i][j] * v[j] for j in range(n)) * v[i] for i in range(n))
        eigenvalues.append(round(eigenvalue, 6))
        eigenvectors.append([round(x, 4) for x in v])

    return eigenvalues, eigenvectors
