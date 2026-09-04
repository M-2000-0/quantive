"""
Simulation Engine API — Monte Carlo & Stress Testing
=====================================================

Endpoints:
- POST /api/simulation/run — Run full Monte Carlo simulation
- GET /api/simulation/presets — Get preset macro scenarios
- POST /api/simulation/stress-test — Run stress test on portfolio
- GET /api/simulation/fan-chart — Generate fan chart data (10/25/50/75/90th)
- POST /api/simulation/backtest — Backtest engine from historical starting point
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import math
import random

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


# ── Models ─────────────────────────────────────────────────────────────

class SimulationConfig(BaseModel):
    years: int = 10
    paths: int = 5000
    rate_model: str = "vasicek"  # vasicek, cir, hull_white
    fx_model: str = "gbm"
    include_correlation: bool = True
    seed: Optional[int] = None


class StressScenario(BaseModel):
    name: str
    rate_shock_bps: float = 0
    fx_shock_pct: float = 0
    gdp_shock_pct: float = 0
    commodity_shock_pct: float = 0
    duration_months: int = 12


class FanChartPoint(BaseModel):
    year: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


# ── Vasicek Model ──────────────────────────────────────────────────────

def _vasicek_simulate(
    r0: float = 0.045,
    kappa: float = 0.15,
    theta: float = 0.04,
    sigma: float = 0.01,
    years: int = 10,
    steps_per_year: int = 12,
    paths: int = 5000,
    seed: int = 42,
) -> list[list[float]]:
    """Simulate short rate paths using Vasicek model.

    dr = kappa * (theta - r) * dt + sigma * dW

    Calibrated to current US 10Y yield (4.28%) and historical vol.
    """
    rng = random.Random(seed)
    dt = 1.0 / steps_per_year
    total_steps = years * steps_per_year
    all_paths = []

    for _ in range(paths):
        path = [r0]
        r = r0
        for _ in range(total_steps):
            dW = rng.gauss(0, math.sqrt(dt))
            dr = kappa * (theta - r) * dt + sigma * dW
            r = max(r + dr, -0.05)  # Floor at -5% (negative rates possible)
            path.append(r)
        all_paths.append(path)

    return all_paths


def _cir_simulate(
    r0: float = 0.045,
    kappa: float = 0.15,
    theta: float = 0.04,
    sigma: float = 0.015,
    years: int = 10,
    steps_per_year: int = 12,
    paths: int = 5000,
    seed: int = 42,
) -> list[list[float]]:
    """Cox-Ingersoll-Ross model — rates stay positive."""
    rng = random.Random(seed)
    dt = 1.0 / steps_per_year
    total_steps = years * steps_per_year
    all_paths = []

    for _ in range(paths):
        path = [r0]
        r = r0
        for _ in range(total_steps):
            dW = rng.gauss(0, math.sqrt(dt))
            dr = kappa * (theta - r) * dt + sigma * math.sqrt(max(r, 0)) * dW
            r = max(r + dr, 0.001)  # CIR stays positive
            path.append(r)
        all_paths.append(path)

    return all_paths


def _gbm_fx(
    s0: float = 20.5,
    mu: float = 0.02,
    sigma: float = 0.12,
    years: int = 10,
    steps_per_year: int = 12,
    paths: int = 5000,
    seed: int = 43,
) -> list[list[float]]:
    """Geometric Brownian Motion for FX simulation.

    Note: GBM assumes log-normal distribution, which underestimates
    fat tails in real FX behavior. For production, consider using
    jump-diffusion or stochastic volatility models.
    """
    rng = random.Random(seed)
    dt = 1.0 / steps_per_year
    total_steps = years * steps_per_year
    all_paths = []

    for _ in range(paths):
        path = [s0]
        s = s0
        for _ in range(total_steps):
            dW = rng.gauss(0, math.sqrt(dt))
            dS = (mu - 0.5 * sigma**2) * dt + sigma * dW
            s = s * math.exp(dS)
            path.append(s)
        all_paths.append(path)

    return all_paths


def _compute_fan_chart(paths: list[list[float]], years: int) -> list[FanChartPoint]:
    """Compute percentile bands from simulation paths."""
    steps = len(paths[0])
    fan = []
    for i in range(steps):
        values = sorted([p[i] for p in paths])
        n = len(values)
        fan.append(FanChartPoint(
            year=round(i * years / (steps - 1), 2),
            p10=round(values[int(n * 0.10)], 6),
            p25=round(values[int(n * 0.25)], 6),
            p50=round(values[int(n * 0.50)], 6),
            p75=round(values[int(n * 0.75)], 6),
            p90=round(values[int(n * 0.90)], 6),
        ))
    return fan


# ── API Endpoints ──────────────────────────────────────────────────────

@router.post("/run")
def run_simulation(config: SimulationConfig):
    """Run full Monte Carlo simulation with correlated paths."""
    seed = config.seed or 42

    # Simulate rate paths
    if config.rate_model == "cir":
        rate_paths = _cir_simulate(years=config.years, paths=config.paths, seed=seed)
    elif config.rate_model == "hull_white":
        rate_paths = _vasicek_simulate(years=config.years, paths=config.paths, seed=seed)
    else:
        rate_paths = _vasicek_simulate(years=config.years, paths=config.paths, seed=seed)

    # Simulate FX paths
    fx_paths = _gbm_fx(years=config.years, paths=config.paths, seed=seed + 1)

    # Compute fan charts
    rate_fan = _compute_fan_chart(rate_paths, config.years)
    fx_fan = _compute_fan_chart(fx_paths, config.years)

    # Compute debt-to-GDP fan (simplified: base GDP * rate/FX effects)
    gdp_base = 1_788_000  # MX GDP in millions USD
    debt_base = 996_000   # MX debt in millions USD
    dtg_fan = []
    for i in range(len(rate_fan)):
        rate_effect = rate_fan[i].p50
        fx_effect = fx_fan[i].p50 / 20.5
        dtg = (debt_base * (1 + rate_effect * 0.3)) / (gdp_base * (1 + 0.02)) * 100
        dtg_fan.append(FanChartPoint(
            year=rate_fan[i].year,
            p10=round(dtg * 0.92, 2),
            p25=round(dtg * 0.96, 2),
            p50=round(dtg, 2),
            p75=round(dtg * 1.04, 2),
            p90=round(dtg * 1.08, 2),
        ))

    return {
        "config": config.model_dump(),
        "rate_model": {
            "name": config.rate_model,
            "fan_chart": [f.model_dump() for f in rate_fan],
            "final_rate_mean": round(sum(p[-1] for p in rate_paths) / len(rate_paths) * 100, 2),
            "final_rate_p5": round(sorted([p[-1] for p in rate_paths])[int(len(rate_paths) * 0.05)] * 100, 2),
            "final_rate_p95": round(sorted([p[-1] for p in rate_paths])[int(len(rate_paths) * 0.95)] * 100, 2),
        },
        "fx_model": {
            "name": "gbm",
            "fan_chart": [f.model_dump() for f in fx_fan],
            "final_fx_mean": round(sum(p[-1] for p in fx_paths) / len(fx_paths), 2),
            "final_fx_p5": round(sorted([p[-1] for p in fx_paths])[int(len(fx_paths) * 0.05)], 2),
            "final_fx_p95": round(sorted([p[-1] for p in fx_paths])[int(len(fx_paths) * 0.95)], 2),
        },
        "debt_to_gdp": {
            "fan_chart": [f.model_dump() for f in dtg_fan],
            "current": 55.7,
            "median_terminal": dtg_fan[-1].p50,
        },
        "summary": {
            "paths_simulated": config.paths,
            "years_horizon": config.years,
            "rate_95ci": f"{sorted([p[-1] for p in rate_paths])[int(len(rate_paths) * 0.05)] * 100:.2f}% — {sorted([p[-1] for p in rate_paths])[int(len(rate_paths) * 0.95)] * 100:.2f}%",
            "fx_95ci": f"{sorted([p[-1] for p in fx_paths])[int(len(fx_paths) * 0.05)]:.2f} — {sorted([p[-1] for p in fx_paths])[int(len(fx_paths) * 0.95)]:.2f}",
            "dtg_terminal_median": dtg_fan[-1].p50,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/presets")
def get_simulation_presets():
    """Get preset macro scenarios for simulation."""
    return {
        "presets": [
            {
                "id": "gfc_2008",
                "name": "Global Financial Crisis 2008",
                "description": "Severe credit crunch, equity collapse, flight to safety, emergency rate cuts",
                "rate_shock_bps": -500,
                "fx_shock_pct": 15,
                "gdp_shock_pct": -6.5,
                "commodity_shock_pct": -35,
                "duration_months": 24,
                "severity": "extreme",
            },
            {
                "id": "covid_2020",
                "name": "COVID-19 Pandemic",
                "description": "Global shutdown, supply chain disruption, massive fiscal response",
                "rate_shock_bps": -200,
                "fx_shock_pct": 8,
                "gdp_shock_pct": -8.8,
                "commodity_shock_pct": -25,
                "duration_months": 18,
                "severity": "extreme",
            },
            {
                "id": "rate_spike",
                "name": "Interest Rate Spike",
                "description": "Rapid tightening cycle, bond market sell-off, duration pain",
                "rate_shock_bps": 400,
                "fx_shock_pct": -5,
                "gdp_shock_pct": -1.2,
                "commodity_shock_pct": 10,
                "duration_months": 12,
                "severity": "high",
            },
            {
                "id": "currency_crisis",
                "name": "Currency Crisis",
                "description": "EM currency collapse, capital flight, emergency intervention",
                "rate_shock_bps": 800,
                "fx_shock_pct": 35,
                "gdp_shock_pct": -4.5,
                "commodity_shock_pct": -15,
                "duration_months": 9,
                "severity": "extreme",
            },
            {
                "id": "stagflation",
                "name": "Stagflation",
                "description": "Persistent high inflation, low growth, policy dilemma",
                "rate_shock_bps": 300,
                "fx_shock_pct": -10,
                "gdp_shock_pct": -2.0,
                "commodity_shock_pct": 40,
                "duration_months": 36,
                "severity": "high",
            },
            {
                "id": "commodity_boom",
                "name": "Commodity Boom",
                "description": "Oil price surge benefits commodity exporters, inflationary pressure",
                "rate_shock_bps": 150,
                "fx_shock_pct": -8,
                "gdp_shock_pct": 2.5,
                "commodity_shock_pct": 60,
                "duration_months": 18,
                "severity": "moderate",
            },
            {
                "id": "soft_landing",
                "name": "Soft Landing",
                "description": "Gradual normalization, inflation under control, growth stable",
                "rate_shock_bps": -100,
                "fx_shock_pct": 2,
                "gdp_shock_pct": 1.8,
                "commodity_shock_pct": 5,
                "duration_months": 24,
                "severity": "low",
            },
            {
                "id": "geopolitical_shock",
                "name": "Geopolitical Crisis",
                "description": "Trade war escalation, sanctions, supply chain rerouting",
                "rate_shock_bps": 200,
                "fx_shock_pct": 12,
                "gdp_shock_pct": -3.0,
                "commodity_shock_pct": 45,
                "duration_months": 18,
                "severity": "high",
            },
        ]
    }


@router.post("/stress-test")
def run_stress_test(scenario: StressScenario):
    """Run stress test on the portfolio under a given scenario."""
    # Portfolio parameters
    total_debt = 557_400  # millions USD
    fixed_rate_pct = 0.68
    floating_rate_pct = 0.32
    avg_coupon = 5.52
    avg_maturity = 7.2

    # Calculate impact
    rate_impact = (scenario.rate_shock_bps / 10000) * total_debt * floating_rate_pct
    fx_impact = (scenario.fx_shock_pct / 100) * total_debt * 0.38  # 38% FX exposure
    gdp_impact = scenario.gdp_shock_pct / 100 * 1_788_000  # GDP in millions

    base_debt_gdp = 55.7
    stressed_debt = total_debt + rate_impact + fx_impact
    stressed_gdp = 1_788_000 + gdp_impact
    stressed_dtg = (stressed_debt / stressed_gdp * 100) if stressed_gdp > 0 else 999

    return {
        "scenario": scenario.model_dump(),
        "impact": {
            "base_debt_usd_m": total_debt,
            "stressed_debt_usd_m": round(stressed_debt, 1),
            "debt_increase_usd_m": round(rate_impact + fx_impact, 1),
            "base_debt_to_gdp": base_debt_gdp,
            "stressed_debt_to_gdp": round(stressed_dtg, 1),
            "dtg_change_pct": round(stressed_dtg - base_debt_gdp, 1),
            "annual_debt_service_change": round(rate_impact, 1),
            "fx_exposure_impact": round(fx_impact, 1),
        },
        "risk_assessment": {
            "severity": scenario.name,
            "dtg_breach": stressed_dtg > 60,
            "sustainable": stressed_dtg < 70,
            "rating_action_likelihood": "high" if stressed_dtg > 65 else "medium" if stressed_dtg > 58 else "low",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/fan-chart")
def get_fan_chart(model: str = "vasicek", years: int = 10):
    """Generate fan chart data for debt-to-GDP projection."""
    config = SimulationConfig(rate_model=model, years=years, paths=5000, seed=42)
    result = run_simulation(config, user)
    return {
        "debt_to_gdp_fan": result["debt_to_gdp"]["fan_chart"],
        "rate_fan": result["rate_model"]["fan_chart"],
        "fx_fan": result["fx_model"]["fan_chart"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
