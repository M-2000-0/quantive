# Quantive — Sprint Backlog: Phase 1 Category B (UX/UI)

**Sprint Period:** Weeks 1–4 (September 1–30, 2026)
**Team:** 2 Frontend Engineers (FE-1, FE-2), 1 Backend Engineer (BE-1)
**Sprint Cadence:** 1-week sprints (4 sprints total)

---

## Story Point Scale

| Points | Definition |
|--------|-----------|
| 1 | Trivial — config change, one-line fix, label update |
| 2 | Small — simple component wiring, no new logic |
| 3 | Medium — single component with state management and API integration |
| 5 | Large — multi-component feature with routing, validation, and error handling |
| 8 | Extra Large — significant new subsystem, multiple API endpoints, complex state |
| 13 | Epic — break down further; do not commit to this in one sprint |

**Velocity assumption:** FE-1 and FE-2 each complete ~20 points/sprint. BE-1 completes ~15 points/sprint (backend work is more interspersed with testing).

---

## Sprint 1: Foundation (Sep 1–5)

**Sprint Goal:** Complete design audit, component inventory, and API layer scaffolding. Ship `dashboard/summary` endpoint.

### User Stories

| ID | Story | Points | Assignee | Acceptance Criteria |
|----|-------|--------|----------|-------------------|
| S1-01 | **As a** frontend developer, **I want** a screenshot baseline of all 5 target pages **so that** we have a before/after comparison. | 2 | FE-1 | 5 annotated screenshots captured; hardcoded vs. dynamic data labeled in a shared document. |
| S1-02 | **As a** frontend developer, **I want** a component mapping spreadsheet linking existing React components to the 5 target pages **so that** we know what's reusable. | 3 | FE-2 | Spreadsheet produced with columns: Page → Existing Component → Status (exists/needs creation/needs modification). Must reference `frontend/src/components/` inventory. |
| S1-03 | **As a** frontend developer, **I want** an API coverage map showing which endpoints exist for each page's data needs **so that** we know backend gaps. | 3 | FE-1 | Document listing: Page → Data Need → Existing Endpoint → Gap (yes/no). Must scan all files in `backend/app/api/`. |
| S1-04 | **As a** backend engineer, **I want** to create `GET /api/v1/dashboard/summary` returning total debt, instrument count, currency count, avg maturity, and risk scores from the database. | 5 | BE-1 | Endpoint returns JSON with fields: `total_debt`, `instrument_count`, `currency_count`, `avg_maturity_years`, `risk_scores`. Data pulled from real DB, not hardcoded. Response time < 500ms. |
| S1-05 | **As a** frontend developer, **I want** to review TypeScript types in `frontend/src/types/index.ts` and identify gaps for API response shapes. | 2 | FE-2 | List of missing types (e.g., `DashboardSummary`, `PortfolioDetail`) with proposed interfaces documented. |
| S1-06 | **As a** frontend developer, **I want** to catalog existing CSS/Tailwind tokens and color system in `frontend/src/styles/` **so that** we have a design baseline. | 2 | FE-1 | Design token document listing: colors, spacing scale, typography, component variants. Identifies inconsistencies. |
| S1-07 | **As a** backend engineer, **I want** to add OpenAPI docs (summary, description, response_model) to the new dashboard endpoint. | 1 | BE-1 | Swagger UI at `/docs` shows description and example response for `GET /api/v1/dashboard/summary`. |

**Sprint 1 Total: 18 points**

---

## Sprint 2: Dashboard & Portfolio Detail (Sep 8–12)

**Sprint Goal:** Ship live dashboard with real data. Ship portfolio detail page with instrument table and maturity ladder. Create all remaining backend API endpoints.

### User Stories

