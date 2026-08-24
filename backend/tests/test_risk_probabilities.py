"""Tests for the Risk Probabilities Engine."""
import pytest

from app.risk_probabilities import RiskProbabilityEngine, get_risk_summary


@pytest.fixture
def sample_instruments():
    """Sample sovereign debt instruments for testing."""
    return [
        {
            "id": "bond1",
            "name": "US Treasury 10Y",
            "instrument_type": "treasury_bond",
            "currency": "USD",
            "principal_outstanding": 500_000_000,
            "coupon_rate": 0.045,
            "maturity_date": "2030-01-01",
            "issue_date": "2020-01-01",
            "spread_bps": 10,
        },
        {
            "id": "bond2",
            "name": "Eurobond 5Y",
            "instrument_type": "eurobond",
            "currency": "EUR",
            "principal_outstanding": 300_000_000,
            "coupon_rate": 0.035,
            "maturity_date": "2028-06-15",
            "issue_date": "2023-06-15",
            "spread_bps": 50,
        },
        {
            "id": "bond3",
            "name": "Floating Rate Note",
            "instrument_type": "floating_rate_note",
            "currency": "USD",
            "principal_outstanding": 200_000_000,
            "coupon_rate": 0.025,
            "maturity_date": "2027-12-31",
            "issue_date": "2024-12-31",
            "spread_bps": 25,
        },
    ]


@pytest.fixture
def engine():
    return RiskProbabilityEngine(seed=42)


class TestRiskIndicators:
    """Tests for risk indicator calculations."""

    def test_returns_correct_number_of_indicators(self, engine, sample_instruments):
        indicators = engine.calculate_risk_indicators(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
        )
        assert len(indicators) == 7

    def test_indicators_have_required_fields(self, engine, sample_instruments):
        indicators = engine.calculate_risk_indicators(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
        )
        for ind in indicators:
            assert ind.label
            assert ind.description
            assert 0 <= ind.probability <= 1
            assert ind.investment_amount > 0
            assert ind.time_horizon_months > 0
            assert ind.icon

    def test_indicators_to_dict(self, engine, sample_instruments):
        indicators = engine.calculate_risk_indicators(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
        )
        d = indicators[0].to_dict()
        assert "probability_pct" in d
        assert "expected_return_pct_str" in d
        assert "profit_loss_str" in d

    def test_empty_instruments_returns_indicators(self, engine):
        indicators = engine.calculate_risk_indicators(
            portfolio_value=1_000_000,
            instruments=[],
        )
        assert len(indicators) == 7

    def test_different_time_horizons(self, engine, sample_instruments):
        ind_12 = engine.calculate_risk_indicators(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
            time_horizon_months=12,
        )
        ind_24 = engine.calculate_risk_indicators(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
            time_horizon_months=24,
        )
        # 24-month returns should generally be larger in magnitude
        assert len(ind_12) == len(ind_24)


class TestInvestmentScenarios:
    """Tests for concrete investment scenarios."""

    def test_returns_scenarios_for_each_amount(self, engine, sample_instruments):
        scenarios = engine.calculate_investment_scenarios(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
            investment_amounts=[1_000_000, 5_000_000],
        )
        # 4 scenarios per amount (best, expected, downside, worst)
        assert len(scenarios) == 8

    def test_custom_investment_amounts(self, engine, sample_instruments):
        scenarios = engine.calculate_investment_scenarios(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
            investment_amounts=[2_500_000],
        )
        assert len(scenarios) == 4
        assert all(s.investment == 2_500_000 for s in scenarios)

    def test_scenario_to_dict(self, engine, sample_instruments):
        scenarios = engine.calculate_investment_scenarios(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
            investment_amounts=[1_000_000],
        )
        d = scenarios[0].to_dict()
        assert "scenario_name" in d
        assert "investment" in d
        assert "return_amount" in d
        assert "probability_pct" in d
        assert "annualized_return_str" in d

    def test_expected_scenario_positive_for_normal_bonds(self, engine, sample_instruments):
        scenarios = engine.calculate_investment_scenarios(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
            investment_amounts=[1_000_000],
        )
        expected = [s for s in scenarios if s.scenario_name == "Expected Return"]
        assert len(expected) == 1
        # With positive coupons, expected return should be positive over 12 months
        assert expected[0].return_amount > expected[0].investment


