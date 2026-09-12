# Quantive — Automation Reference

> Sovereign debt optimization platform. Python/FastAPI + PostgreSQL + n8n + Stripe + Docker.

---

## PLATFORM

Quantive optimizes sovereign debt portfolios using PuLP solvers, Monte Carlo stress testing (10K paths), real-time market data (Yahoo Finance, FRED), and AI policy briefings. Multi-layer risk management covers Cyber, Fiscal, Climate, Infrastructure, Geopolitical, Supply Chain with a 12-indicator early warning system.

**Stack**: Python 3.11, FastAPI, PostgreSQL 16, Redis 7, React+Vite, n8n, Stripe, Docker Compose
**Auth**: Bearer JWT | **DB**: `postgresql://quantive:pass@localhost:5432/quantive` | **Timezone**: America/Mexico_City

---

## API ENDPOINTS (Base: http://localhost:8000, Auth: Bearer JWT)

### Portfolios
- `POST /portfolios` — Create (synthetic or uploaded). Body: `{synthetic:true, seed:42, name:"..."}` or `{synthetic:false, name:"...", instruments:[...]}`
- `GET /portfolios` — List all
- `GET /portfolios/{id}` — Get by ID

### Optimization
- `POST /optimization` — Create problem. Body: `{portfolio_id, financing_requirement, profile:"BEST_OVERALL"}`
- `GET /optimization` — List all | `GET /{id}` — Details
- `POST /{id}/run` — Run async (returns job_id) | `POST /{id}/run/{job_id}/cancel` — Cancel
- `GET /{id}/results` — Results | `GET /{id}/strategies` — Strategies | `GET /{id}/benchmark` — Benchmark
- `GET /{id}/stress` — Stress tests | `GET /{id}/scenarios` — Scenarios
- `GET /jobs/{job_id}` — Job status

### Risk (6 categories: cyber, fiscal, climate, infrastructure, geopolitical, supply-chain)
- `POST /risk/{category}` — Create | `GET /risk/{category}` — List | `GET /risk/{category}/summary` — Dashboard
- `GET /risk/aggregate/{entity_id}` — Aggregate all | `GET /risk/early-warning/{entity_id}` — Early warning integration

### Early Warning (12 indicators)
- `GET /early-warning/signals/{entity_id}?horizon_months=12` — Signals
- `POST /early-warning/detect/{entity_id}` — Trigger detection
- `GET /early-warning/indicators` — Indicator configs | `GET /early-warning/categories` — Categories
- `POST /early-warning/scenarios/project` — Project scenarios

Indicators: debt_to_gdp (60/80), debt_service (25/35), external_financing_needs (15/25), liquidity_coverage (15/10), foreign_reserve_coverage (1.5/1.0), cds_spread (250/500bps), external_debt_ratio (40/60), primary_balance (-3/-5), tax_revenue_volatility (0.15/0.25), revenue_volatility (0.10/0.20), tax_base_contraction (-5/-10), pension_funding_ratio (80/60), pension_demographic_ratio (0.25/0.35)

### Procurement
- `POST /procurement` — Create | `GET /procurement` — List | `GET /{id}` — Details
- `POST /{id}/waste` — Waste detection | `GET /{id}/waste/summary` — Summary
- `POST /{id}/bottlenecks` — Bottlenecks | `GET /{id}/bottlenecks/summary` — Summary
- `POST /{id}/benchmarks` — Vendor benchmarks | `POST /{id}/forecast` — Forecast
- `POST /{id}/integrate` — Integrate with optimization | `GET /health/check` — Health

### Reasoning
- `GET /reasoning/refinancing/{portfolio_id}` — Refinancing risk
- `GET /reasoning/profile/{portfolio_id}` — Debt profile
- `POST /reasoning/dangerous-assumptions` — Dangerous assumptions
- `POST /reasoning/cross-layer` — Cross-layer reasoning

