"""AI Model Validation and Backtesting Framework.

Provides independent validation of optimization models and backtesting
against historical data. Addresses the "No AI Model Validation" critical
issue from the Government Procurement Stress Test.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ValidationStatus(str, Enum):
    """Status of model validation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class ModelType(str, Enum):
    """Types of optimization models."""
    MILP = "milp"
    SIMULATED_ANNEALING = "simulated_annealing"
    QUBO = "qubo"
    GENETIC_ALGORITHM = "genetic_algorithm"
    SCENARIO_ENGINE = "scenario_engine"
    RISK_MODEL = "risk_model"


@dataclass
class ValidationResult:
    """Result of a model validation test."""
    test_id: str
    test_name: str
    model_type: ModelType
    status: ValidationStatus
    metric_name: str
    expected_value: float
    actual_value: float
    tolerance: float
    deviation_pct: float
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BacktestResult:
    """Result of a backtesting run."""
    backtest_id: str
    model_type: ModelType
    period_start: datetime
    period_end: datetime
    total_periods: int
    accuracy_metrics: dict[str, float]
    comparisons: list[dict] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


class ModelValidationEngine:
    """Validates optimization models against known benchmarks."""

    def __init__(self):
        self._results: list[ValidationResult] = []
        self._backtests: list[BacktestResult] = []

    def validate_feasibility(
        self,
        model_type: ModelType,
        allocations: dict[str, float],
        constraints: dict[str, Any],
    ) -> ValidationResult:
        """Validate that allocations satisfy all constraints."""
        violations = []

        # Check sum to 1.0
        total = sum(allocations.values())
        if abs(total - 1.0) > 0.01:
            violations.append(f"Allocations sum to {total:.4f}, expected 1.0")

        # Check non-negative
        for key, value in allocations.items():
            if value < 0:
                violations.append(f"Negative allocation for {key}: {value}")

        # Check concentration limits
        max_concentration = constraints.get("max_concentration", 0.4)
        for key, value in allocations.items():
            if value > max_concentration:
                violations.append(f"Concentration exceeded for {key}: {value:.2%} > {max_concentration:.2%}")

        status = ValidationStatus.PASSED if not violations else ValidationStatus.FAILED
        deviation = max([abs(v) for v in [total - 1.0]] + [0]) * 100

        result = ValidationResult(
            test_id=f"val-{uuid.uuid4().hex[:8]}",
            test_name="Feasibility Validation",
            model_type=model_type,
            status=status,
            metric_name="constraint_satisfaction",
            expected_value=1.0,
            actual_value=total,
            tolerance=0.01,
            deviation_pct=deviation,
            details={"violations": violations, "allocations": allocations},
        )

        self._results.append(result)
        return result

    def validate_optimality_gap(
        self,
        model_type: ModelType,
        solution_value: float,
        best_known_value: float,
    ) -> ValidationResult:
        """Validate optimality gap against best known solution."""
        gap_pct = abs(solution_value - best_known_value) / abs(best_known_value) * 100 if best_known_value != 0 else 0
        tolerance_pct = 5.0  # 5% tolerance

        status = ValidationStatus.PASSED if gap_pct <= tolerance_pct else ValidationStatus.WARNING

        result = ValidationResult(
            test_id=f"val-{uuid.uuid4().hex[:8]}",
            test_name="Optimality Gap Validation",
            model_type=model_type,
            status=status,
            metric_name="optimality_gap_pct",
            expected_value=0.0,
            actual_value=gap_pct,
            tolerance=tolerance_pct,
            deviation_pct=gap_pct,
            details={
                "solution_value": solution_value,
                "best_known_value": best_known_value,
                "gap_pct": gap_pct,
            },
        )

        self._results.append(result)
        return result

    def validate_stability(
        self,
        model_type: ModelType,
        runs: list[dict[str, float]],
    ) -> ValidationResult:
        """Validate solution stability across multiple runs."""
        if len(runs) < 2:
            return ValidationResult(
                test_id=f"val-{uuid.uuid4().hex[:8]}",
                test_name="Stability Validation",
                model_type=model_type,
                status=ValidationStatus.WARNING,
                metric_name="solution_variance",
                expected_value=0.0,
                actual_value=0.0,
                tolerance=0.01,
                deviation_pct=0.0,
                details={"error": "Need at least 2 runs"},
            )

        # Calculate variance across runs
        import statistics
        objectives = [run.get("objective_value", 0) for run in runs]
        mean_obj = statistics.mean(objectives)
        stdev_obj = statistics.stdev(objectives) if len(objectives) > 1 else 0
        cv = stdev_obj / mean_obj if mean_obj != 0 else 0  # Coefficient of variation

        tolerance = 0.05  # 5% CV tolerance
        status = ValidationStatus.PASSED if cv <= tolerance else ValidationStatus.WARNING

        result = ValidationResult(
            test_id=f"val-{uuid.uuid4().hex[:8]}",
            test_name="Stability Validation",
            model_type=model_type,
            status=status,
            metric_name="coefficient_of_variation",
            expected_value=0.0,
            actual_value=cv,
            tolerance=tolerance,
            deviation_pct=cv * 100,
            details={
                "num_runs": len(runs),
                "mean_objective": mean_obj,
                "stdev_objective": stdev_obj,
                "coefficient_of_variation": cv,
            },
        )

        self._results.append(result)
        return result

    def run_comprehensive_validation(
        self,
        model_type: ModelType,
        test_cases: list[dict],
    ) -> list[ValidationResult]:
        """Run a comprehensive validation suite."""
        results = []

        for i, test_case in enumerate(test_cases):
            if test_case.get("type") == "feasibility":
                result = self.validate_feasibility(
                    model_type=model_type,
                    allocations=test_case["allocations"],
                    constraints=test_case.get("constraints", {}),
                )
            elif test_case.get("type") == "optimality":
                result = self.validate_optimality_gap(
                    model_type=model_type,
                    solution_value=test_case["solution_value"],
                    best_known_value=test_case["best_known_value"],
                )
            elif test_case.get("type") == "stability":
                result = self.validate_stability(
                    model_type=model_type,
                    runs=test_case["runs"],
                )
            else:
                continue

            results.append(result)

        return results

    def get_validation_report(self) -> dict:
        """Generate a comprehensive validation report."""
        total = len(self._results)
        passed = sum(1 for r in self._results if r.status == ValidationStatus.PASSED)
        warnings = sum(1 for r in self._results if r.status == ValidationStatus.WARNING)
        failed = sum(1 for r in self._results if r.status == ValidationStatus.FAILED)

        return {
            "summary": {
                "total_tests": total,
                "passed": passed,
                "warnings": warnings,
                "failed": failed,
                "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
            },
            "results": [
                {
                    "test_id": r.test_id,
                    "test_name": r.test_name,
                    "model_type": r.model_type.value,
                    "status": r.status.value,
                    "metric_name": r.metric_name,
                    "expected_value": r.expected_value,
                    "actual_value": r.actual_value,
                    "tolerance": r.tolerance,
                    "deviation_pct": r.deviation_pct,
                }
                for r in self._results
            ],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


class BacktestingFramework:
    """Backtests optimization strategies against historical data."""

    def __init__(self):
        self._backtests: list[BacktestResult] = []

    def run_backtest(
        self,
        model_type: ModelType,
        historical_data: list[dict],
        strategy: dict[str, Any],
    ) -> BacktestResult:
        """Run a backtest against historical data."""
        backtest_id = f"bt-{uuid.uuid4().hex[:8]}"

        # Simulate backtest (in production, this would use real historical data)
        comparisons = []
        for period in historical_data:
            predicted = strategy.get("predicted_return", 0.05)
            actual = period.get("actual_return", 0.04)
            error = abs(predicted - actual)
            comparisons.append({
                "period": period.get("period"),
                "predicted": predicted,
                "actual": actual,
                "error": error,
                "error_pct": error / actual * 100 if actual != 0 else 0,
            })

        # Calculate accuracy metrics
        errors = [c["error"] for c in comparisons]
        import statistics
        mae = statistics.mean(errors) if errors else 0
        rmse = (statistics.mean([e**2 for e in errors]))**0.5 if errors else 0
        mape = statistics.mean([c["error_pct"] for c in comparisons]) if comparisons else 0

        result = BacktestResult(
            backtest_id=backtest_id,
            model_type=model_type,
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            total_periods=len(historical_data),
            accuracy_metrics={
                "mae": mae,
                "rmse": rmse,
                "mape": mape,
            },
            comparisons=comparisons,
            summary={
                "total_periods": len(historical_data),
                "avg_error": mae,
                "max_error": max(errors) if errors else 0,
                "accuracy_score": max(0, 100 - mape),
            },
        )

        self._backtests.append(result)
        return result

    def get_backtest_report(self) -> dict:
        """Generate a backtesting report."""
        return {
            "total_backtests": len(self._backtests),
            "results": [
                {
                    "backtest_id": bt.backtest_id,
                    "model_type": bt.model_type.value,
                    "total_periods": bt.total_periods,
                    "accuracy_metrics": bt.accuracy_metrics,
                    "summary": bt.summary,
                }
                for bt in self._backtests
            ],
        }


# Global instances
_validation_engine: ModelValidationEngine | None = None
_backtesting_framework: BacktestingFramework | None = None


def get_validation_engine() -> ModelValidationEngine:
    """Get the global validation engine."""
    global _validation_engine
    if _validation_engine is None:
        _validation_engine = ModelValidationEngine()
    return _validation_engine


def get_backtesting_framework() -> BacktestingFramework:
    """Get the global backtesting framework."""
    global _backtesting_framework
    if _backtesting_framework is None:
        _backtesting_framework = BacktestingFramework()
    return _backtesting_framework
