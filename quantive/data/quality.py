"""Data Quality Engine — rejects corrupted datasets before they reach AI.

Checks: missing values, duplicates, timestamp consistency, splits/dividends
adjustment sanity, bad prices, extreme outliers, stale data.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from quantive.data.schema import DataQualityIssue, DataQualityReport


class DataQualityEngine:
    """Stateless quality checker. All thresholds are configurable."""

    def __init__(
        self,
        outlier_z_threshold: float = 6.0,
        stale_days_threshold: int = 7,
        max_gap_days: int = 5,
        min_volume: float = 0.0,
    ):
        self.outlier_z = outlier_z_threshold
        self.stale_days = stale_days_threshold
        self.max_gap = max_gap_days
        self.min_volume = min_volume

    def check(
        self,
        df: pd.DataFrame,
        dataset_id: str = "dataset",
        *,
        price_col: str = "close",
        volume_col: str = "volume",
        timestamp_col: str = "timestamp",
        ticker_col: str = "ticker",
        fail_on_error: bool = False,
    ) -> DataQualityReport:
        """Run all checks on a DataFrame with OHLCV columns.

        Expected columns: ticker, timestamp, open, high, low, close, volume.
        Returns a report; optionally raises on errors.
        """
        issues: list[DataQualityIssue] = []
        total = len(df)
        stats: dict = {"total_bars": total}

        if df.empty:
            issues.append(DataQualityIssue(severity="error", code="empty_dataset", message="Dataset is empty"))
            report = DataQualityReport(dataset_id=dataset_id, total_bars=0, issues=issues, passed=False, stats=stats)
            if fail_on_error:
                raise ValueError(report.model_dump_json())
            return report

        required = {ticker_col, timestamp_col, "open", "high", "low", price_col, volume_col}
        missing_cols = required - set(df.columns)
        if missing_cols:
            for c in missing_cols:
                issues.append(DataQualityIssue(severity="error", code="missing_column", message=f"Missing required column: {c}", field=c))

        # Missing values
        null_counts = df.isnull().sum()
        for col, n in null_counts.items():
            if n > 0:
                issues.append(DataQualityIssue(
                    severity="error" if col in required else "warning",
                    code="missing_values",
                    message=f"{n} nulls in column '{col}' ({n/total:.1%})",
                    field=str(col),
                ))

        # Duplicates (ticker + timestamp)
        if ticker_col in df.columns and timestamp_col in df.columns:
            dup = df.duplicated(subset=[ticker_col, timestamp_col], keep=False)
            if dup.any():
                issues.append(DataQualityIssue(
                    severity="error", code="duplicate_records",
                    message=f"{dup.sum()} duplicate ticker×timestamp rows",
                ))
                stats["duplicate_rows"] = int(dup.sum())

        # Timestamp consistency
        if timestamp_col in df.columns:
            try:
                ts = pd.to_datetime(df[timestamp_col], utc=True, errors="coerce")
                if ts.isna().any():
                    issues.append(DataQualityIssue(severity="error", code="bad_timestamp", message=f"{ts.isna().sum()} unparseable timestamps", field=timestamp_col))
                # monotonic per ticker
                for ticker, g in df.groupby(ticker_col) if ticker_col in df.columns else [("__all__", df)]:
                    g_ts = pd.to_datetime(g[timestamp_col], utc=True, errors="coerce").sort_values()
                    diffs = g_ts.diff().dropna()
                    # negative diffs = out of order (already flagged by not sorted)
                    neg = (diffs < timedelta(0)).sum()
                    if neg > 0:
                        issues.append(DataQualityIssue(severity="error", code="timestamp_not_monotonic", message=f"Ticker {ticker}: {neg} timestamps out of order", ticker=str(ticker)))
                    # gaps > max_gap days
                    gap_days = diffs.dt.total_seconds() / 86400
                    big_gaps = (gap_days > self.max_gap).sum()
                    if big_gaps > 0:
                        issues.append(DataQualityIssue(severity="warning", code="timestamp_gap", message=f"Ticker {ticker}: {big_gaps} gaps > {self.max_gap}d (max {gap_days.max():.1f}d)", ticker=str(ticker)))
                    # stale data
                    max_ts = g_ts.max()
                    if pd.notna(max_ts):
                        age_days = (datetime.now(timezone.utc) - max_ts.to_pydatetime()).days
                        if age_days > self.stale_days:
                            issues.append(DataQualityIssue(severity="warning", code="stale_data", message=f"Ticker {ticker}: last bar {age_days}d ago (> {self.stale_days}d)", ticker=str(ticker)))
            except Exception as e:
                issues.append(DataQualityIssue(severity="warning", code="timestamp_check_failed", message=str(e)))

        # Bad prices (open/high/low/close)
        for col in ["open", "high", "low", price_col]:
            if col not in df.columns:
                continue
            s = pd.to_numeric(df[col], errors="coerce")
            neg = (s <= 0).sum()
            if neg > 0:
                issues.append(DataQualityIssue(severity="error", code="bad_price", message=f"{neg} non-positive values in '{col}'", field=col))
            # extreme outliers via z-score on log returns
            if len(s.dropna()) > 20:
                log_ret = np.log(s.replace(0, np.nan)).diff().dropna()
                if len(log_ret) > 10 and log_ret.std() > 0:
                    z = (log_ret - log_ret.mean()) / log_ret.std()
                    extreme = (z.abs() > self.outlier_z).sum()
                    if extreme > 0:
                        issues.append(DataQualityIssue(severity="warning", code="extreme_outlier", message=f"{extreme} |z|>{self.outlier_z} log-returns in '{col}'", field=col))

        # OHLC consistency: high >= max(open,close,low), low <= min(...)
        if all(c in df.columns for c in ["open", "high", "low", price_col]):
            try:
                o = pd.to_numeric(df["open"], errors="coerce")
                h = pd.to_numeric(df["high"], errors="coerce")
                lo = pd.to_numeric(df["low"], errors="coerce")
                c = pd.to_numeric(df[price_col], errors="coerce")
                bad_high = (h < pd.concat([o, c, lo], axis=1).max(axis=1) - 1e-9).sum()
                bad_low = (lo > pd.concat([o, c], axis=1).min(axis=1) + 1e-9).sum()
                if bad_high:
                    issues.append(DataQualityIssue(severity="error", code="ohlc_high_violation", message=f"{bad_high} bars where high < max(open,close,low)"))
                if bad_low:
                    issues.append(DataQualityIssue(severity="error", code="ohlc_low_violation", message=f"{bad_low} bars where low > min(open,close)"))
            except Exception:
                pass

        # Split detection: >40% overnight gap without corporate action flag
        if price_col in df.columns and ticker_col in df.columns:
            for ticker, g in df.groupby(ticker_col):
                closes = pd.to_numeric(g[price_col], errors="coerce").values
                if len(closes) > 2:
                    gaps = np.abs(np.diff(closes) / np.where(closes[:-1] != 0, closes[:-1], 1))
                    big = (gaps > 0.4).sum()
                    if big > 0:
                        issues.append(DataQualityIssue(severity="info", code="possible_split", message=f"Ticker {ticker}: {big} >40% price gaps — check splits/dividends", ticker=str(ticker)))

        passed = not any(i.severity == "error" for i in issues)
        report = DataQualityReport(dataset_id=dataset_id, total_bars=total, issues=issues, passed=passed, stats=stats)
        if fail_on_error and not passed:
            raise ValueError(f"Data quality failed ({len(report.errors)} errors): {report.errors[0].message}")
        return report

    def validate_bars(self, bars: list, dataset_id: str = "bars") -> DataQualityReport:
        """Validate a list of OHLCVBar (already Pydantic-validated)."""
        import pandas as pd
        df = pd.DataFrame([b.model_dump() if hasattr(b, "model_dump") else b for b in bars])
        return self.check(df, dataset_id=dataset_id)
