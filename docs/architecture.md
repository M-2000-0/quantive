# Quantive Architecture

Quantive is a public-debt optimization engine: it models a debt portfolio,
defines an optimization problem with economic scenarios and policy constraints,
solves the problem with multiple interchangeable solver backends, benchmarks the
backends, generates a set of distinct strategies, and stress-tests each strategy
across Monte Carlo scenarios.

```
                    ┌─────────────────────────────────────────────┐
                    │               Pipeline (orchestration)      │
   Portfolio  ──┐   │                                             │
   Problem   ──┼──▶│  scenarios → build_spec → solver ──▶ result  │──▶ API / JSON
   Scenarios ──┘   │  strategies ──▶ benchmark ──▶ stress test    │
                    └─────────────────────────────────────────────┘
```

## Layers

### 1. Models (`quantive/models/`)
Pydantic domain objects that define the entire input/output contract:

- `instruments.py` — `DebtInstrument`, `Portfolio`. Each instrument describes a
  borrowing option: issuer currency, coupon (fixed or floating), liquidity,
  capacity, issue/maturity dates, and a market yield.
- `optimization.py` — `OptimizationProblem` (financing requirement, objective
  weights, constraint set, scenario config, solver config, strategy profile),
  `Constraint`, `EconomicScenario`, `SolverConfiguration`,
  `ScenarioConfiguration`, `NamedStrategyProfiles`.
- `results.py` — `OptimizationResult`, `Strategy`, `RiskMetrics`,
  `ConstraintStatus`, `ScenarioResult`, `StressTestResult`, `BenchmarkResult`,
  `BenchmarkRow`.
- `enums.py` — shared enums (`SolverType`, `ExecutionBackend`, `Currency`,
  `ConstraintType`, `StrategyProfile`, `JobStatus`).

### 2. Data (`quantive/data/`)
- `synthetic.py` — deterministic generator for a realistic sovereign portfolio
  (yield curves, FX volatility, 64 instruments) plus named macro scenarios.
- `fixtures.py` — ready-made demo portfolio, default problem, default
  constraints.

### 3. Scenario engine (`quantive/scenarios/`)
- `definitions.py` — named stress scenarios (base, IR shock, FX shock, credit
  spread widening, liquidity shock).
- `engine.py` — `ScenarioEngine.materialize()` expands the named scenarios and a
  seeded Monte Carlo simulation into the final scenario list. Shocks are
  correlated Gaussian draws applied to interest rates, FX, spreads, and
  liquidity; the seed makes every run reproducible.

### 4. Problem compilation (`quantive/objectives/`)
- `costs.py` — vectorized scenario financing costs, expected cost, interest-rate
  risk, FX risk.
- `spec.py` — `ProblemSpec`: a compiled, numpy-ready representation of
  portfolio + problem + scenarios. Holds the cost matrix, risk vectors,
  per-instrument flags (floating / foreign / liquid), maturity buckets, weights,
  and enabled constraint limits. Also evaluates feasibility and constraint
  violations (used by all solvers and by the stress tester).

### 5. Solvers (`quantive/solvers/`)
All solvers implement the same `SolverInterface` (see
`docs/solver-interface.md`):

- `milp.py` — linear program (CBC via PuLP), globally optimal for linear
  objectives.
- `heuristic.py` — simulated annealing, classical heuristic, no optimality
  guarantee.
- `qubo.py` — quantum-inspired QUBO-encoded annealing on a classical simulator,
  explicitly labelled `QUANTUM_INSPIRED` / `SIMULATOR`.
- `common.py` — box-simplex projection and a maturity-ladder initial allocation.
- `repair.py` — deterministic classical repair that restores feasibility after
  stochastic solvers.
- `registry.py` — name → solver lookup.

### 6. Benchmark (`quantive/benchmark/`)
Runs every registered solver on the same problem and ranks them with
feasibility-gated, weighted min-max normalized metrics
(`docs/benchmarking.md`).

### 7. Stress testing (`quantive/stress/`)
`stress_test()` evaluates a strategy across every scenario and reports average /
worst financing cost, breaches of liquidity, refinancing, and currency limits,
plus an overall constraint satisfaction rate.

### 8. Strategies (`quantive/strategies.py`)
Re-weights the objective per profile (balanced / lowest risk / lowest cost /
stress-resilient robust minimax) under the *same* constraint set, producing four
genuinely different but equally feasible allocations.

### 9. Orchestration (`quantive/orchestration.py`)
`run_full_job()` wires everything into one pipeline returning the main result,
all strategies, the benchmark, stress results, and the scenario list.

### 10. API (`quantive/api/`)
FastAPI application:

- `portfolios.py` — create/list portfolios.
- `optimization.py` — create/list problems, kick off async runs, poll jobs,
  fetch results / strategies / benchmark / stress / scenarios.
- `jobs/manager.py` — thread-pool job manager so the API never blocks.
- `main.py` — the ASGI app.

## Design principles

- **Honest solver claims.** Solver type and execution backend are attached to
  every result. The QUBO path is explicitly a quantum-inspired algorithm on a
  classical simulator; nothing is ever claimed to come from quantum hardware and
  no quantum superiority is implied. See `docs/solver-interface.md`.
- **Reproducibility.** All randomness (scenario generation, annealing seeds) is
  seeded and deterministic.
- **One problem, many backends.** The MILP formulation is canonical; SA and QUBO
  are alternative engines for the same objective, and the benchmark compares
  them fairly.
- **Feasibility is a hard gate.** A solver result that violates constraints is
  not a valid strategy; stochastic solvers run a deterministic repair pass
  before results are reported.