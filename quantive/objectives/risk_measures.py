"""Advanced risk measure objective functions.

Value-at-Risk (VaR), Conditional VaR (CVaR/Expected Shortfall),
Mean-Semivariance, and other risk measures for portfolio optimization.
"""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np


def value_at_risk(
    scenario_costs: np.ndarray,
    probabilities: Optional[np.ndarray] = None,
    confidence_level: float = 0.95,
) -> float:
    """Calculate Value-at-Risk (VaR) of a portfolio's cost distribution.

    VaR at confidence level α is the α-percentile of the cost distribution.
    Higher cost = worse outcome, so VaR is a worst-case cost threshold.

    Args:
        scenario_costs: Array of per-scenario total costs, shape (S,)
        probabilities: Scenario probabilities, shape (S,). Uniform if None.
        confidence_level: Percentile level (e.g., 0.95 for 95th percentile)

    Returns:
        The cost at the given confidence level
    """
    if scenario_costs.size == 0:
        return 0.0

    if probabilities is None:
        probabilities = np.ones_like(scenario_costs) / len(scenario_costs)

    # Sort costs and find the percentile
    sorted_indices = np.argsort(scenario_costs)
    sorted_costs = scenario_costs[sorted_indices]
    sorted_probs = probabilities[sorted_indices]

    cumulative = np.cumsum(sorted_probs)
    idx = np.searchsorted(cumulative, confidence_level)
    idx = min(idx, len(sorted_costs) - 1)

    return float(sorted_costs[idx])


def conditional_value_at_risk(
    scenario_costs: np.ndarray,
    probabilities: Optional[np.ndarray] = None,
    confidence_level: float = 0.95,
) -> float:
    """Calculate Conditional VaR (CVaR) / Expected Shortfall.

    CVaR is the expected cost conditional on the cost exceeding VaR.
    It provides a more coherent risk measure than VaR as it captures
    the severity of tail losses.

    Args:
        scenario_costs: Array of per-scenario total costs, shape (S,)
        probabilities: Scenario probabilities, shape (S,). Uniform if None.
        confidence_level: Confidence level (e.g., 0.95 for 95% CVaR)

    Returns:
        Expected cost in the worst (1-α) fraction of scenarios
    """
    if scenario_costs.size == 0:
        return 0.0

    if probabilities is None:
        probabilities = np.ones_like(scenario_costs) / len(scenario_costs)

    var = value_at_risk(scenario_costs, probabilities, confidence_level)

    # Scenarios where cost exceeds VaR
    tail_mask = scenario_costs >= var
    tail_probs = probabilities * tail_mask.astype(float)

    tail_sum = tail_probs.sum()
    if tail_sum <= 0:
        return var

    # CVaR = E[cost | cost >= VaR]
    cvar = float(np.dot(scenario_costs, tail_probs) / tail_sum)
    return cvar


def mean_semivariance(
    scenario_costs: np.ndarray,
    probabilities: Optional[np.ndarray] = None,
    target_cost: Optional[float] = None,
) -> float:
    """Calculate mean-semivariance (downside risk).

    Semivariance only penalizes costs that exceed a target, providing
    an asymmetric risk measure that focuses on the worst outcomes.

    Args:
        scenario_costs: Per-scenario costs, shape (S,)
        probabilities: Scenario probabilities
        target_cost: Target cost (mean if None)

    Returns:
        Mean-semivariance value
    """
    if scenario_costs.size == 0:
        return 0.0

    if probabilities is None:
        probabilities = np.ones_like(scenario_costs) / len(scenario_costs)

    if target_cost is None:
        target_cost = float(np.dot(scenario_costs, probabilities))

    downside = np.maximum(scenario_costs - target_cost, 0.0)
    return float(np.dot(downside ** 2, probabilities))


def mean_absolutedeviation(
    scenario_costs: np.ndarray,
    probabilities: Optional[np.ndarray] = None,
) -> float:
    """Mean absolute deviation from the expected cost."""
    if scenario_costs.size == 0:
        return 0.0
    if probabilities is None:
        probabilities = np.ones_like(scenario_costs) / len(scenario_costs)

    expected = float(np.dot(scenario_costs, probabilities))
    return float(np.dot(np.abs(scenario_costs - expected), probabilities))


