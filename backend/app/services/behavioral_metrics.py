"""Behavioral Metrics — Track user actions for product analytics.

Records every meaningful user interaction to build behavioral profiles
and validate feature adoption hypotheses.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, Integer, Float, Index
from sqlalchemy.orm import Session

from app.database import Base

logger = logging.getLogger("quantive.metrics")


class UserEvent(Base):
    """A single user interaction event."""
    __tablename__ = "user_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    org_id = Column(String, nullable=True, index=True)
    event_type = Column(String, nullable=False, index=True)  # page_view, optimization_run, alert_click, etc.
    event_category = Column(String, nullable=True)  # navigation, feature, engagement, conversion
    resource_type = Column(String, nullable=True)  # portfolio, optimization, alert, etc.
    resource_id = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)
    session_id = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    duration_ms = Column(Integer, nullable=True)  # Time spent on action
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    __table_args__ = (
        Index("idx_event_user_type", "user_id", "event_type"),
        Index("idx_event_type_created", "event_type", "created_at"),
    )


class BehavioralMetrics:
    """Track and analyze user behavior."""

    def __init__(self, db: Session):
        self.db = db

    def track(
        self,
        user_id: str,
        event_type: str,
        event_category: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> dict:
        """Record a user event."""
        org_id = None
        try:
            from app.models import User
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                org_id = user.org_id
        except Exception:
            pass

        record = UserEvent(
            user_id=user_id,
            org_id=org_id,
            event_type=event_type,
            event_category=event_category,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=json.dumps(metadata, default=str) if metadata else None,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            duration_ms=duration_ms,
        )
        self.db.add(record)
        self.db.commit()

        return {"tracked": True, "event_type": event_type}

    def get_user_summary(self, user_id: str, days: int = 30) -> dict:
        """Get behavioral summary for a user over the past N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        events = self.db.query(UserEvent).filter(
            UserEvent.user_id == user_id,
            UserEvent.created_at > cutoff,
        ).all()

        # Aggregate
        type_counts = {}
        category_counts = {}
        daily_activity = {}
        feature_usage = {}
        total_duration = 0

        for e in events:
            type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1
            if e.event_category:
                category_counts[e.event_category] = category_counts.get(e.event_category, 0) + 1
            day = e.created_at.strftime("%Y-%m-%d") if e.created_at else "unknown"
            daily_activity[day] = daily_activity.get(day, 0) + 1
            if e.resource_type:
                feature_usage[e.resource_type] = feature_usage.get(e.resource_type, 0) + 1
            if e.duration_ms:
                total_duration += e.duration_ms

        return {
            "user_id": user_id,
            "period_days": days,
            "total_events": len(events),
            "event_types": type_counts,
            "categories": category_counts,
            "daily_activity": daily_activity,
            "feature_usage": feature_usage,
            "total_duration_ms": total_duration,
            "active_days": len(daily_activity),
            "avg_events_per_day": round(len(events) / max(len(daily_activity), 1), 1),
        }

    def get_org_summary(self, org_id: str, days: int = 30) -> dict:
        """Get aggregate behavioral summary for an organization."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        events = self.db.query(UserEvent).filter(
            UserEvent.org_id == org_id,
            UserEvent.created_at > cutoff,
        ).all()

        user_activity = {}
        type_counts = {}
        daily_active_users = {}

        for e in events:
            user_activity[e.user_id] = user_activity.get(e.user_id, 0) + 1
            type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1
            day = e.created_at.strftime("%Y-%m-%d") if e.created_at else "unknown"
            if day not in daily_active_users:
                daily_active_users[day] = set()
            daily_active_users[day].add(e.user_id)

        dau_series = {day: len(users) for day, users in daily_active_users.items()}

        return {
            "org_id": org_id,
            "period_days": days,
            "total_events": len(events),
            "unique_users": len(user_activity),
            "event_types": type_counts,
            "user_activity": user_activity,
            "daily_active_users": dau_series,
            "avg_dau": round(sum(dau_series.values()) / max(len(dau_series), 1), 1),
        }

    def get_feature_adoption(self, org_id: str, days: int = 30) -> list[dict]:
        """Analyze feature adoption rates."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Define features and their trigger events
        features = {
            "optimization": ["optimization_run", "optimize_click"],
            "rebalancing": ["rebalance_view", "rebalance_check"],
            "alerts": ["alert_view", "alert_click"],
            "portfolio_management": ["portfolio_create", "portfolio_edit", "csv_upload"],
            "pdf_export": ["pdf_export", "export_click"],
            "market_intelligence": ["market_intel_view", "fintech_tracker_view"],
            "external_factors": ["external_factors_view"],
            "case_studies": ["case_studies_view"],
            "approvals": ["approval_create", "approval_decide"],
            "mfa": ["mfa_setup", "mfa_verify"],
        }

        results = []
        for feature_name, trigger_events in features.items():
            count = self.db.query(UserEvent).filter(
                UserEvent.org_id == org_id,
                UserEvent.event_type.in_(trigger_events),
                UserEvent.created_at > cutoff,
            ).count()

            users = self.db.query(UserEvent.user_id).filter(
                UserEvent.org_id == org_id,
                UserEvent.event_type.in_(trigger_events),
                UserEvent.created_at > cutoff,
            ).distinct().count()

            results.append({
                "feature": feature_name,
                "events": count,
                "unique_users": users,
                "trigger_events": trigger_events,
            })

        return sorted(results, key=lambda x: x["events"], reverse=True)
