# QPF MVP Scope — Public Debt Optimization

**Status:** Draft
**Version:** 0.1
**Owner:** Quantive
**Phase 1 thesis:** *Can we take a realistic sovereign debt problem and produce a demonstrably better decision than a conventional baseline?*

---

## 1. Product thesis

QPF (working name; exact expansion TBD — "Quantive Portfolio Framework" / "Quantive Public Finance") is the decision-optimization infrastructure for governments. We start with one measurable problem: **public debt optimization**.

A treasury faces hundreds of debt instruments, multiple currencies, maturity and interest-rate exposures, refinancing requirements, liquidity constraints, and thousands of plausible economic scenarios. Combining those constraints makes the search space enormous — this is where human judgment, spreadsheets, and single-tool models break down.

QPF is not a quantum-computing company. The engine runs multiple approaches and answers a single question per problem:

> **Which method produces the best feasible solution for this problem?**

- Classical optimization
- Heuristics
- Quantum-inspired optimization
- Quantum/hybrid optimization

If classical wins, we use classical. If quantum wins, we use quantum. The customer buys **better decision optimization**, not hardware.

### The path

```
Debt → Treasury → Budget → Infrastructure → Procurement → Government Decision Intelligence
```

The moat is not owning a quantum computer. It is:
- the optimization models and government-specific problem formulations
- benchmark data and scenario generators
- solver orchestration ("which method wins")
- audit infrastructure
- eventually: automatic translation of messy government problems into the right mathematical optimization problem

### Why public debt first

- Value is **measurable** (financing cost, risk metrics) and denominated in currency, not vibes.
- Every sovereign has one; the problem is universal and politically visible.
- The data is (mostly) public: issuance calendars, debt bulletins, benchmark yields.
- Success is provable: a strategy that dominates a conventional baseline on the same constraints.

---

## 2. MVP scope (what we build)

```
Upload debt portfolio
  → define objectives
  → define constraints
  → generate scenarios
  → optimize (multi-solver orchestration)
  → benchmark vs. conventional baseline
  → stress-test
  → produce an auditable decision package
```

The MVP is an **engine + demo harness**, not a product. Its only job is to prove the thesis on one credible, reproducible instance.

### 2.1 Demo instance

| Parameter | Value |
|---|---|
| Portfolio size | $100B notional |
| Instruments | 50–100 (bills, fixed-coupon bonds, FRNs, FX-linked, a concessional loan) |
| Scenarios | 10,000 |
| Horizon | 5 years, quarterly granularity |
| Currencies | USD domestic + one FX tranche (e.g. EUR) |
| Seed | Fixed, for reproducibility |

Deliverable of the demo: a comparison table

```
Baseline     $6.42B annual financing cost
Strategy A   $6.18B   (engine X)
Strategy B   $6.21B   (engine Y)
Strategy C   $6.24B   (engine Z)
```

— plus refinancing risk, interest-rate exposure, FX exposure, stress resilience, constraint satisfaction, runtime, and behavior across scenarios. Then a government-grade report: what was optimized, why the strategy was selected, what assumptions were used, what alternatives exist, and how robust the result is.

### 2.2 In scope (phase 1)

1. Synthetic portfolio generator (credible sovereign profile).
2. Scenario engine (rates + FX) with documented calibration.
3. Faithful conventional baseline.
4. Mathematical problem formulation + classical optimizer.
5. Heuristic solver plug-ins.
6. Quantum-inspired solver plug-in (emulated; hardware-optional behind an interface).
7. Solver orchestration + winner arbitration.
8. Benchmarking and risk/stress metrics.
9. Auditable decision-package generator.
10. Demo harness + reproducibility (seeds, versions, hashes).

### 2.3 Non-goals (explicitly out of phase 1)

- Real government data ingestion, integrations, or compliance (procurement law, MTDS/DSA regulatory reporting).
- A multi-user platform or UI beyond the demo harness.
- Production-grade quantum hardware commitments.
- Blockchain, tokenization, or any carryover from the previous Omnichain concept.
- Full multistage stochastic programming research (see §5 — we approximate honestly).
- Advisory services, pricing, or custody of actual debt decisions.

---

## 3. The baseline (critical to credibility)

The demo only proves something if the baseline is **what a competent DMO actually does** — not a strawman. A fair, auditable baseline:

- **Status-quo rollover:** maturing instruments are rolled into the same tenors, maintaining the current portfolio composition. Issuance calendar follows today's pattern (bill share, coupon frequency, auction sizes).
- **Target-ATM heuristic:** issuance is tilted toward a stated target risk posture (e.g., target average time to maturity, refinancing-risk cap) the way a DMO's portfolio rules would, adjusting bill vs. bond share mechanically.
- **No look-ahead:** the baseline uses only information available at each decision date.

