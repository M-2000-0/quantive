"""Expand SovereignGPT knowledge base with more comprehensive domain knowledge.

Run: python scripts/expand_knowledge_base.py
"""

import sys
sys.path.insert(0, r'C:\Users\HP\OneDrive\Desktop\Quantive\backend')

from app.ai.rag_pipeline import ingest_document
from app.ai.vector_store import get_count, list_sources

KNOWLEDGE_DOCUMENTS = [
    # ── IMF & World Bank ──────────────────────────────────────────
    ("imf_programs", """The IMF provides financial assistance through various lending facilities:
Stand-By Arrangements (SBA) for short-term balance of payments problems,
Extended Fund Facility (EFF) for medium-term structural issues,
Flexible Credit Line (FCL) for countries with strong fundamentals,
Precautionary and Liquidity Line (PLL) for moderate vulnerabilities,
and Rapid Financing Instrument (RI) for emergency needs. Conditionality
varies by facility, with FCL having ex-ante qualification rather than
traditional conditionality. IMF lending involves quota-based access limits,
phased disbursements tied to program reviews, and catalytic effects on
private capital flows."""),

    ("world_bank_role", """The World Bank Group supports debt management through:
International Bank for Reconstruction and Development (IBRD) provides loans
to middle-income countries at near-market rates. International Development
Association (IDA) provides concessional loans and grants to the poorest
countries. The World Bank's Debt Management Performance Assessment (DeMPA)
tool evaluates debt management practices across 15 performance areas.
Technical assistance includes debt recording systems, cash flow forecasting,
and medium-term debt management strategies. The World Bank also publishes
the International Debt Statistics database with comprehensive debt data."""),

    ("dsf_methodology", """The IMF Debt Sustainability Framework uses two main tools:
The Debt Sustainability Analysis (DSA) for low-income countries uses
probabilistic debt projections with Monte Carlo simulations, assessing
sustainability as sustainable, sustainable with high risk, or in debt distress.
The Market-Assisted DSA for market-access countries incorporates market-based
indicators like credit default swap spreads, bond yields, and EMBI spreads.
Both frameworks use stress tests with adverse scenarios including GDP shocks,
interest rate spikes, exchange rate depreciations, and primary balance
deterioration. Threshold indicators include debt-to-GDP, debt service
ratios, and gross financing needs."""),

    # ── Bond Mathematics ──────────────────────────────────────────
    ("bond_math_advanced", """Advanced bond mathematics includes:
Modified Duration = Macaulay Duration / (1 + yield/m), where m is coupon frequency.
Effective Duration accounts for embedded options by measuring price sensitivity
to parallel yield shifts. Key Rate Duration measures sensitivity to non-parallel
shifts at specific maturity points. Convexity Adjustment = 0.5 * convexity * (yield change)^2.
The Fisher-Weil duration uses actual zero coupon rates for more accurate duration.
Price Value of a Basis Point (PVBP) = Duration * Price * 0.0001.
The yield to call considers the earliest call date and call price.
The yield to worst is the minimum of yield to maturity and all yield to call values."""),

    ("duration_matching", """Duration matching strategies for debt portfolios:
Cash flow matching pairs specific bonds with specific liabilities.
Duration matching ensures portfolio duration equals liability duration.
Immunization protects against parallel yield curve shifts.
Horizon matching combines duration matching for near-term with cash flow
matching for distant liabilities. Multi-period immunization extends
single-period immunization across multiple liability dates.
Contingent immunization allows active management as long as a surplus
exists above the minimum required. The key rate duration approach
addresses non-parallel yield curve shifts by matching sensitivities
at specific maturity points."""),

    ("swap定价", """Interest rate swap valuation:
A swap's value equals the difference between the present value of fixed
and floating legs. The fixed leg is valued as a bond. The floating leg
is valued using forward rates derived from the yield curve. At initiation,
a par swap has zero value. During its life, the swap value depends on
changes in the swap rate. The swap spread reflects credit risk and
liquidity premiums. Cross-currency swaps involve exchange of principal
and interest in different currencies. The basis swap spread reflects
funding cost differentials between currencies. Swaps are priced using
the OIS discounting framework for post-2008 valuations."""),

    # ── Credit Analysis ───────────────────────────────────────────
    ("credit_scoring", """Sovereign credit scoring methodology:
Quantitative factors include debt-to-GDP ratio (threshold: 60% for EU),
debt service-to-revenue ratio (threshold: 25%), foreign currency share
of debt (threshold: 30%), and international reserves import cover
(threshold: 3 months). Qualitative factors include institutional quality,
political stability, policy credibility, and market access. The IMF's
sovereign stress test framework uses five-year cumulative default
probabilities derived from CDS spreads. Credit migration analysis
tracks rating transitions across categories. Recovery rate assumptions
for sovereign defaults range from 30% to 70% depending on the
restructuring mechanism and creditor coordination."""),

    ("spreads_analysis", """Sovereign spread decomposition:
The total sovereign spread = credit spread + liquidity spread +
term premium + country risk premium. Credit spread reflects default
probability and loss given default. Liquidity spread compensates for
trading costs and market depth. Term premium increases with maturity.
Country risk premium includes political risk, institutional quality,
and macroeconomic stability. EMBI spread components: UST spread,
local currency spread, and individual bond spread. The spread dynamics
reflect global risk appetite, commodity prices, and domestic reforms.
Mean reversion in spreads suggests temporary dislocations versus
permanent deterioration."""),

    ("restructuring_mechanics", """Sovereign debt restructuring mechanics:
The Common Framework for Debt Treatments (G20) provides a platform for
bilateral debt treatment. The Paris Club restructuring typically involves
comparable treatment among creditors, new money provisions, and exit
concepts. Brady Bond-style restructuring converts bank loans to bonds
with collateral. Collective Action Clauses (CACs) in bond contracts
allow majority restructuring to bind all holders. The aggregated CAC
mechanism (post-2014) allows cross-series modification. Holdout risk
is managed through pari passu clauses and jurisdiction selection.
The IMF's Lending Into Arrears policy allows lending even when a
country is in default to private creditors."""),

    # ── Market Microstructure ─────────────────────────────────────
    ("trading_mechanics", """Sovereign bond market microstructure:
Primary market: Treasury auctions use single-price (Dutch) or
multiple-price formats. The bid-to-cover ratio indicates demand strength.
The when-issued market provides price discovery before settlement.
Secondary market: OTC trading through dealer networks with bid-ask
spreads reflecting credit quality and liquidity. The repo market
provides funding for bond positions. Government securities lending
facilitates short selling. The yield curve is constructed from
on-the-run Treasury securities using interpolation. The Treasury
yield curve drives pricing for all fixed income securities globally."""),

    ("liquidity_analysis", """Bond market liquidity metrics:
Bid-ask spread: 1-2 bps for on-the-run Treasuries, 5-10 bps for
off-the-run, 20-50 bps for EM sovereigns. Trading volume: daily
volume in US Treasuries exceeds $500 billion. The Amihud illiquidity
ratio measures price impact per unit of trading. Market depth shows
the volume available at best bid and offer. Price impact measures
how much prices move for a given trade size. Liquidity premium
compensates investors for holding less liquid securities. The
liquidity-adjusted VaR accounts for the cost of unwinding positions
under stress. The Liquidity Coverage Ratio (LCR) requires banks
to hold sufficient liquid assets."""),

    # ── Risk Management ───────────────────────────────────────────
    ("var_methodologies", """Value-at-Risk methodologies for sovereign debt:
Historical VaR uses actual return distributions. Parametric VaR
assumes normal distribution with mean and variance. Monte Carlo VaR
simulates thousands of scenarios. Conditional VaR (Expected Shortfall)
measures average loss beyond VaR. The variance-covariance method
uses factor models to decompose risk. Component VaR shows individual
risk contributions. Marginal VaR measures the effect of adding one
more unit of exposure. Incremental VaR measures the effect of adding
a new position. Stress VaR uses extreme historical scenarios.
The FRTB (Fundamental Review of the Trading Book) requires
expected shortfall-based capital charges."""),

    ("stress_testing", """Stress testing frameworks for sovereign debt:
The IMF's Financial Sector Assessment Program (FSAP) conducts
macro-financial stress tests. The EBA runs EU-wide stress tests
with adverse scenarios. The Fed's CCAR/DFAST tests US bank capital.
Scenario design includes GDP contraction, unemployment spike,
interest rate shock, and exchange rate depreciation. Sensitivity
analysis varies one factor at a time. Reverse stress testing
identifies scenarios that cause failure. Contagion analysis
captures cross-border spillovers. The stress test results inform
capital planning, dividend policies, and risk appetite."""),

    ("counterparty_credit", """Counterparty credit risk in sovereign derivatives:
CVA (Credit Valuation Adjustment) accounts for counterparty default
risk. DVA (Debit Valuation Adjustment) reflects the entity's own
credit risk. FVA (Funding Valuation Adjustment) captures the cost
of funding uncollateralized positions. The wrong-way risk occurs
when exposure increases as counterparty credit quality deteriorates.
The right-way risk occurs when exposure decreases as counterparty
credit quality deteriorates. Netting agreements reduce exposure
by offsetting positive and negative mark-to-market values.
Collateral management through CSA (Credit Support Annex) agreements
requires daily margin calls. The ISDA Master Agreement governs
OTC derivatives documentation."""),

    # ── AI in Finance ─────────────────────────────────────────────
    ("ml_debt_management", """Machine learning applications in debt management:
Gradient boosting models predict sovereign credit rating changes.
Random forests classify debt restructuring probability. LSTM networks
forecast yield curves and term structure dynamics. Transformer models
analyze central bank communications for policy signals. Reinforcement
learning optimizes debt issuance timing and maturity selection.
Natural language processing extracts policy signals from central bank
minutes, IMF reports, and credit agency publications. Graph neural
networks model contagion risk in sovereign bond networks. Federated
learning enables cross-border model training without data sharing.
Explainable AI (XAI) provides transparency for regulatory compliance."""),

    ("nlp_finance", """NLP applications in sovereign debt analysis:
Sentiment analysis of central bank minutes predicts policy changes.
Topic modeling identifies emerging themes in fiscal policy documents.
Named entity recognition extracts country names, institutions, and
economic indicators from news articles. Text classification categorizes
IMF Article IV reports by risk level. Summarization generates executive
summaries of lengthy fiscal reports. Question answering systems provide
instant access to debt management guidelines. Document similarity
identifies comparable restructuring precedents. The GDELT project
provides real-time global event data for sovereign risk monitoring."""),

    # ── Fiscal Policy ─────────────────────────────────────────────
    ("fiscal_frameworks", """Fiscal policy frameworks and rules:
The EU's Stability and Growth Pact requires deficit below 3% of GDP
and debt below 60% of GDP. The Fiscal Compact adds the structural
balance rule with automatic correction mechanisms. The US Budget
Control Act of 2011 set spending caps and sequestration triggers.
The Swiss debt brake limits structural deficits to 0.35% of GDP.
Germany's constitutional debt brake limits the structural federal
deficit to 0.35% of GDP. The IMF's fiscal monitors assess fiscal
sustainability across 190 member countries. Medium-term fiscal
frameworks (MTFFs) link annual budgets to long-term sustainability.
Fiscal responsibility laws establish numerical targets and
enforcement mechanisms."""),

    ("debt_statistics", """Key debt statistics and thresholds:
Maastricht criteria: 60% debt-to-GDP, 3% deficit-to-GDP.
IMF thresholds: 85% debt-to-GDP for emerging markets.
The JP Morgan EMBI Global tracks EM sovereign bond performance.
The Bloomberg Barclays Global Aggregate covers investment grade bonds.
US Treasury market: $27 trillion outstanding, $500 billion daily volume.
Global sovereign debt: $56 trillion (2024).
The average matured debt maturity: 6.5 years (US), 7.2 years (UK),
5.8 years (Japan), 4.2 years (Brazil), 3.1 years (Argentina).
Gross financing needs above 20% of GDP signal elevated rollover risk.
The interest rate-growth differential (r-g) is the key driver of
debt dynamics over the medium term."""),

    # ── Central Banking ───────────────────────────────────────────
    ("monetary_policy", """Monetary policy transmission to sovereign debt:
The policy rate influences short-term rates directly. The yield curve
responds to expectations of future policy rates. Quantitative easing
compresses term premia through large-scale asset purchases.
Forward guidance shapes expectations about the rate path. The balance
sheet reduction (quantitative tightening) affects long-term rates.
The interest rate corridor (floor vs ceiling system) determines
money market conditions. The Taylor rule provides a benchmark for
policy rate decisions. The neutral rate (r-star) represents the
equilibrium real interest rate. The effective lower bound constrains
conventional monetary policy, necessitating unconventional tools."""),

    ("fx_reserves", """Foreign exchange reserve management:
The IMF's Adequacy of Reserves framework uses:
Import cover (minimum 3 months of imports).
Short-term debt cover (100% of debt maturing within one year).
Money supply cover (10-20% of broad money).
The Guidotti-Greenspan rule suggests reserves should cover
one year of external debt maturing. Reserve composition includes
US dollars (59%), euros (20%), yen (5%, Chinese renminbi (2.5%),
and gold (15% of total reserves). The cost of holding reserves
includes the opportunity cost of not investing in domestic assets.
The benefit includes crisis prevention and exchange rate management.
The Chiang Mai Initiative provides regional financial safety nets
in Asia."""),

    # ── Emerging Markets ──────────────────────────────────────────
    ("em_debt_dynamics", """Emerging market debt dynamics:
Local currency bond markets have grown from $2 trillion (2000)
to $30 trillion (2024). The EMBI Global tracks 70+ EM sovereigns.
Key risks include: currency mismatch (original sin), rollover risk,
commodity dependence, and political instability. The carry trade
exploits interest rate differentials between EM and DM currencies.
Capital flow volatility creates sudden stop risks. The Federal Reserve's
taper tantrum (2013) demonstrated spillover effects from DM monetary
policy to EM debt markets. The COVID-19 pandemic triggered the largest
EM capital outflows in history, followed by unprecedented central bank
interventions and IMF emergency lending."""),

    ("chinese_bonds", """Chinese sovereign bond market:
China is the world's second-largest bond market with $18 trillion outstanding.
The People's Bank of China manages monetary policy through the Loan Prime
Rate (LPR) and Medium-term Lending Facility (MLF). The yuan's inclusion
in the SDR basket (2016) increased foreign participation. The Bond Connect
program allows offshore investors to access China's interbank bond market.
The Panda Bond market has grown significantly for foreign issuers.
Key risks include: capital controls, regulatory uncertainty, and
geopolitical tensions. The credit spread between Chinese and US
Treasuries reflects growth differentials and risk premiums."""),
]


def main():
    print("=" * 60)
    print("EXPANDING SOVEREIGNGPT KNOWLEDGE BASE")
    print("=" * 60)

    initial_count = get_count()
    print(f"Initial knowledge base: {initial_count} chunks")

    total_chunks = 0
    for source, text in KNOWLEDGE_DOCUMENTS:
        count = ingest_document(text, source, doc_type="knowledge")
        total_chunks += count
        print(f"  {source}: +{count} chunks")

    final_count = get_count()
    print()
    print(f"Added {total_chunks} new chunks")
    print(f"Final knowledge base: {final_count} chunks")

    sources = list_sources()
    print(f"Total sources: {len(sources)}")
    for s in sources:
        print(f"  {s['source']}: {s['count']} chunks ({s['type']})")


if __name__ == "__main__":
    main()
