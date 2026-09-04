"""Scenario analysis, trend analysis, and assumption tracking for Layer 5.

Provides:
- ScenarioAnalyzer: "what-if" analysis with multiple future paths
- TrendAnalyzer: statistical trend detection and projection
- AssumptionTracker: tracks bias directions from the assumption registry
"""

from __future__ import annotations

import math
from collections import deque
from datetime import datetime, timedelta
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np

from quantive.early_warning.models import (
    EarlyWarningResult,
    EarlyWarningRequest,
    IndicatorConfig,
    ScenarioProjection,
    WarningDetail,
)


# ── Bias Direction Enums ──────────────────────────────────────────────────

BIAS_DIRECTIONS = {"improving": "below_danger", "deteriorating": "above_danger", "stable": "none"}


# ── TrendAnalyzer ────────────────────────────────────────────────────────

class TrendAnalyzer:
    """Analyzes trend direction and strength from time-series data."""

    def __init__(self, window_size: int = 6) -> None:
        self.window_size = window_size

    def compute_trend(
        self, values: List[float], dates: Optional[List[datetime]] = None
    ) -> Tuple[str, float]:
        """Compute trend direction and strength.

        Returns:
            (direction, strength) where direction is one of:
            'improving', 'stable', 'deteriorating'
            and strength is a float in [0, 1]
        """
        if len(values) < 2:
            return "stable", 0.0

        values = np.array(values)
        n = len(values)

        # Linear regression: y = mx + b
        x = np.arange(n)
        m, b = np.polyfit(x, values, 1)

        # Overall change ratio
        change_ratio = (values[-1] - values[0]) / max(abs(values[0]), 1e-8)

        # Acceleration (second difference)
        if n >= 3:
            accel = values[-1] - 2 * values[-2] + values[-3]
        else:
            accel = 0.0

        # Determine direction
        if abs(change_ratio) < 0.02:
            direction = "stable"
            strength = min(abs(accel) / max(abs(values).mean(), 1e-8), 1.0) * 0.3
        elif change_ratio < 0:
            # Values decreasing - for most indicators this is "improving"
            direction = "improving"
            strength = min(abs(change_ratio), 1.0)
        else:
            # Values increasing - for most indicators this is "deteriorating"
            direction = "deteriorating"
            strength = min(abs(change_ratio), 1.0)

        # Adjust strength based on acceleration
        if abs(accel) > 0.01:
            strength = min(strength + 0.2, 1.0)

        # If we have dates and can compute month-over-month changes
        if dates and len(dates) >= 2:
            monthly_changes = []
            for i in range(1, len(values)):
                if values[i-1] != 0:
                    monthly_changes.append((values[i] - values[i-1]) / abs(values[i-1]))
            if monthly_changes:
                avg_monthly_change = sum(monthly_changes) / len(monthly_changes)
                strength = min(abs(avg_monthly_change) * 12, 1.0)  # annualized

        return direction, round(strength, 3)

    def project_value(
        self,
        current: float,
        direction: str,
        strength: float,
        months_ahead: int,
    ) -> float:
        """Project a value forward by months_ahead months based on trend.

        Uses a simple linear projection with strength modulation.
        """
        if direction == "stable":
            return current

        # Determine rate of change per month
        if direction == "improving":
            rate = -strength * 0.1  # improving at ~10% of strength per month
        else:  # deteriorating
            rate = strength * 0.1  # deteriorating at ~10% of strength per month

        # Linear projection with acceleration consideration
        projected = current + rate * months_ahead
        return round(projected, 2)


# ── ScenarioAnalyzer ─────────────────────────────────────────────────────

