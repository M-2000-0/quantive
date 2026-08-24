"""Export, webhook, and integration models for async jobs and third-party connections."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Export Jobs ─────────────────────────────────────────────────────────────

class ExportJob(Base):
    """Async report/data export jobs."""
    __tablename__ = "export_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    export_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "portfolio", "optimization", "report"
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    output_format: Mapped[str] = mapped_column(String(20), nullable=False, default="pdf")  # pdf, xlsx, csv, json
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")  # queued, running, completed, failed
    progress: Mapped[float] = mapped_column(Integer, default=0)
    output_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Webhooks ────────────────────────────────────────────────────────────────

class Webhook(Base):
    """Configurable webhook endpoints for event notifications."""
    __tablename__ = "webhooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    events: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)  # ["optimization.completed", "portfolio.updated"]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class WebhookDelivery(Base):
    """Webhook delivery attempts and status."""
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    webhook_id: Mapped[str] = mapped_column(String(36), ForeignKey("webhooks.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Integrations ────────────────────────────────────────────────────────────

class Integration(Base):
    """Third-party integration connections."""
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    integration_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "bloomberg", "reuters", "slack", etc.
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_status: Mapped[str] = mapped_column(String(20), default="idle")  # idle, syncing, error
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# ── Model Experiments ───────────────────────────────────────────────────────

class ModelExperiment(Base):
    """A/B testing of optimization algorithms."""
    __tablename__ = "model_experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    control_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    treatment_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    traffic_split: Mapped[float] = mapped_column(Integer, default=50)  # percentage for treatment
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, running, completed, cancelled
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── API Usage Log ───────────────────────────────────────────────────────────

class APIUsageLog(Base):
    """API usage tracking for analytics and billing."""
    __tablename__ = "api_usage_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    org_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    request_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
