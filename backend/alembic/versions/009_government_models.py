"""Add government models for transparency index, pilot programs, and related tables

Revision ID: 009_government_models
Revises: 72f492cf0553
Create Date: 2026-09-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '009_government_models'
down_revision: Union[str, None] = '72f492cf0553'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sovereign_debt_index table
    op.create_table(
        'sovereign_debt_index',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('country_code', sa.String(3), nullable=False, unique=True),
        sa.Column('country_name', sa.String(255), nullable=False),
        sa.Column('region', sa.String(100), nullable=False),
        sa.Column('income_group', sa.String(50), nullable=False),
        sa.Column('overall_score', sa.Float, nullable=False),
        sa.Column('tier', sa.String(20), nullable=False),
        sa.Column('rank', sa.Integer, nullable=True),
        sa.Column('disclosure_score', sa.Float, server_default='0.0'),
        sa.Column('data_access_score', sa.Float, server_default='0.0'),
        sa.Column('institutional_score', sa.Float, server_default='0.0'),
        sa.Column('reporting_freq_score', sa.Float, server_default='0.0'),
        sa.Column('audit_trail_score', sa.Float, server_default='0.0'),
        sa.Column('digital_infra_score', sa.Float, server_default='0.0'),
        sa.Column('compliance_score', sa.Float, server_default='0.0'),
        sa.Column('stakeholder_score', sa.Float, server_default='0.0'),
        sa.Column('data_sources', sa.JSON, nullable=True),
        sa.Column('methodology_version', sa.String(20), server_default='1.0'),
        sa.Column('assessment_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('next_assessment', sa.DateTime(timezone=True), nullable=True),
        sa.Column('strengths', sa.JSON, nullable=True),
        sa.Column('weaknesses', sa.JSON, nullable=True),
        sa.Column('recommendations', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Create index_methodology table
    op.create_table(
        'index_methodology',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('version', sa.String(20), nullable=False, unique=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('category_weights', sa.JSON, nullable=False),
        sa.Column('scoring_criteria', sa.JSON, nullable=False),
        sa.Column('data_sources', sa.JSON, nullable=False),
        sa.Column('is_current', sa.Boolean, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Create index_history table
    op.create_table(
        'index_history',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('country_code', sa.String(3), nullable=False),
        sa.Column('overall_score', sa.Float, nullable=False),
        sa.Column('tier', sa.String(20), nullable=False),
        sa.Column('rank', sa.Integer, nullable=True),
        sa.Column('assessment_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('category_scores', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Create government_pilots table
    op.create_table(
        'government_pilots',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('country_code', sa.String(3), nullable=False),
        sa.Column('country_name', sa.String(255), nullable=False),
        sa.Column('government_entity', sa.String(255), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('contact_name', sa.String(255), nullable=False),
        sa.Column('contact_title', sa.String(255), nullable=False),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('total_debt_outstanding', sa.Float, nullable=False),
        sa.Column('annual_issuance', sa.Float, nullable=False),
        sa.Column('currency', sa.String(3), server_default='USD'),
        sa.Column('debt_to_gdp', sa.Float, server_default='0.0'),
        sa.Column('portfolio_tier', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extension_months', sa.Integer, server_default='0'),
        sa.Column('financing_cost_reduction_bps', sa.Float, server_default='0.0'),
        sa.Column('risk_score_improvement_pct', sa.Float, server_default='0.0'),
        sa.Column('report_generation_time_min', sa.Float, server_default='0.0'),
        sa.Column('user_adoption_rate_pct', sa.Float, server_default='0.0'),
        sa.Column('conversion_status', sa.String(20), server_default='pending'),
        sa.Column('conversion_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('conversion_value_usd', sa.Float, server_default='0.0'),
        sa.Column('contract_term_years', sa.Integer, server_default='0'),
        sa.Column('case_study_published', sa.Boolean, server_default='0'),
        sa.Column('case_study_url', sa.String(500), nullable=True),
        sa.Column('testimonial_allowed', sa.Boolean, server_default='0'),
        sa.Column('data_for_training', sa.Boolean, server_default='0'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('metadata_json', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Create pilot_milestones table
    op.create_table(
        'pilot_milestones',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('pilot_id', sa.String(36), nullable=False),
        sa.Column('milestone_name', sa.String(255), nullable=False),
        sa.Column('milestone_type', sa.String(50), nullable=False),
        sa.Column('target_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Create pilot_metrics table
    op.create_table(
        'pilot_metrics',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('pilot_id', sa.String(36), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float, nullable=False),
        sa.Column('metric_unit', sa.String(50), nullable=False),
        sa.Column('recorded_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Create pilot_case_studies table
    op.create_table(
        'pilot_case_studies',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('pilot_id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('subtitle', sa.String(500), nullable=True),
        sa.Column('executive_summary', sa.Text, nullable=True),
        sa.Column('challenge', sa.Text, nullable=True),
        sa.Column('solution', sa.Text, nullable=True),
        sa.Column('results', sa.JSON, nullable=True),
        sa.Column('testimonials', sa.JSON, nullable=True),
        sa.Column('metrics', sa.JSON, nullable=True),
        sa.Column('status', sa.String(20), server_default='draft'),
        sa.Column('published_url', sa.String(500), nullable=True),
        sa.Column('published_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Create indexes
    op.create_index('ix_sovereign_debt_index_country_code', 'sovereign_debt_index', ['country_code'])
    op.create_index('ix_sovereign_debt_index_tier', 'sovereign_debt_index', ['tier'])
    op.create_index('ix_index_history_country_code', 'index_history', ['country_code'])
    op.create_index('ix_government_pilots_country_code', 'government_pilots', ['country_code'])
    op.create_index('ix_government_pilots_status', 'government_pilots', ['status'])
    op.create_index('ix_pilot_milestones_pilot_id', 'pilot_milestones', ['pilot_id'])
    op.create_index('ix_pilot_metrics_pilot_id', 'pilot_metrics', ['pilot_id'])
    op.create_index('ix_pilot_case_studies_pilot_id', 'pilot_case_studies', ['pilot_id'])


def downgrade() -> None:
    op.drop_index('ix_pilot_case_studies_pilot_id')
    op.drop_index('ix_pilot_metrics_pilot_id')
    op.drop_index('ix_pilot_milestones_pilot_id')
    op.drop_index('ix_government_pilots_status')
    op.drop_index('ix_government_pilots_country_code')
    op.drop_index('ix_index_history_country_code')
    op.drop_index('ix_sovereign_debt_index_tier')
    op.drop_index('ix_sovereign_debt_index_country_code')

    op.drop_table('pilot_case_studies')
    op.drop_table('pilot_metrics')
    op.drop_table('pilot_milestones')
    op.drop_table('government_pilots')
    op.drop_table('index_history')
    op.drop_table('index_methodology')
    op.drop_table('sovereign_debt_index')
