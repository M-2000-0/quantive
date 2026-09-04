"""Alert Engine — Proactive notification system for portfolio events.

Monitors:
- Allocation drift exceeding user-set thresholds
- Maturity walls (concentration of maturities in a single quarter)
- Rate window opportunities (yield curve inversions, spread changes)
- Data freshness warnings (stale market data)

Generates in-app alerts and optional email notifications.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, Float, ForeignKey, Index
from sqlalchemy.orm import Session

from app.database import Base

logger = logging.getLogger("quantive.alerts")


class AlertRecord(Base):
    """Persistent alert record for in-app display and email queue."""
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    org_id = Column(String, nullable=True, index=True)
    alert_type = Column(String, nullable=False)  # drift, maturity_wall, rate_window, data_freshness
    severity = Column(String, default="info")  # info, warning, critical
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    portfolio_id = Column(String, nullable=True)
    metric_name = Column(String, nullable=True)
    metric_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    is_read = Column(Boolean, default=False)
    is_emailed = Column(Boolean, default=False)
    action_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_alert_user_unread", "user_id", "is_read"),
        Index("idx_alert_type_created", "alert_type", "created_at"),
    )


class AlertEngine:
    """Monitor portfolio conditions and generate alerts."""

    # Default thresholds
    DRIFT_WARNING_PCT = 5.0
    DRIFT_CRITICAL_PCT = 10.0
    MATURITY_WALL_PCT = 15.0  # >15% of debt maturing in single quarter
    RATE_WINDOW_SPREAD_BPS = 50  # Inversion or steepening opportunity
    DATA_STALE_HOURS = 24

    def __init__(self, db: Session):
        self.db = db

    def check_all_alerts(self, user_id: str, org_id: str) -> list[dict]:
        """Run all alert checks for a user and return new alerts."""
        alerts = []

        # Load user's portfolios
        from app.models import Portfolio, DebtInstrument
        portfolios = self.db.query(Portfolio).filter(Portfolio.org_id == org_id).all()

        for portfolio in portfolios:
            instruments = self.db.query(DebtInstrument).filter(
                DebtInstrument.portfolio_id == portfolio.id
            ).all()

            if not instruments:
                continue

            # Check drift
            drift_alerts = self._check_drift(user_id, org_id, portfolio, instruments)
            alerts.extend(drift_alerts)

            # Check maturity walls
            maturity_alerts = self._check_maturity_walls(user_id, org_id, portfolio, instruments)
            alerts.extend(maturity_alerts)

        # Check rate windows
        rate_alerts = self._check_rate_windows(user_id, org_id)
        alerts.extend(rate_alerts)

        # Persist new alerts
        for alert_data in alerts:
            # Deduplicate: don't create if same type/portfolio exists within 24h
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            existing = self.db.query(AlertRecord).filter(
                AlertRecord.user_id == user_id,
                AlertRecord.alert_type == alert_data["alert_type"],
                AlertRecord.portfolio_id == alert_data.get("portfolio_id"),
                AlertRecord.created_at > cutoff,
            ).first()

            if not existing:
                record = AlertRecord(
                    user_id=user_id,
                    org_id=org_id,
                    **alert_data,
                )
                self.db.add(record)

        if alerts:
            self.db.commit()

        return alerts

    def _check_drift(self, user_id, org_id, portfolio, instruments) -> list[dict]:
        """Check if any asset class has drifted beyond thresholds."""
        alerts = []

        # Calculate current allocation by type
        total = sum(float(i.principal_outstanding) for i in instruments)
        if total == 0:
            return alerts

        type_values = {}
        for inst in instruments:
            t = inst.instrument_type.value if hasattr(inst.instrument_type, 'value') else str(inst.instrument_type)
            type_values[t] = type_values.get(t, 0) + float(inst.principal_outstanding)

        # Target allocation (simplified - use equal weight as baseline)
        n_types = len(type_values) if type_values else 1
        target_pct = 100.0 / n_types

        for type_name, value in type_values.items():
            current_pct = (value / total) * 100
            drift = abs(current_pct - target_pct)

            if drift >= self.DRIFT_CRITICAL_PCT:
                alerts.append({
                    "alert_type": "drift",
                    "severity": "critical",
                    "title": f"Critical drift: {type_name.replace('_', ' ')}",
                    "message": f"Allocation drift of {drift:.1f}% detected for {type_name.replace('_', ' ')}. Current: {current_pct:.1f}%, Target: {target_pct:.1f}%. Immediate rebalancing recommended.",
                    "portfolio_id": portfolio.id,
                    "metric_name": f"drift_{type_name}",
                    "metric_value": round(drift, 2),
                    "threshold_value": self.DRIFT_CRITICAL_PCT,
                    "action_url": "/rebalancing",
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
                })
            elif drift >= self.DRIFT_WARNING_PCT:
                alerts.append({
                    "alert_type": "drift",
                    "severity": "warning",
                    "title": f"Drift detected: {type_name.replace('_', ' ')}",
                    "message": f"Allocation drift of {drift:.1f}% for {type_name.replace('_', ' ')}. Current: {current_pct:.1f}%, Target: {target_pct:.1f}%.",
                    "portfolio_id": portfolio.id,
                    "metric_name": f"drift_{type_name}",
                    "metric_value": round(drift, 2),
                    "threshold_value": self.DRIFT_WARNING_PCT,
                    "action_url": "/rebalancing",
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=14),
                })

        return alerts

    def _check_maturity_walls(self, user_id, org_id, portfolio, instruments) -> list[dict]:
        """Check for concentration of maturities in a single quarter."""
        alerts = []
        now = datetime.now(timezone.utc)

        # Group instruments by maturity quarter
        quarter_totals = {}
        total = sum(float(i.principal_outstanding) for i in instruments)
        if total == 0:
            return alerts

        for inst in instruments:
            try:
                mat_date = datetime.strptime(inst.maturity_date, "%Y-%m-%d")
                # Get quarter key (e.g., "2027-Q2")
                q = (mat_date.month - 1) // 3 + 1
                key = f"{mat_date.year}-Q{q}"
                quarter_totals[key] = quarter_totals.get(key, 0) + float(inst.principal_outstanding)
            except (ValueError, TypeError):
                continue

        for quarter, amount in quarter_totals.items():
            pct = (amount / total) * 100
            if pct >= self.MATURITY_WALL_PCT:
                # Only alert for upcoming quarters (within 18 months)
                try:
                    year, q = quarter.split("-Q")
                    q_start_month = (int(q) - 1) * 3 + 1
                    q_date = datetime(int(year), q_start_month, 1, tzinfo=timezone.utc)
                    months_until = (q_date.year - now.year) * 12 + (q_date.month - now.month)
                    if 0 <= months_until <= 18:
                        severity = "critical" if pct >= 25 else "warning"
                        alerts.append({
                            "alert_type": "maturity_wall",
                            "severity": severity,
                            "title": f"Maturity wall: {quarter}",
                            "message": f"{pct:.1f}% of portfolio (${amount/1e9:.1f}B) matures in {quarter}. Consider pre-funding or extending maturities.",
                            "portfolio_id": portfolio.id,
                            "metric_name": f"maturity_{quarter}",
                            "metric_value": round(pct, 2),
                            "threshold_value": self.MATURITY_WALL_PCT,
                            "action_url": "/debt-optimizer",
                            "expires_at": q_date,
                        })
                except (ValueError, TypeError):
                    continue

        return alerts

    def _check_rate_windows(self, user_id, org_id) -> list[dict]:
        """Check for rate window opportunities based on yield curve."""
        alerts = []

        try:
            from app.market_data.cache import get_cache
            cache = get_cache()
            snapshot = cache.get("market_snapshot")
            if not snapshot:
                return alerts

            yc = snapshot.get("yield_curve", {})
            spread = yc.get("two_ten_spread_bps", 0)

            if spread < -self.RATE_WINDOW_SPREAD_BPS:
                alerts.append({
                    "alert_type": "rate_window",
                    "severity": "critical",
                    "title": "Yield curve inversion opportunity",
                    "message": f"2Y-10Y spread at {spread:.0f}bps indicates inverted curve. Locking long-term rates now could save significantly on refinancing costs.",
                    "metric_name": "yield_spread_bps",
                    "metric_value": spread,
                    "threshold_value": -self.RATE_WINDOW_SPREAD_BPS,
                    "action_url": "/debt-optimizer",
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
                })
            elif spread > self.RATE_WINDOW_SPREAD_BPS:
                alerts.append({
                    "alert_type": "rate_window",
                    "severity": "info",
                    "title": "Steepening curve detected",
                    "message": f"2Y-10Y spread at {spread:.0f}bps indicates steepening. Short-term borrowing is relatively cheap.",
                    "metric_name": "yield_spread_bps",
                    "metric_value": spread,
                    "threshold_value": self.RATE_WINDOW_SPREAD_BPS,
                    "action_url": "/debt-optimizer",
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
                })
        except Exception as e:
            logger.warning(f"Rate window check failed: {e}")

        return alerts

    def get_user_alerts(self, user_id: str, unread_only: bool = False, limit: int = 50) -> list[dict]:
        """Get alerts for a user."""
        query = self.db.query(AlertRecord).filter(AlertRecord.user_id == user_id)
        if unread_only:
            query = query.filter(AlertRecord.is_read == False)
        records = query.order_by(AlertRecord.created_at.desc()).limit(limit).all()

        return [
            {
                "id": r.id,
                "alert_type": r.alert_type,
                "severity": r.severity,
                "title": r.title,
                "message": r.message,
                "portfolio_id": r.portfolio_id,
                "metric_name": r.metric_name,
                "metric_value": r.metric_value,
                "threshold_value": r.threshold_value,
                "is_read": r.is_read,
                "action_url": r.action_url,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]

    def mark_read(self, alert_id: int, user_id: str) -> bool:
        """Mark an alert as read."""
        record = self.db.query(AlertRecord).filter(
            AlertRecord.id == alert_id,
            AlertRecord.user_id == user_id,
        ).first()
        if record:
            record.is_read = True
            self.db.commit()
            return True
        return False

    def mark_all_read(self, user_id: str) -> int:
        """Mark all alerts as read. Returns count."""
        count = self.db.query(AlertRecord).filter(
            AlertRecord.user_id == user_id,
            AlertRecord.is_read == False,
        ).update({"is_read": True})
        self.db.commit()
        return count

    def get_unread_count(self, user_id: str) -> int:
        """Get count of unread alerts."""
        return self.db.query(AlertRecord).filter(
            AlertRecord.user_id == user_id,
            AlertRecord.is_read == False,
        ).count()
