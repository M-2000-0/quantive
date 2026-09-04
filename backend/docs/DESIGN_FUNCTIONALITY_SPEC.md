# Quantive Design & Functionality Specification
## Version 1.0 — August 2026

---

## Introduction

This document defines the precise design language and functional requirements for Quantive, a sovereign finance intelligence platform. Every CSS value, interaction pattern, and behavioral specification in this document has been chosen to achieve one outcome: a product that feels indistinguishable from a first-party Apple application while serving the analytical depth of a Bloomberg Terminal.

The reference products informing this specification are:

- **Apple Vision Pro** — spatial depth, glassmorphism, motion choreography
- **BlackRock Aladdin** — data density without visual noise
- **Linear** — typography precision, interaction choreography, keyboard-first design
- **Stripe Dashboard** — number hierarchy, whitespace discipline, glass panel depth

The design philosophy is: **clarity is premium.** Every pixel exists to serve the user's comprehension. Decoration is eliminated. Information hierarchy is enforced through typography weight, spatial rhythm, and restrained color.

---

## 1. Design System — Foundational Tokens

### 1.1 Color Palette

The palette is built on three principles: (1) the dark background absorbs all ambient attention, (2) data colors communicate meaning without decoration, (3) border and surface treatments create depth through opacity, not brightness.

**Backgrounds (AMOLED dark hierarchy):**
```
--bg-primary:    #090A0F    (viewport background — pure, absorbs light)
--bg-surface:    #0F1117    (card surfaces — 3% lighter, establishes layer 1)
--bg-elevated:   #161923    (hover states, dropdowns — establishes layer 2)
--bg-interactive:#1C1F2B    (input focus, active states — establishes layer 3)
```

**Data Colors (communicate meaning, not decoration):**
```
--green:    #34D399    (positive, gains, compliant, below threshold)
--red:      #F87171    (negative, losses, breach, above threshold)
--blue:     #60A5FA    (primary accent, active states, links)
--yellow:   #FBBF24    (warning, elevated risk, approaching threshold)
--purple:   #A78BFA    (secondary accent, features, tags)
--teal:     #2DD4BF    (operational, system status, RBAC)
```

These are deliberately desaturated from their base values by approximately 15-20%. The reason: fully saturated colors on AMOLED black create visual vibration that fatigues the eye over extended use. A finance minister reviewing a 40-page debt report should not experience color fatigue by page 5.

**Text Hierarchy:**
```
--text:      #FFFFFF     (primary numbers, headlines — 100% white)
--text2:     #A1A1AA     (secondary text — 63% white)
--text3:     #52525B     (metadata, timestamps — 33% white)
```

**Borders:**
```
--border:    rgba(255, 255, 255, 0.06)    (default card border)
--border-hover: rgba(255, 255, 255, 0.10) (hover state)
--border-active: rgba(255, 255, 255, 0.15) (active/focus state)
```

### 1.2 Typography Scale

Every font size in the system maps to a specific use case. No size exists without a reason.

| Token | Size | Weight | Letter-Spacing | Use Case |
|-------|------|--------|----------------|----------|
| `display` | 48-56px | 700 | -0.03em | Hero portfolio value ($557.4B) |
| `h1` | 28-32px | 700 | -0.02em | Page titles |
| `h2` | 18-20px | 600 | -0.01em | Section titles |
| `h3` | 14-16px | 600 | 0 | Subsections, card titles |
| `body` | 13-14px | 400 | 0 | Descriptions, analysis text |
| `caption` | 11-12px | 500 | 0.06em | Labels, metadata, chart labels |
| `micro` | 9-10px | 500 | 0.08em | Timestamps, source citations |

**Critical rules:**
- All numbers use `font-variant-numeric: tabular-nums` so columns align in tables
- Currency symbols (`$`, `€`) render at 60% of the number's font size and are vertically aligned to the number's baseline
- Percentage changes (`+0.84%`, `-3bps`) use the same font size as their parent number — never smaller
- Section labels (e.g., "PORTFOLIO HEALTH") use 11px, weight 500, uppercase, 0.06em letter-spacing, `--text3` color

### 1.3 Spacing System (8px Grid)

All spacing is derived from an 8px base unit. This creates mathematical rhythm that the eye perceives as "orderly" without consciously understanding why.

```
--space-xs:   4px     (gap between tightly related elements)
--space-sm:   8px     (internal padding for small elements)
--space-md:   16px    (default padding for cards and sections)
--space-lg:   24px    (padding for major sections)
--space-xl:   32px    (page-level vertical spacing)
--space-2xl:  48px    (between major page sections)
```

