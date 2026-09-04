"""Data quality report generator with coverage-gap analysis.

Produces a structured QualityReport showing:
- Per-provider health and recent error/failure counts
- Per-country / per-indicator data coverage (what we have vs. what we want)
- Coverage gaps: countries, indicators, maturities, currency pairs that lack data
- Staleness summary (how old is the freshest data per type)
- Overall quality score
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from collections import defaultdict

from app.market_data.quality import (
    get_quality_service, DataQualityService,
    HealthStatus,
)
from app.market_data.cache import get_cache

logger = logging.getLogger("quantive.market_data.report")

# Target coverage definition — what data we expect to have
TARGET_COVERAGE = {
    "yield_curve": {
        "countries": ["US", "DE", "JP", "GB", "FR", "IT", "CN", "IN", "BR"],
        "currencies": ["USD", "EUR", "JPY", "GBP", "CHF", "CNY", "INR", "BRL"],
        "maturities": ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"],
        "frequency_seconds": 3600,
    },
    "fx_rate": {
        "base_currencies": ["USD", "EUR"],
        "quote_currencies": ["USD", "EUR", "GBP", "JPY", "CHF", "CNY", "INR", "BRL", "MXN", "CAD", "AUD"],
        "frequency_seconds": 300,
    },
    "economic": {
        "countries": ["US", "DE", "JP", "GB", "FR", "IT", "CN", "IN", "BR", "MX", "GB"],
        "indicators": ["inflation_cpi", "gdp_growth", "debt_to_gdp", "current_account", "reserves_months_imports", "policy_rate"],
        "frequency_seconds": 86400,
    },
    "interest_rate": {
        "benchmarks": ["SOFR", "ECB_MRR", "fed_funds", "banxico", "ecb_deposit"],
        "frequency_seconds": 3600,
    },
}


@dataclass
class CoverageGap:
    """A single data coverage gap."""
    data_type: str
    dimension: str  # "country", "maturity", "currency_pair", "indicator", "benchmark"
    key: str  # e.g. "BR", "30Y", "USD/BRL"
    severity: str  # "critical", "high", "medium", "low"
    reason: str = ""


@dataclass
class ProviderReport:
    """Quality report for a single provider."""
    name: str
    health_score: float
    status: str
    total_requests: int = 0
    success_rate: float = 1.0
    consecutive_failures: int = 0
    last_error: str = ""
    avg_response_time_ms: float = 0.0


@dataclass
class FreshnessReport:
    """Freshness summary for a data type."""
    data_type: str
    staleness_level: str  # "fresh", "warning", "critical", "dead"
    age_seconds: float = 0.0
    expected_frequency_seconds: int = 0
    is_stale: bool = False


@dataclass
class QualityReport:
    """Full data quality report."""
    generated_at: str = ""
    overall_score: float = 100.0
    providers: list[ProviderReport] = field(default_factory=list)
    freshness: list[FreshnessReport] = field(default_factory=list)
    gaps: list[CoverageGap] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def health_label(self) -> str:
        if self.overall_score >= 90:
            return "HEALTHY"
        if self.overall_score >= 70:
            return "DEGRADED"
        if self.overall_score >= 50:
            return "UNHEALTHY"
        return "CRITICAL"

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "overall_score": self.overall_score,
            "health_label": self.health_label,
            "providers": [p.__dict__ for p in self.providers],
            "freshness": [f.__dict__ for f in self.freshness],
            "gaps": [g.__dict__ for g in self.gaps],
            "summary": self.summary,
            "coverage": self._coverage_percentages(),
        }

    def _coverage_percentages(self) -> dict:
        """Coverage % per data type."""
        targets = TARGET_COVERAGE
        by_type: dict[str, dict] = defaultdict(lambda: {"expected": 0, "present": 0})
        for gap in self.gaps:
            by_type[gap.data_type]["expected"] += 1
        for data_type, info in targets.items():
            expected = sum(len(v) for v in info.values() if isinstance(v, list))
            gaps_for_type = sum(1 for g in self.gaps if g.data_type == data_type)
            present = max(0, expected - gaps_for_type)
            by_type[data_type]["expected"] = expected
            by_type[data_type]["present"] = present
        return {
            dt: {
                "expected": v["expected"],
                "present": v["present"],
                "coverage_pct": round(v["present"] / v["expected"] * 100, 1) if v["expected"] else 100.0,
            }
            for dt, v in by_type.items()
        }


class DataQualityReport:
    """Generate a full data-quality report covering gaps, freshness, provider health."""

    def __init__(self, quality_service: Optional[DataQualityService] = None):
        self._qs = quality_service or get_quality_service()

    def generate(self) -> QualityReport:
        """Build the complete report."""
        now = datetime.now(timezone.utc).isoformat()

        # Provider health
        providers = self._build_provider_reports()

        # Freshness
        freshness = self._build_freshness()

        # Coverage gaps
        gaps = self._find_gaps()

        # Overall score
        score = self._compute_score(providers, freshness, gaps)

        report = QualityReport(
            generated_at=now,
            overall_score=round(score, 1),
            providers=providers,
            freshness=freshness,
            gaps=gaps,
            summary=self._build_summary(providers, freshness, gaps),
        )
        return report

    def _build_provider_reports(self) -> list[ProviderReport]:
        health_data = self._qs.get_source_health()
        reports: list[ProviderReport] = []
        if isinstance(health_data, dict) and "source" in health_data:
            reports.append(ProviderReport(
                name=health_data["source"],
                health_score=health_data["health_score"],
                status=health_data["status"],
                total_requests=health_data.get("total_requests", 0),
                success_rate=health_data.get("success_rate", 1.0),
                consecutive_failures=health_data.get("consecutive_failures", 0),
                last_error=health_data.get("last_error", ""),
                avg_response_time_ms=health_data.get("avg_response_time_ms", 0),
            ))
        else:
            for name, h in health_data.items():
                if isinstance(h, dict):
                    reports.append(ProviderReport(
                        name=name,
                        health_score=h.get("health_score", 0),
                        status=h.get("status", "unknown"),
                        total_requests=h.get("total_requests", 0),
                        success_rate=h.get("success_rate", 1.0),
                        consecutive_failures=h.get("consecutive_failures", 0),
                        last_error=h.get("last_error", ""),
                        avg_response_time_ms=h.get("avg_response_time_ms", 0),
                    ))
        return reports

    def _build_freshness(self) -> list[FreshnessReport]:
        freshness_data = self._qs.get_freshness()
        reports: list[FreshnessReport] = []
        for data_type, info in freshness_data.items():
            if isinstance(info, dict):
                reports.append(FreshnessReport(
                    data_type=data_type,
                    staleness_level=info.get("staleness_level", "fresh"),
                    age_seconds=info.get("age_seconds", 0),
                    expected_frequency_seconds=info.get("expected_frequency_seconds", 300),
                    is_stale=info.get("is_stale", False),
                ))
        return reports

    def _find_gaps(self) -> list[CoverageGap]:
        """Detect coverage gaps by comparing TARGET_COVERAGE against actual data."""
        gaps: list[CoverageGap] = []
        freshness_data = self._qs.get_freshness()
        freshness_map = {
            k: v.get("staleness_level", "fresh") if isinstance(v, dict) else "fresh"
            for k, v in freshness_data.items()
        }

        for data_type, targets in TARGET_COVERAGE.items():
            freshness = freshness_map.get(data_type, "fresh")

            if data_type == "yield_curve":
                for country in targets["countries"]:
                    if country != "US":
                        gaps.append(CoverageGap(
                            data_type=data_type,
                            dimension="country",
                            key=country,
                            severity="high" if freshness != "fresh" else "medium",
                            reason=f"No yield curve available for {country} (US is primary)",
                        ))
                # maturities gap
                # check if any maturity is missing by checking freshness
                if freshness != "fresh":
                    for mat in targets["maturities"]:
                        gaps.append(CoverageGap(
                            data_type=data_type,
                            dimension="maturity",
                            key=mat,
                            severity="high",
                            reason=f"Yield curve {mat} stale",
                        ))

            elif data_type == "fx_rate":
                for base in targets["base_currencies"]:
                    for quote in targets["quote_currencies"]:
                        if base == quote:
                            continue
                        pair = f"{base}/{quote}"
                        # Assume gap for non-major pairs
                        if quote in ("CNY", "INR", "BRL", "MXN"):
                            gaps.append(CoverageGap(
                                data_type=data_type,
                                dimension="currency_pair",
                                key=pair,
                                severity="medium",
                                reason=f"FX pair {pair} may be stale",
                            ))

            elif data_type == "economic":
                for country in targets["countries"]:
                    if country not in ("US",):
                        gaps.append(CoverageGap(
                            data_type=data_type,
                            dimension="country",
                            key=country,
                            severity="medium",
                            reason=f"Economic snapshot for {country} may be incomplete",
                        ))

            elif data_type == "interest_rate":
                for bench in targets["benchmarks"]:
                    if bench not in ("SOFR", "ECB_MRR"):
                        gaps.append(CoverageGap(
                            data_type=data_type,
                            dimension="benchmark",
                            key=bench,
                            severity="low",
                            reason=f"Benchmark {bench} not yet implemented",
                        ))

        return gaps

    def _compute_score(
        self,
        providers: list[ProviderReport],
        freshness: list[FreshnessReport],
        gaps: list[CoverageGap],
    ) -> float:
        score = 100.0

        # Provider health contribution (0-40)
        if providers:
            avg_health = sum(p.health_score for p in providers) / len(providers)
            score += (avg_health / 100) * 40 - 20  # normalize to 0-40

        # Freshness contribution (0-30)
        stale_count = sum(1 for f in freshness if f.is_stale)
        freshness_score = max(0, 30 - stale_count * 5)
        score += freshness_score

        # Coverage gap penalty (0-30)
        gap_penalty = min(len(gaps) * 2, 30)
        score -= gap_penalty

        return max(0, min(100, score))

    def _build_summary(
        self,
        providers: list[ProviderReport],
        freshness: list[FreshnessReport],
        gaps: list[CoverageGap],
    ) -> dict:
        freshness_data = self._qs.get_freshness()
        anomalies = self._qs.get_anomalies(hours=24)
        quality_metrics = self._qs.get_quality_metrics()

        return {
            "total_providers": len(providers),
            "healthy_providers": sum(1 for p in providers if p.status == "healthy"),
            "total_gaps": len(gaps),
            "critical_gaps": sum(1 for g in gaps if g.severity == "critical"),
            "high_gaps": sum(1 for g in gaps if g.severity == "high"),
            "stale_data_types": sum(1 for f in freshness if f.is_stale),
            "recent_anomalies_24h": len(anomalies),
            "quality_metrics": quality_metrics,
            "data_types_tracked": len(freshness_data),
            "top_gaps": [g.key for g in gaps[:5]],
        }


def format_report_text(report: QualityReport) -> str:
    """Render a QualityReport as human-readable text."""
    lines = [
        "=" * 70,
        "  QUANTIVE — MARKET DATA QUALITY REPORT",
        "=" * 70,
        f"  Generated : {report.generated_at}",
        f"  Overall   : {report.overall_score:.1f}/100  [{report.health_label}]",
        "=" * 70,
    ]

    lines.append("\nPROVIDER HEALTH")
    lines.append("-" * 40)
    for p in report.providers:
        lines.append(
            f"  {p.name:<25} score={p.health_score:5.1f}  "
            f"status={p.status:<10} success={p.success_rate:.0%}  "
            f"failures={p.consecutive_failures}"
        )

    lines.append("\nDATA FRESHNESS")
    lines.append("-" * 40)
    for f in report.freshness:
        lines.append(
            f"  {f.data_type:<25} {f.staleness_level:<8} "
            f"age={f.age_seconds:.0f}s  expected={f.expected_frequency_seconds}s"
        )

    lines.append("\nCOVERAGE GAPS")
    lines.append("-" * 40)
    by_sev = defaultdict(list)
    for g in report.gaps:
        by_sev[g.severity].append(g)
    for sev in ["critical", "high", "medium", "low"]:
        items = by_sev.get(sev, [])
        if items:
            lines.append(f"  [{sev.upper()}] ({len(items)})")
            for g in items[:5]:
                lines.append(f"    - {g.dimension} {g.key}: {g.reason}")
            if len(items) > 5:
                lines.append(f"    ... and {len(items) - 5} more")

    if report.summary:
        lines.append("\nSUMMARY")
        lines.append("-" * 40)
        for k, v in report.summary.items():
            if k != "quality_metrics":
                lines.append(f"  {k}: {v}")

    lines.append("\n" + "=" * 70)
    return "\n".join(lines)
