# Quantive n8n Workflows

Production-ready workflow automation for the Quantive sovereign debt optimization platform.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WF-0: Error Handler                         │
│                    (Sub-workflow, called by all others)              │
│         Error Trigger → Classify → Log to DB → Route → Slack       │
└─────────────────────────────────────────────────────────────────────┘

┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│      WF-1         │  │      WF-2         │  │      WF-3         │  │      WF-4         │
│   Sales & CRM     │  │ Billing & Lifecycle│  │  Platform & AI    │  │  Operations       │
├───────────────────┤  ├───────────────────┤  ├───────────────────┤  ├───────────────────┤
│ • Lead Capture    │  │ • Stripe Events   │  │ • Market Data     │  │ • Daily Digest    │
│ • Demo Booking    │  │ • Signup Create   │  │ • News Ingestion  │  │ • Weekly Report   │
│ • Deal Close      │  │ • Onboarding      │  │ • Watchlist       │  │ • SLA Monitor     │
│ • Stage Updates   │  │ • MRR Tracking    │  │ • Stock Events    │  │ • Security Check  │
│ • Follow-up Cron  │  │ • Re-engagement   │  │ • Model Tracking  │  │ • Nightly Backup  │
│                   │  │ • Cancellation    │  │ • API Health      │  │ • Error Monitor   │
│                   │  │ • Payment Failure │  │ • Weekly Report   │  │ • Support Tickets │
└───────────────────┘  └───────────────────┘  └───────────────────┘  └───────────────────┘
```

## File Structure

```
n8n-workflows/
├── README.md                              # This file
├── AUDIT_AND_REDESIGN.md                  # Audit findings + fixes applied
├── .env.example                           # Environment variables template
├── credentials/
│   └── CREDENTIALS.md                     # Credential setup + webhook URL table
├── database/
│   └── schema.sql.md                      # Deprecated pointer → schemas/database-schema.sql
├── schemas/
│   └── database-schema.sql                # CANONICAL schema (matches workflow SQL)
├── analyze_tables.py                      # Verifies schema covers all workflow SQL
└── workflows/
    ├── 00-error-handler.json              # WF-0: Master error handler
    ├── 01-sales-crm.json                  # WF-1: Sales & CRM
    ├── 02-billing-lifecycle.json          # WF-2: Billing & Customer Lifecycle
    ├── 03-platform-ai.json                # WF-3: Platform & AI
    ├── 04-operations-internal.json        # WF-4: Operations & Internal
    ├── svc1-enrichment.json               # SVC-1: Lead enrichment (sub-workflow)
    ├── svc2-notification.json             # SVC-2: Slack notify + dedupe (sub-workflow)
    └── svc3-logger.json                   # SVC-3: Execution logging (sub-workflow)
```

> **Schema note:** `schemas/database-schema.sql` is derived from the SQL
> actually executed in the workflow Code nodes. After changing any
> workflow SQL, run `python analyze_tables.py` to confirm every
> referenced table/column is still covered. Quantive platform tables
> (`organizations`, `users`, `portfolios`, `debt_instruments`,
> `api_access_logs`, `login_attempts`) are read-only for n8n and are
> owned by the backend's migrations — intentionally not defined here.

## Prerequisites

- n8n v1.x (self-hosted or cloud)
- PostgreSQL 16+ with the schema from `schemas/database-schema.sql`
- Slack workspace with bot permissions
- Stripe account with webhook access
- OpenAI API key (for WF-3 predictions)
- FRED API key (for economic data in WF-3)
- News API key (for news ingestion in WF-3)

> **IMPORTANT — `Postgres.main` helper:** All database access in these workflows is done through a non-standard global `Postgres.main` (a connection/query helper exposed in the n8n Code node sandbox). It uses `Postgres.main.query(text, params)`. Before activating any workflow, you must make this helper available in the n8n Code-node environment (e.g. via a small plugin/community helper or a `loadWorkflowData`-style bootstrap that sets a global `Postgres` object using the `postgres-main` credential). Without it every Code node that touches the DB will fail. See the `credentials/CREDENTIALS.md` and `AUDIT_AND_REDESIGN.md` for details.

## Setup Instructions

### 1. Database Schema

```bash
psql -h localhost -U quantive -d quantive -f schemas/database-schema.sql
```

### 2. Environment Variables

```bash
cp .env.example .env
# Edit .env with your actual credentials and keys
```

### 3. Import Workflows

Import in order (WF-0 first, then 1-4):

1. **WF-0 Error Handler** — Import first, then activate
2. **WF-1 Sales & CRM** — Requires Postgres, Slack credentials
3. **WF-2 Billing & Lifecycle** — Requires Postgres, Slack credentials
4. **WF-3 Platform & AI** — Requires Postgres, Slack, OpenAI, FRED, News API keys
5. **WF-4 Operations** — Requires Postgres, Slack credentials

### 4. Configure Credentials

In n8n Settings → Credentials, create:

| Credential | Type | Purpose |
|---|---|---|
| `postgres-main` | PostgreSQL | Connection pool used by the `Postgres.main` helper |
| `slack-main` | Slack API | All Slack alerts |

API keys (FRED, NewsAPI, OpenAI, Stripe, webhook secrets) are provided via environment variables — see `.env.example`.

### 5. Activate Workflows

After configuring credentials and testing each workflow:

```bash
# Or activate via n8n API
curl -X PATCH https://your-n8n.example.com/api/v1/workflows/{id} \
  -H "X-N8N-API-KEY: your-key" \
  -H "Content-Type: application/json" \
  -d '{"active": true}'
