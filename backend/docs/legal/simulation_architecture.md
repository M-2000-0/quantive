# QUANTIVE — SIMULATION ENGINE ARCHITECTURE
## Ultra-Lightweight, Deterministic, Audit-Ready Financial Computation Blueprint

---

## 1. DETERMINISTIC ENGINE vs. LLM DIVISION OF LABOR

### Core Principle: Never Let an LLM Do Math

The fundamental architecture rule:

```
LLM = Natural Language Interface
Deterministic Engine = All Calculations
```

**Why This Matters:**
- LLMs hallucinate numbers. Governments sue over wrong numbers.
- LLMs are non-deterministic. Same input can produce different output.
- LLMs are slow for computation. Users need instant answers.
- LLMs cannot be audited. Deterministic code can be version-controlled and reproduced.

### Division of Labor

| Responsibility | Owner | Why |
|---------------|-------|-----|
| All financial calculations | Deterministic Engine | Exact, reproducible, auditable |
| Monte Carlo simulations | Deterministic Engine | Deterministic randomness with seed |
| Sensitivity analysis | Deterministic Engine | Matrix operations, no AI needed |
| Cash flow projections | Deterministic Engine | Date arithmetic, no ambiguity |
| Debt service schedules | Deterministic Engine | Day-count conventions, exact |
| Pension projections | Deterministic Engine | Actuarial math, must be precise |
| Credit scorecard metrics | Deterministic Engine | Formula-based, reproducible |
| Natural language summaries | LLM Layer | "Here's what this means" |
| Scenario framing | LLM Layer | "What if rates rise?" |
| Plain-language explanations | LLM Layer | "This means your taxes go up $X" |
| Council briefing generation | LLM Layer | "Write a 1-page summary" |
| Question answering | LLM Layer | "Why did you recommend this?" |
| Report narrative | LLM Layer | "Explain the tradeoffs" |

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Sliders  │  │ Inputs   │  │ Toggles  │  │ Date     │   │
│  │ (rates)  │  │ (amounts)│  │ (scenarios)│ │ Picker   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │          │
│       └──────────────┴──────────────┴──────────────┘          │
│                         │                                    │
│                    ┌────▼────┐                               │
│                    │  Event  │                               │
│                    │  Router │                               │
│                    └────┬────┘                               │
│                         │                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │
                    ┌─────▼─────┐
                    │ DETERMINISTIC│
                    │ ENGINE      │
                    │ (WASM/Python)│
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │  RESULT   │
                    │  CACHE    │
                    └─────┬─────┘
                          │
              ┌───────────┴───────────┐
              │                       │
        ┌─────▼─────┐          ┌─────▼─────┐
        │ DETERMINISTIC│        │ LLM LAYER │
        │ OUTPUT      │        │ FRAMING   │
        │ (numbers)   │        │ (narrative)│
        └─────┬─────┘          └─────┬─────┘
              │                       │
              └───────────┬───────────┘
                          │
                    ┌─────▼─────┐
                    │  UI RENDERS│
                    │  BOTH      │
                    └───────────┘
```

### Implementation: Python Backend + WASM Frontend

**Backend (Python):**
- Heavy calculations (Monte Carlo, multi-scenario)
- Audit trail logging
- Data persistence
- Complex scenarios requiring database access

**Frontend (WebAssembly):**
- Slider-driven instant updates
- Simple scenarios (< 1000 iterations)
- Client-side cash flow projections
- Real-time sensitivity analysis

**Why WASM for Frontend:**
- 10-100x faster than JavaScript for math
- Deterministic execution
- No network latency for simple scenarios
- Works offline (air-gapped deployment)

---

## 2. LIGHTWEIGHT SIMULATION ENGINE ARCHITECTURE

### Minimal Mathematical Models

The principle: **Maximum predictive power with minimum computational overhead.**

#### Model 1: Deterministic Cash Flow Tree
- **What:** Branching tree of cash flows over time
- **Computation:** O(n) where n = number of periods
- **Use case:** Basic debt service projections, revenue forecasts
- **Latency:** < 1ms for 10-year projection

#### Model 2: Sensitivity Matrix
- **What:** Grid showing outcome changes as input varies
- **Computation:** O(m*n) where m = scenarios, n = time periods
- **Use case:** "What if rates change by +/- 100bps?"
- **Latency:** < 10ms for 20x10 matrix

#### Model 3: Monte Carlo Light
- **What:** Random sampling with deterministic seed
- **Computation:** O(k*n) where k = iterations, n = periods
- **Use case:** Confidence intervals on projections
- **Latency:** < 100ms for 1000 iterations

#### Model 4: Interpolation Engine
- **What:** Pre-computed lookup tables with interpolation
- **Computation:** O(1) per query after pre-computation
- **Use case:** Yield curve shifts, price sensitivity
- **Latency:** < 1ms

#### Model 5: Linear Programming (Simplex)
- **What:** Optimal allocation under constraints
- **Computation:** O(n^3) worst case, O(n) typical
- **Use case:** Budget optimization, debt allocation
- **Latency:** < 50ms for 50 variables

### Browser-Side WASM Architecture

```
┌─────────────────────────────────────────────────────┐
│              BROWSER (WASM MODULE)                  │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │            CALCULATION CORE                  │   │
│  │                                             │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐ │   │
│  │  │ Cash Flow│  │Sensitivity│  │ Monte    │ │   │
│  │  │ Tree     │  │ Matrix   │  │ Carlo    │ │   │
│  │  │          │  │          │  │ Light    │ │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘ │   │
│  │       │              │              │       │   │
│  │       └──────────────┴──────────────┘       │   │
│  │                      │                      │   │
│  │               ┌──────▼──────┐              │   │
│  │               │  RESULT     │              │   │
│  │               │  AGGREGATOR │              │   │
│  │               └──────┬──────┘              │   │
│  │                      │                      │   │
│  └──────────────────────┼──────────────────────┘   │
│                         │                          │
│                    ┌────▼────┐                     │
│                    │  SLIDER │                     │
│                    │  EVENT  │                     │
│                    │  HANDLER│                     │
│                    └────┬────┘                     │
│                         │                          │
│                    ┌────▼────┐                     │
│                    │  RESULT │                     │
│                    │  CACHE  │                     │
│                    └────┬────┘                     │
│                         │                          │
│                    ┌────▼────┐                     │
│                    │  JS     │                     │
│                    │  BINDING│                     │
│                    └─────────┘                     │
└─────────────────────────────────────────────────────┘
```

### Slider-Driven Instant Updates

**How It Works:**

1. User moves interest rate slider from 4.5% to 5.0%
2. Slider event fires with new value
3. WASM module receives value via JS binding
4. WASM recalculates: cash flow tree + sensitivity matrix
5. WASM returns new results via shared memory
6. JS updates UI immediately (< 16ms = 60fps)

**Key Optimization: Pre-computed Interpolation Tables**

Instead of recalculating eve
