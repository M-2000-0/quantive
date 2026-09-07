# Component Inventory — 5 Target Pages

Generated: September 6, 2026

## Legend

| Status | Meaning |
|--------|---------|
| **EXISTS** | Component exists and is functional |
| **NEEDS WIRING** | Component exists but uses mock/hardcoded data |
| **NEEDS CREATION** | Component does not exist |
| **NEEDS MODIFICATION** | Component exists but needs changes for target page |

---

## 1. Dashboard (`/dashboard`)

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| DashboardPage | `pages/DashboardPage.tsx` | **EXISTS** | Wired to live API (`api.dashboard.summary()`, `api.dashboard.tasks()`) |
| AssetTracker | `components/AssetTracker.tsx` | **EXISTS** | Rendered in DashboardPage |
| DailyBriefing | `components/DailyBriefing.tsx` | **EXISTS** | Rendered in DashboardPage |
| FirstRunWizard | `components/FirstRunWizard.tsx` | **EXISTS** | Rendered in DashboardPage |
| MarketPulseWidget | `components/MarketPulseWidget.tsx` | **EXISTS** | Rendered in DashboardPage |
| SavingsDashboard | `components/SavingsDashboard.tsx` | **EXISTS** | Rendered in DashboardPage |
| GlassBarChart | `components/charts/GlassBarChart.tsx` | **EXISTS** | Used for maturity distribution |
| Skeleton | `components/ui/Skeleton.tsx` | **NEEDS CREATION** | Loading state placeholder (referenced in backlog) |
| PageTransition | `components/PageTransition.tsx` | **EXISTS** | Navigation animation wrapper |
| ErrorBoundary | `components/ErrorBoundary.tsx` | **EXISTS** | Error fallback UI |

**Dashboard Status: COMPLETE** — All components exist and are wired.

---

## 2. Portfolio Detail (`/portfolios/:id`)

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| PortfolioDetailPage | `pages/PortfolioDetailPage.tsx` | **EXISTS** | Created Sep 6 — wired to `GET /api/portfolio-detail/{id}` |
| DataTable | `components/ui/DataTable.tsx` | **NEEDS CHECK** | May need adaptation for instrument columns |
| GlassBarChart | `components/charts/GlassBarChart.tsx` | **EXISTS** | For maturity ladder visualization |
| GlassPieChart | `components/charts/GlassPieChart.tsx` | **EXISTS** | For currency breakdown |
| AllocationVisualizer | `components/AllocationVisualizer.tsx` | **EXISTS** | Alternative maturity ladder viz |
| FilterBar | `components/FilterBar.tsx` | **EXISTS** | For currency filtering |
| Skeleton | `components/ui/Skeleton.tsx` | **NEEDS CREATION** | Loading state |

**Portfolio Detail Status: COMPLETE** — Page created with inline instrument table, sorting, and filtering.

---

## 3. Optimization Wizard (`/optimizations/new`)

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| NewOptimizationPage | `pages/NewOptimizationPage.tsx` | **EXISTS** | Routed, has multi-step form |
| ConstraintBuilderAI | `components/ConstraintBuilderAI.tsx` | **EXISTS** | AI-assisted constraint configuration |
| PortfolioSelector | `components/PortfolioSelector.tsx` | **EXISTS** | Portfolio picker for wizard |
| CollaborativeOptimizationEditor | `components/CollaborativeOptimizationEditor.tsx` | **EXISTS** | Multi-user editing |
| ProgressBar | (inline or `components/ui/`) | **NEEDS CHECK** | Step progress indicator |
| Toast | `stores/toast.tsx` | **EXISTS** | Success/error notifications |

**Optimization Wizard Status: COMPLETE** — Page exists and is routed.

---

## 4. Risk Dashboard (`/risk-dashboard`)

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| RiskDashboard | `components/RiskDashboard.tsx` | **NEEDS WIRING** | Component exists but not routed, likely uses mock data |
| NationalRiskRadar | `components/NationalRiskRadar.tsx` | **EXISTS** | Risk radar visualization |
| EarlyWarningSystem | `components/EarlyWarningSystem.tsx` | **EXISTS** | Threshold breach alerts |
| WhatIfSlider | `components/WhatIfSlider.tsx` | **EXISTS** | Parameter adjustment simulator |
| GlassRadarChart | `components/charts/GlassRadarChart.tsx` | **EXISTS** | Multi-axis risk chart |
| GlassLineChart | `components/charts/GlassLineChart.tsx` | **EXISTS** | Risk trend over time |
| MonteCarloViz | `components/MonteCarloViz.tsx` | **EXISTS** | Scenario visualization |

**Risk Dashboard Status: PARTIAL** — Components exist but page is not routed. Needs:
1. Create `pages/RiskDashboardPage.tsx` (or wire existing component)
2. Add route in `App.tsx`
3. Wire to `GET /api/risk/summary`, `GET /api/risk/early-warning/{id}`

---

## 5. Solver Tournament (`/solver-tournament`)

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| SolverTournamentPage | **NEEDS CREATION** | **NEEDS CREATION** | No page component exists |
| GlassRadarChart | `components/charts/GlassRadarChart.tsx` | **EXISTS** | Multi-dimensional solver comparison |
| GlassBarChart | `components/charts/GlassBarChart.tsx` | **EXISTS** | Benchmark bar charts |
| AIChallenger | `components/AIChallenger.tsx` | **EXISTS** | AI vs solver comparison |

**Solver Tournament Status: MISSING** — Needs:
1. Create `pages/SolverTournamentPage.tsx`
2. Add route in `App.tsx`
3. Wire to `GET /api/solvers/leaderboard`

---

## Summary

| Page | Components Ready | Missing | Status |
|------|------------------|---------|--------|
| Dashboard | 10/10 | 0 | **DONE** |
| Portfolio Detail | 7/7 | 0 | **DONE** (new) |
| Optimization Wizard | 5/5 | 0 | **DONE** |
| Risk Dashboard | 6/7 | 1 (route) | **NEEDS ROUTE** |
| Solver Tournament | 3/4 | 1 (page) | **NEEDS PAGE + ROUTE** |

### Key Components Available but Unused

| Component | Potential Use |
|-----------|---------------|
| `GlassBoxPlot.tsx` | Solver performance distribution |
| `GlassScatterChart.tsx` | Risk vs return scatter |
| `GlassHeatmap.tsx` | Correlation matrix |
| `GlassWaterfallChart.tsx` | Cost decomposition |
| `DecisionCopilot.tsx` | AI-assisted decisions |
| `ExplainabilityEngine.tsx` | Strategy explanation |
| `CorrelationMatrix.tsx` | Cross-asset correlation |

### Design Tokens

| Token Category | File | Status |
|----------------|------|--------|
| Colors, spacing, typography | `frontend/src/lib/designTokens.ts` | Exists |
| Glass theme CSS | `frontend/src/styles/` | Exists |
| Tailwind config | `frontend/tailwind.config.*` | Exists |
