"""Early Warning Detection Engine (Layer 5).

The detection engine queries the assumption registry for current values and
bias directions, computes leading indicators, and triggers warnings months or
years before crises manifest.

Key functions:
- Compute leading indicators for each risk type using mathematical models
- Query assumption registry bias tracking to adjust warning thresholds
- Run scenario analysis to project forward multiple futures
- Detect debt crises, liquidity stress, rating downgrade risk,
  fiscal instability, revenue collapse, and pension stress
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from quantive.early_warning.models import (
    EarlyWarningRequest,
    EarlyWarningResult,
    IndicatorConfig,
    ScenarioProjection,
    WarningDetail,
)
from quantive.early_warning.indicators import (
    # Debt Crisis
    DEBT_TO_GDP_CONFIG,
    DEBT_SERVICE_CONFIG,
    EXTERNAL_FINANCING_NEEDS_CONFIG,
    # Liquidity Stress
    LIQUIDITY_COVERAGE_RATIO_CONFIG,
    FOREIGN_RESERVE_COVERAGE_CONFIG,
    # Rating Downgrade Risk
    CDS_SPREAD_CONFIG,
    EXTERNAL_DEBT_RATIO_CONFIG,
    # Fiscal Instability
    PRIMARY_BALANCE_CONFIG,
    TAX_REVENUE_Volatility_CONFIG,
    # Revenue Collapse
    REVENUE_VOLATILITY_CONFIG,
    TAX_BASE_CONTRACTION_CONFIG,
    # Pension Stress
    PENSION_FUNDING_RATIO_CONFIG,
    PENSION_DEMOGRAPHIC_RATIO_CONFIG,
)
from quantive.early_warning.scenario_analysis import (
    AssumptionTracker,
    ScenarioAnalyzer,
    TrendAnalyzer,
    default_assumption_tracker,
    default_scenario_analyzer,
    default_trend_analyzer,
)


# ── Global Indicator Registry ────────────────────────────────────────────

INDICATOR_REGISTRY: Dict[str, IndicatorConfig] = {
    # Debt Crisis Indicators
    "debt_to_gdp": DEBT_TO_GDP_CONFIG,
    "debt_service": DEBT_SERVICE_CONFIG,
    "external_financing_needs": EXTERNAL_FINANCING_NEEDS_CONFIG,
    # Liquidity Stress Indicators
    "liquidity_coverage": LIQUIDITY_COVERAGE_RATIO_CONFIG,
    "foreign_reserve_coverage": FOREIGN_RESERVE_COVERAGE_CONFIG,
    # Rating Downgrade Risk Indicators
    "cds_spread": CDS_SPREAD_CONFIG,
    "external_debt_ratio": EXTERNAL_DEBT_RATIO_CONFIG,
    # Fiscal Instability Indicators
    "primary_balance": PRIMARY_BALANCE_CONFIG,
    "tax_revenue_volatility": TAX_REVENUE_Volatility_CONFIG,
    # Revenue Collapse Indicators
    "revenue_volatility": REVENUE_VOLATILITY_CONFIG,
    "tax_base_contraction": TAX_BASE_CONTRACTION_CONFIG,
    # Pension Stress Indicators
    "pension_funding_ratio": PENSION_FUNDING_RATIO_CONFIG,
    "pension_demographic_ratio": PENSION_DEMOGRAPHIC_RATIO_CONFIG,
}


# ── Engine ───────────────────────────────────────────────────────────────

class EarlyWarningEngine:
    """Core detection engine for sovereign early warning signals."""

    def __init__(
        self,
        trend_analyzer: Optional[TrendAnalyzer] = None,
        scenario_analyzer: Optional[ScenarioAnalyzer] = None,
        assumption_tracker: Optional[AssumptionTracker] = None,
    ) -> None:
        self.trend_analyzer = trend_analyzer or default_trend_analyzer
        self.scenario_analyzer = scenario_analyzer or default_scenario_analyzer
        self.assumption_tracker = assumption_tracker or default_assumption_tracker

    def detect(
        self,
        entity_id: str,
        indicator_values: Dict[str, float],
        assumptions: Optional[Dict[str, dict]] = None,
        request: Optional[EarlyWarningRequest] = None,
    ) -> EarlyWarningResult:
        """Run full early warning detection for an entity.

        Args:
            entity_id: Government/entity identifier
            indicator_values: Dict of indicator_name -> current_value
            assumptions: Optional dict of assumption data from registry
            request: Optional EarlyWarningRequest with configuration

        Returns:
            EarlyWarningResult with all detected warnings and summary
        """
        request = request or EarlyWarningRequest()
        horizon = request.horizon_months or 12

        # Update bias directions from assumption registry
        if assumptions is not None:
            self.assumption_tracker.update_bias_from_registry(entity_id, assumptions)

        warnings: List[WarningDetail] = []

        # Detect warnings for each risk category
        for indicator_name, config in INDICATOR_REGISTRY.items():
            if indicator_name not in indicator_values:
                continue

            current_value = indicator_values[indicator_name]
            bias_direction = self.assumption_tracker.get_bias_direction(
                entity_id, indicator_name
            )

            # Adjust thresholds based on bias
            adjusted_threshold, adjusted_critical = self.assumption_tracker.adjust_threshold(
                config.threshold,
                config.critical_threshold,
                bias_direction,
                config.direction,
            )

            # Check threshold crossing
            warning = self._check_indicator(
                indicator_name,
                config,
                current_value,
                adjusted_threshold,
                adjusted_critical,
                bias_direction,
            )

            if warning is not None:
                # Integrate scenario analysis
                if request.include_scenarios:
                    scenarios = self.scenario_analyzer.project_scenarios(
                        current_value,
                        config,
                        months_ahead=horizon,
                        bias_direction=bias_direction,
                    )
                    warning.months_until_crisis = self._estimate_lead_time(
                        scenarios, config, bias_direction
                    )

                warnings.append(warning)

        # Sort by severity
        severity_order = {"critical": 0, "warning": 1, "watch": 2, "normal": 3}
        warnings.sort(key=lambda w: severity_order.get(w.status, 99))

        # Compute summary
        summary = {"normal": 0, "watch": 0, "warning": 0, "critical": 0}
        for w in warnings:
            summary[w.status] = summary.get(w.status, 0) + 1

        # Compute average lead time
        lead_times = [w.months_until_crisis for w in warnings if w.months_until_crisis]
        avg_lead = round(sum(lead_times) / len(lead_times), 1) if lead_times else 0.0

        return EarlyWarningResult(
            entity_id=entity_id,
            warnings=warnings,
            summary=summary,
            total_months_lead=avg_lead,
        )

    def _check_indicator(
        self,
        indicator_name: str,
        config: IndicatorConfig,
        current_value: float,
        adjusted_threshold: float,
        adjusted_critical: float,
        bias_direction: str,
    ) -> Optional[WarningDetail]:
        """Check a single indicator for warning/critical crossing.

        Uses the ScenarioAnalyzer's check_threshold_crossing method
        with bias-adjusted thresholds.
        """
        warning = self.scenario_analyzer.check_threshold_crossing(
            current_value=current_value,
            threshold=adjusted_threshold,
            critical_threshold=adjusted_critical,
            direction=config.direction,
            bias_adjustment=config.bias_adjustment,
        )

        if warning is None:
            return None

        # Set category and indicator from the config name
        category_map = {
            "debt_to_gdp": "debt_crisis",
            "debt_service": "debt_crisis",
            "external_financing_needs": "debt_crisis",
            "liquidity_coverage": "liquidity",
            "foreign_reserve_coverage": "liquidity",
            "cds_spread": "rating",
            "external_debt_ratio": "rating",
            "primary_balance": "fiscal_instability",
            "tax_revenue_volatility": "fiscal_instability",
            "revenue_volatility": "revenue_collapse",
            "tax_base_contraction": "revenue_collapse",
            "pension_funding_ratio": "pension_stress",
            "pension_demographic_ratio": "pension_stress",
        }

        category = category_map.get(indicator_name, "unknown")

        warning.category = category
        warning.indicator = indicator_name

        # Adjust status and trend based on bias
        if bias_direction == "deteriorating":
            if warning.status in ("normal", "watch"):
                # Escalate one level
                status_order = ["normal", "watch", "warning", "critical"]
                current_idx = status_order.index(warning.status)
                if current_idx < len(status_order) - 1:
                    warning.status = status_order[current_idx + 1]
            if warning.trend == "stable":
                warning.trend = "deteriorating"
        elif bias_direction == "improving":
            if warning.status in ("warning", "critical"):
                # De-escalate one level
                status_order = ["normal", "watch", "warning", "critical"]
                current_idx = status_order.index(warning.status)
                if current_idx > 0:
                    warning.status = status_order[current_idx - 1]
            if warning.trend == "stable":
                warning.trend = "improving"

        # Set description if not already set
        if not warning.description:
            warning.description = self._generate_description(
                current_value,
                config.threshold,
                config.critical_threshold,
                config.direction,
                warning.status,
            )

        return warning

    def _estimate_lead_time(
        self,
        scenarios: List[ScenarioProjection],
        config: IndicatorConfig,
        bias_direction: str,
    ) -> Optional[float]:
        """Estimate months until crisis based on scenario projections.

        Returns the minimum months until crisis across all scenarios,
        or None if no crisis projected.
        """
        lead_times: List[float] = []

        for scenario in scenarios:
            projected = scenario.projected_values
            critical = config.critical_threshold
            threshold = config.threshold
            direction = config.direction

            # Find when projected value crosses critical threshold
            for month in sorted(projected.keys()):
                val = projected[month]
                if direction == "above_danger" and val >= critical:
                    lead_times.append(float(month))
                    break
                if direction == "below_danger" and val <= critical:
                    lead_times.append(float(month))
                    break

        if not lead_times:
            # Check if currently already past critical
            current = scenarios[0].current_value if scenarios else 0
            if config.direction == "above_danger" and current >= critical:
                return 0.0
            if config.direction == "below_danger" and current <= critical:
                return 0.0

        return min(lead_times) if lead_times else None

    def _generate_description(
        self,
        current_value: float,
        threshold: float,
        critical_threshold: float,
        direction: str,
        status: str,
        unit: str = "%",
    ) -> str:
        """Generate human-readable warning description."""
        if status == "critical":
            return (
                f"CRITICAL: {current_value:.1f}{unit} "
                f"exceeds critical threshold of {critical_threshold:.1f}{unit}. "
                f"Immediate action required."
            )
        elif status == "warning":
            proximity = (
                (current_value / threshold) * 100
                if direction == "above_danger"
                else (threshold / current_value) * 100
            )
            return (
                f"WARNING: {current_value:.1f}{unit} "
                f"approaching threshold of {threshold:.1f}{unit} "
                f"({proximity:.1f}% proximity). "
                f"Monitor closely and prepare mitigation measures."
            )
        elif status == "watch":
            proximity = (
                (current_value / threshold) * 100
                if direction == "above_danger"
                else (threshold / current_value) * 100
            )
            return (
                f"WATCH: {current_value:.1f}{unit} "
                f"{'approaching' if direction == 'above_danger' else 'below'} "
                f"threshold of {threshold:.1f}{unit} "
                f"({proximity:.1f}% proximity). "
                f"Early indicators suggest potential escalation."
            )
        else:
            return (
                f"NORMAL: {current_value:.1f}{unit} "
                f"{'below' if direction == 'above_danger' else 'above'} "
                f"threshold of {threshold:.1f}{unit}. "
                f"Continue monitoring standard indicators."
            )

    def run_full_detection(
        self,
        entity_id: str,
        db_session: Any,
        horizon_months: int = 12,
    ) -> EarlyWarningResult:
        """Run full detection using values from database/assumption registry.

        Args:
            entity_id: Government/entity identifier
            db_session: Database session for querying assumptions
            horizon_months: Analysis horizon in months

        Returns:
            EarlyWarningResult with all detected warnings
        """
        # Fetch current indicator values from assumption registry
        indicator_values = self._fetch_indicator_values(entity_id, db_session)

        # Fetch assumptions for bias tracking
        assumptions = self._fetch_assumptions(entity_id, db_session)

        request = EarlyWarningRequest(
            entity_id=entity_id,
            include_scenarios=True,
            horizon_months=horizon_months,
        )

        return self.detect(
            entity_id=entity_id,
            indicator_values=indicator_values,
            assumptions=assumptions,
            request=request,
        )

    def _fetch_indicator_values(
        self, entity_id: str, db_session: Any
    ) -> Dict[str, float]:
        """Fetch current indicator values from the assumption registry.

        In a full implementation, this would query the database for
        the latest values of each early warning indicator.
        """
        # Placeholder: return mock values for demonstration
        # In production, this queries the institutional_memory_assumptions table
        return {
            "debt_to_gdp": 62.5,
            "debt_service": 21.3,
            "external_financing_needs": 16.2,
            "liquidity_coverage": 14.8,
            "foreign_reserve_coverage": 1.4,
            "cds_spread": 295.0,
            "external_debt_ratio": 38.0,
            "primary_balance": -2.1,
            "tax_revenue_volatility": 0.14,
            "revenue_volatility": 0.08,
            "tax_base_contraction": -2.5,
            "pension_funding_ratio": 78.5,
            "pension_demographic_ratio": 0.28,
        }

    def _fetch_assumptions(
        self, entity_id: str, db_session: Any
    ) -> Dict[str, dict]:
        """Fetch assumptions from the registry for bias tracking.

        In a full implementation, this would query the institutional_memory
        table for versioned assumptions with bias directions.
        """
        # Placeholder: return mock assumptions with bias directions
        return {
            "debt_to_gdp": {"bias_direction": "deteriorating"},
            "debt_service": {"bias_direction": "stable"},
            "cds_spread": {"bias_direction": "deteriorating"},
            "pension_funding_ratio": {"bias_direction": "deteriorating"},
            "primary_balance": {"bias_direction": "improving"},
        }