import hashlib
import logging
import os
import re
from datetime import datetime, timezone


logger = logging.getLogger("quantive.security.secrets")


class SecretEntry:
    def __init__(self, name, secret_type, environment, created_by, rotation_days=90):
        self.name = name
        self.secret_type = secret_type
        self.environment = environment
        self.created_by = created_by
        self.rotation_days = rotation_days
        self.created_at = datetime.now(timezone.utc)
        self.last_rotated = self.created_at
        self.status = "active"

    def is_expired(self):
        return (datetime.now(timezone.utc) - self.last_rotated).days > self.rotation_days

    def days_until_rotation(self):
        return max(0, self.rotation_days - (datetime.now(timezone.utc) - self.last_rotated).days)

    def to_dict(self):
        return {"name": self.name, "type": self.secret_type, "env": self.environment,
                "rotation_days": self.rotation_days, "expired": self.is_expired(),
                "days_until_rotation": self.days_until_rotation(), "status": self.status}


class SecretsManager:
    def __init__(self):
        self._secrets = {}

    def register_secret(self, name, secret_type, environment, created_by, rotation_days=90):
        entry = SecretEntry(name, secret_type, environment, created_by, rotation_days)
        self._secrets[name] = entry
        return entry

    def check_rotation(self):
        expired = [s.to_dict() for s in self._secrets.values() if s.is_expired()]
        upcoming = [s.to_dict() for s in self._secrets.values()
                    if not s.is_expired() and s.days_until_rotation() <= 14]
        return {"total": len(self._secrets), "expired": expired, "upcoming": upcoming}

    def scan_source_for_secrets(self, file_path):
        findings = []
        patterns = [
            (r"api_key\s*=\s*[\"']", "API key in source"),
            (r"password\s*=\s*[\"']", "Password in source"),
            (r"secret\s*=\s*[\"']", "Secret in source"),
            (r"token\s*=\s*[\"']", "Token in source"),
            (r"AWS_ACCESS_KEY", "AWS access key in source"),
            (r"MYSQL_PWD", "MySQL password in source"),
            (r"PRIVATE_KEY", "Private key in source"),
        ]
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    for pattern, desc in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            findings.append({"file": file_path, "line": line_num,
                                             "issue": desc, "severity": "critical"})
        except FileNotFoundError:
            pass
        return findings


class EnvironmentIsolator:
    def __init__(self):
        self._envs = {
            "production": {"network": "prod-vpc", "pii_allowed": True},
            "staging": {"network": "staging-vpc", "pii_allowed": False},
            "development": {"network": "dev-vpc", "pii_allowed": False},
            "test": {"network": "test-vpc", "pii_allowed": False},
        }

    def validate_cross_env_access(self, source_env, target_env, data_type="customer_data"):
        if source_env in ("staging", "development", "test") and target_env == "production":
            if data_type in ("customer_data", "pii", "financial_data", "credentials"):
                return {"allowed": False,
                        "reason": source_env + " cannot access " + data_type + " from production."}
        return {"allowed": True, "source": source_env, "target": target_env}

    def validate_production_config(self, env_vars):
        violations = []
        forbidden = ["localhost", "127.0.0.1", "test", "debug=true", "sqlite"]
        for key, value in env_vars.items():
            if isinstance(value, str):
                for pattern in forbidden:
                    if pattern.lower() in value.lower():
                        violations.append({"key": key, "issue": "Contains " + pattern,
                                           "severity": "critical" if pattern in ("localhost", "sqlite") else "warning"})
        return violations