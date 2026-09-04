"""Leading indicators for sovereign early warning detection.

Each indicator is designed to detect specific risk types MONTHS or YEARS
before the actual crisis manifests. Indicators use trend analysis and
scenario projections to provide early warnings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


@dataclass
class IndicatorConfig:
    """Configuration for an early warning indicator."""
    name: str
    description: str
    threshold: float  # Warning threshold
    critical_threshold: float  # Critical threshold
    direction: str  # 'above_danger' or 'below_danger'
    unit: str
    lookahead_months: int  # How far ahead we can detect
    bias_adjustment: float = 0.0  # Bias direction adjustment factor


# ── Debt Crisis Indicators ────────────────────────────────────────────

DEBT_TO_GDP_CONFIG = IndicatorConfig(
    name="Debt-to-GDP Ratio",
    description="Total government debt as percentage of GDP. Elevated levels indicate fiscal unsustainability.",
    threshold=60.0,
    critical_threshold=90.0,
    direction="above_danger",
    unit="%",
    lookahead_months=12,
    bias_adjustment=0.5,
)

DEBT_SERVICE_CONFIG = IndicatorConfig(
    name="Debt Service Ratio",
    description="Interest + Principal payments as percentage of revenue. Measures ability to service debt from income.",
    threshold=25.0,
    critical_threshold=35.0,
    direction="above_danger",
    unit="%",
    lookahead_months=6,
    bias_adjustment=0.3,
)

EXTERNAL_FINANCING_NEEDS_CONFIG = IndicatorConfig(
    name="External Financing Needs",
    description="Gross external financing required as percentage of GDP. High values indicate dependence on market access.",
    threshold=15.0,
    critical_threshold=25.0,
    direction="above_danger",
    unit="%",
    lookahead_months=9,
    bias_adjustment=0.4,
)


# ── Liquidity Stress Indicators ───────────────────────────────────────

LIQUIDITY_COVERAGE_RATIO_CONFIG = IndicatorConfig(
    name="Liquidity Coverage Ratio",
    description="Liquid assets as percentage of short-term debt. Below 15% indicates liquidity stress.",
    threshold=15.0,
    critical_threshold=10.0,
    direction="below_danger",
    unit="%",
    lookahead_months=3,
    bias_adjustment=-0.3,
)

FOREIGN_RESERVE_COVERAGE_CONFIG = IndicatorConfig(
    name="Foreign Reserve Coverage",
    description="Reserves as multiple of short-term external debt. Below 1.5x indicates insufficient buffer.",
    threshold=1.5,
    critical_threshold=1.0,
    direction="below_danger",
    unit="x",
    lookahead_months=4,
    bias_adjustment=-0.2,
)


# ── Rating Downgrade Risk Indicators ──────────────────────────────────

CDS_SPREAD_CONFIG = IndicatorConfig(
    name="Sovereign CDS Spread",
    description="5-year Credit Default Swap spread in basis points. Elevated spreads indicate market perceived downgrade risk.",
    threshold=250.0,
    critical_threshold=500.0,
    direction="above_danger",
    unit="bps",
    lookahead_months=6,
    bias_adjustment=0.5,
)

EXTERNAL_DEBT_RATIO_CONFIG = IndicatorConfig(
    name="External Debt Ratio",
    description="External debt as percentage of total debt. High foreign currency exposure increases downgrade risk.",
    threshold=40.0,
    critical_threshold=60.0,
    direction="above_danger",
    unit="%",
    lookahead_months=8,
    bias_adjustment=0.3,
)


# ── Fiscal Instability Indicators ────────────────────────────────────

PRIMARY_BALANCE_CONFIG = IndicatorConfig(
    name="Primary Balance",
    description="Government balance excluding interest payments. Negative primary balance indicates structural fiscal instability.",
    threshold=-3.0,
    critical_threshold=-6.0,
    direction="below_danger",
    unit="%GDP",
    lookahead_months=9,
    bias_adjustment=-0.4,
)

TAX_REVENUE_Volatility_CONFIG = IndicatorConfig(
    name="Tax Revenue Volatility",
    description="Coefficient of variation of tax revenue over 5-year period. High volatility indicates fiscal unpredictability.",
    threshold=0.15,
    critical_threshold=0.25,
    direction="above_danger",
    unit="cv",
    lookahead_months=12,
    bias_adjustment=0.3,
)


# ── Revenue Collapse Indicators ──────────────────────────────────────

REVENUE_VOLATILITY_CONFIG = IndicatorConfig(
    name="Revenue Volatility",
    description="Coefficient of variation of total revenue over 3-year period. Rising volatility signals collapse risk.",
    threshold=0.10,
    critical_threshold=0.20,
    direction="above_danger",
    unit="cv",
    lookahead_months=6,
    bias_adjustment=0.3,
)

TAX_BASE_CONTRACTION_CONFIG = IndicatorConfig(
    name="Tax Base Contraction",
    description="Year-over-year decline in taxable economic base. Indicates revenue collapse trajectory.",
    threshold=-5.0,
    critical_threshold=-10.0,
    direction="below_danger",
    unit="%",
    lookahead_months=3,
    bias_adjustment=-0.3,
)


# ── Pension Stress Indicators ────────────────────────────────────────

PENSION_FUNDING_RATIO_CONFIG = IndicatorConfig(
    name="Pension Funding Ratio",
    description="Pension assets as percentage of liabilities. Below 80% indicates stress.",
    threshold=80.0,
    critical_threshold=60.0,
    direction="below_danger",
    unit="%",
    lookahead_months=12,
    bias_adjustment=-0.3,
)

PENSION_DEMOGRAPHIC_RATIO_CONFIG = IndicatorConfig(
    name="Pension-to-Worker Ratio",
    description="Number of pensioners per active worker. Rising ratio indicates aging burden.",
    threshold=0.25,
    critical_threshold=0.35,
    direction="above_danger",
    unit="ratio",
    lookahead_months=24,
    bias_adjustment=-0.2,
)