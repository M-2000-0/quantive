"""Data layer: synthetic datasets and reproducible fixtures."""
from quantive.data.fixtures import (
    DEMO_FINANCING_REQUIREMENT,
    DEMO_PORTFOLIO_ID,
    build_default_problem,
    default_solver_config,
    demo_portfolio,
    load_demo_dataset,
    named_scenarios,
)
from quantive.data.synthetic import (
    BASE_FX,
    FX_VOLATILITY,
    SOFR_BASE,
    TODAY,
    USD_YIELD_CURVE,
    SyntheticPortfolioGenerator,
    base_fx_rates,
    curve_rate,
    fx_volatilities,
    generate_synthetic_portfolio,
)

__all__ = [
    "DEMO_FINANCING_REQUIREMENT",
    "DEMO_PORTFOLIO_ID",
    "BASE_FX",
    "FX_VOLATILITY",
    "SOFR_BASE",
    "TODAY",
    "USD_YIELD_CURVE",
    "SyntheticPortfolioGenerator",
    "build_default_problem",
    "base_fx_rates",
    "curve_rate",
    "default_solver_config",
    "demo_portfolio",
    "fx_volatilities",
    "generate_synthetic_portfolio",
    "load_demo_dataset",
    "named_scenarios",
]