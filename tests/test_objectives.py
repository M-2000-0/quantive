"""Objective / cost / risk computation tests."""
from __future__ import annotations

import numpy as np
import pytest

from quantive.models.enums import Currency, RateType
from quantive.models.instruments import DebtInstrument
from quantive.models.optimization import EconomicScenario
from quantive.objectives.costs import (
    expected_financing_cost,
    fx_factor,
    fx_risk_per_instrument,
    instrument_rate,
    rate_stddev_per_instrument,
    scenario_cost_matrix,
    scenario_costs,
    weighted_average_rate,
)


def _fixed(currency=Currency.USD, coupon=0.04):
    return DebtInstrument(
        id="f", name="f", currency=currency, principal=100, coupon=coupon,
        rate_type=RateType.FIXED, maturity_date=__import__("datetime").date(2040, 1, 1),
        issue_date=__import__("datetime").date(2024, 1, 1), liquidity=0.8, market_capacity=100,
    )


def _floating(spread=0.005):
    return DebtInstrument(
        id="fl", name="fl", currency=Currency.USD, principal=100, coupon=spread,
        rate_type=RateType.FLOATING, maturity_date=__import__("datetime").date(2030, 1, 1),
        issue_date=__import__("datetime").date(2025, 1, 1), liquidity=0.8, market_capacity=100,
        benchmark="SOFR",
    )


def _scen(ir=0.0, fx=None, liq=1.0):
    return EconomicScenario(id="s", name="s", probability=1.0,
                            interest_rate_shock=ir, fx_shocks=fx or {}, liquidity_conditions=liq)


def test_fixed_rate_does_not_move_with_scenario():
    inst = _fixed(coupon=0.04)
    assert instrument_rate(inst, _scen(ir=0.0)) == pytest.approx(0.04)
    assert instrument_rate(inst, _scen(ir=0.03)) == pytest.approx(0.04)


def test_floating_rate_moves_with_scenario():
    inst = _floating(spread=0.005)
    base = instrument_rate(inst, _scen(ir=0.0))
    high = instrument_rate(inst, _scen(ir=0.02))
    assert high - base == pytest.approx(0.02)


def test_fx_factor_domestic_is_one():
    inst = _fixed()
    assert fx_factor(inst, _scen(fx={"EUR": 2.0}), Currency.USD) == pytest.approx(1.0)


def test_fx_factor_foreign_scales_with_shock():
    inst = _fixed(currency=Currency.EUR, coupon=0.04)
    f0 = fx_factor(inst, _scen(fx={"EUR": 1.0}), Currency.USD)
    f2 = fx_factor(inst, _scen(fx={"EUR": 1.1}), Currency.USD)
    assert f2 / f0 == pytest.approx(1.1)


def test_cost_matrix_shapes_and_values():
    insts = [_fixed(), _floating()]
    scens = [_scen(ir=0.0), _scen(ir=0.01)]
    C = scenario_cost_matrix(insts, scens, Currency.USD)
    assert C.shape == (2, 2)
    # fixed column identical across scenarios
    assert C[0, 0] == pytest.approx(C[0, 1])
    # floating higher in the rate-hike scenario
    assert C[1, 1] > C[1, 0]


def test_expected_cost():
    C = np.array([[0.04, 0.04], [0.05, 0.06]])
    probs = np.array([0.5, 0.5])
    x = np.array([100.0, 200.0])
    expected = expected_financing_cost(x, C, probs)
    assert expected == pytest.approx(0.5 * (100 * 0.04 + 200 * 0.05) + 0.5 * (100 * 0.04 + 200 * 0.06))


def test_scenario_costs_vector():
    C = np.array([[0.04, 0.05], [0.06, 0.07]])
    x = np.array([100.0, 50.0])
    costs = scenario_costs(x, C)
    assert costs[0] == pytest.approx(100 * 0.04 + 50 * 0.06)
    assert costs[1] == pytest.approx(100 * 0.05 + 50 * 0.07)


def test_ir_risk_zero_for_fixed_positive_for_floating():
    insts = [_fixed(), _floating()]
    scens = [_scen(ir=0.0), _scen(ir=0.02), _scen(ir=-0.01)]
    ir = rate_stddev_per_instrument(insts, scens)
    assert ir[0] == pytest.approx(0.0)
    assert ir[1] > 0


def test_fx_risk_zero_domestic_positive_foreign():
    insts = [_fixed(), _fixed(currency=Currency.EUR)]
    scens = [_scen(fx={"EUR": 1.0}), _scen(fx={"EUR": 1.1}), _scen(fx={"EUR": 0.95})]
    fx = fx_risk_per_instrument(insts, scens, Currency.USD)
    assert fx[0] == pytest.approx(0.0)
    assert fx[1] > 0


def test_weighted_average_rate():
    C = np.array([[0.04]])
    probs = np.array([1.0])
    x = np.array([100.0])
    assert weighted_average_rate(x, C, probs, 100.0) == pytest.approx(0.04)


def test_spec_objective_components(portfolio, problem, scenarios, spec):
    x = spec.capacity / spec.capacity.sum() * spec.financing_requirement
    obj = spec.objective_value(x)
    decomp = spec.objective_decomposition(x)
    assert obj == pytest.approx(
        decomp["weighted_financing_cost"]
        + decomp["weighted_refinancing_risk"]
        + decomp["weighted_interest_rate_risk"]
        + decomp["weighted_currency_risk"]
    )
    assert decomp["financing_cost"] > 0
    assert spec.expected_cost(x) == pytest.approx(decomp["financing_cost"])


def test_spec_robust_cost_is_worst_case(portfolio, problem, scenarios, spec):
    x = spec.capacity / spec.capacity.sum() * spec.financing_requirement
    per_scenario = scenario_costs(x, spec.cost_matrix)
    assert spec.robust_cost(x) == pytest.approx(per_scenario.max())