class TestRiskScore:
    """Tests for risk score calculations."""

    def test_score_range(self, engine, sample_instruments):
        score = engine.calculate_risk_score(sample_instruments)
        assert 1 <= score.overall_score <= 10

    def test_score_to_dict(self, engine, sample_instruments):
        score = engine.calculate_risk_score(sample_instruments)
        d = score.to_dict()
        assert "overall_score" in d
        assert "label" in d
        assert "color" in d
        assert "description" in d
        assert "factors" in d
        assert "recommendations" in d

    def test_empty_instruments_low_score(self, engine):
        score = engine.calculate_risk_score([])
        assert score.overall_score == 5  # Default for insufficient data

    def test_concentrated_portfolio_higher_risk(self, engine):
        concentrated = [
            {"instrument_type": "treasury_bond", "currency": "USD",
             "principal_outstanding": 1_000_000_000, "coupon_rate": 0.04,
             "maturity_date": "2035-01-01", "spread_bps": 50},
        ]
        diversified = [
            {"instrument_type": "treasury_bond", "currency": "USD",
             "principal_outstanding": 200_000_000, "coupon_rate": 0.04,
             "maturity_date": "2030-01-01", "spread_bps": 20},
            {"instrument_type": "eurobond", "currency": "EUR",
             "principal_outstanding": 200_000_000, "coupon_rate": 0.03,
             "maturity_date": "2028-06-15", "spread_bps": 30},
            {"instrument_type": "t_bill", "currency": "USD",
             "principal_outstanding": 200_000_000, "coupon_rate": 0.02,
             "maturity_date": "2026-12-31", "spread_bps": 5},
            {"instrument_type": "concessional_loan", "currency": "JPY",
             "principal_outstanding": 200_000_000, "coupon_rate": 0.01,
             "maturity_date": "2032-01-01", "spread_bps": 10},
            {"instrument_type": "sovereign_bond", "currency": "GBP",
             "principal_outstanding": 200_000_000, "coupon_rate": 0.035,
             "maturity_date": "2029-06-15", "spread_bps": 40},
        ]
        score_c = engine.calculate_risk_score(concentrated)
        score_d = engine.calculate_risk_score(diversified)
        # Concentrated should generally score higher (riskier)
        assert score_c.overall_score >= score_d.overall_score

    def test_recommendations_not_empty(self, engine, sample_instruments):
        score = engine.calculate_risk_score(sample_instruments)
        assert len(score.recommendations) > 0

    def test_score_labels(self, engine, sample_instruments):
        score = engine.calculate_risk_score(sample_instruments)
        assert score.label in [
            "Very Low Risk", "Low Risk", "Moderate Risk",
            "High Risk", "Very High Risk", "Insufficient Data"
        ]


class TestVaR:
    """Tests for Value-at-Risk calculations."""

    def test_var_returns_multiple_levels(self, engine, sample_instruments):
        var = engine.calculate_var(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
            confidence_levels=[0.95, 0.99],
        )
        assert "var_95" in var
        assert "var_99" in var

    def test_var_99_greater_than_var_95(self, engine, sample_instruments):
        var = engine.calculate_var(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
            confidence_levels=[0.95, 0.99],
        )
        assert var["var_99"]["var_pct"] > var["var_95"]["var_pct"]

    def test_var_has_required_fields(self, engine, sample_instruments):
        var = engine.calculate_var(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
        )
        for key, data in var.items():
            assert "confidence_level" in data
            assert "var_pct" in data
            assert "var_dollar" in data
            assert "cvar_pct" in data
            assert "description" in data

    def test_var_increases_with_time(self, engine, sample_instruments):
        var_short = engine.calculate_var(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
            time_horizon_days=30,
        )
        var_long = engine.calculate_var(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
            time_horizon_days=252,
        )
        assert var_long["var_95"]["var_pct"] > var_short["var_95"]["var_pct"]


class TestGetRiskSummary:
    """Tests for the convenience function."""

    def test_returns_complete_summary(self, sample_instruments):
        summary = get_risk_summary(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
            time_horizon_months=12,
        )
        assert "portfolio_value" in summary
        assert "risk_score" in summary
        assert "indicators" in summary
        assert "investment_scenarios" in summary
        assert "value_at_risk" in summary
        assert "generated_at" in summary

    def test_summary_structure(self, sample_instruments):
        summary = get_risk_summary(
            portfolio_value=1_000_000_000,
            instruments=sample_instruments,
        )
        assert summary["portfolio_value"] == 1_000_000_000
        assert len(summary["indicators"]) == 7
        assert len(summary["investment_scenarios"]) == 12  # 4 scenarios x 3 default amounts
        assert summary["risk_score"]["overall_score"] >= 1

    def test_empty_instruments_summary(self):
        summary = get_risk_summary(
            portfolio_value=1_000_000,
            instruments=[],
        )
        assert summary["portfolio_value"] == 1_000_000
        assert len(summary["indicators"]) == 7
