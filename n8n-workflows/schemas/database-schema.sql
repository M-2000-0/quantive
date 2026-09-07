-- Quantive n8n Automation — Canonical Database Schema
-- ============================================================
-- This is THE single source of truth for the n8n workflow segment.
-- (database/schema.sql is a deprecated pointer to this file.)
--
-- Every table/column below was derived from the SQL actually executed
-- inside workflows/*.json Code nodes. If you change workflow SQL,
-- change it here too.
--
-- Run: psql -U quantive -d quantive -f schemas/database-schema.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- WORKFLOWS SCHEMA (logs live in a dedicated Postgres schema;
-- all workflow code writes to workflows.workflow_executions /
-- workflows.workflow_errors / workflows.backup_history)
-- ============================================================

CREATE SCHEMA IF NOT EXISTS workflows;

CREATE TABLE IF NOT EXISTS workflows.workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(100) NOT NULL,
    workflow_name VARCHAR(255) NOT NULL,
    execution_id VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    duration_ms INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflows.workflow_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(100) NOT NULL,
    workflow_name VARCHAR(255) NOT NULL,
    execution_id VARCHAR(100),
    node_id VARCHAR(255),
    node_type VARCHAR(255),
    error_type VARCHAR(100) NOT NULL DEFAULT 'workflow_error',
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'medium',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflows.backup_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_path VARCHAR(500) NOT NULL,
    backup_size VARCHAR(50),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wf_exec_workflow ON workflows.workflow_executions(workflow_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_wf_exec_status ON workflows.workflow_executions(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_wf_exec_created ON workflows.workflow_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_wf_errors_created ON workflows.workflow_errors(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_wf_errors_type ON workflows.workflow_errors(error_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_wf_errors_sev ON workflows.workflow_errors(severity, created_at DESC);

-- ============================================================
-- SALES & CRM (WF-1)
-- ============================================================

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    company VARCHAR(255),
    source VARCHAR(100),
    score INTEGER DEFAULT 0,
    tier VARCHAR(20) DEFAULT 'cold',
    status VARCHAR(50) DEFAULT 'new',
    company_size VARCHAR(50),
    industry VARCHAR(100),
    technology JSONB DEFAULT '[]',
    location VARCHAR(255),
    enriched_data JSONB DEFAULT '{}',
    demo_booked_at TIMESTAMPTZ,
    converted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_tier ON leads(tier);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);

CREATE TABLE IF NOT EXISTS deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_email VARCHAR(255),
    company VARCHAR(255),
    value DECIMAL(12,2) DEFAULT 0,
    stage VARCHAR(50) DEFAULT 'lead',
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(stage, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deals_email ON deals(lead_email);

CREATE TABLE IF NOT EXISTS demos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_email VARCHAR(255),
    lead_name VARCHAR(255),
    company VARCHAR(255),
    demo_date TIMESTAMPTZ,
    demo_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'scheduled',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_demos_status ON demos(status, demo_date DESC);
CREATE INDEX IF NOT EXISTS idx_demos_email ON demos(lead_email);

CREATE TABLE IF NOT EXISTS lead_followups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_email VARCHAR(255) NOT NULL,
    followup_type VARCHAR(50) NOT NULL DEFAULT 'nurture',
    scheduled_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER DEFAULT 0,
    last_attempt TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lead_followups_pending
    ON lead_followups(status, scheduled_at)
    WHERE status = 'pending';

-- ============================================================
-- BILLING & LIFECYCLE (WF-2)
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    company VARCHAR(255),
    deal_id UUID,
    stripe_customer_id VARCHAR(100) UNIQUE,
    plan VARCHAR(50) DEFAULT 'trial',
    status VARCHAR(50) DEFAULT 'active',
    mrr DECIMAL(10,2) DEFAULT 0,
    arr DECIMAL(12,2) DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'usd',
    health_score DECIMAL(5,2) DEFAULT 0,
    last_active_at TIMESTAMPTZ,
    reengagement_sent BOOLEAN DEFAULT FALSE,
    trial_ends_at TIMESTAMPTZ,
    churned_at TIMESTAMPTZ,
    subscription_status VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_stripe ON customers(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_customers_reengagement
    ON customers(last_active_at, reengagement_sent)
    WHERE status = 'active';

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    stripe_subscription_id VARCHAR(100) UNIQUE,
    plan VARCHAR(50),
    status VARCHAR(50),
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_customer ON subscriptions(customer_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);

-- Code writes: (customer_id, amount, event_type, created_at)
CREATE TABLE IF NOT EXISTS mrr_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    amount DECIMAL(10,2) DEFAULT 0,
    event_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mrr_events_customer ON mrr_events(customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mrr_events_type ON mrr_events(event_type, created_at DESC);

-- Code writes: (customer_id, stripe_customer_id, event_type, amount, status, created_at)
CREATE TABLE IF NOT EXISTS invoice_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    stripe_customer_id VARCHAR(100),
    event_type VARCHAR(100) NOT NULL,
    amount DECIMAL(10,2),
    status VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invoice_events_customer ON invoice_events(customer_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_invoice_events_type ON invoice_events(event_type, created_at DESC);

-- Onboarding schedule — spaced email sequences
CREATE TABLE IF NOT EXISTS onboarding_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    plan VARCHAR(50) DEFAULT 'trial',
    current_step INTEGER DEFAULT 1,
    total_steps INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'active',
    next_send_at TIMESTAMPTZ NOT NULL,
    completed_steps JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_onboarding_next_send
    ON onboarding_schedules(next_send_at, status)
    WHERE status = 'active';

-- ============================================================
-- PLATFORM & AI (WF-3)
-- ============================================================

-- Code writes: (symbol, name, value, source, timestamp)
CREATE TABLE IF NOT EXISTS market_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    value DECIMAL(18,8),
    source VARCHAR(100),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data(symbol, timestamp DESC);

-- Code writes: (title, description, url, source, published_at, keywords, created_at)
CREATE TABLE IF NOT EXISTS news_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    url VARCHAR(1000) UNIQUE,
    source VARCHAR(255),
    published_at TIMESTAMPTZ,
    keywords JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_articles_created ON news_articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_articles_url ON news_articles(url);

-- Code writes: (symbol, prediction_type, prediction, confidence, model_version, created_at)
-- Weekly aggregate reads: actual_value
CREATE TABLE IF NOT EXISTS ai_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(50) NOT NULL,
    prediction_type VARCHAR(100),
    prediction JSONB,
    confidence DECIMAL(5,4),
    model_version VARCHAR(50) DEFAULT 'gpt-4',
    actual_value DECIMAL(18,8),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_predictions_symbol ON ai_predictions(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_predictions_created ON ai_predictions(created_at DESC);

-- Code writes: (service, status_code, response_time_ms, status, checked_at)
CREATE TABLE IF NOT EXISTS api_health_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service VARCHAR(255) NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    status VARCHAR(20) NOT NULL,
    checked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_health_service ON api_health_checks(service, checked_at DESC);

CREATE TABLE IF NOT EXISTS watchlist_securities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255),
    target_value DECIMAL(18,8),
    alert_threshold DECIMAL(10,4) DEFAULT 0.05,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_watchlist_active ON watchlist_securities(is_active);

-- ============================================================
-- OPERATIONS (WF-4)
-- ============================================================

-- Code writes: (subject, description, priority, status, customer_email, created_at)
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject VARCHAR(500) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(50) DEFAULT 'open',
    customer_email VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status, priority);
CREATE INDEX IF NOT EXISTS idx_support_tickets_email ON support_tickets(customer_email);

-- ============================================================
-- CROSS-WORKFLOW SERVICES
-- ============================================================

-- svc2-notification dedup + audit trail
-- Code writes: (channel, severity, dedupe_key, message_preview, created_at)
CREATE TABLE IF NOT EXISTS workflow_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel VARCHAR(100) NOT NULL,
    severity VARCHAR(20) DEFAULT 'low',
    dedupe_key VARCHAR(255),
    message_preview VARCHAR(220),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workflow_notifications_dedupe
    ON workflow_notifications(dedupe_key, created_at DESC);

-- ============================================================
-- QUANTIVE PLATFORM TABLES (read-only for workflows — WF-4 digest)
-- These live in the main Quantive application schema.
-- n8n only SELECTs from them; the application owns their DDL.
-- ============================================================
-- organizations, users, portfolios, debt_instruments, api_access_logs,
-- login_attempts are referenced read-only by WF-4 "Generate Digest"
-- and WF-4 "Security Check". They are created and managed by the
-- Quantive backend (backend/app/models.py / Alembic migrations), so
-- they are intentionally NOT defined here.

-- ============================================================
-- MRR / REVENUE REPORTING (aggregates written by WF-2/WF-4 crons)
-- ============================================================

CREATE TABLE IF NOT EXISTS revenue_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    total_mrr DECIMAL(12,2),
    arr DECIMAL(12,2),
    by_plan_json JSONB,
    active_customers INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_revenue_snapshots_date ON revenue_snapshots(date DESC);
