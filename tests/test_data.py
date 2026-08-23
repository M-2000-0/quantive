from __future__ import annotations


from quantive.data.synthetic import generate_synthetic_portfolio
from quantive.data.fixtures import demo_portfolio, named_scenarios, build_default_problem


class TestSyntheticPortfolioGenerator:
    def test_generates_portfolio(self):
        portfolio = generate_synthetic_portfolio(seed=42, portfolio_id="test")
        assert len(portfolio.instruments) > 0

    def test_portfolio_has_required_fields(self):
        portfolio = generate_synthetic_portfolio(seed=42, portfolio_id="test")
        for inst in portfolio.instruments:
            assert inst.name is not None
            assert inst.rate_type is not None
            assert inst.currency is not None
            assert inst.principal > 0
            assert inst.coupon is not None
            assert inst.maturity_date is not None

    def test_deterministic_with_seed(self):
        p1 = generate_synthetic_portfolio(seed=42, portfolio_id="test")
        p2 = generate_synthetic_portfolio(seed=42, portfolio_id="test")
        assert len(p1.instruments) == len(p2.instruments)
        assert p1.instruments[0].name == p2.instruments[0].name

    def test_different_seeds_differ(self):
        p1 = generate_synthetic_portfolio(seed=42, portfolio_id="test")
        p2 = generate_synthetic_portfolio(seed=99, portfolio_id="test")
        assert p1.total_capacity() != p2.total_capacity()


class TestFixtures:
    def test_demo_portfolio(self):
        portfolio = demo_portfolio()
        assert len(portfolio.instruments) > 0
        assert all(i.principal > 0 for i in portfolio.instruments)

    def test_named_scenarios(self):
        scenarios = named_scenarios()
        assert len(scenarios) == 6

    def test_named_scenarios_probabilities(self):
        scenarios = named_scenarios()
        total = sum(s.probability for s in scenarios)
        assert abs(total - 1.0) < 1e-9

    def test_build_default_problem(self):
        problem = build_default_problem()
        assert problem is not None
        assert problem.financing_requirement > 0
        assert problem.solver_config is not None
