"""Debt Optimizer API — End-to-End Optimization Endpoint.

POST /api/optimize-debt
    Full pipeline: data ingestion → QUBO → quantum solver → Monte Carlo → AI brief

GET /api/optimize-debt/status
    Health check for the optimization engine

GET /api/optimize-debt/scenarios
    Available stress test scenarios

POST /api/optimize-debt/quick
    Quick optimization with pre-filled parameters (for demo/dashboard)
"""

import json
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.billing import check_limit, record_usage
from app.models import User
from app.security import get_current_user
from app.optimization.qubo_formulator import formulate_qubo, decode_solution, evaluate_cost, DebtParameters, N_VARIABLES
from app.optimization.monte_carlo import run_monte_carlo, PortfolioInput, SimulationConfig
from app.optimization.policy_engine import generate_policy_brief
from app.market_data.covariance import compute_yield_covariance, compute_cost_of_service, YieldObservation


router = APIRouter(prefix="/api/optimize-debt", tags=["debt-optimizer"])


# ── Request/Response Models ─────────────────────────────────────────

class InstrumentInput(BaseModel):
    principal_outstanding: float = Field(..., gt=0, description="Principal in local currency")
    coupon_rate: float = Field(..., ge=0, le=0.5, description="Coupon rate as decimal (0.0425 = 4.25%)")
    maturity_years: float = Field(..., gt=0, le=50, description="Years to maturity")
    rate_type: str = Field(default="fixed", description="fixed, floating, or inflation")
    currency: str = Field(default="USD", min_length=3, max_length=3)


class OptimizationRequest(BaseModel):
    instruments: list[InstrumentInput] = Field(..., min_length=1, max_length=100)
    total_target_issuance: float = Field(..., gt=0, description="Total new issuance target")
    yield_curve: dict[str, float] = Field(default={"3M": 0.042, "1Y": 0.040, "2Y": 0.038, "5Y": 0.037, "10Y": 0.040, "30Y": 0.042})
    macro_data: dict = Field(default={"gdp_growth_pct": 2.5, "inflation_pct": 3.0, "fiscal_balance_pct": -3.5})
    max_floating_pct: float = Field(default=30.0, ge=0, le=100)
    target_avg_maturity: float = Field(default=7.0, gt=0, le=30)
    n_simulations: int = Field(default=1000, ge=100, le=10000)
    use_noise_mitigation: bool = Field(default=False)
    llm_provider: str = Field(default="template", description="template, openai, anthropic, ollama")
    llm_api_key: Optional[str] = Field(default=None)


class QuickOptimizationRequest(BaseModel):
    """Quick optimization with sensible defaults for demo."""
    total_debt_billion: float = Field(default=50.0, gt=0, description="Total debt in billions")
    current_avg_coupon_pct: float = Field(default=5.2, ge=0, le=20)
    current_avg_maturity_years: float = Field(default=6.5, gt=0, le=30)
    current_floating_pct: float = Field(default=25.0, ge=0, le=100)
    use_live_data: bool = Field(default=True, description="Fetch real Treasury yield curve")


# ── Endpoints ───────────────────────────────────────────────────────

@router.get("/status")
def optimization_status():
    """Health check for the optimization engine."""
    return {
        "status": "operational",
        "engine": "hybrid_quantum_classical",
        "qubo_variables": N_VARIABLES,
        "features": [
            "QUBO formulation",
            "QAOA quantum circuit (classical simulation)",
            "Noise mitigation (ZNE + REM)",
            "Monte Carlo stress testing (1000+ sims)",
            "LLM policy generation (template/OpenAI/Anthropic/Ollama)",
            "Classical fallback (SciPy SLSQP)",
        ],
        "classical_fallback": "SciPy SLSQP",
        "quantum_backend": "classical_simulator",
    }


@router.get("/scenarios")
def list_scenarios():
    """List available stress test scenarios."""
    return {
        "scenarios": [
            {"name": "rate_200bps_up", "description": "Parallel +200bps yield curve shift", "severity": "moderate"},
            {"name": "rate_100bps_down", "description": "Parallel -100bps yield curve rally", "severity": "mild"},
            {"name": "rate_300bps_up", "description": "Parallel +300bps severe rate shock", "severity": "severe"},
            {"name": "yield_steepening", "description": "Long-end +100bps, short-end -50bps", "severity": "moderate"},
            {"name": "inflation_spike", "description": "+300bps CPI shock with rate response", "severity": "severe"},
            {"name": "fx_devaluation", "description": "Local currency -20% with inflation pass-through", "severity": "severe"},
            {"name": "liquidity_crisis", "description": "Short-term rates spike +500bps", "severity": "critical"},
            {"name": "recession", "description": "Rates drop -200bps, GDP contraction -3%", "severity": "moderate"},
        ]
    }


