# API Coverage Map — 5 Target Pages

Generated: September 6, 2026

## 1. Dashboard (`/dashboard`)

| Data Need | Endpoint | Status | Gap |
|-----------|----------|--------|-----|
| Portfolio summary (total debt, instruments, currencies) | `GET /api/dashboard/summary` | **LIVE** | None |
| Risk scores (refinancing, currency, interest rate) | `GET /api/dashboard/summary` | **LIVE** | None |
| Maturity distribution chart data | `GET /api/dashboard/summary` | **LIVE** | None |
| Top currencies breakdown | `GET /api/dashboard/summary` | **LIVE** | None |
| Priority tasks (active jobs, upcoming maturities) | `GET /api/dashboard/tasks` | **LIVE** | None |
| Market data (yield curve, FX rates) | `GET /api/market/snapshot` | **LIVE** | None |
| Daily briefing | `GET /api/briefing` | **LIVE** | None |
| Savings summary | `GET /api/savings/summary` | **LIVE** | None |
| Asset tracker | `GET /api/assets/all` | **LIVE** | None |

**Dashboard Status: FULLY WIRED** — All data needs have live endpoints.

---

## 2. Portfolio Detail (`/portfolios/:id`)

| Data Need | Endpoint | Status | Gap |
|-----------|----------|--------|-----|
| Portfolio metadata (name, description, dates) | `GET /api/portfolio-detail/{id}` | **LIVE** | None |
| Instrument table (name, type, currency, principal, coupon, maturity, spread) | `GET /api/portfolio-detail/{id}` | **LIVE** | None |
| Summary stats (total principal, avg maturity, weighted coupon, weighted spread) | `GET /api/portfolio-detail/{id}` | **LIVE** | None |
| Maturity ladder (principal by year) | `GET /api/portfolio-detail/{id}` | **LIVE** | None |
| Currency breakdown (principal by currency) | `GET /api/portfolio-detail/{id}` | **LIVE** | None |
| Instrument sorting (by maturity, principal, coupon, spread) | `GET /api/portfolio-detail/{id}?sort_by=...&sort_order=...` | **LIVE** | None |
| Currency filtering | `GET /api/portfolio-detail/{id}?currency=...` | **LIVE** | None |
| Risk summary for portfolio | `GET /api/portfolios/{id}/risk-summary` | **LIVE** | None |
| Run optimization (navigate to wizard) | Client-side route `/optimizations/new?portfolio={id}` | **LIVE** | None |

**Portfolio Detail Status: FULLY WIRED** — Backend endpoint exists and is registered. Frontend page created and routed.

---

## 3. Optimization Wizard (`/optimizations/new`)

| Data Need | Endpoint | Status | Gap |
|-----------|----------|--------|-----|
| Portfolio selector (list portfolios) | `GET /api/portfolios` | **LIVE** | None |
| Create optimization job | `POST /api/optimizations` | **LIVE** | None |
| Progress polling | `GET /api/optimizations/{id}/progress` | **LIVE** | None |
| SSE progress stream | `GET /api/optimizations/{id}/progress` (EventSource) | **LIVE** | None |
| View results | `GET /api/optimizations/{id}/report` | **LIVE** | None |
| View strategies | `GET /api/optimizations/{id}/strategies` | **LIVE** | None |
| View benchmarks | `GET /api/optimizations/{id}/benchmarks` | **LIVE** | None |

**Optimization Wizard Status: FULLY WIRED** — All endpoints exist.

---

## 4. Risk Dashboard (`/risk-dashboard`)

| Data Need | Endpoint | Status | Gap |
|-----------|----------|--------|-----|
| Risk summary (score, VaR, scenarios) | `GET /api/portfolios/{id}/risk-summary` | **LIVE** | None |
| Early warning signals | `GET /api/risk/early-warning/{entity_id}` | **LIVE** | None |
| Risk score by category | `GET /api/risk/{category}/summary?entity_id=...` | **LIVE** | None |
| Aggregate risk score | `GET /api/risk/aggregate/{entity_id}` | **LIVE** | None |
| VaR analysis | `GET /api/portfolios/{id}/var` | **LIVE** | None |

**Risk Dashboard Status: NEEDS PAGE ROUTE** — All endpoints exist but `/risk-dashboard` is not routed in `App.tsx`. Page component exists (`RiskDashboard.tsx`) but is not wired.

**Action Required:** Add route for risk dashboard page in `App.tsx`.

---

## 5. Solver Tournament (`/solver-tournament`)

| Data Need | Endpoint | Status | Gap |
|-----------|----------|--------|-----|
| Solver leaderboard (ranked benchmarks) | `GET /api/solvers/leaderboard` | **NEW** | Created Sep 6 |
| Benchmark details per solver | `GET /api/optimizations/{id}/benchmarks` | **LIVE** | None |
| Run new benchmark | `POST /api/optimizations` (triggers full pipeline) | **LIVE** | None |
| Solver comparison (radar chart) | Client-side computation from leaderboard data | **LIVE** | None |

**Solver Tournament Status: NEEDS PAGE ROUTE** — Backend endpoint created. Frontend page component exists (`SolverTournament.tsx` likely in components) but no routed page.

**Action Required:** Create `/solver-tournament` page route in `App.tsx`.

---

## Summary

| Page | Backend Endpoints | Frontend Route | Status |
|------|-------------------|----------------|--------|
| Dashboard | **9/9 live** | `/dashboard` | **DONE** |
| Portfolio Detail | **9/9 live** | `/portfolios/:id` | **DONE** (new) |
| Optimization Wizard | **7/7 live** | `/optimizations/new` | **DONE** |
| Risk Dashboard | **5/5 live** | Not routed | **BLOCKED** (needs route) |
| Solver Tournament | **4/4 live** | Not routed | **BLOCKED** (needs route) |

### Remaining Gaps (Sprint 2+)
1. Add `/risk-dashboard` route to `App.tsx`
2. Add `/solver-tournament` route to `App.tsx`
3. Wire `RiskDashboard.tsx` component to live endpoints
4. Create solver tournament page with radar chart visualization
