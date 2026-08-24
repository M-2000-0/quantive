"""Tests for advanced scenario engines: regime-switching and historical simulation."""
import numpy as np
import pytest

from quantive.scenarios.regime import (
    CRISIS,
    DEFAULT_REGIMES,
    EXPANSION,
    NORMAL,
    STRESS,
    HistoricalSimulationEngine,
    Regime,
    RegimeSwitchingEngine,
)


class TestRegime:
    def test_regime_creation(self):
        """Should create a regime with specified parameters."""
        regime = Regime(
            name="Test",
            interest_rate_shock_mean=0.01,
            interest_rate_shock_std=0.005,
            probability=0.25,
        )
        assert regime.name == "Test"
        assert regime.probability == 0.25

    def test_default_regimes(self):
        """Default regime set should include expansion, normal, stress, crisis."""
        assert len(DEFAULT_REGIMES) == 4
        names = [r.name for r in DEFAULT_REGIMES]
        assert "Expansion" in names
        assert "Normal" in names
        assert "Stress" in names
        assert "Crisis" in names

    def test_regime_probabilities_positive(self):
        """All regime probabilities should be positive."""
        for regime in DEFAULT_REGIMES:
            assert regime.probability > 0


class TestRegimeSwitchingEngine:
    def test_generates_correct_count(self):
        """Should generate exactly the requested number of scenarios."""
        engine = RegimeSwitchingEngine(seed=42)
        scenarios = engine.generate(100)
        assert len(scenarios) == 100

    def test_scenario_fields(self):
        """Each scenario should have all required fields."""
        engine = RegimeSwitchingEngine(seed=42)
        scenarios = engine.generate(10)
        for s in scenarios:
            assert s.id.startswith("regime-")
            assert s.name
            assert s.probability > 0
            assert isinstance(s.interest_rate_shock, float)
            assert isinstance(s.inflation_shock, float)
            assert isinstance(s.fx_shocks, dict)
            assert 0.0 <= s.liquidity_conditions <= 1.0

    def test_regime_distribution(self):
        """Over many scenarios, regime distribution should roughly match probabilities."""
        engine = RegimeSwitchingEngine(seed=42)
        scenarios = engine.generate(10000)

        regime_counts = {}
        for s in scenarios:
            regime = s.id.split("-")[1]
            regime_counts[regime] = regime_counts.get(regime, 0) + 1

        # Normal and expansion should have more scenarios than crisis
        assert regime_counts.get("normal", 0) > regime_counts.get("crisis", 0)

    def test_deterministic(self):
        """Same seed should produce same scenarios."""
        s1 = RegimeSwitchingEngine(seed=42).generate(50)
        s2 = RegimeSwitchingEngine(seed=42).generate(50)
        for a, b in zip(s1, s2):
            assert a.interest_rate_shock == b.interest_rate_shock
            assert a.inflation_shock == b.inflation_shock

    def test_custom_regimes(self):
        """Should support custom regime definitions."""
        custom = [Regime(name="Custom", probability=1.0)]
        engine = RegimeSwitchingEngine(regimes=custom, seed=42)
        scenarios = engine.generate(10)
        for s in scenarios:
            assert "custom" in s.id

    def test_crisis_regime_higher_rates(self):
        """Crisis regime should produce higher interest rate shocks on average."""
        engine = RegimeSwitchingEngine(seed=42)
        scenarios = engine.generate(5000)

        crisis_shocks = [s.interest_rate_shock for s in scenarios if "crisis" in s.id]
        expansion_shocks = [s.interest_rate_shock for s in scenarios if "expansion" in s.id]

        if crisis_shocks and expansion_shocks:
            assert np.mean(crisis_shocks) > np.mean(expansion_shocks)

    def test_zero_count(self):
        """Zero count should return empty list."""
        engine = RegimeSwitchingEngine(seed=42)
        assert engine.generate(0) == []

    def test_fx_shocks_present(self):
        """FX shocks should be present for each scenario."""
        engine = RegimeSwitchingEngine(seed=42)
        scenarios = engine.generate(5)
        for s in scenarios:
            assert len(s.fx_shocks) > 0
            assert "USD" in s.fx_shocks
            assert s.fx_shocks["USD"] == 1.0


class TestHistoricalSimulationEngine:
    def test_generates_correct_count(self):
        """Should generate exactly the requested number of scenarios."""
        engine = HistoricalSimulationEngine(seed=42)
        scenarios = engine.generate(100)
        assert len(scenarios) == 100

    def test_scenario_fields(self):
        """Each scenario should have all required fields."""
        engine = HistoricalSimulationEngine(seed=42)
        scenarios = engine.generate(10)
        for s in scenarios:
            assert s.id.startswith("historical-")
            assert s.probability > 0
            assert isinstance(s.interest_rate_shock, float)

    def test_deterministic(self):
        """Same seed should produce same scenarios."""
        s1 = HistoricalSimulationEngine(seed=42).generate(50)
        s2 = HistoricalSimulationEngine(seed=42).generate(50)
        for a, b in zip(s1, s2):
            assert a.interest_rate_shock == b.interest_rate_shock

    def test_with_historical_data(self):
        """Should work with provided historical data."""
        engine = HistoricalSimulationEngine(seed=42)
        hist_rates = np.random.normal(0.0, 0.015, size=252)
        scenarios = engine.generate(50, historical_rates=hist_rates)
        assert len(scenarios) == 50

    def test_with_historical_fx(self):
        """Should work with provided historical FX data."""
        engine = HistoricalSimulationEngine(seed=42)
        hist_fx = {
            "EUR": np.random.normal(0.0, 0.08, size=252),
            "GBP": np.random.normal(0.0, 0.10, size=252),
        }
        scenarios = engine.generate(50, historical_fx=hist_fx)
        assert len(scenarios) == 50
        for s in scenarios:
            assert "EUR" in s.fx_shocks
            assert "GBP" in s.fx_shocks

    def test_zero_count(self):
        """Zero count should return empty list."""
        engine = HistoricalSimulationEngine(seed=42)
        assert engine.generate(0) == []

    def test_liquidity_bounded(self):
        """Liquidity conditions should be between 0 and 1."""
        engine = HistoricalSimulationEngine(seed=42)
        scenarios = engine.generate(100)
        for s in scenarios:
            assert 0.0 <= s.liquidity_conditions <= 1.0