```

## Workflow Details

### WF-0: Error Handler

**Trigger:** Error Trigger node (sub-workflow, called by WF-1 through WF-4)

**Flow:**
1. Classifies error by severity (critical/high/medium/low)
2. Logs to `workflow_errors` table
3. Routes based on severity:
   - Critical → `#platform-critical` + PagerDuty
   - High → `#platform-alerts`
   - Medium/Low → `#workflow-logs`

**Error Handler Reference:** Each workflow points its `settings.errorWorkflow` at `wf0-error-handler` (the WF-0 workflow id). Any unhandled error in a workflow is routed to the Error Trigger of WF-0 for classification, logging, and alerting. Non-critical side-effect nodes (Slack posts) additionally use `onError: "continueRegularOutput"` so a notification failure never aborts the process.

**Webhook authentication:**
- Internal webhooks (`/lead-capture`, `/demo-booked`, `/deal-closed`, `/deal-stage`, `/support-ticket`) require an `x-quantive-signature` header containing the HMAC-SHA256 of `JSON.stringify(body)` using `WEBHOOK_SECRET`.
- The Stripe webhook verifies the `stripe-signature` header (t=, v1=) against `STRIPE_WEBHOOK_SECRET` with a 5-minute timestamp tolerance and uses `rawBody` so the exact payload bytes are checked.
- Requests with invalid signatures are rejected (logged to `workflow_errors`, no side effects).

---

### WF-1: Sales & CRM

**Triggers:** 4 webhooks + 1 scheduled cron

| Flow | Trigger | Action |
|---|---|---|
| Lead Capture | `POST /webhook/lead-capture` | Verify HMAC → Upsert lead → Notify Slack → Log |
| Demo Booked | `POST /webhook/demo-booked` | Verify HMAC → Create demo + update lead → Notify Slack → Log |
| Deal Closed | `POST /webhook/deal-closed` | Verify HMAC → Create deal + customer + convert lead → Notify Slack → Log |
| Stage Update | `POST /webhook/deal-stage` | Verify HMAC → Update deal stage → Log |
| Follow-up | Cron: 9am/2pm weekdays | Get pending follow-ups → Mark attempts → Notify Slack → Log |

**Error Handler:** WF-0 (all errors route through error output)

---

### WF-2: Billing & Customer Lifecycle

**Triggers:** Stripe webhook (with signature verification) + 2 crons

| Flow | Trigger | Action |
|---|---|---|
| Stripe Router | `POST /webhook/stripe-webhook` | Verify signature → Route by `event.type` |
| Subscription Created | Stripe event | Create/upsert customer → Record MRR → Notify → Log |
| Subscription Updated | Stripe event | Update plan → Record MRR → Notify → Log |
| Subscription Deleted | Stripe event | Mark cancelled → Record cancellation → Notify → Log |
| Invoice Paid | Stripe event | Track MRR → Notify → Log |
| Invoice Failed | Stripe event | Record in `invoice_events` → Notify → Log |
| Checkout Completed | Stripe event | Notify → Log |
| Daily MRR | Cron: 6am daily | Aggregate MRR + churn → Report to Slack → Log |
| Re-engagement | Cron: 9am Mon | Find inactive customers → Flag → Notify Slack → Log |

