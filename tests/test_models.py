"""Data validation and domain-model tests."""
from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from quantive.models.enums import Currency, RateType
from quantive.models.instruments import DebtInstrument, make_portfolio
from quantive.models.optimization import (
    Constraint,
    ConstraintType,
    EconomicScenario,
    OptimizationObjective,
    OptimizationProblem,
    SolverConfiguration,
)
from quantive.models.results import RiskMetrics, Strategy, StressTestResult


def make_instrument(iid="inst-1", currency=Currency.USD, coupon=0.04, rate_type=RateType.FIXED):
    return DebtInstrument(
        id=iid,
        name=f"Instrument {iid}",
        currency=currency,
        principal=1000.0,
        coupon=coupon,
        rate_type=rate_type,
        maturity_date=date(2040, 1, 1),
        issue_date=date(2024, 1, 1),
        liquidity=0.8,
        market_capacity=1000.0,
    )


def test_instrument_defaults_and_terms():
    inst = make_instrument()
    assert inst.term_years == pytest.approx(16.0, abs=0.2)
    assert inst.capacity == 1000.0
    assert inst.is_foreign(Currency.USD) is False
    assert inst.is_foreign(Currency.EUR) is True


def test_instrument_validation():
    with pytest.raises(ValidationError):
        DebtInstrument(
            id=" ", name="x", currency=Currency.USD, principal=-5,
            coupon=0.04, rate_type=RateType.FIXED,
            maturity_date=date(2040, 1, 1), issue_date=date(2024, 1, 1),
        )
    with pytest.raises(ValidationError):
        make_instrument(coupon=-0.01)


def test_portfolio_duplicate_ids_rejected():
    inst1 = make_instrument("dup")
    inst2 = make_instrument("dup")
    with pytest.raises(ValueError):
        make_portfolio("p", "test", [inst1, inst2])


def test_portfolio_views(portfolio):
    assert portfolio.total_principal() > 0
    exposure = portfolio.currency_exposure()
    assert sum(exposure.values()) == pytest.approx(portfolio.total_principal())
    rate_exp = portfolio.rate_exposure()
    assert set(rate_exp) <= {RateType.FIXED, RateType.FLOATING}
    profile = portfolio.maturity_profile()
    assert profile and all(y >= 0 for y in profile)


def test_objective_weights():
    obj = OptimizationObjective(financing_cost=2.0, refinancing_risk=0.5)
    assert obj.as_tuple == (2.0, 0.5, 1.0, 1.0)


def test_scenario_probability_must_be_positive():
    with pytest.raises(ValidationError):
        EconomicScenario(id="s", name="x", probability=0.0)
    with pytest.raises(ValidationError):
        EconomicScenario(id="s", name="x", probability=-1.0)


def test_constraint_types():
    c = Constraint(type=ConstraintType.FLOATING_RATE_LIMIT, limit=0.3)
    assert c.label() == "floating_rate_limit"


def test_problem_validation():
    with pytest.raises(ValidationError):
        OptimizationProblem(
            id="p", name="x", portfolio_id="pf",
            financing_requirement=-1.0,
            objectives=OptimizationObjective(),
        )
    with pytest.raises(ValidationError):
        OptimizationProblem(
            id="", name="x", portfolio_id="pf", financing_requirement=100.0,
            objectives=OptimizationObjective(),
        )


def test_solver_config_defaults():
    cfg = SolverConfiguration()
    assert cfg.solver == "milp"
    assert cfg.seed == 42
    assert cfg.anneal_iterations >= 100


def test_risk_metrics_defaults():
    rm = RiskMetrics()
    assert rm.expected_cost == 0.0
    assert rm.max_maturity_share == 0.0


def test_stress_result_model():
    st = StressTestResult(strategy_id="s", scenario_count=10)
    assert st.constraint_satisfaction_rate == 1.0


def test_strategy_model(portfolio, spec):
    allocation = {iid: 10.0 for iid in spec.instrument_ids}
    st = Strategy(id="s", name="Test", allocation=allocation)
    assert st.profile.value == "best_overall"
    assert sum(st.allocation.values()) == 10.0 * spec.n_instruments