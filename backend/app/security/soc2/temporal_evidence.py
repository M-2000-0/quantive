"""SOC 2 Temporal Evidence Tracking.

Distinguishes between:
- Type 1: Design effectiveness at a point in time
- Type 2: Operational effectiveness over a period (3-12 months)

Implements:
- Daily control operation snapshots
- Consistency scoring over time
- Gap detection (days where controls were not verified)
- Type 1 readiness assessment
- Type 2 audit period tracking
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Float, Boolean
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import Base


class ControlSnapshot(Base):
    """Daily snapshot of control operation status."""
    __tablename__ = "control_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_date = Column(DateTime(timezone=True), nullable=False, index=True)
    control_id = Column(String(20), nullable=False, index=True)  # CC6.1, CC7.2, etc.
    control_name = Column(String(200), nullable=False)
    operated = Column(Boolean, nullable=False)  # Was the control operated this day?
    effectiveness = Column(Float, nullable=True)  # 0-100 score
    evidence_count = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    verified_by = Column(String(36), nullable=True)


class AuditPeriod(Base):
    """Tracks SOC 2 audit periods."""
    __tablename__ = "audit_periods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period_type = Column(String(10), nullable=False)  # type1 or type2
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), default="active")  # active, completed, archived
    total_controls = Column(Integer, default=0)
    controls_operated_days = Column(Integer, default=0)
    total_audit_days = Column(Integer, default=0)
    consistency_score = Column(Float, nullable=True)
    auditor_notes = Column(Text, nullable=True)


# Known SOC 2 controls for daily tracking
SOC2_CONTROLS = {
    "CC6.1": "Logical Access Security Software",
    "CC6.2": "System Authentication",
    "CC6.3": "Authorization",
    "CC7.1": "Anomaly Detection",
    "CC7.2": "System Monitoring",
    "CC7.3": "Security Event Evaluation",
    "CC7.4": "Incident Response",
    "CC8.1": "Change Management",
    "CC9.1": "Risk Assessment",
    "CC9.2": "Vendor Risk Management",
    "A1.1": "Availability Commitments",
    "C1.1": "Confidentiality Commitments",
}


class TemporalEvidenceManager:
    """Manages temporal evidence for SOC 2 Type 1 and Type 2 compliance.

    Type 1 Assessment:
    - Are controls properly designed?
    - Are all required controls in place?
    - Is the control framework documented?

    Type 2 Assessment:
    - Did controls operate every day during the audit period?
    - Were there any gaps?
    - What is the consistency score?
    """

    def __init__(self, db: Session):
        self.db = db

    def record_daily_snapshot(
        self,
        control_id: str,
        operated: bool,
        effectiveness: Optional[float] = None,
        evidence_count: int = 0,
        notes: Optional[str] = None,
        verified_by: Optional[str] = None,
        snapshot_date: Optional[datetime] = None,
    ) -> ControlSnapshot:
        """Record daily control operation snapshot."""
        date = snapshot_date or datetime.now(timezone.utc)
        control_name = SOC2_CONTROLS.get(control_id, control_id)

        snapshot = ControlSnapshot(
            snapshot_date=date,
            control_id=control_id,
            control_name=control_name,
            operated=operated,
            effectiveness=effectiveness,
            evidence_count=evidence_count,
            notes=notes,
            verified_by=verified_by,
        )
        self.db.add(snapshot)
        self.db.commit()
        return snapshot

    def start_audit_period(
        self,
        period_type: str,
        start_date: datetime,
        total_controls: int = 12,
    ) -> AuditPeriod:
        """Start a new SOC 2 audit period."""
        period = AuditPeriod(
            period_type=period_type,
            start_date=start_date,
            total_controls=total_controls,
            status="active",
        )
        self.db.add(period)
        self.db.commit()
        return period

    def close_audit_period(self, period_id: int) -> AuditPeriod:
        """Close an audit period and calculate consistency score."""
        period = self.db.query(AuditPeriod).filter(AuditPeriod.id == period_id).first()
        if not period:
            raise ValueError(f"Period {period_id} not found")

        period.end_date = datetime.now(timezone.utc)
        period.status = "completed"

        # Calculate consistency
        days = (period.end_date - period.start_date).days
        period.total_audit_days = days

        snapshots = self.db.query(ControlSnapshot).filter(
            ControlSnapshot.snapshot_date >= period.start_date,
            ControlSnapshot.snapshot_date <= period.end_date,
        ).all()

        operated_days = len(set(s.snapshot_date.date() for s in snapshots if s.operated))
        period.controls_operated_days = operated_days
        period.consistency_score = round((operated_days / days * 100), 1) if days > 0 else 0

        self.db.commit()
        return period

    def get_type1_readiness(self) -> dict:
        """Assess Type 1 readiness (design effectiveness)."""
        snapshots = self.db.query(ControlSnapshot).filter(
            ControlSnapshot.control_id.in_(SOC2_CONTROLS.keys())
        ).all()

        controls_checked = set(s.control_id for s in snapshots)
        all_controls = set(SOC2_CONTROLS.keys())
        missing = all_controls - controls_checked

        return {
            "type": "SOC 2 Type 1",
            "question": "Are controls properly designed?",
            "controls_required": len(all_controls),
            "controls_documented": len(controls_checked),
            "controls_missing": list(missing),
            "readiness_score": round(len(controls_checked) / len(all_controls) * 100, 1),
            "ready": len(missing) == 0,
        }

    def get_type2_readiness(self, audit_days: int = 90) -> dict:
        """Assess Type 2 readiness (operational effectiveness)."""
        start = datetime.now(timezone.utc) - timedelta(days=audit_days)

        snapshots = self.db.query(ControlSnapshot).filter(
            ControlSnapshot.snapshot_date >= start
        ).all()

        if not snapshots:
            return {
                "type": "SOC 2 Type 2",
                "question": "Did controls operate consistently?",
                "audit_days": audit_days,
                "days_with_evidence": 0,
                "consistency_score": 0,
                "ready": False,
                "message": "No evidence collected yet",
            }

        days_with_evidence = len(set(s.snapshot_date.date() for s in snapshots))
        consistency = round(days_with_evidence / audit_days * 100, 1)

        # Find gaps
        dates_with_data = set(s.snapshot_date.date() for s in snapshots)
        all_dates = set()
        for i in range(audit_days):
            d = (start + timedelta(days=i)).date()
            all_dates.add(d)
        gap_days = sorted(all_dates - dates_with_data)

        return {
            "type": "SOC 2 Type 2",
            "question": "Did controls operate consistently?",
            "audit_days": audit_days,
            "days_with_evidence": days_with_evidence,
            "gap_days": len(gap_days),
            "gap_dates": [str(d) for d in gap_days[:10]],  # First 10 gaps
            "consistency_score": consistency,
            "ready": consistency >= 90,
            "target": 90,
        }

    def get_control_history(self, control_id: str, days: int = 30) -> dict:
        """Get operation history for a specific control."""
        start = datetime.now(timezone.utc) - timedelta(days=days)
        snapshots = self.db.query(ControlSnapshot).filter(
            ControlSnapshot.control_id == control_id,
            ControlSnapshot.snapshot_date >= start,
        ).order_by(ControlSnapshot.snapshot_date.desc()).all()

        operated = sum(1 for s in snapshots if s.operated)
        return {
            "control_id": control_id,
            "control_name": SOC2_CONTROLS.get(control_id, control_id),
            "period_days": days,
            "snapshots": len(snapshots),
            "operated_days": operated,
            "consistency": round(operated / days * 100, 1) if days > 0 else 0,
        }
