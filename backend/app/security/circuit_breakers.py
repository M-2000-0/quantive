import logging
import time
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger("quantive.security.circuit_breaker")


class RateLimiter:
    def __init__(self, max_requests=1000, window_seconds=60, burst_limit=100, burst_window=10):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit
        self.burst_window = burst_window
        self._requests = defaultdict(list)

    def check(self, identifier):
        now = time.time()
        self._requests[identifier] = [t for t in self._requests[identifier] if now - t < self.window_seconds]
        if len(self._requests[identifier]) >= self.max_requests:
            return {"allowed": False, "reason": "Rate limit exceeded", "retry_after": self.window_seconds}
        burst = [t for t in self._requests[identifier] if now - t < self.burst_window]
        if len(burst) >= self.burst_limit:
            return {"allowed": False, "reason": "Burst limit exceeded", "retry_after": self.burst_window}
        self._requests[identifier].append(now)
        return {"allowed": True, "remaining": self.max_requests - len(self._requests[identifier])}


class PayloadValidator:
    def __init__(self, max_payload_mb=50, max_fields=1000):
        self.max_payload_mb = max_payload_mb
        self.max_fields = max_fields

    def validate(self, payload):
        import json
        size_mb = len(json.dumps(payload, default=str).encode()) / (1024 * 1024)
        if size_mb > self.max_payload_mb:
            return {"valid": False, "reason": "Payload exceeds max size"}
        if len(payload) > self.max_fields:
            return {"valid": False, "reason": "Too many fields"}
        return {"valid": True, "size_mb": round(size_mb, 3)}


class AnomalyDetector:
    def __init__(self):
        self._baselines = {}
        self._alerts = []

    def set_baseline(self, metric, expected_value, tolerance=0.5):
        self._baselines[metric] = {"expected": expected_value, "tolerance": tolerance}

    def check_metric(self, metric, actual_value):
        baseline = self._baselines.get(metric)
        if not baseline:
            return {"anomaly": False}
        expected, tolerance = baseline["expected"], baseline["tolerance"]
        deviation = abs(actual_value - expected) / abs(expected) if expected != 0 else (0 if actual_value == 0 else float("inf"))
        if deviation > tolerance:
            alert = {"metric": metric, "expected": expected, "actual": actual_value,
                     "deviation": round(deviation, 4), "timestamp": datetime.now(timezone.utc).isoformat()}
            self._alerts.append(alert)
            return {"anomaly": True, "alert": alert}
        return {"anomaly": False, "metric": metric}


class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = "closed"
        self._failures = 0
        self._last_failure = None
        self._tripped_count = 0

    def record_success(self):
        self._failures = 0
        if self._state == "half-open":
            self._state = "closed"

    def record_failure(self):
        self._failures += 1
        self._last_failure = datetime.now(timezone.utc)
        if self._failures >= self.failure_threshold:
            self._state = "open"
            self._tripped_count += 1
            logger.critical("CIRCUIT BREAKER TRIPPED after %d failures", self._failures)

    def allow_request(self):
        if self._state == "closed":
            return {"allowed": True, "state": "closed"}
        if self._state == "open" and self._last_failure:
            elapsed = (datetime.now(timezone.utc) - self._last_failure).total_seconds()
            if elapsed >= self.recovery_timeout:
                self._state = "half-open"
                return {"allowed": True, "state": "half-open"}
            return {"allowed": False, "state": "open", "failures": self._failures}
        return {"allowed": True, "state": "half-open"}

    def get_state(self):
        return {"state": self._state, "failures": self._failures, "tripped_count": self._tripped_count}


class IncidentResponsePlan:
    def __init__(self):
        self._incidents = []
        self._templates = {
            "data_breach": {"subject": "Data Breach Notification", "timeline_hours": 72,
                           "notify": ["legal", "customer", "regulator"], "escalation": "immediate"},
            "service_outage": {"subject": "Service Disruption Notification", "timeline_hours": 4,
                              "notify": ["customer", "support"], "escalation": "within_1_hour"},
            "data_loss": {"subject": "Data Loss Notification", "timeline_hours": 24,
                         "notify": ["legal", "customer"], "escalation": "within_2_hours"},
            "unauthorized_access": {"subject": "Unauthorized Access Notification", "timeline_hours": 24,
                                   "notify": ["security_team", "legal"], "escalation": "immediate"},
        }

    def declare_incident(self, incident_type, severity, description, detected_by):
        template = self._templates.get(incident_type, self._templates["service_outage"])
        incident = {
            "id": "INC-" + str(len(self._incidents) + 1).zfill(4),
            "type": incident_type, "severity": severity,
            "description": description, "detected_by": detected_by,
            "declared_at": datetime.now(timezone.utc).isoformat(),
            "timeline_hours": template["timeline_hours"],
            "escalation": template["escalation"],
            "notify": template["notify"], "status": "open",
        }
        self._incidents.append(incident)
        logger.critical("INCIDENT: %s [%s] - %s", incident["id"], severity, description)
        return incident

    def get_template(self, incident_type, incident_id):
        t = self._templates.get(incident_type, self._templates["service_outage"])
        nl = chr(10)
        result = "Subject: " + t["subject"] + nl + nl
        result += "Incident ID: " + incident_id + nl
        result += "Date: " + datetime.now(timezone.utc).isoformat() + nl + nl
        result += "Dear Customer," + nl + nl
        result += "We are writing to inform you of a " + incident_type.replace("_", " ") + " incident." + nl + nl
        result += "What happened: [DESCRIBE]" + nl
        result += "What data was affected: [DESCRIBE]" + nl
        result += "What we are doing: [DESCRIBE]" + nl
        result += "What you should do: [DESCRIBE]" + nl + nl
        result += "We are committed to transparency." + nl + nl
        result += "Sincerely," + nl + "Quantive Security Team"
        return result

    def get_incidents(self):
        return self._incidents
