-- Quantive Production Database Initialization
-- Runs automatically on first container start

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- Create custom types
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('analyst', 'senior_analyst', 'director', 'treasury', 'minister', 'admin');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE optimization_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE instrument_type AS ENUM ('government_bond', 'corporate_bond', 'green_bond', 'treasury_bill', 'notes', 'loan', 'swap', 'other');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create tables
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role user_role DEFAULT 'analyst',
    org_id VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    mfa_enabled BOOLEAN DEFAULT false,
    mfa_secret VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES users(id),
    org_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS instruments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    instrument_type instrument_type DEFAULT 'government_bond',
    currency VARCHAR(3) NOT NULL,
    principal_outstanding BIGINT NOT NULL,
    coupon_rate DECIMAL(10, 4),
    maturity_date DATE NOT NULL,
    issuer VARCHAR(255),
    rating VARCHAR(10),
    isin VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS optimization_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID REFERENCES portfolios(id),
    name VARCHAR(255),
    optimization_type VARCHAR(100) NOT NULL,
    status optimization_status DEFAULT 'pending',
    progress DECIMAL(5, 2) DEFAULT 0,
    objectives JSONB DEFAULT '{}',
    constraints JSONB DEFAULT '{}',
    result JSONB,
    error_message TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE TABLE IF NOT EXISTS approval_workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    optimization_job_id UUID REFERENCES optimization_jobs(id),
    status VARCHAR(50) DEFAULT 'pending',
    current_approver UUID REFERENCES users(id),
    approval_chain JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_owner ON portfolios(owner_id);
CREATE INDEX IF NOT EXISTS idx_portfolios_org ON portfolios(org_id);
CREATE INDEX IF NOT EXISTS idx_instruments_portfolio ON instruments(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_instruments_currency ON instruments(currency);
CREATE INDEX IF NOT EXISTS idx_instruments_maturity ON instruments(maturity_date);
CREATE INDEX IF NOT EXISTS idx_optimization_jobs_portfolio ON optimization_jobs(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_optimization_jobs_status ON optimization_jobs(status);
CREATE INDEX IF NOT EXISTS idx_optimization_jobs_created ON optimization_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource_type, resource_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portfolios_updated_at BEFORE UPDATE ON portfolios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_instruments_updated_at BEFORE UPDATE ON instruments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create audit log partitioning (monthly)
-- Auto-create the current month's partition plus one for the next month.
CREATE OR REPLACE FUNCTION create_audit_partition(target_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    start_date DATE;
    end_date DATE;
BEGIN
    start_date := DATE_TRUNC('month', target_date);
    end_date := start_date + INTERVAL '1 month';
    partition_name := 'audit_log_' || TO_CHAR(start_date, 'YYYY_MM');
    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        EXECUTE format(
            'CREATE TABLE %I PARTITION OF audit_log FOR VALUES FROM (%L) TO (%L)',
            partition_name, start_date, end_date
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

SELECT create_audit_partition(CURRENT_DATE);
SELECT create_audit_partition(CURRENT_DATE + INTERVAL '1 month');

-- Auto-create the partition for any row whose month has no partition yet.
CREATE OR REPLACE FUNCTION audit_log_partition_trigger()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM create_audit_partition(NEW.created_at::DATE);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_log_auto_partition
BEFORE INSERT ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_partition_trigger();

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO quantive;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO quantive;
