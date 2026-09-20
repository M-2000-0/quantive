"""Enterprise Sovereign Debt Engine — FastAPI Microservices.

Endpoints:
    POST /api/v1/ingest      — Sync yield curves + debt inventory into DuckDB
    POST /api/v1/optimize     — Run QUBO optimization (quantum + classical)
    POST /api/v1/simulate     — Run 10K Monte Carlo stress tests
    POST /api/v1/report       — Generate LLM policy briefing
    GET  /api/v1/status       — System health + data freshness
    GET  /api/v1/history      — Past simulation/optimization results
"""

import json
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import get_current_user


router = APIRouter(prefix="/api/v1", tags=["enterprise-engine"])


# ── Request Models ──────────────────────────────────────────────────

class IngestRequest(BaseModel):
    country_code: str = Field(default="US", description="Country code for yield curve")
    days_back: int = Field(default=90, ge=1, le=365)
    include_tips: bool = Field(default=True)
    include_macro: bool = Field(default=True)


class OptimizeRequest(BaseModel):
    yield_curve: dict[str, float] = Field(default={"3M": 0.042, "2Y": 0.038, "5Y": 0.037, "10Y": 0.040, "30Y": 0.042})
    covariance_matrix: Optional[list[list[float]]] = None
    total_issuance: float = Field(default=50e9, gt=0)
    risk_aversion: float = Field(default=10.0, ge=0, le=100)
    instruments: Optional[list[dict]] = None


class SimulateRequest(BaseModel):
    yield_curve: dict[str, float] = Field(default={"3M": 0.042, "2Y": 0.038, "5Y": 0.037, "10Y": 0.040, "30Y": 0.042})
    instruments: Optional[list[dict]] = Field(default=None)
    n_paths: int = Field(default=10000, ge=100, le=100000)
    horizon_months: int = Field(default=60, ge=12, le=120)
    stress_scenarios: bool = Field(default=True)


class ReportRequest(BaseModel):
    portfolio_data: dict = Field(default={})
    yield_data: dict = Field(default={})
    macro_data: dict = Field(default={})
    optimization_result: Optional[dict] = None
    stress_test_result: Optional[dict] = None
    model: str = Field(default="ollama", description="ollama, openai, anthropic, template")
    api_key: Optional[str] = None


# ── Background Task Store ───────────────────────────────────────────

_tasks = {}


# ── Endpoints ───────────────────────────────────────────────────────

@router.get("/status")
def system_status():
    """System health, data freshness, and component availability."""
    status = {
        "engine": "enterprise_sovereign_debt_engine",
        "version": "2.0.0",
        "components": {},
    }

    # Check DuckDB
    try:
        from app.data.duckdb_engine import get_database_stats, get_connection
        conn = get_connection()
        stats = get_database_stats(conn)
        conn.close()
        status["components"]["duckdb"] = {"status": "operational", "stats": stats}
    except Exception as e:
        status["components"]["duckdb"] = {"status": "error", "error": str(e)}

    # Check Ollama — removed (external LLM dependency eliminated)
    status["components"]["ollama"] = {"status": "removed", "message": "External LLM dependencies removed — using own AI engine"}

    # Check ChromaDB — removed (external RAG dependency eliminated)
    status["components"]["chromadb"] = {"status": "removed", "message": "External RAG dependencies removed — using own AI engine"}

    # Check quantum
    try:
        import pennylane
        status["components"]["pennylane"] = {"status": "operational", "version": pennylane.__version__}
    except ImportError:
        status["components"]["pennylane"] = {"status": "not_installed"}

    try:
        import qiskit
        status["components"]["qiskit"] = {"status": "operational", "version": qiskit.__version__}
    except ImportError:
        status["components"]["qiskit"] = {"status": "not_installed"}

    return status


@router.post("/ingest")
def ingest_data(request: IngestRequest, background_tasks: BackgroundTasks):
    """Sync yield curves and debt inventory into DuckDB."""
    task_id = f"ingest_{int(time.time())}"

    def _run_ingest():
        try:
            from app.data.yield_fetcher import YieldFetcher
            fetcher = YieldFetcher()
            result = fetcher.fetch_all()
            _tasks[task_id] = {"status": "completed", "result": result}
        except Exception as e:
            _tasks[task_id] = {"status": "failed", "error": str(e)}

    _tasks[task_id] = {"status": "running", "started_at": time.time()}
    background_tasks.add_task(_run_ingest)

    return {"task_id": task_id, "status": "started"}


