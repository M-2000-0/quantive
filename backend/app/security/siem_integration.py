"""SIEM Integration and Retention Locks.

Directive 5: Immutable Audit Trails and Non-Repudiation
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("quantive.audit.siem")

RETENTION_PERIODS = {
    "public": 365, "internal": 1825, "confidential": 2555,
    "restricted": 3650, "regulated": 3650,
}


class SIEMEvent:
    def __init__(self, event_type, actor_id, actor_role, action, resource_type,
                 resource_id, outcome, ip_address=None, user_agent=None,
                 details=None, classification="internal"):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.event_id = hashlib.sha256(
            (self.timestamp + event_type + actor_id + action + resource_id).encode()
        ).hexdigest()[:16]
        self.event_type = event_type
        self.actor_id = actor_id
        self.actor_role = actor_role
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.outcome = outcome
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.details = details or {}
        self.classification = classification
        self.retention_days = RETENTION_PERIODS.get(classification, 1825)

    def to_dict(self):
        d = {
            "event_id": self.event_id, "timestamp": self.timestamp,
            "event_type": self.event_type, "actor_id": self.actor_id,
            "actor_role": self.actor_role, "action": self.action,
            "resource_type": self.resource_type, "resource_id": self.resource_id,
            "outcome": self.outcome, "ip_address": self.ip_address,
            "details": self.details, "classification": self.classification,
            "retention_days": self.retention_days,
        }
        d["integrity_hash"] = hashlib.sha256(
            json.dumps(d, sort_keys=True, default=str).encode()
        ).hexdigest()
        return d


class SIEMLogger:
    def __init__(self, log_dir="logs/siem", retention_override=None):
        self.log_dir = log_dir
        self.retention_override = retention_override
        os.makedirs(log_dir, exist_ok=True)

    def log_event(self, event):
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, "siem_" + date_str + ".jsonl")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), default=str) + chr(10))
        return event.event_id

    def verify_integrity(self, date_str=None):
        if not date_str:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, "siem_" + date_str + ".jsonl")
        if not os.path.exists(log_file):
            return {"date": date_str, "events": 0, "valid": 0, "tampered": 0}
        valid, tampered = 0, 0
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    stored = data.pop("integrity_hash", None)
                    recomputed = hashlib.sha256(
                        json.dumps(data, sort_keys=True, default=str).encode()
                    ).hexdigest()
                    if stored == recomputed:
                        valid += 1
                    else:
                        tampered += 1
                except (json.JSONDecodeError, KeyError):
                    tampered += 1
        return {"date": date_str, "events": valid + tampered, "valid": valid, "tampered": tampered}

    def get_retention_status(self):
        now = datetime.now(timezone.utc)
        status = []
        if not os.path.exists(self.log_dir):
            return {"logs": [], "total_files": 0}
        for fname in sorted(os.listdir(self.log_dir)):
            if not fname.startswith("siem_") or not fname.endswith(".jsonl"):
                continue
            date_part = fname.replace("siem_", "").replace(".jsonl", "")
            try:
                file_date = datetime.strptime(date_part, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                age_days = (now - file_date).days
                retention = self.retention_override or RETENTION_PERIODS["confidential"]
                status.append({"file": fname, "date": date_part, "age_days": age_days,
                               "retention_days": retention, "locked": age_days < retention})
            except ValueError:
                continue
        return {"logs": status, "total_files": len(status)}


class IdentityEnforcer:
    def __init__(self):
        self._service_accounts = {}

    def register_service_account(self, name, description, owner):
        self._service_accounts[name] = {"description": description, "owner": owner,
                                         "registered_at": datetime.now(timezone.utc).isoformat()}

    def validate_actor(self, actor_id, actor_role, action):
        if not actor_id or actor_id in ("anonymous", "system", "unknown", ""):
            logger.critical("BLOCKED: Anonymous actor attempted: %s", action)
            return {"allowed": False,
                    "reason": "Anonymous elevated execution prohibited. Every production change must map to an authenticated identity.",
                    "actor_id": actor_id, "action": action}
        if actor_id.startswith("svc/") and actor_id not in self._service_accounts:
            return {"allowed": False,
                    "reason": "Service account " + actor_id + " not registered.",
                    "actor_id": actor_id, "action": action}
        return {"allowed": True, "actor_id": actor_id, "action": action}
