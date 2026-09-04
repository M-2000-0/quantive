# QUANTIVE — Complete UX/UI Design Brief

## Sovereign Financial Intelligence Platform

**Version:** 1.0
**Last Updated:** August 30, 2026
**Audience:** Design engineers, frontend developers, product managers

---

## 1. Design System

### 1.1 Color Palette

**Surfaces (3-shade dark system):**
- Background: `#090A0F`
- Surface Level 1: `#0F1117`
- Surface Level 2: `#161820`
- Surface Level 3: `#1C1E28`

**Text Hierarchy:**
- Primary (headings, data): `#e2e2e8`
- Secondary (labels, descriptions): `rgba(226,226,232,0.55)`
- Tertiary (metadata, captions): `rgba(226,226,232,0.3)`

**Data Colors (muted backgrounds, vivid indicators):**
- Positive/Up: `#34d399` (green)
- Negative/Down: `#f87171` (red)
- Warning/Watch: `#fbbf24` (yellow)
- Info/Active: `#60a5fa` (blue)
- Accent: `#a78bfa` (purple)
- Success: `#2dd4bf` (teal)

**Borders:**
- Default: `rgba(255,255,255,0.06)`
- Hover: `rgba(255,255,255,0.1)`
- Active: `rgba(255,255,255,0.12)`

### 1.2 Typography

**Font Family:** Inter (weights: 400, 500, 600, 700, 800)

**Scale:**
| Level | Size | Weight | Letter-spacing | Use |
|-------|------|--------|---------------|-----|
| Display XL | 56px | 800 | -0.04em | Hero numbers ($557.4B) |
| Display LG | 44px | 800 | -0.035em | Section hero |
| Display MD | 32px | 700 | -0.025em | Card headings |
| Display SM | 22px | 700 | -0.02em | Sub-headings |
| Stat Number | 28px | 800 | -0.025em | KPI values |
| Body | 14px | 400 | -0.01em | Default text |
| Small | 12px | 500 | 0 | Labels, metadata |
| Caption | 11px | 600 | 0.08em | Section titles, uppercase |
| Micro | 10px | 600 | 0.06em | Timestamps, fine print |

**Rules:**
- All numbers use `font-feature-settings: 'cv11'` for tabular alignment
- Section titles are always uppercase with 0.08em letter-spacing
- Unit suffixes (%, B, yr, bps) are always 50% opacity of the parent color
- No text should ever clip or overflow — use `overflow: hidden; text-overflow: ellipsis`

### 1.3 Spacing (8px Grid)

| Token | Value | Use |
|-------|-------|-----|
| xs | 4px | Tight gaps, inline elements |
| sm | 8px | Card internal gaps |
| md | 12px | Between related elements |
| lg | 16px | Card padding, section gaps |
| xl | 20px | Card padding (premium) |
| 2xl | 24px | Content padding, major gaps |
| 3xl | 32px | Section separation |

### 1.4 Components

**Cards:**
- Background: `rgba(15,17,23,0.6)`
- Border: `1px solid rgba(255,255,255,0.06)`
- Border-radius: 12px
- Padding: 20px
- Hover: border transitions to `rgba(255,255,255,0.1)`
- No shadows by default — use backdrop-filter: blur(20px) for glass effect

**Buttons:**
- Primary: `background: #e2e2e8; color: #090A0F` (white on dark)
- Secondary: `background: transparent; border: 1px solid rgba(255,255,255,0.08)`
- Ghost: `background: transparent; border: none`
- Sizes: sm (5px 11px, 12px), default (8px 15px, 13px), lg (10px 20px, 14px)
- Border-radius: 8px
- Active: `transform: translateY(1px) scale(0.985)`

**Progress Bars:**
- Height: 4px
- Border-radius: 10px (pill shape)
- Background: `rgba(255,255,255,0.04)`
- Fill: linear-gradient with data color at 100% to 50% opacity
- Animation: 0.5s cubic-bezier(0.16,1,0.3,1) on width change

**Sparklines:**
- SVG polylines, 32px wide, 12px tall
- Stroke-width: 1.5px
- Stroke-linecap: round
- No fill — line only
- Color matches the data direction (green/red)

