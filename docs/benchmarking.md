# Benchmarking

The benchmark runs every registered solver on the *same* `ProblemSpec` and
ranks the results with a transparent, configurable methodology. Quantive never
declares a "winner" a priori — the ranking is data-driven, and feasibility is a
hard gate.

## Metrics

For each solver, `quantive/benchmark/metrics.py` computes a `BenchmarkRow`:

| Metric | Meaning | Direction |
|---|---|---|
| `objective_value` | Canonical composite objective of the solution | lower is better |
| `feasibility` | Whether every constraint is satisfied | true is better |
| `constraint_violations` | Number of violated constraints | lower is better |
| `constraint_violation_magnitude` | Total violation magnitude | lower is better |
| `risk_total` | `IR risk + FX risk + refinancing risk` | lower is better |
| `robustness_worst_cost` | Worst financing cost across all scenarios (from the stress tester) | lower is better |
| `runtime` | Wall-clock solve time (seconds) | lower is better |
| `compute_cost` | Objective evaluations performed (stochastic solvers) | lower is better |

All metrics are evaluated on the same spec, so they are comparable across
backends. The stress metrics are produced by the same `stress_test` used
elsewhere.

## Ranking methodology

`quantive/benchmark/ranking.py`:

1. **Normalize** each scored metric to `[0, 1]` with min-max scaling; metrics
   where "lower is better" are inverted so that, in every column, **larger =
   better**.
2. **Weight** the normalized metrics with the configured weights:
   `objective_value × 1.0`, `feasibility × 2.0`, `runtime × 0.4`,
   `constraint_violations × 1.5`, `robustness_worst_cost × 0.8`,
   `compute_cost × 0.3`.
3. **Gate on feasibility**: any solver whose solution violates a constraint has
   `100` points subtracted from its score, so infeasible solvers rank below all
   feasible ones regardless of the other metrics.
4. Ties are broken by `objective_value`.

The weights are configurable (`ranking_weights` argument of
`run_benchmark`), letting a user define what "best" means (e.g. a runtime-focus
vs a worst-case-focus ranking).

## Usage

```python
from quantive.benchmark.engine import run_benchmark

benchmark = run_benchmark(portfolio, problem, scenarios)
for row in benchmark.ranked_rows():
    print(row.rank, row.solver, row.objective_value, row.runtime)
```

On the bundled demo problem the methodology ranks `milp_cbc` first (globally
optimal, sub-second), `simulated_annealing` second (within ~1% of the MILP
objective), and `qubo_annealing` third — see `scripts/demo.py`.

## Intent

The benchmark exists to (a) validate every backend on the same objective, (b)
surface the classical exact solver as the reference, and (c) make it explicit —
without claims of quantum superiority — how each alternative engine compares on
objective quality, robustness, and cost.