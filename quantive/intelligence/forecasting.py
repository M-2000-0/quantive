"""Forecasting engine — Phase 3 Decision Intelligence.

A thin, projection-based forecasting layer. Honest: produces trajectories from
base rates + shocks, never fabricates precision. Used by policy simulator and
National Digital Twin. Lightweight statistical methods only (no heavy deps).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
import math


@dataclass
class Forecast:
    name: str
    years: list[int]
    base: list[float]          # baseline trajectory
    optimistic: list[float]
    pessimistic: list[float]
    central: list[float]       # most likely
    assumptions: list[str]
    method: str


class ForecastingEngine:
    """Projects a metric over a horizon with central/optimistic/pessimistic bands."""

    def __init__(self) -> None:
        self._base_rate: dict[str, float] = {}
        self._shock: dict[str, dict[int, float]] = {}

    def set_base_rate(self, key: str, annual_rate: float) -> None:
        """Set a default annual growth/change rate for a metric."""
        self._base_rate[key] = annual_rate

    def add_shock(self, key: str, year: int, delta: float) -> None:
        """Add a one-off shock to a metric in a given year."""
        self._shock.setdefault(key, {})[year] = delta

    def project(
        self,
        name: str,
        start: float,
        years: list[int],
        base_rate: float | None = None,
        uncertainty: float = 0.3,
        method: str = "exponential",
        custom_shocks: dict[int, float] | None = None,
    ) -> Forecast:
        """Project a metric from start value over given years.

        - exponential: Y_t = Y_0 * (1+r)^t
        - linear:      Y_t = Y_0 + r*t
        uncertainty scales band width each year.
        """
        rate = base_rate if base_rate is not None else self._base_rate.get(name, 0.0)
        central: list[float] = []
        optimistic: list[float] = []
        pessimistic: list[float] = []
        base: list[float] = []

        t = 0
        for year in years:
            t += 1
            if method == "linear":
                val = start + rate * t
            else:
                val = start * math.pow(1 + rate, t)
            # apply shocks
            shocks = custom_shocks if custom_shocks is not None else self._shock.get(name, {})
            if year in shocks:
                val += shocks[year]

            band = abs(val * uncertainty) * math.sqrt(t)
            central.append(val)
            base.append(val)
            optimistic.append(val + band)
            pessimistic.append(val - band)

        return Forecast(
            name=name,
            years=years,
            base=base,
            optimistic=optimistic,
            pessimistic=pessimistic,
            central=central,
            assumptions=[
                f"base_rate={rate:.2%}" if rate else "no base rate set",
                f"uncertainty={uncertainty:.0%}",
                f"method={method}",
            ],
            method=method,
        )

    def compound(self, start: float, annual_rate: float, years: int) -> float:
        """Simple compound growth helper for policy simulators."""
        return start * math.pow(1 + annual_rate, years)