**Badges/Pills:**
- Height: 20px
- Padding: 2px 8px
- Border-radius: 10px (full pill)
- Font: 10px, 600 weight
- Background: data color at 10% opacity
- Text: data color at full

**Inputs:**
- Background: `rgba(255,255,255,0.035)`
- Border: `1px solid rgba(255,255,255,0.06)`
- Focus: border `rgba(255,255,255,0.12)`, box-shadow `0 0 0 3px rgba(255,255,255,0.08)`
- Border-radius: 8px
- Padding: 9px 13px

### 1.5 Layout

**Sidebar:**
- Width: 236px fixed
- Background: `#090A0F`
- Border-right: 1px solid `rgba(255,255,255,0.06)`
- Inactive links: 45% white opacity
- Active links: 100% white, with 2px left indicator bar at 60% opacity
- Section headers: uppercase, 10px, 600 weight, 30% white opacity

**Topbar:**
- Height: 52px
- Background: `#090A0F`
- Border-bottom: 1px solid `rgba(255,255,255,0.06)`
- Title: 15px, 600 weight

**Content Area:**
- Padding: 24px
- Overflow-y: auto
- Max-width: none (fluid)

**Grid System:**
- Gap: 16px
- Columns: flexible (use grid-template-columns with fr units)
- Common layouts: 2-column (2fr 1fr), 3-column (1fr 1fr 1fr), 4-column (repeat(4,1fr))

---

## 2. Navigation Structure

### Sidebar Sections

```
OVERVIEW
  Overview (dashboard)

INTELLIGENCE
  Portfolio Intelligence
  Market Intelligence

COMMAND
  Risk Command
  Optimization Engine
  Scenario Lab

ADVISOR
  AI Advisor

GOVERNANCE
  Compliance Center
  Audit Trail

SIMULATE
  Simulation Engine

ANALYZE
  Advanced Analysis

MONITOR
  Reports & Exports
  Settings
```

### Navigation Rules
- Only one active page at a time
- Active state: white text, 2px left bar, subtle background
- Hover state: 85% white, subtle background
- Sections are separated by 14px top padding
- Section labels: 10px, uppercase, 30% opacity

---

## 3. Page Specifications

### 3.1 Overview (Dashboard)

