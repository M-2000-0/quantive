#!/usr/bin/env python3
"""Setup Row Level Security on Quantive PostgreSQL database."""
import os
import psycopg2

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "5432")),
    "dbname": os.environ.get("DB_NAME", "quantive"),
    "user": os.environ.get("DB_USER", "quantive"),
    "password": os.environ.get("DB_PASSWORD", ""),
}

def run():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    # ── Extensions ─────────────────────────────────────────────────
    print("Creating extensions...")
    for ext in ["uuid-ossp", "pgcrypto", "pg_trgm"]:
        cur.execute(f'CREATE EXTENSION IF NOT EXISTS "{ext}";')
    print("  Done")

    # ── Custom Types ───────────────────────────────────────────────
    print("Creating custom types...")
    types = {
        "user_role": ["analyst", "senior_analyst", "director", "treasury", "minister", "admin"],
        "optimization_status": ["pending", "running", "completed", "failed", "cancelled"],
        "instrument_type": ["government_bond", "corporate_bond", "green_bond", "treasury_bill", "notes", "loan", "swap", "other"],
        "data_classification": ["public", "internal", "confidential", "secret", "top_secret"],
    }
    for name, vals in types.items():
        vals_str = ", ".join(f"'{v}'" for v in vals)
        cur.execute(f"""
            DO $$ BEGIN
                CREATE TYPE {name} AS ENUM ({vals_str});
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)
    print("  Done")

    # ── Helper Functions (basic, no table refs yet) ────────────────
    print("Creating helper functions...")
    cur.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
        $$ LANGUAGE plpgsql;
    """)
    cur.execute("""
        CREATE OR REPLACE FUNCTION current_user_id()
        RETURNS UUID AS $$
            SELECT NULLIF(current_setting('app.current_user_id', true), '')::UUID;
        $$ LANGUAGE sql STABLE;
    """)
    cur.execute("""
        CREATE OR REPLACE FUNCTION current_org_id()
        RETURNS TEXT AS $$
            SELECT current_setting('app.current_org_id', true);
        $$ LANGUAGE sql STABLE;
    """)
    print("  Done")

    # ── Tables ─────────────────────────────────────────────────────
    print("Creating tables...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            role user_role DEFAULT 'analyst',
            org_id VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT true,
            mfa_enabled BOOLEAN DEFAULT false,
            mfa_secret VARCHAR(255),
            last_login TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
            org_id VARCHAR(255) NOT NULL,
            classification data_classification DEFAULT 'confidential',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    cur.execute("""
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
            country VARCHAR(3),
            org_id VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS optimization_jobs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
            name VARCHAR(255),
            optimization_type VARCHAR(100) NOT NULL,
            status optimization_status DEFAULT 'pending',
            progress DECIMAL(5, 2) DEFAULT 0,
            objectives JSONB DEFAULT '{}',
            constraints JSONB DEFAULT '{}',
            result JSONB,
            error_message TEXT,
            created_by UUID REFERENCES users(id),
            org_id VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            action VARCHAR(100) NOT NULL,
            resource_type VARCHAR(100),
            resource_id UUID,
            details JSONB DEFAULT '{}',
            ip_address INET,
            user_agent TEXT,
            org_id VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS approval_workflows (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            optimization_job_id UUID REFERENCES optimization_jobs(id) ON DELETE CASCADE,
            status VARCHAR(50) DEFAULT 'pending',
            current_approver UUID REFERENCES users(id),
            approval_chain JSONB DEFAULT '[]',
            org_id VARCHAR(255) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS org_settings (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            org_id VARCHAR(255) UNIQUE NOT NULL,
            settings JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)
    print("  Done")

    # ── Create is_admin AFTER users table exists ───────────────────
    print("Creating is_admin function...")
    cur.execute("""
        CREATE OR REPLACE FUNCTION is_admin()
        RETURNS BOOLEAN AS $$
            SELECT EXISTS (
                SELECT 1 FROM users WHERE id = current_user_id() AND role = 'admin'
            );
        $$ LANGUAGE sql STABLE;
    """)
    print("  Done")

    # ── Indexes ────────────────────────────────────────────────────
    print("Creating indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
        "CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id);",
        "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);",
        "CREATE INDEX IF NOT EXISTS idx_portfolios_owner ON portfolios(owner_id);",
        "CREATE INDEX IF NOT EXISTS idx_portfolios_org ON portfolios(org_id);",
        "CREATE INDEX IF NOT EXISTS idx_portfolios_classification ON portfolios(classification);",
        "CREATE INDEX IF NOT EXISTS idx_instruments_portfolio ON instruments(portfolio_id);",
        "CREATE INDEX IF NOT EXISTS idx_instruments_currency ON instruments(currency);",
        "CREATE INDEX IF NOT EXISTS idx_instruments_maturity ON instruments(maturity_date);",
        "CREATE INDEX IF NOT EXISTS idx_instruments_org ON instruments(org_id);",
        "CREATE INDEX IF NOT EXISTS idx_opt_jobs_portfolio ON optimization_jobs(portfolio_id);",
        "CREATE INDEX IF NOT EXISTS idx_opt_jobs_status ON optimization_jobs(status);",
        "CREATE INDEX IF NOT EXISTS idx_opt_jobs_org ON optimization_jobs(org_id);",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_org ON audit_log(org_id);",
        "CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_approval_job ON approval_workflows(optimization_job_id);",
        "CREATE INDEX IF NOT EXISTS idx_approval_org ON approval_workflows(org_id);",
        "CREATE INDEX IF NOT EXISTS idx_org_settings_org ON org_settings(org_id);",
    ]
    for idx in indexes:
        cur.execute(idx)
    print(f"  {len(indexes)} indexes created")

    # ── Triggers ───────────────────────────────────────────────────
    print("Creating triggers...")
    for table in ["users", "portfolios", "instruments", "org_settings"]:
        cur.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)
    print("  Done")

    # ── Roles ──────────────────────────────────────────────────────
    print("Creating roles...")
    for role in ["quantive_app", "quantive_readonly"]:
        cur.execute(f"DO $$ BEGIN CREATE ROLE {role}; EXCEPTION WHEN duplicate_object THEN null; END $$;")
    cur.execute("GRANT USAGE ON SCHEMA public TO quantive_app;")
    cur.execute("GRANT USAGE ON SCHEMA public TO quantive_readonly;")
    all_tables = ["users", "portfolios", "instruments", "optimization_jobs", "audit_log", "approval_workflows", "org_settings"]
    for t in all_tables:
        cur.execute(f"GRANT SELECT, INSERT, UPDATE ON {t} TO quantive_app;")
        cur.execute(f"GRANT SELECT ON {t} TO quantive_readonly;")
    cur.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO quantive_app;")
    print("  Done")

    # ── Enable RLS ─────────────────────────────────────────────────
    print("Enabling Row Level Security...")
    for t in all_tables:
        cur.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;")
        cur.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY;")
    print(f"  RLS enabled and forced on {len(all_tables)} tables")

    # ── RLS Policies ───────────────────────────────────────────────
    print("Creating RLS policies...")

    # Users
    cur.execute("""
        CREATE POLICY users_org_isolation ON users
            FOR ALL USING (org_id = current_org_id() OR is_admin())
            WITH CHECK (org_id = current_org_id());
    """)
    cur.execute("""
        CREATE POLICY users_self_read ON users
            FOR SELECT USING (id = current_user_id() OR org_id = current_org_id());
    """)
    print("  users: 2 policies")

    # Portfolios
    cur.execute("""
        CREATE POLICY portfolios_org_isolation ON portfolios
            FOR ALL USING (org_id = current_org_id() OR is_admin())
            WITH CHECK (org_id = current_org_id());
    """)
    cur.execute("""
        CREATE POLICY portfolios_read_own ON portfolios
            FOR SELECT USING (
                org_id = current_org_id()
                OR owner_id = current_user_id()
                OR is_admin()
            );
    """)
    print("  portfolios: 2 policies")

    # Instruments
    cur.execute("""
        CREATE POLICY instruments_org_isolation ON instruments
            FOR ALL USING (org_id = current_org_id() OR is_admin())
            WITH CHECK (org_id = current_org_id());
    """)
    cur.execute("""
        CREATE POLICY instruments_read_via_portfolio ON instruments
            FOR SELECT USING (
                org_id = current_org_id()
                OR EXISTS (
                    SELECT 1 FROM portfolios
                    WHERE portfolios.id = instruments.portfolio_id
                    AND (portfolios.owner_id = current_user_id() OR portfolios.org_id = current_org_id())
                )
                OR is_admin()
            );
    """)
    print("  instruments: 2 policies")

    # Optimization Jobs
    cur.execute("""
        CREATE POLICY opt_jobs_org_isolation ON optimization_jobs
            FOR ALL USING (org_id = current_org_id() OR is_admin())
            WITH CHECK (org_id = current_org_id());
    """)
    cur.execute("""
        CREATE POLICY opt_jobs_read_own ON optimization_jobs
            FOR SELECT USING (
                org_id = current_org_id()
                OR created_by = current_user_id()
                OR is_admin()
            );
    """)
    print("  optimization_jobs: 2 policies")

    # Audit Log
    cur.execute("""
        CREATE POLICY audit_log_org_isolation ON audit_log
            FOR ALL USING (org_id = current_org_id() OR is_admin())
            WITH CHECK (org_id = current_org_id());
    """)
    cur.execute("""
        CREATE POLICY audit_log_read ON audit_log
            FOR SELECT USING (
                org_id = current_org_id()
                OR user_id = current_user_id()
                OR is_admin()
            );
    """)
    print("  audit_log: 2 policies")

    # Approval Workflows
    cur.execute("""
        CREATE POLICY approval_org_isolation ON approval_workflows
            FOR ALL USING (org_id = current_org_id() OR is_admin())
            WITH CHECK (org_id = current_org_id());
    """)
    cur.execute("""
        CREATE POLICY approval_read_own ON approval_workflows
            FOR SELECT USING (
                org_id = current_org_id()
                OR current_approver = current_user_id()
                OR is_admin()
            );
    """)
    print("  approval_workflows: 2 policies")

    # Org Settings
    cur.execute("""
        CREATE POLICY org_settings_org_isolation ON org_settings
            FOR ALL USING (org_id = current_org_id() OR is_admin())
            WITH CHECK (org_id = current_org_id());
    """)
    cur.execute("""
        CREATE POLICY org_settings_read ON org_settings
            FOR SELECT USING (org_id = current_org_id());
    """)
    print("  org_settings: 2 policies")

    # ── Demo Data ──────────────────────────────────────────────────
    print("Creating demo data...")
    cur.execute("""
        INSERT INTO org_settings (org_id, settings)
        VALUES ('demo-org', '{"name": "Demo Ministry of Finance", "country": "Demo Country"}')
        ON CONFLICT (org_id) DO NOTHING;
    """)
    cur.execute("""
        INSERT INTO users (id, email, hashed_password, full_name, role, org_id) VALUES
            ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'admin@demo.gov', crypt('admin123', gen_salt('bf')), 'Admin User', 'admin', 'demo-org'),
            ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'analyst@demo.gov', crypt('analyst123', gen_salt('bf')), 'Analyst User', 'analyst', 'demo-org'),
            ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'director@demo.gov', crypt('director123', gen_salt('bf')), 'Director User', 'director', 'demo-org')
        ON CONFLICT (id) DO NOTHING;
    """)
    cur.execute("""
        INSERT INTO portfolios (id, name, description, owner_id, org_id, classification) VALUES
            ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'Sovereign Debt Portfolio', 'Main government debt portfolio', 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'demo-org', 'confidential')
        ON CONFLICT (id) DO NOTHING;
    """)
    cur.execute("""
        INSERT INTO instruments (portfolio_id, name, instrument_type, currency, principal_outstanding, coupon_rate, maturity_date, issuer, rating, country, org_id) VALUES
            ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'US Treasury 10Y', 'government_bond', 'USD', 5000000000, 4.25, '2034-06-15', 'US Treasury', 'AAA', 'US', 'demo-org'),
            ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'German Bund 5Y', 'government_bond', 'EUR', 3200000000, 2.85, '2029-09-15', 'German Federal Gov', 'AAA', 'DE', 'demo-org'),
            ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'Green Bond AAA', 'green_bond', 'USD', 1500000000, 3.75, '2031-03-01', 'World Bank', 'AAA', 'US', 'demo-org'),
            ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'UK Gilt 7Y', 'government_bond', 'GBP', 2800000000, 4.10, '2031-07-22', 'UK Debt Management', 'AA', 'GB', 'demo-org'),
            ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'JGB 3Y', 'government_bond', 'JPY', 450000000000, 0.10, '2027-03-20', 'Japan Gov Bond', 'A+', 'JP', 'demo-org'),
            ('d0eebc99-9c0b-4ef8-bb6d-6bb9bd380a44', 'Corporate BBB+', 'corporate_bond', 'USD', 800000000, 5.50, '2028-12-01', 'Various Corps', 'BBB+', 'US', 'demo-org')
        ON CONFLICT DO NOTHING;
    """)
    print("  Demo data created")

    # ── Verify ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RLS SETUP COMPLETE")
    print("=" * 60)

    cur.execute("""
        SELECT relname, relrowsecurity, relforcerowsecurity
        FROM pg_class
        WHERE relnamespace = 'public'::regnamespace AND relkind = 'r'
        ORDER BY relname;
    """)
    print("\nTable RLS Status:")
    for row in cur.fetchall():
        status = "ENABLED" if row[1] else "DISABLED"
        forced = " (FORCED)" if row[2] else ""
        print(f"  {row[0]}: {status}{forced}")

    cur.execute("SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public';")
    print(f"\nTotal RLS Policies: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM users;")
    print(f"Demo Users: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM instruments;")
    print(f"Demo Instruments: {cur.fetchone()[0]}")

    cur.close()
    conn.close()
    print("\nAll done!")

if __name__ == "__main__":
    run()