| ID | Story | Points | Assignee | Acceptance Criteria |
|----|-------|--------|----------|-------------------|
| S2-01 | **As a** backend engineer, **I want** to create `GET /api/v1/portfolios/{id}/detail` returning portfolio with instruments, summary stats, and maturity distribution. | 5 | BE-1 | Endpoint returns nested portfolio JSON. Response time < 200ms (verified with `time.perf_counter`). Uses `selectinload` to avoid N+1. |
| S2-02 | **As a** backend engineer, **I want** to create `GET /api/v1/optimizations/{id}/progress` returning real-time job status. | 3 | BE-1 | Endpoint returns: `{ phase, percentage, started_at, estimated_completion }`. Reads from DB, not in-memory. |
| S2-03 | **As a** backend engineer, **I want** to create `GET /api/v1/risk/summary` returning risk scores, VaR, and early warnings. | 5 | BE-1 | Endpoint returns structured risk data matching `RiskSummary` type. Includes `var_analysis` array with confidence levels. |
| S2-04 | **As a** backend engineer, **I want** to create `GET /api/v1/solvers/leaderboard` returning ranked benchmark results. | 3 | BE-1 | Endpoint returns array of `BenchmarkRow` objects ranked by weighted score. Includes `solver_type`, `execution_backend`, `optimality_note`. |
| S2-05 | **As a** frontend developer, **I want** to replace hardcoded stats in `App.tsx` with live data from `GET /api/v1/dashboard/summary` using `@tanstack/react-query`. | 5 | FE-1 | Dashboard shows real values from API. Stats update on page load. Loading state handled with skeleton (existing `Skeleton.tsx`). |
| S2-06 | **As a** frontend developer, **I want** to replace the hardcoded bar chart in `App.tsx` with a `recharts` `BarChart` using maturity distribution data. | 3 | FE-1 | Chart renders real data from API response. Uses existing `GlassBarChart.tsx` from `components/charts/`. |
| S2-07 | **As a** frontend developer, **I want** to replace the hardcoded task list with data from `GET /api/v1/dashboard/tasks` (or inline computed from summary). | 3 | FE-2 | Task list shows real pending items: upcoming maturities, active jobs. Empty state handled gracefully. |
| S2-08 | **As a** frontend developer, **I want** to wire portfolio detail page to `GET /api/v1/portfolios/{id}/detail` with an instrument table. | 5 | FE-2 | Table renders instruments with columns: name, currency, principal, coupon, maturity, spread. Uses existing `DataTable.tsx` from `components/ui/`. |
| S2-09 | **As a** frontend developer, **I want** to add a maturity ladder visualization using `AllocationVisualizer.tsx`. | 3 | FE-2 | Chart shows principal amounts grouped by maturity year. Uses existing `GlassBarChart.tsx` or `AllocationVisualizer.tsx`. |
| S2-10 | **As a** backend engineer, **I want** to add OpenAPI docs to all 4 new endpoints. | 2 | BE-1 | All new endpoints have `summary`, `description`, `response_model` in Swagger. |

**Sprint 2 Total: 37 points**

> ⚠️ **Risk:** 37 points exceeds expected velocity (20 per FE, 15 for BE). **Mitigation:** Defer S2-03 and S2-04 to Sprint 3 if capacity is constrained. These are independent and can be deferred without blocking frontend work.

---

## Sprint 3: Portfolio Polish & Optimization Wizard (Sep 15–19)

**Sprint Goal:** Complete portfolio detail page (summary stats, filtering, sorting). Ship optimization wizard with 4-step form.

### User Stories

| ID | Story | Points | Assignee | Acceptance Criteria |
|----|-------|--------|----------|-------------------|
| S3-01 | **As a** frontend developer, **I want** to add portfolio summary stats panel: total debt, weighted avg coupon, weighted avg maturity, currency breakdown pie chart. | 3 | FE-1 | Summary panel displays computed metrics. Currency breakdown uses existing `GlassPieChart.tsx`. Metrics match manual calculation. |
| S3-02 | **As a** frontend developer, **I want** to add instrument filtering (by currency, type) and sorting (by maturity, principal, coupon rate) to the portfolio table. | 5 | FE-1 | Table supports column header click for sorting (ascending/descending toggle). Currency filter dropdown reduces visible rows. All filter states reset with "Clear filters" button. |
| S3-03 | **As a** frontend developer, **I want** to add a "Run Optimization" button on portfolio detail that navigates to the wizard with portfolio ID pre-selected. | 2 | FE-1 | Button navigates to `/optimizations/new?portfolio={id}`. Wizard reads portfolio ID from URL params. |
| S3-04 | **As a** frontend developer, **I want** to implement the 4-step optimization wizard shell with progress indicator and step navigation. | 8 | FE-2 | 4 steps render: Objectives → Constraints → Scenarios → Review. Progress bar shows current step. Back/Next buttons work. Form state persists across steps. Validation prevents advancing with invalid state. Uses existing `ProgressBar.tsx`. |
| S3-05 | **As a** frontend developer, **I want** to implement Step 1 (Objectives): weight sliders for 4 risk dimensions that must sum to 1.0. | 3 | FE-2 | 4 range sliders with labels and percentage display. Real-time validation: weights must sum to 1.0 (±0.01 tolerance). "Normalize" button auto-adjusts to sum to 1.0. |
| S3-06 | **As a** frontend developer, **I want** to implement Step 2 (Constraints): form inputs for max financing cost, max refi concentration, max currency exposure, max floating rate, min liquidity. | 3 | FE-2 | 5 numeric input fields with labels, units, and default values. Each field has inline validation (non-negative, within logical bounds). Values saved to wizard state. |
| S3-07 | **As a** frontend developer, **I want** to implement Step 3 (Scenario Config): named scenario checkboxes, Monte Carlo slider, seed input. | 3 | FE-2 | 5 named scenario checkboxes (base, IR shock, FX shock, credit spread, liquidity shock). Slider for Monte Carlo count (1K–10K, step 1K). Numeric seed input with randomize button. |
| S3-08 | **As a** frontend developer, **I want** to implement Step 4 (Review): summary card showing all configured parameters before submission. | 2 | FE-2 | Summary card displays: selected objectives with weights, configured constraints, scenario settings. Edit buttons on each section jump back to that step. |
| S3-09 | **As a** frontend developer, **I want** to add responsive layout for dashboard: sidebar collapses on < 1024px, cards stack on < 768px. | 3 | FE-1 | Dashboard renders correctly at 375px, 768px, 1024px, 1440px widths. No horizontal scroll. Uses existing `AppShell.tsx` and `Sidebar.tsx` from `components/layout/`. |
| S3-10 | **As a** frontend developer, **I want** to add loading skeletons for dashboard and portfolio detail pages during data fetch. | 2 | FE-1 | Skeleton placeholders appear during loading. Uses existing `Skeleton.tsx` and `Skeletons.tsx` from `components/ui/`. No layout shift when data replaces skeleton. |

