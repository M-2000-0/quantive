# Quantive — 3-Month Implementation Action Plan

**Date:** September 1, 2026
**Duration:** September 1 – November 30, 2026
**Source:** Codebase assessment completed September 1, 2026

---

## Executive Summary

This plan addresses four focus areas identified in the Quantive codebase review: database optimization, UX/UI page revamps, data refresh infrastructure, and simulation engine improvements. Each task is derived from a specific finding in the code review, with a measurable outcome and a deadline. The plan is divided into three monthly phases: **Foundation** (Month 1), **Implementation** (Month 2), and **Polish & Hardening** (Month 3).

### Success KPIs (Overall)

| KPI | Baseline | Month 1 Target | Month 2 Target | Month 3 Target |
|-----|----------|----------------|----------------|----------------|
| API response time (p95) | Unknown/unmeasured | < 800ms | < 500ms | < 300ms |
| DB query time (avg) | Unknown/unmeasured | < 200ms | < 100ms | < 50ms |
| Pages with live data | 0 of 100+ | 2 of 5 target pages | 4 of 5 target pages | 5 of 5 target pages |
| Data freshness | Static/stale | < 24hr refresh | < 1hr refresh | < 15min refresh |
| Simulation accuracy (vs. benchmark) | Unmeasured | Baseline captured | 10% improvement | 20% improvement |
| Frontend bundle size | Unknown | Measured | -10% | -20% |
| Test coverage (API layer) | 0% | 20% | 50% | 75% |

---

# PHASE 1: FOUNDATION (Weeks 1–4)

---

## Category A: Database Management & Data Pulling

### A1: Audit & Baseline (Week 1)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| A1.1 | Inventory all database tables and their row counts using `SELECT COUNT(*)` across every model in `backend/app/models/` | Sep 2 | Document listing every table, row count, and index status | Document produced |
| A1.2 | Profile the slowest 10 API endpoints by adding timing middleware that logs `duration_ms` to a dedicated `query_performance` log | Sep 3 | Sorted list of slowest endpoints with p50/p95/p99 latencies | Baseline latency report |
| A1.3 | Identify all N+1 query patterns by enabling SQLAlchemy `echo=True` in development and running the full test suite | Sep 4 | List of N+1 queries with file:line references | Catalog of issues |
| A1.4 | Check existing database indexes by running `PRAGMA index_list` (SQLite) or `\di` (PostgreSQL) on every table | Sep 4 | Index coverage map showing tables with/without indexes | Index map document |
| A1.5 | Measure current `ProblemSpec.build_spec` compilation time for 1K, 5K, and 10K scenarios using `time.perf_counter` | Sep 5 | Baseline compilation times for each scenario count | Timing report |

### A2: Schema Optimization (Week 2)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| A2.1 | Add composite index on `DebtInstrument(portfolio_id, maturity_date)` to speed up portfolio queries and maturity ladder calculations | Sep 9 | Index created; portfolio detail query runs in < 50ms | Query time < 50ms |
| A2.2 | Add index on `OptimizationJob(status, org_id, created_at)` for the jobs listing endpoint | Sep 9 | Jobs list endpoint serves paginated results in < 100ms | Query time < 100ms |
| A2.3 | Add index on `AuditEvent(actor_id, action, created_at)` for audit trail filtering | Sep 10 | Audit log queries return in < 100ms regardless of table size | Query time < 100ms |
| A2.4 | Create a covering index on `User(email)` since login queries filter exclusively by email | Sep 10 | Login lookup is a pure index scan | Explain plan shows index-only scan |
| A2.5 | Add database-level `CHECK` constraints for `coupon_rate >= 0`, `principal_outstanding > 0` on `DebtInstrument` | Sep 11 | Invalid data rejected at DB layer, not just application layer | Constraint violation test passes |
| A2.6 | Evaluate converting `metadata_json` columns from JSON string to native JSON/JSONB type (PostgreSQL only) and create GIN index | Sep 12 | Decision document: implement or defer with rationale | Decision recorded |
| A2.7 | Add `created_at` and `updated_at` with `DEFAULT CURRENT_TIMESTAMP` to all tables missing timestamp columns | Sep 12 | All tables have consistent timestamp tracking | Migration created and tested |

### A3: Connection & Pool Management (Week 2-3)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| A3.1 | Configure SQLAlchemy connection pool with `pool_size=20`, `max_overflow=10`, `pool_timeout=30` for PostgreSQL | Sep 16 | Connection pool configured; no "connection refused" errors under load | Zero connection errors in load test |
| A3.2 | Add connection pool monitoring by exposing `/api/v1/metrics/pool` endpoint returning active/idle/waiting connection counts | Sep 17 | Metrics endpoint operational | Endpoint returns valid JSON |
| A3.3 | Implement `pool_pre_ping=True` (already present) and verify it handles PostgreSQL failover by testing with Docker container restart | Sep 18 | Application recovers from database restart within 5 seconds | Recovery time < 5s |
| A3.4 | Add `PRAGMA journal_mode=WAL` (SQLite dev) and verify concurrent read/write performance | Sep 18 | WAL mode confirmed active; concurrent reads don't block | PRAGMA returns "wal" |
| A3.5 | Create a `db/` directory with `init.sql` for PostgreSQL containing all extensions, RLS policies, and the `set_app_context` function referenced in `database.py` | Sep 19 | Docker Compose creates a fully configured database on first boot | `docker-compose up` produces working DB |

### A4: Query Optimization (Week 3-4)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| A4.1 | Replace the in-memory `RUNTIME_JOBS` dict in `jobs.py` with database-backed persistence using the existing `JobModel` | Sep 23 | Jobs survive server restart; no data loss on `SIGTERM` | Restart test: job state preserved |
| A4.2 | Implement database-level pagination for `/api/portfolios`, `/api/optimizations`, `/api/audit` endpoints using `LIMIT`/`OFFSET` with `X-Total-Count` header | Sep 24 | All list endpoints accept `?page=1&per_page=25` and return correct totals | Response size < 50KB for 25 items |
| A4.3 | Add `selectinload()` or `joinedload()` for all relationships in portfolio detail queries to eliminate N+1 patterns | Sep 25 | Portfolio detail API returns in < 100ms with instruments loaded | Zero N+1 queries in logs |
| A4.4 | Cache scenario generation results by storing materialized scenarios in a `ScenarioCache` table keyed by `(problem_config_hash, seed)` | Sep 26 | Re-running the same problem config skips scenario generation | Second run is 5x faster than first |
| A4.5 | Implement read replicas configuration for PostgreSQL (even if using single instance, prepare the `database.py` routing for read vs write) | Sep 27 | `get_read_db()` and `get_write_db()` dependencies available | Code compiles; tests pass |
| A4.6 | Add query result caching with `@lru_cache` for the health check endpoint and static configuration lookups | Sep 27 | Health check responds in < 5ms on warm requests | Response time < 5ms |
| A4.7 | Create a database migration (Alembic) for all schema changes made in A2 and A3 | Sep 30 | Single `alembic upgrade head` applies all changes | Migration applies cleanly on fresh DB |

