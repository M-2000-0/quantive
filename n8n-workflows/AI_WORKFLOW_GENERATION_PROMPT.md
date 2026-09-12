# n8n Workflow Generation Prompt: Quantive Platform & AI

## System Overview

**Quantive** is a sovereign debt management platform with a FastAPI backend and n8n for async automation. The n8n workflows are **supplementary** to native Python automations — they handle external data ingestion (market data, news, AI predictions) and report execution status back to the Quantive automation dashboard via HMAC-signed webhook.

---

## Database Schema (Canonical Source: `schemas/database-schema.sql`)

All n8n workflows **must** use PostgreSQL nodes (`n8n-nodes-base.postgres`) targeting these tables. **Do not use n8n dataTables.**

### Core Tables (n8n writes to these)

```sql
-- Market data time-series
market_data (
  id UUID PRIMARY KEY,
  symbol VARCHAR(50) NOT NULL,           -- e.g., '^TNX', 'GC=F', 'BTC-USD'
  name VARCHAR(255),                     -- Human-readable name
  value DECIMAL(18,8),                   -- Current price/value
  source VARCHAR(100),                   -- 'yahoo_finance', 'newsapi', etc.
  timestamp TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
)
INDEX idx_market_data_symbol ON market_data(symbol, timestamp DESC);

-- News articles with ticker extraction
news_articles (
  id UUID PRIMARY KEY,
  title VARCHAR(500) NOT NULL,
  description TEXT,
  url VARCHAR(1000) UNIQUE,
  source VARCHAR(255),
  published_at TIMESTAMPTZ,
  keywords JSONB DEFAULT '[]',           -- Store: {matched_tickers: [...], sentiment: 'positive|negative|neutral'}
  created_at TIMESTAMPTZ DEFAULT NOW()
)
INDEX idx_news_articles_url ON news_articles(url);

-- AI price predictions
ai_predictions (
  id UUID PRIMARY KEY,
  symbol VARCHAR(50) NOT NULL,
  prediction_type VARCHAR(100),          -- '1h', '24h', '7d'
  prediction JSONB,                      -- Full prediction object
  confidence DECIMAL(5,4),               -- 0.0 - 1.0
  model_version VARCHAR(50) DEFAULT 'gpt-4o-mini',
  actual_value DECIMAL(18,8),            -- Price at prediction time
  created_at TIMESTAMPTZ DEFAULT NOW()
)
INDEX idx_ai_predictions_symbol ON ai_predictions(symbol, created_at DESC);

-- System watchlist (n8n schema, not user watchlists)
watchlist_securities (
  id UUID PRIMARY KEY,
  symbol VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(255),
  target_value DECIMAL(18,8),
  alert_threshold DECIMAL(10,4) DEFAULT 0.05,  -- 5%
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
)

-- Backend health checks
api_health_checks (
  id UUID PRIMARY KEY,
  service VARCHAR(255) NOT NULL,
  status_code INTEGER,
  response_time_ms INTEGER,
  status VARCHAR(20) NOT NULL,           -- 'healthy' | 'unhealthy'
  checked_at TIMESTAMPTZ DEFAULT NOW()
)
```

### Read-Only Tables (Backend owns these; n8n only SELECTs)

- `watchlists` / `watchlist_items` — User-created watchlists (social.py models)
- `organizations`, `users`, `portfolios`, `debt_instruments` — Core app tables

---

## External APIs (Configured in n8n Credentials)

| Credential Name | Type | Purpose |
|-----------------|------|---------|
| `postgres-main` | PostgreSQL | Quantive DB (all writes) |
| `slack-main` | Slack OAuth2 | Alert channels |
| `openAiApi` | Header Auth (`Authorization: Bearer {{ $credentials.openAiApi }}`) | OpenAI GPT-4o-mini |
| `newsApiKey` | Query Auth (`apiKey={{ $credentials.newsApiKey }}`) | NewsAPI.org |

---

## Automation API Bridge (Required for All Workflows)

