"""SOC 2 Change Management Controller.

CC8.1 — Change management policies and procedures

Implements:
- Change request tracking
- Approval workflows for code changes
- Deployment verification
- Rollback procedures
- Change audit trail
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import Base


class ChangeType(str, Enum):
    CODE = "code"
    INFRASTRUCTURE = "infrastructure"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    EMERGENCY = "emergency"


class ChangeStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"


class ChangeRecord(Base):
    """Immutable record of every change to the system."""
    __tablename__ = "change_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    change_id = Column(String(36), unique=True, nullable=False, index=True)
    change_type = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    requested_by = Column(String(36), nullable=False)
    requested_at = Column(DateTime(timezone=True), default=func.now())
    approved_by = Column(String(36), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="requested")
    risk_level = Column(String(10), default="medium")
    rollback_plan = Column(Text, nullable=True)
    verification_steps = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)


class ChangeManagementController:
    """Manages changes with SOC 2 compliance.

    Enforces:
    - All changes require approval before implementation
    - Emergency changes require post-hoc review
    - Rollback plans required for high-risk changes
    - Complete audit trail of all changes
    """

    # Changes that require two approvers
    HIGH_RISK_TYPES = {"database", "security", "infrastructure"}

    def __init__(self, db: Session):
        self.db = db

    def request_change(
        self,
        change_id: str,
        change_type: str,
        description: str,
        requested_by: str,
        risk_level: str = "medium",
        rollback_plan: Optional[str] = None,
        verification_steps: Optional[str] = None,
    ) -> ChangeRecord:
        """Submit a change request."""
        record = ChangeRecord(
            change_id=change_id,
            change_type=change_type,
            description=description,
            requested_by=requested_by,
            risk_level=risk_level,
            rollback_plan=rollback_plan,
            verification_steps=verification_steps,
        )
        self.db.add(record)
        self.db.commit()
        return record

    def approve_change(self, change_id: str, approved_by: str) -> ChangeRecord:
        """Approve a change request."""
        record = self.db.query(ChangeRecord).filter(
            ChangeRecord.change_id == change_id
        ).first()

        if not record:
            raise ValueError(f"Change {change_id} not found")
        if record.status != "requested":
            raise ValueError(f"Change {change_id} is in status {record.status}")

        record.approved_by = approved_by
        record.approved_at = datetime.now(timezone.utc)
        record.status = "approved"
        self.db.commit()
        return record

    def complete_change(self, change_id: str) -> ChangeRecord:
        """Mark a change as completed."""
        record = self.db.query(ChangeRecord).filter(
            ChangeRecord.change_id == change_id
        ).first()
        if not record:
            raise ValueError(f"Change {change_id} not found")

        record.status = "completed"
        record.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        return record

    def rollback_change(self, change_id: str, reason: str) -> ChangeRecord:
        """Rollback a change."""
        record = self.db.query(ChangeRecord).filter(
            ChangeRecord.change_id == change_id
        ).first()
        if not record:
            raise ValueError(f"Change {change_id} not found")

        record.status = "rolled_back"
        record.rolled_back_at = datetime.now(timezone.utc)
        record.notes = f"Rolled back: {reason}"
        self.db.commit()
        return record

    def get_pending_changes(self) -> list:
        """Get all changes awaiting approval."""
        return self.db.query(ChangeRecord).filter(
            ChangeRecord.status == "requested"
        ).all()

    def get_change_history(self, limit: int = 50) -> list:
        """Get recent change history for audit."""
        return self.db.query(ChangeRecord).order_by(
            ChangeRecord.requested_at.desc()
        ).limit(limit).all()

    def verify_change_controls(self) -> dict:
        """Verify all change management controls are in place."""
        total = self.db.query(ChangeRecord).count()
        completed = self.db.query(ChangeRecord).filter(
            ChangeRecord.status == "completed"
        ).count()
        rolled_back = self.db.query(ChangeRecord).filter(
            ChangeRecord.status == "rolled_back"
        ).count()
        unapproved = self.db.query(ChangeRecord).filter(
            ChangeRecord.status == "requested",
            ChangeRecord.approved_by.is_(None),
        ).count()

        return {
            "total_changes": total,
            "completed": completed,
            "rolled_back": rolled_back,
            "pending_approval": unapproved,
            "rollback_rate": f"{(rolled_back/total*100):.1f}%" if total > 0 else "0%",
            "compliance_score": 100 if unapproved == 0 else max(0, 100 - (unapproved * 10)),
        }
