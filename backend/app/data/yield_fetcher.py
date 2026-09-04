"""Async Yield Curve Fetcher — Real Data into DuckDB.

Pulls sovereign yield curves, TIPS, CDS spreads, and macro benchmarks
from FRED API and stores locally for air-gapped operation.

Usage:
    fetcher = YieldFetcher()
    await fetcher.fetch_all()
    curve = fetcher.get_latest_curve("US")
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

import duckdb

from app.data.duckdb_engine import get_connection, upsert_yield_curve


# FRED Series IDs for US Treasury yields
FRED_YIELD_SERIES = {
    3: "DGS3MO",     # 3-Month
    6: "DGS6MO",     # 6-Month
    12: "DGS1",      # 1-Year
    24: "DGS2",      # 2-Year
    36: "DGS3",      # 3-Year
    60: "DGS5",      # 5-Year
    84: "DGS7",      # 7-Year
    120: "DGS10",    # 10-Year
    180: "DGS20",    # 20-Year
    360: "DGS30",    # 30-Year
}

# FRED Series for TIPS (Inflation-Indexed)
FRED_TIPS_SERIES = {
    120: "DFII10",   # 10-Year TIPS
    60: "DFII5",     # 5-Year TIPS
    360: "DFII30",   # 30-Year TIPS
}

# Macro indicators
FRED_MACRO_SERIES = {
    "gdp_growth": "A191RL1Q225SBEA",    # Real GDP Growth
    "inflation_cpi": "CPIAUCSL",         # CPI
    "unemployment": "UNRATE",            # Unemployment Rate
    "fed_funds": "FEDFUNDS",            # Federal Funds Rate
    "10y_2y_spread": "T10Y2Y",          # 10Y-2Y Spread
}

FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")


class YieldFetcher:
    """Fetch yield curve data from FRED and store in DuckDB."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.conn = get_connection(db_path) if db_path else get_connection()

    def fetch_fred_series(
        self,
        series_id: str,
        start_date: str = "2020-01-01",
        end_date: Optional[str] = None,
    ) -> list[dict]:
        """Fetch a single FRED series."""
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        url = f"{FRED_BASE_URL}?series_id={series_id}&observation_start={start_date}&observation_end={end_date}&file_type=json&api_key={FRED_API_KEY or 'DEMO_KEY'}"

        try:
            req = Request(url, headers={"User-Agent": "Quantive/1.0"})
            resp = urlopen(req, timeout=15)
            data = json.loads(resp.read())

            observations = []
            for obs in data.get("observations", []):
                if obs["value"] != ".":
                    observations.append({
                        "date": obs["date"],
                        "value": float(obs["value"]),
                    })
            return observations

        except Exception as e:
            print(f"[YieldFetcher] Warning: Failed to fetch {series_id}: {e}")
            return []

    def fetch_yield_curve(self, country_code: str = "US", days_back: int = 30) -> list[dict]:
        """Fetch and store yield curve data."""
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        all_observations = []

        for maturity_months, series_id in FRED_YIELD_SERIES.items():
            obs = self.fetch_fred_series(series_id, start_date)
            for o in obs:
                all_observations.append({
                    "date": o["date"],
                    "maturity_months": maturity_months,
                    "rate_pct": o["value"],
                })

        if all_observations:
            upsert_yield_curve(self.conn, country_code, "USD", all_observations, source="fred")
            print(f"[YieldFetcher] Stored {len(all_observations)} yield observations for {country_code}")

        return all_observations

    def fetch_tips(self, days_back: int = 30) -> list[dict]:
        """Fetch TIPS (inflation-indexed) yields."""
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        observations = []

        for maturity_months, series_id in FRED_TIPS_SERIES.items():
            obs = self.fetch_fred_series(series_id, start_date)
            for o in obs:
                observations.append({
                    "date": o["date"],
                    "maturity_months": maturity_months,
                    "rate_pct": o["value"],
                })

        if observations:
            upsert_yield_curve(self.conn, "US_TIPS", "USD", observations, source="fred_tips")
            print(f"[YieldFetcher] Stored {len(observations)} TIPS observations")

        return observations

    def fetch_macro_indicators(self) -> dict:
        """Fetch macroeconomic indicators."""
        results = {}
        for name, series_id in FRED_MACRO_SERIES.items():
            obs = self.fetch_fred_series(series_id, start_date="2024-01-01")
            if obs:
                results[name] = obs[-1]["value"]  # Latest value
                results[f"{name}_date"] = obs[-1]["date"]
        return results

    def fetch_all(self) -> dict:
        """Fetch all data sources and store in DuckDB."""
        print("[YieldFetcher] Starting full data sync...")
        start = time.time()

        yield_data = self.fetch_yield_curve(days_back=90)
        tips_data = self.fetch_tips(days_back=90)
        macro_data = self.fetch_macro_indicators()

        elapsed = time.time() - start
        print(f"[YieldFetcher] Full sync completed in {elapsed:.1f}s")

        return {
            "yield_observations": len(yield_data),
            "tips_observations": len(tips_data),
            "macro_indicators": macro_data,
            "elapsed_seconds": round(elapsed, 2),
        }

    def get_latest_curve(self, country_code: str = "US") -> dict:
        """Get the latest yield curve as a simple dict."""
        rows = self.conn.execute("""
            SELECT maturity_months, rate_pct
            FROM yield_curves
            WHERE country_code = ?
            AND observation_date = (
                SELECT MAX(observation_date) FROM yield_curves WHERE country_code = ?
            )
            ORDER BY maturity_months
        """, [country_code, country_code]).fetchall()

        if not rows:
            # No data available — return empty dict (no mock fallback)
            return {}

        label_map = {3: "3M", 6: "6M", 12: "1Y", 24: "2Y", 36: "3Y", 60: "5Y", 84: "7Y", 120: "10Y", 180: "20Y", 360: "30Y"}
        return {label_map.get(r[0], f"{r[0]}M"): r[1] / 100 for r in rows}

    def close(self):
        """Close database connection."""
        self.conn.close()


# Singleton for convenience
_fetcher: Optional[YieldFetcher] = None


def get_yield_fetcher() -> YieldFetcher:
    """Get or create the singleton yield fetcher."""
    global _fetcher
    if _fetcher is None:
        _fetcher = YieldFetcher()
    return _fetcher
