"""Alert system — §58.

Alerts when risk ↑, confidence ↓, signal changes, regime shift, concentration, rebalance threshold.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from enum import Enum


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    id: str
    severity: AlertSeverity
    title: str
    message: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    metadata: dict = field(default_factory=dict)


class AlertEngine:
    """Threshold-based alerts — stateless evaluation."""

    def __init__(
        self,
        concentration_threshold: float = 0.25,
        risk_increase_pct: float = 0.2,
        confidence_floor: float = 0.5,
        rebalance_threshold: float = 0.02,
    ):
        self.concentration_threshold = concentration_threshold
        self.risk_increase_pct = risk_increase_pct
        self.confidence_floor = confidence_floor
        self.rebalance_threshold = rebalance_threshold

    def evaluate(
        self,
        *,
        concentration_hhi: float | None = None,
        risk_current: float | None = None,
        risk_previous: float | None = None,
        confidence: float | None = None,
        regime_previous: str | None = None,
        regime_current: str | None = None,
        drift_pct: float | None = None,
    ) -> list[Alert]:
        alerts: list[Alert] = []
        now = datetime.now(timezone.utc).isoformat()
        if concentration_hhi is not None and concentration_hhi > self.concentration_threshold:
            alerts.append(Alert(id=f"conc-{now}", severity=AlertSeverity.WARNING, title="Concentration risk", message=f"HHI {concentration_hhi:.2f} exceeds {self.concentration_threshold:.2f}"))
        if risk_current is not None and risk_previous is not None and risk_previous > 0:
            if (risk_current - risk_previous) / risk_previous > self.risk_increase_pct:
                alerts.append(Alert(id=f"risk-{now}", severity=AlertSeverity.WARNING, title="Risk increased", message=f"Risk {risk_previous:.2%}→{risk_current:.2%} (+{(risk_current-risk_previous)/risk_previous:.0%})"))
        if confidence is not None and confidence < self.confidence_floor:
            alerts.append(Alert(id=f"conf-{now}", severity=AlertSeverity.WARNING, title="Low model confidence", message=f"Confidence {confidence:.0%} below floor {self.confidence_floor:.0%}"))
        if regime_previous and regime_current and regime_previous != regime_current:
            alerts.append(Alert(id=f"regime-{now}", severity=AlertSeverity.INFO, title="Regime shift", message=f"{regime_previous} → {regime_current}"))
        if drift_pct is not None and abs(drift_pct) > self.rebalance_threshold:
            alerts.append(Alert(id=f"rebal-{now}", severity=AlertSeverity.INFO, title="Rebalance threshold reached", message=f"Drift {drift_pct:.1%} exceeds {self.rebalance_threshold:.1%}"))
        return alerts