Every workflow **must** end with an HMAC-signed POST to the Quantive backend so runs appear in `/automation` dashboard.

### Bridge Pattern (Code Node → HTTP Request)

```javascript
// Code Node: "Bridge Sign"
const crypto = require('crypto');
const payload = {
  workflow: '<workflow-key>',        // e.g., 'market-data', 'news-ingestion'
  status: 'success',                  // or 'failed'
  duration_ms: $execution.timeToComplete || 0,
  summary: '<human-readable summary>',
  actions: []                         // Optional: array of action objects
};
const body = JSON.stringify(payload);
const secret = process.env.QUANTIVE_WEBHOOK_SECRET || '';
return [{ json: {
  body,
  signature: crypto.createHmac('sha256', secret).update(body).digest('hex')
}}];
```

```json
// HTTP Request Node: "Bridge Report Run"
{
  "url": "={{ $env.QUANTIVE_BASE_URL || 'http://host.docker.internal:8000' }}/api/automation/webhooks/external-run",
  "method": "POST",
  "jsonBody": "={{ $json.body }}",
  "headerParameters": {
    "parameters": [
      { "name": "x-quantive-signature", "value": "={{ $json.signature }}" },
      { "name": "Content-Type", "value": "application/json" }
    ]
  },
  "onError": "continueRegularOutput"
}
```

### Backend Endpoint (Already Implemented)

`POST /api/automation/webhooks/external-run` — Verifies HMAC, creates `AutomationRun` record with `automation_key = 'n8n:<workflow>'`.

---

## Required Workflow Tracks (6 Independent Crons)

### 1. Market Data Ingestion
- **Schedule**: `*/30 * * * *` (every 30 min)
- **Symbols**: `^TNX`, `DX-Y.NYB`, `GC=F`, `CL=F`, `^GSPC`, `^VIX`, `BTC-USD`, `ETH-USD`
- **Source**: Yahoo Finance `https://query1.finance.yahoo.com/v8/finance/chart/{{symbol}}?range=1d&interval=1h`
- **Parser**: Extract `chart.result[0].meta.regularMarketPrice`, `previousClose`, `regularMarketTime`
- **Write**: `INSERT INTO market_data (symbol, name, value, source, timestamp) VALUES (...) ON CONFLICT DO NOTHING`
- **Bridge**: `workflow: 'market-data'`

### 2. News Ingestion + Ticker Matching
- **Schedule**: `0 * * * *` (hourly)
- **Source**: NewsAPI `https://newsapi.org/v2/top-headlines?category=business&language=en&pageSize=30`
- **Ticker Extraction** (in Code node, `executeOnce: true`):
  - Exact: `$AAPL` → score 1.0
  - Bracket: `[NVDA]` → score 0.9
  - Fuzzy: Known company names (Apple, Microsoft, NVIDIA, Tesla, Google, Amazon, Meta, Bitcoin) → score 0.85
  - Max 5 matches per article
- **Sentiment**: Count positive/negative keywords → `positive|negative|neutral`
- **Write**: `INSERT INTO news_articles (title, description, url, source, published_at, keywords) VALUES (...) ON CONFLICT (url) DO NOTHING`
  - `keywords` = JSONB: `{matched_tickers: [...], sentiment: '...'}`
- **Bridge**: `workflow: 'news-ingestion'`

### 3. AI Daily Market Summary
- **Schedule**: `0 7 * * 1-5` (weekdays 7 AM UTC)
- **OpenAI Call**: `gpt-4o-mini`, system prompt: *"You are a sovereign-debt market analyst. Summarize today's market conditions in 5 bullet points, max 120 words."*
- **User prompt**: *"Rates, dollar, gold, oil, equities, VIX, crypto — what matters for treasury desks today?"*
- **Output**: Post to Slack `#market-news` with 📈 *Daily Market Summary* (AI)
- **Bridge**: `workflow: 'ai-market-summary'`

