import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SCENARIO_GENERATION = "scenario_generation"
    SOLVING = "solving"
    BENCHMARKING = "benchmarking"
    STRESS_TESTING = "stress_testing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OptimizationType(str, enum.Enum):
    MINIMIZE_COST = "minimize_cost"
    MINIMIZE_RISK = "minimize_risk"
    MAXIMIZE_RETURN = "maximize_return"
    MEAN_VARIANCE = "mean_variance"
    MINIMIZE_DURATION = "minimize_duration"
    MULTI_OBJECTIVE = "multi_objective"


class DebtInstrumentType(str, enum.Enum):
    TREASURY_BOND = "treasury_bond"
    T_BILL = "t_bill"
    SOVEREIGN_BOND = "sovereign_bond"
    CONCESSIONAL_LOAN = "concessional_loan"
    COMMERCIAL_LOAN = "commercial_loan"
    FLOATING_RATE_NOTE = "floating_rate_note"
    INFLATION_LINKED = "inflation_linked"
    EUROBOND = "eurobond"
    DOMESTIC_BOND = "domestic_bond"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    portfolios: Mapped[list["Portfolio"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="users")
    portfolio_accesses: Mapped[list["PortfolioAccess"]] = relationship(
        back_populates="user", foreign_keys="[PortfolioAccess.user_id]"
    )


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="portfolios")
    instruments: Mapped[list["DebtInstrument"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    access_grants: Mapped[list["PortfolioAccess"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )


class DebtInstrument(Base):
    __tablename__ = "debt_instruments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    instrument_type: Mapped[DebtInstrumentType] = mapped_column(SAEnum(DebtInstrumentType), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    principal_outstanding: Mapped[float] = mapped_column(Float, nullable=False)
    coupon_rate: Mapped[float] = mapped_column(Float, nullable=False)
    maturity_date: Mapped[str] = mapped_column(String(10), nullable=False)
    issue_date: Mapped[str] = mapped_column(String(10), nullable=False)
    is_callable: Mapped[bool] = mapped_column(Boolean, default=False)
    call_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    call_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    spread_bps: Mapped[float] = mapped_column(Float, default=0.0)
    amortization_schedule: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    portfolio: Mapped["Portfolio"] = relationship(back_populates="instruments")


class OptimizationJob(Base):
    __tablename__ = "optimization_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id"), nullable=False)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="Untitled Optimization")
    status: Mapped[JobStatus] = mapped_column(SAEnum(JobStatus), default=JobStatus.QUEUED)
    optimization_type: Mapped[OptimizationType] = mapped_column(SAEnum(OptimizationType), default=OptimizationType.MINIMIZE_COST)
    objectives: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    constraints: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    solver_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    scenario_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    random_seed: Mapped[int] = mapped_column(Integer, default=42)
    model_version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    results: Mapped[list["OptimizationResult"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    scenarios: Mapped[list["Scenario"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    strategies: Mapped[list["Strategy"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    benchmarks: Mapped[list["BenchmarkResult"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("optimization_jobs.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    market_shocks: Mapped[dict] = mapped_column(JSON, nullable=False)
    probability: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped["OptimizationJob"] = relationship(back_populates="scenarios")


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("optimization_jobs.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    allocations: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    stress_test_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped["OptimizationJob"] = relationship(back_populates="strategies")


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("optimization_jobs.id"), nullable=False)
    solver_name: Mapped[str] = mapped_column(String(100), nullable=False)
    execution_time_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    objective_value: Mapped[float] = mapped_column(Float, nullable=False)
    feasible: Mapped[bool] = mapped_column(Boolean, default=True)
    iterations: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped["OptimizationJob"] = relationship(back_populates="benchmarks")


class OptimizationResult(Base):
    __tablename__ = "optimization_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("optimization_jobs.id"), nullable=False)
    strategy_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("strategies.id"), nullable=True)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    allocation: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped["OptimizationJob"] = relationship(back_populates="results")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    actor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    org_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# ── Extended models (auth security, user prefs, notifications, etc.) ──────────
from app.models.extended import (  # noqa: E402, F401
    ApiKey,
    ConstraintTemplate,
    Notification,
    NotificationType,
    PortfolioSnapshot,
    ScheduledReport,
    UserPreferences,
)
from app.models.integrations import (  # noqa: E402, F401
    APIUsageLog,
    ExportJob,
    Integration,
    ModelExperiment,
    Webhook,
    WebhookDelivery,
)
from app.models.password_reset import (  # noqa: E402, F401
    EmailVerificationToken,
    PasswordResetToken,
    RevokedToken,
)
from app.models.portfolio_access import (  # noqa: E402, F401
    PortfolioAccess,
    PortfolioRole,
)
from app.models.social import (  # noqa: E402, F401
    ActivityLog,
    Attachment,
    Comment,
    SavedFilter,
    SavedView,
    Tag,
    TaggedItem,
    Watchlist,
    WatchlistItem,
)