def maximum_drawdown(
    scenario_costs: np.ndarray,
    probabilities: Optional[np.ndarray] = None,
) -> float:
    """Calculate maximum drawdown of cost distribution.

    In our context, this measures the maximum deterioration from
    the best-case scenario to any worse scenario.
    """
    if scenario_costs.size == 0:
        return 0.0

    best_case = float(np.min(scenario_costs))
    worst_case = float(np.max(scenario_costs))

    if best_case <= 0:
        return worst_case

    return (worst_case - best_case) / abs(best_case)


def cost_variance(
    scenario_costs: np.ndarray,
    probabilities: Optional[np.ndarray] = None,
) -> float:
    """Calculate variance of the cost distribution."""
    if scenario_costs.size == 0:
        return 0.0
    if probabilities is None:
        probabilities = np.ones_like(scenario_costs) / len(scenario_costs)

    expected = float(np.dot(scenario_costs, probabilities))
    return float(np.dot((scenario_costs - expected) ** 2, probabilities))


def cost_stddev(
    scenario_costs: np.ndarray,
    probabilities: Optional[np.ndarray] = None,
) -> float:
    """Standard deviation of the cost distribution."""
    return float(np.sqrt(cost_variance(scenario_costs, probabilities)))


def worst_case_cost(
    scenario_costs: np.ndarray,
) -> float:
    """Maximum cost across all scenarios (minimax)."""
    return float(np.max(scenario_costs)) if scenario_costs.size > 0 else 0.0


def best_case_cost(
    scenario_costs: np.ndarray,
) -> float:
    """Minimum cost across all scenarios."""
    return float(np.min(scenario_costs)) if scenario_costs.size > 0 else 0.0


def cost_percentiles(
    scenario_costs: np.ndarray,
    probabilities: Optional[np.ndarray] = None,
    percentiles: Tuple[float, ...] = (5, 25, 50, 75, 95),
) -> dict:
    """Calculate multiple percentiles of the cost distribution."""
    if scenario_costs.size == 0:
        return {str(p): 0.0 for p in percentiles}

    if probabilities is not None and not np.allclose(probabilities, probabilities[0]):
        # Weighted percentile calculation
        sorted_indices = np.argsort(scenario_costs)
        sorted_costs = scenario_costs[sorted_indices]
        sorted_probs = probabilities[sorted_indices]
        cumulative = np.cumsum(sorted_probs)

        result = {}
        for p in percentiles:
            target = p / 100.0
            idx = np.searchsorted(cumulative, target)
            idx = min(idx, len(sorted_costs) - 1)
            result[str(p)] = float(sorted_costs[idx])
        return result
    else:
        result = {}
        for p in percentiles:
            result[str(p)] = float(np.percentile(scenario_costs, p))
        return result


def coherent_risk_report(
    x: np.ndarray,
    cost_matrix: np.ndarray,
    probabilities: np.ndarray,
) -> dict:
    """Generate a comprehensive risk report for an allocation.

    Args:
        x: Allocation vector, shape (N,)
        cost_matrix: Scenario cost matrix, shape (N, S)
        probabilities: Scenario probabilities, shape (S,)

    Returns:
        Dictionary with all risk measures
    """
    costs = cost_matrix.T @ x  # shape (S,)

    return {
        "expected_cost": float(np.dot(costs, probabilities)),
        "var_95": value_at_risk(costs, probabilities, 0.95),
        "var_99": value_at_risk(costs, probabilities, 0.99),
        "cvar_95": conditional_value_at_risk(costs, probabilities, 0.95),
        "cvar_99": conditional_value_at_risk(costs, probabilities, 0.99),
        "mean_semivariance": mean_semivariance(costs, probabilities),
        "mean_absolute_deviation": mean_absolutedeviation(costs, probabilities),
        "variance": cost_variance(costs, probabilities),
        "std_dev": cost_stddev(costs, probabilities),
        "worst_case": worst_case_cost(costs),
        "best_case": best_case_cost(costs),
        "max_drawdown": maximum_drawdown(costs, probabilities),
        "percentiles": cost_percentiles(costs, probabilities),
    }