**Purpose:** Executive summary of the sovereign portfolio — what am I managing, how much, what changed, what should I do next.

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ HERO                                                     │
│ [Live indicator] Mexico Sovereign Portfolio              │
│ $557.4B                                                  │
│ +4.8% Efficiency | $12.7B Savings | 87/100 Risk         │
│                                    [Run Optimization]    │
│                                    [Scenario Analysis]   │
│                                    [Create Portfolio]    │
├──────────────────────────┬──────────────────────────────┤
│ CHART: 12-Month Trajectory│ AI ADVISOR                   │
│ (SVG area chart with      │ Refinancing Opportunity      │
│  benchmark comparison)    │ $2.4B savings | 92% conf.   │
│  1Y/3Y/5Y toggle          │ [Review Proposal]            │
│                           │ TODAY'S CHANGES              │
│                           │ -0.3% debt service cost      │
│                           │ +1.2% FX exposure            │
├──────────────────────────┴──────────────────────────────┤
│ SOVEREIGN METRICS STRIP (6 cells, ticker-style)          │
│ Debt-to-GDP | Fiscal Deficit | Avg Yield |              │
│ Refinancing Risk | Duration | FX Exposure                │
├────────────────────┬─────────────┬───────────────────────┤
│ DEBT ALLOCATION    │ RISK PROFILE│ ACTIVITY FEED         │
│ Treemap with 5     │ 4 risk bars │ 4 recent events      │
│ categories         │ with %      │ with timestamps       │
├────────────────────┴─────────────┴───────────────────────┤
│ QUICK COMMANDS (8 cards in 4x2 grid)                     │
│ Optimization | Risk | AI | Scenario |                    │
│ Compliance | Reports | Advanced | Audit                  │
├──────────────────────────────────┬───────────────────────┤
│ MATURITY WALL (stacked bar chart)│ SYSTEM STATUS         │
│ 5 years, 4 currencies           │ 5 services + sparklines│
│ with data labels                │ Uptime + Latency       │
└──────────────────────────────────┴───────────────────────┘
```

**Interactions:**
- Chart: 1Y/3Y/5Y toggle switches time range
- Maturity wall bars: hover shows tooltip with exact breakdown
- Treemap cells: hover scales up 2%, shows border glow
- Quick command cards: hover lifts 1px with border highlight
- All command buttons navigate to their respective pages

**Data Sources:**
- Portfolio total: `GET /api/portfolios`
- Metrics: `GET /api/risk`
- Market data: `GET /api/market-data/snapshot`
- AI recommendations: `GET /api/advisor/recommendations`

---

### 3.2 Market Intelligence

**Purpose:** Real-time market data, yield curves, sovereign-specific analytics, AI-driven insights.

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ [Live] Live Markets | Last updated 2 min ago   [Refresh]│
├──────────────────────────────────┬──────────────────────┤
│ SOVEREIGN PORTFOLIO METRICS      │ AI COMMAND CENTER    │
│ 8-cell grid with sparklines:     │ [Refinancing Alert]  │
│ Debt-to-GDP | Avg Maturity       │ Savings: $2.7B       │
│ Interest Expense | Funding Gap   │ Confidence: 91%      │
│ Debt Service | FX Exposure       │ [Review Proposal]    │
│ Fiscal Deficit | Refinancing Risk│                      │
├──────────────────────────────────┴──────────────────────┤
│ YIELD CURVE (SVG)              │ GLOBAL MARKETS         │
│ US Treasury curve 3M→30Y       │ 8-tile heatmap         │
│ Inversion zone highlighted     │ Green/red by magnitude │
│ 2Y-10Y spread: -24 bps        │ US, DE, MX, JP,        │
│ Current/1Y Ago toggle          │ CN, UK, BR, IN         │
├───────────────┬────────────────┬────────────────────────┤
│ GOVT BOND     │ CREDIT SPREADS │ FX RATES               │
│ YIELDS        │ AAA→BBB with   │ USD/MXN, EUR/USD,      │
│ US, DE, MX    │ bars, change,  │ USD/JPY, DXY, Gold     │
│ 4 maturities  │ percentile     │ with sparklines        │
│ each + spark  │ Mexico CDS     │                        │
├───────────────┴────────────────┴────────────────────────┤
│ MARKET EVENTS                │ AI MARKET INTELLIGENCE   │
│ Color-coded live feed:       │ Opportunity (green)      │
│ Fed, CPI, Auctions, ECB     │ Risk (yellow)            │
│ with timestamps              │ Insight (blue)           │
└──────────────────────────────┴─────────────────────────┘
```

**Interactions:**
- Refresh button: triggers data reload with spinner animation
- Yield curve: Current/1Y Ago toggles between curves
- Heatmap tiles: hover shows 7-day trend mini-chart
- Bond yield rows: expand to show full maturity breakdown
- Event stream: newest items have subtle pulse animation

---

### 3.3 Risk Command

**Purpose:** Comprehensive risk monitoring, VaR analysis, stress testing, and alerting.

**Sub-pages:**
- Risk Overview (default)
- Risk Dashboard (detailed)
- Early Warning
- Risk Radar
- Risk Intelligence
- Sovereign Health
- Consolidated Debt
- Vendor Risk
- Geopolitical Risk
- Political Feasibility
- Fiscal Impact
- National Resilience
- Event Impact
- War Room