Both baseline and optimized strategies are evaluated on the **same** scenarios and the **same** constraints. The baseline is deterministic, its policy is written out explicitly, and its outputs are included in the audit package so a treasury quant can verify we didn't rig it.

**Acceptance bar (phase 1):** on the demo instance, at least one engine produces a strategy that
- satisfies all risk constraints and stress tests,
- strictly dominates the baseline on expected cost (or achieves materially lower risk at equal cost),
- with a full audit package proving the win is reproducible.

Wins that depend on an unrealistic assumption are failures, not successes — the modeling layer (§4) is where this is won or lost.

---

## 4. Modeling layer (the real moat)

The optimizer is downstream of the model. If the model is wrong, "better" is an artifact. Phase 1 model choices are deliberately standard, transparent, and defensible — innovation here is a later-phase play.

### 4.1 Term structure / rates

- **Scenario generator:** PCA bootstrap from historical yield-curve moves (documented source + window) combined with a small number of explicit stress regimes (normal, persistent hike, recession, re-anchoring). Optionally a 2-factor Gaussian model (level + slope) for clean interpolation of 10,000 paths.
- **No-arbitrage sanity:** forward curves and coupon cashflows priced consistently.

### 4.2 FX

- One foreign tranche. FX scenarios correlated with rate regimes (e.g., a rates-stress regime carries a depreciation shock).
- FX risk is reported as a constraint and as a stress metric, not silently optimized away.

### 4.3 Instruments

- T-bills (3M/6M/12M), fixed-coupon bonds (2Y–30Y), FRNs, an indexed or FX-linked bond, one concessional loan. Cashflows, accrued interest, and call/prepay assumptions explicit.

### 4.4 Cost objective

- Primary: **expected present-value financing cost** over the horizon.
- Reported alongside: cost distribution percentiles, CVaR, and refinancing-risk metrics. The decision report shows cost *and* risk, not cost alone.

---

## 5. Problem formulation

This is the heart of the MVP and must be written down precisely and reviewed before any solver runs.

### 5.1 Decision variables

Issuance decisions per period per tenor/currency/instrument class (bill vs. bond vs. FX), consistent with the auction calendar granularity. If instrument *selection* (discrete issuance calendar slots) is required, we get mixed-integer structure; otherwise the core is a large-scale linear/quadratic program over scenarios.

### 5.2 Constraints (candidate set)

