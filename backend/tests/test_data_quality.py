"""Tests for the Data Quality Framework."""

import pytest
from app.market_data.quality import (
    DataQualityService,
    AnomalyType,
    HealthStatus,
    get_quality_service,
)


@pytest.fixture
def quality_service():
    """Create a fresh quality service for each test."""
    return DataQualityService()


class TestRangeValidation:
    """Test range validation for market data."""

    def test_valid_yield(self, quality_service):
        result = quality_service.validate_range("yield_pct", 4.55, "treasury_yield")
        assert result.is_valid is True

    def test_yield_below_minimum(self, quality_service):
        result = quality_service.validate_range("yield_pct", -5.0, "treasury_yield")
        assert result.is_valid is False
        assert "below minimum" in result.error_message

    def test_yield_above_maximum(self, quality_service):
        result = quality_service.validate_range("yield_pct", 50.0, "treasury_yield")
        assert result.is_valid is False
        assert "above maximum" in result.error_message

    def test_valid_fx_rate(self, quality_service):
        result = quality_service.validate_range("rate", 1.08, "fx_rate")
        assert result.is_valid is True

    def test_fx_rate_too_low(self, quality_service):
        result = quality_service.validate_range("rate", 0.0001, "fx_rate")
        assert result.is_valid is False

    def test_batch_validation(self, quality_service):
        data = [
            {"yield_pct": 4.5, "maturity": "10Y"},
            {"yield_pct": 5.2, "maturity": "2Y"},
        ]
        results = quality_service.validate_batch(data, "treasury_yield")
        assert len(results) >= 2
        assert all(r.is_valid for r in results)


class TestCrossSourceConsistency:
    """Test cross-source consistency checks."""

    def test_consistent_sources(self, quality_service):
        result = quality_service.check_consistency(
            [4.55, 4.56, 4.54],
            ["treasury_gov", "fred", "bloomberg"],
            "yield_10y",
        )
        assert result["consistent"] is True

    def test_divergent_sources(self, quality_service):
        result = quality_service.check_consistency(
            [4.55, 5.50, 4.54],
            ["treasury_gov", "bad_source", "bloomberg"],
            "yield_10y",
        )
        assert result["consistent"] is False
        assert result["max_deviation_pct"] > 10

    def test_single_source(self, quality_service):
        result = quality_service.check_consistency(
            [4.55],
            ["treasury_gov"],
            "yield_10y",
        )
        assert result["consistent"] is True


class TestYieldCurveOrdering:
    """Test yield curve ordering validation."""

    def test_normal_curve(self, quality_service):
        yields = {"2Y": 4.5, "5Y": 4.6, "10Y": 4.7, "30Y": 4.8}
        result = quality_service.check_yield_curve_ordering(yields)
        assert result["normal"] is True

    def test_inverted_curve(self, quality_service):
        yields = {"2Y": 5.0, "5Y": 4.8, "10Y": 4.5, "30Y": 4.3}
        result = quality_service.check_yield_curve_ordering(yields)
        assert result["normal"] is False
        assert len(result["inversions"]) > 0


class TestAnomalyDetection:
    """Test anomaly detection."""

    def test_spike_detection(self, quality_service):
        historical = [4.5, 4.6, 4.5, 4.7, 4.6, 4.5, 4.6]
        anomalies = quality_service.detect_anomalies(
            8.0, historical, "yield_10y", threshold_std=2.0
        )
        assert len(anomalies) > 0
        assert anomalies[0].anomaly_type == AnomalyType.SPIKE

    def test_no_anomaly_normal_data(self, quality_service):
        historical = [4.5, 4.6, 4.5, 4.7, 4.6, 4.5, 4.6]
        anomalies = quality_service.detect_anomalies(
            4.55, historical, "yield_10y", threshold_std=3.0
        )
        assert len(anomalies) == 0

    def test_insufficient_history(self, quality_service):
        historical = [4.5, 4.6]
        anomalies = quality_service.detect_anomalies(
            8.0, historical, "yield_10y"
        )
        assert len(anomalies) == 0


class TestSourceHealth:
    """Test source health scoring."""

    def test_healthy_source(self, quality_service):
        for _ in range(10):
            quality_service.record_fetch("treasury_gov", success=True, response_time_ms=100)
        health = quality_service.get_source_health("treasury_gov")
        assert health["health_score"] >= 90
        assert health["status"] == HealthStatus.HEALTHY.value

    def test_degraded_source(self, quality_service):
        for _ in range(5):
            quality_service.record_fetch("slow_source", success=True, response_time_ms=500)
        for _ in range(5):
            quality_service.record_fetch("slow_source", success=False, error="Timeout")
        health = quality_service.get_source_health("slow_source")
        assert health["health_score"] < 80
        assert health["status"] in [HealthStatus.DEGRADED.value, HealthStatus.UNHEALTHY.value, HealthStatus.CRITICAL.value]

    def test_all_sources_health(self, quality_service):
        quality_service.record_fetch("source_a", success=True)
        quality_service.record_fetch("source_b", success=True)
        health = quality_service.get_source_health()
        assert "source_a" in health
        assert "source_b" in health


class TestFreshnessTracking:
    """Test freshness tracking."""

    def test_fresh_data(self, quality_service):
        quality_service.update_freshness("yield_curve", expected_frequency_seconds=3600)
        freshness = quality_service.get_freshness()
        assert freshness["yield_curve"]["staleness_level"] == "fresh"

    def test_stale_data(self, quality_service):
        import time
        old_time = time.time() - 7200  # 2 hours ago
        quality_service.update_freshness(
            "yield_curve",
            last_updated=old_time,
            expected_frequency_seconds=3600,
        )
        freshness = quality_service.get_freshness()
        assert freshness["yield_curve"]["is_stale"] is True


class TestQualityMetrics:
    """Test overall quality metrics."""

    def test_metrics_completeness(self, quality_service):
        quality_service.record_fetch("src1", success=True)
        quality_service.record_fetch("src1", success=True)
        quality_service.record_fetch("src2", success=False)
        metrics = quality_service.get_quality_metrics()
        assert metrics["completeness"] == pytest.approx(0.667, rel=0.01)

    def test_metrics_structure(self, quality_service):
        metrics = quality_service.get_quality_metrics()
        assert "overall_health_score" in metrics
        assert "completeness" in metrics
        assert "sources" in metrics
        assert "requests" in metrics
        assert "anomalies" in metrics
        assert "freshness" in metrics
