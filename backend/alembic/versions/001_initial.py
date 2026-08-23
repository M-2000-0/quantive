"""initial schema with indexes

Revision ID: 001_initial
Revises:
Create Date: 2026-08-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table("users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("1")),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])

    op.create_table("portfolios",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_portfolios_org_id", "portfolios", ["org_id"])

    op.create_table("debt_instruments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("portfolio_id", sa.String(36), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("instrument_type", sa.String(50), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("principal_outstanding", sa.Float, nullable=False),
        sa.Column("coupon_rate", sa.Float, nullable=False),
        sa.Column("maturity_date", sa.String(10), nullable=False),
        sa.Column("issue_date", sa.String(10), nullable=False),
        sa.Column("is_callable", sa.Boolean, server_default=sa.text("0")),
        sa.Column("call_date", sa.String(10), nullable=True),
        sa.Column("call_price", sa.Float, nullable=True),
        sa.Column("spread_bps", sa.Float, server_default=sa.text("0.0")),
        sa.Column("amortization_schedule", sa.JSON, nullable=True),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_debt_instruments_portfolio_id", "debt_instruments", ["portfolio_id"])

    op.create_table("optimization_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("portfolio_id", sa.String(36), sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), server_default="Untitled Optimization"),
        sa.Column("status", sa.String(30), server_default="queued"),
        sa.Column("optimization_type", sa.String(50), server_default="minimize_cost"),
        sa.Column("objectives", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("constraints", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("solver_config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("scenario_config", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("random_seed", sa.Integer, server_default=sa.text("42")),
        sa.Column("model_version", sa.String(50), server_default="1.0.0"),
        sa.Column("progress", sa.Float, server_default=sa.text("0.0")),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_optimization_jobs_org_id", "optimization_jobs", ["org_id"])
    op.create_index("ix_optimization_jobs_status", "optimization_jobs", ["status"])
    op.create_index("ix_optimization_jobs_created_at", "optimization_jobs", ["created_at"])
    op.create_index("ix_optimization_jobs_org_created", "optimization_jobs", ["org_id", "created_at"])

    op.create_table("scenarios",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("optimization_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("scenario_config", sa.JSON, nullable=False),
        sa.Column("market_shocks", sa.JSON, nullable=False),
        sa.Column("probability", sa.Float, server_default=sa.text("1.0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_scenarios_job_id", "scenarios", ["job_id"])

    op.create_table("strategies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("optimization_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("allocations", sa.JSON, nullable=False),
        sa.Column("metrics", sa.JSON, nullable=False),
        sa.Column("stress_test_results", sa.JSON, nullable=True),
        sa.Column("rank", sa.Integer, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_strategies_job_id", "strategies", ["job_id"])

    op.create_table("benchmark_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("optimization_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("solver_name", sa.String(100), nullable=False),
        sa.Column("execution_time_seconds", sa.Float, nullable=False),
        sa.Column("objective_value", sa.Float, nullable=False),
        sa.Column("feasible", sa.Boolean, server_default=sa.text("1")),
        sa.Column("iterations", sa.Integer, server_default=sa.text("0")),
        sa.Column("metrics", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_benchmark_results_job_id", "benchmark_results", ["job_id"])

    op.create_table("optimization_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("optimization_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("strategy_id", sa.String(36), sa.ForeignKey("strategies.id"), nullable=True),
        sa.Column("metrics", sa.JSON, nullable=False),
        sa.Column("allocation", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_optimization_results_job_id", "optimization_results", ["job_id"])

    op.create_table("audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_events_org_id", "audit_events", ["org_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index("ix_audit_events_org_created", "audit_events", ["org_id", "created_at"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("optimization_results")
    op.drop_table("benchmark_results")
    op.drop_table("strategies")
    op.drop_table("scenarios")
    op.drop_table("optimization_jobs")
    op.drop_table("debt_instruments")
    op.drop_table("portfolios")
    op.drop_table("users")
    op.drop_table("organizations")