### 1.4 Component Specifications

**Cards (Glass Panels):**
```css
background: rgba(15, 17, 23, 0.6);
backdrop-filter: blur(20px);
-webkit-backdrop-filter: blur(20px);
border: 1px solid rgba(255, 255, 255, 0.06);
border-radius: 12px;
padding: 24px;
transition: border-color 0.2s ease;
```

On hover, the border transitions from `0.06` to `0.10` opacity over 200ms. This is the only visual change — no scale transform, no shadow change, no color shift. The subtlety communicates: "this element is interactive" without shouting.

**Buttons:**
```
Primary:    background: #60A5FA, color: #090A0F, weight: 600, padding: 12px 20px, border-radius: 8px
Secondary:  background: transparent, border: 1px solid var(--border), color: var(--text2)
Destructive: background: #F87171, color: #090A0F
```

All buttons have a minimum height of 44px (Apple HIG touch target). On hover, primary buttons lighten by 8%. On active (mousedown), they darken by 4%. Transitions: `all 0.15s ease`.

**Progress Bars:**
```
Height: 4px
Border-radius: 2px
Background: rgba(255, 255, 255, 0.06) (track)
Fill: linear gradient from the data color at 100% to 80% opacity
```

No animation on the fill unless it's actively loading (in which case, a shimmer animation at 1.5s duration, ease-in-out, infinite).

---

## 2. Layout Architecture

### 2.1 Page Structure

Every page follows this skeleton:

```
┌────────────┬──────────────────────────────────────┐
│            │  Topbar (48px)                        │
│  Sidebar   ├──────────────────────────────────────┤
│  (240px)   │  Content Area                        │
│            │  max-width: 1100px, centered          │
│            │  padding: 32px 24px                   │
│            │                                       │
│            │  ┌──────────────────────────────┐    │
│            │  │ Section Header                │    │
│            │  │ (label + title + description) │    │
│            │  └──────────────────────────────┘    │
│            │                                       │
│            │  ┌──────────────────────────────┐    │
│            │  │ Content Blocks                │    │
│            │  │ (cards, charts, data grids)   │    │
│            │  └──────────────────────────────┘    │
└────────────┴──────────────────────────────────────┘
```

**Sidebar (240px fixed):**
- Background: transparent — the viewport background shows through
- Section labels (e.g., "INTELLIGENCE", "COMMAND") use 10px, uppercase, 0.08em spacing, `--text3` at 45% opacity
- Active link: 100% text opacity, left border accent (2px, `--blue`), background `rgba(96, 165, 250, 0.06)`
- Inactive links: 45% text opacity, no background
- Hover: 70% text opacity, background `rgba(255, 255, 255, 0.03)`
- Transitions: `all 0.15s ease`

**Content Area:**
- Maximum width: 1100px, centered horizontally
- Vertical rhythm: 24px between cards, 32px between sections
- Grid layouts use CSS Grid with `gap: 16px` or `gap: 24px`

### 2.2 Dashboard-Specific Layout

The dashboard is the most information-dense page. Its layout follows this hierarchy:

```
Row 1: Hero Section (1 full width)
  ├── Portfolio identity + key metrics
  └── Action buttons

Row 2: Chart + AI Insights (2 columns, 3:1 ratio)
  ├── Debt performance chart (SVG)
  └── AI Advisor card + today's changes

Row 3: Sovereign Metrics Strip (6 equal columns)
  └── One metric per column with sparkline

Row 4: Treemap + Risk + Activity (3 columns, 2:1:1 ratio)
  ├── Debt allocation treemap
  ├── Risk profile bars
  └── Activity feed

Row 5: Command Palette (4 equal columns, 2 rows)
  └── 8 navigation cards with colored icons

Row 6: Maturity Wall + System Status (3:1 ratio)
  ├── Stacked bar chart (years)
  └── System status with sparklines
```

---

## 3. Feature Specifications — Exact Functionality

### 3.1 AI Advisor (`/copilot`)

**User Flow:**
1. Page loads → immediately calls `GET /api/ai-advisor/portfolio-health`
2. Health score renders with a 300ms count-up animation from 0 to the actual value
3. Health factor bars animate left-to-right sequentially (50ms stagger between each)
4. Proposals section calls `GET /api/ai-advisor/refinancing-proposals` and renders cards
5. Insights section calls `GET /api/ai-advisor/insights` and renders priority-tagged cards
6. Chat input is focused by default — user can type immediately