- **Rollover feasibility:** every maturing instrument is refinanced or repaid from a stated primary surplus path.
- **Refinancing risk:** share of debt maturing within 12 months ≤ cap; minimum average time to maturity (ATM).
- **Interest-rate risk:** fixed/floating mix bounds; duration band.
- **FX risk:** foreign-currency share cap (matching the baseline's posture).
- **Issuance calendar:** per-tenor auction size within [min, max]; annual issuance within limits; coupon-smoothening.
- **Liquidity:** minimum cash buffer over the horizon.
- **Market absorption:** realism cap on how much a single tenor can absorb in a period.

### 5.3 Objective variants

- Min expected cost (with hard risk constraints) — the default for the demo.
- A second configuration: min expected cost + λ·CVaR for a risk-tilted view, used to show trade-offs rather than a single answer.

### 5.4 Honest tractability position

Full multistage stochastic programming on 10,000 scenarios is heavy. Phase 1 uses the approach DMOs themselves use and that is explainable to them: **policy search over strategy parameters** (e.g., issuance tilt by regime, bill-share rule, ATM glide path) with scenario-based evaluation. The optimizer searches over policy space; scenarios evaluate each policy. This is rigorous, auditable, and cheap to explain — and still a real optimization problem whose search space classical/quantum approaches can attack differently.

---

## 6. Solver orchestration ("which method wins")

### 6.1 Architecture

```
instance (canonical JSON: portfolio, objectives, constraints, scenarios)
        │
        ├─ solver: classical       (HiGHS/SCIP; Gurobi if licensed)
        ├─ solver: heuristic       (GA, simulated annealing, GRASP on policy space)
        ├─ solver: quantum-inspired (QUBO encoding → simulated annealing / path relinking)
        └─ solver: quantum/hybrid  (D-Wave hybrid BQM sampler, optional; emulated otherwise)
        │
        └─ arbiter: pick best feasible solution by primary objective, tie-breaks, time budget
             └─ leaderboard + provenance per solver → audit package
```

- Every solver consumes the **same** canonical instance and returns `(solution, objective, feasibility, runtime, provenance)`.
- Arbiter rules are explicit: feasibility first, then primary objective, then documented tie-breakers.
- Solver plug-ins are behind one interface; hardware is swappable and never assumed.

### 6.2 Quantum-inspired honesty

The quantum-inspired path is *emulated* (QUBO → simulated annealing / path relinking / tabu) so the pipeline works with zero external dependency. A real D-Wave or similar backend is an optional plug-in used only to demonstrate the orchestration story; the demo must not depend on it.

### 6.3 What the demo shows

A per-instance leaderboard: which method produced the best feasible solution, at what runtime, with what objective — proving the "engine, not quantum" narrative in the demo itself.

---

## 7. Benchmarking, stress, and audit metrics

### 7.1 Performance metrics (reported per strategy)

- Expected annual financing cost and PV cost
- Cost distribution percentiles (5/50/95) and CVaR
- Refinancing risk (share maturing < 12m), ATM, duration
- Fixed/floating mix, FX share
- Constraint satisfaction (explicit pass/fail per constraint per scenario)

### 7.2 Stress tests

- Severe parallel rate shock (+300bp sustained)
- Rollover freeze / market closure (forced to bills for 2 periods)
- FX shock (depreciation + inflation pass-through)
- Refinancing-gap worst case
- Results: worst-case cost, breaches, and whether the strategy degrades gracefully vs. the baseline

### 7.3 Robustness checks

- Rank stability of strategies across scenario subsets (bootstrap)
- Sensitivity to model assumptions (ATM target, FX cap, λ)
- If a strategy's win evaporates under modest parameter perturbation, the report says so.

### 7.4 Audit package (decision report)

Generated artifact containing:
- Inputs: portfolio JSON, objectives, constraints, scenario generator config, seeds
- Hashes + software versions (reproducibility manifest)
- Formulation file (the §5 problem, machine-readable and human-readable)
- Per-solver logs and leaderboard
- Selected strategy, rationale, alternatives considered, and why they lost
- Assumptions, limitations, robustness summary
- Formats: Markdown + HTML/PDF export

---

## 8. Milestones

| # | Milestone | Exit criterion |
|---|---|---|
| M0 | Repo setup: data model, canonical instance format, seeding | `generate_portfolio()` produces the $100B instance reproducibly |
| M1 | Scenario engine + baseline | 10,000 scenarios with documented calibration; baseline policy runs and is auditable |
| M2 | Formulation + classical optimizer | Feasible strategies produced; constraint pass/fail verified |
| M3 | Heuristics + quantum-inspired + arbiter | All solvers run on same instance; leaderboard produced |
| M4 | Stress, metrics, report generator | Full audit package generated end-to-end |
| M5 | Demo harness + validation | Thesis test: does an engine beat the baseline credibly? Internal review gates M5 |

**Phase 1 "go" decision:** M5 produces a defensible dominant strategy with a complete audit package. "No" → we have a calibrated scenario engine and a credible baseline, which is still a meaningful deliverable for the next problem.

---

## 9. Proposed tech stack

- **Language:** Python 3 (scientific ecosystem dominates here; hiring + integration path)
- **Modeling/data:** numpy, pandas, scipy; dataclasses/pydantic for canonical instances
- **Classical solvers:** HiGHS (open-source LP/MILP), SCIP or OR-Tools; optional Gurobi flag
- **Heuristics:** DEAP (GA) / scipy.optimize (SA); hand-rolled GRASP
- **Quantum-inspired:** dimod/neal (QUBO + simulated annealing) or equivalent pure-Python QUBO sampler
- **Reports:** Jinja2 → Markdown/HTML; optional LaTeX/PDF
- **Determinism:** fixed seeds, pinned versions, hash manifest

Everything open-source first; nothing in the demo requires a paid license.

---

## 10. Open decisions (need owner input)

1. **Repo state:** the workspace was cleared (`.git`, prior files gone). Do we initialize a fresh QPF repo here, or a separate one?
2. **Name:** does QPF stand for something we commit to publicly?
3. **Currency mix:** single-currency demo first, or include the FX tranche from day one (recommended: include it — FX risk is half the story)?
4. **Horizon/granularity:** 5y quarterly is the proposal; confirm.
5. **Risk posture of the baseline portfolio:** target ATM / refi-risk caps must be chosen to be defensible (e.g., reflective of a typical EM sovereign).
6. **Quantum access:** emulation-only for the demo, or do we have D-Wave/other access to exercise the real hybrid plug-in?
7. **Cost vs. risk objective:** default is hard-constraint + min expected cost; confirm the CVaR variant is worth the extra M2 time.

---

## 11. What success looks like

A single-page artifact:

> "On a realistic $100B sovereign portfolio over 10,000 scenarios, engine **X** produced a feasible issuance strategy with expected annual financing cost **$6.18B** vs. **$6.42B** for the conventional baseline — same constraints, same scenarios, same risk posture — with a full audit package and reproducible results."

If we can produce that credibly, we have a company-shaped problem. Until then, we have a benchmark engine and a modeling layer — which is exactly the moat we want to keep building on.