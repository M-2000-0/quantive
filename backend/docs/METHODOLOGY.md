# Quantive — Full Methodology Document
## For Non-Technical Auditors and Parliamentary Reviewers

**Version:** 1.0
**Date:** August 2026
**Classification:** Internal — Audit-Ready

---

## 1. What This System Does

Quantive is a sovereign debt management platform that helps government Debt Management Offices (DMOs) make better decisions about:

- **How much debt** to issue and in what currencies
- **When to issue** (timing, maturity selection)
- **How to manage existing debt** (refinancing, buybacks, restructuring)
- **What risks** the debt portfolio faces (interest rate, FX, refinancing)
- **Whether fiscal rules** are being met

---

## 2. Data Sources

### Free/Public Sources (Implemented)

| Source | Data | Update Frequency | URL |
|--------|------|-----------------|-----|
| US Treasury | USD yield curves, interest rates | Daily | api.fiscaldata.treasury.gov |
| ECB | EUR reference rates, EUR yield curves | Daily | data-api.ecb.europa.eu |
| IMF IFS | Inflation, macro indicators | Quarterly | imf.org/external/datamapi |
| IMF WEO | GDP, debt-to-GDP, fiscal balances | Annual | imf.org/external/datamapi |
| World Bank | Development indicators, debt stats | Annual | api.worldbank.org |
| FRED | Historical US economic series | Daily | api.stlouisfed.org (requires free key) |

### Paid Sources (Interface Ready, Not Connected)

| Source | Data | Cost | Status |
|--------|------|------|--------|
| Bloomberg | Real-time bond pricing, all markets | $$$$ | Interface ready |
| Refinitiv (LSEG) | Bond pricing, macro data | $$$$ | Interface ready |
| ICE Data | EM sovereign bond pricing | $$$ | Interface ready |
| Trading Economics | Mid-tier macro/yield data | $$ | Interface ready |

**Architecture note:** The data layer uses an adapter pattern. Swapping Bloomberg in for Treasury.gov is a configuration change, not a rewrite.

---

## 3. Yield Curve Construction

### Nelson-Siegel-Svensson (NSS) Model

For building yield curves from sparse bond market data:

```
r(t) = β₀ + β₁·(1-e^(-t/τ₁))/(t/τ₁)
      + β₂·((1-e^(-t/τ₁))/(t/τ₁) - e^(-t/τ₁))
      + β₃·((1-e^(-t/τ₂))/(t/τ₂) - e^(-t/τ₂))
```

**Parameters:**
- β₀: Long-term rate level
- β₁: Short-term slope (typically negative)
- β₂: Medium-term curvature
- β₃: Second curvature term
- τ₁, τ₂: Decay parameters controlling where curvature peaks

**Fitting method:** Nelder-Mead simplex optimization (minimizes sum of squared residuals between model and observed yields).

**Why NSS?** Linear interpolation between observed points creates unrealistic curves that can produce negative rates or sharp kinks. NSS produces smooth, economically sensible curves that behave well between and beyond observed maturities.

**Reference:** Svensson, L.E.O. (1994), "Estimating and Interpreting Forward Interest Rates," IMF Working Paper.

---

## 4. Stochastic Rate Models

### Vasicek Model

```
dr = κ(θ - r)dt + σdW
```

- **κ (kappa):** Mean-reversion speed (how fast rates return to long-term mean)
- **θ (theta):** Long-term mean rate
- **σ (sigma):** Volatility of rate changes
- **dW:** Random shock (Wiener process increment)

**Properties:** Mean-reverting, can produce negative rates, analytically tractable.

**Calibration:** Default parameters (κ=0.15, θ=4%, σ=1%) calibrated from US Treasury data. Country-specific calibration uses maximum likelihood estimation on historical rate data.

### Cox-Ingersoll-Ross (CIR) Model

```
dr = κ(θ - r)dt + σ√r·dW
```

Same as Vasicek but with √r term ensuring rates stay non-negative. Uses full truncation discretization scheme for numerical stability.

### Hull-White Model

```
dr = [θ(t) - a·r]dt + σdW
```

