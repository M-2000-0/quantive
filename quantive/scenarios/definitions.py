"""Named scenario definitions."""
from __future__ import annotations

from typing import List, Optional

from quantive.data.synthetic import FX_VOLATILITY
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


# Sector-specific shock parameters for Energy, Infrastructure, Water, Housing, Employment
_ENERGY_FX_STRESS = {
    Currency.USD: 1.0, Currency.EUR: 1.12, Currency.GBP: 1.15, Currency.JPY: 1.08,
    Currency.CHF: 1.12, Currency.CAD: 1.10, Currency.AUD: 1.18, Currency.BRL: 1.30,
}
_INFRASTRUCTURE_FX_STRESS = {
    Currency.USD: 1.0, Currency.EUR: 1.09, Currency.GBP: 1.11, Currency.JPY: 1.05,
    Currency.CHF: 1.09, Currency.CAD: 1.07, Currency.AUD: 1.12, Currency.BRL: 1.20,
}
_WATER_FX_STRESS = {
    Currency.USD: 1.0, Currency.EUR: 1.07, Currency.GBP: 1.09, Currency.JPY: 1.04,
    Currency.CHF: 1.07, Currency.CAD: 1.05, Currency.AUD: 1.10, Currency.BRL: 1.15,
}
_HOUSING_FX_STRESS = {
    Currency.USD: 1.0, Currency.EUR: 1.06, Currency.GBP: 1.08, Currency.JPY: 1.03,
    Currency.CHF: 1.06, Currency.CAD: 1.04, Currency.AUD: 1.09, Currency.BRL: 1.12,
}
_EMPLOYMENT_FX_STRESS = {
    Currency.USD: 1.0, Currency.EUR: 1.04, Currency.GBP: 1.05, Currency.JPY: 1.02,
    Currency.CHF: 1.04, Currency.CAD: 1.02, Currency.AUD: 1.07, Currency.BRL: 1.08,
}

# Policy what-if shock parameters
_POLICY_TAX_CUT = -0.02  # -2% tax reduction shock
_POLICY_SPENDING_CUT = -0.08  # -8% spending reduction shock
_POLICY_REGULATORY_RELIEF = 0.015  # +15% regulatory relief shock
_POLICY_SUBSIDY_INCREASE = 0.10  # +10% subsidy increase shock

# Macro-economic impact multipliers for policy what-if analysis
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


# Policy scenario multipliers for cost and dimension impacts
_POLICY_TAX_MULTIPLIERS = {
    "tax-cut-2pct": {"gdp": 1.02, "inflation": 1.01, "employment": 1.03, "debt_gdp": 0.98},
    "tax-cut-5pct": {"gdp": 1.05, "inflation": 1.02, "employment": 1.04, "debt_gdp": 0.95},
}
_POLICY_SPENDING_MULTIPLIERS = {
    "spending-cut-5pct": {"gdp": 0.97, "inflation": 0.99, "employment": 0.98, "debt_gdp": 0.95},
    "spending-cut-10pct": {"gdp": 0.92, "inflation": 0.95, "employment": 0.93, "debt_gdp": 0.88},
}
_POLICY_REGULATORY_MULTIPLIERS = {
    "regulatory-relief": {"gdp": 1.015, "inflation": 1.005, "employment": 1.02, "debt_gdp": 0.995},
}
_POLICY_SUBSIDY_MULTIPLIERS = {
    "subsidy-increase-10pct": {"gdp": 1.03, "inflation": 1.02, "employment": 1.04, "debt_gdp": 0.97},
}


def _fx(d: dict) -> dict:
    return {c.value: v for c, v in d.items()}


def _sector_fx_shocks(sector: str) -> dict:
    """Return FX shock multipliers for a given sector stress scenario."""
    mapping = {
        "energy": _ENERGY_FX_STRESS,
        "infrastructure": _INFRASTRUCTURE_FX_STRESS,
        "water": _WATER_FX_STRESS,
        "housing": _HOUSING_FX_STRESS,
        "employment": _EMPLOYMENT_FX_STRESS,
    }
    return mapping.get(sector, _FX_MODERATE)


def _policy_shock_multiplier(scenario_id: str) -> dict:
    """Get policy impact multipliers by scenario ID."""
    # Tax policy multipliers
    if scenario_id.startswith("tax-cut"):
        return _POLICY_TAX_MULTIPLIERS.get(scenario_id, {"gdp": 1.0, "inflation": 1.0, "employment": 1.0, "debt_gdp": 1.0})
    # Spending policy multipliers
    if scenario_id.startswith("spending-cut"):
        return _POLICY_SPENDING_MULTIPLIERS.get(scenario_id, {"gdp": 1.0, "inflation": 1.0, "employment": 1.0, "debt_gdp": 1.0})
    # Regulatory policy multipliers
    if scenario_id.startswith("regulatory"):
        return _POLICY_REGULATORY_MULTIPLIERS.get(scenario_id, {"gdp": 1.0, "inflation": 1.0, "employment": 1.0, "debt_gdp": 1.0})
    # Subsidy policy multipliers
    if scenario_id.startswith("subsidy"):
        return _POLICY_SUBSIDY_MULTIPLIERS.get(scenario_id, {"gdp": 1.0, "inflation": 1.0, "employment": 1.0, "debt_gdp": 1.0})
    return {"gdp": 1.0, "inflation": 1.0, "employment": 1.0, "debt_gdp": 1.0}

