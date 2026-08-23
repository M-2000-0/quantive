"""Synthetic demonstration dataset.

Generates a realistic synthetic sovereign debt candidate-issuance universe.
All data is synthetic — no real or confidential government data is used.

The portfolio represents a *candidate issuance universe*: each instrument is a
line the government could issue (or refinance into) with a given nominal size,
coupon structure, currency, maturity and market absorption capacity.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Optional

import numpy as np

from quantive.models.enums import Currency, RateType
from quantive.models.instruments import DebtInstrument, Portfolio, make_portfolio

TODAY: date = date(2026, 8, 18)

# -- Reporting-currency (USD) spot yield curve by tenor (decimal) ------------
USD_YIELD_CURVE: Dict[int, float] = {
    1: 0.0380, 2: 0.0400, 3: 0.0410, 4: 0.0418, 5: 0.0420,
    6: 0.0425, 7: 0.0430, 8: 0.0433, 9: 0.0435, 10: 0.0435,
    12: 0.0440, 15: 0.0445, 20: 0.0450, 25: 0.0455, 30: 0.0460,
}

# -- Credit / term spreads over the USD curve per currency (decimal) ---------
CURRENCY_SPREADS: Dict[Currency, float] = {
    Currency.USD: 0.0000,
    Currency.EUR: 0.0010,
    Currency.GBP: 0.0020,
    Currency.JPY: 0.0030,
    Currency.CHF: 0.0015,
    Currency.CAD: 0.0040,
    Currency.AUD: 0.0060,
    Currency.BRL: 0.0250,
}

# -- Annual FX volatility (std dev of log move) per currency ------------------
FX_VOLATILITY: Dict[Currency, float] = {
    Currency.USD: 0.00,
    Currency.EUR: 0.08,
    Currency.GBP: 0.10,
    Currency.JPY: 0.11,
    Currency.CHF: 0.09,
    Currency.CAD: 0.07,
    Currency.AUD: 0.12,
    Currency.BRL: 0.18,
}

# -- USD-per-currency spot rates (1 EUR == 1.08 USD) --------------------------
BASE_FX: Dict[Currency, float] = {
    Currency.USD: 1.0,
    Currency.EUR: 1.08,
    Currency.GBP: 1.27,
    Currency.JPY: 0.0067,
    Currency.CHF: 1.12,
    Currency.CAD: 0.73,
    Currency.AUD: 0.65,
    Currency.BRL: 0.18,
}

# -- Floating benchmark (SOFR) base rate --------------------------------------
SOFR_BASE: float = 0.0450

TENORS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30]


def curve_rate(tenor: int, currency: Currency = Currency.USD) -> float:
    """Interpolated yield for a tenor (linear between anchor points)."""
    years = list(USD_YIELD_CURVE.keys())
    if tenor <= years[0]:
        return USD_YIELD_CURVE[years[0]] + CURRENCY_SPREADS[currency]
    if tenor >= years[-1]:
        return USD_YIELD_CURVE[years[-1]] + CURRENCY_SPREADS[currency]
    import bisect

    i = bisect.bisect_left(years, tenor)
    lo, hi = years[i - 1], years[i]
    t = (tenor - lo) / (hi - lo)
    rate = USD_YIELD_CURVE[lo] * (1 - t) + USD_YIELD_CURVE[hi] * t
    return rate + CURRENCY_SPREADS[currency]


def _future_date(tenor_years: int, jitter_days: int = 0) -> date:
    return TODAY + timedelta(days=int(tenor_years * 365.25) + jitter_days)


class SyntheticPortfolioGenerator:
    """Deterministic generator for the synthetic demonstration portfolio.

    All random choices are driven by a supplied seed, so the exact same
    portfolio is reproduced on every call.
    """

    def __init__(self, seed: int = 42):
        self._rng = np.random.default_rng(seed)

    def _jitter(self, magnitude: float) -> float:
        return float(self._rng.normal(0.0, magnitude))

    def generate(self, n_usd_fixed: int = 20, n_usd_floating: int = 8,
                 foreign_counts: Optional[Dict[Currency, int]] = None,
                 n_callable: int = 5) -> List[DebtInstrument]:
        """Generate the candidate issuance universe."""
        foreign_counts = foreign_counts or {
            Currency.EUR: 8, Currency.GBP: 6, Currency.JPY: 5, Currency.CHF: 4,
            Currency.CAD: 5, Currency.AUD: 4, Currency.BRL: 4,
        }
        instruments: List[DebtInstrument] = []
        counter: Dict[str, int] = {}

        def _next_id(prefix: str) -> str:
            counter[prefix] = counter.get(prefix, 0) + 1
            return f"{prefix}-{counter[prefix]:02d}"

        def _add(currency: Currency, rate_type: RateType, tenor: int,
                 coupon: float, capacity: float, liquid: float,
                 callable_: bool = False, jitter_days: int = 0) -> None:
            ccy = currency.value.lower()
            rty = "fix" if rate_type == RateType.FIXED else "flt"
            inst_id = _next_id(f"{ccy}-{rty}")
            benchmark = "SOFR" if rate_type == RateType.FLOATING else None
            instruments.append(
                DebtInstrument(
                    id=inst_id,
                    name=f"{currency.value} {'Fixed' if rate_type == RateType.FIXED else 'Floating'} {tenor}Y #{counter[ccy + '-fix' if rate_type == RateType.FIXED else ccy + '-flt']}",
                    currency=currency,
                    principal=capacity,
                    coupon=round(coupon, 4),
                    rate_type=rate_type,
                    maturity_date=_future_date(tenor, jitter_days),
                    issue_date=TODAY - timedelta(days=int(self._rng.integers(0, 400))),
                    callable=callable_,
                    liquidity=round(liquid, 3),
                    benchmark=benchmark,
                    market_capacity=round(capacity, 3),
                )
            )

        # ---- USD fixed -------------------------------------------------------
        for i in range(n_usd_fixed):
            tenor = TENORS[i % len(TENORS)]
            base = curve_rate(tenor, Currency.USD)
            coupon = base + self._jitter(0.0008)
            capacity = float(self._rng.uniform(4_000, 9_000))
            liquid = float(self._rng.uniform(0.55, 0.95))
            callable_ = i < n_callable
            _add(Currency.USD, RateType.FIXED, tenor, coupon, capacity, liquid, callable_)

        # ---- USD floating ----------------------------------------------------
        for i in range(n_usd_floating):
            tenor = int(self._rng.choice([2, 3, 5, 7, 10]))
            spread = float(self._rng.uniform(0.0015, 0.0060))
            capacity = float(self._rng.uniform(3_000, 6_000))
            liquid = float(self._rng.uniform(0.6, 0.9))
            _add(Currency.USD, RateType.FLOATING, tenor, spread, capacity, liquid)

        # ---- Foreign currencies ---------------------------------------------
        for currency, count in foreign_counts.items():
            n_floating = 1 if count >= 5 else 0
            n_fixed = count - n_floating
            for i in range(n_fixed):
                tenor = TENORS[i % len(TENORS)]
                base = curve_rate(tenor, currency)
                coupon = base + self._jitter(0.0010)
                capacity = float(self._rng.uniform(1_500, 4_500))
                liquid = float(self._rng.uniform(0.4, 0.85))
                _add(currency, RateType.FIXED, tenor, coupon, capacity, liquid)
            for i in range(n_floating):
                tenor = int(self._rng.choice([3, 5, 7]))
                spread = float(self._rng.uniform(0.0020, 0.0080))
                capacity = float(self._rng.uniform(1_500, 3_500))
                liquid = float(self._rng.uniform(0.4, 0.8))
                _add(currency, RateType.FLOATING, tenor, spread, capacity, liquid)

        return instruments

    def portfolio(self, portfolio_id: str = "synthetic-demo",
                  name: str = "Synthetic Demonstration Portfolio",
                  reference_currency: Currency = Currency.USD,
                  **kwargs) -> Portfolio:
        instruments = self.generate(**kwargs)
        return make_portfolio(
            portfolio_id=portfolio_id,
            name=name,
            instruments=instruments,
            reference_currency=reference_currency,
            description="Synthetic Demonstration Portfolio — candidate issuance universe. "
                        "Sovereign debt instruments with multiple currencies, maturities and "
                        "rate structures. Synthetic data, NOT real government data.",
            tags=["synthetic", "demonstration", "sovereign-debt"],
        )


def generate_synthetic_portfolio(seed: int = 42, **kwargs) -> Portfolio:
    """Convenience wrapper around :class:`SyntheticPortfolioGenerator`."""
    return SyntheticPortfolioGenerator(seed=seed).portfolio(**kwargs)


def base_fx_rates() -> Dict[str, float]:
    return {c.value: v for c, v in BASE_FX.items()}


def fx_volatilities() -> Dict[str, float]:
    return {c.value: v for c, v in FX_VOLATILITY.items()}