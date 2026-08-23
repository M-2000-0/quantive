"""Result, strategy, benchmark and stress-test models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from quantive.models.enums import ExecutionBackend, SolverType, StrategyProfile


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RiskMetrics(BaseModel):
    """Risk summary for a strategy, in annualized reference-currency units."""

    expected_cost: float = Field(0.0, description="Expected annual financing cost")
    interest_rate_risk: float = Field(0.0, description="Annual cost volatility from rate shocks")
    currency_risk: float = Field(0.0, description="Annual cost volatility from FX shocks")
    refinancing_risk: float = Field(0.0, description="Maturity-profile deviation penalty")
    max_maturity_share: float = Field(0.0, description="Largest share of debt maturing in a single year bucket")
    floating_share: float = Field(0.0, description="Share of floating-rate debt")
    foreign_currency_share: float = Field(0.0, description="Share of foreign-currency debt")


class ConstraintStatus(BaseModel):
    """Evaluation of one constraint for a given allocation."""

    name: str
    satisfied: bool
    violation: float = Field(0.0, description="Magnitude of violation (0 when satisfied)")
    detail: str = ""


class ScenarioResult(BaseModel):
    """Per-scenario behaviour of a strategy."""

    scenario_id: str
    scenario_name: str
    probability: float
    financing_cost: float
    effective_interest_rate: float = Field(0.0, description="Weighted-average financing rate in that scenario")
    violations: int = Field(0, description="Number of constraint violations in this scenario")


class Strategy(BaseModel):
    """A feasible allocation produced by an optimization run."""

    id: str
    name: str
    description: str = ""
    profile: StrategyProfile = StrategyProfile.BEST_OVERALL
    allocation: Dict[str, float] = Field(default_factory=dict)
    objective_value: float = 0.0
    financing_cost: float = 0.0
    risk_metrics: RiskMetrics = Field(default_factory=RiskMetrics)
    constraint_status: List[ConstraintStatus] = Field(default_factory=list)
    objective_decomposition: Dict[str, float] = Field(default_factory=dict)
    feasible: bool = True
    solver: str = ""
    solver_type: SolverType = SolverType.CLASSICAL
    execution_backend: ExecutionBackend = ExecutionBackend.CLASSICAL_CPU


class OptimizationResult(BaseModel):
    """Full result of one optimization run."""

    id: str
    problem_id: str
    profile: StrategyProfile = StrategyProfile.BEST_OVERALL
    strategy: Strategy
    scenario_results: List[ScenarioResult] = Field(default_factory=list)
    runtime: float = 0.0
    solver: str = ""
    solver_type: SolverType = SolverType.CLASSICAL
    execution_backend: ExecutionBackend = ExecutionBackend.CLASSICAL_CPU
    iterations: Optional[int] = None
    objective_evaluations: Optional[int] = None
    optimality_note: str = ""
    metadata: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)


class StressTestResult(BaseModel):
    """How a strategy behaves if the assumptions are wrong."""

    strategy_id: str
    scenario_count: int
    avg_financing_cost: float = 0.0
    worst_financing_cost: float = 0.0
    percentile_costs: Dict[str, float] = Field(default_factory=dict)
    refinancing_breaches: int = 0
    liquidity_breaches: int = 0
    currency_breaches: int = 0
    interest_rate_exposure: float = 0.0
    constraint_satisfaction_rate: float = 1.0
    cost_distribution: List[float] = Field(default_factory=list)


class BenchmarkRow(BaseModel):
    """Comparable metrics for one solver on one problem."""

    solver: str
    solver_type: SolverType
    execution_backend: ExecutionBackend
    feasible: bool
    objective_value: float
    financing_cost: float
    risk_total: float
    runtime: float
    constraint_violations: int = 0
    constraint_violation_magnitude: float = 0.0
    robustness_worst_cost: float = 0.0
    compute_cost: float = 0.0
    optimality_note: str = ""
    normalized: Dict[str, float] = Field(default_factory=dict)
    score: float = 0.0
    rank: int = 0
    best_for: List[str] = Field(default_factory=list)


class BenchmarkResult(BaseModel):
    """Benchmark of multiple solvers on the same problem."""

    problem_id: str
    methodology: str = ""
    ranking_weights: Dict[str, float] = Field(default_factory=dict)
    rows: List[BenchmarkRow] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)

    def ranked_rows(self) -> List[BenchmarkRow]:
        return sorted(self.rows, key=lambda r: r.rank if r.rank > 0 else 10**9)