### 4. AI Price Predictions
- **Schedule**: `*/15 * * * *` (every 15 min)
- **Symbols**: From `watchlist_securities WHERE is_active = true`
- **For each symbol**:
  1. Fetch current price from Yahoo Finance
  2. Call OpenAI: *"You are a quant analyst. Predict 1h, 24h, 7d price for {{symbol}}. Current: {{price}}. Return JSON: {predictions: [{horizon, predicted_price, confidence}]}"*
  3. Filter `confidence >= 0.5`
  4. Write to `ai_predictions` with full prediction JSON in `prediction` column
- **Bridge**: `workflow: 'prediction-refresh'`

### 5. Watchlist Alerts (System Watchlist)
- **Schedule**: `*/5 * * * *` (every 5 min)
- **Read**: `watchlist_securities` (active) + latest `market_data` (last 2 hours)
- **Alert Logic**: If price deviates > `alert_threshold` (default 5%) from `target_value` or previous check
- **Cooldown**: 1 hour per symbol (track in workflow static data or separate table)
- **Output**: Slack `#watchlist-alerts`: `Watchlist alert: {{symbol}} ({{name}}) at {{price}}. Threshold: {{threshold}}`
- **Bridge**: `workflow: 'watchlist-refresh'`

### 6. Data Quality Monitor
- **Schedule**: `0 */6 * * *` (every 6 hours)
- **Check**: All 8 expected symbols have data in last 24h; none stale > 2 hours
- **Query**: `SELECT symbol, COUNT(*), MAX(timestamp) FROM market_data WHERE timestamp > NOW() - INTERVAL '24 hours' GROUP BY symbol`
- **Alert**: If missing/stale → Slack `#platform-alerts`: `⚠️ Data quality issue: Missing: [...]. Stale: [...]`
- **Bridge**: `workflow: 'data-quality-monitor'`

---

## n8n Node Conventions

| Pattern | Implementation |
|---------|----------------|
| **Postgres Write** | `operation: executeQuery`, parameterized with `{{ $json.field }}`, `ON CONFLICT DO NOTHING` |
| **Postgres Read** | `operation: executeQuery`, `SELECT ...` returning rows |
| **HTTP Request** | `onError: continueRegularOutput`, `retryOnFail: true`, `maxTries: 3`, `waitBetweenTries: 3000` |
| **Code Node** | `typeVersion: 2`, `executeOnce: true` for array→item transformations |
| **IF Node** | `typeVersion: 2.2`, boolean condition on `{{ $json.flag }}` |
| **Slack** | `typeVersion: 2.1`, channel from credentials, `onError: continueRegularOutput` |
| **Schedule** | `typeVersion: 1.2`, `cronExpression` field |

---

## Environment Variables (n8n)

```
QUANTIVE_BASE_URL=http://host.docker.internal:8000
QUANTIVE_WEBHOOK_SECRET=<shared-secret-matching-backend>
```

---

## Output Requirements

Generate a **single n8n workflow JSON** with:
1. All 6 cron tracks as independent branches
2. Proper node IDs (UUIDs) and connections
3. Credential references (not inline secrets)
4. Bridge pattern at end of each track
5. `executionOrder: v1`
6. Tags: `["platform", "ai", "market-data", "predictions", "watchlist", "news"]`
7. Description matching the functionality

**File name**: `05-platform-ai-enhanced.json`

---

## Validation Checklist

Before outputting, verify:
- [ ] No `n8n-nodes-base.dataTable` nodes
- [ ] All Postgres queries reference tables from schema above
- [ ] All 6 tracks have Bridge Sign + Bridge Report Run
- [ ] Slack nodes use correct channel names (`#market-news`, `#watchlist-alerts`, `#platform-alerts`)
- [ ] OpenAI calls use `gpt-4o-mini` with proper JSON response format
- [ ] Yahoo Finance URLs use correct symbol interpolation
- [ ] NewsAPI uses query auth credential
- [ ] Cron expressions match spec exactly
- [ ] JSON is valid and parseable