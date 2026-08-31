# Quantive — Master Architecture Proposal (Audit + Plan)

> Response to Master Spec §72 BEFORE CODING. Verified locally 2026-08-31.

## 1. Audit — 10 Questions

### 1. Framework
- **Core engine `quantive/`**: pure Python library (`numpy>=1.26`, `scipy`, `pydantic>=2.5`, `pulp` CBC, `pandas`) — deterministic, no I/O, solver-agnostic `ProblemSpec` at `quantive/objectives/spec.py:37`.
- **Enterprise wrapper `backend/app`**: FastAPI 0.115 + SQLAlchemy 2.0 + Jinja2 SSR + Vite React 19 SPA + Electron 44 desktop. Two FastAPIs coexist: lightweight `quantive/api/main.py:33` (in-memory `AppState`) and full `backend/app/main.py:55` (enterprise RBAC/SOC2/PQC).
- **Frontend `frontend/`**: Vite 8 + React 19 + TS 6 + recharts + framer-motion + react-router 7 + tailwind 4. Entry `frontend/src/main.tsx:12`, static demo `App.tsx` mounted; 150+ glass components + 80 pages exist but not routed (see `work.md`).

### 2. Backend
FastAPI with `CORSMiddleware`, `SecurityHeaders`, `RateLimit`, `RBAC`, `ThreatDetection`, `Compression`, `RequestID` (`backend/app/main.py:147`). Versioned router at `/api/v1` aggregating 60+ sub-routers (`backend/app/api/__init__.py:63`). Async jobs via `ThreadPoolExecutor` (`quantive/jobs/manager.py`). `run.py:124` single-process dev launcher.

### 3. Database
- Dev: `sqlite:///./quantive.db` (`backend/app/config.py:13`, `quantive.db` exists) with WAL + FK pragmas (`database.py:43`).
- Prod: must switch to `postgresql://` with RLS — `app/security/rls_migration.sql` + `ContextVar` org/user/role (`database.py:10`) + `set_app_context()` on connect. `validate_production_config()` blocks sqlite+default SECRET_KEY in prod.
- ORM: `backend/app/models/__init__.py:59` `Organization → User → Portfolio → DebtInstrument → OptimizationJob → Strategy/BenchmarkResult/Scenario/OptimizationResult` + `AuditEvent` + `DatabaseAuditEntry` (hash-chain) + `DataProvenance` + `ModelVersion`.

### 4. Authentication
- JWT HS256 `python-jose` + `bcrypt` (`oauth2.py:31`), `SECRET_KEY` from settings (≥32 bytes), 30m access / 7d refresh, `OAuth2PasswordBearer(tokenUrl="/auth/login")`.
- RBAC matrix `backend/app/security/rbac.py:91` — 6 hierarchical roles (`system_admin > minister > treasury_officer > analyst > auditor > public_view`) × 20+ permissions. Enforced via `RBACMiddleware` + `require_role/require_permissions` dependencies + per-portfolio `PortfolioAccess`. MFA TOTP (`backend/app/api/mfa.py`), portfolio RBAC table, RLS org isolation. Note: `DISABLED_AUTH_ROUTER` string at `oauth2.py:176` — real auth lives in `app/api/auth.py` + `auth_extended.py` (verified importable).

### 5. Existing AI
**Not a stock predictor** — sovereign-debt financing optimizer:
- `scenario_cost_matrix()` at `costs.py` builds `C[i,s]` from instrument rates × FX factors × sector multipliers.
- `ProblemSpec.objective_value()` at `spec.py:160` weighted composite `w_cost·cost + w_refi·refi + w_ir·IR + w_fx·FX` (+ robust minimax variant).
- 3 solvers behind `SolverInterface` (`solvers/base.py:100`): `milp.py` CBC (globally optimal), `heuristic.py` SA, `qubo.py:40` quantum-inspired binary-expansion annealing on `SIMULATOR` with `to_qubo_matrix()` + classical repair. No fabricated quantum.
- Benchmark `benchmark/engine.py` + stress `stress/tester.py:101`.

### 6. Market Data
- Abstraction `backend/app/market_data/provider.py:237` `MarketDataProvider` ABC + `YieldCurve/YieldCurvePoint/FxRate/EconomicSnapshot/BenchmarkRate` unified schema, `RateLimiter` token-bucket, `Paginator`, `_request()` helper.
- Concrete: `treasury_fiscal.py`, `imf_connector.py`, `real_providers.py`, `fx_rates.py`, `yield_curve.py` (FRED/Treasury/IMF) with TTL cache (`cache.py`).
- Synthetic fallback `quantive/data/synthetic.py` (64 instruments, deterministic); `quantive/data/fixtures.py` demo portfolio. Frontend uses `frontend/src/api/mockAdapter.ts` when backend unavailable.

### 7. Prediction Generation
No ticker expected-return predictions today. Pipeline is `Portfolio+Problem+Scenarios → build_spec → solver → Strategy → ScenarioResult[]` (`orchestration.py:112` `run_full_job`). 4 profile strategies via re-weighted objectives (`strategies.py`). Financing-cost per scenario + refinancing/FX/IR risk, not equity returns.

