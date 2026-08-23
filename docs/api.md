# API

Quantive exposes a FastAPI application (`quantive/api/main.py`). It stores
portfolios and problems in memory and runs optimization jobs on a background
thread pool, so the API never blocks on a solve.

## Running the server

```bash
uvicorn quantive.api.main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/docs

## Endpoints

### Portfolios (`/portfolios`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/portfolios` | Create a portfolio from a synthetic generator (`{"generator": "synthetic", "seed": ...}`) or from an uploaded instrument list |
| `GET` | `/portfolios` | List all portfolios |
| `GET` | `/portfolios/{id}` | Get one portfolio |

### Optimization (`/optimization`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/optimization` | Create an `OptimizationProblem` for a portfolio (financing requirement, objectives, constraints, scenario + solver config, strategy profile) |
| `GET` | `/optimization` | List all problems |
| `GET` | `/optimization/{id}` | Get one problem |
| `POST` | `/optimization/{id}/run` | Start an async run; returns a `job_id` (`202`) |
| `GET` | `/optimization/{id}/results` | The main `OptimizationResult` (status + strategy + scenario results) |
| `GET` | `/optimization/{id}/strategies` | The four profile strategies |
| `GET` | `/optimization/{id}/benchmark` | The ranked solver benchmark |
| `GET` | `/optimization/{id}/stress` | Per-strategy stress test results |
| `GET` | `/optimization/{id}/scenarios?limit=N` | The scenario list (truncate with `limit`) |
| `GET` | `/optimization/jobs/{job_id}` | Poll a job: `queued` → `running` → `completed`/`failed`; on completion the run payload is published to the problem's endpoints |

## Example flow

```bash
# 1. create a portfolio
curl -X POST localhost:8000/portfolios \
  -H 'Content-Type: application/json' \
  -d '{"name":"Demo","generator":"synthetic","seed":7}'

# 2. create a problem
curl -X POST localhost:8000/optimization \
  -H 'Content-Type: application/json' \
  -d '{"portfolio_id":"portfolio-<id>","name":"Baseline","profile":"best_overall","financing_requirement":120000}'

# 3. run (async)
curl -X POST localhost:8000/optimization/problem-<id>/run

# 4. poll until completed
curl -X GET localhost:8000/optimization/jobs/<job_id>

# 5. fetch results
curl -X GET localhost:8000/optimization/problem-<id>/results
curl -X GET localhost:8000/optimization/problem-<id>/strategies
curl -X GET localhost:8000/optimization/problem-<id>/benchmark
curl -X GET localhost:8000/optimization/problem-<id>/stress
```

## Data model

- `Portfolio` — reference currency, description, tags, instrument list.
- `OptimizationProblem` — financing requirement, objective weights, constraint
  list, `ScenarioConfiguration`, `SolverConfiguration`, strategy profile.
- Results are the Pydantic models from `quantive/models/results.py`
  (`OptimizationResult`, `Strategy`, `RiskMetrics`, `ConstraintStatus`,
  `ScenarioResult`, `StressTestResult`, `BenchmarkResult`).

Every result carries solver provenance (`solver`, `solver_type`,
`execution_backend`) so consumers can distinguish classical, quantum-inspired,
and simulator results without parsing numbers.

## Job manager

`quantive/jobs/manager.py` runs `run_full_job` in a `ThreadPoolExecutor`. Jobs
are keyed by `job_id`; `GET /optimization/jobs/{job_id}` returns status plus,
on completion, the full pipeline output, which is then served from the problem
endpoints above.