**Sprint 3 Total: 34 points**

> ⚠️ **Risk:** S3-04 is an 8-point story — high risk for a single sprint item. **Mitigation:** Break into sub-tasks: (a) wizard shell + navigation (3pts), (b) step 1+2 content (3pts), (c) step 3+4 content (2pts). Assign sub-tasks across FE-1 and FE-2.

---

## Sprint 4: Wizard Submission & Responsive Polish (Sep 22–30)

**Sprint Goal:** Complete optimization wizard submission flow. Finalize responsive design and cross-cutting UI improvements.

### User Stories

| ID | Story | Points | Assignee | Acceptance Criteria |
|----|-------|--------|----------|-------------------|
| S4-01 | **As a** frontend developer, **I want** the wizard submission to call `POST /api/v1/optimizations` and navigate to a progress view. | 5 | FE-2 | Submit button sends all wizard state as API payload. On success, navigates to `/optimizations/{id}`. On error, shows toast with error message. Loading state on submit button prevents double-click. |
| S4-02 | **As a** frontend developer, **I want** the optimization progress view to poll `GET /api/v1/optimizations/{id}/progress` and show real-time status. | 5 | FE-2 | Progress bar updates every 2 seconds. Phase label changes (Scenario Generation → Solving → Benchmarking → Stress Testing → Complete). "View Results" button appears on completion. |
| S4-03 | **As a** frontend developer, **I want** to add a `PageTransition` wrapper for smooth navigation between all pages. | 2 | FE-1 | Animations on route changes. Uses existing `PageTransition.tsx` from `components/`. No layout shift. |
| S4-04 | **As a** frontend developer, **I want** to add error boundaries on all 5 target pages with retry and fallback UI. | 3 | FE-1 | Each page wrapped in existing `ErrorBoundary.tsx`. Fallback shows friendly message with "Retry" button. API error triggers boundary, not blank screen. |
| S4-05 | **As a** frontend developer, **I want** a global loading indicator (top bar) for API requests. | 2 | FE-1 | Thin progress bar at top of page during any API call. Uses `react-query`'s `useIsFetching()`. Appears/disappears smoothly (CSS transition). |
| S4-06 | **As a** frontend developer, **I want** to add toast notifications for all form submissions and mutations. | 3 | FE-1 | Toast appears after: portfolio create/update, optimization submit, constraint save. Uses existing `Toast.tsx`. Auto-dismiss after 3 seconds. Close button on each toast. |
| S4-07 | **As a** frontend developer, **I want** to add skeleton loading states for portfolio detail and wizard pages. | 2 | FE-1 | Skeletons render during data fetch. Uses existing `Skeleton.tsx`. No flash of empty content. |
| S4-08 | **As a** frontend developer, **I want** to implement responsive design fixes for portfolio detail and wizard pages. | 3 | FE-2 | Portfolio table scrolls horizontally on mobile. Wizard steps stack vertically on < 768px. All form inputs are usable on touch devices (min 44px tap target). |
| S4-09 | **As a** frontend developer, **I want** to add input validation feedback on wizard forms with inline error messages. | 3 | FE-2 | Invalid fields show red border + error message below. Validation triggers on blur, not on every keystroke. Submit button disabled until all fields valid. |
| S4-10 | **As a** frontend developer, **I want** to add a responsive design audit report: test all 5 pages at 375px, 768px, 1024px, 1440px and document issues. | 2 | FE-1 | Audit document with screenshots at all 4 breakpoints per page. Issues tracked with severity (critical/major/minor). |
| S4-11 | **As a** backend engineer, **I want** to add OpenAPI docs to `POST /api/v1/optimizations` and `GET /api/v1/optimizations/{id}/progress`. | 1 | BE-1 | Both endpoints documented in Swagger with request/response examples. |

