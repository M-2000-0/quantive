-- Quantive Row-Level Security Migration
-- Run after table creation to enforce org-level data isolation
-- All queries automatically filtered by org_id via PostgreSQL RLS

-- Enable RLS on all tenant-scoped tables
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE debt_instruments ENABLE ROW LEVEL SECURITY;
ALTER TABLE optimization_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE optimization_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE benchmark_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE database_audit_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_provenance ENABLE ROW LEVEL SECURITY;

-- Create app context function (called on each connection)
CREATE OR REPLACE FUNCTION set_app_context(
    p_user_id UUID,
    p_org_id UUID,
    p_role TEXT
) RETURNS VOID AS 1121
BEGIN
    PERFORM set_config('app.current_user_id', COALESCE(p_user_id::TEXT, ''), true);
    PERFORM set_config('app.current_org_id', COALESCE(p_org_id::TEXT, ''), true);
    PERFORM set_config('app.current_role', COALESCE(p_role, 'viewer'), true);
END;
1121 LANGUAGE plpgsql SECURITY DEFINER;

-- Portfolio RLS: users can only see their org's portfolios
CREATE POLICY portfolio_org_isolation ON portfolios
    USING (org_id = current_setting('app.current_org_id')::UUID);

-- Debt instruments: inherit from portfolio
CREATE POLICY instrument_org_isolation ON debt_instruments
    USING (portfolio_id IN (
        SELECT id FROM portfolios
        WHERE org_id = current_setting('app.current_org_id')::UUID
    ));

-- Optimization jobs: org-scoped
CREATE POLICY optimization_org_isolation ON optimization_jobs
    USING (org_id = current_setting('app.current_org_id')::UUID);

-- Optimization results: inherit from job
CREATE POLICY result_org_isolation ON optimization_results
    USING (job_id IN (
        SELECT id FROM optimization_jobs
        WHERE org_id = current_setting('app.current_org_id')::UUID
    ));

-- Scenarios: inherit from job
CREATE POLICY scenario_org_isolation ON scenarios
    USING (job_id IN (
        SELECT id FROM optimization_jobs
        WHERE org_id = current_setting('app.current_org_id')::UUID
    ));

-- Strategies: inherit from job
CREATE POLICY strategy_org_isolation ON strategies
    USING (job_id IN (
        SELECT id FROM optimization_jobs
        WHERE org_id = current_setting('app.current_org_id')::UUID
    ));

-- Audit events: org-scoped
CREATE POLICY audit_org_isolation ON audit_events
    USING (org_id = current_setting('app.current_org_id')::UUID);

-- Database audit entries: org-scoped
CREATE POLICY audit_entry_org_isolation ON database_audit_entries
    USING (org_id = current_setting('app.current_org_id')::UUID);

-- Data provenance: org-scoped (via resource lookup)
CREATE POLICY provenance_org_isolation ON data_provenance
    USING (resource_id IN (
        SELECT id FROM portfolios
        WHERE org_id = current_setting('app.current_org_id')::UUID
    ));

-- Prevent direct writes to audit tables (append-only via application)
-- Revoke UPDATE/DELETE on audit tables from app role
-- GRANT SELECT, INSERT ON database_audit_entries TO quantive_app;
-- REVOKE UPDATE, DELETE ON database_audit_entries FROM quantive_app;
