"""Comprehensive tests for risk measure objective functions."""
import numpy as np

from quantive.objectives.risk_measures import (
    best_case_cost,
    coherent_risk_report,
    conditional_value_at_risk,
    cost_percentiles,
    cost_stddev,
    cost_variance,
    maximum_drawdown,
    mean_absolutedeviation,
    mean_semivariance,
    value_at_risk,
    worst_case_cost,
)


class TestVaR:
    def test_uniform_distribution(self):
        """VaR of uniform distribution at 95% should be near the 95th percentile."""
        costs = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        var = value_at_risk(costs, confidence_level=0.95)
        assert 9.0 <= var <= 10.0

    def test_deterministic(self):
        """VaR of a single value should be that value."""
        costs = np.array([5.0])
        var = value_at_risk(costs, confidence_level=0.99)
        assert var == 5.0

    def test_high_confidence(self):
        """Higher confidence level should give higher VaR."""
        costs = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
        var_90 = value_at_risk(costs, confidence_level=0.90)
        var_99 = value_at_risk(costs, confidence_level=0.99)
        assert var_99 >= var_90

    def test_empty(self):
        """Empty costs should return 0."""
        assert value_at_risk(np.array([])) == 0.0


class TestCVaR:
    def test_cvar_exceeds_var(self):
        """CVaR should be >= VaR (it's the tail expectation)."""
        costs = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
        var = value_at_risk(costs, confidence_level=0.95)
        cvar = conditional_value_at_risk(costs, confidence_level=0.95)
        assert cvar >= var

    def test_cvar_deterministic(self):
        """CVaR of a single value should be that value."""
        costs = np.array([5.0])
        cvar = conditional_value_at_risk(costs, confidence_level=0.99)
        assert cvar == 5.0

    def test_cvar_symmetric(self):
        """For symmetric distributions, CVaR should be roughly symmetric."""
        costs = np.concatenate([np.ones(50) * 2, np.ones(50) * 8])
        cvar_low = conditional_value_at_risk(costs, confidence_level=0.05)
        cvar_high = conditional_value_at_risk(costs, confidence_level=0.95)
        assert cvar_high >= cvar_low


class TestMeanSemivariance:
    def test_non_negative(self):
        """Semivariance should always be non-negative."""
        costs = np.array([1, 2, 3, 4, 5], dtype=float)
        sv = mean_semivariance(costs)
        assert sv >= 0

    def test_constant_costs(self):
        """Semivariance of constant costs should be 0."""
        costs = np.array([5.0, 5.0, 5.0, 5.0])
        sv = mean_semivariance(costs)
        assert sv == 0.0

    def test_with_custom_target(self):
        """Semivariance with a custom target should work."""
        costs = np.array([1, 2, 3, 4, 5], dtype=float)
        sv = mean_semivariance(costs, target_cost=3.0)
        assert sv > 0


class TestMeanAbsoluteDeviation:
    def test_mad_non_negative(self):
        """MAD should always be non-negative."""
        costs = np.array([1, 2, 3, 4, 5], dtype=float)
        mad = mean_absolutedeviation(costs)
        assert mad >= 0

    def test_mad_constant(self):
        """MAD of constant costs should be 0."""
        costs = np.array([5.0, 5.0, 5.0])
        mad = mean_absolutedeviation(costs)
        assert mad == 0.0


class TestMaximumDrawdown:
    def test_positive_drawdown(self):
        """Max drawdown should be positive for varying costs."""
        costs = np.array([1, 3, 2, 5, 1], dtype=float)
        dd = maximum_drawdown(costs)
        assert dd >= 0

    def test_constant_costs(self):
        """Max drawdown for constant costs should be 0."""
        costs = np.array([5.0, 5.0, 5.0])
        dd = maximum_drawdown(costs)
        assert dd == 0.0


class TestCostVariance:
    def test_variance_non_negative(self):
        """Variance should always be non-negative."""
        costs = np.array([1, 2, 3, 4, 5], dtype=float)
        var = cost_variance(costs)
        assert var >= 0

    def test_variance_constant(self):
        """Variance of constant costs should be 0."""
        costs = np.array([5.0, 5.0, 5.0])
        var = cost_variance(costs)
        assert var == 0.0

    def test_variance_known(self):
        """Variance of [1,2,3,4,5] should be 2.0."""
        costs = np.array([1, 2, 3, 4, 5], dtype=float)
        var = cost_variance(costs)
        assert abs(var - 2.0) < 0.01


class TestCostStddev:
    def test_stddev_matches_variance(self):
        """Stddev should be sqrt of variance."""
        costs = np.array([1, 2, 3, 4, 5], dtype=float)
        std = cost_stddev(costs)
        var = cost_variance(costs)
        assert abs(std - np.sqrt(var)) < 1e-10


class TestCostPercentiles:
    def test_percentiles_sorted(self):
        """Percentiles should be in ascending order."""
        costs = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
        pcts = cost_percentiles(costs)
        values = list(pcts.values())
        assert values == sorted(values)

    def test_median(self):
        """50th percentile should be near the median."""
        costs = np.array([1, 2, 3, 4, 5], dtype=float)
        pcts = cost_percentiles(costs)
        assert abs(pcts["50"] - 3.0) < 1.0


class TestWorstBestCase:
    def test_worst_case(self):
        """Worst case should be max."""
        costs = np.array([1, 5, 3, 8, 2], dtype=float)
        assert worst_case_cost(costs) == 8.0

    def test_best_case(self):
        """Best case should be min."""
        costs = np.array([1, 5, 3, 8, 2], dtype=float)
        assert best_case_cost(costs) == 1.0

    def test_empty(self):
        """Empty should return 0."""
        assert worst_case_cost(np.array([])) == 0.0
        assert best_case_cost(np.array([])) == 0.0


class TestCoherentRiskReport:
    def test_report_completeness(self):
        """Report should contain all risk measures."""
        np.random.seed(42)
        x = np.array([5000, 3000, 2000])
        cost_matrix = np.random.uniform(0.01, 0.06, size=(3, 100))
        probabilities = np.ones(100) / 100

        report = coherent_risk_report(x, cost_matrix, probabilities)

        assert "expected_cost" in report
        assert "var_95" in report
        assert "var_99" in report
        assert "cvar_95" in report
        assert "cvar_99" in report
        assert "mean_semivariance" in report
        assert "mean_absolute_deviation" in report
        assert "variance" in report
        assert "std_dev" in report
        assert "worst_case" in report
        assert "best_case" in report
        assert "max_drawdown" in report
        assert "percentiles" in report

    def test_cvar_exceeds_var_in_report(self):
        """In the report, CVaR should be >= VaR."""
        np.random.seed(42)
        x = np.array([5000, 3000, 2000])
        cost_matrix = np.random.uniform(0.01, 0.06, size=(3, 100))
        probabilities = np.ones(100) / 100

        report = coherent_risk_report(x, cost_matrix, probabilities)
        assert report["cvar_95"] >= report["var_95"]
        assert report["cvar_99"] >= report["var_99"]

    def test_worst_ge_expected(self):
        """Worst case should be >= expected cost."""
        np.random.seed(42)
        x = np.array([5000, 3000, 2000])
        cost_matrix = np.random.uniform(0.01, 0.06, size=(3, 100))
        probabilities = np.ones(100) / 100

        report = coherent_risk_report(x, cost_matrix, probabilities)
        assert report["worst_case"] >= report["expected_cost"]
