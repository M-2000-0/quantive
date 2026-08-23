"""Named scenario definitions."""
from __future__ import annotations

from typing import List, Optional

from quantive.models.enums import Currency
from quantive.models.optimization import EconomicScenario, NamedScenarioIds

# Per-currency FX shock multipliers used in named stress scenarios.
_FX_UP = {
    Currency.USD: 1.0, Currency.EUR: 1.05, Currency.GBP: 1.06, Currency.JPY: 1.04,
    Currency.CHF: 1.05, Currency.CAD: 1.03, Currency.AUD: 1.07, Currency.BRL: 1.10,
}
_FX_DOWN = {
    Currency.USD: 1.0, Currency.EUR: 0.97, Currency.GBP: 0.96, Currency.JPY: 0.98,
    Currency.CHF: 0.97, Currency.CAD: 0.99, Currency.AUD: 0.94, Currency.BRL: 0.90,
}
_FX_STRESS = {
    Currency.USD: 1.0, Currency.EUR: 1.08, Currency.GBP: 1.10, Currency.JPY: 1.06,
    Currency.CHF: 1.08, Currency.CAD: 1.12, Currency.AUD: 1.15, Currency.BRL: 1.25,
}
_FX_MODERATE = {
    Currency.USD: 1.0, Currency.EUR: 1.04, Currency.GBP: 1.05, Currency.JPY: 1.03,
    Currency.CHF: 1.04, Currency.CAD: 1.02, Currency.AUD: 1.06, Currency.BRL: 1.10,
}


def _fx(d: dict) -> dict:
    return {c.value: v for c, v in d.items()}


def _named_scenarios() -> List[EconomicScenario]:
    return [
        EconomicScenario(
            id=NamedScenarioIds.BASE, name="Base Case", probability=0.40,
            interest_rate_shock=0.0, inflation_shock=0.0, fx_shocks={},
            liquidity_conditions=1.0,
        ),
        EconomicScenario(
            id=NamedScenarioIds.HIGH_INTEREST, name="High Interest Rates", probability=0.15,
            interest_rate_shock=0.020, inflation_shock=0.010, fx_shocks=_fx(_FX_UP),
            liquidity_conditions=0.80,
        ),
        EconomicScenario(
            id=NamedScenarioIds.LOW_INTEREST, name="Low Interest Rates", probability=0.10,
            interest_rate_shock=-0.015, inflation_shock=-0.005, fx_shocks=_fx(_FX_DOWN),
            liquidity_conditions=0.95,
        ),
        EconomicScenario(
            id=NamedScenarioIds.HIGH_INFLATION, name="High Inflation", probability=0.10,
            interest_rate_shock=0.010, inflation_shock=0.030, fx_shocks=_fx(_FX_MODERATE),
            liquidity_conditions=0.85,
        ),
        EconomicScenario(
            id=NamedScenarioIds.FX_SHOCK, name="FX Shock", probability=0.10,
            interest_rate_shock=0.005, inflation_shock=0.005, fx_shocks=_fx(_FX_STRESS),
            liquidity_conditions=0.75,
        ),
        EconomicScenario(
            id=NamedScenarioIds.LIQUIDITY_SHOCK, name="Liquidity Shock", probability=0.15,
            interest_rate_shock=0.010, inflation_shock=0.008, fx_shocks=_fx(_FX_MODERATE),
            liquidity_conditions=0.30,
        ),
    ]


def named_scenarios(ids: Optional[List[str]] = None) -> List[EconomicScenario]:
    """Return named scenarios, optionally filtered by id.

    ``ids=None`` returns all six canonical scenarios. Order is preserved.
    """
    all_scenarios = _named_scenarios()
    if ids is None:
        return all_scenarios
    by_id = {s.id: s for s in all_scenarios}
    return [by_id[i] for i in ids if i in by_id]