### Billing & Automation
- `POST /api/billing/webhook` — Stripe webhook (HMAC)
- `GET /api/billing/checkout` — Checkout session | `GET /api/billing/portal` — Customer portal
- `POST /api/automation/webhooks/external-run` — n8n relay (HMAC)
- `POST /api/lead-capture` — Lead webhook (HMAC) | `POST /api/demo-booked` — Demo (HMAC)
- `POST /api/deal-closed` — Deal (HMAC) | `POST /api/support-ticket` — Support (HMAC)
- `GET /api/optimize-debt/status` — Health | `GET /docs` — Swagger

### Stripe Events Handled
- `customer.subscription.created` → Upsert customer, log MRR
- `customer.subscription.updated` → Update plan
- `invoice.payment_failed` → Log failure, mark past_due
- `customer.subscription.deleted` → Mark churned

---

## DATABASE (PostgreSQL 16)

### Core
```sql
users (id UUID PK, email UNIQUE, hashed_password, full_name, role [analyst|senior_analyst|director|treasury|minister|admin], org_id, is_active, mfa_enabled, created_at)
portfolios (id UUID PK, name, description, owner_id→users, org_id, created_at)
instruments (id UUID PK, portfolio_id→portfolios ON DELETE CASCADE, name, instrument_type [government_bond|corporate_bond|green_bond|treasury_bill|notes|loan|swap|other], currency, principal_outstanding BIGINT, coupon_rate, maturity_date, issuer, rating, isin)
optimization_jobs (id UUID PK, portfolio_id→portfolios, name, optimization_type, status [pending|running|completed|failed|cancelled], progress, objectives JSONB, constraints JSONB, result JSONB, error_message, created_by→users, created_at, started_at, completed_at)
audit_log (id UUID PK, user_id→users, action, resource_type, resource_id, details JSONB, ip_address INET, created_at) -- partitioned monthly
approval_workflows (id UUID PK, optimization_job_id→optimization_jobs, status, current_approver→users, approval_chain JSONB)
```

### Billing & CRM
```sql
customers (id UUID PK, email UNIQUE, name, company, plan [starter|pro|enterprise], status [active|past_due|churned], stripe_customer_id UNIQUE, subscription_status, last_active_at, reengagement_sent, churned_at)
leads (id UUID PK, email UNIQUE, name, company, source, score, tier [hot|warm|cold], status [new|demo_scheduled|converted], company_size, industry, location, enriched_data JSONB, demo_booked_at, converted_at)
demos (id UUID PK, lead_email→leads, lead_name, company, demo_date, demo_type [discovery|technical|executive], status)
deals (id UUID PK, lead_email→leads, company, value DECIMAL, stage, closed_at)
mrr_events (id UUID PK, customer_id→customers, amount, event_type)
invoice_events (id UUID PK, stripe_customer_id, event_type, amount, status)
lead_followups (id UUID PK, lead_email→leads, followup_type, scheduled_at, status, attempts)
```

### Market & AI
```sql
market_data (id UUID PK, symbol, name, value DECIMAL, source, timestamp) -- ^TNX, DX-Y.NYB, GC=F, CL=F, ^GSPC, ^VIX, BTC-USD, ETH-USD
news_articles (id UUID PK, title, description, url UNIQUE, source, published_at)
api_health_checks (id UUID PK, service, status_code, response_time_ms, status)
```

### Risk & Operations
```sql
risk_assessments (id UUID PK, entity_id, entity_type, category [cyber|fiscal|climate|infrastructure|geopolitical|supply_chain], overall_score, indicators JSONB)
early_warning_signals (id UUID PK, entity_id, indicator_name, current_value, threshold, critical_threshold, status [normal|warning|critical], trend [improving|stable|deteriorating], months_until_crisis, bias_adjustment)
support_tickets (id UUID PK, subject, description, priority [low|medium|high|urgent], status [open|in_progress|resolved|closed], customer_email, assignee_id→users)
login_attempts (id UUID PK, email, ip_address INET, success, attempted_at)
government_entities (id UUID PK, entity_id UNIQUE, name, country_code, region)
versioned_assumptions (id UUID PK, entity_id→government_entities, assumption_key, assumption_value JSONB, bias_direction, confidence, version)
procurement_requests (id UUID PK, entity_id, items JSONB, metadata JSONB)
```

