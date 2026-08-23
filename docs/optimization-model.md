# Optimization Model

This document describes the mathematical model compiled into a `ProblemSpec`
and solved by every backend.

## Decision variables

For a portfolio of `N` instruments, the decision vector is

```
x_i  ∈  [0, cap_i]      i = 1..N
```

where `x_i` is the amount issued/borrowed through instrument `i` and `cap_i` is
its market capacity. The total amount raised must equal the financing
requirement `R` (debt capacity constraint):

```
Σ_i x_i = R
```

## Scenarios

A scenario list of `S` scenarios with probabilities `p_s` (Σp = 1) describes
economic states. In each scenario, each instrument `i` has a financing cost
`C[i, s]` (annualized, in reporting currency). Cost coefficients are computed
from the coupon/rate model, the scenario's interest-rate and credit-spread
shocks, and (for foreign instruments) the FX level, which is expressed in
reporting currency per unit of foreign currency so that `FX > 1` means the
foreign currency appreciated and is *more expensive* for the reporting-currency
borrower.

## Objective

The composite objective is minimized:

```
min  w_cost·cost(x) + w_refi·refinancing_risk(x)
     + w_ir·interest_rate_risk(x) + w_fx·currency_risk(x)
```

### Financing cost

- **Expected-cost objective:** `cost(x) = Σ_i x_i · Σ_s p_s · C[i, s]`
  (linear in `x`).
- **Robust (minimax) objective:** `cost(x) = max_s Σ_i x_i · C[i, s]`
  (worst-case financing cost across scenarios). The robust mode is used by the
  `STRESS_RESILIENT` strategy profile and is linearized in the MILP with an
  epigraph variable `z ≥ Σ_i x_i·C[i,s]` for every scenario `s`.

### Refinancing / rollover risk

Maturities are bucketed into whole years `t = 1..15`. Let `M_t = Σ_{i: bucket(i)=t} x_i`
be the amount maturing in year `t`. Refinancing risk is the **peak-year
maturing amount**:

```
refinancing_risk(x) = max_t M_t
```

Minimizing this spreads maturities across the ladder and shrinks the largest
single rollover event. In the MILP it is linearized with an epigraph variable
`peak ≥ M_t` for every bucket `t`.

### Interest-rate risk

```
interest_rate_risk(x) = Σ_i x_i · vol_ir_i
```

where `vol_ir_i` is the exposure of instrument `i` to interest-rate shocks
(larger for floating-rate instruments and longer durations).

### Currency risk

```
currency_risk(x) = Σ_i x_i · vol_fx_i
```

where `vol_fx_i` is nonzero for instruments issued in a currency other than the
reporting currency and scales with the scenario FX volatility.

## Constraints

All constraints are evaluated by `ProblemSpec.constraint_violations(x)`, which
returns one `ConstraintStatus` per active constraint; a result is **feasible**
only if every constraint is satisfied within tolerance.

| Constraint | Form | Notes |
|---|---|---|
| Debt capacity | `Σ x_i = R` | equality; tolerance is relative to `R` |
| Instrument capacity | `x_i ≤ cap_i` | per-instrument bound |
| Floating-rate limit | `Σ_{floating} x_i ≤ f·R` | cap on floating-rate exposure |
| Currency limits | `Σ_{foreign} x_i ≤ c·R`, per-currency caps | FX exposure caps |
| Minimum liquidity | `Σ_{liquid} x_i ≥ ℓ·R` | must keep liquid instruments available |
| Refinancing limit | `M_t ≤ ρ·R` for all `t` | per-year maturity cap |
| Maturity concentration | `M_t ≤ μ·R` (max), optional `M_t ≥ ν·R` (min) | distribution shape |
| Cardinality | `#{i : x_i > ε} ≤ K` | integer constraint (MILP only) |
| Custom linear | `Σ_i a_i·x_i ≤ b` | user-defined linear constraints |

## Weights and profiles

The default `NamedStrategyProfiles` define four objective weightings used to
generate distinct strategies under the *same* constraint set:

| Profile | `w_cost` | `w_refi` | `w_ir` | `w_fx` | Behavior |
|---|---|---|---|---|---|
| `best_overall` | 1.0 | 1.0 | 1.0 | 1.0 | Balanced |
| `lowest_risk` | 0.3 | 3.0 | 3.0 | 3.0 | Minimize risk |
| `lowest_cost` | 4.0 | 0.2 | 0.2 | 0.2 | Minimize cost |
| `stress_resilient` | 1.0 | 1.0 | 1.0 | 1.0 | Robust minimax cost |

## Solver backends

- **MILP (`milp_cbc`)** solves the linearized model exactly with CBC; it
  returns a globally optimal solution when the status is `Optimal`.
- **Simulated annealing (`simulated_annealing`)** minimizes the composite
  objective (with the non-linear forms of the risk terms) using continuous
  moves; no optimality guarantee.
- **QUBO (`qubo_annealing`)** encodes each `x_i` as a binary expansion and
  minimizes a QUBO-structured energy on a classical simulator, followed by a
  deterministic classical repair. It is labelled `QUANTUM_INSPIRED` /
  `SIMULATOR`; see `docs/solver-interface.md`.

## Numerical details

- All solvers consume the same compiled `ProblemSpec`, so objective values and
  constraint checks are identical across backends.
- Feasibility tolerances are relative (`1e-6 · max(1, R)` for money amounts) to
  absorb CBC / floating-point slack without masking real violations.
- The stochastic solvers end with `repair_feasibility()`: project to the
  box-simplex (`Σx = R`, `0 ≤ x ≤ cap`) and deterministically fix any remaining
  constraint breach before the allocation is reported.