"""Model Validation and Backtesting API endpoints.

Exposes model validation, backtesting, and reporting for government compliance.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/model-validation", tags=["model-validation"])


# ── Request Models ─────────────────────────────────────────────────

class FeasibilityValidationRequest(BaseModel):
    model_type: str = Field(..., description="Model type (milp, simulated_annealing, etc.)")
    allocations: dict[str, float] = Field(..., description="Allocation percentages")
    constraints: dict | None = Field(default=None, description="Constraints to validate against")


class OptimalityGapRequest(BaseModel):
    model_type: str = Field(..., description="Model type")
    solution_value: float = Field(..., description="Solution objective value")
    best_known_value: float = Field(..., description="Best known solution value")


class StabilityValidationRequest(BaseModel):
    model_type: str = Field(..., description="Model type")
    runs: list[dict] = Field(..., min_length=2, description="Multiple run results")


class BacktestRequest(BaseModel):
    model_type: str = Field(..., description="Model type")
    historical_data: list[dict] = Field(..., min_length=1, description="Historical data periods")
    strategy: dict = Field(..., description="Strategy to backtest")


# ── API Endpoints ──────────────────────────────────────────────────

@router.post("/validate/feasibility")
def validate_feasibility(
    request: FeasibilityValidationRequest,
    user: User = Depends(get_current_user),
):
    """Validate that allocations satisfy all constraints."""
    from quantive.trust.model_validation import ModelType, get_validation_engine

    engine = get_validation_engine()

    model_type_map = {e.value: e for e in ModelType}
    model_type = model_type_map.get(request.model_type)
    if not model_type:
        raise HTTPException(400, f"Invalid model type: {request.model_type}")

    result = engine.validate_feasibility(
        model_type=model_type,
        allocations=request.allocations,
        constraints=request.constraints or {},
    )

    return {
        "test_id": result.test_id,
        "test_name": result.test_name,
        "status": result.status.value,
        "metric_name": result.metric_name,
        "expected_value": result.expected_value,
        "actual_value": result.actual_value,
        "tolerance": result.tolerance,
        "deviation_pct": result.deviation_pct,
        "details": result.details,
    }


@router.post("/validate/optimality")
def validate_optimality_gap(
    request: OptimalityGapRequest,
    user: User = Depends(get_current_user),
):
    """Validate optimality gap against best known solution."""
    from quantive.trust.model_validation import ModelType, get_validation_engine

    engine = get_validation_engine()

    model_type_map = {e.value: e for e in ModelType}
    model_type = model_type_map.get(request.model_type)
    if not model_type:
        raise HTTPException(400, f"Invalid model type: {request.model_type}")

    result = engine.validate_optimality_gap(
        model_type=model_type,
        solution_value=request.solution_value,
        best_known_value=request.best_known_value,
    )

    return {
        "test_id": result.test_id,
        "test_name": result.test_name,
        "status": result.status.value,
        "metric_name": result.metric_name,
        "expected_value": result.expected_value,
        "actual_value": result.actual_value,
        "tolerance": result.tolerance,
        "deviation_pct": result.deviation_pct,
        "details": result.details,
    }


@router.post("/validate/stability")
def validate_stability(
    request: StabilityValidationRequest,
    user: User = Depends(get_current_user),
):
    """Validate solution stability across multiple runs."""
    from quantive.trust.model_validation import ModelType, get_validation_engine

    engine = get_validation_engine()

    model_type_map = {e.value: e for e in ModelType}
    model_type = model_type_map.get(request.model_type)
    if not model_type:
        raise HTTPException(400, f"Invalid model type: {request.model_type}")

    result = engine.validate_stability(
        model_type=model_type,
        runs=request.runs,
    )

    return {
        "test_id": result.test_id,
        "test_name": result.test_name,
        "status": result.status.value,
        "metric_name": result.metric_name,
        "expected_value": result.expected_value,
        "actual_value": result.actual_value,
        "tolerance": result.tolerance,
        "deviation_pct": result.deviation_pct,
        "details": result.details,
    }


@router.post("/validate/comprehensive")
def run_comprehensive_validation(
    model_type: str,
    test_cases: list[dict],
    user: User = Depends(get_current_user),
):
    """Run a comprehensive validation suite."""
    from quantive.trust.model_validation import ModelType, get_validation_engine

    engine = get_validation_engine()

    model_type_map = {e.value: e for e in ModelType}
    mt = model_type_map.get(model_type)
    if not mt:
        raise HTTPException(400, f"Invalid model type: {model_type}")

    results = engine.run_comprehensive_validation(
        model_type=mt,
        test_cases=test_cases,
    )

    return {
        "model_type": model_type,
        "total_tests": len(results),
        "results": [
            {
                "test_id": r.test_id,
                "test_name": r.test_name,
                "status": r.status.value,
                "metric_name": r.metric_name,
                "actual_value": r.actual_value,
                "tolerance": r.tolerance,
            }
            for r in results
        ],
    }


@router.post("/backtest")
def run_backtest(
    request: BacktestRequest,
    user: User = Depends(get_current_user),
):
    """Run a backtest against historical data."""
    from quantive.trust.model_validation import ModelType, get_backtesting_framework

    framework = get_backtesting_framework()

    model_type_map = {e.value: e for e in ModelType}
    model_type = model_type_map.get(request.model_type)
    if not model_type:
        raise HTTPException(400, f"Invalid model type: {request.model_type}")

    result = framework.run_backtest(
        model_type=model_type,
        historical_data=request.historical_data,
        strategy=request.strategy,
    )

    return {
        "backtest_id": result.backtest_id,
        "model_type": result.model_type.value,
        "total_periods": result.total_periods,
        "accuracy_metrics": result.accuracy_metrics,
        "summary": result.summary,
    }


@router.get("/report")
def get_validation_report(
    user: User = Depends(get_current_user),
):
    """Get comprehensive validation report."""
    from quantive.trust.model_validation import get_validation_engine

    engine = get_validation_engine()
    report = engine.get_validation_report()

    return report


@router.get("/backtest/report")
def get_backtest_report(
    user: User = Depends(get_current_user),
):
    """Get backtesting report."""
    from quantive.trust.model_validation import get_backtesting_framework

    framework = get_backtesting_framework()
    report = framework.get_backtest_report()

    return report
