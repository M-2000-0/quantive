"""Problem specification: the compiled, solver-independent formulation.

``ProblemSpec`` is the single source of truth that every solver consumes. It
precomputes all scenario/risk coefficients once, so the MILP, heuristic and
QUBO solvers all optimise the *same* objective with the *same* constraint
semantics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from quantive.models.enums import ConstraintType, Currency, RateType
from quantive.models.instruments import Portfolio
from quantive.models.optimization import (
    Constraint,
    EconomicScenario,
    OptimizationObjective,
    OptimizationProblem,
)
from quantive.models.results import ConstraintStatus, RiskMetrics
from quantive.objectives.costs import (
    fx_risk_per_instrument,
    rate_stddev_per_instrument,
    scenario_cost_matrix,
    scenario_costs,
)

MAX_YEAR = 30


@dataclass
class ProblemSpec:
    """Compiled optimization problem."""

    problem: OptimizationProblem
    portfolio: Portfolio
    instruments: List = field(repr=False)
    instrument_ids: List[str]
    scenarios: List[EconomicScenario]
    n_instruments: int
    n_scenarios: int

    # numpy tables (all indexed by instrument order)
    cost_matrix: np.ndarray = field(repr=False)          # (I, S)
    probabilities: np.ndarray = field(repr=False)        # (S,) normalized
    cost_coeff: np.ndarray = field(repr=False)           # (I,) expected cost per unit = C @ p
    ir_risk: np.ndarray = field(repr=False)              # (I,)
    fx_risk: np.ndarray = field(repr=False)              # (I,)
    base_cost: np.ndarray = field(repr=False)            # (I,) base-scenario cost
    is_floating: np.ndarray = field(repr=False)          # (I,) bool
    is_foreign: np.ndarray = field(repr=False)           # (I,) bool
    currencies: np.ndarray = field(repr=False)           # (I,) str
    year_bucket: np.ndarray = field(repr=False)          # (I,) int
    is_liquid: np.ndarray = field(repr=False)            # (I,) bool
    capacity: np.ndarray = field(repr=False)             # (I,)
    cost_per_instrument: np.ndarray = field(repr=False)  # (I,) base cost (pre-FX)

    # objective
    weights: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    robust: bool = False

    # constraints
    financing_requirement: float = 0.0
    target_maturity_share: Dict[int, float] = field(default_factory=dict)
    refi_cap_share: float = 0.20
    concentration_max_share: float = 0.30
    concentration_min_share: float = 0.0
    min_liquidity_share: float = 0.0
    liquidity_threshold: float = 0.7
    floating_rate_limit_share: Optional[float] = None
    foreign_currency_limit_share: Optional[float] = None
    per_currency_limits: Dict[str, float] = field(default_factory=dict)
    max_instruments: Optional[int] = None
    custom_constraints: List[Dict] = field(default_factory=list)
    penalty: float = 1e4

    # -- objective evaluation ------------------------------------------------
    def expected_cost(self, x: np.ndarray) -> float:
        return float(np.dot(x, self.cost_coeff))

    def robust_cost(self, x: np.ndarray) -> float:
        if self.n_scenarios == 0:
            return 0.0
        return float(scenario_costs(x, self.cost_matrix).max())

    def maturity_amounts(self, x: np.ndarray) -> Dict[int, float]:
        out: Dict[int, float] = {}
        for i, b in enumerate(self.year_bucket):
            out[b] = out.get(b, 0.0) + x[i]
        return out

    def refinancing_risk(self, x: np.ndarray) -> float:
        """Peak-year refinancing need: largest single-year maturing amount.

        Minimising this spreads maturities across the year ladder and reduces
        the size of the largest rollover event (a standard measure of
        refinancing / rollover risk for a debt manager).
        """
        amounts = self.maturity_amounts(x)
        return max(amounts.values(), default=0.0)

    def interest_rate_risk(self, x: np.ndarray) -> float:
        return float(np.dot(x, self.ir_risk))

    def currency_risk(self, x: np.ndarray) -> float:
        return float(np.dot(x, self.fx_risk))

    def objective_value(self, x: np.ndarray) -> float:
        """Weighted composite objective (minimize)."""
        w_cost, w_refi, w_ir, w_fx = self.weights
        cost = self.robust_cost(x) if self.robust else self.expected_cost(x)
        return (w_cost * cost
                + w_refi * self.refinancing_risk(x)
                + w_ir * self.interest_rate_risk(x)
                + w_fx * self.currency_risk(x))

    def objective_decomposition(self, x: np.ndarray) -> Dict[str, float]:
        w_cost, w_refi, w_ir, w_fx = self.weights
        cost = self.robust_cost(x) if self.robust else self.expected_cost(x)
        return {
            "financing_cost": cost,
            "refinancing_risk": self.refinancing_risk(x),
            "interest_rate_risk": self.interest_rate_risk(x),
            "currency_risk": self.currency_risk(x),
            "weighted_financing_cost": w_cost * cost,
            "weighted_refinancing_risk": w_refi * self.refinancing_risk(x),
            "weighted_interest_rate_risk": w_ir * self.interest_rate_risk(x),
            "weighted_currency_risk": w_fx * self.currency_risk(x),
        }

    # -- risk metrics ---------------------------------------------------------
    def risk_metrics(self, x: np.ndarray) -> RiskMetrics:
        amounts = self.maturity_amounts(x)
        total = float(x.sum())
        max_share = max((v / total for v in amounts.values() if total > 0), default=0.0)
        floating = float(x[self.is_floating].sum()) if self.n_instruments else 0.0
        foreign = float(x[self.is_foreign].sum()) if self.n_instruments else 0.0
        return RiskMetrics(
            expected_cost=self.expected_cost(x),
            interest_rate_risk=self.interest_rate_risk(x),
            currency_risk=self.currency_risk(x),
            refinancing_risk=self.refinancing_risk(x),
            max_maturity_share=max_share,
            floating_share=floating / total if total > 0 else 0.0,
            foreign_currency_share=foreign / total if total > 0 else 0.0,
        )

    # -- constraint evaluation -------------------------------------------------
    def constraint_violations(self, x: np.ndarray) -> List[ConstraintStatus]:
        """Evaluate every enabled constraint; report satisfaction and violation."""
        statuses: List[ConstraintStatus] = []
        total = float(x.sum())
        R = self.financing_requirement
        amounts = self.maturity_amounts(x)

        def add(name, limit, value, detail="", lower_bound=False):
            if lower_bound:
                violation = max(0.0, limit - value) if limit is not None else 0.0
            else:
                violation = max(0.0, value - limit) if limit is not None else 0.0
            tol = (1e-6 * max(1.0, abs(limit))) if limit is not None else 1e-6
            statuses.append(ConstraintStatus(
                name=name, satisfied=violation <= tol, violation=violation, detail=detail,
            ))

        # debt capacity (equality: sum == R)
        deviation = total - R
        statuses.append(ConstraintStatus(
            name="debt_capacity",
            satisfied=abs(deviation) <= 1e-6 * max(1.0, R),
            violation=abs(deviation),
            detail=f"raised={total:.2f} (required {R:.2f})",
        ))
        # instrument capacities
        cap_viol = float(np.maximum(x - self.capacity, 0.0).sum())
        statuses.append(ConstraintStatus(
            name="instrument_capacity", satisfied=cap_viol <= 1e-6, violation=cap_viol,
            detail="sum of per-instrument capacity breaches",
        ))
        # floating rate limit
        if self.floating_rate_limit_share is not None:
            flt = float(x[self.is_floating].sum())
            add("floating_rate_limit", self.floating_rate_limit_share * R, flt,
                f"floating={flt/R:.1%}")
        # currency limits
        foreign = float(x[self.is_foreign].sum())
        if self.foreign_currency_limit_share is not None:
            add("currency_limit_foreign", self.foreign_currency_limit_share * R, foreign,
                f"foreign={foreign/R:.1%}")
        for ccy, cap in self.per_currency_limits.items():
            val = sum(v for i, v in enumerate(x) if self.currencies[i] == ccy)
            add(f"currency_limit:{ccy}", cap * R, val, f"{ccy}={val/R:.1%}")
        # minimum liquidity
        if self.min_liquidity_share > 0:
            liq = float(x[self.is_liquid].sum())
            add("min_liquidity", self.min_liquidity_share * R, liq,
                f"liquid={liq/R:.1%}", lower_bound=True)
        # refinancing limit per bucket
        for bucket, share in self.target_maturity_share.items():
            limit = self.refi_cap_share * R
            val = amounts.get(bucket, 0.0)
            add(f"refinancing_limit:y{bucket}", limit, val,
                f"maturing_y{bucket}={val/R:.1%}")
        # maturity concentration (max share)
        for bucket, val in amounts.items():
            add(f"maturity_concentration:y{bucket}", self.concentration_max_share * R, val,
                f"share={val/R:.1%}")
        # maturity concentration (min share when active)
        if self.concentration_min_share > 0:
            min_val = self.concentration_min_share * R
            for bucket, val in amounts.items():
                if val > 1e-9 and val < min_val - 1e-6:
                    statuses.append(ConstraintStatus(
                        name=f"maturity_min_share:y{bucket}",
                        satisfied=False,
                        violation=min_val - val,
                        detail=f"share={val/R:.1%} < {self.concentration_min_share:.1%}",
                    ))
        # cardinality
        if self.max_instruments is not None:
            n_active = int((x > 1e-6).sum())
            add("max_instruments", self.max_instruments, n_active, f"active={n_active}")
        # custom linear constraints: {"label", "weights": {id: coeff}, "limit"}
        for cst in self.custom_constraints:
            val = 0.0
            for inst_id, coeff in cst.get("weights", {}).items():
                try:
                    idx = self.instrument_ids.index(inst_id)
                except ValueError:
                    continue
                val += coeff * x[idx]
            add(cst.get("label", "custom"), cst.get("limit"), val)
        return statuses

    def feasibility(self, x: np.ndarray) -> Tuple[bool, int, float]:
        """Overall feasibility: all constraints satisfied within tolerance."""
        statuses = self.constraint_violations(x)
        violations = [s for s in statuses if not s.satisfied]
        total_mag = sum(s.violation for s in violations)
        return (len(violations) == 0, len(violations), total_mag)

    def violation_magnitude(self, x: np.ndarray) -> float:
        """Fast vectorized total constraint-violation magnitude.

        Used by stochastic solvers inside their inner loops (avoids building
        ``ConstraintStatus`` objects every iteration).
        """
        R = self.financing_requirement
        total = 0.0
        total += abs(float(x.sum()) - R)
        total += float(np.maximum(x - self.capacity, 0.0).sum())
        if self.floating_rate_limit_share is not None:
            total += max(0.0, float(x[self.is_floating].sum()) - self.floating_rate_limit_share * R)
        if self.foreign_currency_limit_share is not None:
            total += max(0.0, float(x[self.is_foreign].sum()) - self.foreign_currency_limit_share * R)
        for ccy, cap in self.per_currency_limits.items():
            val = sum(float(v) for i, v in enumerate(x) if self.currencies[i] == ccy)
            total += max(0.0, val - cap * R)
        if self.min_liquidity_share > 0:
            total += max(0.0, self.min_liquidity_share * R - float(x[self.is_liquid].sum()))
        amounts = self.maturity_amounts(x)
        for bucket in set(int(b) for b in self.year_bucket):
            val = amounts.get(bucket, 0.0)
            total += max(0.0, val - self.refi_cap_share * R)
            total += max(0.0, val - self.concentration_max_share * R)
        if self.concentration_min_share > 0:
            min_val = self.concentration_min_share * R
            for bucket, val in amounts.items():
                if val > 1e-9 and val < min_val:
                    total += min_val - val
        if self.max_instruments is not None:
            total += max(0, int((x > 1e-6).sum()) - self.max_instruments)
        for cst in self.custom_constraints:
            val = 0.0
            for iid, coeff in cst.get("weights", {}).items():
                if iid in self.instrument_ids:
                    val += coeff * x[self.instrument_ids.index(iid)]
            lim = cst.get("limit")
            if lim is not None:
                total += max(0.0, val - lim)
        return float(total)

    def n_feasible_constraints(self, x: np.ndarray) -> int:
        return sum(1 for s in self.constraint_violations(x) if s.satisfied)

    def total_constraints(self) -> int:
        return len(self.constraint_violations(np.zeros(self.n_instruments) + 1.0))


def _param(constraint: Constraint, key: str, default: float | None = None):
    return constraint.parameters.get(key, default)


def build_spec(portfolio: Portfolio, problem: OptimizationProblem,
               scenarios: List[EconomicScenario]) -> ProblemSpec:
    """Compile a portfolio + problem + scenario set into a ``ProblemSpec``."""
    instruments = portfolio.instruments
    ids = [i.id for i in instruments]
    n_i = len(instruments)
    n_s = len(scenarios)

    probs = np.array([max(s.probability, 1e-12) for s in scenarios], dtype=float)
    if probs.sum() <= 0:
        probs = np.ones(n_s) / max(n_s, 1)
    probs = probs / probs.sum()

    cost_matrix = scenario_cost_matrix(instruments, scenarios, portfolio.reference_currency)
    ir_risk = rate_stddev_per_instrument(instruments, scenarios)
    fx_risk = fx_risk_per_instrument(instruments, scenarios, portfolio.reference_currency)
    base = EconomicScenario(id="__base__", name="base", probability=1.0)
    base_cost = np.array([_base_cost_of(i, base, portfolio.reference_currency) for i in instruments])
    is_floating = np.array([i.rate_type == RateType.FLOATING for i in instruments])
    is_foreign = np.array([i.currency != portfolio.reference_currency for i in instruments])
    currencies = np.array([i.currency.value for i in instruments])
    year_bucket = np.array([min(MAX_YEAR, int(round(i.years_to_maturity()))) for i in instruments])
    liquid_threshold = _default_param(problem.constraints, ConstraintType.MIN_LIQUIDITY, "liquidity_threshold", 0.7)
    is_liquid = np.array([i.liquidity >= liquid_threshold for i in instruments])
    capacity = np.array([i.capacity for i in instruments])

    # objective weights
    obj: OptimizationObjective = problem.objectives
    weights = obj.as_tuple
    robust = problem.profile.value == "stress_resilient"

    # -- constraints ----------------------------------------------------------
    R = problem.financing_requirement
    target_maturity_share: Dict[int, float] = {}
    refi_cap = _default_param(problem.constraints, ConstraintType.REFINANCING_LIMIT, "max_share_per_bucket", 0.20)
    conc_max = _default_param(problem.constraints, ConstraintType.MATURITY_CONCENTRATION, "max_share", 0.30)
    conc_min = _default_param(problem.constraints, ConstraintType.MATURITY_CONCENTRATION, "min_share", 0.0)
    min_liq = _default_param(problem.constraints, ConstraintType.MIN_LIQUIDITY, "min_share", 0.0)
    float_limit = _default_param(problem.constraints, ConstraintType.FLOATING_RATE_LIMIT, "max_share", None)
    foreign_limit = None
    per_currency_limits: Dict[str, float] = {}
    for c in problem.constraints:
        if c.type == ConstraintType.CURRENCY_LIMIT:
            if c.currency is None:
                foreign_limit = _param(c, "max_share", None)
            else:
                per_currency_limits[c.currency.value] = _param(c, "max_share", 0.15)

    active_buckets = sorted(set(int(b) for b in year_bucket))
    if active_buckets:
        share = 1.0 / len(active_buckets)
        target_maturity_share = {b: share for b in active_buckets}

    custom = []
    for c in problem.constraints:
        if c.type == ConstraintType.CUSTOM and c.enabled:
            custom.append({
                "label": c.label(),
                "weights": c.parameters.get("coefficients", {}),
                "limit": c.parameters.get("limit"),
            })

    spec = ProblemSpec(
        problem=problem,
        portfolio=portfolio,
        instruments=instruments,
        instrument_ids=ids,
        scenarios=scenarios,
        n_instruments=n_i,
        n_scenarios=n_s,
        cost_matrix=cost_matrix,
        probabilities=probs,
        cost_coeff=cost_matrix @ probs,
        ir_risk=ir_risk,
        fx_risk=fx_risk,
        base_cost=base_cost,
        is_floating=is_floating,
        is_foreign=is_foreign,
        currencies=currencies,
        year_bucket=year_bucket,
        is_liquid=is_liquid,
        capacity=capacity,
        cost_per_instrument=base_cost,
        weights=weights,
        robust=robust,
        financing_requirement=R,
        target_maturity_share=target_maturity_share,
        refi_cap_share=refi_cap,
        concentration_max_share=conc_max,
        concentration_min_share=conc_min,
        min_liquidity_share=min_liq,
        liquidity_threshold=liquid_threshold,
        floating_rate_limit_share=float_limit,
        foreign_currency_limit_share=foreign_limit,
        per_currency_limits=per_currency_limits,
        max_instruments=problem.solver_config.max_instruments,
        custom_constraints=custom,
        penalty=problem.solver_config.constraint_penalty,
    )
    return spec


def _default_param(constraints: List[Constraint], ctype: ConstraintType, key: str, default):
    for c in constraints:
        if c.type == ctype and c.enabled and key in c.parameters:
            return c.parameters[key]
    return default


def _base_cost_of(instrument, base_scenario, reference_currency: Currency) -> float:
    from quantive.objectives.costs import instrument_rate, fx_factor

    rate = instrument_rate(instrument, base_scenario)
    return rate * fx_factor(instrument, base_scenario, reference_currency)