**Supported Stripe Events:**
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`
- `checkout.session.completed`

**Error Handler:** WF-0

---

### WF-3: Platform & AI

**Triggers:** Multiple crons

| Flow | Schedule | Action |
|---|---|---|
| Market Data + AI | Every 15m | Fetch FRED data → Store → GPT-4 prediction → Store → Log |
| News Ingestion | Every 30m | Fetch news → Filter by keywords → Dedupe/store → Slack + Log |
| Watchlist | Cron: 8am/6pm | Compare symbols vs market data → Alert on target hit → Log |
| API Health | Every 10m | Ping FRED/NewsAPI/OpenAI → Store status → Alert if unhealthy → Log |
| Weekly Report | Cron: 9am Fri | Aggregate accuracy/news/health → Report to Slack → Log |

**AI Features:**
- OpenAI GPT-4 for market predictions (JSON-only output)
- Failure-tolerant: AI/API fetch errors are caught, logged, and surfaced via the API Health monitor

**Error Handler:** WF-0

---

### WF-4: Operations & Internal

**Triggers:** Multiple crons + 1 webhook

| Flow | Schedule | Action |
|---|---|---|
| Daily Digest | Cron: 8am daily | Platform stats + workflow health → Slack |
| Weekly Report | Cron: 5pm Fri | Revenue/growth metrics → Slack |
| SLA Monitor | Every 5m | Check ticket SLAs → Alert on breaches |
| Security Check | Hourly | Login failures + API abuse → Alert on anomalies |
| Nightly Backup | Cron: 2am daily | pg_dump → record backup_history → Slack |
| Error Monitor | Every 30m | Recent errors → Alert on patterns |
| Support Ticket | `POST /webhook/support-ticket` | Verify HMAC → Create ticket → Alert if urgent |

**Error Handler:** WF-0 (via `settings.errorWorkflow`)

---

## Monitoring & Observability

### Database Tables

All workflows log to PostgreSQL:

```sql
-- Execution tracking
workflows.workflow_executions (workflow_id, status, duration, error_message)
workflows.workflow_errors (severity, error_type, node_id, stack_trace)
workflows.api_health_checks (service, status_code, response_time_ms)
workflows.backup_history (backup_path, backup_size, status)
```

### Slack Channels

| Channel | Purpose |
|---|---|
| `#sales-leads` | New lead captured |
| `#sales-demos` | Demo booked |
| `#sales-closed` | Deal closed |
| `#sales-followups` | Follow-up reminders |
| `#billing-events` | Stripe lifecycle events |
| `#metrics-daily` | Daily MRR report |
| `#customer-success` | Re-engagement alerts |
| `#market-news` | Relevant market news |
| `#watchlist-alerts` | Watchlist target hits |
| `#api-alerts` | External API health issues |
| `#platform-weekly` | Weekly platform report |
| `#daily-digest` | Daily platform stats |
| `#weekly-report` | Weekly metrics |
| `#platform-alerts` | Workflow/system errors |
| `#support-alerts` | SLA breaches, urgent tickets |
| `#security-alerts` | Security anomalies |
| `#ops-notifications` | Backup results |

---

## Scaling & Production Notes

### Rate Limits
- Stripe webhooks: Handle idempotency via `stripe_event_id` dedup
- OpenAI API: 100 req/min (WF-3 predictions)
- FRED API: 120 req/min (WF-3 economic data)
- News API: 100 req/day (WF-3 news ingestion)

### Performance
- WF-1: ~50 executions/day (webhook-driven)
- WF-2: ~200 executions/day (Stripe events)
- WF-3: ~200 executions/day (scheduled crons)
- WF-4: ~300 executions/day (scheduled crons + monitoring)

### Security
- All webhooks validate HMAC signatures (Stripe)
- API keys stored in n8n credentials, never in workflow JSON
- Database connections use SSL in production
- Backup files encrypted at rest

---

## Troubleshooting

### Common Issues

1. **Workflow fails to import**
   - Check n8n version (requires v1.x)
   - Verify JSON is valid

2. **Credential errors**
   - Ensure credential IDs match: `postgres-main`, `slack-main`, etc.
   - Re-create credentials if IDs don't match

3. **Stripe webhook not firing**
   - Verify webhook endpoint URL
   - Check Stripe dashboard for delivery failures
   - Ensure `STRIPE_WEBHOOK_SECRET` matches

4. **PostgreSQL connection errors**
   - Verify SSL settings in credential
   - Check `DATABASE_URL` environment variable
   - Ensure schema tables exist

---

## License

Internal use only. Quantive © 2026
