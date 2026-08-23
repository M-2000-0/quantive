"""End-to-end demonstration of the Quantive pipeline.

Runs the full pipeline on a synthetic sovereign portfolio with Monte Carlo
scenarios, then prints the main result, the four profile strategies, the solver
benchmark, and the per-strategy stress-test summary.

Usage:
    python scripts/demo.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantive.data.fixtures import build_default_problem, demo_portfolio
from quantive.orchestration import run_full_job


def main() -> None:
    portfolio = demo_portfolio()
    problem = build_default_problem()
    problem.scenario_config.monte_carlo_count = 10_000
    problem.scenario_config.monte_carlo_seed = 123

    t0 = time.perf_counter()
    out = run_full_job(portfolio, problem, scenario_seed=123)
    elapsed = time.perf_counter() - t0

    result = out["result"]
    spec = out["spec"]

    print("=" * 72)
    print("QUANTIVE - PUBLIC DEBT OPTIMIZATION (DEMO)")
    print("=" * 72)
    print(f"portfolio        : {portfolio.name}")
    print(f"instruments      : {len(portfolio.instruments)}")
    print(f"financing need   : {problem.financing_requirement:,.0f} {portfolio.reference_currency.value}")
    print(f"scenarios        : {spec.n_scenarios} ({result.metadata['n_scenarios']} total)")
    print(f"pipeline runtime : {elapsed:.1f}s")
    print(f"solver           : {result.solver} [{result.solver_type.value}, {result.execution_backend.value}]")
    print(f"main strategy    : feasible={result.strategy.feasible}")
    print(f"objective        : {result.strategy.objective_value:,.1f}")
    print(f"financing cost   : {result.strategy.financing_cost:,.1f} ({portfolio.reference_currency.value}/yr)")
    print()
    print("risk metrics")
    print(f"  refinancing risk (peak year maturing) : {result.strategy.risk_metrics.refinancing_risk:,.0f}")
    print(f"  floating share                       : {result.strategy.risk_metrics.floating_share:.1%}")
    print(f"  foreign currency share               : {result.strategy.risk_metrics.foreign_currency_share:.1%}")
    print(f"  max single-year maturity share       : {result.strategy.risk_metrics.max_maturity_share:.1%}")
    print()

    print("constraint checks (main strategy)")
    for st in result.strategy.constraint_status:
        if not st.satisfied:
            print(f"  [FAIL] {st.name}: {st.detail}")
    print("  all other constraints satisfied" if all(s.satisfied for s in result.strategy.constraint_status) else "")
    print()

    print("strategies (same constraint set, different risk appetites)")
    print(f"  {'name':<26} {'feasible':<9} {'cost':>10} {'foreign':>8} {'sat%':>6}")
    for s in out["strategies"]:
        st = out["stress"][s.id]
        print(f"  {s.name:<26} {str(s.feasible):<9} {s.financing_cost:>10,.1f} "
              f"{s.risk_metrics.foreign_currency_share:>7.0%} {st.constraint_satisfaction_rate:>5.0%}")
    print()

    print("solver benchmark (feasibility-gated, weighted ranking)")
    for row in out["benchmark"].ranked_rows():
        print(f"  #{row.rank} {row.solver:<22} obj={row.objective_value:>10,.1f} "
              f"runtime={row.runtime:>6.1f}s feasible={row.feasible} "
              f"worst_cost={row.robustness_worst_cost:>9,.1f}")
    print()

    print("stress test (per strategy, across all scenarios)")
    for sid, st in out["stress"].items():
        print(f"  {sid:<28} avg={st.avg_financing_cost:>10,.1f} "
              f"worst={st.worst_financing_cost:>10,.1f} sat={st.constraint_satisfaction_rate:.1%}")
    print("=" * 72)


if __name__ == "__main__":
    main()