Unlike Vasicek (constant θ), Hull-White uses time-dependent θ(t) calibrated to fit today's yield curve exactly. This means:
- The model reproduces today's observed prices exactly
- Stochastic variation captures future uncertainty
- More realistic for debt management than Vasicek

**Calibration:** θ(t) computed from observed forward rates: θ(t) = ∂f(0,t)/∂t + a·f(0,t) + σ²/(2a)·(1-e^(-2at))

---

## 5. Monte Carlo Simulation

### Correlated Multi-Factor Simulation

Rates, FX, and GDP growth are not independent. The simulation uses:

1. **Cholesky decomposition** of the correlation matrix to generate correlated random draws
2. **Each factor** follows its own stochastic model (Vasicek/CIR for rates, GBM for FX, mean-reverting for growth)
3. **Correlation structure** ensures that when rates spike, FX depreciates and growth slows (as happens in real crises)

**Default correlations (US calibration):**
- Rate-FX: -0.15 (rate hikes → currency strengthens)
- Rate-Growth: -0.30 (rate hikes → growth slows)
- FX-Growth: 0.20 (currency depreciation → export competitiveness)

### Fan Charts

Output as percentile bands (5th, 10th, 25th, 50th, 75th, 90th, 95th) — the same format used by the IMF and central banks for communicating forecast uncertainty.

---

## 6. Optimization

### Problem Formulation

**Minimize:** Expected portfolio cost (weighted average of instrument costs)

**Subject to:**
- Refinancing risk ≤ X% (instruments maturing within N years)
- FX exposure ≤ Y% (foreign-currency denominated)
- Single instrument ≤ Z% (concentration limit)
- Duration within [min, max] range

**Solver:** scipy.optimize.minimize with SLSQP (Sequential Least Squares Programming) — handles nonlinear constraints, suitable for debt portfolio problems.

**When constraints are infeasible:** The system returns a diagnostic report explaining which constraint is the bottleneck and suggesting relaxations.

---

## 7. Fiscal Rule Compliance

The system monitors compliance with fiscal rules at both national and subnational levels:

- **Debt-to-GDP ceiling** (Maastricht: 60%, but varies by country)
- **Deficit-to-GDP ceiling** (Maastricht: 3%)
- **Debt service-to-revenue ratio** (common subnational limit: 25%)
- **Debt-to-budget ratio** (subnational: 50%)

**Alerting:** Entities approaching 90% of any limit generate warnings. Breaches generate critical alerts.

---

## 8. Post-Quantum Encryption

**Why it matters:** Sovereign debt records have 30+ year sensitivity. "Harvest now, decrypt later" attacks capture encrypted data today for future quantum decryption.

**What we implemented:** Hybrid encryption combining:
- Classical: ECDH P-256 (proven, battle-tested)
- Post-quantum: ML-KEM-768 (NIST FIPS 203 standardized)
- Symmetric: AES-256-GCM (quantum-resistant)

**Standards:** NIST FIPS 203 (ML-KEM), NIST FIPS 204 (ML-DSA), NIST SP 800-38D (AES-GCM).

---

## 9. What This Does NOT Do

- **Does not make decisions.** It provides analysis and optimization to support human decision-making.
- **Does not replace legal counsel.** CAC/pari passu clause analysis is informational, not legal advice.
- **Does not guarantee accuracy.** Models have limitations documented in OPEN_QUESTIONS.md.
- **Does not protect against insider threats.** Encryption protects data at rest, not access by authorized users.
- **Does not predict the future.** Simulations show possible ranges, not certainties.

---

## 10. Model Limitations (Honest Assessment)

1. **FX model (GBM) assumes thin tails.** Real FX has fat tails. Jump-diffusion would be more realistic but adds complexity.
2. **Correlation estimates are backward-looking.** Correlations change during crises (correlation increases). Using historical correlations may underestimate tail risk.
3. **NSS fitting on sparse data is uncertain.** With fewer than 5 data points, the model is underdetermined.
4. **Optimizer assumes known cost parameters.** In practice, issue costs depend on market conditions at time of issuance.
5. **Fiscal rules vary enormously by country.** Default rules are based on IMF common practices, not specific legislation.

---

*This document is suitable for review by non-technical stakeholders, ministry officials, and external auditors.*
