# Scenario Engine

`quantive/scenarios/engine.py` turns a `ScenarioConfiguration` into the list of
`EconomicScenario` objects every solver consumes.

## Scenario configuration

`ScenarioConfiguration` fields:

- `include_named` — which named scenarios to include (see below). Default: all.
- `monte_carlo_count` — number of simulated scenarios. Default: `0` (named only).
- `monte_carlo_seed` — seed for the simulation.
- `interest_rate_shock_sigma`, `fx_shock_sigma`, `credit_spread_shock_sigma`,
  `liquidity_shock_sigma` — volatilities of the Gaussian shocks.
- `correlation_fx_ir` — correlation between FX and interest-rate shocks.

## Named scenarios

Defined in `quantive/scenarios/definitions.py` (default probabilities shown):

| Scenario | id | Probability | IR shock | FX | Liquidity |
|---|---|---|---|---|---|
| Base Case | `base` | 0.40 | — | — | 1.00 |
| High Interest Rates | `high_interest` | 0.15 | +200 bp | up | 0.80 |
| Low Interest Rates | `low_interest` | 0.10 | −150 bp | down | 0.95 |
| High Inflation | `high_inflation` | 0.10 | +100 bp | moderate up | 0.85 |
| FX Shock | `fx_shock` | 0.10 | +50 bp | strong up (BRL +25%) | 0.75 |
| Liquidity Shock | `liquidity_shock` | 0.15 | +100 bp | moderate up | 0.30 |

Each scenario sets `interest_rate_shock`, `inflation_shock`, `fx_shocks`
(a per-currency multiplier, `>1` = appreciation), `liquidity_conditions`, and a
`probability`. The engine normalizes probabilities so they sum to 1.
`named_scenarios(ids=None)` returns all six; passing a list of ids filters them.

## Monte Carlo scenarios

When `monte_carlo_count > 0`, the engine appends simulated scenarios drawn from
correlated Gaussian shocks:

```
z_fx  ~ N(0, σ_fx²)
z_ir  = ρ·z_fx + sqrt(1−ρ²)·z_fx_indep      (correlated with z_fx)
z_cr  ~ N(0, σ_cr²)
z_liq ~ N(0, σ_liq²)
```

Shocks are applied consistently across all instruments:

- **Interest rates**: base rate path shifts by `z_ir`.
- **FX**: the level of every foreign currency moves by `z_fx`, expressed so that
  `FX > 1` = foreign currency appreciated = costlier for the reporting-currency
  borrower.
- **Credit spreads**: issuer spreads widen by `z_cr`.
- **Liquidity**: `liquidity_conditions` scales the amount of liquid capacity
  available for rollover.

Every draw is seeded, so `ScenarioEngine(seed).materialize(config)` is
reproducible across runs.

## Cost model

Financing cost of instrument `i` in scenario `s` is assembled in
`ProblemSpec.cost_matrix` during `build_spec`:

```
C[i, s] = (coupon_i + rate_shock_s · rate_beta_i + spread_shock_s + spread_i)
           · fx_level_s
```

- `rate_beta_i` is higher for floating-rate instruments (full pass-through) and
  lower for fixed-rate instruments (only new issuance is priced at the new
  level);
- `fx_level_s` converts foreign-currency costs into reporting currency and is
  `1.0` for instruments issued in the reporting currency.

The vectorized implementation lives in `quantive/objectives/costs.py` and
computes `C` for all instruments and all scenarios in one pass.