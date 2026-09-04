"""
Simulation & Market Data API
=============================
Real data + real simulation endpoints.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/sim", tags=["simulation"])


class SimConfig(BaseModel):
    n_paths: int = 500
    horizon_years: float = 10.0
    rate_model: str = "vasicek"
    rate_kappa: float = 0.15
    rate_theta: float = 0.04
    rate_sigma: float = 0.01
    fx_s0: float = 1.08
    fx_sigma: float = 0.08
    growth_mu: float = 0.025
    growth_sigma: float = 0.02


@router.get("/market-data/{country_code}")
def get_market_data(country_code: str):
    """Get real market data snapshot."""
    from app.market_data.real_providers import MarketDataEngine
    engine = MarketDataEngine()
    snapshot = engine.get_snapshot(country_code)

    result = {
        "country": country_code,
        "timestamp": snapshot["timestamp"],
        "providers": snapshot["providers_available"],
        "yield_curve": None,
        "fx_rates": {},
    }

    if snapshot["yield_curve"]:
        yc = snapshot["yield_curve"]
        result["yield_curve"] = {
            "source": yc.source,
            "date": yc.date,
            "points": [{"maturity": p.maturity_months, "rate": p.rate_pct} for p in yc.points],
            "two_ten_spread_bps": yc.two_ten_spread_bps,
        }

    for pair, rate in snapshot["fx_rates"].items():
        result["fx_rates"][pair] = {"rate": rate.rate, "date": rate.date, "source": rate.source}

    return result


@router.post("/monte-carlo")
def run_monte_carlo(config: SimConfig):
    """Run correlated Monte Carlo simulation."""
    from app.simulation.engine import MonteCarloEngine, SimulationConfig

    sim_config = SimulationConfig(
        n_paths=min(config.n_paths, 2000),
        n_steps=int(config.horizon_years * 252),
        rate_kappa=config.rate_kappa,
        rate_theta=config.rate_theta,
        rate_sigma=config.rate_sigma,
        rate_model=config.rate_model,
        fx_s0=config.fx_s0,
        fx_sigma=config.fx_sigma,
        growth_mu=config.growth_mu,
        growth_sigma=config.growth_sigma,
    )

    engine = MonteCarloEngine(sim_config)
    result = engine.simulate()

    # Downsample for chart (max 200 points)
    step = max(1, len(result.rate_p50) // 200)

    return {
        "config": {
            "n_paths": config.n_paths,
            "horizon_years": config.horizon_years,
            "rate_model": config.rate_model,
        },
        "rate": {
            "mean": result.rate_mean[::step],
            "p5": result.rate_p5[::step],
            "p25": result.rate_p25[::step],
            "p50": result.rate_p50[::step],
            "p75": result.rate_p75[::step],
            "p95": result.rate_p95[::step],
        },
        "fx": {
            "mean": result.fx_mean[::step],
            "p5": result.fx_p5[::step],
            "p95": result.fx_p95[::step],
        },
        "debt_to_gdp": {
            "median": result.debt_to_gdp_median[::step],
            "p5": result.debt_to_gdp_p5[::step],
            "p95": result.debt_to_gdp_p95[::step],
        },
        "points_per_series": len(result.rate_p50[::step]),
    }


@router.get("/backtest")
def run_backtest():
    """Run backtest validation against 2008 crisis."""
    from app.simulation.engine import BacktestValidator
    validator = BacktestValidator()
    return validator.validate_2008_crisis()


@router.get("/yield-curve-fit/{country_code}")
def get_fitted_curve(country_code: str):
    """Get NSS-fitted yield curve from real data."""
    from app.market_data.real_providers import MarketDataEngine
    from app.simulation.engine import fit_nss, nss_rate

    data_engine = MarketDataEngine()
    curve = data_engine.get_yield_curve(country_code)

    if not curve or len(curve.points) < 3:
        return {"error": "Insufficient data points for NSS fitting", "country": country_code}

    maturities = [p.maturity_months / 12.0 for p in curve.points]  # Convert to years
    rates = [p.rate_pct for p in curve.points]

    params = fit_nss(maturities, rates)

    # Generate fitted curve at regular intervals
    fitted_maturities = [0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 25, 30]
    fitted_points = []
    residuals = []
    for mat in fitted_maturities:
        fitted_rate = nss_rate(mat, params)
        fitted_points.append({"maturity_years": mat, "fitted_rate": round(fitted_rate, 4)})

    # Compute residuals at observed points
    for mat, actual in zip(maturities, rates):
        fitted = nss_rate(mat, params)
        residuals.append(round(abs(fitted - actual), 4))

    avg_residual = sum(residuals) / len(residuals) if residuals else 0

    return {
        "country": country_code,
        "source": curve.source,
        "n_observed": len(curve.points),
        "n_fitted": len(fitted_points),
        "nss_params": {
            "beta0": round(params.beta0, 4),
            "beta1": round(params.beta1, 4),
            "beta2": round(params.beta2, 4),
            "beta3": round(params.beta3, 4),
            "tau1": round(params.tau1, 4),
            "tau2": round(params.tau2, 4),
        },
        "fitted_points": fitted_points,
        "observed_points": [{"maturity_years": m, "rate": r} for m, r in zip(maturities, rates)],
        "avg_residual_bps": round(avg_residual * 100, 2),
        "goodness_of_fit": round(max(0, 1 - avg_residual / max(rates)), 4),
    }
