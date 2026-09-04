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

Sector-specific cost multipliers model nonlinear industry exposure under
different economic scenarios (energy price shocks, infrastructure demand
variation, water scarcity costs, housing market feedback, employment cost
pressures).

Policy what-if multipliers model fiscal and regulatory policy impacts:
- Tax policy changes (cuts/increases)
- Spending policy changes (cuts/growth)
- Regulatory changes (relief/burden)
- Subsidy modifications (increases/reductions)
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from quantive.data.synthetic import BASE_FX, SOFR_BASE
from quantive.models.instruments import DebtInstrument
from quantive.models.optimization import EconomicScenario
from quantive.models.enums import Currency, RateType
from quantive.scenarios.definitions import _policy_shock_multiplier

_FX_DEFAULT = {c.value: 1.0 for c in Currency}

# Sector-specific nonlinear cost multipliers applied on top of base rates.
# Each is a dict mapping scenario_name -> multiplier > 1.0 for stress, < 1.0 for benign.
_SECTOR_COST_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "energy": {
        "energy-stress": 1.45,
        "high_inflation": 1.20,
        "fx_shock": 1.15,
    },
    "infrastructure": {
        "infrastructure-stress": 1.30,
        "high_inflation": 1.12,
        "fx_shock": 1.08,
    },
    "water": {
        "water-stress": 1.25,
        "high_inflation": 1.10,
        "fx_shock": 1.05,
    },
    "housing": {
        "housing-stress": 1.35,
        "high_inflation": 1.15,
        "fx_shock": 1.10,
    },
    "employment": {
        "employment-stress": 1.20,
        "high_inflation": 1.08,
        "fx_shock": 1.06,
    },
}

# Policy what-if multipliers for macroeconomic dimensions
_POLICY_DIMENSION_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "tax-cut-2pct": {"gdp": 1.02, "inflation": 1.01, "employment": 1.03, "debt_gdp": 0.98},
    "tax-cut-5pct": {"gdp": 1.05, "inflation": 1.02, "employment": 1.04, "debt_gdp": 0.95},
    "spending-cut-5pct": {"gdp": 0.97, "inflation": 0.99, "employment": 0.98, "debt_gdp": 0.95},
    "spending-cut-10pct": {"gdp": 0.92, "inflation": 0.95, "employment": 0.93, "debt_gdp": 0.88},
    "regulatory-relief": {"gdp": 1.015, "inflation": 1.005, "employment": 1.02, "debt_gdp": 0.995},
    "subsidy-increase-10pct": {"gdp": 1.03, "inflation": 1.02, "employment": 1.04, "debt_gdp": 0.97},
}

# Policy dimension impact multipliers (new - budget, GDP, debt, inflation, employment)
_POLICY_BUDGET_MULTIPLIERS = {
    "tax-cut-2pct": {"budget_impact": -0.02, "gdp_impact": 0.02, "debt_gdp_impact": -0.02, "inflation_impact": 0.01, "employment_impact": 0.01},
    "tax-cut-5pct": {"budget_impact": -0.05, "gdp_impact": 0.05, "debt_gdp_impact": -0.05, "inflation_impact": 0.02, "employment_impact": 0.02},
    "spending-cut-5pct": {"budget_impact": 0.08, "gdp_impact": -0.03, "debt_gdp_impact": 0.05, "inflation_impact": -0.02, "employment_impact": -0.01},
    "spending-cut-10pct": {"budget_impact": 0.15, "gdp_impact": -0.05, "debt_gdp_impact": 0.10, "inflation_impact": -0.04, "employment_impact": -0.02},
    "regulatory-relief": {"budget_impact": 0.0, "gdp_impact": 0.015, "debt_gdp_impact": -0.005, "inflation_impact": 0.005, "employment_impact": 0.01},
    "subsidy-increase-10pct": {"budget_impact": -0.10, "gdp_impact": 0.03, "debt_gdp_impact": -0.03, "inflation_impact": 0.035, "employment_impact": 0.02},
}

_POLICY_DEBT_MULTIPLIERS = {
    "tax-cut-2pct": {"debt": -0.02, "interest_savings": 0.01},
    "tax-cut-5pct": {"debt": -0.05, "interest_savings": 0.02},
    "spending-cut-5pct": {"debt": 0.08, "interest_savings": 0.0},
    "spending-cut-10pct": {"debt": 0.15, "interest_savings": 0.0},
    "regulatory-relief": {"debt": -0.005, "interest_savings": 0.0},
    "subsidy-increase-10pct": {"debt": -0.10, "interest_savings": -0.005},
}


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


