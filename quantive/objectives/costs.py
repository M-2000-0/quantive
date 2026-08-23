"""Financing cost and risk computation.

Units: all money figures are expressed in units of the reporting (reference)
currency. Rates are decimals. The scenario cost matrix ``C[i, s]`` holds the
annual financing cost of instrument ``i`` per unit of principal issued, under
scenario ``s``, converted into reporting-currency units.

For a FIXED instrument the nominal rate is the coupon and does not move with
the scenario (that is the point of fixed-rate funding). For a FLOATING
instrument the nominal rate is ``SOFR_BASE + interest_rate_shock + spread``.

Foreign-currency instruments additionally convert through the scenario FX
shock, where a shock ``q > 1`` means the foreign currency *appreciated* against
the reporting currency (costlier for the reporting-currency borrower).
"""
from __future__ import annotations

from typing import List

import numpy as np

from quantive.data.synthetic import BASE_FX, SOFR_BASE
from quantive.models.instruments import DebtInstrument
from quantive.models.optimization import EconomicScenario
from quantive.models.enums import Currency, RateType

_FX_DEFAULT = {c.value: 1.0 for c in Currency}


def instrument_rate(instrument: DebtInstrument, scenario: EconomicScenario,
                    sofr_base: float = SOFR_BASE) -> float:
    """Nominal coupon rate of an instrument in a scenario (local currency)."""
    if instrument.rate_type == RateType.FLOATING:
        return sofr_base + scenario.interest_rate_shock + instrument.coupon
    return instrument.coupon


def fx_factor(instrument: DebtInstrument, scenario: EconomicScenario,
              reference_currency: Currency, base_fx=None) -> float:
    """Multiplicative factor converting local-currency amounts to reporting currency."""
    base_fx = base_fx or BASE_FX
    base_to_usd = base_fx[reference_currency.value]
    if instrument.currency == reference_currency:
        return 1.0
    shock = scenario.fx_shocks.get(instrument.currency.value, 1.0)
    return (base_fx[instrument.currency.value] * shock) / base_to_usd


def scenario_cost_matrix(instruments: List[DebtInstrument],
                         scenarios: List[EconomicScenario],
                         reference_currency: Currency = Currency.USD) -> np.ndarray:
    """Return ``C`` of shape (n_instruments, n_scenarios). Vectorized."""
    n_i = len(instruments)
    n_s = len(scenarios)
    if n_i == 0 or n_s == 0:
        return np.zeros((n_i, n_s))
    rates = _local_rates(instruments, scenarios)
    fx = _fx_factors(instruments, scenarios, reference_currency)
    return rates * fx


def _local_rates(instruments: List[DebtInstrument],
                 scenarios: List[EconomicScenario]) -> np.ndarray:
    """Vectorized local-currency nominal rates, shape (I, S)."""
    n_i = len(instruments)
    n_s = len(scenarios)
    is_float = np.array([i.rate_type == RateType.FLOATING for i in instruments])
    coupons = np.array([i.coupon for i in instruments])
    shocks = np.array([s.interest_rate_shock for s in scenarios])
    rates = np.empty((n_i, n_s))
    fixed = ~is_float
    if fixed.any():
        rates[fixed] = coupons[fixed][:, None]
    if is_float.any():
        rates[is_float] = SOFR_BASE + coupons[is_float][:, None] + shocks[None, :]
    return rates


def _fx_factors(instruments: List[DebtInstrument],
                scenarios: List[EconomicScenario],
                reference_currency: Currency) -> np.ndarray:
    """Vectorized FX conversion factors, shape (I, S)."""
    n_i = len(instruments)
    n_s = len(scenarios)
    base_to_usd = BASE_FX[reference_currency.value]
    ccy = [i.currency.value for i in instruments]
    base_fx = np.array([BASE_FX[c] for c in ccy])
    # per-scenario shock per currency
    shock = np.ones((n_i, n_s))
    for s, scen in enumerate(scenarios):
        for k, c in enumerate(ccy):
            shock[k, s] = scen.fx_shocks.get(c, 1.0)
    return (base_fx[:, None] / base_to_usd) * shock


def rate_stddev_per_instrument(instruments: List[DebtInstrument],
                               scenarios: List[EconomicScenario]) -> np.ndarray:
    """Std dev of the local-currency nominal rate per instrument across scenarios.

    Fixed-rate instruments have zero interest-rate risk under this model;
    floating-rate instruments inherit the volatility of the benchmark.
    """
    if not scenarios:
        return np.zeros(len(instruments))
    return _local_rates(instruments, scenarios).std(axis=1)


def fx_risk_per_instrument(instruments: List[DebtInstrument],
                           scenarios: List[EconomicScenario],
                           reference_currency: Currency = Currency.USD) -> np.ndarray:
    """Annual cost volatility attributable to FX per instrument.

    Defined as the base local-currency rate times the std dev of the FX
    conversion factor across scenarios. Zero for reporting-currency debt.
    """
    out = np.zeros(len(instruments))
    if not scenarios:
        return out
    base_rates = _local_rates(instruments, [EconomicScenario(id="__base__", name="base", probability=1.0)])
    fx = _fx_factors(instruments, scenarios, reference_currency)
    return (base_rates[:, 0] * fx.std(axis=1))


def expected_financing_cost(x: np.ndarray, cost_matrix: np.ndarray,
                            probabilities: np.ndarray) -> float:
    """Expected annual financing cost of allocation ``x`` under scenario weights."""
    if cost_matrix.size == 0:
        return 0.0
    return float(np.dot(x, cost_matrix @ probabilities))


def scenario_costs(x: np.ndarray, cost_matrix: np.ndarray) -> np.ndarray:
    """Per-scenario total financing cost of allocation ``x``. Shape (S,)."""
    if cost_matrix.size == 0:
        return np.zeros(0)
    return cost_matrix.T @ x


def weighted_average_rate(x: np.ndarray, cost_matrix: np.ndarray,
                          probabilities: np.ndarray, total: float) -> float:
    """Weighted-average financing rate (expected cost / principal)."""
    if total <= 0:
        return 0.0
    return expected_financing_cost(x, cost_matrix, probabilities) / total