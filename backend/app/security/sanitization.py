"""Input sanitization and XSS prevention utilities.

Provides middleware and helper functions to sanitize user inputs,
detect potential SQL injection attempts, and prevent XSS attacks.
"""

import html
import re
from typing import Optional

# Common XSS patterns
XSS_PATTERNS = [
    re.compile(r"<script\b", re.IGNORECASE),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"<iframe\b", re.IGNORECASE),
    re.compile(r"<object\b", re.IGNORECASE),
    re.compile(r"<embed\b", re.IGNORECASE),
    re.compile(r"<link\b.*rel\s*=\s*[\"']stylesheet", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"vbscript:", re.IGNORECASE),
    re.compile(r"data:text/html", re.IGNORECASE),
    re.compile(r"<svg\b.*onload", re.IGNORECASE),
]

# SQL injection patterns
SQL_INJECTION_PATTERNS = [
    re.compile(r"'\s*OR\s+'", re.IGNORECASE),
    re.compile(r"'\s*OR\s+\d+\s*=\s*\d+", re.IGNORECASE),
    re.compile(r";\s*DROP\s+TABLE", re.IGNORECASE),
    re.compile(r";\s*DELETE\s+FROM", re.IGNORECASE),
    re.compile(r";\s*INSERT\s+INTO", re.IGNORECASE),
    re.compile(r";\s*UPDATE\s+", re.IGNORECASE),
    re.compile(r"UNION\s+SELECT", re.IGNORECASE),
    re.compile(r"--\s*$", re.IGNORECASE),
    re.compile(r"/\*.*\*/", re.IGNORECASE),
    re.compile(r"CHAR\s*\(", re.IGNORECASE),
    re.compile(r"CONCAT\s*\(", re.IGNORECASE),
    re.compile(r"WAITFOR\s+DELAY", re.IGNORECASE),
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\./"),
    re.compile(r"\.\.\\"),
    re.compile(r"%2e%2e", re.IGNORECASE),
    re.compile(r"%252e%252e", re.IGNORECASE),
]


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """Sanitize a string input by escaping HTML entities and truncating.

    Args:
        value: The input string to sanitize.
        max_length: Maximum allowed length.

    Returns:
        Sanitized string safe for display.
    """
    if not isinstance(value, str):
        return value

    # Truncate
    value = value[:max_length]

    # Escape HTML entities
    value = html.escape(value)

    # Remove null bytes
    value = value.replace("\x00", "")

    return value


def detect_xss(value: str) -> bool:
    """Check if a string contains potential XSS payloads.

    Returns:
        True if XSS pattern detected.
    """
    if not isinstance(value, str):
        return False
    return any(pattern.search(value) for pattern in XSS_PATTERNS)


def detect_sql_injection(value: str) -> bool:
    """Check if a string contains potential SQL injection patterns.

    Returns:
        True if SQL injection pattern detected.
    """
    if not isinstance(value, str):
        return False
    return any(pattern.search(value) for pattern in SQL_INJECTION_PATTERNS)


def detect_path_traversal(value: str) -> bool:
    """Check if a string contains path traversal attempts.

    Returns:
        True if path traversal detected.
    """
    if not isinstance(value, str):
        return False
    return any(pattern.search(value) for pattern in PATH_TRAVERSAL_PATTERNS)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing dangerous characters.

    Args:
        filename: The input filename.

    Returns:
        Safe filename.
    """
    # Remove path components
    filename = filename.split("/")[-1].split("\\")[-1]

    # Remove null bytes
    filename = filename.replace("\x00", "")

    # Remove control characters
    filename = "".join(c for c in filename if ord(c) >= 32)

    # Truncate
    filename = filename[:255]

    return filename


def validate_json_input(data: dict, field_whitelist: Optional[set] = None) -> dict:
    """Validate and sanitize all string values in a JSON dictionary.

    Args:
        data: The input dictionary.
        field_whitelist: Optional set of allowed field names. If provided,
                         fields not in the whitelist are removed.

    Returns:
        Sanitized dictionary.
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        # Check whitelist
        if field_whitelist and key not in field_whitelist:
            continue

        if isinstance(value, str):
            # Check for attacks
            if detect_xss(value) or detect_sql_injection(value):
                raise ValueError(f"Potentially malicious input in field '{key}'")
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[key] = validate_json_input(value, field_whitelist)
        elif isinstance(value, list):
            sanitized[key] = [
                validate_json_input(item, field_whitelist) if isinstance(item, dict)
                else sanitize_string(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


class SecurityAuditLog:
    """In-memory security event log for monitoring and alerting."""

    def __init__(self, max_entries: int = 10000):
        self._entries: list[dict] = []
        self._max_entries = max_entries

    def log_event(self, event_type: str, details: dict, severity: str = "info"):
        """Log a security event.

        Args:
            event_type: Type of event (e.g., 'xss_attempt', 'sql_injection', 'brute_force').
            details: Event details dictionary.
            severity: Severity level ('info', 'warning', 'critical').
        """
        from datetime import datetime, timezone

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "severity": severity,
            "details": details,
        }
        self._entries.append(entry)

        # Trim old entries
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        # Log critical events
        if severity == "critical":
            import logging
            logger = logging.getLogger("quantive.security")
            logger.warning(f"SECURITY EVENT [{severity.upper()}] {event_type}: {details}")

    def get_recent(self, count: int = 100, severity: Optional[str] = None) -> list[dict]:
        """Get recent security events."""
        entries = self._entries
        if severity:
            entries = [e for e in entries if e["severity"] == severity]
        return entries[-count:]

    def get_stats(self) -> dict:
        """Get security event statistics."""
        from collections import Counter
        severity_counts = Counter(e["severity"] for e in self._entries)
        type_counts = Counter(e["event_type"] for e in self._entries)
        return {
            "total_events": len(self._entries),
            "by_severity": dict(severity_counts),
            "by_type": dict(type_counts.most_common(20)),
        }


# Global security audit log instance
security_log = SecurityAuditLog()
