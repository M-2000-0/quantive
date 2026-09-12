"""Deterministic synthetic market data and portfolio generation.

Everything in this module is seeded and reproducible: a fixed seed always
produces the identical portfolio. This keeps demo data stable across runs,
docs and CI without depending on external market data feeds.

``BASE_FX`` is quoted as USD per one unit of foreign currency. ``FX_VOLATILITY``
is the annualized FX volatility per currency (decimal). ``USD_YIELD_CURVE`` maps
a maturity in years to an annual rate (decimal) for USD sovereign paper.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

import numpy as np

from quantive.models.enums import Currency, RateType
from quantive.models.instruments import DebtInstrument, Portfolio, make_portfolio

# Reference "today" for derived instruments. Kept fixed so fixture-derived
# dates do not drift with wall-clock time between runs.
TODAY = date(2026, 3, 15)

# SOFR-style short-dated benchmark used as the base for floating instruments.
SOFR_BASE = 0.044

# USD per 1 unit of foreign currency (USD is the reporting currency).
BASE_FX: Dict[str, float] = {
    "USD": 1.0000,
    "EUR": 1.0800,
    "GBP": 1.2600,
    "JPY": 0.0067,
    "CHF": 1.1000,
    "CAD": 0.7400,
    "AUD": 0.6600,
    "BRL": 0.2000,
    "NOK": 0.0950,
    "SEK": 0.0980,
}

# Annualized per-currency FX volatility (decimal). Keyed by ISO currency code.
FX_VOLATILITY: Dict[str, float] = {
    "USD": 0.01,
    "EUR": 0.08,
    "GBP": 0.09,
    "JPY": 0.10,
    "CHF": 0.07,
    "CAD": 0.06,
    "AUD": 0.11,
    "BRL": 0.16,
    "NOK": 0.12,
    "SEK": 0.11,
}

# USD sovereign yield curve: term (years) -> annual rate (decimal).
USD_YIELD_CURVE: Dict[int, float] = {
    1: 0.0360,
    2: 0.0380,
    3: 0.0395,
    5: 0.0415,
    7: 0.0430,
    10: 0.0445,
    15: 0.0460,
    20: 0.0470,
    30: 0.0485,
}

_TERMS = (2, 3, 5, 7, 10, 15, 20, 30)


def curve_rate(term: float) -> float:
    """Linear-interpolated USD yield-curve rate for an arbitrary term (years)."""
    points = sorted(USD_YIELD_CURVE.items())
    if term <= points[0][0]:
        return points[0][1]
    if term >= points[-1][0]:
        return points[-1][1]
    for (t0, r0), (t1, r1) in zip(points, points[1:]):
        if t0 <= term <= t1:
            frac = (term - t0) / (t1 - t0)
            return r0 + frac * (r1 - r0)
    return points[-1][1]


def base_fx_rates() -> Dict[str, float]:
    """Snapshot of the base FX rates (USD per unit of foreign currency)."""
    return dict(BASE_FX)


def fx_volatilities() -> Dict[str, float]:
    """Snapshot of the per-currency annualized volatilities."""
    return dict(FX_VOLATILITY)


def generate_yield_curve() -> List[dict]:
    """Deterministic yield-curve export records for the air-gap transfer."""
    return [
        {
            "currency": "USD",
            "tenor_years": term,
            "rate": round(curve_rate(float(term)), 6),
            "asof": TODAY.isoformat(),
        }
        for term in range(1, 31)
    ]


def generate_fx_rates() -> List[dict]:
    """Deterministic FX-export records (USD per unit and inverse)."""
    rows = []
    for ccy, rate in sorted(BASE_FX.items()):
        rows.append({
            "currency": ccy,
            "usd_per_unit": rate,
            "units_per_usd": round(1.0 / rate, 6) if rate else 1.0,
            "asof": TODAY.isoformat(),
        })
    return rows


def generate_economic_indicators() -> List[dict]:
    """Deterministic macro-indicator export records."""
    return [
        {"indicator": "sofr", "value": SOFR_BASE, "unit": "decimal", "asof": TODAY.isoformat()},
        {"indicator": "gdp_growth", "value": 0.021, "unit": "decimal", "asof": TODAY.isoformat()},
        {"indicator": "inflation_cpi", "value": 0.024, "unit": "decimal", "asof": TODAY.isoformat()},
        {"indicator": "unemployment", "value": 0.038, "unit": "decimal", "asof": TODAY.isoformat()},
        {"indicator": "debt_to_gdp", "value": 0.95, "unit": "decimal", "asof": TODAY.isoformat()},
    ]


class SyntheticPortfolioGenerator:
    """Generate a deterministic, realistic debt portfolio from a seed.

    A fixed seed always produces the identical instrument set (count, names,
    principals, coupons); different seeds produce different portfolios.

    The structure is engineered to model a sovereign issuer: a USD-dominant
    maturity ladder (fixed-rate anchors and pillars per tenor), a floating-rate
    tranche benchmarked to SOFR, and a modest foreign-currency tranche. That
    mix keeps the default demo problem feasible under the default constraint
    set (foreign <= 25% of the raise, floating <= 30%, per-maturity caps).
    """

    # Foreign issuance currencies rotated across the maturity ladder.
    _FOREIGN_CURRENCIES = ["EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "BRL", "SEK", "NOK"]

    def __init__(self, seed: int = 42):
        self.seed = seed

    def _add(
        self,
        instruments: List[DebtInstrument],
        rng,
        ccy: str,
        term: int,
        rate_type: RateType,
        principal_lo: float,
        principal_hi: float,
        idx: int,
    ) -> None:
        principal = float(rng.uniform(principal_lo, principal_hi))
        if rate_type == RateType.FIXED:
            coupon = max(0.001, curve_rate(float(term)) + float(rng.normal(0.0, 0.0025)))
        else:
            coupon = float(rng.uniform(0.008, 0.018))
        liquidity = float(rng.uniform(0.55, 0.98))
        capacity = principal * float(rng.uniform(1.2, 2.2))
        maturity = TODAY + timedelta(days=int(365.25 * term))
        issue = maturity - timedelta(days=int(365.25 * max(1, int(0.35 * term))))
        instruments.append(DebtInstrument(
            id=f"{ccy}-{rate_type.value[:1]}-{idx:02d}",
            name=f"{ccy} {rate_type.value.replace('_', ' ').capitalize()} {term}Y",
            currency=Currency(ccy),
            principal=round(principal, 2),
            coupon=round(coupon, 4),
            rate_type=rate_type,
            maturity_date=maturity,
            issue_date=issue,
            callable=bool(rng.integers(0, 2)),
            liquidity=round(liquidity, 2),
            benchmark="SOFR" if rate_type == RateType.FLOATING else None,
            market_capacity=round(capacity, 2),
        ))

    def portfolio(
        self,
        portfolio_id: str,
        name: str = "Synthetic Demonstration Portfolio",
        reference_currency: Currency = Currency.USD,
        description: str = "Synthetic Demonstration Portfolio; deterministic synthetic data; not live market data.",
    ) -> Portfolio:
        if not portfolio_id or not portfolio_id.strip():
            portfolio_id = "synthetic-portfolio"
        rng = np.random.default_rng(self.seed)
        instruments: List[DebtInstrument] = []
        idx = 0

        # USD-dominant maturity ladder: per tenor two large fixed anchors, a
        # mid-size pillar, a floating tranche and a substantial foreign line.
        # Foreign capacity intentionally exceeds 1/3 of total capacity so a
        # capacity-proportional allocation violates the foreign-currency cap -
        # while USD supply stays ample for a feasible optimal solution.
        for term in _TERMS:
            for _ in range(2):
                self._add(instruments, rng, "USD", term, RateType.FIXED, 25e6, 50e6, idx)
                idx += 1
            self._add(instruments, rng, "USD", term, RateType.FIXED, 10e6, 22e6, idx)
            idx += 1
            self._add(instruments, rng, "USD", term, RateType.FLOATING, 6e6, 14e6, idx)
            idx += 1
            fccy = self._FOREIGN_CURRENCIES[term % len(self._FOREIGN_CURRENCIES)]
            self._add(instruments, rng, fccy, term, RateType.FIXED, 70e6, 120e6, idx)
            idx += 1

        # Supplementary lines to round out the book past 50 instruments.
        for term in (2, 5, 10, 20):
            self._add(instruments, rng, "USD", term, RateType.FIXED, 5e6, 9e6, idx)
            idx += 1
        for term in (2, 3, 5):
            self._add(instruments, rng, "USD", term, RateType.FLOATING, 3e6, 6e6, idx)
            idx += 1
        for term in (10, 15, 20):
            fccy = self._FOREIGN_CURRENCIES[(term + 1) % len(self._FOREIGN_CURRENCIES)]
            self._add(instruments, rng, fccy, term, RateType.FIXED, 30e6, 60e6, idx)
            idx += 1

        return make_portfolio(
            portfolio_id=portfolio_id,
            name=name,
            instruments=instruments,
            reference_currency=reference_currency,
            description=description,
            tags=["synthetic", "demo"],
        )


def generate_synthetic_portfolio(seed: int = 42, portfolio_id: str = "synthetic-portfolio") -> Portfolio:
    """Convenience function: build a synthetic portfolio from a seed."""
    return SyntheticPortfolioGenerator(seed=seed).portfolio(
        portfolio_id=portfolio_id or "synthetic-portfolio",
    )