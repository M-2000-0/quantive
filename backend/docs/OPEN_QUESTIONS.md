# OPEN_QUESTIONS.md

Running log of every assumption made and every decision that needs human sign-off before production use.

## Resolved Items

### Data Infrastructure
- [x] **Data provider abstraction**: Built adapter pattern in `real_providers.py` — any source can be swapped via config change
- [x] **Day-count convention**: Implemented Actual/360, Actual/365, 30/360 in `day_count.py` — all existing interest calculations audited
- [x] **Fuzzy matching for ETL**: Implemented in `etl_pipeline.py` using `SequenceMatcher` — threshold needs tuning per dataset

### Simulation Engine
- [x] **NSS yield curve fitting**: Implemented in `engine.py` — verified with sparse data (11 points, avg residual < 1bp)
- [x] **Stochastic models**: Vasicek + CIR implemented — CIR guarantees non-negative rates
- [x] **Hull-White**: Curve-consistent model implemented — requires θ(t) calibration to real curve
- [x] **FX model**: GBM implemented with documented thin-tail limitation noted in methodology

### Optimization
- [x] **Solver choice**: scipy SLSQP — appropriate for smooth constrained problems, handles infeasible sets gracefully
- [x] **Buyback optimization**: Kyle's lambda market impact model — calibrated parameters need real market data

### Security
- [x] **PQC library**: oqs-python (Open Quantum Safe) — requires liboqs C library installation
- [x] **Key rotation policy**: 90-day default — configurable per deployment
- [x] **RBAC roles**: Government DMO hierarchy implemented (system_admin → public_view)

### Compliance
- [x] **Fiscal rules**: IMF-standard thresholds implemented — can be customized per country

### Documentation
- [x] **Methodology document**: Full formulas + limitations written in `METHODOLOGY.md`
- [x] **PQC methodology**: Plain-language document for auditors in `PQC_METHODOLOGY.md`

---

## Open Items — Requires Human Decision

### HIGH PRIORITY

1. **FRED API key**: Free registration at https://fred.stlouisfed.org/docs/api/api_key.html
   - Currently: interface ready but hardcoded key
   - Decision: Who registers? Where is the key stored?

2. **Bloomberg/Refinitiv access**: Institutional decision
   - Currently: abstraction layer ready, no live connection
   - Decision: Does the DMO have existing Bloomberg terminal access? Budget for API?

3. **Country prioritization**: Which countries for central bank connectors?
   - Currently: ECB + Treasury implemented, others are interfaces
   - Decision: Priority list? (Mexico? Brazil? Nigeria? Others?)

4. **Correlation matrix estimation approach**
   - Currently: hardcoded default correlations (rate-FX: -0.15, rate-growth: -0.30, FX-growth: 0.20)
   - Options:
     - (a) Rolling window from historical data (e.g., 5-year window)
     - (b) DCC-GARCH for time-varying correlations
     - (c) Regime-switching correlations (calm vs crisis)
   - Recommendation: Start with (a), upgrade later

5. **RBAC role structure**: Are the 6 roles (system_admin, minister, treasury_officer, analyst, auditor, public_view) correct for this DMO?
   - Does the DMO have additional roles like "Chief Economist" or "Risk Manager"?
   - Should "minister" role exist, or is approval delegated to senior treasury officers?

### MEDIUM PRIORITY

6. **HSM choice**: Cloud vs on-premise for key management
   - Cloud: AWS KMS, Azure Key Vault, GCP Cloud KMS — managed, audited, costs money
   - On-premise: HashiCorp Vault, Thales Luna — more control, more ops burden
   - For sovereign data, on-premise may be required by policy

7. **WCAG accessibility audit**: Full audit needed
   - Current: basic semantic HTML, ARIA labels not yet added
   - Recommendation: Manual audit + axe-core automated scan

8. **IMF export template validation**: Are current templates accurate?
   - MTDS/DSA formats based on published IMF specifications
   - Need: Validation against actual IMF template files

9. **Data retention policy**: How long is historical data retained?
   - Sovereign debt records are relevant for 20-30+ years
   - Options: (a) Forever, (b) 30 years, (c) Configurable per data type
   - GDPR/privacy implications for user data vs. fiscal data

10. **Multi-currency aggregation policy**: How to aggregate debt across currencies
    - Options: (a) Convert all to USD at spot, (b) Convert at historical rates, (c) Show both
    - Impact: FX volatility dramatically changes reported totals

### LOW PRIORITY

11. **Country-specific bond indices**: Which JP Morgan GBI-EM indices to track?
    - EM indices: Local Currency, Hard Currency, Diversified
    - Thresholds differ by index type

12. **Creditor litigation database**: Sources for vulture fund track records
    - Sovereign Debt Restructuring Database (IMF)
    - Academic databases (Sturzenegger & Zettelmeyer)
    - Court records ( PACER for US cases)

13. **Debt-for-nature swap data**: How current is the dataset?
    - Ecuador (2023), Belize (2021), Gabon (2024)
    - Need: Real-time tracking of new transactions

14. **Shadow ratings calibration**: Against which vintage of Moody's/S&P methodology?
    - Methodologies change every 2-3 years
    - Recommendation: Pin to most recent published version, flag date

15. **Simulation backtest period**: 2007-2010 is one crisis — need more
    - Suggest: Also test 1997-98 (Asian crisis), 2010-12 (Eurozone), 2020 (COVID)
    - Each tests different correlation assumptions

16. **Contingent liability data source**: Where to get guarantee registry?
    - Most DMOs publish annual guarantee reports
    - IMF Fiscal Transparency Code requires disclosure

17. **Multi-tenant isolation**: Is this single-DMO or multi-DMO?
    - Current: single-org model
    - If multi-tenant: need data isolation, cross-tenant access controls

---

## Assumptions Made (Flag for Review)

1. **GDP estimates**: Used $500B debt / $1000B GDP as default — needs real country data
2. **Discount rate**: 8% used for NPV calculations — may differ by country/instrument
3. **Exit yield**: 8% used for restructuring NPV — should reflect actual market conditions
4. **Correlation assumptions**: Based on academic literature, not estimated from country-specific data
5. **NSS fitting**: 6-parameter model — some markets may need fewer parameters
6. **CIR/Vasicek parameters**: Calibrated to US data — need re-calibration for each country
7. **Kyle's lambda**: Simplified market impact model — real calibration needs order book data
8. **Fiscal thresholds**: Based on EU Maastricht + IMF LIC-DSA — may differ by country
9. **RBAC permissions**: Assumed standard DMO org structure — may not match actual hierarchy
10. **Day-count conventions**: Assumed USD instruments use Actual/360 — may differ by instrument type

---

*Last updated: 2026-08-29*