**Chat Interaction:**
- User types question and presses Enter (or clicks Send)
- User's message appears instantly (optimistic rendering) with blue background
- Input clears and shows loading state
- API call to `POST /api/ai-advisor/ask?question=...` fires
- Response appears with confidence score and data sources
- Chat area auto-scrolls to bottom
- Response cards have a subtle border-left color: blue for responses, no border for user messages

**Expected Outcome:** The user asks "What is our refinancing risk for 2027?" and receives a specific, data-backed answer within 200ms, with the source of the data cited.

### 3.2 Risk Command (`/risk`)

**Stress Test Flow:**
1. User selects a scenario from dropdown (GFC 2008, COVID-19, Rate Spike, Currency Crisis, Stagflation)
2. Input fields auto-populate with that scenario's parameters
3. User can override any value manually
4. User clicks "Run Stress Test"
5. API call to `POST /api/simulation/stress-test` fires
6. Results render in 5 cards: Stressed Debt, Stressed DTG, Rate Impact, FX Impact, DTG Breach
7. Color coding: green if below threshold, red if breach, yellow if approaching

**Monte Carlo Flow:**
1. User clicks a model button (Vasicek, CIR, Hull-White)
2. Button shows loading state (spinner)
3. API call to `POST /api/simulation/run` with 5,000 paths fires
4. Results render: 3 summary cards (Rate Model, FX Model, Debt-to-GDP Fan)
5. SVG fan chart draws with 400ms animation — bands expand from center outward
6. 60% threshold line renders as a red dashed line with label

**Expected Outcome:** A finance officer selects "Currency Crisis" and clicks Run. Within 300ms, they see that stressed debt-to-GDP rises to 72.3%, breaching the 60% threshold, with a "HIGH" rating action likelihood. The fan chart shows the 90th percentile breaching 80%.

### 3.3 Optimization Engine (`/optimizations`)

**Optimization Flow:**
1. User selects objective (Minimize Cost, Minimize Risk, Maximize Duration, Balanced)
2. User adjusts constraint sliders (Max FX Exposure, Max Refinancing Risk, Maturity Range)
3. User clicks "Run Optimization"
4. API call to `POST /api/optimizer/run` fires
5. Results render: annual savings in large green text, 4 constraint status cards (PASS/FAIL)
6. Recommended actions appear as priority-tagged cards with specific dollar impacts

**Restructuring Simulator Flow:**
1. User adjusts haircut, maturity extension, coupon reduction via inputs
2. User selects instrument from dropdown
3. User clicks "Simulate"
4. API call to `POST /api/optimizer/restructure` fires
5. Results render: 4 cards showing NPV Relief, New Coupon, New Maturity, Annual Savings

**Expected Outcome:** The optimizer identifies $382M in annual savings from refinancing the 2027 USD bond. It recommends a $15-18B multi-tranche offering. The user can simulate what happens if they add a 5% haircut and extend maturity by 5 years — seeing the NPV relief in real time.

### 3.4 Advanced Analysis (`/advanced-debt`)

**Tab Navigation:**
- 6 analysis modules: CAC, Pari Passu, Ratings Shadow, Withholding Tax, Settlement Risk, Arrears
- Clicking a tab loads that module's API data
- Only one module loads at a time (not pre-fetched)
- Active tab: blue background, blue text
- Inactive tabs: transparent, gray text

**CAC Analysis Content:**
- 4 metric cards: With CAC, Without CAC, Single-Limb, Two-Limb
- "Hardest to Restructure" card with instrument name, outstanding amount, holder concentration, litigation risk
- Recommendation text at bottom

**Ratings Shadow Content:**
- 3 rating cards: Moody's (Baa2), S&P (BBB), Fitch (BBB) with outlook color
- Shadow model score and distance-to-upgrade/downgrade
- Factor analysis bars showing each factor's current score vs. upgrade threshold

**Expected Outcome:** A debt officer opens the Ratings Shadow tab and sees that the shadow rating is BBB+, 3 points from upgrade. They can see that reducing FX exposure to 30% would improve the external debt metric enough to trigger an upgrade consideration.

### 3.5 Settings (`/settings`)

**System Section:**
- 4 cards: Platform (name + version), Build, Encryption (algorithm), Active Features (count)
- All data from `GET /api/settings/system`

**Data Sources Section:**
- List of 6 data providers with status dot (green = active, yellow = configured), type, refresh rate, record count, cost (free/paid)
- 3 paid provider stubs shown as "not configured"