### n8n Tables (schema: workflows)
```sql
workflow_executions (id UUID PK, workflow_id, workflow_name, execution_id, status, duration_ms, metadata JSONB)
workflow_errors (id UUID PK, workflow_id, workflow_name, execution_id, error_type, message, severity [critical|high|medium|low])
backup_history (id UUID PK, backup_path, backup_size, status)
```

### Relationships
```
users→portfolios→instruments, users→optimization_jobs→approval_workflows
customers→mrr_events, leads→demos/deals/lead_followups
government_entities→versioned_assumptions/risk_assessments/early_warning_signals
```

---

## n8n WORKFLOWS (n8n-workflows/workflows/*.json, regenerate: `python generate_workflows.py`)

### WF-0: Error Handler
Error Trigger → Classify → Log to DB → Route by Severity → Slack
- Critical (timeout/5xx): #platform-critical | High (auth/401/403): #platform-alerts | Medium: #workflow-logs

### WF-1: Sales & CRM
- **Lead Capture** (webhook /webhook/lead-capture): HMAC → Upsert Lead → Clearbit Enrich → Score → Route (Hot≥70→#sales-leads, Warm 40-69→#sales-leads, Cold<40→schedule follow-ups)
- **Demo Booked** (webhook /webhook/demo-booked): HMAC → Insert Demo → Mark Lead → Slack #sales-demos
- **Deal Closed** (webhook /webhook/deal-closed): HMAC → Insert Deal → Convert Lead→Customer → Slack #sales-closed
- **Follow-ups** (cron weekdays 13:00): Get pending → Send email (SMTP)

### WF-2: Billing & Lifecycle
Stripe Trigger → Switch event → Upsert Customer/Update Plan/Log Failure/Mark Churned → Relay to /api/billing/webhook → Slack #billing-events
Re-engagement (Monday 09:00): Find inactive 30+ days → Send email → Mark sent

### WF-3: Platform & AI
- **Market Data** (*/30 * * * *): Yahoo Finance 8 symbols → Store → Bridge relay
- **News** (0 * * * *): NewsAPI → Insert articles → Bridge relay
- **AI Summary** (0 7 * * 1-5): OpenAI gpt-4o-mini → Slack #market-news → Bridge relay
- **Health** (*/15 * * * *): Ping backend → Store → Bridge relay
- **Digest** (0 * * * *): Fetch /api/v1/digest → Store → Bridge relay

### WF-4: Operations
- **Daily Digest** (0 8 * * *): Collect metrics → Slack #daily-digest → Bridge relay
- **Error Monitor** (0 */2 * * *): Recent errors → Slack #platform-alerts → Bridge relay
- **Security** (*/30 * * * *): Failed logins≥5 → Slack #security-alerts → Bridge relay
- **Backup** (0 3 * * *): Record → Slack #ops-notifications → Bridge relay
- **Support** (webhook /webhook/support-ticket): HMAC → Insert ticket → Route → Slack → Bridge relay

### Services
SVC-1: Enrichment (Clearbit) | SVC-2: Notification (Slack) | SVC-3: Logger (Postgres)

### Credentials
`postgres-main` (PostgreSQL), `slack-main` (Slack), `smtp-main` (SMTP), `httpQueryAuth` (Clearbit/NewsAPI), `httpHeaderAuth` (OpenAI), `stripe-main` (Stripe)

### Slack Channels
#platform-critical, #platform-alerts, #workflow-logs, #sales-leads, #sales-demos, #sales-closed, #billing-events, #market-news, #daily-digest, #ops-notifications, #support-alerts, #customer-success

### Cron Schedules (America/Mexico_City)
Market */30min, News hourly, AI weekdays 07:00, Health */15min, Digest hourly, Daily 08:00, Errors */2h, Security */30min, Backup 03:00, Follow-ups weekdays 13:00, Re-engagement Monday 09:00

---

## INTEGRATION PATTERNS

### Auth
```python
# API
headers = {"Authorization": f"Bearer {TOKEN}"}
# Webhook HMAC
expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
# Compare with X-Quantive-Signature header
# Direct Postgres
pool = await asyncpg.create_pool("postgresql://quantive:pass@host:5432/quantive")
```

### Webhook Events
optimization.completed | optimization.failed | risk.threshold_breached | billing.subscription_created | billing.payment_failed | billing.subscription_cancelled | lead.captured | lead.demo_booked | deal.closed | support.ticket_created

### Trigger Optimization
```python
problem = await api_post("/optimization", {"portfolio_id": pid, "financing_requirement": amount, "profile": "BEST_OVERALL"})
run = await api_post(f"/optimization/{problem['id']}/run", {"timeout": 600})
# Poll /optimization/jobs/{job_id} until completed/failed
```

### n8n Bridge Relay
```javascript
const body = JSON.stringify({ workflow: 'market-data', status: 'success', duration_ms: $execution.timeToComplete || 0 });
const signature = crypto.createHmac('sha256', secret).update(body).digest('hex');
// POST /api/automation/webhooks/external-run with X-Quantive-Signature header
```

### Rate Limits
Portfolio/Optimization CRUD: 100/min | Optimization Run: 10/min | Risk: 60/min | Webhooks: unlimited

---

## ENVIRONMENT VARIABLES

```
QUANTIVE_ENV=production
QUANTIVE_CORS_ORIGINS=https://app.yourdomain.gov
QUANTIVE_JOB_TIMEOUT=300
QUANTIVE_MAX_WORKERS=4
DB_HOST=postgres | DB_PORT=5432 | DB_NAME=quantive | DB_USER=quantive | DB_PASSWORD=xxx
DATABASE_URL=postgresql://quantive:${DB_PASSWORD}@postgres:5432/quantive
STRIPE_SECRET_KEY=sk_live_... | STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_MONTHLY_PRICE_ID=price_... | STRIPE_PRO_YEARLY_PRICE_ID=price_...
STRIPE_ENTERPRISE_MONTHLY_PRICE_ID=price_... | STRIPE_ENTERPRISE_YEARLY_PRICE_ID=price_...
QUANTIVE_WEBHOOK_SECRET=your-32-char-secret
FRED_API_KEY=... | NEWSAPI_KEY=... | OPENAI_API_KEY=sk-... | CLEARBIT_API_KEY=...
N8N_HOST=localhost | N8N_PORT=5678 | QUANTIVE_BASE_URL=http://backend:8000
SLACK_BOT_TOKEN=xoxb-... | SLACK_SIGNING_SECRET=...
SMTP_HOST=smtp.provider.com | SMTP_PORT=587 | SMTP_USER=quantive@domain.com | SMTP_PASS=... | SMTP_FROM=quantive@domain.com
```

---

## QUICK REFERENCE

```
BASE:      localhost:8000 (dev) | yourdomain.gov (prod)
AUTH:      Bearer <JWT>
DB:        postgresql://quantive:pass@localhost:5432/quantive
SWAGGER:   GET /docs | REDOC: GET /redoc

POST /portfolios → POST /optimization → POST /{id}/run → GET /{id}/results
GET /risk/aggregate/{entity} | GET /early-warning/signals/{entity}
POST /api/billing/webhook | POST /api/automation/webhooks/external-run

KEY TABLES: users, portfolios, instruments, optimization_jobs, customers, leads,
mrr_events, market_data, news_articles, risk_assessments, early_warning_signals, support_tickets

WORKFLOWS: WF-0 Error | WF-1 Sales | WF-2 Billing | WF-3 Platform | WF-4 Ops
SERVICES:  SVC-1 Enrichment | SVC-2 Notification | SVC-3 Logger
REGENERATE: cd n8n-workflows && python generate_workflows.py
```