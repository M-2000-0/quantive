from __future__ import annotations

import numpy as np

from quantive.objectives.costs import scenario_cost_matrix
from quantive.objectives.spec import build_spec
from quantive.solvers.common import project_box_simplex, ladder_initial
from quantive.data.fixtures import named_scenarios
from quantive.models.enums import Currency


class TestCostMatrixEdgeCases:
    def test_zero_instruments(self, problem):
        scenarios = named_scenarios()
        matrix = scenario_cost_matrix([], scenarios)
        assert matrix.shape == (0, len(scenarios))

    def test_single_instrument_single_scenario(self):
        from quantive.models.instruments import DebtInstrument
        from quantive.models.enums import RateType
        from quantive.models.optimization import EconomicScenario
        from datetime import date

        inst = DebtInstrument(
            id="i1", name="Bond A", currency=Currency.USD,
            principal=1000.0, coupon=0.05,
            maturity_date=date(2030, 1, 1), issue_date=date(2025, 1, 1),
            rate_type=RateType.FIXED,
        )
        scen = EconomicScenario(id="s1", name="S1", probability=1.0,
                                interest_rate_shock=0.0, inflation_shock=0.0,
                                fx_shocks={}, liquidity_conditions=1.0)
        matrix = scenario_cost_matrix([inst], [scen])
        assert matrix.shape == (1, 1)

    def test_all_floating_rate(self):
        from quantive.models.instruments import DebtInstrument
        from quantive.models.enums import RateType
        from quantive.models.optimization import EconomicScenario
        from datetime import date

        instruments = [
            DebtInstrument(id=f"i{i}", name=f"B{i}", currency=Currency.USD,
                          principal=1000.0, coupon=0.01,
                          maturity_date=date(2030, 1, 1), issue_date=date(2025, 1, 1),
                          rate_type=RateType.FLOATING)
            for i in range(2)
        ]
        scenarios = [
            EconomicScenario(id=f"s{i}", name=f"S{i}", probability=0.5,
                            interest_rate_shock=0.01 * i, inflation_shock=0.0,
                            fx_shocks={}, liquidity_conditions=1.0)
            for i in range(2)
        ]
        matrix = scenario_cost_matrix(instruments, scenarios)
        assert matrix.shape == (2, 2)
        assert not np.any(np.isnan(matrix))


class TestProjection:
    def test_simplex_projection(self):
        v = np.array([0.5, 0.5, 0.5, 0.5])
        caps = np.ones(4)
        result = project_box_simplex(v, caps, 1.0)
        assert abs(np.sum(result) - 1.0) < 1e-9
        assert all(r >= 0 for r in result)

    def test_negative_values(self):
        v = np.array([-1.0, 2.0, 0.0])
        caps = np.ones(3)
        result = project_box_simplex(v, caps, 1.0)
        assert abs(np.sum(result) - 1.0) < 1e-9
        assert all(r >= 0 for r in result)

    def test_already_on_simplex(self):
        v = np.array([1.0, 0.0, 0.0])
        caps = np.ones(3)
        result = project_box_simplex(v, caps, 1.0)
        assert abs(np.sum(result) - 1.0) < 1e-9

    def test_large_values_with_caps(self):
        v = np.array([1000.0, 2000.0, 3000.0])
        caps = np.array([0.5, 0.3, 0.2])
        result = project_box_simplex(v, caps, 1.0)
        assert abs(np.sum(result) - 1.0) < 1e-9
        assert all(r <= cap + 1e-9 for r, cap in zip(result, caps))


class TestSpecEdgeCases:
    def test_build_spec(self, portfolio, problem, scenarios):
        spec = build_spec(portfolio, problem, scenarios)
        assert spec.n_instruments == len(portfolio.instruments)
        assert spec.n_scenarios == len(scenarios)

    def test_ladder_initial(self, portfolio, problem, scenarios):
        spec = build_spec(portfolio, problem, scenarios)
        x = ladder_initial(spec)
        assert abs(x.sum() - spec.financing_requirement) < 1e-6
        assert all(x >= -1e-9)