**Users Section:**
- User cards with avatar initial, name, email, role badge (blue), last active date
- Role distribution summary

**Security Section:**
- 3 cards: Encryption (algorithm + key rotation), Authentication (method + MFA status), RBAC (roles + permissions + active users)

**Audit Section:**
- 6 action-type counters (read, create, update, delete, export, login)
- Security events summary (failed logins, permission denied, unusual access)

**Expected Outcome:** An administrator opens Settings and immediately sees that all 6 free data sources are active, 5 users are registered across 5 roles, PQC encryption is active with 90-day key rotation, and 1,247 audit events occurred in the last 30 days with 3 failed login attempts.

---

## 4. Interaction Patterns

### 4.1 Loading States

Every API-dependent section shows a loading state before data arrives:
- Text: "Loading..." in `--text3` color, 12px font
- No skeleton screens (they add visual noise without improving perceived speed for data that arrives in <500ms)
- If an API call fails, show a red error message with the specific error and a "Retry" button

### 4.2 Animation Choreography

All animations follow this choreography framework:

| Phase | Duration | Easing | What Happens |
|-------|----------|--------|--------------|
| Enter | 200ms | cubic-bezier(0.25, 0.1, 0.25, 1) | Element fades in from 0% to 100% opacity |
| Count-up | 300ms | ease-out | Numbers animate from 0 to value |
| Bar fill | 400ms | cubic-bezier(0.25, 0.1, 0.25, 1) | Progress bars fill left to right |
| Chart draw | 500ms | ease-in-out | SVG paths draw from left to right |
| Stagger | 50ms | — | Delay between sequential elements |

No animation should exceed 500ms. The user should never wait for an animation to complete before being able to interact with the next element.

### 4.3 Error States

Every API call has three possible outcomes:

1. **Success (200):** Render data immediately
2. **Loading (pending):** Show "Loading..." text
3. **Error (4xx/5xx):** Show red text with error message and "Retry" button

The Retry button calls the same API endpoint again. If it fails twice, show "Service unavailable — try again later."

### 4.4 Empty States

When a section has no data (e.g., no optimization has been run yet):
- Show a centered message in `--text3` color: "Configure parameters and click Run Optimization"
- No illustrations, no icons, no decorative elements
- The empty state is the honest representation of "nothing here yet"

---

## 5. Accessibility Requirements

Every interactive element meets WCAG 2.1 AA:

- **Color contrast:** All text meets 4.5:1 contrast ratio against its background. White (#FFF) on #090A0F = 19.3:1. Text2 (#A1A1AA) on #090A0F = 8.2:1. Text3 (#52525B) on #090A0F = 3.1:1 — acceptable only for decorative text, never for essential information.
- **Focus indicators:** All interactive elements show a 2px blue outline on keyboard focus. The outline uses `outline: 2px solid #60A5FA; outline-offset: 2px`.
- **Touch targets:** All buttons, links, and interactive elements are minimum 44×44px.
- **Screen reader support:** All data tables use proper `<th>` headers. All charts include `aria-label` descriptions. All form inputs have associated `<label>` elements.
- **Keyboard navigation:** Tab order follows visual order. All modals can be dismissed with Escape. All forms can be submitted with Enter.

---

## 6. Performance Budget

| Metric | Target | Measurement |
|--------|--------|-------------|
| First Contentful Paint | < 1.5s | Lighthouse |
| Largest Contentful Paint | < 2.5s | Lighthouse |
| Cumulative Layout Shift | < 0.1 | Lighthouse |
| Total Blocking Time | < 200ms | Lighthouse |
| API response time (p95) | < 500ms | Server-side |
| CSS file size | < 15KB gzipped | Build |
| JS file size (shared) | < 5KB gzipped | Build |
| Per-page inline JS | < 10KB | Manual audit |

The CSS file (`quantive.css`) is served as a static asset with `Cache-Control: public, max-age=86400`. The shared JS file (`quantive.js`) uses the same caching strategy. No inline styles should exceed 200px in width or contain animation keyframes.

---

## 7. Conclusion

A product's premium status is not declared — it is experienced. The user does not read a specification and conclude "this is premium." They open the application, and within three seconds, their nervous system has already rendered a judgment based on the weight of the typography, the depth of the darkness, the responsiveness of the interface, and the precision of the information hierarchy.

This specification exists to make that judgment favorable. Every CSS value, every animation timing, every spacing token, and every interaction pattern has been chosen to serve a single purpose: **the user trusts this product with their most important decisions.**

The design is the product. The product is the brand. The brand is the valuation.
