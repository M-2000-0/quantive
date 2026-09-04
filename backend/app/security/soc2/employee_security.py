"""SOC 2 Employee Security Controls.

CC1.4 — Commitment to competence
CC2.2 — Internal communication of objectives

Implements:
- Employee security training tracking
- Background check status
- Security awareness certification
- Annual training compliance
- Offboarding checklist
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean, Float
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import Base


class EmployeeSecurityRecord(Base):
    """Employee security compliance record."""
    __tablename__ = "employee_security_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(36), nullable=False, index=True)
    employee_email = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    hire_date = Column(DateTime(timezone=True), nullable=False)

    # Background check
    background_check_completed = Column(Boolean, default=False)
    background_check_date = Column(DateTime(timezone=True), nullable=True)
    background_check_result = Column(String(20), nullable=True)  # passed, failed, pending

    # Security training
    security_training_completed = Column(Boolean, default=False)
    security_training_date = Column(DateTime(timezone=True), nullable=True)
    training_score = Column(Float, nullable=True)  # 0-100

    # Annual refresher
    annual_training_completed = Column(Boolean, default=False)
    annual_training_date = Column(DateTime(timezone=True), nullable=True)
    next_training_due = Column(DateTime(timezone=True), nullable=True)

    # Access review
    last_access_review_date = Column(DateTime(timezone=True), nullable=True)
    access_review_passed = Column(Boolean, default=True)

    # NDA and policies
    nda_signed = Column(Boolean, default=False)
    acceptable_use_signed = Column(Boolean, default=False)
    data_handling_signed = Column(Boolean, default=False)


class EmployeeOffboarding(Base):
    """Offboarding checklist tracking."""
    __tablename__ = "employee_offboarding"

    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(36), nullable=False, index=True)
    employee_email = Column(String(255), nullable=False)
    termination_date = Column(DateTime(timezone=True), nullable=False)
    terminated_by = Column(String(36), nullable=False)

    # Checklist
    access_revoked = Column(Boolean, default=False)
    access_revoked_at = Column(DateTime(timezone=True), nullable=True)
    credentials_rotated = Column(Boolean, default=False)
    assets_returned = Column(Boolean, default=False)
    nda_reminder_sent = Column(Boolean, default=False)
    final_access_review = Column(Boolean, default=False)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class EmployeeSecurityManager:
    """Manages employee security controls for SOC 2 compliance.

    Enforces:
    - Background checks before granting access
    - Security training within 30 days of hire
    - Annual security awareness training
    - Quarterly access reviews
    - Complete offboarding checklist
    """

    TRAINING_VALIDITY_DAYS = 365  # 1 year
    BACKGROUND_CHECK_DEADLINE_DAYS = 30  # Must complete within 30 days of hire

    def __init__(self, db: Session):
        self.db = db

    def register_employee(
        self,
        employee_id: str,
        employee_email: str,
        role: str,
        hire_date: datetime,
    ) -> EmployeeSecurityRecord:
        """Register a new employee for security tracking."""
        record = EmployeeSecurityRecord(
            employee_id=employee_id,
            employee_email=employee_email,
            role=role,
            hire_date=hire_date,
            next_training_due=hire_date + timedelta(days=self.TRAINING_VALIDITY_DAYS),
        )
        self.db.add(record)
        self.db.commit()
        return record

    def complete_background_check(
        self,
        employee_id: str,
        result: str,
    ) -> EmployeeSecurityRecord:
        """Record background check completion."""
        record = self._get_record(employee_id)
        record.background_check_completed = True
        record.background_check_date = datetime.now(timezone.utc)
        record.background_check_result = result
        self.db.commit()
        return record

    def complete_security_training(
        self,
        employee_id: str,
        score: float,
    ) -> EmployeeSecurityRecord:
        """Record security training completion."""
        record = self._get_record(employee_id)
        record.security_training_completed = True
        record.security_training_date = datetime.now(timezone.utc)
        record.training_score = score
        record.next_training_due = datetime.now(timezone.utc) + timedelta(days=self.TRAINING_VALIDITY_DAYS)
        self.db.commit()
        return record

    def complete_annual_training(self, employee_id: str) -> EmployeeSecurityRecord:
        """Record annual security refresher completion."""
        record = self._get_record(employee_id)
        record.annual_training_completed = True
        record.annual_training_date = datetime.now(timezone.utc)
        record.next_training_due = datetime.now(timezone.utc) + timedelta(days=self.TRAINING_VALIDITY_DAYS)
        self.db.commit()
        return record

    def complete_offboarding(self, employee_id: str, terminated_by: str) -> EmployeeOffboarding:
        """Initiate offboarding checklist."""
        record = self._get_record(employee_id)
        offboarding = EmployeeOffboarding(
            employee_id=employee_id,
            employee_email=record.employee_email,
            termination_date=datetime.now(timezone.utc),
            terminated_by=terminated_by,
        )
        self.db.add(offboarding)
        self.db.commit()
        return offboarding

    def verify_offboarding(self, employee_id: str) -> dict:
        """Verify all offboarding steps are complete."""
        offboarding = self.db.query(EmployeeOffboarding).filter(
            EmployeeOffboarding.employee_id == employee_id
        ).order_by(EmployeeOffboarding.termination_date.desc()).first()

        if not offboarding:
            return {"completed": False, "reason": "No offboarding record found"}

        checks = [
            ("Access Revoked", offboarding.access_revoked),
            ("Credentials Rotated", offboarding.credentials_rotated),
            ("Assets Returned", offboarding.assets_returned),
            ("NDA Reminder Sent", offboarding.nda_reminder_sent),
            ("Final Access Review", offboarding.final_access_review),
        ]

        all_done = all(done for _, done in checks)
        return {
            "completed": all_done,
            "checks": [{"name": name, "done": done} for name, done in checks],
            "termination_date": offboarding.termination_date.isoformat(),
        }

    def get_compliance_report(self) -> dict:
        """Generate employee security compliance report."""
        records = self.db.query(EmployeeSecurityRecord).all()
        now = datetime.now(timezone.utc)

        total = len(records)
        bg_check_done = sum(1 for r in records if r.background_check_completed)
        training_done = sum(1 for r in records if r.security_training_completed)
        training_overdue = sum(1 for r in records if r.next_training_due and r.next_training_due < now)
        nda_done = sum(1 for r in records if r.nda_signed)

        return {
            "total_employees": total,
            "background_checks_completed": bg_check_done,
            "background_checks_pending": total - bg_check_done,
            "security_training_completed": training_done,
            "training_overdue": training_overdue,
            "nda_signed": nda_done,
            "compliance_rate": round(bg_check_done / total * 100, 1) if total > 0 else 0,
            "compliance_score": max(0, 100 - (training_overdue * 10) - ((total - bg_check_done) * 5)),
        }

    def _get_record(self, employee_id: str) -> EmployeeSecurityRecord:
        record = self.db.query(EmployeeSecurityRecord).filter(
            EmployeeSecurityRecord.employee_id == employee_id
        ).first()
        if not record:
            raise ValueError(f"Employee {employee_id} not found")
        return record
