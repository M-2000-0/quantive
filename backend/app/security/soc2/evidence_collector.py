"""SOC 2 Compliance Evidence Collector.

CC2.1 — Communication and information
CC7.1 — Detection of anomalies
CC9.1 — Risk assessment

Implements:
- Automated evidence collection for SOC 2 audits
- Evidence categorization by Trust Service Criteria
- Evidence integrity verification
- Audit-ready report generation
- Evidence retention management
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import Base


class EvidenceRecord(Base):
    """Immutable evidence record for SOC 2 compliance."""
    __tablename__ = "soc2_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evidence_id = Column(String(36), unique=True, nullable=False, index=True)
    criterion = Column(String(20), nullable=False)  # e.g., CC6.1, CC7.2
    category = Column(String(50), nullable=False)  # access, audit, incident, vendor, etc.
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    data = Column(Text, nullable=False)  # JSON evidence payload
    sha256_hash = Column(String(64), nullable=False)
    collected_by = Column(String(36), nullable=False)
    collected_at = Column(DateTime(timezone=True), default=func.now())
    retention_until = Column(DateTime(timezone=True), nullable=True)
    verified = Column(Boolean, default=False)


class ComplianceEvidenceCollector:
    """Collects and manages SOC 2 compliance evidence.

    Ensures:
    - All evidence is cryptographically hashed
    - Evidence maps to specific Trust Service Criteria
    - Retention policies are enforced
    - Evidence is tamper-evident
    """

    # Retention periods by evidence type (years)
    RETENTION_YEARS = {
        "access_review": 7,
        "audit_log": 7,
        "incident": 7,
        "vendor_assessment": 5,
        "change_record": 5,
        "policy_acknowledgment": 3,
        "training_record": 3,
        "penetration_test": 3,
        "configuration_baseline": 5,
    }

    # SOC 2 Trust Service Criteria mapping
    CRITERIA_MAP = {
        "security": ["CC1", "CC2", "CC3", "CC4", "CC5", "CC6", "CC7", "CC8", "CC9"],
        "availability": ["A1"],
        "processing_integrity": ["PI1"],
        "confidentiality": ["C1"],
        "privacy": ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"],
    }

    def __init__(self, db: Session):
        self.db = db

    def collect_evidence(
        self,
        criterion: str,
        category: str,
        title: str,
        description: str,
        data: dict,
        collected_by: str,
    ) -> EvidenceRecord:
        """Collect a piece of compliance evidence."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        sha256 = hashlib.sha256(data_str.encode()).hexdigest()

        evidence_id = f"EVD-{category[:4].upper()}-{sha256[:8].upper()}"

        # Determine retention
        retention_years = self.RETENTION_YEARS.get(category, 5)
        from datetime import timedelta
        retention_until = datetime.now(timezone.utc) + timedelta(days=retention_years * 365)

        record = EvidenceRecord(
            evidence_id=evidence_id,
            criterion=criterion,
            category=category,
            title=title,
            description=description,
            data=data_str,
            sha256_hash=sha256,
            collected_by=collected_by,
            retention_until=retention_until,
        )

        self.db.add(record)
        self.db.commit()
        return record

    def verify_evidence_integrity(self, evidence_id: str) -> dict:
        """Verify evidence hasn't been tampered with."""
        record = self.db.query(EvidenceRecord).filter(
            EvidenceRecord.evidence_id == evidence_id
        ).first()

        if not record:
            return {"verified": False, "error": "Evidence not found"}

        current_hash = hashlib.sha256(record.data.encode()).hexdigest()
        is_valid = current_hash == record.sha256_hash

        if is_valid:
            record.verified = True
            self.db.commit()

        return {
            "evidence_id": evidence_id,
            "verified": is_valid,
            "stored_hash": record.sha256_hash[:16] + "...",
            "current_hash": current_hash[:16] + "...",
            "collected_at": record.collected_at.isoformat(),
        }

    def get_evidence_by_criterion(self, criterion: str) -> list:
        """Get all evidence for a specific SOC 2 criterion."""
        return self.db.query(EvidenceRecord).filter(
            EvidenceRecord.criterion.like(f"{criterion}%")
        ).all()

    def get_audit_readiness_report(self) -> dict:
        """Generate audit readiness report."""
        total = self.db.query(EvidenceRecord).count()
        verified = self.db.query(EvidenceRecord).filter(
            EvidenceRecord.verified == True
        ).count()

        # Count evidence by category
        categories = {}
        records = self.db.query(EvidenceRecord).all()
        for r in records:
            categories[r.category] = categories.get(r.category, 0) + 1

        # Check criteria coverage
        covered_criteria = set(r.criterion for r in records)
        all_criteria = set()
        for group in self.CRITERIA_MAP.values():
            all_criteria.update(group)
        missing = all_criteria - covered_criteria

        return {
            "total_evidence_items": total,
            "verified": verified,
            "verification_rate": f"{(verified/total*100):.1f}%" if total > 0 else "0%",
            "by_category": categories,
            "criteria_covered": len(covered_criteria),
            "criteria_missing": list(missing),
            "readiness_score": max(0, 100 - (len(missing) * 5)),
        }

    def get_expired_evidence(self) -> list:
        """Get evidence past retention period."""
        now = datetime.now(timezone.utc)
        return self.db.query(EvidenceRecord).filter(
            EvidenceRecord.retention_until < now
        ).all()
