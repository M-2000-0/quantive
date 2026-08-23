# Quantive — Public Debt Optimization Engine

Quantive models a sovereign debt portfolio, defines an optimization problem
(financing requirement, objective weights, policy constraints, macro
scenarios), solves it with multiple solver backends, benchmarks them, generates
a set of distinct strategies, and stress-tests every strategy across Monte Carlo
scenarios.

## Quick start

```bash
pip install -r requirements.txt        # or: pip install -e .
python scripts/demo.py                 # end-to-end pipeline on the demo portfolio
python -m pytest tests -q              # run the test suite
uvicorn quantive.api.main:app --reload --port 8000   # REST API (docs at /docs)
```

`scripts/demo.py` runs the full pipeline with 10,000 Monte Carlo scenarios and
prints the main strategy, four profile strategies, the solver benchmark, and the
stress-test summary (~30 s).

## What it does

1. **Model** — instruments (currencies, fixed/floating coupons, liquidity,
   capacity, maturities), portfolios, problems, scenarios.
2. **Compile** — `ProblemSpec`: a numpy-ready, solver-agnostic form of
   portfolio + problem + scenarios (cost matrix, risk vectors, flags, buckets,
   weights, constraint limits).
3. **Solve** — three interchangeable backends behind one interface:
   - `milp_cbc` — classical MILP/LP solved exactly with CBC (globally optimal);
   - `simulated_annealing` — classical heuristic, no optimality guarantee;
   - `qubo_annealing` — quantum-inspired QUBO-encoded annealing on a **classical
     simulator**, explicitly labelled `QUANTUM_INSPIRED` / `SIMULATOR`.
4. **Benchmark** — every backend on the same spec, ranked with
   feasibility-gated, weighted min-max normalized metrics.
5. **Strategies** — four distinct allocations (best overall, lowest risk,
   lowest cost, stress-resilient robust minimax) under the *same* constraints.
6. **Stress** — per-strategy average/worst financing cost and constraint
   satisfaction across all scenarios.

## Documentation

- `docs/architecture.md` — system layers and design principles
- `docs/optimization-model.md` — the mathematical model
- `docs/solver-interface.md` — solver contract and honest quantum reporting
- `docs/scenario-engine.md` — named + Monte Carlo scenarios and the cost model
- `docs/benchmarking.md` — ranking methodology
- `docs/api.md` — REST API reference

## Honest reporting

Quantive treats quantum as a computational capability, not a marketing claim.
Every result carries `solver_type` and `execution_backend`; the QUBO path runs
on a classical simulator, is never claimed to come from real quantum hardware,
and is never assumed superior to the classical solvers. The benchmark decides
that question with data.

## Repository layout

```
quantive/
  models/       Pydantic domain models and enums
  data/         synthetic portfolio generator, fixtures
  scenarios/    named + Monte Carlo scenario engine
  objectives/   costs, ProblemSpec, feasibility checks
  solvers/      milp, simulated annealing, qubo, repair, registry
  benchmark/    metrics + ranking engine
  stress/       stress tester
  strategies.py profile-based strategy generation
  orchestration.py  full pipeline
  api/          FastAPI app and routers
  jobs/         async job manager
tests/          pytest suite
scripts/demo.py end-to-end demo
docs/           this documentation
```