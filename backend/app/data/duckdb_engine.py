"""DuckDB Local Data Engine — Air-Gapped Sovereign Debt Store.

Provides:
1. Local DuckDB database for yield curves, debt inventory, simulation results
2. Schema versioning for reproducible queries
3. Idempotent upsert operations
4. Offline-first: no external dependencies after initial data load
"""

import json
import os
import time
from datetime import datetime, timezone
from typing import Optional

import duckdb


DB_PATH = os.path.join(os.path.dirname(__file__), "quantive.duckdb")


def get_connection(db_path: str = DB_PATH) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection with schema initialized."""
    conn = duckdb.connect(db_path)
    _init_schema(conn)
    return conn


def _init_schema(conn: duckdb.DuckDBPyConnection):
    """Initialize database schema (idempotent)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS yield_curves (
            id INTEGER PRIMARY KEY DEFAULT 1,
            country_code VARCHAR NOT NULL,
            currency VARCHAR NOT NULL,
            observation_date DATE NOT NULL,
            maturity_months INTEGER NOT NULL,
            rate_pct DOUBLE NOT NULL,
            source VARCHAR DEFAULT 'unknown',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(country_code, observation_date, maturity_months)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS debt_inventory (
            id VARCHAR PRIMARY KEY,
            instrument_name VARCHAR NOT NULL,
            instrument_type VARCHAR NOT NULL,
            currency VARCHAR NOT NULL,
            principal_outstanding DOUBLE NOT NULL,
            coupon_rate DOUBLE NOT NULL,
            maturity_date DATE NOT NULL,
            issue_date DATE NOT NULL,
            is_callable BOOLEAN DEFAULT FALSE,
            call_date DATE,
            call_price DOUBLE,
            spread_bps DOUBLE DEFAULT 0,
            data_quality VARCHAR DEFAULT 'verified',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS simulation_results (
            id INTEGER PRIMARY KEY DEFAULT 1,
            scenario_name VARCHAR NOT NULL,
            portfolio_name VARCHAR NOT NULL,
            mean_value DOUBLE,
            median_value DOUBLE,
            std_dev DOUBLE,
            var_95 DOUBLE,
            var_99 DOUBLE,
            cvar_95 DOUBLE,
            cvar_99 DOUBLE,
            expected_loss DOUBLE,
            max_loss DOUBLE,
            prob_loss_10pct DOUBLE,
            prob_loss_20pct DOUBLE,
            n_simulations INTEGER,
            horizon_months INTEGER,
            parameters_json VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS optimization_runs (
            id INTEGER PRIMARY KEY DEFAULT 1,
            solver_status VARCHAR,
            objective_value DOUBLE,
            allocations_json VARCHAR,
            qubo_cost DOUBLE,
            solve_time_seconds DOUBLE,
            n_variables INTEGER,
            backend VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS policy_briefs (
            id INTEGER PRIMARY KEY DEFAULT 1,
            executive_summary TEXT,
            recommendations_json VARCHAR,
            risk_assessment TEXT,
            issuance_strategy TEXT,
            cost_savings TEXT,
            confidence_level VARCHAR,
            model_used VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


# ── Yield Curve Operations ──────────────────────────────────────────

def upsert_yield_curve(
    conn: duckdb.DuckDBPyConnection,
    country_code: str,
    currency: str,
    observations: list[dict],
    source: str = "api",
):
    """Upsert yield curve observations.

    Args:
        observations: List of {date, maturity_months, rate_pct}
    """
    for obs in observations:
        conn.execute("""
            INSERT OR REPLACE INTO yield_curves
            (country_code, currency, observation_date, maturity_months, rate_pct, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [country_code, currency, obs["date"], obs["maturity_months"], obs["rate_pct"], source])


def get_yield_curve(
    conn: duckdb.DuckDBPyConnection,
    country_code: str = "US",
    as_of_date: Optional[str] = None,
) -> list[dict]:
    """Get latest yield curve for a country."""
    if as_of_date:
        rows = conn.execute("""
            SELECT maturity_months, rate_pct, observation_date
            FROM yield_curves
            WHERE country_code = ? AND observation_date <= ?
            ORDER BY observation_date DESC, maturity_months
        """, [country_code, as_of_date]).fetchall()
    else:
        rows = conn.execute("""
            SELECT maturity_months, rate_pct, observation_date
            FROM yield_curves
            WHERE country_code = ?
            AND observation_date = (SELECT MAX(observation_date) FROM yield_curves WHERE country_code = ?)
            ORDER BY maturity_months
        """, [country_code, country_code]).fetchall()

    return [{"maturity_months": r[0], "rate_pct": r[1], "date": str(r[2])} for r in rows]


# ── Debt Inventory Operations ───────────────────────────────────────

def upsert_debt_instruments(conn: duckdb.DuckDBPyConnection, instruments: list[dict]):
    """Upsert debt instruments into inventory."""
    for inst in instruments:
        conn.execute("""
            INSERT OR REPLACE INTO debt_inventory
            (id, instrument_name, instrument_type, currency, principal_outstanding,
             coupon_rate, maturity_date, issue_date, is_callable, call_date, call_price,
             spread_bps, data_quality)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            inst.get("id", f"INST-{inst['instrument_name'][:8]}"),
            inst["instrument_name"],
            inst.get("instrument_type", "treasury_bond"),
            inst.get("currency", "USD"),
            inst["principal_outstanding"],
            inst["coupon_rate"],
            inst["maturity_date"],
            inst.get("issue_date", "2025-01-01"),
            inst.get("is_callable", False),
            inst.get("call_date"),
            inst.get("call_price"),
            inst.get("spread_bps", 0),
            inst.get("data_quality", "verified"),
        ])


def get_debt_inventory(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    """Get all debt instruments."""
    rows = conn.execute("""
        SELECT id, instrument_name, instrument_type, currency, principal_outstanding,
               coupon_rate, maturity_date, issue_date, is_callable, data_quality
        FROM debt_inventory
        ORDER BY principal_outstanding DESC
    """).fetchall()

    return [{
        "id": r[0], "instrument_name": r[1], "instrument_type": r[2],
        "currency": r[3], "principal_outstanding": r[4], "coupon_rate": r[5],
        "maturity_date": str(r[6]), "issue_date": str(r[7]),
        "is_callable": r[8], "data_quality": r[9],
    } for r in rows]


# ── Simulation & Optimization Storage ───────────────────────────────

def save_simulation_result(conn: duckdb.DuckDBPyConnection, result: dict):
    """Save a Monte Carlo simulation result."""
    conn.execute("""
        INSERT INTO simulation_results
        (scenario_name, portfolio_name, mean_value, median_value, std_dev,
         var_95, var_99, cvar_95, cvar_99, expected_loss, max_loss,
         prob_loss_10pct, prob_loss_20pct, n_simulations, horizon_months, parameters_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        result["scenario_name"], result["portfolio_name"],
        result.get("mean_value"), result.get("median_value"), result.get("std_dev"),
        result.get("var_95"), result.get("var_99"),
        result.get("cvar_95"), result.get("cvar_99"),
        result.get("expected_loss"), result.get("max_loss"),
        result.get("prob_loss_10pct"), result.get("prob_loss_20pct"),
        result.get("n_simulations"), result.get("horizon_months"),
        json.dumps(result.get("parameters", {})),
    ])


def save_optimization_run(conn: duckdb.DuckDBPyConnection, result: dict):
    """Save an optimization run."""
    conn.execute("""
        INSERT INTO optimization_runs
        (solver_status, objective_value, allocations_json, qubo_cost,
         solve_time_seconds, n_variables, backend)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        result.get("solver_status"), result.get("objective_value"),
        json.dumps(result.get("allocations", [])), result.get("qubo_cost"),
        result.get("solve_time_seconds"), result.get("n_variables"),
        result.get("backend"),
    ])


def save_policy_brief(conn: duckdb.DuckDBPyConnection, brief: dict):
    """Save a policy brief."""
    conn.execute("""
        INSERT INTO policy_briefs
        (executive_summary, recommendations_json, risk_assessment,
         issuance_strategy, cost_savings, confidence_level, model_used)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [
        brief.get("executive_summary"), json.dumps(brief.get("key_recommendations", [])),
        brief.get("risk_assessment"), brief.get("issuance_strategy"),
        brief.get("cost_savings_analysis"), brief.get("confidence_level"),
        brief.get("model_used"),
    ])


# ── Analytics Queries ───────────────────────────────────────────────

def get_simulation_history(conn: duckdb.DuckDBPyConnection, limit: int = 50) -> list[dict]:
    """Get recent simulation results."""
    rows = conn.execute("""
        SELECT scenario_name, portfolio_name, mean_value, var_95, cvar_95,
               expected_loss, n_simulations, created_at
        FROM simulation_results
        ORDER BY created_at DESC
        LIMIT ?
    """, [limit]).fetchall()

    return [{
        "scenario_name": r[0], "portfolio_name": r[1],
        "mean_value": r[2], "var_95": r[3], "cvar_95": r[4],
        "expected_loss": r[5], "n_simulations": r[6],
        "created_at": str(r[7]),
    } for r in rows]


def get_yield_history(
    conn: duckdb.DuckDBPyConnection,
    country_code: str = "US",
    maturity_months: int = 120,
    limit: int = 252,
) -> list[dict]:
    """Get historical yield data for a maturity point."""
    rows = conn.execute("""
        SELECT observation_date, rate_pct
        FROM yield_curves
        WHERE country_code = ? AND maturity_months = ?
        ORDER BY observation_date DESC
        LIMIT ?
    """, [country_code, maturity_months, limit]).fetchall()

    return [{"date": str(r[0]), "rate_pct": r[1]} for r in reversed(rows)]


def get_database_stats(conn: duckdb.DuckDBPyConnection) -> dict:
    """Get database statistics."""
    tables = {}
    for table in ["yield_curves", "debt_inventory", "simulation_results", "optimization_runs", "policy_briefs"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        tables[table] = count

    return {
        "tables": tables,
        "total_records": sum(tables.values()),
        "db_path": DB_PATH,
        "db_size_bytes": os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0,
    }
