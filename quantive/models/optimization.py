"""Optimization problem definition models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from pydantic import BaseModel, Field, field_validator

from quantive.models.enums import ConstraintType, Currency, StrategyProfile


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OptimizationObjective(BaseModel):
    """Configurable weights for the composite objective.

    All terms are expressed in consistent units (annualized millions of the
    reference currency). A weight of ``1.0`` values a unit of that risk equally
    to a unit of financing cost.
    """

    financing_cost: float = Field(1.0, ge=0, description="Weight on expected financing cost")
    refinancing_risk: float = Field(1.0, ge=0, description="Weight on maturity-profile refinancing risk")
    interest_rate_risk: float = Field(1.0, ge=0, description="Weight on floating-rate / interest-rate risk")
    currency_risk: float = Field(1.0, ge=0, description="Weight on foreign-currency exposure risk")

    @property
    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.financing_cost, self.refinancing_risk, self.interest_rate_risk, self.currency_risk)


class Constraint(BaseModel):
    """A single constraint on the optimization.

    ``limit`` is the numeric bound; interpretation depends on ``type``.
    ``parameters`` carries type-specific options (target profiles, coefficient
    matrices for custom constraints, etc.).
    """

    type: ConstraintType
    name: str | None = Field(None, description="Optional label for reporting")
    limit: float | None = Field(None, ge=0)
    currency: Currency | None = Field(None, description="Currency scope for CURRENCY_LIMIT")
    parameters: Dict = Field(default_factory=dict)
    enabled: bool = Field(True)

    def label(self) -> str:
        if self.name:
            return self.name
        if self.type == ConstraintType.CURRENCY_LIMIT and self.currency:
            return f"currency_limit:{self.currency.value}"
        return self.type.value


class EconomicScenario(BaseModel):
    """An economic scenario describing shocks applied to the base world.

    ``interest_rate_shock`` and ``inflation_shock`` are additive decimal shocks
    (0.01 == +100bp). ``fx_shocks`` are multiplicative per-currency shocks
    (1.0 == no change; 1.2 == +20% depreciation of the reporting currency
    against that currency). ``liquidity_conditions`` is 1.0 for normal
    conditions and lower under stress.
    """

    id: str
    name: str
    probability: float = Field(1.0, gt=0)
    interest_rate_shock: float = Field(0.0)
    inflation_shock: float = Field(0.0)
    fx_shocks: Dict[str, float] = Field(default_factory=dict)
    liquidity_conditions: float = Field(1.0, gt=0, le=1)

    @field_validator("probability")
    @classmethod
    def _prob_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("scenario probability must be > 0")
        return v


class SolverConfiguration(BaseModel):
    """Configuration for solver execution."""

    solver: str = Field("milp", description="Solver name; see quantive.solvers.registry")
    time_limit_seconds: float = Field(60.0, gt=0)
    seed: int = Field(42, description="Determinism seed for stochastic solvers")
    qubo_bits: int = Field(8, ge=2, le=16, description="Binary expansion resolution per continuous variable (QUBO)")
    anneal_iterations: int = Field(50_000, ge=100, description="Annealing iterations for stochastic solvers")
    annealing_initial_temp: float = Field(2.0, gt=0)
    annealing_cooling_rate: float = Field(0.98, gt=0, lt=1)
    max_instruments: int | None = Field(None, ge=1, description="Optional cardinality cap (MILP only)")
    constraint_penalty: float = Field(1e4, gt=0, description="Penalty multiplier for stochastic solvers")


class ScenarioConfiguration(BaseModel):
    """How the working scenario set is materialized for a problem.

    Named scenarios are always included. ``monte_carlo_count`` additional
    scenarios are generated deterministically from ``monte_carlo_seed``.
    The engine guarantees determinism when a seed is supplied.
    """

    include_named: List[str] = Field(default_factory=lambda: list(NamedScenarioIds.ALL))
    monte_carlo_count: int = Field(0, ge=0, le=20_000)
    monte_carlo_seed: int = Field(42)
    include_base_in_mc: bool = Field(True)


class NamedScenarioIds:
    """Well-known named scenario identifiers."""

    BASE = "base"
    HIGH_INTEREST = "high_interest"
    LOW_INTEREST = "low_interest"
    HIGH_INFLATION = "high_inflation"
    FX_SHOCK = "fx_shock"
    LIQUIDITY_SHOCK = "liquidity_shock"
    ALL = (BASE, HIGH_INTEREST, LOW_INTEREST, HIGH_INFLATION, FX_SHOCK, LIQUIDITY_SHOCK)


class OptimizationProblem(BaseModel):
    """Complete definition of an optimization problem."""

    id: str
    name: str
    portfolio_id: str
    financing_requirement: float = Field(gt=0, description="Total principal (R) to raise in reference-currency units")
    objectives: OptimizationObjective
    constraints: List[Constraint] = Field(default_factory=list)
    scenarios: List[EconomicScenario] = Field(default_factory=list, description="Materialized named scenarios")
    scenario_config: ScenarioConfiguration = Field(default_factory=ScenarioConfiguration)
    solver_config: SolverConfiguration = Field(default_factory=SolverConfiguration)
    reference_currency: Currency = Currency.USD
    profile: StrategyProfile = Field(StrategyProfile.BEST_OVERALL, description="Objective profile this problem targets")
    created_at: datetime = Field(default_factory=_utcnow)
    provenance: Dict = Field(
        default_factory=lambda: {
            "synthetic_data": True,
            "model_version": "quantive-engine/0.1.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
    )

    @field_validator("id")
    @classmethod
    def _id_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("problem id must not be blank")
        return v.strip()

    @field_validator("financing_requirement")
    @classmethod
    def _requirement_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("financing_requirement must be > 0")
        return v


class NamedStrategyProfiles:
    """Default objective-weight profiles used to generate distinct strategies.

    Each profile emphasizes a different trade-off and yields genuinely
    different feasible allocations.
    """

    PROFILES: Dict[StrategyProfile, tuple[OptimizationObjective, str]] = {
        StrategyProfile.BEST_OVERALL: (
            OptimizationObjective(financing_cost=1.0, refinancing_risk=1.0, interest_rate_risk=1.0, currency_risk=1.0),
            "Balanced trade-off across cost and risk.",
        ),
        StrategyProfile.LOWEST_RISK: (
            OptimizationObjective(financing_cost=0.3, refinancing_risk=3.0, interest_rate_risk=3.0, currency_risk=3.0),
            "Minimises maturity, interest-rate and currency risk within constraints.",
        ),
        StrategyProfile.LOWEST_COST: (
            OptimizationObjective(financing_cost=4.0, refinancing_risk=0.2, interest_rate_risk=0.2, currency_risk=0.2),
            "Minimises expected financing cost; risks only bounded by hard constraints.",
        ),
        StrategyProfile.STRESS_RESILIENT: (
            OptimizationObjective(financing_cost=1.0, refinancing_risk=1.0, interest_rate_risk=1.0, currency_risk=1.0),
            "Robust (minimax) objective: minimises worst-case financing cost across scenarios.",
        ),
    }


def default_constraints(reference_currency: Currency = Currency.USD) -> List[Constraint]:
    """A sensible default constraint set for sovereign debt optimization."""
    return [
        Constraint(type=ConstraintType.DEBT_CAPACITY, name="debt_capacity", limit=None),
        Constraint(type=ConstraintType.INSTRUMENT_CAPACITY, name="instrument_capacity", limit=None),
        Constraint(
            type=ConstraintType.FLOATING_RATE_LIMIT,
            name="floating_rate_limit",
            limit=0.30,
            parameters={"max_share": 0.30},
        ),
        Constraint(
            type=ConstraintType.CURRENCY_LIMIT,
            name="foreign_currency_limit",
            limit=0.25,
            parameters={"max_share": 0.25, "scope": "foreign"},
        ),
        Constraint(
            type=ConstraintType.MIN_LIQUIDITY,
            name="min_liquidity",
            limit=0.10,
            parameters={"min_share": 0.10, "liquidity_threshold": 0.7},
        ),
        Constraint(
            type=ConstraintType.REFINANCING_LIMIT,
            name="refinancing_limit",
            limit=0.20,
            parameters={"max_share_per_bucket": 0.20},
        ),
        Constraint(
            type=ConstraintType.MATURITY_CONCENTRATION,
            name="maturity_concentration",
            limit=0.30,
            parameters={"max_share": 0.30, "min_share": 0.03},
        ),
    ]