---

## Category B: UX/UI Improvements (5 Key Pages)

### Target Pages (selected from codebase review):

1. **Dashboard** (`/dashboard`) — Currently hardcoded in Jinja2; React `App.tsx` has static mock data
2. **Portfolio Detail** (`/portfolios/{id}`) — Core workflow page, needs live instrument data
3. **Optimization Wizard** (`/optimizations/new`) — Multi-step form, currently non-functional
4. **Risk Dashboard** (`/risk-dashboard`) — Needs real VaR/risk data integration
5. **Solver Tournament** (`/solver-tournament`) — Unique differentiator, currently placeholder

### B1: Design Audit & Component Inventory (Week 1)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| B1.1 | Screenshot all 5 target pages in their current state and document what data is hardcoded vs. dynamic | Sep 2 | Baseline screenshot deck with annotations | Document produced |
| B1.2 | Inventory existing React components in `frontend/src/components/` that relate to these 5 pages (e.g., `RiskDashboard.tsx`, `AllocationVisualizer.tsx`) | Sep 3 | Component mapping: which existing components serve which pages | Mapping spreadsheet |
| B1.3 | Identify which backend API endpoints already exist for each page's data needs by scanning `backend/app/api/*.py` | Sep 3 | API coverage map: page → required data → existing endpoint → gap | Gap analysis document |
| B1.4 | Review existing TypeScript types in `frontend/src/types/index.ts` and identify missing types for API response shapes | Sep 4 | List of missing or incomplete type definitions | Type gap list |
| B1.5 | Establish a design system baseline by cataloging existing CSS classes, Tailwind usage, and color tokens in `frontend/src/styles/` | Sep 5 | Design token documentation | Style guide draft |

### B2: API Layer for Frontend (Week 2)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| B2.1 | Create `GET /api/v1/dashboard/summary` endpoint returning total debt, instrument count, currency count, avg maturity, and risk scores — pulling from the database, not hardcoded | Sep 9 | Endpoint returns live data matching portfolio state | Response matches DB query results |
| B2.2 | Create `GET /api/v1/portfolios/{id}/detail` endpoint returning portfolio with all instruments, summary stats, and maturity distribution | Sep 10 | Endpoint returns nested portfolio data in < 200ms | Response time < 200ms |
| B2.3 | Create `GET /api/v1/optimizations/{id}/progress` endpoint returning real-time job progress (phase, percentage, ETA) | Sep 11 | Endpoint streams or polls current optimization status | Progress increments smoothly |
| B2.4 | Create `GET /api/v1/risk/summary` endpoint returning risk scores, VaR results, and early warning signals for a given portfolio | Sep 12 | Endpoint returns structured risk data | Response matches risk engine output |
| B2.5 | Create `GET /api/v1/solvers/leaderboard` endpoint returning benchmark results ranked by weighted metrics | Sep 13 | Endpoint returns solver comparison data | Response matches benchmark engine output |
| B2.6 | Add OpenAPI documentation (`summary`, `description`, `response_model`) to all new endpoints | Sep 13 | Swagger UI at `/docs` shows clear documentation for each endpoint | Each endpoint has description and example |

### B3: Dashboard Page Revamp (Week 2-3)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| B3.1 | Replace hardcoded stats in `App.tsx` (currently `$12.4M`, `8.7%`, etc.) with data fetched from `GET /api/v1/dashboard/summary` using `@tanstack/react-query` | Sep 17 | Dashboard shows live portfolio values | Values change when DB data changes |
| B3.2 | Replace hardcoded bar chart in `App.tsx` with a `recharts` `BarChart` component fed by actual maturity distribution data | Sep 18 | Bar chart renders real data from the API | Chart updates on page load |
| B3.3 | Replace hardcoded task list with data from a new `GET /api/v1/dashboard/tasks` endpoint (pending approvals, upcoming maturities, active alerts) | Sep 19 | Task list shows real pending items | Tasks match DB records |
| B3.4 | Add a `PageTransition` wrapper (component already exists at `components/PageTransition.tsx`) for smooth navigation between dashboard sections | Sep 19 | Page transitions animate smoothly | No layout shift on navigation |
| B3.5 | Implement responsive layout for dashboard: sidebar collapses on screens < 1024px, cards stack vertically on < 768px | Sep 20 | Dashboard renders correctly on tablet and mobile viewports | No horizontal scroll at 375px width |
| B3.6 | Add loading skeletons (use existing `Skeleton` pattern or create `components/ui/Skeleton.tsx`) for each dashboard card during data fetch | Sep 20 | No blank/flash-of-empty-content during loading | Visual regression test passes |

### B4: Portfolio Detail Page Revamp (Week 3)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| B4.1 | Wire portfolio detail page to `GET /api/v1/portfolios/{id}/detail` with instrument table showing name, currency, principal, coupon, maturity, spread | Sep 23 | Instrument table renders live data | Table rows match DB records |
| B4.2 | Add maturity ladder visualization using existing `AllocationVisualizer.tsx` component, showing principal amounts grouped by maturity year | Sep 24 | Visual maturity ladder renders from API data | Chart shows correct year groupings |
| B4.3 | Add portfolio summary stats panel: total debt, weighted average coupon, weighted average maturity, currency breakdown pie chart | Sep 25 | Summary panel shows computed metrics | Metrics match manual calculation |
| B4.4 | Add instrument filtering and sorting: filter by currency, type; sort by maturity, principal, coupon rate | Sep 26 | Table supports column sorting and currency filter dropdown | Filter reduces visible rows correctly |
| B4.5 | Add "Run Optimization" button that navigates to the optimization wizard with the current portfolio pre-selected | Sep 26 | Button triggers navigation with portfolio ID in URL params | Portfolio ID carried to wizard |

