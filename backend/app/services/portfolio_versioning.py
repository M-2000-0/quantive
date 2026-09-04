"""Portfolio Versioning — Snapshot and diff for portfolio state changes.

Tracks every significant portfolio change as a versioned snapshot,
enabling before/after comparison and audit trail.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import Session

from app.database import Base

logger = logging.getLogger("quantive.versioning")


class PortfolioVersion(Base):
    """A point-in-time snapshot of a portfolio's state."""
    __tablename__ = "portfolio_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(String, nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    trigger = Column(String, nullable=False)  # optimization, manual_edit, rebalance, creation
    snapshot_json = Column(Text, nullable=False)  # Full portfolio state as JSON
    metrics_json = Column(Text, nullable=True)  # Key metrics at this point
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    description = Column(String, nullable=True)

    __table_args__ = (
        Index("idx_version_portfolio_num", "portfolio_id", "version_number", unique=True),
    )


class PortfolioVersioning:
    """Manage portfolio snapshots and diffs."""

    def __init__(self, db: Session):
        self.db = db

    def create_snapshot(
        self,
        portfolio_id: str,
        trigger: str,
        created_by: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """Create a snapshot of the current portfolio state."""
        from app.models import Portfolio, DebtInstrument

        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            return {"error": "Portfolio not found"}

        instruments = self.db.query(DebtInstrument).filter(
            DebtInstrument.portfolio_id == portfolio_id
        ).all()

        # Build snapshot
        inst_data = []
        for inst in instruments:
            inst_data.append({
                "id": inst.id,
                "name": inst.name,
                "instrument_type": inst.instrument_type.value if hasattr(inst.instrument_type, 'value') else str(inst.instrument_type),
                "currency": inst.currency,
                "principal_outstanding": float(inst.principal_outstanding),
                "coupon_rate": float(inst.coupon_rate),
                "maturity_date": inst.maturity_date,
                "issue_date": inst.issue_date,
                "spread_bps": float(inst.spread_bps) if inst.spread_bps else 0,
                "is_callable": inst.is_callable,
            })

        total_principal = sum(i["principal_outstanding"] for i in inst_data)
        avg_coupon = (
            sum(i["coupon_rate"] * i["principal_outstanding"] for i in inst_data) / total_principal
            if total_principal else 0
        )

        # Compute maturity distribution
        maturity_dist = {}
        for i in inst_data:
            try:
                year = i["maturity_date"][:4]
                maturity_dist[year] = maturity_dist.get(year, 0) + i["principal_outstanding"]
            except (KeyError, TypeError):
                pass

        # Currency breakdown
        currency_breakdown = {}
        for i in inst_data:
            cur = i["currency"]
            currency_breakdown[cur] = currency_breakdown.get(cur, 0) + i["principal_outstanding"]

        snapshot = {
            "portfolio_name": portfolio.name,
            "instruments": inst_data,
            "instrument_count": len(inst_data),
            "total_principal": total_principal,
            "avg_coupon": round(avg_coupon, 4),
            "currencies": list(currency_breakdown.keys()),
            "maturity_distribution": maturity_dist,
            "currency_breakdown": currency_breakdown,
        }

        metrics = {
            "total_principal": total_principal,
            "instrument_count": len(inst_data),
            "avg_coupon_pct": round(avg_coupon * 100, 2),
            "currency_count": len(currency_breakdown),
        }

        # Get next version number
        last_version = self.db.query(PortfolioVersion).filter(
            PortfolioVersion.portfolio_id == portfolio_id
        ).order_by(PortfolioVersion.version_number.desc()).first()
        version_num = (last_version.version_number + 1) if last_version else 1

        record = PortfolioVersion(
            portfolio_id=portfolio_id,
            version_number=version_num,
            trigger=trigger,
            snapshot_json=json.dumps(snapshot, default=str),
            metrics_json=json.dumps(metrics),
            created_by=created_by,
            description=description or f"Snapshot on {trigger}",
        )
        self.db.add(record)
        self.db.commit()

        return {
            "version": version_num,
            "trigger": trigger,
            "metrics": metrics,
            "created_at": record.created_at.isoformat(),
        }

    def get_versions(self, portfolio_id: str, limit: int = 20) -> list[dict]:
        """Get version history for a portfolio."""
        records = self.db.query(PortfolioVersion).filter(
            PortfolioVersion.portfolio_id == portfolio_id
        ).order_by(PortfolioVersion.version_number.desc()).limit(limit).all()

        return [
            {
                "version": r.version_number,
                "trigger": r.trigger,
                "description": r.description,
                "created_by": r.created_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "metrics": json.loads(r.metrics_json) if r.metrics_json else {},
            }
            for r in records
        ]

    def diff_versions(self, portfolio_id: str, v1: int, v2: int) -> dict:
        """Compare two versions and return the diff."""
        ver1 = self.db.query(PortfolioVersion).filter(
            PortfolioVersion.portfolio_id == portfolio_id,
            PortfolioVersion.version_number == v1,
        ).first()
        ver2 = self.db.query(PortfolioVersion).filter(
            PortfolioVersion.portfolio_id == portfolio_id,
            PortfolioVersion.version_number == v2,
        ).first()

        if not ver1 or not ver2:
            return {"error": "Version not found"}

        snap1 = json.loads(ver1.snapshot_json)
        snap2 = json.loads(ver2.snapshot_json)

        # Compare instruments
        ids1 = {i["id"]: i for i in snap1.get("instruments", [])}
        ids2 = {i["id"]: i for i in snap2.get("instruments", [])}

        added = [ids2[iid] for iid in ids2 if iid not in ids1]
        removed = [ids1[iid] for iid in ids1 if iid not in ids2]

        modified = []
        for iid in ids1:
            if iid in ids2:
                changes = {}
                for key in ["principal_outstanding", "coupon_rate", "maturity_date", "spread_bps"]:
                    if ids1[iid].get(key) != ids2[iid].get(key):
                        changes[key] = {"from": ids1[iid].get(key), "to": ids2[iid].get(key)}
                if changes:
                    modified.append({"id": iid, "name": ids1[iid]["name"], "changes": changes})

        # Compare metrics
        m1 = json.loads(ver1.metrics_json) if ver1.metrics_json else {}
        m2 = json.loads(ver2.metrics_json) if ver2.metrics_json else {}
        metric_diff = {}
        for key in set(list(m1.keys()) + list(m2.keys())):
            if m1.get(key) != m2.get(key):
                metric_diff[key] = {"from": m1.get(key), "to": m2.get(key)}

        return {
            "version_from": v1,
            "version_to": v2,
            "added": added,
            "removed": removed,
            "modified": modified,
            "metric_diff": metric_diff,
            "summary": {
                "instruments_added": len(added),
                "instruments_removed": len(removed),
                "instruments_modified": len(modified),
                "principal_change": metric_diff.get("total_principal", {}),
            },
        }

    def get_version_snapshot(self, portfolio_id: str, version: int) -> dict:
        """Get the full snapshot for a specific version."""
        record = self.db.query(PortfolioVersion).filter(
            PortfolioVersion.portfolio_id == portfolio_id,
            PortfolioVersion.version_number == version,
        ).first()

        if not record:
            return {"error": "Version not found"}

        return {
            "version": record.version_number,
            "trigger": record.trigger,
            "description": record.description,
            "snapshot": json.loads(record.snapshot_json),
            "metrics": json.loads(record.metrics_json) if record.metrics_json else {},
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