class ScenarioAnalyzer:
    """Performs "what-if" scenario analysis for early warning indicators."""

    def __init__(self, trend_analyzer: Optional[TrendAnalyzer] = None) -> None:
        self.trend_analyzer = trend_analyzer or TrendAnalyzer()

    def project_scenarios(
        self,
        current_value: float,
        indicator_config: IndicatorConfig,
        months_ahead: int = 12,
        bias_direction: str = "stable",
    ) -> List[ScenarioProjection]:
        """Project indicator values across multiple scenarios.

        Creates baseline, optimistic, and pessimistic scenarios based on:
        - Current trend direction
        - Bias direction from assumption registry
        - Indicator-specific volatility
        """
        bias_adjustment = 0.0
        if bias_direction == "deteriorating":
            bias_adjustment = indicator_config.bias_adjustment
        elif bias_direction == "improving":
            bias_adjustment = -abs(indicator_config.bias_adjustment)

        # Baseline: current trend continuation
        baseline_proj = self._project_linear(
            current_value, months_ahead, bias_adjustment=0.0
        )

        # Optimistic: improving bias + favorable trend
        optimistic_proj = self._project_linear(
            current_value, months_ahead, bias_adjustment=-abs(indicator_config.bias_adjustment)
        )

        # Pessimistic: deteriorating bias + adverse trend
        pessimistic_proj = self._project_linear(
            current_value, months_ahead, bias_adjustment=abs(indicator_config.bias_adjustment)
        )

        return [
            ScenarioProjection(
                indicator_name=indicator_config.name,
                current_value=current_value,
                projected_values=self._project_monthly(
                    current_value, months_ahead, bias_adjustment=0.0
                ),
                scenario_name="baseline",
                confidence=0.8,
            ),
            ScenarioProjection(
                indicator_name=indicator_config.name,
                current_value=current_value,
                projected_values=self._project_monthly(
                    current_value, months_ahead, bias_adjustment=-abs(indicator_config.bias_adjustment)
                ),
                scenario_name="optimistic",
                confidence=0.6,
            ),
            ScenarioProjection(
                indicator_name=indicator_config.name,
                current_value=current_value,
                projected_values=self._project_monthly(
                    current_value, months_ahead, bias_adjustment=abs(indicator_config.bias_adjustment)
                ),
                scenario_name="pessimistic",
                confidence=0.6,
            ),
        ]

    def _project_linear(
        self, current: float, months: int, bias_adjustment: float = 0.0
    ) -> float:
        """Linear projection with optional bias adjustment."""
        # Base rate: 1% of current value per month as baseline
        rate = current * 0.01
        projected = current + rate * months + bias_adjustment
        return round(max(projected, 0), 2)

    def _project_monthly(
        self, current: float, months: int, bias_adjustment: float = 0.0
    ) -> Dict[int, float]:
        """Project monthly values for the given horizon."""
        projections: Dict[int, float] = {}
        for m in range(1, months + 1):
            projections[m] = self._project_linear(current, m, bias_adjustment)
        return projections

    def check_threshold_crossing(
        self,
        current_value: float,
        threshold: float,
        critical_threshold: float,
        direction: str,
        bias_adjustment: float = 0.0,
    ) -> Optional[WarningDetail]:
        """Check if an indicator crosses warning/critical thresholds.

        Returns a WarningDetail if threshold is crossed, None otherwise.
        """
        # Apply bias adjustment to thresholds
        if direction == "above_danger":
            adjusted_threshold = threshold + bias_adjustment
            adjusted_critical = critical_threshold + bias_adjustment
            current_effective = current_value
        else:  # below_danger
            adjusted_threshold = threshold - abs(bias_adjustment)
            adjusted_critical = critical_threshold - abs(bias_adjustment)
            current_effective = current_value

        # Check warning threshold
        warning_crossed = self._crossed(
            current_effective, adjusted_threshold, direction
        )
        # Check critical threshold
        critical_crossed = self._crossed(
            current_effective, adjusted_critical, direction
        )

        if critical_crossed:
            severity = "critical"
        elif warning_crossed:
            severity = "warning"
        else:
            return None

        # Determine trend direction from bias
        if bias_adjustment > 0 and direction == "above_danger":
            trend = "deteriorating"
        elif bias_adjustment < 0 and direction == "below_danger":
            trend = "deteriorating"
        elif bias_adjustment > 0 and direction == "below_danger":
            trend = "improving"
        elif bias_adjustment < 0 and direction == "above_danger":
            trend = "improving"
        else:
            trend = "stable"

        # Estimate months until crisis
        months_until = self._estimate_months_until_crisis(
            current_value, adjusted_critical, direction, strength=0.5
        )

        return WarningDetail(
            name="Early Warning Signal",
            category="",  # will be set by caller
            indicator="",  # will be set by caller
            current_value=current_value,
            threshold=threshold,
            unit="",
            direction=direction,
            status=severity,
            trend=trend,
            description=self._generate_description(
                current_value, threshold, critical_threshold, direction, severity
            ),
            bias_adjustment=bias_adjustment,
            months_until_crisis=months_until,
        )

    @staticmethod
    def _generate_description(
        current_value: float,
        threshold: float,
        critical_threshold: float,
        direction: str,
        status: str,
        unit: str = "",
    ) -> str:
        """Generate a human-readable description for a crossed threshold."""
        if status == "critical":
            return (
                f"CRITICAL: {current_value:.1f}{unit} "
                f"exceeds critical threshold of {critical_threshold:.1f}{unit}. "
                f"Immediate action required."
            )
        proximity = (
            (current_value / threshold) * 100
            if direction == "above_danger"
            else (threshold / current_value) * 100
        )
        return (
            f"{status.upper()}: {current_value:.1f}{unit} at "
            f"{proximity:.1f}% of the {threshold:.1f}{unit} threshold. "
            f"Monitor closely and prepare mitigation measures."
        )

    @staticmethod
    def _crossed(value: float, threshold: float, direction: str) -> bool:
        """Check if value has crossed threshold in the given direction."""
        if direction == "above_danger":
            return value >= threshold
        else:  # below_danger
            return value <= threshold

    @staticmethod
    def _estimate_months_until_crisis(
        current: float,
        critical_threshold: float,
        direction: str,
        strength: float = 0.5,
    ) -> Optional[float]:
        """Estimate months until reaching critical threshold.

        Uses linear projection based on current rate of change.
        """
        if direction == "above_danger" and current <= critical_threshold:
            return 0.0
        if direction == "below_danger" and current >= critical_threshold:
            return 0.0

        # Rate of change per month (strength * scale)
        if direction == "above_danger":
            # Moving away from threshold upward
            if critical_threshold <= current:
                return None  # already past critical
            # Estimate based on strength
            gap = critical_threshold - current
            monthly_rate = strength * abs(current) * 0.01 if current != 0 else 1.0
            if monthly_rate > 0:
                months = gap / monthly_rate
                return max(months, 0.1)
        else:  # below_danger
            if critical_threshold >= current:
                return 0.0
            gap = current - critical_threshold
            monthly_rate = strength * abs(current) * 0.01 if current != 0 else 1.0
            if monthly_rate > 0:
                months = gap / monthly_rate
                return max(months, 0.1)

        return None