### B5: Optimization Wizard Revamp (Week 3-4)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| B5.1 | Implement multi-step form with 4 steps: (1) Objectives, (2) Constraints, (3) Scenario Config, (4) Review & Submit | Sep 30 | Four-step wizard with progress indicator | All 4 steps navigate correctly |
| B5.2 | Step 1: Weight sliders for financing cost, refinancing risk, interest rate risk, currency risk (must sum to 1.0) | Oct 1 | Four sliders with real-time validation | Weights always sum to 1.0 |
| B5.3 | Step 2: Constraint configuration form with inputs for max financing cost, max refi concentration, max currency exposure, max floating rate, min liquidity | Oct 2 | Constraint form saves values to wizard state | Constraints passed to API correctly |
| B5.4 | Step 3: Scenario configuration — named scenario checkboxes (base, IR shock, FX shock, credit spread, liquidity shock) + Monte Carlo count slider (1K–10K) + seed input | Oct 3 | Scenario config saves values to wizard state | Config matches API expectations |
| B5.5 | Step 4: Review screen showing all configured parameters in a summary card before submission | Oct 3 | Summary card displays all choices | User can review before submitting |
| B5.6 | Submit wizard creates `POST /api/v1/optimizations` and navigates to progress view with real-time status updates | Oct 4 | Optimization starts and progress updates display | Progress reaches 100% on completion |

---

## Category C: Data Refresh Strategies

### C1: Assessment & Architecture (Week 1-2)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| C1.1 | Audit all data sources currently used: synthetic data (`quantive/data/synthetic.py`), fixtures (`quantive/data/fixtures.py`), market data API (`backend/app/market_data/`), FRED API (referenced in `docker-compose.yml`) | Sep 3 | Data source inventory: source → refresh frequency → current staleness | Inventory document |
| C1.2 | Check if Yahoo Finance and FRED API integrations are functional by calling their endpoints with test keys | Sep 4 | Pass/fail status for each external data source | Functional status report |
| C1.3 | Design a `DataRefreshSchedule` model in `backend/app/models/` tracking: source, frequency, last_refresh, status, next_scheduled | Sep 5 | SQLAlchemy model created and migration generated | Model creates successfully |
| C1.4 | Create a `POST /api/v1/data/refresh` endpoint that triggers refresh for a specified source | Sep 8 | Endpoint accepts source name and returns a job ID | Endpoint accepts and processes request |
| C1.5 | Create a `GET /api/v1/data/status` endpoint returning freshness status of all data sources | Sep 8 | Endpoint returns JSON with last-refresh timestamps for each source | Response includes all sources |

### C2: Automated Refresh Infrastructure (Week 2-3)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| C2.1 | Implement a background scheduler using `APScheduler` or FastAPI `BackgroundTasks` with cron-like scheduling for data refresh jobs | Sep 12 | Scheduler starts on application boot; refresh jobs execute on schedule | Jobs run at configured intervals |
| C2.2 | Implement yield curve refresh from FRED API: fetch daily Treasury yields, store in `YieldCurve` table, handle API failures with retry (3 attempts, exponential backoff) | Sep 15 | Yield curve data is refreshed daily; failures retry 3 times | Data age < 24 hours during normal operation |
| C2.3 | Implement FX rate refresh from Yahoo Finance or FRED: fetch major currency pairs used in portfolio instruments, update `FxRate` table | Sep 16 | FX rates refreshed at configured interval | Rates within 1 hour of market close |
| C2.4 | Implement interest rate refresh: fetch central bank policy rates and interbank rates for active currencies | Sep 17 | Interest rate data current | Rates match official sources within 24 hours |
| C2.5 | Add data staleness detection: flag any data older than configured threshold in the `GET /api/v1/data/status` response with `is_stale: true` | Sep 18 | Stale data is visually flagged in the UI | Stale flag triggers within threshold of last update |
| C2.6 | Implement synthetic data regeneration: update `quantive/data/synthetic.py` to incorporate real market data when available, falling back to generated data | Sep 19 | Synthetic portfolio incorporates real yield curves when available | Generated yields track real yields when source is available |

### C3: Data Quality & Validation (Week 3-4)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| C3.1 | Create a `DataValidation` module in `backend/app/data_quality.py` (already exists) that checks: no null values in critical fields, coupon rates in 0–20% range, maturity dates in the future for new instruments, principal > 0 | Sep 23 | Validation runs on every data refresh; failures logged | Zero invalid records after refresh |
| C3.2 | Implement anomaly detection for time-series data: flag yield curve inversions, FX rate moves > 5% in a day, and interest rate changes > 100bps | Sep 24 | Anomalies trigger notifications via existing notification system | Anomaly detected and notification sent |
| C3.3 | Create a `GET /api/v1/data/quality` endpoint returning validation results for each data source: total records, valid count, invalid count, anomalies detected | Sep 25 | Endpoint returns per-source quality metrics | Response shows quality score per source |
| C3.4 | Add data lineage tracking: log which source provided each data point and when it was last updated in the `metadata` JSON column | Sep 26 | Every data record has provenance metadata | Metadata includes source and timestamp |
| C3.5 | Implement data versioning: store the previous version of each refreshable dataset so users can compare "current vs. last week" | Sep 27 | Two versions of each dataset available for comparison | Diff endpoint returns meaningful comparison |
| C3.6 | Create a `GET /api/v1/data/diff?source=yield_curve&from=2026-09-01&to=2026-09-15` endpoint returning changes between two dates | Sep 30 | Diff endpoint returns added/removed/changed records | Response correctly identifies changes |

---

## Category D: Simulation Engine Improvements

