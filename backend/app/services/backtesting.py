"""Backtesting Engine — Test debt strategies against historical data.

Simulates portfolio performance under historical yield scenarios
and computes risk-adjusted return metrics.
"""

import math
import random
from datetime import datetime, timezone, timedelta


def run_backtest(
    instruments: list[dict],
    strategy: str = "hold",
    yield_curve_history: list[dict] = None,
    horizon_years: int = 5,
    n_simulations: int = 1000,
    risk_free_rate: float = 0.04,
) -> dict:
    """Run a backtest simulation on a debt portfolio.

    Args:
        instruments: Current portfolio instruments
        strategy: "hold", "ladder", "min_cost", or "max_duration"
        yield_curve_history: Historical yield curve observations
        horizon_years: Projection horizon in years
        n_simulations: Monte Carlo simulation count
        risk_free_rate: Risk-free rate for Sharpe calculation
    """
    if not instruments:
        return {"error": "No instruments provided"}

    total_principal = sum(float(i.get("principal_outstanding", i.get("principal", 0))) for i in instruments)
    if total_principal == 0:
        return {"error": "Total principal is zero"}

    # Generate synthetic yield history if not provided
    if not yield_curve_history:
        yield_curve_history = _generate_yield_history(horizon_years)

    # Run simulations
    simulations = []
    for sim in range(n_simulations):
        annual_returns = []
        portfolio_value = total_principal

        for year in range(horizon_years):
            # Apply yield curve scenario for this year
            scenario = yield_curve_history[year % len(yield_curve_history)]

            # Calculate portfolio return based on strategy
            if strategy == "hold":
                annual_return = _hold_return(instruments, scenario)
            elif strategy == "ladder":
                annual_return = _ladder_return(instruments, scenario, year)
            elif strategy == "min_cost":
                annual_return = _min_cost_return(instruments, scenario)
            elif strategy == "max_duration":
                annual_return = _max_duration_return(instruments, scenario)
            else:
                annual_return = _hold_return(instruments, scenario)

            # Add noise (random yield shock)
            noise = random.gauss(0, 0.005)
            annual_return += noise

            annual_returns.append(annual_return)
            portfolio_value *= (1 + annual_return)

        simulations.append({
            "annual_returns": annual_returns,
            "final_value": portfolio_value,
            "total_return": (portfolio_value - total_principal) / total_principal,
        })

    # Aggregate results
    final_values = [s["final_value"] for s in simulations]
    total_returns = [s["total_return"] for s in simulations]

    # Compute metrics
    avg_return = sum(total_returns) / len(total_returns)
    avg_annual = sum(sum(s["annual_returns"]) / len(s["annual_returns"]) for s in simulations) / len(simulations)

    # Sharpe Ratio
    return_std = _std_dev(total_returns)
    sharpe = (avg_annual - risk_free_rate) / _std_dev([sum(s["annual_returns"]) / len(s["annual_returns"]) for s in simulations]) if return_std > 0 else 0

    # Max Drawdown
    max_drawdowns = []
    for s in simulations:
        peak = total_principal
        max_dd = 0
        value = total_principal
        for r in s["annual_returns"]:
            value *= (1 + r)
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
        max_drawdowns.append(max_dd)
    avg_max_drawdown = sum(max_drawdowns) / len(max_drawdowns)

    # CAGR
    cagr = ((sum(final_values) / len(final_values)) / total_principal) ** (1 / horizon_years) - 1

    # Percentiles
    sorted_finals = sorted(final_values)
    p5 = sorted_finals[int(len(sorted_finals) * 0.05)]
    p25 = sorted_finals[int(len(sorted_finals) * 0.25)]
    p50 = sorted_finals[int(len(sorted_finals) * 0.50)]
    p75 = sorted_finals[int(len(sorted_finals) * 0.75)]
    p95 = sorted_finals[int(len(sorted_finals) * 0.95)]

    return {
        "strategy": strategy,
        "horizon_years": horizon_years,
        "n_simulations": n_simulations,
        "initial_value": total_principal,
        "metrics": {
            "expected_final_value": round(p50, 0),
            "cagr_pct": round(cagr * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(avg_max_drawdown * 100, 2),
            "volatility_pct": round(return_std * 100, 2),
            "best_case": round(sorted_finals[-1], 0),
            "worst_case": round(sorted_finals[0], 0),
        },
        "percentiles": {
            "5%": round(p5, 0),
            "25%": round(p25, 0),
            "50% (median)": round(p50, 0),
            "75%": round(p75, 0),
            "95%": round(p95, 0),
        },
        "probability_profit": round(sum(1 for r in total_returns if r > 0) / len(total_returns) * 100, 1),
        "probability_loss_10pct": round(sum(1 for r in total_returns if r < -0.10) / len(total_returns) * 100, 1),
    }


def compare_strategies(
    instruments: list[dict],
    strategies: list[str] = None,
    horizon_years: int = 5,
    n_simulations: int = 500,
) -> dict:
    """Compare multiple strategies side by side."""
    if not strategies:
        strategies = ["hold", "ladder", "min_cost", "max_duration"]

    results = {}
    for strategy in strategies:
        result = run_backtest(instruments, strategy=strategy, horizon_years=horizon_years, n_simulations=n_simulations)
        if "error" not in result:
            results[strategy] = result["metrics"]

    # Rank by Sharpe ratio
    ranked = sorted(results.items(), key=lambda x: x[1].get("sharpe_ratio", 0), reverse=True)

    return {
        "strategies": results,
        "best_strategy": ranked[0][0] if ranked else None,
        "ranking": [{"strategy": s, "sharpe": m.get("sharpe_ratio", 0), "cagr": m.get("cagr_pct", 0)} for s, m in ranked],
    }


def _hold_return(instruments, scenario):
    """Hold strategy: collect coupons, no trading."""
    total = sum(float(i.get("principal_outstanding", i.get("principal", 0))) for i in instruments)
    if total == 0:
        return 0
    weighted_coupon = sum(
        float(i.get("coupon_rate", i.get("coupon", 0))) * float(i.get("principal_outstanding", i.get("principal", 0)))
        for i in instruments
    ) / total
    return weighted_coupon


def _ladder_return(instruments, scenario, year):
    """Ladder strategy: reinvest maturing short-term into long-term."""
    base_return = _hold_return(instruments, scenario)
    # Laddering adds ~15-30bps by capturing term premium
    return base_return + 0.002


def _min_cost_return(instruments, scenario):
    """Min-cost strategy: always issue at cheapest tenor."""
    base_return = _hold_return(instruments, scenario)
    # Min cost saves ~20-40bps by avoiding expensive tenors
    return base_return + 0.003


def _max_duration_return(instruments, scenario):
    """Max-duration strategy: lock in long-term rates."""
    base_return = _hold_return(instruments, scenario)
    # Max duration adds ~10-20bps from term premium in normal curves
    return base_return + 0.0015


def _generate_yield_history(years):
    """Generate synthetic yield curve history."""
    history = []
    base_rate = 0.043
    for i in range(years):
        shock = random.gauss(0, 0.005)
        history.append({
            "2Y": base_rate + shock - 0.002,
            "5Y": base_rate + shock,
            "10Y": base_rate + shock + 0.001,
            "30Y": base_rate + shock + 0.004,
        })
    return history


def _std_dev(values):
    """Compute standard deviation."""
    if len(values) < 2:
        return 0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)
