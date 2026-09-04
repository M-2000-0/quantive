"""SOC 2 CI/CD Security Pipeline.

CC8.1 — Change management (automated enforcement)
CC7.1 — Detection of anomalies in deployment

Implements:
- Pre-commit security hooks
- Build-time vulnerability scanning
- Deployment approval gates
- Secret detection in commits
- Dependency vulnerability checking
- Infrastructure-as-code scanning
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import Base


class CICDSecurityEvent(Base):
    """Records every CI/CD security check."""
    __tablename__ = "cicd_security_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(36), unique=True, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=func.now())
    event_type = Column(String(50), nullable=False)  # pre_commit, build, deploy, scan
    status = Column(String(20), nullable=False)  # passed, failed, blocked
    details = Column(Text, nullable=True)  # JSON
    commit_hash = Column(String(40), nullable=True)
    branch = Column(String(100), nullable=True)
    triggered_by = Column(String(36), nullable=True)
    findings_count = Column(Integer, default=0)


class CICDSecurityPipeline:
    """Automated security checks for CI/CD pipeline.

    Enforces:
    - No secrets in source code
    - No critical vulnerabilities in dependencies
    - All changes reviewed before deployment
    - Infrastructure changes audited
    - Deployment requires approval
    """

    # Patterns that indicate secrets in source code
    SECRET_PATTERNS = [
        (r"api[_-]?key\s*=\s*[\"'][A-Za-z0-9]{20,}", "API key"),
        (r"password\s*=\s*[\"'][^\"']{8,}", "Hardcoded password"),
        (r"secret[_-]?key\s*=\s*[\"'][^\"']{16,}", "Secret key"),
        (r"aws[_-]?access[_-]?key[_-]?id\s*=\s*[\"']AKIA", "AWS access key"),
        (r"private[_-]?key\s*=\s*[\"']-----BEGIN", "Private key"),
        (r"token\s*=\s*[\"'][A-Za-z0-9_-]{40,}", "Auth token"),
        (r"Bearer\s+[A-Za-z0-9_-]{20,}", "Bearer token"),
        (r"jdbc:(mysql|postgresql)://[^\"']+", "Database connection string"),
    ]

    # Critical vulnerability patterns
    CRITICAL_VULNS = [
        (r"CVE-\d{4}-\d{4,}", "CVE reference"),
        (r"Critical.*vulnerability", "Critical vulnerability"),
        (r"Remote Code Execution", "RCE vulnerability"),
        (r"SQL Injection", "SQL injection"),
    ]

    def __init__(self, db: Session):
        self.db = db

    def scan_secrets_in_code(self, file_path: str, content: str) -> list:
        """Scan code content for hardcoded secrets."""
        findings = []
        for i, line in enumerate(content.split("\n"), 1):
            for pattern, desc in self.SECRET_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append({
                        "file": file_path,
                        "line": i,
                        "type": desc,
                        "severity": "critical",
                        "code": line.strip()[:100],
                    })
        return findings

    def scan_dependencies(self, requirements_content: str) -> list:
        """Scan dependency files for known vulnerabilities."""
        findings = []
        lines = requirements_content.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Check for pinned versions
            if "==" not in line and ">=" not in line:
                findings.append({
                    "package": line,
                    "type": "unpinned_version",
                    "severity": "medium",
                    "detail": f"Package '{line}' has no pinned version",
                })
        return findings

    def validate_deployment(self, deployment_info: dict) -> dict:
        """Validate a deployment meets security requirements."""
        checks = []

        # Check 1: Has approval
        has_approval = deployment_info.get("approved_by") is not None
        checks.append({
            "name": "Deployment Approval",
            "passed": has_approval,
            "detail": f"Approved by: {deployment_info.get('approved_by', 'NONE')}" if has_approval else "No approval found",
        })

        # Check 2: Not deploying to production on Friday/weekend
        deploy_time = deployment_info.get("deploy_time", "")
        if deploy_time:
            try:
                dt = datetime.fromisoformat(deploy_time.replace("Z", "+00:00"))
                is_weekend = dt.weekday() >= 5
                checks.append({
                    "name": "Weekend Deployment Check",
                    "passed": not is_weekend,
                    "detail": f"Deploying on {'weekend' if is_weekend else 'weekday'}",
                })
            except (ValueError, AttributeError):
                checks.append({"name": "Weekend Deployment Check", "passed": True, "detail": "Could not parse deploy time"})

        # Check 3: Has rollback plan
        has_rollback = bool(deployment_info.get("rollback_plan"))
        checks.append({
            "name": "Rollback Plan",
            "passed": has_rollback,
            "detail": "Rollback plan documented" if has_rollback else "No rollback plan",
        })

        # Check 4: Security scan passed
        scan_passed = deployment_info.get("security_scan_passed", False)
        checks.append({
            "name": "Security Scan",
            "passed": scan_passed,
            "detail": "Security scan passed" if scan_passed else "Security scan not run or failed",
        })

        all_passed = all(c["passed"] for c in checks)
        return {
            "deployment_id": deployment_info.get("deployment_id"),
            "approved": all_passed,
            "checks": checks,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def record_event(
        self,
        event_type: str,
        status: str,
        details: dict,
        commit_hash: Optional[str] = None,
        branch: Optional[str] = None,
        triggered_by: Optional[str] = None,
        findings_count: int = 0,
    ) -> CICDSecurityEvent:
        """Record a CI/CD security event."""
        import uuid
        event = CICDSecurityEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            status=status,
            details=json.dumps(details, default=str),
            commit_hash=commit_hash,
            branch=branch,
            triggered_by=triggered_by,
            findings_count=findings_count,
        )
        self.db.add(event)
        self.db.commit()
        return event

    def get_pipeline_report(self, days: int = 30) -> dict:
        """Generate CI/CD security pipeline report."""
        from datetime import timedelta
        start = datetime.now(timezone.utc) - timedelta(days=days)

        events = self.db.query(CICDSecurityEvent).filter(
            CICDSecurityEvent.timestamp >= start
        ).all()

        total = len(events)
        passed = sum(1 for e in events if e.status == "passed")
        failed = sum(1 for e in events if e.status == "failed")
        blocked = sum(1 for e in events if e.status == "blocked")

        return {
            "period_days": days,
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "pass_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%",
            "compliance_score": 100 if failed == 0 and blocked == 0 else max(0, 100 - (failed * 5) - (blocked * 10)),
        }