def policy_dimension_multipliers(policy_type: str, intensity: float = 1.0) -> dict:
    """Get macro-economic dimension multipliers for policy what-if analysis.
    
    Returns impacts on: budget, GDP, debt-to-GDP, inflation, employment.
    Multipliers are proportional to intensity.
    """
    base = _POLICY_BUDGET_MULTIPLIERS.get(policy_type, {"budget_impact": 0.0, "gdp_impact": 0.0, "debt_gdp_impact": 0.0, "inflation_impact": 0.0, "employment_impact": 0.0})
    # Apply intensity scaling
    return {k: round(v * intensity, 4) for k, v in base.items()}

def policy_debt_multipliers(policy_type: str, intensity: float = 1.0) -> dict:
    """Get debt-specific multipliers for policy what-if analysis."""
    base = _POLICY_DEBT_MULTIPLIERS.get(policy_type, {"debt": 0.0, "interest_savings": 0.0})
    return {k: round(v * intensity, 4) for k, v in base.items()}


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
        # New sector-specific scenarios
        EconomicScenario(
            id="energy-stress", name="Energy Stress", probability=0.12,
            interest_rate_shock=0.015, inflation_shock=0.025, fx_shocks=_sector_fx_shocks("energy"),
            liquidity_conditions=0.45,
        ),
        EconomicScenario(
            id="infrastructure-stress", name="Infrastructure Stress", probability=0.10,
            interest_rate_shock=0.010, inflation_shock=0.015, fx_shocks=_sector_fx_shocks("infrastructure"),
            liquidity_conditions=0.70,
        ),
        EconomicScenario(
            id="water-stress", name="Water Stress", probability=0.08,
            interest_rate_shock=0.008, inflation_shock=0.012, fx_shocks=_sector_fx_shocks("water"),
            liquidity_conditions=0.80,
        ),
        EconomicScenario(
            id="housing-stress", name="Housing Stress", probability=0.11,
            interest_rate_shock=0.020, inflation_shock=0.035, fx_shocks=_sector_fx_shocks("housing"),
            liquidity_conditions=0.50,
        ),
        EconomicScenario(
            id="employment-stress", name="Employment Stress", probability=0.14,
            interest_rate_shock=0.012, inflation_shock=0.018, fx_shocks=_sector_fx_shocks("employment"),
            liquidity_conditions=0.65,
        ),
        # Policy what-if scenarios
        EconomicScenario(
            id="tax-cut-2pct", name="Tax Cut 2%", probability=0.05,
            interest_rate_shock=0.0, inflation_shock=0.01, fx_shocks={},
            liquidity_conditions=1.0,
        ),
        EconomicScenario(
            id="tax-cut-5pct", name="Tax Cut 5%", probability=0.05,
            interest_rate_shock=0.0, inflation_shock=0.02, fx_shocks={},
            liquidity_conditions=1.0,
        ),
        EconomicScenario(
            id="spending-cut-5pct", name="Spending Cut 5%", probability=0.05,
            interest_rate_shock=0.0, inflation_shock=-0.005, fx_shocks={},
            liquidity_conditions=1.0,
        ),
        EconomicScenario(
            id="spending-cut-10pct", name="Spending Cut 10%", probability=0.05,
            interest_rate_shock=0.0, inflation_shock=-0.01, fx_shocks={},
            liquidity_conditions=1.0,
        ),
        EconomicScenario(
            id="regulatory-relief", name="Regulatory Relief", probability=0.05,
            interest_rate_shock=-0.005, inflation_shock=0.0, fx_shocks={},
            liquidity_conditions=1.0,
        ),
        EconomicScenario(
            id="subsidy-increase-10pct", name="Subsidy Increase 10%", probability=0.05,
            interest_rate_shock=0.0, inflation_shock=0.015, fx_shocks={},
            liquidity_conditions=1.0,
        ),
    ]

def named_scenarios(ids: Optional[List[str]] = None) -> List[EconomicScenario]:
    """Return named scenarios, optionally filtered by id.

    ``ids=None`` returns the 6 canonical scenarios (BASE..LIQUIDITY_SHOCK) for
    backwards-compatibility. Extra sector/policy scenarios are available via
    explicit ids. Order is preserved.
    """
    all_scenarios = _named_scenarios()
    if ids is None:
        ids = list(NamedScenarioIds.ALL)
    by_id = {s.id: s for s in all_scenarios}
    return [by_id[i] for i in ids if i in by_id]