**Sprint 4 Total: 31 points**

---

## Backlog Summary

| Sprint | Stories | Total Points | Key Deliverables |
|--------|---------|-------------|-----------------|
| Sprint 1 (Sep 1–5) | 7 | 18 | Design audit, component inventory, API coverage map, dashboard summary endpoint |
| Sprint 2 (Sep 8–12) | 10 | 37 | Live dashboard, portfolio detail page, 4 new API endpoints |
| Sprint 3 (Sep 15–19) | 10 | 34 | Portfolio polish (filtering, sorting, summary), full optimization wizard |
| Sprint 4 (Sep 22–30) | 11 | 31 | Wizard submission flow, error boundaries, loading states, responsive polish |
| **Total** | **38** | **120** | **5 target pages wired to live backend APIs** |

---

## Dependency Graph

```
Sprint 1:
  S1-01 (baseline) ──────────┐
  S1-02 (component map) ─────┤
  S1-03 (API coverage) ──────┼──▶ Sprint 2 (frontend work depends on audit outputs)
  S1-04 (dashboard API) ─────┤
  S1-05 (type review) ───────┤
  S1-06 (design tokens) ─────┘

Sprint 2:
  S2-01 (portfolio API) ─────┬──▶ S2-08 (portfolio table) ──▶ S3-01 (summary stats)
  S2-02 (progress API) ──────┤                               S3-02 (filtering/sorting)
  S2-03 (risk API) ──────────┤                               S3-03 (run optimization btn)
  S2-04 (leaderboard API) ───┘
  S2-05 (dashboard live) ────┐
  S2-06 (dashboard chart) ───┼──▶ S3-09 (responsive) ──▶ S4-03 (transitions)
  S2-07 (dashboard tasks) ───┘                            S4-04 (error boundaries)

Sprint 3:
  S3-04 (wizard shell) ─────┬──▶ S3-05 (step 1) ──┐
  S3-06 (step 2) ───────────┤                      ├──▶ S4-01 (submission)
  S3-07 (step 3) ───────────┤                      │    S4-02 (progress view)
  S3-08 (step 4) ───────────┘                      │    S4-09 (validation)
                                                   ┘
```

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Sprint 2 exceeds velocity (37 pts vs ~35 capacity) | High | Medium | Defer S2-03 (risk API) and S2-04 (leaderboard API) to Sprint 3. They're independent of dashboard/portfolio frontend work. |
| Optimization wizard (S3-04) is an 8-point epic | Medium | High | Already broken into sub-tasks in sprint planning. Pair FE-1 and FE-2 on this story. |
| Backend API endpoints require schema changes not yet migrated | Medium | Medium | A1–A4 database tasks must be completed in parallel by BE-1. If delayed, use mock endpoints for frontend development. |
| Existing components (`DataTable`, `AllocationVisualizer`) don't match new data shapes | Low | Medium | Time-box component adaptation to 2 hours. If adaptation exceeds that, build a thin wrapper component instead. |
| Responsive design reveals deep CSS issues in legacy Jinja2 templates | Low | Low | We're replacing Jinja2 with React — focus only on React components. Ignore Jinja2 layout issues. |

---

## Definition of Done (per story)

- [ ] Code merged to main branch
- [ ] TypeScript compiles with zero errors (`tsc --noEmit` passes)
- [ ] `oxlint` passes with zero errors
- [ ] Component renders in browser at all 4 breakpoints (375px, 768px, 1024px, 1440px)
- [ ] Loading state implemented (skeleton or spinner)
- [ ] Error state implemented (error boundary or inline message)
- [ ] Empty state implemented (when no data available)
- [ ] At least one unit test for new utility functions (if any)
- [ ] API endpoint has OpenAPI documentation (if new endpoint)
- [ ] Screenshot comparison: before and after stored in PR description