### D1: Baseline & Profiling (Week 1)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| D1.1 | Run `scripts/demo.py` and record total runtime, per-phase timing (scenario generation, solving, benchmarking, stress testing, strategy generation) | Sep 2 | Baseline timing breakdown for the full pipeline | Timing report |
| D1.2 | Profile memory usage during a 10K-scenario run using `tracemalloc` or `memory_profiler` | Sep 3 | Peak memory usage recorded for 1K, 5K, 10K scenarios | Memory profile report |
| D1.3 | Measure solver accuracy: run MILP, simulated annealing, and QUBO solvers on the same problem 10 times each; compute variance in objective value | Sep 4 | Variance report: MILP (expected ~0), SA (measured), QUBO (measured) | Variance values recorded |
| D1.4 | Review the `ProblemSpec.build_spec` method for unnecessary computation (e.g., recomputing cost matrix when scenarios haven't changed) | Sep 5 | List of optimization opportunities with estimated savings | Optimization opportunity list |
| D1.5 | Verify that all three solvers correctly handle edge cases: 0 instruments, 1 instrument, all instruments at capacity, infeasible constraints | Sep 5 | Edge case test results for each solver | Test results documented |

### D2: Scenario Engine Enhancement (Week 2-3)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| D2.1 | Add correlation matrix support to `ScenarioEngine`: currently shocks are independent Gaussians; implement Cholesky decomposition for correlated shocks across IR, FX, spreads | Sep 9 | Scenarios with correlated shocks produce realistic joint distributions | Correlation between IR and FX shocks > 0.3 in designed scenarios |
| D2.2 | Add fat-tailed distribution option (Student-t or Cornish-Fisher expansion) as an alternative to Gaussian for scenario generation | Sep 10 | Configurable distribution type in `ScenarioConfiguration` | Tail scenarios are 2-3x more frequent than Gaussian baseline |
| D2.3 | Implement regime-switching scenarios: Bull/Bear/Neutral regimes with different parameter sets, transitions governed by a Markov chain | Sep 12 | Regime sequence appears in scenario metadata | Scenario output includes regime labels |
| D2.4 | Add scenario clustering: after Monte Carlo generation, cluster scenarios into groups using k-means on the shock vectors; report cluster sizes and centroids | Sep 15 | Cluster analysis included in scenario output | Clusters are non-trivial (no single cluster > 80% of scenarios) |
| D2.5 | Implement scenario importance weighting: allow users to upweight specific scenario types (e.g., "increase probability of FX shocks") without changing the total count | Sep 16 | User-specified weights applied to scenario probabilities | Weighted probabilities sum to 1.0 |
| D2.6 | Add scenario comparison tool: given two scenario sets, compute KL-divergence or Wasserstein distance between their distributions | Sep 17 | Comparison metric returned for any two scenario sets | Metric is non-negative and symmetric |

### D3: Solver Improvements (Week 3-4)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| D3.1 | Implement warm-start for MILP solver: when re-solving with similar parameters, use previous solution as initial basis (CBC supports this via `initialBasis`) | Sep 23 | Second solve is 20-40% faster than cold start | Measured speedup > 20% |
| D3.2 | Add `highs_solver.py` integration (file already exists in `quantive/solvers/`): wire HiGHS as a fourth solver backend and register it in `registry.py` | Sep 24 | HiGHS solver appears in solver registry and produces valid results | HiGHS result passes feasibility check |
| D3.3 | Implement parallel solver execution: run all registered solvers simultaneously using `concurrent.futures.ProcessPoolExecutor` instead of sequentially | Sep 25 | Total benchmark time is max(individual solver times), not sum | Benchmark time reduced by 50%+ |
| D3.4 | Add solver timeout handling: if a solver exceeds `config.time_limit_seconds`, gracefully return best-so-far solution instead of blocking | Sep 26 | Timeout produces partial result with `optimality_note="timeout"` | Timeout doesn't crash the pipeline |
| D3.5 | Implement solver memory limits: cap memory usage per solver at 2GB and return error if exceeded (use `resource.setrlimit` on Linux) | Sep 27 | Memory-constrained solvers return error instead of crashing OOM | No OOM kills in 10K-scenario tests |
| D3.6 | Add sensitivity analysis: after solving, vary each constraint bound by ±10% and report the change in objective value (shadow prices approximation) | Sep 30 | Sensitivity report shows which constraints are binding | Binding constraints correctly identified |

### D4: Stress Testing Enhancement (Week 4)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| D4.1 | Add time-series stress testing: instead of single-point shocks, simulate gradual shock propagation over N quarters (e.g., rates rise 25bps/quarter for 8 quarters) | Oct 1 | Stress test produces multi-period results | Results include quarterly breakdown |
| D4.2 | Implement reverse stress testing: find the minimum shock magnitude that causes a constraint violation for each strategy | Oct 2 | Reverse stress test identifies breaking points per constraint | Breaking point values are reasonable (not 0 or ∞) |
| D4.3 | Add Monte Carlo stress testing: run each strategy through 1000 additional random scenarios (separate from the optimization scenarios) to validate out-of-sample robustness | Oct 3 | Out-of-sample stress results included in report | Out-of-sample satisfaction rate within 5% of in-sample |
| D4.4 | Implement stress test comparison: given two strategies, compute the probability that strategy A outperforms strategy B across all scenarios | Oct 3 | Pairwise comparison probability returned | Probability is between 0 and 1 |
| D4.5 | Add tail risk metrics to stress test output: CVaR (Conditional Value at Risk) at 95% and 99% confidence levels for each strategy | Oct 4 | CVaR metrics included in `StressTestResult` | CVaR ≥ VaR at the same confidence level |

---

# PHASE 2: IMPLEMENTATION (Weeks 5–8)

---

## Category A: Database (Continued)

### A5: Performance Optimization (Week 5-6)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| A5.1 | Implement query caching with Redis for frequently accessed, rarely changing data (portfolio summaries, solver registry, user permissions) | Oct 10 | Redis cache layer operational; cache hit rate > 80% after warm-up | Cache hit rate > 80% |
| A5.2 | Batch insert optimization: replace sequential `db.add()` + `db.commit()` in job result storage with bulk `bulk_insert_mappings()` | Oct 11 | Scenario result storage is 5x faster | Bulk insert time < sequential / 5 |
| A5.3 | Add database connection health monitoring dashboard at `/api/v1/admin/db-health` showing pool stats, slow queries, table sizes | Oct 12 | Admin endpoint returns comprehensive DB health data | Endpoint returns valid JSON with all metrics |
| A5.4 | Implement soft deletes for portfolios and optimization jobs (add `deleted_at` column) instead of hard deletes | Oct 13 | Deleted records have `deleted_at` set; queries filter them out | `SELECT COUNT(*)` excludes soft-deleted records |
| A5.5 | Create materialized views (PostgreSQL) or summary tables for dashboard aggregates: total debt per org, active jobs count, recent activity feed | Oct 14 | Dashboard query time < 20ms using summary tables | Dashboard API responds in < 20ms |
| A5.6 | Add database-level audit trail: create a trigger that logs all INSERT/UPDATE/DELETE on `DebtInstrument` and `OptimizationJob` tables to a shadow audit table | Oct 15 | Every data mutation is recorded with timestamp, user, old/new values | Audit records exist for test mutations |
| A5.7 | Implement database migration rollback testing: create a CI step that runs `alembic upgrade head` then `alembic downgrade -1` and verifies data integrity | Oct 16 | Rollback test passes in CI | CI pipeline includes migration test |

### A6: Data Access Patterns (Week 7-8)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| A6.1 | Implement repository pattern for data access: create `backend/app/repositories/portfolio_repository.py` encapsulating all portfolio queries | Oct 21 | Portfolio repository with `find_by_id`, `find_by_org`, `create`, `update`, `delete` methods | All portfolio endpoints use repository |
| A6.2 | Create `OptimizationRepository` encapsulating job queries, result storage, and progress tracking | Oct 22 | Optimization repository operational | All optimization endpoints use repository |
| A6.3 | Create `AuditRepository` with efficient time-range queries and aggregation support | Oct 23 | Audit repository supports `events_in_range`, `count_by_action`, `top_actors` | Aggregation queries execute in < 50ms |
| A6.4 | Implement data access logging: every repository method logs query time and row count at DEBUG level | Oct 24 | Query performance visible in development logs | Debug logs show query metrics |
| A6.5 | Add data access retry logic for transient database errors (connection reset, lock timeout) with 3 retries and exponential backoff | Oct 25 | Transient DB errors recovered automatically | Test with simulated connection drop |
| A6.6 | Implement optimistic locking on `DebtInstrument` and `OptimizationJob`: add `version` column, reject updates if version doesn't match | Oct 27 | Concurrent updates to same record produce conflict error, not silent overwrite | Two simultaneous updates: one succeeds, one gets 409 |

---

## Category B: UX/UI (Continued)

### B6: Risk Dashboard Revamp (Week 5-6)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| B6.1 | Wire risk dashboard to `GET /api/v1/risk/summary` endpoint, displaying overall risk score with color-coded severity indicator | Oct 8 | Risk score renders from live data | Score updates when portfolio changes |
| B6.2 | Integrate `VaRResult` data into dashboard: display VaR at 95% and 99% confidence with bar chart comparison | Oct 9 | VaR chart renders from API data | Chart values match API response |
| B6.3 | Build early warning signals panel using existing `EarlyWarningSystem.tsx` component: show threshold breaches with severity colors | Oct 10 | Warning signals appear when thresholds are exceeded | Signal triggers when data crosses threshold |
| B6.4 | Add risk decomposition view: pie chart showing contribution of each risk factor (IR, FX, refinancing, liquidity) to total risk | Oct 11 | Risk decomposition chart renders | Pie chart percentages sum to 100% |
| B6.5 | Implement risk score trend: line chart showing historical risk score over time (stored in `RiskHistory` table) | Oct 12 | Historical trend line renders from stored data | Line chart has ≥ 10 data points after one week of operation |
| B6.6 | Add "What-If" risk simulator: user adjusts a parameter (e.g., rates +100bps), dashboard shows projected risk score change | Oct 14 | Parameter adjustment triggers recalculation and UI update | Projected score matches calculation |

### B7: Solver Tournament Page Revamp (Week 6-7)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| B7.1 | Wire solver tournament to `GET /api/v1/solvers/leaderboard` endpoint, displaying ranked solver comparison table | Oct 16 | Leaderboard table renders from live benchmark data | Table matches benchmark engine output |
| B7.2 | Add solver detail cards: expandable row for each solver showing execution time, iterations, constraint violations, optimality note | Oct 17 | Detail cards expand on click with full metrics | All metrics display correctly |
| B7.3 | Implement radar chart comparing solvers across 5 dimensions: cost, risk, runtime, feasibility, robustness using `recharts` `RadarChart` | Oct 18 | Radar chart visualizes multi-dimensional comparison | Chart renders 5 axes correctly |
| B7.4 | Add "Run Tournament" button that triggers benchmark run and shows real-time progress | Oct 19 | Button starts benchmark; progress updates display | Benchmark completes and results appear |
| B7.5 | Implement solver selection: user picks a solver from tournament results and creates optimization with that solver pre-selected | Oct 20 | Solver selection carries to optimization wizard | Selected solver is pre-filled in wizard |
| B7.6 | Add historical tournament results: store benchmark results and show trend of solver performance over time | Oct 21 | Historical performance chart displays | Chart shows data from multiple benchmark runs |

### B8: Cross-Cutting UI Improvements (Week 7-8)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| B8.1 | Implement error boundaries on all 5 target pages using existing `ErrorBoundary.tsx` component with retry and fallback UI | Oct 23 | Errors show friendly fallback, not blank screen | Test: kill API → error boundary activates |
| B8.2 | Add global loading indicator (top bar) for API requests using `react-query`'s `useIsFetching` | Oct 24 | Thin progress bar appears during any API call | Bar appears and disappears correctly |
| B8.3 | Implement keyboard shortcuts using existing `KeyboardShortcutOverlay.tsx`: Ctrl+K for command palette, Ctrl+/ for help | Oct 25 | Keyboard shortcuts functional | Shortcuts trigger expected actions |
| B8.4 | Add toast notifications for success/error states using existing `Toast.tsx` component on all form submissions and data mutations | Oct 27 | Toast appears after create/update/delete operations | Toast shows for 3 seconds then dismisses |
| B8.5 | Implement dark mode toggle using existing `ThemeToggle.tsx` and `theme.ts` store across all 5 target pages | Oct 28 | Theme toggle switches all pages between light and dark | No white-on-white or dark-on-dark elements |
| B8.6 | Add skeleton loading states for all data-dependent sections on all 5 target pages | Oct 28 | Skeleton placeholders appear during loading | No layout shift when skeleton replaced by data |
| B8.7 | Implement responsive design audit: test all 5 pages at 375px, 768px, 1024px, 1440px widths and fix layout issues | Oct 30 | All pages render correctly at all breakpoints | No horizontal scroll, no overflow at any breakpoint |

---

## Category C: Data Refresh (Continued)

### C4: Scheduling & Orchestration (Week 5-6)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| C4.1 | Implement a `SchedulerService` class that manages all refresh jobs with configurable cron expressions per source | Oct 8 | Scheduler class with `schedule`, `unschedule`, `get_status` methods | Scheduler starts and runs on app boot |
| C4.2 | Configure refresh schedules: yield curve (daily 6am UTC), FX rates (hourly during market hours), interest rates (daily), synthetic data (weekly) | Oct 9 | Four refresh schedules active | Each source refreshes at configured interval |
| C4.3 | Implement refresh job queue using database-backed queue (table with status columns) instead of in-memory scheduling | Oct 10 | Refresh jobs persist across server restarts | Restart doesn't interrupt scheduled refreshes |
| C4.4 | Add refresh dependency graph: yield curve refresh triggers dependent calculations (e.g., synthetic data regeneration) | Oct 11 | Dependent refreshes cascade correctly | Upstream change triggers downstream refresh |
| C4.5 | Implement refresh job retry with exponential backoff: 1st retry after 1min, 2nd after 5min, 3rd after 30min; alert after 3 failures | Oct 12 | Failed refreshes retry automatically; alerts after 3 failures | Alert notification sent after 3 failures |
| C4.6 | Add a `GET /api/v1/data/refresh/status` endpoint showing next scheduled refresh time for each source and last 10 refresh job results | Oct 14 | Status endpoint shows schedule and history | Response includes next_run and job_history |

### C5: Real-Time Data Feeds (Week 7-8)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| C5.1 | Implement WebSocket connection for real-time market data updates on the risk dashboard (WebSocket infrastructure exists at `backend/app/websocket.py`) | Oct 21 | WebSocket pushes market data updates to connected clients | Dashboard updates without page refresh |
| C5.2 | Add Server-Sent Events (SSE) as a fallback for environments where WebSocket is blocked (government firewalls) | Oct 22 | SSE endpoint delivers same data as WebSocket | SSE clients receive updates correctly |
| C5.3 | Implement data source health monitoring: periodic heartbeat check for FRED API, Yahoo Finance, and any custom data feeds | Oct 23 | Health status visible in admin dashboard | Unhealthy source flagged within 5 minutes |
| C5.4 | Add rate limiting for external API calls: respect FRED API rate limits (120 requests/minute) and Yahoo Finance limits | Oct 24 | No rate limit violations | Zero 429 responses from external APIs |
| C5.5 | Implement data caching layer for external API responses: cache yield curves for 1 hour, FX rates for 15 minutes, rates for 4 hours | Oct 25 | Cached responses served without external API call | Cache hit rate > 70% for repeated queries |
| C5.6 | Create a `GET /api/v1/market/snapshot` endpoint returning the latest available market data (yield curve, FX rates, interest rates) with freshness indicators | Oct 27 | Snapshot endpoint returns comprehensive market state | Response includes freshness metadata per data point |

---

## Category D: Simulation Engine (Continued)

### D5: Simulation Accuracy & Performance (Week 5-6)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| D5.1 | Implement scenario reduction: after generating 10K Monte Carlo scenarios, reduce to 500 representative scenarios using-scenario-matching (K均值) to speed up solving without significant accuracy loss | Oct 8 | Reduced scenario set produces results within 2% of full set | Objective value difference < 2% |
| D5.2 | Add parallel scenario cost computation: vectorize `scenario_costs()` in `quantive/objectives/costs.py` using NumPy broadcasting instead of Python loops | Oct 9 | Cost computation is 10x faster for large scenario sets | 10K scenarios computed in < 1s |
| D5.3 | Implement incremental problem compilation: when only scenarios change (not portfolio or constraints), reuse cached `ProblemSpec` components | Oct 10 | Re-compilation with new scenarios is 3x faster | Measured speedup > 3x |
| D5.4 | Add numerical stability checks: verify cost matrix has no NaN/Inf values, probabilities sum to 1.0, capacity bounds are non-negative | Oct 11 | Invalid inputs produce clear error messages instead of silent failures | Test: NaN in input → descriptive error |
| D5.5 | Implement warm-start for simulated annealing: use the MILP solution as initial point for SA, which often converges faster from a good starting point | Oct 12 | SA with warm-start converges 20% faster | Iterations to convergence reduced by 20% |
| D5.6 | Add convergence diagnostics for SA and QUBO: report best-so-far objective at each temperature step, enabling users to assess solution quality | Oct 14 | Convergence plot data available in solver results | Convergence data included in result metadata |

### D6: Advanced Simulation Features (Week 7-8)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| D6.1 | Implement multi-objective optimization using Pareto front generation: find non-dominated solutions across cost vs. risk tradeoff | Oct 21 | Pareto front returned as set of solutions | Solutions are non-dominated (no solution beats another on both objectives) |
| D6.2 | Add portfolio rebalancing simulation: given current portfolio and target allocation, compute optimal transition path with transaction costs | Oct 22 | Transition plan with quarterly rebalancing steps returned | Total cost of transition is minimized |
| D6.3 | Implement what-if scenario injection: allow user to add a custom shock scenario (e.g., "rates +200bps, FX -15%") and see its impact on each strategy | Oct 23 | Custom scenario impact calculated for each strategy | Impact results include new financing cost and constraint violations |
| D6.4 | Add portfolio backtesting: given historical data, replay the optimization strategy through past periods and compare against actual outcomes | Oct 24 | Backtest report shows historical performance of strategy | Backtest produces year-by-year comparison |
| D6.5 | Implement strategy stress decomposition: break down the stress test results by risk factor to show which factor contributes most to each strategy's vulnerability | Oct 25 | Factor-level decomposition included in stress results | Decomposition correctly attributes risk to factors |
| D6.6 | Add simulation result export: export full simulation results (scenarios, costs, allocations, stress tests) as a structured JSON or CSV file | Oct 27 | Export endpoint produces downloadable file | File is parseable and contains all result data |

---

# PHASE 3: POLISH & HARDENING (Weeks 9–12)

---

## Category A: Database Hardening

### A7: Security & Compliance (Week 9-10)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| A7.1 | Implement row-level security (RLS) in PostgreSQL: create the `set_app_context` function referenced in `database.py` and enable RLS on all tenant-scoped tables | Nov 4 | User A cannot query User B's data even with direct SQL access | Penetration test: cross-org access blocked |
| A7.2 | Add SQL injection protection: verify all queries use parameterized statements (no string interpolation in SQL) by running semgrep with custom rules | Nov 5 | Zero instances of string-interpolated SQL | Semgrep scan passes |
| A7.3 | Encrypt sensitive columns at rest: `User.password_hash` (already bcrypt), `DebtInstrument` notes/comments, audit event metadata | Nov 6 | Sensitive data encrypted in database file/dump | DB dump shows encrypted values |
| A7.4 | Implement database connection encryption: enforce TLS for PostgreSQL connections in production | Nov 7 | All production DB connections use TLS | Connection string includes `sslmode=require` |
| A7.5 | Add database backup automation: daily pg_dump to encrypted storage with 30-day retention | Nov 8 | Automated backup runs daily | Backup file exists and is restorable |
| A7.6 | Implement database backup restore testing: weekly automated restore to a test database to verify backup integrity | Nov 8 | Restore test runs weekly | Restore test passes |

### A8: Monitoring & Observability (Week 10-11)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| A8.1 | Add Prometheus metrics endpoint at `/metrics` exposing: request count, latency histogram, DB pool stats, job queue depth | Nov 12 | Metrics endpoint operational | Prometheus can scrape the endpoint |
| A8.2 | Implement slow query logging: queries exceeding 500ms are logged with full SQL, parameters (redacted), and execution plan | Nov 13 | Slow queries appear in dedicated log | Slow query log captures > 500ms queries |
| A8.3 | Add database alerting: alert if connection pool utilization > 80%, query error rate > 1%, or replication lag > 5s | Nov 14 | Alerting rules configured and tested | Test alert fires when threshold exceeded |
| A8.4 | Create a `/api/v1/admin/database/stats` endpoint returning: table sizes, index usage statistics, cache hit ratios, dead tuple counts | Nov 15 | Admin can inspect DB health from API | Response includes all requested metrics |
| A8.5 | Implement query plan analysis: for identified slow queries, capture and store `EXPLAIN ANALYZE` output for optimization | Nov 15 | Query plans available for slow queries | Plans stored and accessible via API |
| A8.6 | Add OpenTelemetry tracing for database spans: each DB operation appears in the distributed trace with duration and query summary | Nov 18 | Traces show DB operations with timing | Jaeger/Zipkin UI shows DB spans |

---

## Category B: UX/UI Hardening

### B9: Testing & Quality (Week 9-10)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| B9.1 | Write integration tests for the dashboard page: mock API responses, verify rendering of stats, charts, tasks | Nov 4 | Dashboard tests pass in CI | Test coverage > 80% for Dashboard.tsx |
| B9.2 | Write integration tests for portfolio detail page: verify instrument table, maturity ladder, summary stats render correctly | Nov 5 | Portfolio detail tests pass | Test coverage > 80% for portfolio page |
| B9.3 | Write integration tests for optimization wizard: verify all 4 steps, form validation, submission flow | Nov 6 | Wizard tests pass | Test coverage > 80% for wizard |
| B9.4 | Write Playwright E2E tests for critical user flow: login → view portfolio → run optimization → view results | Nov 7 | E2E test passes in CI | E2E test completes in < 2 minutes |
| B9.5 | Implement visual regression testing with Playwright screenshot comparison for all 5 target pages | Nov 8 | Visual regression tests pass | Zero unexpected visual changes |
| B9.6 | Add accessibility (a11y) audit: run `axe-core` on all 5 target pages, fix all critical violations | Nov 10 | Zero critical a11y violations | axe-core scan returns zero critical issues |
| B9.7 | Implement performance budget: bundle size < 500KB gzipped, Largest Contentful Paint < 2.5s, First Input Delay < 100ms | Nov 10 | All performance metrics within budget | Lighthouse score > 90 |

### B10: Polish & Refinement (Week 11-12)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| B10.1 | Implement empty state designs for all 5 pages: friendly illustrations and CTAs when no data exists | Nov 18 | Empty states display correctly | Test: empty DB → appropriate empty states |
| B10.2 | Add input validation feedback on all forms: real-time field validation with error messages using react-query error states | Nov 19 | Form errors show inline below each field | Submit with invalid data → errors appear |
| B10.3 | Implement optimistic updates for mutations: UI updates immediately before server confirms, rolls back on error | Nov 20 | UI feels instant on create/update/delete | Perceived latency < 100ms |
| B10.4 | Add breadcrumb navigation across all pages showing current location in hierarchy | Nov 21 | Breadcrumbs appear on all pages | Breadcrumbs correctly reflect route |
| B10.5 | Implement page metadata: set `<title>` and meta description per page for browser tabs and sharing | Nov 21 | Browser tab shows page-specific title | Title matches page content |
| B10.6 | Add print-friendly styles for dashboard and reports: hide navigation, adjust layouts for A4 paper | Nov 22 | Ctrl+P produces clean printout | Print preview looks correct |
| B10.7 | Implement data export on all 5 pages: CSV and PDF export buttons with current view's data | Nov 25 | Export buttons functional on all pages | Downloaded files contain correct data |

---

## Category C: Data Refresh Hardening

### C6: Reliability & Monitoring (Week 9-10)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| C6.1 | Implement circuit breaker for external API calls (FRED, Yahoo Finance): after 3 consecutive failures, stop calling for 30 minutes | Nov 4 | Circuit breaker prevents hammering failing APIs | Test: 3 failures → circuit opens → no calls for 30min |
| C6.2 | Add data freshness SLA monitoring: alert if any data source exceeds its configured maximum age | Nov 5 | Alerts fire when data becomes stale | Alert within configured threshold of staleness |
| C6.3 | Implement graceful degradation: when external data is unavailable, serve cached data with a staleness indicator in the UI | Nov 6 | UI shows "data as of [timestamp]" when serving cached data | Staleness banner visible during outage |
| C6.4 | Add refresh job metrics: track average refresh duration, success rate, and data volume per source | Nov 7 | Metrics available at `/api/v1/metrics/data-refresh` | Response includes per-source metrics |
| C6.5 | Implement data source failover: if primary source fails, automatically fall back to secondary source (e.g., FRED → Yahoo Finance for FX rates) | Nov 8 | Failover to secondary source on primary failure | Secondary source data used during primary outage |
| C6.6 | Create a data refresh operations dashboard showing: current status of all sources, next refresh time, last 24h success/failure count | Nov 10 | Admin dashboard shows refresh operations overview | Dashboard displays all required information |

### C7: Advanced Data Features (Week 11-12)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| C7.1 | Implement data correlation engine: compute real-time correlation matrix between all tracked market variables (IR, FX, spreads) | Nov 18 | Correlation matrix available via API | Matrix dimensions match number of variables |
| C7.2 | Add data forecast capability: project yield curves and FX rates forward 6 months using historical trends and current momentum | Nov 19 | 6-month forecast returned with confidence intervals | Forecast includes upper/lower bounds |
| C7.3 | Implement custom data ingestion: allow users to upload CSV files with market data that integrates into the existing data pipeline | Nov 20 | CSV upload adds data points to the system | Uploaded data appears in subsequent queries |
| C7.4 | Add data comparison across countries: fetch peer country debt metrics for benchmarking (leverage existing `CrossCountryBenchmarking.tsx`) | Nov 21 | Cross-country comparison data available for 5+ countries | Peer data displayed in benchmarking view |
| C7.5 | Implement data change notifications: send alerts when market data changes significantly (configurable thresholds) | Nov 22 | Users receive notifications on significant market moves | Notification sent when threshold exceeded |
| C7.6 | Create data export API: `POST /api/v1/data/export` returning all market data in specified date range as CSV or JSON | Nov 25 | Export endpoint produces downloadable data | Exported file is parseable and complete |

---

## Category D: Simulation Engine Hardening

### D7: Validation & Testing (Week 9-10)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| D7.1 | Create golden master tests: run full pipeline with fixed seed, compare output against stored expected results (detects regressions) | Nov 4 | Golden master test passes in CI | Output matches expected within tolerance |
| D7.2 | Add property-based testing for solvers using Hypothesis: verify allocations sum to financing requirement, all constraints satisfied, objective is non-negative | Nov 5 | Property tests pass for all 4 solvers | No counterexamples found |
| D7.3 | Implement solver correctness verification: for small problems (N < 10), verify SA and QUBO results against MILP optimal solution | Nov 6 | Heuristic solvers produce solutions within 5% of MILP optimal | Gap < 5% for all small test problems |
| D7.4 | Add benchmark reproducibility test: run benchmark twice with same seed, verify identical results | Nov 7 | Reproducibility test passes | Output byte-identical for same seed |
| D7.5 | Create stress test for edge cases: empty portfolio, single instrument, extreme constraints (min liquidity = 99%), very large portfolios (1000 instruments) | Nov 8 | All edge cases produce valid results or clear error messages | No crashes or silent failures |
| D7.6 | Implement fuzz testing for the scenario engine: random inputs to `ScenarioEngine.materialize()` should never produce NaN, Inf, or negative probabilities | Nov 10 | Fuzz test finds zero invalid outputs | 10K random inputs, zero failures |

### D8: Documentation & Developer Experience (Week 11-12)

| # | Task | Deadline | Outcome | KPI |
|---|------|----------|---------|-----|
| D8.1 | Write comprehensive docstrings for all public functions in `quantive/solvers/`, `quantive/objectives/`, `quantive/stress/` | Nov 18 | Every public function has a docstring with params, returns, and example | `pydoc` generates useful documentation |
| D8.2 | Create Jupyter notebooks demonstrating each solver's usage, scenario generation, and stress testing workflows | Nov 19 | 4 notebooks: MILP, SA, QUBO, full pipeline | Notebooks run end-to-end without errors |
| D8.3 | Add type annotations to all untyped functions in `quantive/` (check with `mypy --strict`) | Nov 20 | `mypy --strict quantive/` produces zero errors | Mypy strict mode passes |
| D8.4 | Create a `CONTRIBUTING.md` for the `quantive/` package: how to add a new solver, extend the scenario engine, or modify the optimization model | Nov 21 | Contributing guide exists and is accurate | New contributor can follow guide to add a solver |
| D8.5 | Implement solver plugin architecture: new solvers can be registered via entry points in `pyproject.toml` without modifying `registry.py` | Nov 22 | Plugin-based solver registration works | Test: add solver via entry point, no registry changes |
| D8.6 | Create performance regression benchmarks: automated test that runs the full pipeline and fails if runtime increases by > 20% from baseline | Nov 25 | Performance regression test in CI | Test passes with current code |
| D8.7 | Write migration guide for upgrading from v0.1 to v0.2: document all API changes, new features, and breaking changes | Nov 27 | Migration guide published | Guide covers all changes |
| D8.8 | Create a CHANGELOG.md tracking all implemented improvements across the 3-month period | Nov 28 | Changelog covers Phase 1-3 changes | Changelog is comprehensive and accurate |

---

# APPENDICES

## Appendix A: Weekly Capacity Assumptions

| Role | Headcount | Hours/week | Capacity |
|------|-----------|------------|----------|
| Backend Developer | 2 | 40 each | 80 hrs/week |
| Frontend Developer | 2 | 40 each | 80 hrs/week |
| Data Engineer | 1 | 40 | 40 hrs/week |
| QA Engineer | 1 | 40 | 40 hrs/week |
| **Total** | **6** | | **240 hrs/week** |

## Appendix B: Task Count by Category

| Category | Phase 1 | Phase 2 | Phase 3 | Total |
|----------|---------|---------|---------|-------|
| A: Database Management | 26 | 13 | 12 | **51** |
| B: UX/UI Improvements | 38 | 25 | 14 | **77** |
| C: Data Refresh | 17 | 12 | 12 | **41** |
| D: Simulation Engine | 21 | 12 | 14 | **47** |
| **Total** | **102** | **62** | **52** | **216** |

## Appendix C: Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| FRED API key unavailable or rate limited | Medium | High | Implement caching and synthetic fallback; obtain API key early in Week 1 |
| PostgreSQL RLS setup requires DBA expertise | Medium | Medium | Budget for DBA consultation in Week 2; use Docker init scripts |
| React frontend rewrite scope exceeds estimate | High | High | Prioritize 2 pages first; defer remaining to next quarter if behind |
| Solver performance regression from parallelization | Low | Medium | Run golden master tests after each parallelization change |
| Team capacity below assumed 240 hrs/week | Medium | High | Weekly capacity check; defer P3 tasks if running behind |
| External API breaking changes (Yahoo Finance) | Medium | Medium | Abstract API clients behind interfaces; maintain fallback sources |

## Appendix D: Definition of Done

A task is considered complete when:
1. Code is written and passes type checking (mypy for Python, tsc for TypeScript)
2. Unit tests are written and passing
3. Integration test covers the happy path at minimum
4. Code review completed by at least one other team member
5. Documentation updated (docstrings, API docs, or user-facing docs as applicable)
6. Deployed to staging environment and manually verified
7. Performance impact measured if the task touches database queries or API endpoints