**Risk Overview Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ PORTFOLIO VaR | CVaR (99%) | MAX DRAWDOWN | RISK SCORE  │
│ -2.8%        | -4.1%       | -6.2%        | Medium      │
├──────────────────────────┬──────────────────────────────┤
│ RISK BREAKDOWN           │ ACTIVE ALERTS                │
│ Market Risk    42% ━━━━━ │ [High] VaR breach detected  │
│ Credit Risk    28% ━━━   │ [Med]  Duration exceeds      │
│ Liquidity Risk 18% ━━    │ [Low]  Credit watchlist      │
│ Operational    12% ━     │                             │
├──────────────────────────┴──────────────────────────────┤
│ VaR BACKTEST CHART (line chart with confidence bands)   │
├─────────────────────────────────────────────────────────┤
│ STRESS TEST RESULTS (table with scenario outcomes)      │
│ 2008 Crisis | COVID | Rate Spike | FX Crisis | Custom   │
└─────────────────────────────────────────────────────────┘
```

**Alert Severity Colors:**
- High: red background at 8%, red left border
- Medium: yellow background at 8%, yellow left border
- Low: blue background at 8%, blue left border

---

### 3.4 Optimization Engine

**Purpose:** Multi-objective debt portfolio optimization with real solver (scipy SLSQP).

**Sub-pages:**
- Optimization Form (create new)
- Optimization Results
- Strategy Comparison
- Solver Tournament
- Savings Trace
- Maturity Ladder

**Optimization Form Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ SECTION 1: Portfolio & Method                           │
│ Portfolio: [dropdown] | Method: [dropdown]              │
│ [Mean-Variance | Min-Cost | Min-Risk | Multi-Objective] │
├─────────────────────────────────────────────────────────┤
│ SECTION 2: Objectives                                   │
│ Target Return: 6.0%  | Max VaR: 5.0%                    │
│ Max Drawdown: -10%   | Min Sharpe: 0.8                  │
│ Helper text under each field                             │
├─────────────────────────────────────────────────────────┤
│ SECTION 3: Constraints                                  │
│ Max FX Exposure: 30% | Min Avg Maturity: 5yr            │
│ Max Single Issuer: 15% | Duration Target: 6-8yr         │
│ Floating Rate Cap: 20% | Credit Rating Floor: BBB       │
├─────────────────────────────────────────────────────────┤
│ SECTION 4: Execution                                    │
│ [Run Optimization]                                       │
│ Estimated runtime: ~30 seconds                           │
└─────────────────────────────────────────────────────────┘
```

**Form Rules:**
- All inputs have real default values (no "e.g." placeholders)
- Helper text in 11px tertiary color under each field
- Dropdowns styled for dark theme (color-scheme: dark)
- Validation: red border on invalid fields with error message
- Submit button: full-width primary, disabled during calculation

---

### 3.5 Scenario Lab (What-If)

**Purpose:** Macro scenario simulation, stress testing, and comparative analysis.

**Sub-pages:**
- Scenario Comparison (default)
- Digital Twin
- Black Swan
- Pareto Frontier
- Policy Impact
- Stock Monitor
- National Digital Twin
- Crisis Simulation

