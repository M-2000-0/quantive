from __future__ import annotations


from quantive.strategies import generate_strategies
from quantive.models.enums import StrategyProfile


class TestStrategies:
    def test_generates_four_strategies(self, portfolio, problem, scenarios):
        strategies = generate_strategies(portfolio, problem, scenarios)
        assert len(strategies) == 4

    def test_strategies_are_models(self, portfolio, problem, scenarios):
        from quantive.models.results import Strategy
        strategies = generate_strategies(portfolio, problem, scenarios)
        for s in strategies:
            assert isinstance(s, Strategy)

    def test_all_profiles_present(self, portfolio, problem, scenarios):
        strategies = generate_strategies(portfolio, problem, scenarios)
        profiles = {s.profile for s in strategies}
        assert StrategyProfile.BEST_OVERALL in profiles
        assert StrategyProfile.LOWEST_RISK in profiles
        assert StrategyProfile.LOWEST_COST in profiles
        assert StrategyProfile.STRESS_RESILIENT in profiles

    def test_strategies_have_allocations(self, portfolio, problem, scenarios):
        strategies = generate_strategies(portfolio, problem, scenarios)
        for s in strategies:
            assert s.allocation is not None
            assert len(s.allocation) > 0

    def test_strategies_have_names(self, portfolio, problem, scenarios):
        strategies = generate_strategies(portfolio, problem, scenarios)
        for s in strategies:
            assert s.name in ("Best Overall", "Lowest Risk", "Lowest Financing Cost", "Most Stress Resilient")

    def test_strategies_feasible_flag(self, portfolio, problem, scenarios):
        strategies = generate_strategies(portfolio, problem, scenarios)
        for s in strategies:
            assert isinstance(s.feasible, bool)

    def test_distinct_profiles(self, portfolio, problem, scenarios):
        strategies = generate_strategies(portfolio, problem, scenarios)
        profiles = [s.profile for s in strategies]
        assert len(set(profiles)) == len(profiles)

    def test_single_profile(self, portfolio, problem, scenarios):
        strategies = generate_strategies(
            portfolio, problem, scenarios, profiles=[StrategyProfile.LOWEST_COST]
        )
        assert len(strategies) == 1
        assert strategies[0].profile == StrategyProfile.LOWEST_COST

    def test_specific_solver(self, portfolio, problem, scenarios):
        strategies = generate_strategies(portfolio, problem, scenarios, solver_name="milp")
        assert len(strategies) == 4