### 8. Frontend Display
- `frontend/src/App.tsx:43` apple-shell demo (static `$12.4M / 8.7% / 96.2%` placeholders, not live) mounted by `main.tsx`.
- Full routed shell `components/layout/AppShell.tsx` + `Sidebar.tsx` + 80 pages under `src/pages/` + 150 components exist but **not wired** to `main.tsx` (per `work.md:107`). API client `src/api/index.ts` + `stores/auth.tsx` + `mockAdapter.ts`. `dist/` prebuilt.

### 9. Safest Integration Point
**Extend `quantive/` as isolated pure-Python packages** — no edits to `objectives/spec.py`, `solvers/*`, `scenarios/engine.py`, `orchestration.py` contracts. New code under `quantive/{features,investor,risk_engine,portfolio,backtesting,ml,regime,quantum,broker,execution,alerts,audit}` with clean imports from `quantive/models` + `quantive/data`. Wire to `quantive/api` + `backend/app` via new routers only. Keeps debt engine validated while equities engine grows beside it.

### 10. What Is Already Implemented vs Spec
| Spec Area | Status |
|---|---|
| Data validation / quality | Partial: `backend/app/market_data/quality.py`, `backend/app/api/data_quality.py`, `quantive/data` basic — no FeatureStore |
| Feature engineering / Feature Store (35) | No |
| Fundamental/Technical/Sentiment/Macro/Alt engines (6-11,17-20) | No |
| ML/Ensemble/Uncertainty (14-16) | No (only heuristic/annealing optimizers) |
| Factor model (12) | No |
| Regime detection (13) | `scenarios/regime.py` exists for debt regimes only, not equity market regimes |
| Risk engine (26) | Debt `objectives/spec.py:183 risk_metrics` + `objectives/risk_measures.py` VaR/CVaR — no equity portfolio risk (beta/Sharpe/Sortino/maxDD/correlation) as standalone service |
| Portfolio optimizer (22) | Debt LP only — no equity mean-variance/min-var/max-Sharpe/risk-parity/HRP/Black-Litterman |
| Quantum-inspired opt (23-24) | QUBO at `solvers/qubo.py` + `backend/app/optimization/quantum_abstraction.py` exists, needs `QuantumBackend` ABC formalization |
| Backtesting / Walk-forward / Overfitting defense (29-33) | No |
| Constraints (25) | Debt constraints only |
| Stress/Monte Carlo (27-28) | Scenario engine does MC + named crises — not equity stress distributions |
| Rebalancing/Tx cost/Liquidity (39-41) | No |
| Broker/Execution/Paper trading/Safety (42-45) | Abstract `Broker` not yet; `backend/app/optimization/solver.py` only |
| Audit/Versioning (46-47) | `AuditEvent`+`DatabaseAuditEntry` hash-chain + `ModelVersion` exist — needs model-versioning gate for ML |
| Monitoring/Drift (49) | `early_warning/engine.py` for sovereign debt — no ML drift |
| Dashboard/Explainability (50-51) | Placeholders only |

## 2. Proposed Modular Architecture

```
/quantive
  /data          — unified OHLCV schema, validation, quality engine (extends existing)
  /features      — FeatureStore, technical/fundamental/alt feature calculators, registry
  /investor      — InvestorProfile, risk-tolerance vs capacity, horizon, classification
  /risk_engine   — equity risk: vol/beta/Sharpe/Sortino/VaR/CVaR/DD/correlation/factor
  /portfolio     — optimizer: equal/MV/min-var/max-Sharpe/risk-parity/max-div/CVaR/BL/HRP
  /ml            — predictors (Ridge/Lasso/RF/XGB/MLP) + Ensemble + Uncertainty
  /regime        — market regime classifier (bull/bear/sideways/vol regime)
  /quantum       — QuantumBackend ABC + ClassicalSimulator/QuantumInspired/Qiskit backends
  /backtesting   — walk-forward, rolling windows, tx-cost/slippage, leakage guards
  /broker        — Broker ABC + adapters
  /execution     — Execution planner, safety (kill-switch, size, duplicate, stale price)
  /alerts        — regime/concentration/rebalance alerts
  /audit         — audit log + model versioning (wraps existing)
  /strategies    — Strategy ABC + library (momentum/mean-reversion/pairs/stat-arb/factor)
  existing: models, objectives, scenarios, solvers, benchmark, stress, analytics, ...
/backend/app/api — new routers thinly wrapping quantive/* (no business logic duplicated)
/frontend/src    — new pages/components under `features/portfolio/*` reusing `ui/` + `charts/`
```

**Principles:** Prediction ≠ Decision ≠ Execution ≠ Evaluation; one backend per problem; honest quantum labeling; reproducibility (seeded); feasibility is hard gate; every layer independently testable; no silent model replacement.

## 3. Implementation Order (Spec §71)

Phase 1 ✓ Audit (this doc) → Phase 2 Data+Features → Phase 3 Investor → Phase 4 Risk → Phase 5-6 Portfolio+Backtesting → Phase 7-15 ML/Ensemble/Regime/Quantum/Paper/Broker/Safety/Monitoring

Each phase: code + tests + docs + commit to `origin/main`.