def _apply_policy_multipliers(cost_matrix: np.ndarray,
                              scenarios: List[EconomicScenario],
                              instruments: List[DebtInstrument],
                              reference_currency: Currency,
                              policy_type: str = "",
                              intensity: float = 1.0) -> np.ndarray:
    """Apply policy what-if multipliers to the cost matrix.
    
    Policy multipliers affect the macroeconomic dimensions (GDP, inflation,
    employment, debt-to-GDP) but do not directly change financing costs
    unless linked to specific instrument types.
    """
    n_i = len(instruments)
    n_s = len(scenarios)
    multipliers = np.ones((n_i, n_s))
    
    for s, scenario in enumerate(scenarios):
        scenario_name = scenario.id
        if policy_type and scenario_name in _POLICY_DIMENSION_MULTIPLIERS:
            mult = _POLICY_DIMENSION_MULTIPLIERS[scenario_name]
            # Apply generalized macro multiplier proportionally to instrument exposure
            for i in range(n_i):
                # Base multiplier applied uniformly; instrument-specific
                # effects handled by sector multipliers above
                multipliers[i, s] = mult.get("gdp", 1.0)
        elif policy_type and scenario_name in _POLICY_BUDGET_MULTIPLIERS:
            # Apply budget/GDP/debt/inflation/employment dimension multipliers
            budget_mult = _POLICY_BUDGET_MULTIPLIERS[scenario_name]
            debt_mult = _POLICY_DEBT_MULTIPLIERS.get(scenario_name, {"debt": 0.0, "interest_savings": 0.0})
            for i in range(n_i):
                # Apply dimension multipliers proportionally
                # GDP factor affects cost through economic activity
                gdp_factor = budget_mult.get("gdp_impact", 0.0) * intensity
                # Budget impact affects deficit financing costs
                budget_factor = budget_mult.get("budget_impact", 0.0) * intensity
                # Debt-to-GDP impact affects real financing costs
                debt_factor = debt_mult.get("debt", 0.0) * intensity
                # Inflation impact reduces real debt burden
                inflation_factor = -budget_mult.get("inflation_impact", 0.0) * intensity  # negative: inflation erodes real debt
                # Employment impact affects tax revenue and growth
                employment_factor = budget_mult.get("employment_impact", 0.0) * intensity
                
                # Composite multiplier: base 1.0 plus dimension effects
                base_mult = 1.0 + gdp_factor + debt_factor + inflation_factor + employment_factor
                multipliers[i, s] = base_mult
    
    return cost_matrix * multipliers


def scenario_cost_matrix(instruments: List[DebtInstrument],
                         scenarios: List[EconomicScenario],
                         reference_currency: Currency = Currency.USD,
                         sector_multipliers: bool = True,
                         policy_type: str = "",
                         intensity: float = 1.0) -> np.ndarray:
    """Return ``C`` of shape (n_instruments, n_scenarios). Vectorized.
    
    If ``sector_multipliers`` is True, sector-specific nonlinear cost
    multipliers are applied based on scenario names.
    
    If ``policy_type`` is specified, policy what-if multipliers are applied
    to model fiscal/policy impact on macroeconomic dimensions.
    """
    n_i = len(instruments)
    n_s = len(scenarios)
    if n_i == 0 or n_s == 0:
        return np.zeros((n_i, n_s))
    rates = _local_rates(instruments, scenarios)
    fx = _fx_factors(instruments, scenarios, reference_currency)
    base_costs = rates * fx

    # Apply sector-specific nonlinear multipliers
    if sector_multipliers:
        base_costs = _apply_sector_multipliers(base_costs, scenarios, instruments, reference_currency)

    # Apply policy what-if multipliers
    if policy_type:
        base_costs = _apply_policy_multipliers(base_costs, scenarios, instruments, reference_currency, policy_type, intensity)

    return base_costs


def _apply_sector_multipliers(cost_matrix: np.ndarray,
                              scenarios: List[EconomicScenario],
                              instruments: List[DebtInstrument],
                              reference_currency: Currency) -> np.ndarray:
    """Apply sector-specific nonlinear cost multipliers to the cost matrix."""
    n_i = len(instruments)
    n_s = len(scenarios)
    multipliers = np.ones((n_i, n_s))

    for s, scenario in enumerate(scenarios):
        scenario_name = scenario.id
        # Determine sector multiplier based on scenario id
        sector = _scenario_sector(scenario_name)
        if sector and sector in _SECTOR_COST_MULTIPLIERS:
            multiplier = _SECTOR_COST_MULTIPLIERS[sector].get(scenario_name, 1.0)
            # Instruments with relevant currency or type get the sector multiplier
            for i in range(n_i):
                inst = instruments[i]
                # Apply multiplier if instrument currency matches sector relevance
                # Energy: foreign currency instruments get amplified effect
                if sector == "energy" and inst.currency != reference_currency:
                    multipliers[i, s] = multiplier
                elif sector == "housing" and inst.rate_type.name == "FLOATING":
                    # Housing stress affects floating-rate debt most
                    multipliers[i, s] = multiplier
                elif sector == "employment" and inst.principal > 100:
                    # Large principal instruments get employment cost pressure
                    multipliers[i, s] = multiplier
                else:
                    multipliers[i, s] = 1.0
        # Default: no sector multiplier
    return cost_matrix * multipliers


def _scenario_sector(scenario_id: str) -> Optional[str]:
    """Map a scenario id to its sector category."""
    sector_map = {
        "energy-stress": "energy",
        "infrastructure-stress": "infrastructure",
        "water-stress": "water",
        "housing-stress": "housing",
        "employment-stress": "employment",
    }
    return sector_map.get(scenario_id)


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