**Scenario Comparison Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ PRESET SCENARIOS (6 cards)                              │
│ GFC 2008 | COVID-19 | Rate Spike |                      │
│ FX Crisis | Stagflation | Commodity Boom                 │
├─────────────────────────────────────────────────────────┤
│ CUSTOM SCENARIO BUILDER                                 │
│ Rate Shock: [+200 bps] | FX Shock: [-15%]              │
│ Growth Shock: [-3%] | Commodity: [+30%]                 │
├─────────────────────────────────────────────────────────┤
│ COMPARISON TABLE                                        │
│              │ Baseline │ GFC 2008 │ Custom │            │
│ Debt-to-GDP  │ 55.7%    │ 68.2%    │ 62.1%  │            │
│ Debt Service │ 18.4%    │ 24.1%    │ 21.3%  │            │
│ Risk Score   │ 87       │ 45       │ 62     │            │
├─────────────────────────────────────────────────────────┤
│ FAN CHART (TradingView Lightweight Charts)               │
│ Monte Carlo projection with confidence bands             │
│ 10th/25th/50th/75th/90th percentiles                    │
└─────────────────────────────────────────────────────────┘
```

---

### 3.6 AI Advisor

**Purpose:** Natural language interface for querying the portfolio, explainability, and AI-driven recommendations.

**Sub-pages:**
- Copilot Chat
- Explainability Engine
- ROI Engine
- Rating Agency Shadow Model
- Issuance Planner
- Constraint Builder
- Knowledge Graph
- Knowledge Network
- Institutional IQ
- Institutional Memory
- Sovereign Advisor
- Sovereign DSA
- AI Challenger
- AI Governance
- QAE (Quantum Amplitude Estimation)
- Assumption Tracker
- Model Validation

**Copilot Chat Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ AI ADVISOR                                              │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Chat messages area (scrollable)                     │ │
│ │                                                     │ │
│ │ User: What's our refinancing risk for 2027?         │ │
│ │                                                     │ │
│ │ AI: Based on current portfolio analysis:            │ │
│ │ • $68B maturing in 2027 (12.2% of total)           │ │
│ │ • Average coupon on maturing debt: 6.2%             │ │
│ │ • Current 10Y yield: 4.28%                          │ │
│ │ • Potential savings if refinanced now: $2.4B        │ │
│ │ • Recommended action: Issue 10Y bonds to           │ │
│ │   refinance 60% of 2027 maturities                 │ │
│ │                                                     │ │
│ │ Confidence: 92% | Source: NSS yield curve model     │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ [Ask about risk | Ask about optimization | ...]    │ │
│ │ Type your question...                     [Send]   │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

### 3.7 Compliance Center

**Purpose:** Fiscal rule monitoring, subnational entity tracking, DSA compliance.

**Sub-pages:**
- Compliance Dashboard
- Fiscal Rules
- AI Governance
- Legal Evidence
- Anti-Corruption
- Corruption Opportunity

**Fiscal Rules Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ FISCAL RULES STATUS                                     │
│ ┌─────────────┬──────────┬──────────┬────────────────┐  │
│ │ Rule        │ Limit    │ Current  │ Status         │  │
│ ├─────────────┼──────────┼──────────┼────────────────┤  │
│ │ Debt/GDP    │ < 60%    │ 55.7%    │ [Pass]         │  │
│ │ Deficit/GDP │ < 3.5%   │ 3.8%     │ [Breach]       │  │
│ │ DSR/Revenue │ < 20%    │ 18.4%    │ [Watch]        │  │
│ │ Interest/Rev│ < 15%    │ 9.4%     │ [Pass]         │  │
│ └─────────────┴──────────┴──────────┴────────────────┘  │
├─────────────────────────────────────────────────────────┤
│ SUBNATIONAL ENTITY MONITORING                           │
│ Entity-level compliance with drill-down                 │
│ Guaranteed debt flagged as distinct risk                │
├─────────────────────────────────────────────────────────┤
│ CONSOLIDATED ROLLUP (national + subnational)            │
└─────────────────────────────────────────────────────────┘
```

---

### 3.8 Audit Trail

**Purpose:** Immutable decision log, RBAC access tracking, version history.

**Sub-pages:**
- Audit Log (default)
- Decision History
- Decision Archive

**Audit Log Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ FILTERS: [Date Range] [User] [Action Type] [Resource]  │
├─────────────────────────────────────────────────────────┤
│ TIMESTAMP     │ USER        │ ACTION      │ RESOURCE    │
│ 2026-08-29    │ J. Martinez │ Optimization│ Portfolio A │
│ 14:32:01      │             │ executed    │             │
├───────────────┼─────────────┼─────────────┼─────────────┤
│ 2026-08-29    │ System      │ Risk alert  │ FX Exposure │
│ 14:18:22      │             │ triggered   │             │
├───────────────┼─────────────┼─────────────┼─────────────┤
│ ...           │ ...         │ ...         │ ...         │
└─────────────────────────────────────────────────────────┘
```

---

### 3.9 Simulation Engine

**Purpose:** Monte Carlo simulation with real stochastic models (Vasicek, CIR, Hull-White).

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ CONTROLS                                                │
│ Country: [Mexico] | Horizon: [5Y] | Model: [Vasicek]   │
│ Paths: [1000] | Steps/Year: [252] | [Run Simulation]   │
├──────────────────────────────────┬──────────────────────┤
│ YIELD CURVE (NSS fitted)         │ RATE FAN CHART       │
│ Observed points + fitted curve   │ p5/p25/p50/p75/p95   │
│ Interactive crosshair            │ Projection bands     │
├──────────────────────────────────┼──────────────────────┤
│ FX PROJECTION                    │ DEBT-TO-GDP FAN      │
│ Mean + confidence bands          │ IMF-style cone       │
│ GBM with documented limitations  │ Median + percentiles │
├──────────────────────────────────┴──────────────────────┤
│ BACKTEST RESULTS                                        │
│ 2008 crisis validation | PASS/NEEDS CALIBRATION         │
└─────────────────────────────────────────────────────────┘
```