# ── AssumptionTracker ─────────────────────────────────────────────────────

class AssumptionTracker:
    """Tracks bias directions from the assumption registry for indicator adjustment.

    Integrates with the institutional memory engine to read assumption bias
    directions and adjust early warning thresholds accordingly.
    """

    BIAS_WEIGHT = 0.3  # How much bias direction affects threshold adjustment (0-1)

    def __init__(self, assumption_repo: Optional[object] = None) -> None:
        self.assumption_repo = assumption_repo
        self._bias_cache: Dict[str, str] = {}  # entity_id -> bias_direction

    def update_bias_from_registry(self, entity_id: str, assumptions: Dict[str, dict]) -> None:
        """Update bias directions from the assumption registry.

        Args:
            entity_id: The government/entity identifier
            assumptions: Dict of assumption_name -> {value, category, bias_direction, ...}
        """
        bias_directions: Dict[str, str] = {}

        for name, data in assumptions.items():
            bias_dir = data.get("bias_direction", "stable")
            if bias_dir in {"improving", "deteriorating", "stable"}:
                bias_directions[name] = bias_dir

        self._bias_cache[entity_id] = bias_directions

    def get_bias_direction(
        self, entity_id: str, assumption_name: str
    ) -> str:
        """Get the bias direction for a specific assumption.

        Returns one of: 'improving', 'deteriorating', 'stable'
        """
        cache = self._bias_cache.get(entity_id, {})
        return cache.get(assumption_name, "stable")

    def get_entity_bias_summary(self, entity_id: str) -> Dict[str, int]:
        """Get a summary of bias directions for an entity.

        Returns count of assumptions by bias direction.
        """
        cache = self._bias_cache.get(entity_id, {})
        summary: Dict[str, int] = {"improving": 0, "deteriorating": 0, "stable": 0}
        for direction in cache.values():
            if direction in summary:
                summary[direction] += 1
        return summary

    def adjust_threshold(
        self,
        threshold: float,
        critical_threshold: float,
        bias_direction: str,
        direction: str,
    ) -> Tuple[float, float]:
        """Adjust warning thresholds based on bias direction.

        Args:
            threshold: Original warning threshold
            critical_threshold: Original critical threshold
            bias_direction: 'improving', 'deteriorating', or 'stable'
            direction: 'above_danger' or 'below_danger'

        Returns:
            Adjusted (threshold, critical_threshold) tuple
        """
        if bias_direction == "stable":
            return threshold, critical_threshold

        adjustment = abs(self.BIAS_WEIGHT * threshold * 0.15)

        if bias_direction == "deteriorating":
            # Lower the threshold (warn earlier) for above_danger
            # Raise the threshold (warn later) for below_danger
            if direction == "above_danger":
                threshold = threshold - adjustment
                critical_threshold = critical_threshold - adjustment
            else:  # below_danger
                threshold = threshold + adjustment
                critical_threshold = critical_threshold + adjustment
        elif bias_direction == "improving":
            # Raise the threshold (warn later) for above_danger
            # Lower the threshold (warn earlier) for below_danger
            if direction == "above_danger":
                threshold = threshold + adjustment
                critical_threshold = critical_threshold + adjustment
            else:  # below_danger
                threshold = threshold - adjustment
                critical_threshold = critical_threshold - adjustment

        return round(threshold, 2), round(critical_threshold, 2)


# Default analyzer instances for convenience
default_trend_analyzer = TrendAnalyzer()
default_scenario_analyzer = ScenarioAnalyzer(default_trend_analyzer)
default_assumption_tracker = AssumptionTracker()