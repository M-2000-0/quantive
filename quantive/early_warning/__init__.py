"""Sovereign Early Warning System.

Layer 5: Detects debt crises, liquidity stress, rating downgrade risk,
fiscal instability, revenue collapse and pension stress months or years
earlier using leading indicators, scenario analysis, assumption tracking
and trend analysis.
"""
from __future__ import annotations

from quantive.early_warning.models import (
    IndicatorConfig,
    WarningDetail,
    EarlyWarningResult,
    EarlyWarningRequest,
    ScenarioProjection,
)
from quantive.early_warning.scenario_analysis import (
    ScenarioAnalyzer,
    TrendAnalyzer,
    AssumptionTracker,
    default_scenario_analyzer,
    default_trend_analyzer,
    default_assumption_tracker,
)
from quantive.early_warning.engine import EarlyWarningEngine

__all__ = [
    "IndicatorConfig",
    "WarningDetail",
    "EarlyWarningResult",
    "EarlyWarningRequest",
    "ScenarioProjection",
    "ScenarioAnalyzer",
    "TrendAnalyzer",
    "AssumptionTracker",
    "default_scenario_analyzer",
    "default_trend_analyzer",
    "default_assumption_tracker",
    "EarlyWarningEngine",
]