@router.post("/optimize")
def optimize_portfolio(request: OptimizeRequest):
    """Run QUBO optimization with covariance-weighted risk terms."""
    start = time.time()
    yield_curve_data = dict(request.yield_curve)
    data_source = {"type": "user_provided", "date": None}

    # ── Fetch real yield curve if using defaults ──────────────────────
    default_curve = {"3M": 0.042, "2Y": 0.038, "5Y": 0.037, "10Y": 0.040, "30Y": 0.042}
    if yield_curve_data == default_curve or not yield_curve_data:
        try:
            from app.market_data.yield_curve import fetch_treasury_yield_curve
            raw = fetch_treasury_yield_curve(use_cache=True)
            if raw and "maturities" in raw:
                yield_curve_data = {m["label"]: m["rate_pct"] / 100.0 for m in raw["maturities"]}
                data_source = {"type": "US Treasury", "date": raw.get("date"), "source": raw.get("source")}
        except Exception:
            pass

    try:
        # Build covariance matrix if not provided
        if request.covariance_matrix is None:
            from app.market_data.covariance import compute_yield_covariance, YieldObservation
            # Generate synthetic observations from current curve
            observations = []
            for i in range(30):
                rates = {}
                for label, rate in yield_curve_data.items():
                    import random
                    noise = random.gauss(0, 0.001) * (i + 1)
                    rates[label] = rate + noise
                observations.append(YieldObservation(date=f"2026-01-{i+1:02d}", rates=rates))
            cov_result = compute_yield_covariance(observations)
            cov_matrix = cov_result.covariance_matrix
        else:
            cov_matrix = request.covariance_matrix

        # Run QUBO optimization
        from app.optimization.covariance_qubo import formulate_covariance_qubo, solve_covariance_qubo
        problem = formulate_covariance_qubo(
            yield_rates=yield_curve_data,
            covariance_matrix=cov_matrix,
            total_issuance=request.total_issuance,
            risk_aversion=request.risk_aversion,
        )

        result = solve_covariance_qubo(problem)

        elapsed = time.time() - start

        # Save to DuckDB
        try:
            from app.data.duckdb_engine import get_connection, save_optimization_run
            conn = get_connection()
            save_optimization_run(conn, {
                "solver_status": "optimal",
                "objective_value": result["objective_value"],
                "allocations": result["selected_options"],
                "qubo_cost": result["objective_value"],
                "solve_time_seconds": elapsed,
                "n_variables": problem.n_variables,
                "backend": "simulated_annealing",
            })
            conn.close()
        except Exception:
            pass

        return {
            "status": "success",
            "result": result,
            "solve_time_seconds": round(elapsed, 3),
            "n_variables": problem.n_variables,
            "risk_aversion": request.risk_aversion,
            "data_source": data_source,
            "yield_curve_used": {k: round(v * 100, 2) for k, v in yield_curve_data.items() if k in ["3M", "6M", "1Y", "2Y", "5Y", "7Y", "10Y", "20Y", "30Y"]},
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.post("/simulate")
def simulate_stress(request: SimulateRequest, user=Depends(get_current_user)):
    """Run parallelized Monte Carlo stress tests (10K+ paths).

    Plan-limited: n_paths is capped by the org's max_scenarios limit
    (100 free / 10,000 pro / unlimited enterprise).
    """
    from app.billing import enforce_resource_limit
    from app.models import User
    enforce_resource_limit(user.org_id, "max_scenarios", request.n_paths)

    start = time.time()

    try:
        # Use provided instruments or build a synthetic portfolio from the yield curve
        instruments = request.instruments
        if not instruments:
            instruments = []
            total = 50e9
            for label, rate in request.yield_curve.items():
                n = len(request.yield_curve)
                instruments.append({
                    "principal_outstanding": total / n,
                    "coupon_rate": rate,
                    "maturity_years": {"3M": 0.25, "2Y": 2, "5Y": 5, "10Y": 10, "30Y": 30}.get(label, 5),
                    "rate_type": "fixed",
                    "name": f"{label} Bond",
                })
        else:
            # Normalize incoming instrument keys to match compute_portfolio_risk schema
            for inst in instruments:
                if "principal_outstanding" not in inst and "principal" in inst:
                    inst["principal_outstanding"] = inst["principal"]
                if "rate_type" not in inst and "type" in inst:
                    inst["rate_type"] = inst["type"]

        # Run scenario generation
        from app.data.scenario_generator import generate_scenarios, scenario_result_to_dict, ScenarioConfig
        config = ScenarioConfig(
            n_paths=request.n_paths,
            horizon_months=request.horizon_months,
        )
        scenarios = generate_scenarios(request.yield_curve, config)
        scenario_dict = scenario_result_to_dict(scenarios)

        # Run portfolio risk analysis
        from app.data.financial_models import compute_portfolio_risk
        risk = compute_portfolio_risk(
            instruments,
            n_simulations=min(request.n_paths, 5000),
            horizon_months=request.horizon_months,
        )

        # Run stress scenarios
        stress_results = {}
        if request.stress_scenarios:
            from app.data.financial_models import generate_stress_scenarios, apply_yield_shock
            for shock in generate_stress_scenarios():
                shocked_curve = apply_yield_shock(request.yield_curve, shock)
                shocked_risk = compute_portfolio_risk(
                    instruments,
                    n_simulations=1000,
                    horizon_months=request.horizon_months,
                )
                stress_results[shock.name] = {
                    "description": shock.description,
                    "shift_bps": shock.parallel_shift_bps,
                    "var_95": shocked_risk.var_95,
                    "cvar_95": shocked_risk.cvar_95,
                    "portfolio_duration": shocked_risk.portfolio_duration,
                }

        elapsed = time.time() - start

        return {
            "status": "success",
            "yield_scenarios": scenario_dict,
            "portfolio_risk": {
                "total_value": risk.total_value,
                "duration": risk.portfolio_duration,
                "convexity": risk.portfolio_convexity,
                "pv01": risk.portfolio_pv01,
                "var_95": risk.var_95,
                "var_99": risk.var_99,
                "cvar_95": risk.cvar_95,
                "cvar_99": risk.cvar_99,
                "sharpe_ratio": risk.sharpe_ratio,
                "volatility": risk.volatility,
            },
            "stress_tests": stress_results,
            "elapsed_seconds": round(elapsed, 3),
            "n_paths": request.n_paths,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


@router.post("/report")
def generate_report(request: ReportRequest):
    """Generate policy briefing using our own template engine."""
    start = time.time()

    try:
        from app.optimization.policy_engine import generate_policy_brief

        brief = generate_policy_brief(
            optimization_result=request.optimization_result or {},
            monte_carlo_results={},
            covariance_data={},
            cost_of_service=request.portfolio_data or {},
            macro_data=request.macro_data or {},
            model_provider="template",
        )

        elapsed = time.time() - start
        result = {
            "executive_summary": brief.executive_summary,
            "key_recommendations": brief.key_recommendations,
            "risk_assessment": brief.risk_assessment,
            "issuance_strategy": brief.issuance_strategy,
            "cost_savings_analysis": brief.cost_savings_analysis,
            "stress_test_interpretation": brief.stress_test_interpretation,
            "confidence_level": brief.confidence_level,
            "caveats": brief.caveats,
            "model_used": brief.model_used,
        }
        result["elapsed_seconds"] = round(elapsed, 3)

        return {"status": "success", "report": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/history")
def get_history(limit: int = 20):
    """Get past simulation and optimization results."""
    try:
        from app.data.duckdb_engine import get_connection, get_simulation_history
        conn = get_connection()
        simulations = get_simulation_history(conn, limit)
        conn.close()
        return {"simulations": simulations}
    except Exception as e:
        return {"simulations": [], "error": str(e)}


@router.get("/task/{task_id}")
def get_task_status(task_id: str):
    """Check status of a background task."""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ── Maturity Ladder Optimizer ────────────────────────────────────

from pydantic import BaseModel as _BaseModel
from typing import Optional as _Optional


class MaturityLadderRequest(_BaseModel):
    instruments: list[dict]
    target_avg_maturity: float = 7.0
    total_issuance: float = 0
    yield_curve: _Optional[dict] = None
    max_single_quarter_pct: float = 12.0


@router.post("/maturity-ladder")
def optimize_maturity_ladder(request: MaturityLadderRequest):
    """Optimize the maturity distribution of a debt portfolio.
    
    Identifies maturity walls and recommends optimal issuance across tenors
    to create a smooth maturity ladder while minimizing cost of service.
    """
    from app.services.maturity_ladder import optimize_maturity_ladder as _optimize
    return _optimize(
        instruments=request.instruments,
        target_avg_maturity=request.target_avg_maturity,
        total_issuance=request.total_issuance,
        yield_curve=request.yield_curve,
        max_single_quarter_pct=request.max_single_quarter_pct,
    )


# ── Sovereign Debt Backtesting ──────────────────────────────────────

class BacktestRequest(_BaseModel):
    strategy: str = "hold"
    horizon_years: int = 5
    n_simulations: int = 1000
    risk_free_rate: float = 0.04
    yield_curve_history: _Optional[list[dict]] = None


@router.post("/backtest")
def run_sovereign_backtest(request_obj: Request, data: BacktestRequest, db: Session = Depends(get_db)):
    """Run Monte Carlo backtest on sovereign debt portfolio."""
    from app.services.backtesting import run_backtest
    from app.models import User
    from app.models import Portfolio
    from app.models import DebtInstrument

    token = request_obj.cookies.get("access_token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        from app.security import decode_token
        payload = decode_token(token)
        user = db.query(User).filter(User.id == payload.get("sub")).first() if payload else None
    except Exception:
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    portfolio_ids = [p.id for p in portfolios]
    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id.in_(portfolio_ids)
    ).all() if portfolio_ids else []

    inst_list = []
    for i in instruments:
        inst_list.append({
            "name": i.name,
            "instrument_type": i.instrument_type,
            "principal_outstanding": float(i.principal_outstanding),
            "currency": i.currency,
            "coupon_rate": float(i.coupon_rate) if i.coupon_rate else 0,
            "maturity_date": str(i.maturity_date) if i.maturity_date else None,
        })

    if not inst_list:
        raise HTTPException(status_code=400, detail="No instruments found")

    result = run_backtest(
        instruments=inst_list,
        strategy=data.strategy,
        yield_curve_history=data.yield_curve_history,
        horizon_years=data.horizon_years,
        n_simulations=data.n_simulations,
        risk_free_rate=data.risk_free_rate,
    )

    return result


@router.get("/backtest/compare")
def compare_backtest_strategies(
    request_obj: Request,
    horizon_years: int = 5,
    n_simulations: int = 500,
    db: Session = Depends(get_db),
):
    """Compare all backtesting strategies side by side."""
    from app.services.backtesting import compare_strategies
    from app.models import User
    from app.models import Portfolio
    from app.models import DebtInstrument

    token = request_obj.cookies.get("access_token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        from app.security import decode_token
        payload = decode_token(token)
        user = db.query(User).filter(User.id == payload.get("sub")).first() if payload else None
    except Exception:
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    portfolios = db.query(Portfolio).filter(Portfolio.org_id == user.org_id).all()
    portfolio_ids = [p.id for p in portfolios]
    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id.in_(portfolio_ids)
    ).all() if portfolio_ids else []

    inst_list = []
    for i in instruments:
        inst_list.append({
            "name": i.name,
            "instrument_type": i.instrument_type,
            "principal_outstanding": float(i.principal_outstanding),
            "currency": i.currency,
            "coupon_rate": float(i.coupon_rate) if i.coupon_rate else 0,
            "maturity_date": str(i.maturity_date) if i.maturity_date else None,
        })

    if not inst_list:
        raise HTTPException(status_code=400, detail="No instruments found")

    result = compare_strategies(
        instruments=inst_list,
        horizon_years=horizon_years,
        n_simulations=n_simulations,
    )

    return result
