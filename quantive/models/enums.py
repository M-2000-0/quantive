"""Enumerations used across the Quantive domain model."""
from __future__ import annotations

from enum import Enum


class RateType(str, Enum):
    """Coupon structure of a debt instrument."""

    FIXED = "fixed"
    FLOATING = "floating"


class Currency(str, Enum):
    """Supported currencies.

    The reporting (base) currency of a portfolio is typically USD, but any of
    these currencies may be the base and any subset may appear as issuance
    currencies.
    """

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    CAD = "CAD"
    AUD = "AUD"
    BRL = "BRL"
    NOK = "NOK"
    SEK = "SEK"


class SolverType(str, Enum):
    """Algorithm family used by a solver.

    These are computational *capabilities*, not marketing claims. Quantive
    never assumes quantum is superior; every solver is benchmarked against the
    same objective and constraints.
    """

    CLASSICAL = "classical"
    HEURISTIC = "heuristic"
    QUANTUM_INSPIRED = "quantum_inspired"


class ExecutionBackend(str, Enum):
    """Where a solver actually executes.

    Quantive explicitly distinguishes between real quantum hardware, simulators
    and classical CPU execution. No fabricated quantum performance is ever
    reported: a result computed on a classical CPU simulator is labelled
    SIMULATOR, and hardware results must be physically obtained.
    """

    CLASSICAL_CPU = "classical_cpu"
    SIMULATOR = "simulator"
    REAL_QUANTUM_HARDWARE = "real_quantum_hardware"


class ConstraintType(str, Enum):
    """Supported constraint families.

    ``CUSTOM`` supports user-defined linear constraints via a coefficient
    matrix referencing instrument properties.
    """

    DEBT_CAPACITY = "debt_capacity"
    INSTRUMENT_CAPACITY = "instrument_capacity"
    MIN_LIQUIDITY = "min_liquidity"
    REFINANCING_LIMIT = "refinancing_limit"
    CURRENCY_LIMIT = "currency_limit"
    FLOATING_RATE_LIMIT = "floating_rate_limit"
    MATURITY_CONCENTRATION = "maturity_concentration"
    MAX_INSTRUMENTS = "max_instruments"
    DURATION_TARGET = "duration_target"
    DURATION_BAND = "duration_band"
    CONVEXITY_TARGET = "convexity_target"
    CONVEXITY_BAND = "convexity_band"
    DV01_LIMIT = "dv01_limit"
    VAR_LIMIT = "var_limit"
    CVAR_LIMIT = "cvar_limit"
    MAX_SINGLE_ISSUER = "max_single_issuer"
    LEVERAGE_RATIO = "leverage_ratio"
    CUSTOM = "custom"


class StrategyProfile(str, Enum):
    """Named objective profiles used to generate distinct strategies."""

    BEST_OVERALL = "best_overall"
    LOWEST_RISK = "lowest_risk"
    LOWEST_COST = "lowest_cost"
    STRESS_RESILIENT = "stress_resilient"


class JobStatus(str, Enum):
    """Lifecycle of an asynchronous optimization job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"