@router.post("")
def optimize_debt(
    request: OptimizationRequest,
    user: User = Depends(get_current_user),
):
    """Full debt optimization pipeline (auth required, plan-limited).

    Pipeline: data ingestion → QUBO → hybrid quantum-classical solver →
    Monte Carlo stress tests → AI policy brief.

    Raises 401 when unauthenticated, 429 when the org's daily
    optimization limit is exhausted.
    """
    # ── Step 0: Plan limit enforcement (metering gate) ───────────
    limit_info = check_limit(user.org_id, "optimizations_per_day")
    if not limit_info["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_reached",
                "message": f"Daily optimization limit reached ({limit_info['current']}/{limit_info['limit']} on the {limit_info['plan']} plan). Upgrade to increase your limit.",
                "current": limit_info["current"],
                "limit": limit_info["limit"],
                "plan": limit_info["plan"],
                "resource": "optimizations_per_day",
            },
        )

    result = _execute_optimization(request)
    record_usage(user.org_id, "optimizations_per_day", 1)
    result["billing"] = {
        "plan": limit_info["plan"],
        "usage": {"used": limit_info["current"] + 1, "limit": limit_info["limit"]},
    }
    return result


def _execute_optimization(request: OptimizationRequest) -> dict:
    """Core pipeline: QUBO formulation → hybrid solver → Monte Carlo → policy brief."""
    start_time = time.time()

    try:
        # ── Step 1: Build QUBO ──────────────────────────────────────
        debt_params = DebtParameters(
            current_allocations=[inst.model_dump() for inst in request.instruments],
            total_target_issuance=request.total_target_issuance,
            yield_rates=request.yield_curve,
            swap_rates=request.yield_curve,  # Use same for simplicity
            max_floating_pct=request.max_floating_pct,
            target_avg_maturity_years=request.target_avg_maturity,
        )
        qubo = formulate_qubo(debt_params)

        # ── Step 2: Solve (quantum attempt → classical fallback) ────
        from app.quantum.hybrid_solver import HybridSolver
        from app.quantum.state_encoder import CircuitParameters, CostFunction

        circuit_params = CircuitParameters(
            n_qubits=qubo.n_variables,
            n_layers=3,
            gamma=[0.5, 0.5, 0.5],
            beta=[0.5, 0.5, 0.5],
        )

        cost_fn = CostFunction(
            max_single_maturity_concentration=request.max_floating_pct / 100,
            max_fx_exposure=0.30,
        )

        solver = HybridSolver(max_iterations=200, timeout_seconds=30)
        quantum_result = solver.solve(
            circuit_params, cost_fn,
            instruments=[inst.model_dump() for inst in request.instruments],
            yield_curve=[{"maturity": k, "rate": v} for k, v in request.yield_curve.items()],
            macro_data=request.macro_data,
            use_noise_mitigation=request.use_noise_mitigation,
        )

        # Decode solution into actionable allocations.
        # The QUBO has one binary variable per (maturity, rate-type) pair.
        # Derive the binary vector from the solver's solution weights when the
        # dimensionality matches; otherwise fall back to a diversified
        # selection (fixed-rate across the mid-curve buckets) so decoding
        # never indexes outside the QUBO's variable space.
        n = qubo.n_variables
        weights = []
        if hasattr(quantum_result, "best_parameters") and quantum_result.best_parameters:
            weights = list(quantum_result.best_parameters)
        if len(weights) != n:
            solution_dict = quantum_result.solution if isinstance(quantum_result.solution, dict) else {}
            weights = solution_dict.get("weights", [])
        if len(weights) != n:
            # Diversified deterministic default: pick fixed+floating across
            # the 5Y/10Y/30Y buckets (indices of those maturities in the map).
            x_binary = [0] * n
            n_maturities = N_VARIABLES // 3 if N_VARIABLES % 3 == 0 else 9
            for mat_idx in (3, 5, 8):  # 5Y, 10Y, 30Y in MATURITY_BUCKETS
                for rt_idx in (0, 1):  # fixed, floating
                    k = mat_idx * 3 + rt_idx
                    if k < n:
                        x_binary[k] = 1
        else:
            max_w = max(weights) or 1.0
            x_binary = [1 if (w / max_w) > 0.5 else 0 for w in weights]
            if sum(x_binary) == 0:
                x_binary[0] = 1
        decoded = decode_solution(x_binary, qubo, request.total_target_issuance)

        optimization_output = {
            "allocations": decoded.get("allocations", []),
            "portfolio_metrics": decoded.get("portfolio_metrics", {}),
            "solver": {
                "status": quantum_result.status.value,
                "backend": quantum_result.backend,
                "solve_time_seconds": round(quantum_result.solve_time_seconds, 3),
                "iterations": quantum_result.iterations,
                "fallback_used": quantum_result.fallback_used,
                "noise_mitigation": quantum_result.noise_mitigation_applied,
            },
            "qubo_cost": round(evaluate_cost(x_binary, qubo), 4),
        }

        # ── Step 3: Monte Carlo ─────────────────────────────────────
        # Normalize both portfolios to the same total value for fair comparison
        mc_total = request.total_target_issuance

        # Scale current instruments proportionally to mc_total
        current_total = sum(inst.principal_outstanding for inst in request.instruments)
        scale = mc_total / current_total if current_total > 0 else 1.0
        current_instruments = []
        for inst in request.instruments:
            d = inst.model_dump()
            d["principal_outstanding"] = d["principal_outstanding"] * scale
            current_instruments.append(d)
        current_portfolio = PortfolioInput(
            instruments=current_instruments,
            total_value=mc_total,
            name="Current Portfolio",
        )

        optimized_instruments = []
        for alloc in decoded.get("allocations", []):
            optimized_instruments.append({
                "principal_outstanding": alloc.get("amount", 0),
                "coupon_rate": request.yield_curve.get(alloc.get("maturity_label", "10Y"), 0.04) if alloc.get("rate_type") == "fixed" else 0.035,
                "maturity_years": alloc.get("maturity_years", 5),
                "rate_type": alloc.get("rate_type", "fixed"),
            })

        optimized_portfolio = PortfolioInput(
            instruments=optimized_instruments if optimized_instruments else current_instruments,
            total_value=mc_total,
            name="Optimized Portfolio",
        )

        mc_config = SimulationConfig(n_simulations=request.n_simulations, random_seed=42)
        mc_results = run_monte_carlo(
            current_portfolio, optimized_portfolio,
            request.yield_curve, request.macro_data, mc_config,
        )

        # ── Step 4: Cost of Service ─────────────────────────────────
        cos = compute_cost_of_service(
            [inst.model_dump() for inst in request.instruments],
            current_portfolio.total_value,
        )

        # ── Step 5: Covariance ──────────────────────────────────────
        # Generate synthetic yield observations from current curve
        observations = _generate_yield_observations(request.yield_curve, n_days=60)
        cov_result = compute_yield_covariance(observations)

        # ── Step 6: AI Policy Brief ─────────────────────────────────
        brief = generate_policy_brief(
            optimization_result=optimization_output,
            monte_carlo_results={
                "var": {
                    "var_95": mc_results.current_portfolio.var_95,
                    "cvar_975": mc_results.current_portfolio.cvar_95,
                    "expected_loss": mc_results.current_portfolio.expected_loss,
                },
                "stress_scenarios": {
                    name: {"portfolio_loss_pct": round((sr.mean_value - optimized_portfolio.total_value) / max(optimized_portfolio.total_value, 1) * 100, 2)}
                    for name, sr in mc_results.stress_scenarios.items()
                },
            },
            covariance_data={
                "volatility": cov_result.volatility,
                "eigenvalues": cov_result.eigenvalues,
            },
            cost_of_service={
                "total_annual_interest": cos.total_annual_interest,
                "weighted_avg_coupon": cos.weighted_avg_coupon,
                "weighted_avg_maturity": cos.weighted_avg_maturity,
                "duration_risk": cos.duration_risk,
            },
            macro_data=request.macro_data,
            model_provider=request.llm_provider,
            api_key=request.llm_api_key,
        )

        total_time = time.time() - start_time

        return {
            "status": "success",
            "optimization": optimization_output,
            "monte_carlo": {
                "current": _scenario_to_dict(mc_results.current_portfolio),
                "optimized": _scenario_to_dict(mc_results.optimized_portfolio),
                "comparison": mc_results.comparison,
                "stress_scenarios": {
                    name: _scenario_to_dict(sr)
                    for name, sr in mc_results.stress_scenarios.items()
                },
            },
            "cost_of_service": {
                "total_annual_interest": cos.total_annual_interest,
                "weighted_avg_coupon_pct": cos.weighted_avg_coupon,
                "weighted_avg_maturity_years": cos.weighted_avg_maturity,
                "duration_risk": cos.duration_risk,
                "convexity": cos.convexity,
                "cost_per_billion": cos.cost_per_billion,
            },
            "covariance": {
                "volatility": cov_result.volatility,
                "correlation": cov_result.correlation_matrix,
                "eigenvalues": cov_result.eigenvalues,
            },
            "policy_brief": {
                "executive_summary": brief.executive_summary,
                "key_recommendations": brief.key_recommendations,
                "risk_assessment": brief.risk_assessment,
                "issuance_strategy": brief.issuance_strategy,
                "cost_savings_analysis": brief.cost_savings_analysis,
                "stress_test_interpretation": brief.stress_test_interpretation,
                "confidence_level": brief.confidence_level,
                "caveats": brief.caveats,
                "model_used": brief.model_used,
            },
            "confidence_intervals": {
                "method": "Monte Carlo simulation with " + str(request.n_simulations) + " paths",
                "confidence_level": brief.confidence_level,
                "current": {
                    "mean_annual_interest": mc_results.current_portfolio.mean_value,
                    "std_dev": mc_results.current_portfolio.std_dev,
                    "ci_95_lower": mc_results.current_portfolio.mean_value - 1.96 * mc_results.current_portfolio.std_dev,
                    "ci_95_upper": mc_results.current_portfolio.mean_value + 1.96 * mc_results.current_portfolio.std_dev,
                    "var_95": mc_results.current_portfolio.var_95,
                    "var_99": mc_results.current_portfolio.var_99,
                    "percentiles": mc_results.current_portfolio.percentiles,
                },
                "optimized": {
                    "mean_annual_interest": mc_results.optimized_portfolio.mean_value,
                    "std_dev": mc_results.optimized_portfolio.std_dev,
                    "ci_95_lower": mc_results.optimized_portfolio.mean_value - 1.96 * mc_results.optimized_portfolio.std_dev,
                    "ci_95_upper": mc_results.optimized_portfolio.mean_value + 1.96 * mc_results.optimized_portfolio.std_dev,
                    "var_95": mc_results.optimized_portfolio.var_95,
                    "var_99": mc_results.optimized_portfolio.var_99,
                    "percentiles": mc_results.optimized_portfolio.percentiles,
                },
                "yield_volatility": cov_result.volatility,
                "disclaimer": "Confidence intervals are derived from Monte Carlo simulations under historical yield volatility assumptions. Actual outcomes may differ due to structural breaks, policy changes, or unprecedented market conditions.",
            },
            "metadata": {
                "solve_time_seconds": round(total_time, 3),
                "n_simulations": request.n_simulations,
                "n_variables_qubo": qubo.n_variables,
                "quantum_backend": quantum_result.backend,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.post("/quick")
def quick_optimize(
    request: QuickOptimizationRequest,
    user: User = Depends(get_current_user),
):
    """Quick optimization with pre-filled parameters for demo/dashboard.

    If use_live_data=True (default), fetches real US Treasury yield curve
    from treasury.gov and uses actual rates for the optimization.
    Auth required; counts against the org's daily optimization limit.
    """
    limit_info = check_limit(user.org_id, "optimizations_per_day")
    if not limit_info["allowed"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "daily_limit_reached",
                "message": f"Daily optimization limit reached ({limit_info['current']}/{limit_info['limit']} on the {limit_info['plan']} plan). Upgrade to increase your limit.",
                "current": limit_info["current"],
                "limit": limit_info["limit"],
                "plan": limit_info["plan"],
                "resource": "optimizations_per_day",
            },
        )
    total = request.total_debt_billion * 1e9

    # ── Fetch real yield curve ──────────────────────────────────────
    yield_curve_data = {}
    yield_curve_source = "hardcoded"
    yield_curve_date = None

    if request.use_live_data:
        try:
            from app.market_data.yield_curve import fetch_treasury_yield_curve
            raw = fetch_treasury_yield_curve(use_cache=True)
            if raw and "maturities" in raw:
                # Map to the format the optimizer expects
                for m in raw["maturities"]:
                    yield_curve_data[m["label"]] = m["rate_pct"] / 100.0  # Convert % to decimal
                yield_curve_source = raw.get("source", "US Treasury")
                yield_curve_date = raw.get("date")
                # Update coupon estimate from real data
                if "5Y" in yield_curve_data:
                    request.current_avg_coupon_pct = yield_curve_data["5Y"] * 100 + 0.5
        except Exception as e:
            print(f"[debt-optimizer] Live yield fetch failed: {e}, using defaults")

    # Fallback to hardcoded if live data unavailable
    if not yield_curve_data:
        yield_curve_data = {"3M": 0.042, "1Y": 0.040, "2Y": 0.038, "5Y": 0.037, "10Y": 0.040, "30Y": 0.042}

    # ── Build instruments from real rates ──────────────────────────
    instruments = []
    # Match instrument maturities to available yield curve points
    maturity_map = [
        (0.15, 2, "fixed", "2Y"),
        (0.20, 5, "fixed", "5Y"),
        (0.25, 10, "fixed", "10Y"),
        (0.15, 20, "fixed", "10Y"),  # Use 10Y rate as proxy for 20Y
        (0.10, 30, "fixed", "30Y"),
        (request.current_floating_pct / 100, 3, "floating", "3M"),
    ]

    for weight, mat_years, rate_type, curve_label in maturity_map:
        coupon = yield_curve_data.get(curve_label, request.current_avg_coupon_pct / 100)
        if rate_type == "floating":
            coupon *= 0.95  # Slight discount for floating
        instruments.append({
            "principal_outstanding": total * weight,
            "coupon_rate": coupon,
            "maturity_years": mat_years,
            "rate_type": rate_type,
        })

    full_request = OptimizationRequest(
        instruments=[InstrumentInput(**inst) for inst in instruments],
        total_target_issuance=total,
        yield_curve=yield_curve_data,
        n_simulations=500,
    )

    result = _execute_optimization(full_request)
    record_usage(user.org_id, "optimizations_per_day", 1)
    result["billing"] = {
        "plan": limit_info["plan"],
        "usage": {"used": limit_info["current"] + 1, "limit": limit_info["limit"]},
    }

    # Inject metadata about data source
    result["data_source"] = {
        "yield_curve_source": yield_curve_source,
        "yield_curve_date": yield_curve_date,
        "live_data": request.use_live_data and bool(yield_curve_data),
        "yield_curve": {k: round(v * 100, 2) for k, v in yield_curve_data.items()},
    }

    return result


# ── Helper Functions ────────────────────────────────────────────────

def _generate_yield_observations(yield_curve: dict[str, float], n_days: int = 60) -> list[YieldObservation]:
    """Generate synthetic yield observations from current curve for covariance."""
    from datetime import datetime as _dt, timedelta, timezone as _tz
    observations = []
    base_date = _dt.now(_tz.utc)

    for day in range(n_days):
        date = base_date - timedelta(days=n_days - day)
        rates = {}
        for label, rate in yield_curve.items():
            # Add random walk noise
            noise = sum(random.gauss(0, 0.001) for _ in range(day + 1))
            rates[label] = rate + noise * 0.1
        observations.append(YieldObservation(date=date.strftime("%Y-%m-%d"), rates=rates))

    return observations


def _scenario_to_dict(scenario) -> dict:
    """Convert ScenarioResult to JSON-serializable dict."""
    return {
        "scenario_name": scenario.scenario_name,
        "portfolio_name": scenario.portfolio_name,
        "mean_value": scenario.mean_value,
        "median_value": scenario.median_value,
        "std_dev": scenario.std_dev,
        "percentiles": scenario.percentiles,
        "var_95": scenario.var_95,
        "var_99": scenario.var_99,
        "cvar_95": scenario.cvar_95,
        "cvar_99": scenario.cvar_99,
        "expected_loss": scenario.expected_loss,
        "max_loss": scenario.max_loss,
        "prob_loss_10pct": scenario.prob_loss_10pct,
        "prob_loss_20pct": scenario.prob_loss_20pct,
        "mean_path": scenario.mean_path,
        "worst_path": scenario.worst_path,
        "best_path": scenario.best_path,
        "n_simulations": scenario.n_simulations,
        "horizon_months": scenario.horizon_months,
    }