**Charts:** TradingView Lightweight Charts (open source)
- Interactive crosshair on hover
- Zoom and pan support
- Responsive to container size

---

### 3.10 Advanced Analysis

**Purpose:** 11 ultra-niche sovereign debt analysis features.

**Layout (card grid):**

```
┌─────────────────────────────────────────────────────────┐
│ ADVANCED DEBT ANALYSIS                                  │
│ Select Country: [Mexico] | Select Instrument: [Bond A] │
├─────────────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│ │ CAC          │ │ Pari Passu   │ │ Index        │     │
│ │ Aggregation  │ │ Exposure     │ │ Inclusion    │     │
│ │ [Analyze]    │ │ [Analyze]    │ │ [Analyze]    │     │
│ └──────────────┘ └──────────────┘ └──────────────┘     │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│ │ Buyback      │ │ Debt-for-    │ │ Shadow       │     │
│ │ Optimization │ │ Nature Swaps │ │ Ratings      │     │
│ │ [Analyze]    │ │ [Analyze]    │ │ [Analyze]    │     │
│ └──────────────┘ └──────────────┘ └──────────────┘     │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│ │ Withholding  │ │ Custody      │ │ Creditor     │     │
│ │ Tax Effects  │ │ Chain Risk   │ │ Litigation   │     │
│ │ [Analyze]    │ │ [Analyze]    │ │ [Analyze]    │     │
│ └──────────────┘ └──────────────┘ └──────────────┘     │
│ ┌──────────────┐ ┌──────────────┐                       │
│ │ Yield Curve  │ │ Arrears /    │                       │
│ │ (NSS Sparse) │ │ Crowding-Out │                       │
│ │ [Analyze]    │ │ [Analyze]    │                       │
│ └──────────────┘ └──────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

**Each analysis card when clicked:**
1. Calls the corresponding `/api/advanced-debt/*` endpoint
2. Displays results in a modal or expanded section
3. Shows key findings with color-coded risk indicators
4. Includes "Why this matters" explanation
5. Links to relevant methodology documentation

---

### 3.11 Reports & Exports

**Purpose:** IMF/World Bank standard format exports with preview.

**Layout:**

```
┌─────────────────────────────────────────────────────────┐
│ Country: [Mexico] | Year: [2025] | Format: [CSV]       │
├─────────────────────────────────────────────────────────┤
│ ┌───────────────────┐ ┌───────────────────┐             │
│ │ IMF MTDS          │ │ IMF DSA           │             │
│ │ Medium-Term Debt  │ │ Debt Sustain.     │             │
│ │ Strategy          │ │ Analysis          │             │
│ │ [Download][Preview]│ │ [Download][Preview]│            │
│ └───────────────────┘ └───────────────────┘             │
│ ┌───────────────────┐                                   │
│ │ World Bank IDS    │                                   │
│ │ International     │                                   │
│ │ Debt Statistics   │                                   │
│ │ [Download][Preview]│                                  │
│ └───────────────────┘                                   │
├─────────────────────────────────────────────────────────┤
│ RECENT REPORTS (table)                                  │
│ Weekly Summary | Risk Report | Compliance Audit | ...   │
└─────────────────────────────────────────────────────────┘
```

**Preview Modal:**
- Full-width modal overlay with dark backdrop
- Scrollable data table with all columns
- Sticky header row
- Color-coded status cells (pass/borderline/fail)
- Download button in footer

---

### 3.12 Settings

**Purpose:** Account management, preferences, system configuration.

**Sub-pages:**
- Settings (default)
- System Status
- Notifications
- Training Academy
- Offline Mode
- Billing

---

## 4. Interaction Patterns

### 4.1 Loading States
- Skeleton screens with subtle shimmer animation
- Pulsing dots for inline loading
- Spinner for button actions (replaces button text)

### 4.2 Empty States
- Centered illustration + message
- "No data available" with action button
- "Connect a data source to get started"

### 4.3 Error States
- Red border on affected card
- Error message with retry button
- Toast notifications for non-blocking errors

### 4.4 Success States
- Green checkmark animation
- "Saved successfully" toast (auto-dismiss 3s)
- Subtle green flash on updated elements

### 4.5 Transitions
- Card hover: 0.2s cubic-bezier(0.16,1,0.3,1)
- Page transitions: fade 0.15s
- Modal open: scale from 0.95 + fade 0.2s
- Progress bar fill: 0.5s cubic-bezier(0.16,1,0.3,1)

### 4.6 Responsive Breakpoints
- Desktop: 1200px+ (full layout)
- Tablet: 768px-1199px (sidebar collapses)
- Mobile: <768px (single column, no sidebar)

---

## 5. Accessibility (WCAG 2.1 AA)

### 5.1 Color Contrast
- All text must meet 4.5:1 contrast ratio against background
- Data colors tested against `#090A0F`: green `#34d399` (7.2:1), red `#f87171` (5.1:1), blue `#60a5fa` (6.8:1)
- Interactive elements must have 3:1 contrast against adjacent colors

### 5.2 Keyboard Navigation
- All interactive elements focusable with Tab
- Focus ring: 2px solid `rgba(255,255,255,0.3)` with 2px offset
- Skip-to-content link
- Modal focus trap

### 5.3 Screen Reader Support
- All images have alt text
- ARIA labels on icon-only buttons
- Live regions for dynamic content updates
- Semantic HTML (nav, main, section, article)

### 5.4 Touch Targets
- Minimum 44x44pt for all interactive elements
- Adequate spacing between adjacent targets

---

## 6. Performance Requirements

- First Contentful Paint: < 1.5s
- Largest Contentful Paint: < 2.5s
- Cumulative Layout Shift: < 0.1
- Time to Interactive: < 3.5s
- Chart render: < 200ms
- API response display: < 100ms after fetch

---

## 7. Data Freshness

| Data Type | Refresh Rate | Source |
|-----------|-------------|--------|
| FX Rates | Real-time (WebSocket) | ECB, Treasury |
| Bond Yields | Every 15 min | Treasury, FRED |
| CDS Spreads | Every 5 min | Market feed |
| Portfolio Metrics | Every 5 min | Calculated |
| Risk Scores | Every 15 min | Calculated |
| AI Recommendations | On-demand | Engine |
| Compliance Status | Every hour | Rules engine |

---

## 8. File Structure

```
backend/app/templates/
├── base.html                    # Design system + sidebar
├── pages/
│   ├── dashboard.html           # Overview
│   ├── market.html              # Market Intelligence
│   ├── risk.html                # Risk Command
│   ├── optimizations-new.html   # Optimization Form
│   ├── copilot.html             # AI Advisor
│   ├── compliance.html          # Compliance Center
│   ├── audit.html               # Audit Trail
│   ├── simulation.html          # Simulation Engine
│   ├── advanced-debt.html       # Advanced Analysis
│   ├── reports.html             # Reports & Exports
│   ├── scenario-compare.html    # Scenario Lab
│   ├── settings.html            # Settings
│   └── ... (80+ page templates)
```

---

## 9. Implementation Priority

### Phase 1: Core Experience (Must Have)
1. Dashboard (Overview)
2. Market Intelligence
3. Risk Command
4. Optimization Engine
5. AI Advisor (Copilot)

### Phase 2: Intelligence Layer
6. Simulation Engine
7. Scenario Lab
8. Advanced Analysis (11 features)
9. Reports & Exports

### Phase 3: Governance
10. Compliance Center
11. Audit Trail
12. RBAC & Access Control

### Phase 4: Polish
13. All remaining sub-pages
14. Accessibility audit
15. Performance optimization
16. Mobile responsiveness

---

*This brief is a living document. Update as features are implemented and design decisions are made.*
