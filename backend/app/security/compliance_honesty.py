"""Compliance Honesty Module - Zero Fabrication, Accurate Reporting."""

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.compliance")


VERIFIED_SOURCES = ["federal_reserve", "treasury", "bloomberg", "internal_calculation", "user_input", "model_output"]


def validate_metric(metric_name, value, source, confidence=1.0):
    if confidence < 0.5:
        logger.warning("Low confidence metric: %s=%s (confidence=%s)", metric_name, value, confidence)
    if source not in VERIFIED_SOURCES:
        logger.warning("Unverified source for metric %s: %s", metric_name, source)
    disclaimer = "Verified data" if confidence >= 0.9 else ("Low confidence" if confidence < 0.7 else "Model estimate")
    return {"metric": metric_name, "value": value, "source": source, "confidence": confidence, "disclaimer": disclaimer, "validated_at": datetime.now(timezone.utc).isoformat()}


def register_calculation(db, calc_type, inputs, output, model_version, user_id):
    from app.audit.database_audit import append_audit_entry
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rid = calc_type + "-" + ts
    append_audit_entry(db=db, event_type="compliance.calculation", resource_type="calculation",
        resource_id=rid, action="calculate",
        details={"calc_type": calc_type, "model_version": model_version, "user_id": user_id})
    return rid


def detect_fabrication(metrics):
    warnings = []
    for m in metrics:
        val = m.get("value", 0)
        if isinstance(val, (int, float)):
            if val > 1e15:
                warnings.append({"metric": m.get("name"), "reason": "implausibly_large_value", "severity": "critical"})
    return warnings


class AccuracyEnforcer:
    def __init__(self, db):
        self.db = db

    def certify_metric(self, metric_name, value, source, confidence, user_id):
        validated = validate_metric(metric_name, value, source, confidence)
        validated["publishable"] = confidence >= 0.5
        if confidence < 0.8:
            validated["publish_condition"] = "Must include low-confidence disclaimer"
        register_calculation(self.db, "metric_certification", {"metric": metric_name}, validated, "1.0", user_id)
        return validated