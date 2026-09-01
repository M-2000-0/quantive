"""Early warning system — Phase 3 Decision Intelligence, Pillar 3/12.

Flags when key metrics cross stress thresholds before they become crises.
Deterministic threshold-based signals (leading/lagging), with severity levels.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable


class SignalSeverity(str, Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Threshold:
    """A threshold rule on a metric."""
    rule_id: str
    name: str
    metric_name: str
    critical_above: float | None = None
    critical_below: float | None = None
    high_above: float | None = None
    high_below: float | None = None
    elevated_above: float | None = None
    elevated_below: float | None = None
    unit: str = ""


@dataclass
class EarlyWarningSignal:
    signal_id: str
    rule: Threshold
    current_value: float
    severity: SignalSeverity
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data_source: str = ""


class EarlyWarningSystem:
    """Tracks metrics against thresholds and emits early-warning signals."""

    def __init__(self) -> None:
        self._rules: dict[str, Threshold] = {}
        self._history: dict[str, float] = {}       # metric_name -> last value
        self._signals: list[EarlyWarningSignal] = []

    def add_rule(self, rule: Threshold) -> None:
        self._rules[rule.rule_id] = rule

    def register_core_rules(self) -> None:
        """Canonical sovereign early-warning thresholds."""
        core = [
            Threshold("e-debt-gdp", "Debt-to-GDP", "debt_to_gdp", critical_above=0.90, high_above=0.70, elevated_above=0.60, unit="ratio"),
            Threshold("e-service", "Interest/revenue", "interest_to_revenue", critical_above=0.25, high_above=0.18, elevated_above=0.12, unit="ratio"),
            Threshold("e-reserves", "Months of import cover", "import_cover_months", critical_below=3.0, high_below=4.0, elevated_below=5.0, unit="months"),
            Threshold("e-deficit", "Fiscal deficit/GDP", "deficit_to_gdp", critical_above=0.08, high_above=0.06, elevated_above=0.04, unit="ratio"),
            Threshold("e-ca", "Current account/GDP", "current_account_to_gdp", critical_below=-0.08, high_below=-0.06, elevated_below=-0.04, unit="ratio"),
        ]
        for r in core:
            self.add_rule(r)

    def evaluate(self, metric_name: str, value: float, data_source: str = "") -> EarlyWarningSignal:
        """Evaluate a single metric against all matching rules."""
        severity = SignalSeverity.NORMAL
        message_suffix = ""
        matching_rule: Threshold | None = None

        for rule in self._rules.values():
            if rule.metric_name != metric_name:
                continue
            matching_rule = rule
            sev = SignalSeverity.NORMAL
            if rule.critical_above is not None and value > rule.critical_above:
                sev = SignalSeverity.CRITICAL
            elif rule.critical_below is not None and value < rule.critical_below:
                sev = SignalSeverity.CRITICAL
            elif rule.high_above is not None and value > rule.high_above:
                sev = SignalSeverity.HIGH
            elif rule.high_below is not None and value < rule.high_below:
                sev = SignalSeverity.HIGH
            elif rule.elevated_above is not None and value > rule.elevated_above:
                sev = SignalSeverity.ELEVATED
            elif rule.elevated_below is not None and value < rule.elevated_below:
                sev = SignalSeverity.ELEVATED
            severity = max(severity, sev, key=lambda s: list(SignalSeverity).index(s))

        if matching_rule:
            message_suffix = f" ({matching_rule.name})"

        signal = EarlyWarningSignal(
            signal_id=f"ews-{len(self._signals):05d}",
            rule=matching_rule or Threshold("none", metric_name, metric_name),
            current_value=value,
            severity=severity,
            message=f"{metric_name} = {value:.3f}{' ' + (matching_rule.unit if matching_rule else '')} — severity {severity.value}{message_suffix}",
            data_source=data_source,
        )
        self._history[metric_name] = value
        self._signals.append(signal)
        return signal

    def evaluate_all(self, metrics: dict[str, float], data_source: str = "") -> list[EarlyWarningSignal]:
        signals = []
        for name, value in metrics.items():
            signals.append(self.evaluate(name, value, data_source))
        return signals

    def active_alerts(self, min_severity: SignalSeverity = SignalSeverity.ELEVATED) -> list[EarlyWarningSignal]:
        """Alerts at or above a severity level."""
        order = list(SignalSeverity)
        return [s for s in self._signals if order.index(s.severity) >= order.index(min_severity)]

    def national_risk_radar(self) -> list[dict]:
        """Pillar 12: the risk radar dashboard view."""
        order = {sev: i for i, sev in enumerate(SignalSeverity)}
        latest_by_metric: dict[str, EarlyWarningSignal] = {}
        for s in self._signals:
            latest_by_metric[s.rule.metric_name] = s
        return [
            {
                "metric": s.rule.metric_name,
                "current_value": s.current_value,
                "severity": s.severity.value,
                "message": s.message,
                "rule_name": s.rule.name,
            }
            for s in latest_by_metric.values()
        ]
