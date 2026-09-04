# Automated Stock Discovery & Screening System
## Architecture, Pipeline & Algorithmic Blueprint

**Author:** Quantive Engineering  
**Version:** 1.0  
**Status:** Draft for architecture review

---

## 1. System Architecture & Data Pipeline Blueprint

### End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES (Layer 0)                       │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────┤
│ SEC      │ Financial│ Open     │ Polygon  │ Yahoo   │ FRED         │
│ EDGAR    │ Modeling │ Insider  │ .io      │ Finance │ (Macro)      │
│ API      │ Prep API │ Scraper  │ API      │ Scraper │              │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬────┴──────┬───────┘
     │          │          │          │          │           │
     ▼          ▼          ▼          ▼          ▼           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     ETL PIPELINE (Layer 1)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Extract  │→ │Transform │→ │  Clean   │→ │  Load    │           │
│  │ (fetch)  │  │ (normalize│  │ (validate│  │ (store)  │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                                                                     │
│  Schedule: Daily at 6:00 AM ET (post-market close + 2hr)          │
│  Storage: PostgreSQL (structured) + S3 (raw filings)               │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                FILTERING ENGINE (Layer 2)                           │
│                                                                     │
│  Layer A: Micro-Cap Baseline Filter                                │
│    → Market cap $50M–$500M                                         │
│    → Float < 25M shares                                            │
│    → Avg daily volume > 50,000 shares                              │
│    → Analyst coverage: 0-1                                         │
│                                                                     │
│  Layer B: Fundamental Quality Filter                               │
│    → ROIC > 15%                                                    │
│    → FCF Yield > 8%                                                │
│    → Debt/Equity < 1.0                                             │
│    → Cash runway > 18 months                                       │
│    → Revenue growth > 0% (trailing 3Y CAGR)                       │
│                                                                     │
│  Layer C: Insider Alignment Filter                                 │
│    → Insider ownership > 20%                                       │
│    → Cluster buying detected (3+ buys in 60 days)                  │
│    → No insider selling in last 90 days                            │
│                                                                     │
│  Expected pipeline output: 50-200 candidates from ~8,000 universe  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              SCORING ALGORITHM (Layer 3)                            │
│                                                                     │
│  Inputs: Filtered candidates from Layer 2                          │
│  Process: Weighted scoring matrix (0-100)                          │
│  Output: Ranked watchlist with conviction scores                   │
│                                                                     │
│  Scoring factors:                                                  │
│    → Fundamental Quality (30%)                                     │
│    → Catalyst Strength (25%)                                       │
│    → Insider Alignment (20%)                                       │
│    → Visibility Discount (15%)                                     │
│    → Risk Penalty (10%)                                            │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              NLP CATALYST ENGINE (Layer 4)                          │
│                                                                     │
│  Scans: 10-K, 10-Q, 8-K, Form 4, press releases                  │
│  Detects: Contract wins, FDA approvals, patents, spin-offs,        │
│           uplisting signals, M&A targets                           │
│  Output: Catalyst score per candidate (0-100)                      │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│              OUTPUT LAYER (Layer 5)                                 │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  Dashboard   │  │  Alert API   │  │  PDF Report  │             │
│  │  (React UI)  │  │  (Webhook)   │  │  (Daily)     │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                     │
│  Deliverables:                                                     │
│    → Daily top-10 watchlist                                        │
│    → Weekly sector heat map                                       │
│    → Real-time insider cluster alerts                              │
│    → Catalyst detection notifications                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Required Data Sources & APIs

| Source | Purpose | Frequency | Cost |
|--------|---------|-----------|------|
| SEC EDGAR API | 10-K, 10-Q, 8-K, Form 4 filings | Daily | Free |
| Financial Modeling Prep | Fundamentals, ratios, analyst estimates | Daily | $29/mo |
| Polygon.io | Price, volume, market cap, float | Daily | $29/mo |
| OpenInsider | Insider transaction data | Daily | Free |
| Yahoo Finance | Supplementary price data, dividends | Daily | Free |
| FRED | Macro indicators (rates, GDP, CPI) | Weekly | Free |
| OTC Markets | OTCQX/OTCMKTS data | Daily | Free |
| MSRB (EMMA) | Municipal bond data (if needed) | Daily | Free |

### Database Schema (Core Tables)

```sql
-- Raw universe
CREATE TABLE stock_universe (
    ticker VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(255),
    exchange VARCHAR(50),
    market_cap DECIMAL(18,2),
    float_shares DECIMAL(18,0),
    avg_daily_volume DECIMAL(18,0),
    sector VARCHAR(100),
    industry VARCHAR(100),
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Fundamental metrics (point-in-time)
CREATE TABLE fundamental_metrics (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10),
    report_date DATE,
    roic DECIMAL(8,4),
    fcf_yield DECIMAL(8,4),
    debt_equity DECIMAL(8,4),
    cash_runway_months INTEGER,
    revenue_cagr_3y DECIMAL(8,4),
    gross_margin DECIMAL(8,4),
    operating_margin DECIMAL(8,4),
    insider_ownership_pct DECIMAL(8,4),
    analyst_count INTEGER,
    UNIQUE(ticker, report_date)
);

-- Insider transactions
CREATE TABLE insider_transactions (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10),
    filing_date DATE,
    transaction_date DATE,
    insider_name VARCHAR(255),
    title VARCHAR(100),
    transaction_type VARCHAR(20), -- BUY/SELL
    shares DECIMAL(18,0),
    price_per_share DECIMAL(10,4),
    total_value DECIMAL(18,2),
    UNIQUE(ticker, insider_name, transaction_date, shares)
);

-- Detected catalysts
CREATE TABLE detected_catalysts (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10),
    detection_date DATE,
 
