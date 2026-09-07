# Quantive n8n Automation Ecosystem — Complete Audit & Redesign

**Audit Date:** 2026-09-06
**Auditor:** Senior n8n Architect / Systems Auditor
**Scope:** All workflows in `n8n-workflows/`

---

## TABLE OF CONTENTS

1. [Current-State Audit](#1-current-state-audit)
2. [Broken Workflows & Issues](#2-broken-workflows--issues)
3. [Duplicate & Overlapping Automations](#3-duplicate--overlapping-automations)
4. [Recommended Architecture](#4-recommended-architecture)
5. [Detailed Implementation Plan](#5-detailed-implementation-plan)
6. [Folder Structure](#6-folder-structure)
7. [Required Integrations & Credentials](#7-required-integrations--credentials)
8. [Workflow 1: Sales & CRM — Node-by-Node Design](#8-workflow-1-sales--crm)
9. [Workflow 2: Billing & Customer Lifecycle — Node-by-Node Design](#9-workflow-2-billing--customer-lifecycle)
10. [Workflow 3: Quantive Platform & AI — Node-by-Node Design](#10-workflow-3-quantive-platform--ai)
11. [Workflow 4: Operations & Internal Management — Node-by-Node Design](#11-workflow-4-operations--internal-management)
12. [Database Schema Recommendations](#12-database-schema-recommendations)
13. [Monitoring & Observability Plan](#13-monitoring--observability-plan)
14. [Security & Access-Control Plan](#14-security--access-control-plan)
15. [Disaster Recovery & Backup Strategy](#15-disaster-recovery--backup-strategy)

---

## 1. CURRENT-STATE AUDIT

### 1.1 Inventory

| File | Name | Nodes | Connections | Triggers | Active |
|------|------|-------|-------------|----------|--------|
| `01-sales.json` | Quantive — Sales | 37 | 24 | 5 webhooks + 2 cron | `false` |
| `02-platform.json` | Quantive — Platform | 24 | 18 | 3 webhooks + 4 cron | `false` |
| `03-management.json` | Quantive — Management | 35 | 22 | 3 webhooks + 9 cron | `false` |
| `04-internal.json` | Quantive — Internal | 29 | 18 | 7 webhooks + 4 cron | `false` |
| **TOTAL** | | **125** | **82** | **29 triggers** | **0 active** |

### 1.2 What Exists Today

The 4 workflows attempt to cover the entire automation surface but are **monolithic, disconnected, and non-functional**:

- **01-sales.json** — Attempts to handle: lead capture, lead enrichment, lead scoring, outreach, demo booking, deal closing, Stripe billing (checkout, subscriptions, invoices, failed payments, cancellations), MRR tracking, user signup, onboarding sequences, usage tracking, and re-engagement. This is 3+ domains crammed into one file.

- **02-platform.json** — Attempts to handle: market data polling, prediction model execution, watchlist alerts, news ingestion, stock event processing, model error tracking, API health checks, and weekly market reports.

- **03-management.json** — Attempts to handle: revenue reporting, MRR breakdowns, customer health scoring, churn alerts, sales pipeline, demo metrics, user activity, prediction performance, system health, support ticketing, SLA monitoring, and escalation management.

- **04-internal.json** — Attempts to handle: team notifications, task management, meeting scheduling, document workflows, contract management, marketing campaigns, weekly reports, backup monitoring, security scanning, and error monitoring.

### 1.3 Technology Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| Error Handling | **NONE** | Zero Error Trigger nodes, zero Try/Catch patterns |
| Retry Logic | **NONE** | No retry configurations on any node |
| Webhook Auth | **NONE** | All webhooks are unauthenticated |
| Credentials | **NONE** | Zero credential references anywhere |
| Real Integrations | **NONE** | 100% of nodes use `jsCode` with mock data |
| Node Types Used | **4 only** | webhook, code, if, scheduleTrigger — missing: httpRequest, slack, stripe, sendEmail, postgres, etc. |
| Execution History | **NONE** | All workflows `active: false` |
| Branching Logic | **MINIMAL** | Only 1 IF node in entire system (`Hot Lead?`) |

---

## 2. BROKEN WORKFLOWS & ISSUES

### 2.1 Critical Issues (System-Blocking)

| # | Workflow | Issue | Impact |
|---|----------|-------|--------|
| C1 | ALL | **Every node uses `jsCode` with mock/hardcoded data** — zero actual HTTP requests, zero real API calls | System is non-functional |
| C2 | ALL | **Zero credentials configured** — no Slack, Stripe, email, database, or API credentials | Nothing can authenticate |
| C3 | ALL | **Zero error handling** — no Error Trigger nodes, no Try/Catch, no `onError` settings | Any failure kills the entire execution |
| C4 | 01-sales | **Stripe Webhook processes ALL event types simultaneously** — `Process Checkout`, `Process Subscription`, `Process Invoice`, `Process Failed Payment` all fire on every webhook | Wrong processors run on wrong events |
| C5 | 01-sales | **`Hot Lead?` IF node connects BOTH outputs to same chain** — `true` branch → `Hot Lead Outreach`, `false` branch → `Warm Lead Nurture` + `Cold Lead Nurture` (both on same index) | Cold leads never get processed correctly |
| C6 | 01-sales | **`Send Follow-up Email` doesn't send anything** — it's a Code node formatting data, not an email node | Follow-ups never arrive |
| C7 | 03-management | **`Churn Alert Webhook` → `Churn Alert Processor` connection is broken** — the connection exists in the node list but the connection mapping is incomplete | Churn alerts silently dropped |
| C8 | 02-platform | **`Fetch Market Data` doesn't fetch anything** — creates objects with URLs but makes zero HTTP requests | No market data ingested |
| C9 | 02-platform | **`Run Prediction Models` uses `Math.random()`** — predictions are random numbers, not model outputs | All predictions are meaningless |

### 2.2 High-Severity Issues

| # | Workflow | Issue | Impact |
|---|----------|-------|--------|
| H1 | 01-sales | `Hot Lead Outreach`, `Warm Lead Nurture`, `Cold Lead Nurture` are Code nodes formatting email objects — no actual email sending | Outreach never sent |
| H2 | 01-sales | `Demo Confirmation + CRM + Slack` is one Code node trying to do 3 things — email + Slack + CRM update in a single `return[]` | Partial execution, no actual delivery |
| H3 | 01-sales | `Closed Deal Triggers` emits 6 items but downstream has no Split/Merge — only first item processed | 5 of 6 actions lost |
| H4 | 01-sales | `Calculate Daily MRR` has hardcoded `active` array with 2 customers | MRR is fake |
| H5 | 01-sales | `Create Account + Subscription + Tier` creates in-memory objects — nothing persisted | Accounts vanish on execution end |
| H6 | 01-sales | `Onboarding Sequence Builder` creates 5 items but `Send Onboarding Email` only processes first | 4 of 5 onboarding emails lost |
| H7 | 01-sales | `Classify + Trigger Re-engagement` has hardcoded user array | Re-engagement is fake |
| H8 | 02-platform | `News Relevance + Sentiment` uses `Math.random()` for sentiment analysis | News analysis is random |
| H9 | 02-platform | `API Health Processor` uses `Math.random()` for latency | Health checks are fake |
| H10 | 03-management | ALL metrics are `Math.random()` based | All reports are fiction |
| H11 | 03-management | `SLA Monitoring` has hardcoded ticket array | SLA tracking is fake |
| H12 | 04-internal | `Backup Status Processor` uses `Math.random()>0.05` for success | Backup status is random |
| H13 | 04-internal | `Security Event Scanner` uses `Math.random()` | Security monitoring is fiction |

### 2.3 Medium-Severity Issues

| # | Workflow | Issue |
|---|----------|-------|
| M1 | 01-sales | No webhook path versioning (all use v1 `webhookId`) |
| M2 | 01-sales | `Follow-up Sequence Builder` references `lead.sequence` but scoring node doesn't set this field |
| M3 | 01-sales | `Payment Recovery` references `f.customerEmail` but `Process Failed Payment` doesn't extract email |
| M4 | 01-sales | `Process Cancellation` references `e.customerEmail` and `e.cancellationReason` but `Process Subscription` doesn't extract these |
| M5 | 01-sales | `Customer Portal Link` references `e.customerName` not present in upstream data |
| M6 | 01-sales | `Revenue Slack Update` references inconsistent field names between `Update Customer + MRR` and `Process Cancellation` |
| M7 | 02-platform | `Watchlist Alert Processor` references `e.changePercent`, `e.threshold`, `e.currentPrice` — none set by upstream |
| M8 | 02-platform | `Store + Send News Digest` references `n.headline` but upstream sets `n.summary` |
| M9 | 02-platform | `Notify Stock Events` references `s.action` and `s.reason` — not validated |
| M10 | 03-management | Duplicate 9 AM triggers: `Daily Revenue Report` and `Daily Pipeline Report` both at `0 9 * * *` |
| M11 | 03-management | `Customer Health Webhook` → `Health Score Calculator` uses weighted formula but inputs are undefined |
| M12 | 04-internal | `Meeting Scheduler` creates calendar event object but no calendar API call |
| M13 | 04-internal | `Document Review Notification` references `d.documentId` not present in upstream |
| M14 | ALL | No `continueOnFail` on any node |
| M15 | ALL | No execution timeout configured |

---

## 3. DUPLICATE & OVERLAPPING AUTOMATIONS

### 3.1 Cross-Workflow Duplicates

| Function | Workflow 1 | Workflow 2 | Resolution |
|----------|-----------|-----------|------------|
| MRR Tracking | `01-sales`: `Update Customer + MRR`, `Revenue Slack Update`, `Daily MRR Snapshot`, `Calculate Daily MRR`, `Store + Report MRR` | `03-management`: `Weekly MRR Breakdown`, `Calculate MRR Breakdown`, `Send MRR Breakdown` | Consolidate into Billing workflow |
| Revenue Reporting | `01-sales`: `Store + Report MRR` | `03-management`: `Daily Revenue Report`, `Pull Revenue Metrics`, `Send Revenue Slack` | Consolidate into Operations |
| Customer Notifications | `01-sales`: `Welcome Email + Team Notification` | `03-management`: `Customer Health Alerts` | Split: welcome → Billing, health → Operations |
| Slack Notifications | `01-sales`: 4 Slack messages | `02-platform`: 3 Slack messages | Standardize channel routing |
| System Health | `02-platform`: `API Health Check`, `API Health Processor`, `API Health Alerts` | `03-management`: `System Health Check`, `Pull System Metrics`, `System Health Alerts` | Consolidate into Operations |
| Error Monitoring | `02-platform`: `Model Error Webhook`, `Error Severity Classifier`, `Notify Model Errors` | `04-internal`: `Error Monitor`, `Error Rate Scanner`, `Error Alert Sender` | Consolidate into Operations |
| Daily Reports | `03-management`: 5 daily reports | `04-internal`: 1 weekly report | Consolidate into Operations |

### 3.2 Intra-Workflow Duplicates

| Workflow | Duplicate Nodes | Issue |
|----------|----------------|-------|
| 01-sales | `Hot Lead Nurture` + `Warm Lead Nurture` + `Cold Lead Nurture` | Nearly identical Code nodes with different template names |
| 01-sales | `Follow-up Sequence Builder` + `Send Follow-up Email` | Could be single node |
| 01-sales | `Onboarding Sequence Builder` + `Send Onboarding Email` | Could be single node |
| 01-sales | `Classify + Trigger Re-engagement` + `Send Re-engagement Email` | Could be single node |
| 03-management | `Pull Revenue Metrics` + `Send Revenue Slack` | Data fetch + send in separate nodes but no real data source |
| 03-management | `Pull Demo Metrics` + `Send Demo Report` | Same pattern |
| 03-management | `Pull User Activity` + `Send User Activity` | Same pattern |
| 03-management | `Pull Prediction Performance` + `Send Prediction Report` | Same pattern |
| 04-internal | `Pull Team Metrics` + `Send Weekly Report` | Same pattern |

---

## 4. RECOMMENDED ARCHITECTURE

### 4.1 Four Master Workflows

```
┌─────────────────────────────────────────────────────────────────────┐
│                    QUANTIVE AUTOMATION ECOSYSTEM                     │
├─────────────────┬──────────────────┬───────────────┬───────────────┤
│  WF-1: SALES    │  WF-2: BILLING   │  WF-3:        │  WF-4:        │
│  & CRM          │  & CUSTOMER      │  PLATFORM     │  OPERATIONS   │
│                 │  LIFECYCLE       │  & AI         │  & INTERNAL   │
├─────────────────┼──────────────────┼───────────────┼───────────────┤
│ Lead Capture    │ Checkout         │ Market Data   │ Revenue Rpts  │
│ Lead Enrichment │ Subscriptions    │ Predictions   │ MRR Rpts      │
│ Lead Scoring    │ Payments         │ Watchlist     │ Pipeline Rpts │
│ Outreach        │ Invoices         │ News          │ Demo Rpts     │
│ Demo Booking    │ Failed Recovery  │ Stock Events  │ User Activity │
│ Deal Tracking   │ Cancellations    │ Model Health  │ Support Tix   │
│ CRM Updates     │ Upgrades/Down    │ API Health    │ SLA Monitor   │
│ Follow-ups      │ Portal           │ AI Summaries  │ Escalation    │
│                 │ MRR/Revenue      │ Error Track   │ Team Notify   │
│                 │ Churn            │ Weekly Rpts   │ Tasks         │
│                 │ Onboarding       │               │ Contracts     │
│                 │ Re-engagement    │               │ Security      │
│                 │                  │               │ Backups       │
│                 │                  │               │ Error Monitor │
├─────────────────┼──────────────────┼───────────────┼───────────────┤
│ 15 nodes        │ 28 nodes         │ 22 nodes      │ 30 nodes      │
│ 3 webhooks      │ 4 webhooks       │ 3 webhooks    │ 5 webhooks    │
│ 0 cron          │ 2 cron           │ 5 cron        │ 8 cron        │
└─────────────────┴──────────────────┴───────────────┴───────────────┘
```

### 4.2 Design Principles

1. **Single Responsibility** — Each workflow handles one business domain
2. **Event Type Filtering** — Webhook routers dispatch by event type before processing
3. **Error Isolation** — Every branch has `continueOnFail: true` + Error Trigger nodes
4. **Real Integrations** — Replace all `jsCode` mock data with actual node types (HTTP Request, Slack, Stripe, Send Email, PostgreSQL)
5. **Idempotency** — Deduplication keys on all webhook processors
6. **Retry with Backoff** — Exponential retry on all external calls
7. **Observability** — Execution logging to PostgreSQL + Slack alerts on failure
8. **Security** — Webhook HMAC validation, credential vault, RBAC on execution access

### 4.3 Shared Infrastructure

All 4 workflows share:
- **Error Trigger Node** → Logs to `workflow_errors` table → Slack `#ops-alerts`
- **Execution Logger** → Post-execution hook → Logs to `workflow_executions` table
- **Credential Vault** — All credentials stored in n8n credential store, referenced by name
- **Slack Channel Standardization**:
  - `#sales-alerts` — Lead/deal events
  - `#billing-alerts` — Payment/subscription events
  - `#market-alerts` — Market data/prediction events
  - `#ops-alerts` — System/security/backup events
  - `#customer-success` — Health/churn events
  - `#team` — Internal team notifications
  - `#metrics` — MRR/revenue metrics

---

## 5. DETAILED IMPLEMENTATION PLAN

### Phase 1: Foundation (Week 1)

| Task | Priority | Effort |
|------|----------|--------|
| Set up n8n credentials (Slack, Stripe, SMTP, PostgreSQL, APIs) | Critical | 4h |
| Create database tables (`workflow_executions`, `workflow_errors`, `leads`, `customers`, `subscriptions`, `revenue_snapshots`, `support_tickets`, `audit_log`) | Critical | 6h |
| Set up Slack channels | High | 1h |
| Create shared Code libraries (reusable functions) | High | 4h |
| Set up monitoring dashboard | High | 4h |

### Phase 2: Workflow 2 — Billing & Customer Lifecycle (Week 2)

This is the most critical workflow as it handles money.

| Task | Priority | Effort |
|------|----------|--------|
| Build Stripe Webhook Router with event type filtering | Critical | 4h |
| Build Checkout processor | Critical | 2h |
| Build Subscription lifecycle processor | Critical | 4h |
| Build Invoice processor | Critical | 2h |
| Build Failed Payment Recovery with escalation | Critical | 4h |
| Build Cancellation/Churn processor | Critical | 3h |
| Build MRR Calculator (scheduled) | High | 3h |
| Build Onboarding Sequence | High | 4h |
| Build Re-engagement Engine | Medium | 3h |
| Test with Stripe CLI | Critical | 4h |

### Phase 3: Workflow 1 — Sales & CRM (Week 3)

| Task | Priority | Effort |
|------|----------|--------|
| Build Lead Capture Webhook with HMAC validation | Critical | 2h |
| Build Lead Enrichment (Clearbit/Apollo API) | Critical | 4h |
| Build Lead Scoring Engine | High | 3h |
| Build Outreach Dispatcher (email sequences) | High | 4h |
| Build Demo Booking flow | High | 3h |
| Build Deal Closed trigger → onboarding handoff | Critical | 3h |
| Build Follow-up Sequence Scheduler | Medium | 3h |
| Test end-to-end | Critical | 4h |

### Phase 4: Workflow 3 — Quantive Platform & AI (Week 4)

| Task | Priority | Effort |
|------|----------|--------|
| Build Market Data Ingestion (FRED, Treasury, World Bank APIs) | Critical | 6h |
| Build Prediction Refresh pipeline | Critical | 4h |
| Build Watchlist Alert processor | High | 3h |
| Build News Ingestion + Sentiment Analysis | High | 4h |
| Build Model Error Tracking | High | 3h |
| Build API Health Check system | Medium | 3h |
| Build Weekly Market Report generator | Medium | 3h |

### Phase 5: Workflow 4 — Operations & Internal Management (Week 5)

| Task | Priority | Effort |
|------|----------|--------|
| Build Daily Revenue/Pipeline/Demo/User reports | High | 6h |
| Build Support Ticket System with SLA | High | 6h |
| Build Customer Health Scoring | High | 4h |
| Build Churn Alert system | High | 3h |
| Build Team Notification router | Medium | 3h |
| Build Task/Meeting/Document/Contract workflows | Medium | 6h |
| Build Backup Monitoring | Medium | 2h |
| Build Security Scanner | Medium | 3h |
| Build Error Monitor | Medium | 2h |

### Phase 6: Hardening (Week 6)

| Task | Priority | Effort |
|------|----------|--------|
| Add error handling to all workflows | Critical | 6h |
| Add retry logic to all external calls | Critical | 4h |
| Add execution logging | High | 3h |
| Load testing | High | 4h |
| Security audit | High | 4h |
| Documentation | Medium | 4h |

---

## 6. FOLDER STRUCTURE

```
n8n-workflows/
├── AUDIT_AND_REDESIGN.md          # This document
├── workflows/
│   ├── 01-sales-crm.json          # Sales & CRM workflow
│   ├── 02-billing-lifecycle.json   # Billing & Customer Lifecycle
│   ├── 03-platform-ai.json        # Quantive Platform & AI
│   └── 04-operations-internal.json # Operations & Internal
├── libraries/
│   ├── slack-helpers.js           # Shared Slack formatting
│   ├── email-templates.js         # Email template definitions
│   ├── scoring-engine.js          # Lead/health scoring logic
│   └── error-handler.js           # Shared error handling
├── credentials/
│   ├── CREDENTIALS.md             # Credential setup guide
│   └── .env.example               # Environment variables
├── database/
│   ├── schema.sql                 # Database schema
│   └── migrations/                # Schema migrations
├── monitoring/
│   ├── dashboards.json            # Grafana/n8n dashboard config
│   └── alerts.json                # Alert rules
└── docs/
    ├── webhook-payloads.md        # Expected webhook formats
    ├── slack-channels.md          # Channel naming conventions
    └── runbook.md                 # Operational runbook
```

---

## 7. REQUIRED INTEGRATIONS & CREDENTIALS

### 7.1 Credential Inventory

| Credential | Type | Used By | Priority |
|------------|------|---------|----------|
| **Slack OAuth** | Slack API | All workflows | Critical |
| **Stripe API Key** | Stripe | WF-2 (Billing) | Critical |
| **Stripe Webhook Secret** | HMAC | WF-2 (Billing) | Critical |
| **SMTP Credentials** | Email | WF-1, WF-2 | Critical |
| **PostgreSQL** | Database | All workflows | Critical |
| **FRED API Key** | HTTP Header | WF-3 (Platform) | High |
| **Treasury.gov API** | HTTP Header | WF-3 (Platform) | High |
| **World Bank API** | HTTP Header | WF-3 (Platform) | High |
| **Clearbit API Key** | HTTP Header | WF-1 (Sales) | High |
| **Apollo API Key** | HTTP Header | WF-1 (Sales) | High |
| **Google Calendar API** | OAuth2 | WF-4 (Operations) | Medium |
| **Sentry API Key** | HTTP Header | WF-4 (Operations) | Medium |
| **PostHog API Key** | HTTP Header | WF-3 (Platform) | Medium |

### 7.2 Slack Channels Required

| Channel | Purpose | Workflows |
|---------|---------|-----------|
| `#sales-alerts` | Lead captures, deal closings, demo bookings | WF-1 |
| `#billing-alerts` | Payment failures, cancellations, subscription changes | WF-2 |
| `#metrics` | MRR updates, revenue snapshots | WF-2, WF-4 |
| `#market-alerts` | Prediction alerts, market shocks | WF-3 |
| `#market-data` | Market data updates, news digests | WF-3 |
| `#watchlist-alerts` | Watchlist price/news triggers | WF-3 |
| `#news-feed` | News relevance digests | WF-3 |
| `#stock-alerts` | Stock event notifications | WF-3 |
| `#model-alerts` | Model errors, degradation | WF-3 |
| `#customer-success` | Health scores, churn risks | WF-4 |
| `#support` | Ticket assignments, SLA alerts | WF-4 |
| `#ops-alerts` | System health, API errors, backups | WF-4 |
| `#security` | Security events, brute force | WF-4 |
| `#team` | Team notifications, weekly reports | WF-4 |
| `#tasks` | Task assignments | WF-4 |
| `#deployments` | Deployment notifications | WF-4 |
| `#contracts` | Contract status changes | WF-4 |
| `#documents` | Document review requests | WF-4 |
| `#general` | Company-wide announcements | All |

### 7.3 Database Tables Required

```sql
-- Core business tables
leads (id, email, name, company, source, score, tier, status, enriched_data, created_at, updated_at)
customers (id, email, name, company, stripe_customer_id, plan, status, mrr, health_score, created_at, updated_at)
subscriptions (id, customer_id, stripe_subscription_id, plan, status, current_period_end, cancel_at_period_end, created_at)
deals (id, customer_id, amount, stage, owner_id, close_date, created_at)

-- Revenue tracking
revenue_snapshots (id, date, total_mrr, arr, by_plan_json, active_customers, created_at)
mrr_events (id, customer_id, old_mrr, new_mrr, change_type, timestamp)

-- Support
support_tickets (id, customer_id, subject, category, priority, status, assignee, sla_deadline, created_at, updated_at)

-- Platform
predictions (id, model, forecast_json, confidence, generated_at)
market_data (id, source, data_json, quality_score, fetched_at)
news_items (id, source, headline, sentiment, relevance, matched_keywords, stored_at)
model_errors (id, model, error_type, error_rate, affected_count, detected_at)

-- Operations
workflow_executions (id, workflow_name, workflow_id, execution_id, status, started_at, finished_at, error_message)
workflow_errors (id, workflow_name, execution_id, node_name, error_message, stack_trace, occurred_at)
audit_log (id, actor, action, resource_type, resource_id, metadata_json, ip_address, timestamp)

-- Onboarding
onboarding_progress (id, customer_id, current_step, total_steps, milestones_json, started_at, completed_at)
```

---

## 8. WORKFLOW 1: SALES & CRM

### Purpose
Capture, enrich, score, and nurture leads through the sales pipeline. Trigger onboarding upon deal closure.

### Trigger
- `POST /webhook/lead-capture` — New lead from website/demo request
- `POST /webhook/demo-booked` — Demo scheduled via Calendly
- `POST /webhook/deal-closed` — Deal marked closed-won in CRM

### Applications Used
- **Slack** — Team notifications
- **SMTP/Gmail** — Outreach emails
- **PostgreSQL** — Lead/customer persistence
- **Clearbit/Apollo** — Lead enrichment API
- **HTTP Request** — External API calls

### Complete Node Architecture (15 nodes)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WF-1: SALES & CRM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  TRIGGER LAYER                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ Lead Capture │  │ Demo Booked  │  │ Deal Closed  │                  │
│  │ Webhook      │  │ Webhook      │  │ Webhook      │                  │
│  │ POST /leads  │  │ POST /demo   │  │ POST /deals  │                  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
│         │                  │                  │                          │
│  PROCESSING LAYER          │                  │                          │
│  ┌──────▼───────┐          │                  │                          │
│  │ HMAC Verify  │          │                  │                          │
│  │ + Dedupe     │          │                  │                          │
│  └──────┬───────┘          │                  │                          │
│  ┌──────▼───────┐          │                  │                          │
│  │ Lead         │          │                  │                          │
│  │ Enrichment   │          │                  │                          │
│  │ (Clearbit)   │          │                  │                          │
│  └──────┬───────┘          │                  │                          │
│  ┌──────▼───────┐          │                  │                          │
│  │ Lead Scoring │          │                  │                          │
│  │ Engine       │          │                  │                          │
│  └──────┬───────┘          │                  │                          │
│         │                  │                  │                          │
│  ROUTING LAYER             │                  │                          │
│  ┌──────▼───────┐          │                  │                          │
│  │ Score Router │          │                  │                          │
│  │ IF ≥80: hot  │──────┐   │                  │                          │
│  │ IF ≥50: warm │────┐ │   │                  │                          │
│  │ ELSE: cold   │──┐ │ │   │                  │                          │
│  └──────────────┘  │ │ │   │                  │                          │
│                    │ │ │   │                  │                          │
│  OUTREACH LAYER    │ │ │   │                  │                          │
│  ┌─────────────────▼─┐ │   │                  │                          │
│  │ Hot Lead: Direct  │ │   │                  │                          │
│  │ Email + Slack     │ │   │                  │                          │
│  └─────────┬─────────┘ │   │                  │                          │
│  ┌─────────▼─────────┐ │   │                  │                          │
│  │ Warm Lead: Nurture │ │   │                  │                          │
│  │ Sequence Start     │ │   │                  │                          │
│  └─────────┬─────────┘ │   │                  │                          │
│  ┌─────────▼─────────┐ │   │                  │                          │
│  │ Cold Lead: Drip   │─┘   │                  │                          │
│  │ Campaign Start    │     │                  │                          │
│  └─────────┬─────────┘     │                  │                          │
│            │               │                  │                          │
│  ┌─────────▼─────────┐     │                  │                          │
│  │ Persist to DB     │     │                  │                          │
│  │ + CRM Update      │     │                  │                          │
│  └─────────┬─────────┘     │                  │                          │
│            │               │                  │                          │
│  ┌─────────▼─────────┐     │                  │                          │
│  │ Schedule Follow-up│     │                  │                          │
│  │ (n8n Wait node)   │     │                  │                          │
│  └─────────┬─────────┘     │                  │                          │
│            │               │                  │                          │
│  ┌─────────▼─────────┐     │                  │                          │
│  │ Send Follow-up    │     │                  │                          │
│  │ Email (SMTP)      │     │                  │                          │
│  └───────────────────┘     │                  │                          │
│                            │                  │                          │
│  DEMO FLOW                 │                  │                          │
│  ┌─────────────────────────▼──┐               │                          │
│  │ Demo Confirmation Email    │               │                          │
│  │ + Slack #sales-alerts      │               │                          │
│  │ + CRM Update (status)      │               │                          │
│  └─────────────────┬──────────┘               │                          │
│                    │                          │                          │
│  DEAL FLOW         │                          │                          │
│  ┌─────────────────┼──────────────────────────▼──┐                      │
│  │ Deal Close Router│                             │                      │
│  │ → CRM Update     │                             │                      │
│  │ → Welcome Email  │                             │                      │
│  │ → Onboarding     │                             │                      │
│  │ → MRR Track      │                             │                      │
│  │ → Slack Notify   │                             │                      │
│  │ → Commission     │                             │                      │
│  └──────────────────┘                             │                      │
│                                                                         │
│  ERROR HANDLING                                                         │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │ Error Trigger → Log to workflow_errors → Slack #ops-alerts   │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Node-by-Node Specification

| # | Node Name | Type | Config | Input | Output |
|---|-----------|------|--------|-------|--------|
| 1 | **Lead Capture Webhook** | `n8n-nodes-base.webhook` | `POST /leads`, `responseMode: lastNode`, `options.responseCode: 201` | HTTP | Lead JSON |
| 2 | **HMAC Signature Verify** | `n8n-nodes-base.code` | Verify `x-webhook-signature` header against HMAC-SHA256 of body using webhook secret | Lead JSON | Verified lead or 401 |
| 3 | **Lead Deduplication** | `n8n-nodes-base.postgres` | `SELECT id FROM leads WHERE email = $1 AND created_at > NOW() - INTERVAL '24 hours'` | Lead JSON | Deduplicated lead |
| 4 | **Lead Enrichment** | `n8n-nodes-base.httpRequest` | `GET https://api.clearbit.com/v1/companies/find?domain={{domain}}` with API key header | Lead JSON | Enriched lead |
| 5 | **Lead Scoring** | `n8n-nodes-base.code` | Weighted scoring: companySize (0-70) + industry (0-30) + tech stack (0-40) + source (0-40) + email domain (0-10) | Enriched lead | Scored lead |
| 6 | **Score Router** | `n8n-nodes-base.if` | `{{score}} >= 80` → hot, `{{score}} >= 50` → warm, else cold | Scored lead | 3 branches |
| 7 | **Hot Lead Email** | `n8n-nodes-base.sendEmail` | Direct personalized email with demo booking CCA, SMTP credential, high priority | Hot lead | Sent email |
| 8 | **Warm Lead Nurture** | `n8n-nodes-base.sendEmail` | 5-step nurture sequence trigger (welcome → insights → case study → demo → ROI) | Warm lead | Sequence started |
| 9 | **Cold Lead Drip** | `n8n-nodes-base.sendEmail` | Monthly market pulse + educational content drip | Cold lead | Drip started |
| 10 | **Demo Confirmation** | `n8n-nodes-base.sendEmail` | Confirmation email with meeting link, prep materials, calendar invite | Demo data | Confirmation sent |
| 11 | **Demo Slack Alert** | `n8n-nodes-base.slack` | `#sales-alerts`: "Demo booked: {name} ({company}) — {date}" | Demo data | Slack message |
| 12 | **Deal Close Processor** | `n8n-nodes-base.code` | Generate 6 actions: CRM update, welcome email, onboarding trigger, MRR track, Slack notify, commission calc | Deal JSON | 6 action items |
| 13 | **Welcome Email** | `n8n-nodes-base.sendEmail` | Welcome template with login URL, plan details, onboarding link, CSM assignment | New customer | Welcome sent |
| 14 | **Deal Slack Alert** | `n8n-nodes-base.slack` | `#sales-alerts`: "New customer: {company} ({plan}) — ${amount}" | Deal data | Slack message |
| 15 | **PostgreSQL Persist** | `n8n-nodes-base.postgres` | `INSERT INTO leads` or `UPDATE leads SET ... WHERE id = $1` | All data | Persisted |

### Data Flow

```
Website Form → Webhook → HMAC Verify → Dedupe → Enrich (Clearbit) → Score
    ↓
Score Router:
  ≥80 (hot) → Direct email + Slack alert
  ≥50 (warm) → 5-step nurture sequence
  <50 (cold) → Monthly drip campaign
    ↓
All paths → PostgreSQL persist → Follow-up scheduler (n8n Wait)

Demo Booked → Webhook → Confirmation email + Slack + CRM update

Deal Closed → Webhook → 6-way fan-out:
  → CRM update (stage=closed_won)
  → Welcome email to customer
  → Onboarding sequence trigger
  → MRR tracking (insert revenue event)
  → Slack #sales-alerts notification
  → Commission calculation
```

### Error Handling

| Error Type | Handler | Action |
|------------|---------|--------|
| HMAC verification failure | Inline Code | Return 401, log to `workflow_errors` |
| Enrichment API timeout | `continueOnFail: true` | Use fallback data, log warning |
| Enrichment API error (5xx) | Retry node (3x, exponential) | Then continue with partial data |
| Score calculation error | `continueOnFail: true` | Default to "cold" tier |
| Email send failure | Retry node (3x, 30s/60s/120s) | Then log to `workflow_errors` |
| Slack API failure | Retry node (3x) | Then continue (non-critical) |
| PostgreSQL write failure | Error Trigger → Slack #ops-alerts | Critical: halt, alert ops |

### Retry Strategy

| Node | Retries | Backoff | Timeout |
|------|---------|---------|---------|
| Lead Enrichment (HTTP) | 3 | Exponential: 5s, 15s, 45s | 30s per attempt |
| Hot Lead Email | 3 | Exponential: 30s, 60s, 120s | 15s per attempt |
| Warm/Cold Email | 3 | Exponential: 30s, 60s, 120s | 15s per attempt |
| PostgreSQL | 2 | Linear: 5s, 10s | 10s per attempt |
| Slack | 2 | Linear: 5s, 10s | 10s per attempt |

### Monitoring Strategy

- **Execution Log**: Every execution logged to `workflow_executions` with status, duration, item count
- **Error Log**: Every error logged to `workflow_errors` with node name, error message, stack trace
- **Slack Alert**: Critical failures → `#ops-alerts`
- **Metrics Dashboard**: Lead capture rate, enrichment success rate, score distribution, email delivery rate
- **Weekly Report**: Total leads, conversion by tier, avg time to demo, demo-to-close rate

### Security Considerations

- Webhook HMAC-SHA256 signature verification on all inbound webhooks
- API keys stored in n8n credential vault, never in code
- Email rate limiting (max 100/hour per domain to prevent spam flags)
- PII handling: leads table encrypted at rest, GDPR-compliant data retention
- Audit log: every lead access logged with actor + timestamp

### Scaling Considerations

- Webhook handles 1000+ req/s via n8n queue mode
- Lead enrichment batched (Clearbit rate limit: 100 req/min)
- Email sending via SMTP pool or SendGrid/Mailgun for high volume
- PostgreSQL indexed on `email`, `score`, `created_at` for fast lookups
- Follow-up scheduling uses n8n Wait nodes (survives restarts)

---

## 9. WORKFLOW 2: BILLING & CUSTOMER LIFECYCLE

### Purpose
Handle the complete Stripe billing lifecycle: checkout, subscriptions, payments, invoices, failures, cancellations, upgrades/downgrades. Track MRR, manage onboarding sequences, and trigger re-engagement.

### Trigger
- `POST /webhook/stripe` — Stripe webhook with event type routing
- `POST /webhook/user-signup` — New user registration
- `POST /webhook/onboarding-event` — Onboarding milestone achieved
- Schedule: Daily MRR snapshot (2 AM UTC)
- Schedule: Daily usage check + re-engagement (9 AM UTC)

### Applications Used
- **Stripe API** — Payment processing, subscription management
- **Slack** — Billing alerts, MRR updates
- **SMTP** — Transactional emails (receipts, payment failures, onboarding)
- **PostgreSQL** — Customer/subscription/revenue persistence

### Complete Node Architecture (28 nodes)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   WF-2: BILLING & CUSTOMER LIFECYCLE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  STRIPE WEBHOOK PROCESSOR                                                  │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────────┐                                                      │
│  │ Stripe Webhook   │                                                      │
│  │ POST /stripe     │                                                      │
│  │ HMAC Verify      │                                                      │
│  └────────┬─────────┘                                                      │
│           │                                                                 │
│  ┌────────▼─────────┐                                                      │
│  │ Event Type Router │──── Switch Node ────┐                                │
│  │ Extract event.type│                     │                                │
│  └──────────────────┘                     │                                │
│                                           │                                │
│  ┌──────────┬──────────┬──────────┬───────┼──────────┬──────────┐          │
│  ▼          ▼          ▼          ▼       ▼          ▼          ▼          │
│ checkout  sub.Updated sub.Deleted invoice pay.success pay.fail  customer   │
│ .completed          .canceled   .paid    .succeeded  .failed   .updated    │
│  │          │          │          │       │          │          │           │
│  ▼          ▼          ▼          ▼       ▼          ▼          ▼           │
│ Process   Process    Process   Process  Process   Process    Process       │
│ Checkout  Sub Update Sub Cancel Invoice  Payment   Failed     Customer     │
│           /Upgrade   /Churn    Receipt  Success   Payment    Update        │
│  │          │          │          │       │          │          │           │
│  ▼          ▼          ▼          ▼       ▼          ▼          ▼           │
│ Create    Update     Record    Send     Log       Start      Update        │
│ Customer  Subscription Cancellation Receipt Payment Recovery Subscription │
│ Record    in DB      Event      Email   Event    Sequence    Status        │
│  │          │          │          │       │          │          │           │
│  ▼          ▼          ▼          ▼       ▼          ▼          ▼           │
│ Welcome   Slack      Slack     Store    Store     Email      Slack         │
│ Email     #billing   #billing  Invoice #payments Day 1:      #billing      │
│ + Onboard #metrics   #churn    + Slack  + Slack   "Payment   + Update      │
│           (MRR)      (alert)           #metrics   Failed"    MRR           │
│                                                       │                    │
│                                                       ▼                    │
│                                                  Email Day 3:              │
│                                                  "Retry Notice"            │
│                                                       │                    │
│                                                       ▼                    │
│                                                  Email Day 7:              │
│                                                  "Final Notice"            │
│                                                       │                    │
│                                                       ▼                    │
│                                                  If still failing:         │
│                                                  → Cancel subscription     │
│                                                  → Slack #billing-alerts   │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  USER SIGNUP & ONBOARDING                                                  │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────┐                                                          │
│  │ User Signup  │                                                          │
│  │ Webhook      │                                                          │
│  └──────┬───────┘                                                          │
│         │                                                                   │
│  ┌──────▼───────┐                                                          │
│  │ Create       │                                                          │
│  │ Account +    │                                                          │
│  │ Subscription │                                                          │
│  │ + Tier       │                                                          │
│  └──────┬───────┘                                                          │
│         │                                                                   │
│  ┌──────▼───────┐    ┌──────────────┐                                      │
│  │ Welcome Email│    │ Onboarding   │                                      │
│  │ (SMTP)       │    │ Sequence     │                                      │
│  └──────┬───────┘    │ Builder      │                                      │
│         │            └──────┬───────┘                                      │
│         │                   │                                               │
│  ┌──────▼───────┐    ┌──────▼───────┐    ┌──────────────┐                  │
│  │ Slack #team  │    │ Step 1: Day 0│    │ Step 2: Day 1│                  │
│  │ "New signup" │    │ "Complete    │    │ "Create      │                  │
│  └──────────────┘    │  profile"    │    │  Portfolio"  │                  │
│                      └──────────────┘    └──────────────┘                  │
│                             │                                               │
│                      ┌──────▼───────┐    ┌──────────────┐                  │
│                      │ Step 3: Day 3│    │ Step 4: Day 7│                  │
│                      │ "Run first   │    │ "Explore AI" │                  │
│                      │  optimization│    │              │                  │
│                      └──────────────┘    └──────────────┘                  │
│                             │                                               │
│                      ┌──────▼───────┐                                      │
│                      │ Step 5: Day 14│                                     │
│                      │ "Trial ending"│                                     │
│                      └──────────────┘                                      │
│                                                                             │
│  ┌──────────────────┐                                                      │
│  │ Onboarding Event │                                                      │
│  │ Webhook          │                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐                                                      │
│  │ Track Milestone  │                                                      │
│  │ Update Progress  │                                                      │
│  │ Slack #onboarding│                                                      │
│  └──────────────────┘                                                      │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  MRR TRACKING & RE-ENGAGEMENT                                              │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────┐                                                          │
│  │ Daily MRR    │                                                          │
│  │ Snapshot     │                                                          │
│  │ (2 AM cron)  │                                                          │
│  └──────┬───────┘                                                          │
│         │                                                                   │
│  ┌──────▼───────┐                                                          │
│  │ Query Active │                                                          │
│  │ Subscriptions│                                                          │
│  │ Calculate MRR│                                                          │
│  └──────┬───────┘                                                          │
│         │                                                                   │
│  ┌──────▼───────┐    ┌──────────────┐                                      │
│  │ Store Snapshot│   │ Slack #metrics│                                     │
│  └──────────────┘    └──────────────┘                                      │
│                                                                             │
│  ┌──────────────┐                                                          │
│  │ Daily Usage  │                                                          │
│  │ Check        │                                                          │
│  │ (9 AM cron)  │                                                          │
│  └──────┬───────┘                                                          │
│         │                                                                   │
│  ┌──────▼───────┐                                                          │
│  │ Classify     │                                                          │
│  │ Users        │                                                          │
│  │ → at_risk    │                                                          │
│  │ → churn_risk │                                                          │
│  │ → power_user │                                                          │
│  └──────┬───────┘                                                          │
│         │                                                                   │
│  ┌──────▼───────┐                                                          │
│  │ Send Targeted│                                                          │
│  │ Emails       │                                                          │
│  │ → trial_nudge│                                                          │
│  │ → win_back   │                                                          │
│  │ → upsell     │                                                          │
│  └──────────────┘                                                          │
│                                                                             │
│  ERROR HANDLING (every branch)                                              │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │ Error Trigger → Log to workflow_errors → Slack #ops-alerts   │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Node-by-Node Specification

| # | Node Name | Type | Config |
|---|-----------|------|--------|
| 1 | **Stripe Webhook** | `webhook` | `POST /stripe`, `responseMode: lastNode`, `options.rawBody: true` |
| 2 | **HMAC Verify** | `code` | Verify `stripe-signature` header using `stripe.webhooks.constructEvent()` |
| 3 | **Event Type Router** | `switch` | Route on `{{eventType}}`: `checkout.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`, `customer.updated` |
| 4 | **Process Checkout** | `code` | Extract: customer, subscription, amount, currency, plan from `data.object` |
| 5 | **Create Customer Record** | `postgres` | `INSERT INTO customers (stripe_customer_id, email, plan, status) ... ON CONFLICT UPDATE` |
| 6 | **Send Welcome Email** | `sendEmail` | Welcome template: login URL, plan details, onboarding link |
| 7 | **Welcome Slack** | `slack` | `#team`: "New signup: {name} ({email}) — {plan}" |
| 8 | **Process Sub Update** | `code` | Extract: subscriptionId, customerId, status, plan, currentPeriodEnd, cancelAtPeriodEnd |
| 9 | **Update Subscription** | `postgres` | `UPDATE subscriptions SET plan=$1, status=$2, current_period_end=$3 WHERE stripe_subscription_id=$4` |
| 10 | **Process Sub Cancel** | `code` | Extract: customerId, cancellationReason, churnedAt |
| 11 | **Record Cancellation** | `postgres` | `UPDATE customers SET status='churned', churned_at=NOW() WHERE id=$1` |
| 12 | **Send Cancellation Email** | `sendEmail` | Acknowledgment + feedback survey link |
| 13 | **Process Invoice** | `code` | Extract: invoiceId, customerId, amount, status, hostedInvoiceUrl, invoicePdf |
| 14 | **Send Invoice Receipt** | `sendEmail` | Invoice receipt with PDF link |
| 15 | **Process Payment Success** | `code` | Log successful payment, reset failure counter |
| 16 | **Process Failed Payment** | `code` | Extract: paymentIntentId, customerId, amount, lastError, attemptCount |
| 17 | **Start Recovery Sequence** | `code` | Schedule: Day 1 email, Day 3 email, Day 7 email, then cancel |
| 18 | **Send Recovery Email** | `sendEmail` | Payment failure notice with update payment link |
| 19 | **User Signup Webhook** | `webhook` | `POST /user-signup` |
| 20 | **Create Account** | `code` | Generate account + subscription + tier config |
| 21 | **Persist Account** | `postgres` | `INSERT INTO customers, subscriptions` |
| 22 | **Onboarding Sequence Builder** | `code` | Generate 5 onboarding steps with scheduled dates |
| 23 | **Onboarding Event Webhook** | `webhook` | `POST /onboarding-event` |
| 24 | **Track Milestone** | `postgres` | `UPDATE onboarding_progress SET current_step=$1, milestones=...` |
| 25 | **Daily MRR Snapshot** | `scheduleTrigger` | `0 2 * * *` UTC |
| 26 | **Calculate MRR** | `postgres` | `SELECT plan, SUM(mrr) as total, COUNT(*) as count FROM customers WHERE status='active' GROUP BY plan` |
| 27 | **Store Snapshot** | `postgres` | `INSERT INTO revenue_snapshots` |
| 28 | **Daily Usage Check** | `scheduleTrigger` | `0 9 * * *` UTC |
| 29 | **Classify Users** | `postgres` | Query users, classify by days-since-login and action count |
| 30 | **Send Re-engagement** | `sendEmail` | Targeted email based on classification |

### Data Flow

```
Stripe Event → Webhook → HMAC Verify → Event Router
  ├─ checkout.completed → Create customer → Welcome email → Slack
  ├─ sub.updated → Update subscription → MRR recalc
  ├─ sub.deleted → Record cancellation → Cancel email → Slack #churn
  ├─ invoice.paid → Send receipt → Log payment
  ├─ invoice.payment_failed → Start recovery (Day 1/3/7 emails) → Cancel if unresolvable
  └─ customer.updated → Update customer record

Signup → Create account + subscription → Welcome email → Onboarding sequence (5 steps)

Daily 2 AM → Query active subs → Calculate MRR → Store snapshot → Slack #metrics
Daily 9 AM → Classify users → Send re-engagement emails (trial nudge / win-back / upsell)
```

### Error Handling

| Error Type | Handler | Action |
|------------|---------|--------|
| HMAC verification failure | Return 400 | Log security event, do not process |
| Stripe API error | Retry 3x with exponential backoff | Then log to `workflow_errors` |
| PostgreSQL write failure | Error Trigger → Slack #ops-alerts | Critical: payment data integrity at risk |
| Email send failure | Retry 3x | Then log, do not block billing flow |
| Invalid event type | Switch node default | Log and ignore unknown events |
| Missing required fields | Code node validation | Return early, log warning |

### Retry Strategy

| Node | Retries | Backoff | Timeout |
|------|---------|---------|---------|
| Stripe API calls | 3 | Exponential: 2s, 8s, 30s | 30s per attempt |
| PostgreSQL | 2 | Linear: 3s, 6s | 10s per attempt |
| Email (SMTP) | 3 | Exponential: 30s, 60s, 120s | 15s per attempt |
| Slack | 2 | Linear: 5s, 10s | 10s per attempt |

### Monitoring Strategy

- **Execution Log**: Every Stripe event processed logged with event type, customer ID, outcome
- **MRR Dashboard**: Real-time MRR, ARR, net new MRR, churn rate, expansion revenue
- **Payment Failure Rate**: Alert if >5% of payments fail in any 24h period
- **Churn Rate**: Daily churn calculation, alert if >2% monthly
- **Revenue Slack Channel**: Every MRR change >$100 triggers notification

### Security Considerations

- **Stripe Webhook HMAC**: Always verify `stripe-signature` header before processing
- **Idempotency**: Use `stripe_subscription_id` as dedup key for subscription events
- **PCI Compliance**: No card data stored in n8n — Stripe handles all card data
- **Webhook Secret**: Stored in n8n credential vault, never in code
- **Audit Trail**: Every payment event logged with timestamp, amount, customer

### Scaling Considerations

- Stripe webhooks deliver at most ~100/sec — n8n queue mode handles this
- MRR calculation uses database aggregation, not in-memory
- Email sending via transactional provider (SendGrid/Mailgun) for deliverability
- Onboarding emails scheduled via n8n Wait nodes (survive n8n restarts)
- Recovery sequence uses date-based branching, not timer nodes

---

## 10. WORKFLOW 3: QUANTIVE PLATFORM & AI

### Purpose
Ingest market data, run prediction models, process watchlist alerts, analyze news, track model health, monitor API endpoints, and generate weekly market reports.

### Trigger
- Schedule: Market data poll (every 5 min)
- Schedule: News poll (every 15 min)
- Schedule: API health check (hourly)
- Schedule: Weekly market report (Monday 8 AM)
- `POST /webhook/watchlist-event` — Watchlist trigger hit
- `POST /webhook/stock-event` — Stock event detected
- `POST /webhook/model-error` — Model error reported

### Applications Used
- **HTTP Request** — FRED API, Treasury.gov, World Bank, news APIs
- **PostgreSQL** — Market data, predictions, news storage
- **Slack** — Market alerts, model health, news digests
- **Ollama/OpenAI** — AI summaries, sentiment analysis

### Complete Node Architecture (22 nodes)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   WF-3: QUANTIVE PLATFORM & AI                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  MARKET DATA INGESTION                                                     │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────────┐                                                      │
│  │ Market Data Poll │                                                      │
│  │ Every 5 min      │                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐    ┌──────────────────┐                              │
│  │ FRED API         │    │ Treasury.gov API │                              │
│  │ Fetch: DFF,      │    │ Fetch: yield     │                              │
│  │ T10Y2Y, CPI      │    │ curve rates      │                              │
│  └──────┬───────────┘    └──────┬───────────┘                              │
│         │                       │                                           │
│  ┌──────▼───────────────────────▼─────┐                                    │
│  │ Merge + Validate                    │                                    │
│  │ (Check freshness, completeness)     │                                    │
│  └──────┬──────────────────────────────┘                                    │
│         │                                                                   │
│  ┌──────▼───────────┐                                                      │
│  │ Data Quality     │                                                      │
│  │ Scorer           │                                                      │
│  │ (freshness,      │                                                      │
│  │  completeness,   │                                                      │
│  │  accuracy)       │                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐    ┌──────────────────┐                              │
│  │ Store to         │    │ If quality < 0.8 │                              │
│  │ PostgreSQL       │    │ → Alert #ops     │                              │
│  └──────┬───────────┘    └──────────────────┘                              │
│         │                                                                   │
│  ┌──────▼───────────┐                                                      │
│  │ Run Prediction   │                                                      │
│  │ Models           │                                                      │
│  │ (yield_curve,    │                                                      │
│  │  inflation,      │                                                      │
│  │  rate_projection)│                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐                                                      │
│  │ Generate Alerts  │                                                      │
│  │ (threshold-based)│                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐    ┌──────────────────┐                              │
│  │ Slack            │    │ Store Predictions│                              │
│  │ #market-alerts   │    │ to PostgreSQL    │                              │
│  └──────────────────┘    └──────────────────┘                              │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  WATCHLIST PROCESSING                                                      │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────────┐                                                      │
│  │ Watchlist Webhook│                                                      │
│  │ POST /watchlist  │                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐                                                      │
│  │ Alert Processor  │                                                      │
│  │ → price_alert    │                                                      │
│  │ → news_alert     │                                                      │
│  │ → volume_alert   │                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐                                                      │
│  │ Slack            │                                                      │
│  │ #watchlist-alerts│                                                      │
│  └──────────────────┘                                                      │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  NEWS INGESTION                                                            │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────────┐                                                      │
│  │ News Poll        │                                                      │
│  │ Every 15 min     │                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐                                                      │
│  │ Fetch News APIs  │                                                      │
│  │ (Reuters, Fed)   │                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐                                                      │
│  │ AI Sentiment     │                                                      │
│  │ Analysis         │                                                      │
│  │ (Ollama/GPT)     │                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐                                                      │
│  │ Relevance Filter │                                                      │
│  │ (keyword + AI)   │                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐    ┌──────────────────┐                              │
│  │ Store +          │    │ If relevance>0.7 │                              │
│  │ Slack #news-feed │    │ → Slack digest   │                              │
│  └──────────────────┘    └──────────────────┘                              │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  STOCK EVENTS & MODEL HEALTH                                               │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐                              │
│  │ Stock Event      │    │ Model Error      │                              │
│  │ Webhook          │    │ Webhook          │                              │
│  └──────┬───────────┘    └──────┬───────────┘                              │
│         │                       │                                           │
│  ┌──────▼───────────┐    ┌──────▼───────────┐                              │
│  │ Match + Explain  │    │ Severity         │                              │
│  │ → Slack          │    │ Classifier       │                              │
│  │ → Store          │    │ → Slack #models   │                              │
│  └──────────────────┘    │ → Update health   │                              │
│                          └──────────────────┘                              │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  API HEALTH & REPORTING                                                    │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐                              │
│  │ API Health Check │    │ Weekly Report    │                              │
│  │ Every hour       │    │ Mon 8 AM         │                              │
│  └──────┬───────────┘    └──────┬───────────┘                              │
│         │                       │                                           │
│  ┌──────▼───────────┐    ┌──────▼───────────┐                              │
│  │ Ping endpoints   │    │ Aggregate week's │                              │
│  │ Measure latency  │    │ predictions      │                              │
│  │ Check status     │    │ accuracy, alerts │                              │
│  └──────┬───────────┘    └──────┬───────────┘                              │
│         │                       │                                           │
│  ┌──────▼───────────┐    ┌──────▼───────────┐                              │
│  │ If unhealthy:    │    │ Email + Slack    │                              │
│  │ → Slack #ops     │    │ #market-data     │                              │
│  └──────────────────┘    └──────────────────┘                              │
│                                                                             │
│  ERROR HANDLING                                                            │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │ Error Trigger → Log → Slack #ops-alerts                       │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Node-by-Node Specification

| # | Node Name | Type | Config |
|---|-----------|------|--------|
| 1 | **Market Data Poll** | `scheduleTrigger` | `*/5 * * * *` (every 5 min) |
| 2 | **Fetch FRED Data** | `httpRequest` | `GET https://api.stlouisfed.org/fred/series/observations?series_id=DFF&api_key={{FRED_KEY}}&file_type=json` |
| 3 | **Fetch Treasury Yields** | `httpRequest` | `GET https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/avg_interest_rates?sort=-record_date&page[size]=10` |
| 4 | **Merge + Validate** | `code` | Merge arrays, validate all required fields present, check timestamps < 1 hour old |
| 5 | **Data Quality Scorer** | `code` | Score 0-1 based on: freshness (0.4), completeness (0.3), consistency (0.3) |
| 6 | **Store Market Data** | `postgres` | `INSERT INTO market_data (source, data, quality_score, fetched_at)` |
| 7 | **Run Predictions** | `code` | Calculate yield curve forecast, inflation projection, rate outlook using stored market data |
| 8 | **Generate Alerts** | `code` | Threshold-based: rate change > 1% → high, > 2% → critical |
| 9 | **Slack Market Alerts** | `slack` | `#market-alerts`: severity + model + confidence |
| 10 | **Watchlist Webhook** | `webhook` | `POST /watchlist` |
| 11 | **Watchlist Processor** | `code` | Route: price_alert (check threshold), news_alert (check relevance), volume_alert |
| 12 | **Slack Watchlist** | `slack` | `#watchlist-alerts`: symbol + change + price |
| 13 | **News Poll** | `scheduleTrigger` | `*/15 * * * *` (every 15 min) |
| 14 | **Fetch News** | `httpRequest` | `GET https://newsapi.org/v2/everything?q=debt+bonds+rates&apiKey={{NEWS_KEY}}` |
| 15 | **AI Sentiment** | `httpRequest` | `POST {{OLLAMA_URL}}/api/generate` with sentiment prompt |
| 16 | **Relevance Filter** | `code` | Filter: keyword match (0.3) + AI relevance (0.7) > 0.7 threshold |
| 17 | **Stock Event Webhook** | `webhook` | `POST /stock-event` |
| 18 | **Stock Processor** | `code` | Match symbol, generate explanation, classify action |
| 19 | **Model Error Webhook** | `webhook` | `POST /model-error` |
| 20 | **Error Classifier** | `code` | Severity: errorRate > 10% → critical, > 5% → high, else medium |
| 21 | **API Health Check** | `scheduleTrigger` | `0 * * * *` (hourly) |
| 22 | **Health Ping** | `httpRequest` | `GET {{BASE_URL}}/health` for each endpoint, measure latency |
| 23 | **Weekly Report** | `scheduleTrigger` | `0 8 * * 1` (Monday 8 AM) |
| 24 | **Aggregate Report** | `postgres` | Query: predictions count, avg confidence, accuracy, alerts triggered |

### Data Flow

```
Every 5 min: FRED + Treasury APIs → Merge → Quality Check → Store → Predictions → Alerts → Slack
Every 15 min: News APIs → AI Sentiment → Relevance Filter → Store + Slack digest
Webhook: Watchlist event → Threshold check → Slack alert
Webhook: Stock event → Match + explain → Slack + store
Webhook: Model error → Classify severity → Slack + update health
Hourly: API endpoint pings → Latency check → Alert if degraded
Weekly: Aggregate metrics → Email + Slack report
```

### Error Handling

| Error Type | Handler | Action |
|------------|---------|--------|
| FRED API timeout | Retry 3x, then use cached data | Log warning, continue with stale data |
| Treasury API error | Retry 3x, then skip | Log, alert if 3 consecutive failures |
| News API rate limit | Exponential backoff | Reduce poll frequency temporarily |
| Ollama/OpenAI timeout | Retry 2x, then skip sentiment | Log, continue with keyword-only relevance |
| PostgreSQL write failure | Error Trigger → Slack #ops | Critical: data pipeline broken |
| Model error webhook | Validate payload | Log and ignore malformed events |

### Retry Strategy

| Node | Retries | Backoff | Timeout |
|------|---------|---------|---------|
| FRED API | 3 | Exponential: 10s, 30s, 90s | 30s per attempt |
| Treasury API | 3 | Exponential: 10s, 30s, 90s | 30s per attempt |
| News API | 3 | Exponential: 15s, 45s, 120s | 20s per attempt |
| Ollama/OpenAI | 2 | Linear: 10s, 30s | 60s per attempt (AI is slow) |
| PostgreSQL | 2 | Linear: 5s, 10s | 10s per attempt |

### Monitoring Strategy

- **Data Freshness**: Alert if market data > 30 min old
- **Prediction Accuracy**: Track vs actuals, alert if accuracy drops below 75%
- **API Latency**: Alert if any endpoint > 500ms or unhealthy
- **Model Error Rate**: Alert if any model error rate > 5%
- **News Coverage**: Alert if no news ingested in 1 hour during market hours

### Security Considerations

- All API keys stored in n8n credential vault
- FRED/Treasury keys rotated quarterly
- Ollama runs locally (no data leaves network)
- News API usage within rate limits
- PostgreSQL connections use SSL
- No sensitive data in Slack messages (use customer IDs, not names)

### Scaling Considerations

- Market data: 5-min poll is sufficient for government debt (not HFT)
- News: 15-min poll with relevance filtering reduces storage
- Predictions: Run as separate Python process, n8n triggers and reads results
- API health: Parallel HTTP requests for all endpoints
- Weekly report: Use database aggregation, not in-memory

---

## 11. WORKFLOW 4: OPERATIONS & INTERNAL MANAGEMENT

### Purpose
Handle all internal operations: revenue/pipeline/demo/user reporting, support ticketing with SLA, customer health scoring, churn alerts, team notifications, task management, contract workflows, backup monitoring, security scanning, and error monitoring.

### Trigger
- Schedule: Daily revenue report (9 AM)
- Schedule: Weekly MRR breakdown (Monday 10 AM)
- Schedule: Daily pipeline report (9 AM)
- Schedule: Daily demo report (5 PM)
- Schedule: Daily user activity (8 AM)
- Schedule: Daily prediction performance (8 AM)
- Schedule: System health check (every 30 min)
- Schedule: SLA monitoring (hourly)
- Schedule: Escalation check (6 PM)
- Schedule: Weekly team report (Friday 5 PM)
- Schedule: Nightly backup (midnight)
- Schedule: Security monitor (every 15 min)
- Schedule: Error monitor (every 5 min)
- `POST /webhook/customer-health` — Customer health update
- `POST /webhook/churn-alert` — Churn risk detected
- `POST /webhook/support-ticket` — New support ticket
- `POST /webhook/team-event` — Team event (deploy, incident, release)
- `POST /webhook/task-created` — New task created
- `POST /webhook/meeting-request` — Meeting requested
- `POST /webhook/document-created` — Document created
- `POST /webhook/contract-event` — Contract status change
- `POST /webhook/campaign-event` — Marketing campaign event

### Applications Used
- **PostgreSQL** — All data persistence
- **Slack** — All team/support/ops notifications
- **SMTP** — Customer emails (health check-ins, SLA breach notices)
- **HTTP Request** — System health endpoints, backup verification

### Complete Node Architecture (30 nodes)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               WF-4: OPERATIONS & INTERNAL MANAGEMENT                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  REVENUE & METRICS REPORTING                                               │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │ Daily Revenue│  │ Weekly MRR   │  │ Daily        │                      │
│  │ 9 AM         │  │ Mon 10 AM    │  │ Pipeline     │                      │
│  └──────┬───────┘  └──────┬───────┘  │ 9 AM         │                      │
│         │                  │          └──────┬───────┘                      │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐                      │
│  │ Query        │  │ Query        │  │ Query        │                      │
│  │ Revenue      │  │ Subscriptions│  │ Deals by     │                      │
│  │ Metrics      │  │ by Plan      │  │ Stage        │                      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                      │
│         │                  │                  │                              │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐                      │
│  │ Slack        │  │ Slack        │  │ Slack        │                      │
│  │ #metrics     │  │ #metrics     │  │ #sales       │                      │
│  └──────────────┘  └──────────────┘  └──────────────┘                      │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │ Daily Demo   │  │ Daily User   │  │ Daily        │                      │
│  │ 5 PM         │  │ Activity     │  │ Prediction   │                      │
│  └──────┬───────┘  │ 8 AM         │  │ Performance  │                      │
│         │          └──────┬───────┘  │ 8 AM         │                      │
│  ┌──────▼───────┐  ┌──────▼───────┐  └──────┬───────┘                      │
│  │ Query Demo   │  │ Query DAU/   │  ┌──────▼───────┐                      │
│  │ Metrics      │  │ WAU/Signups  │  │ Query Model  │                      │
│  └──────┬───────┘  └──────┬───────┘  │ Accuracy     │                      │
│         │                  │          └──────┬───────┘                      │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐                      │
│  │ Slack        │  │ Slack        │  │ Slack        │                      │
│  │ #sales       │  │ #product     │  │ #models      │                      │
│  └──────────────┘  └──────────────┘  └──────────────┘                      │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  CUSTOMER HEALTH & CHURN                                                   │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐                              │
│  │ Customer Health  │    │ Churn Alert      │                              │
│  │ Webhook          │    │ Webhook          │                              │
│  └──────┬───────────┘    └──────┬───────────┘                              │
│         │                       │                                           │
│  ┌──────▼───────────┐    ┌──────▼───────────┐                              │
│  │ Calculate Health │    │ Process Churn    │                              │
│  │ Score:           │    │ Risk:            │                              │
│  │ usage*0.3 +      │    │ → Slack #churn   │                              │
│  │ engagement*0.3 + │    │ → Update DB      │                              │
│  │ support*0.2 +    │    │ → Trigger win-   │                              │
│  │ billing*0.2      │    │   back sequence  │                              │
│  └──────┬───────────┘    └──────────────────┘                              │
│         │                                                                   │
│  ┌──────▼───────────┐                                                      │
│  │ Route by Status: │                                                      │
│  │ healthy → log    │                                                      │
│  │ at_risk → Slack  │                                                      │
│  │ critical → Slack │                                                      │
│  │ + email CSM      │                                                      │
│  └──────────────────┘                                                      │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  SUPPORT TICKETS & SLA                                                     │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────────┐                                                      │
│  │ Support Ticket   │                                                      │
│  │ Webhook          │                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐                                                      │
│  │ Classify:        │                                                      │
│  │ bug → high, 4h   │                                                      │
│  │ feature → med,24h│                                                      │
│  │ question → low,  │                                                      │
│  │              48h  │                                                      │
│  │ billing → med,   │                                                      │
│  │              24h  │                                                      │
│  └──────┬───────────┘                                                      │
│         │                                                                   │
│  ┌──────▼───────────┐    ┌──────────────────┐                              │
│  │ Persist +        │    │ SLA Monitor      │                              │
│  │ Slack #support   │    │ Every hour       │                              │
│  └──────────────────┘    └──────┬───────────┘                              │
│                                 │                                           │
│                          ┌──────▼───────────┐                              │
│                          │ Check tickets    │                              │
│                          │ approaching or   │                              │
│                          │ breaching SLA    │                              │
│                          └──────┬───────────┘                              │
│                                 │                                           │
│                          ┌──────▼───────────┐                              │
│                          │ Slack #support   │                              │
│                          │ Breach: 🚨       │                              │
│                          │ Warning: ⚠️      │                              │
│                          └──────────────────┘                              │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  TEAM WORKFLOWS                                                            │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Team Event   │  │ Task Created │  │ Meeting      │  │ Document     │   │
│  │ Webhook      │  │ Webhook      │  │ Request      │  │ Created      │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                  │                  │                  │           │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐   │
│  │ Route by     │  │ Set Priority │  │ Calendar API │  │ Route by     │   │
│  │ type:        │  │ + SLA        │  │ Create Event │  │ type:        │   │
│  │ deploy →     │  └──────┬───────┘  └──────┬───────┘  │ contract →   │   │
│  │ incident →   │         │                  │          │ proposal →   │   │
│  │ release →    │  ┌──────▼───────┐  ┌──────▼───────┐  │ report →     │   │
│  │ update       │  │ Slack #tasks │  │ Slack        │  │ spec →       │   │
│  └──────┬───────┘  └──────────────┘  │ #meetings    │  └──────┬───────┘   │
│         │                             └──────────────┘         │           │
│  ┌──────▼───────┐                                    ┌──────▼───────┐   │
│  │ Slack        │                                    │ Slack        │   │
│  │ #deployments │                                    │ #documents   │   │
│  │ #incidents   │                                    └──────────────┘   │
│  │ #releases    │                                                        │
│  └──────────────┘                                                        │
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐                                     │
│  │ Contract     │    │ Campaign     │                                     │
│  │ Event        │    │ Event        │                                     │
│  │ Webhook      │    │ Webhook      │                                     │
│  └──────┬───────┘    └──────┬───────┘                                     │
│         │                   │                                              │
│  ┌──────▼───────┐    ┌──────▼───────┐                                     │
│  │ Status       │    │ Route by     │                                     │
│  │ Router:      │    │ type:        │                                     │
│  │ draft→review │    │ launch →     │                                     │
│  │ review→approve│   │ weekly →     │                                     │
│  │ approve→sign │    │ webinar →    │                                     │
│  │ sign→active  │    │ promo →      │                                     │
│  └──────┬───────┘    └──────┬───────┘                                     │
│         │                   │                                              │
│  ┌──────▼───────┐    ┌──────▼───────┐                                     │
│  │ Email notify │    │ Slack        │                                     │
│  │ reviewers    │    │ #marketing   │                                     │
│  │ + Slack      │    └──────────────┘                                     │
│  │ #contracts   │                                                          │
│  └──────────────┘                                                          │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════     │
│  INFRASTRUCTURE MONITORING                                                 │
│  ═══════════════════════════════════════════════════════════════════════     │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ System Health│  │ Weekly Team  │  │ Nightly      │  │ Security     │   │
│  │ Every 30 min │  │ Fri 5 PM     │  │ Backup       │  │ Every 15 min │   │
│  └──────┬───────┘  └──────┬───────┘  │ Midnight     │  └──────┬───────┘   │
│         │                  │          └──────┬───────┘         │           │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┐   │
│  │ Query        │  │ Query        │  │ Trigger      │  │ Scan:        │   │
│  │ CPU/Memory/  │  │ Tasks:       │  │ pg_dump      │  │ failed       │   │
│  │ Disk/Error   │  │ completed/   │  │ Verify       │  │ logins,      │   │
│  │ Rate         │  │ in_progress/ │  │ integrity    │  │ suspicious   │   │
│  └──────┬───────┘  │ blocked      │  └──────┬───────┘  │ IPs, rate    │   │
│         │          └──────┬───────┘         │          │ limit hits   │   │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼───────┘  └──────┬───────┘   │
│  │ Alert if     │  │ Slack #team  │  │ Slack #ops      ┌──────▼───────┐   │
│  │ CPU>80%      │  │              │  │ (success/fail)  │ Alert if     │   │
│  │ Mem>80%      │  └──────────────┘  └─────────────────  │ >threshold  │   │
│  │ Error>3%     │                                        │ Slack        │   │
│  └──────────────┘                                        │ #security    │   │
│                                                          └──────────────┘   │
│  ┌──────────────┐                                                          │
│  │ Error Monitor│                                                          │
│  │ Every 5 min  │                                                          │
│  └──────┬───────┘                                                          │
│         │                                                                   │
│  ┌──────▼───────┐                                                          │
│  │ Scan service │                                                          │
│  │ error rates  │                                                          │
│  │ + latency    │                                                          │
│  └──────┬───────┘                                                          │
│         │                                                                   │
│  ┌──────▼───────┐                                                          │
│  │ Alert if     │                                                          │
│  │ error > 2%   │                                                          │
│  │ Slack #ops   │                                                          │
│  └──────────────┘                                                          │
│                                                                             │
│  ERROR HANDLING                                                            │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │ Error Trigger → Log → Slack #ops-alerts                       │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Node-by-Node Specification

| # | Node Name | Type | Schedule/Path | Config |
|---|-----------|------|---------------|--------|
| 1 | **Daily Revenue** | `scheduleTrigger` | `0 9 * * *` | Query: MRR, new deals, closed revenue, churned customers |
| 2 | **Weekly MRR** | `scheduleTrigger` | `0 10 * * 1` | Query: subscriptions by plan, net new MRR, growth rate |
| 3 | **Daily Pipeline** | `scheduleTrigger` | `0 9 * * *` | Query: deals by stage, weighted pipeline, conversion rate |
| 4 | **Daily Demos** | `scheduleTrigger` | `0 17 * * *` | Query: demos scheduled/completed/converted, avg rating |
| 5 | **Daily Users** | `scheduleTrigger` | `0 8 * * *` | Query: DAU, WAU, signups, churn, feature adoption |
| 6 | **Daily Predictions** | `scheduleTrigger` | `0 8 * * *` | Query: model accuracy, total predictions, confidence |
| 7 | **System Health** | `scheduleTrigger` | `*/30 * * * *` | Query: CPU, memory, disk, error rate, DB connections |
| 8 | **SLA Monitor** | `scheduleTrigger` | `0 * * * *` | Query: tickets approaching/breaching SLA |
| 9 | **Escalation Check** | `scheduleTrigger` | `0 18 * * *` | Query: tickets with escalation level > 1 |
| 10 | **Weekly Team** | `scheduleTrigger` | `0 17 * * 5` | Query: tasks completed/in-progress/blocked, velocity |
| 11 | **Nightly Backup** | `scheduleTrigger` | `0 0 * * *` | Trigger: pg_dump, verify checksum |
| 12 | **Security Scan** | `scheduleTrigger` | `*/15 * * * *` | Query: failed logins, suspicious IPs, rate limits |
| 13 | **Error Monitor** | `scheduleTrigger` | `*/5 * * * *` | Query: service error rates, latency |
| 14 | **Customer Health** | `webhook` | `POST /customer-health` | Calculate weighted health score |
| 15 | **Churn Alert** | `webhook` | `POST /churn-alert` | Process churn risk, trigger win-back |
| 16 | **Support Ticket** | `webhook` | `POST /support-ticket` | Classify, prioritize, set SLA |
| 17 | **Team Event** | `webhook` | `POST /team-event` | Route: deploy/incident/release/update |
| 18 | **Task Created** | `webhook` | `POST /task-created` | Set priority + SLA, notify |
| 19 | **Meeting Request** | `webhook` | `POST /meeting-request` | Create calendar event, notify |
| 20 | **Document Created** | `webhook` | `POST /document-created` | Route by type, assign reviewers |
| 21 | **Contract Event** | `webhook` | `POST /contract-event` | Status transition, notify |
| 22 | **Campaign Event** | `webhook` | `POST /campaign-event` | Route by type, notify marketing |

### Data Flow

```
Scheduled Reports (9 AM - 6 PM):
  Query PostgreSQL → Format → Slack channel → Store snapshot

Customer Health:
  Webhook → Calculate score → Route (healthy/at_risk/critical) → Slack + email

Churn:
  Webhook → Record risk → Slack #churn → Trigger win-back

Support Tickets:
  Webhook → Classify → Set SLA → Persist → Slack #support
  Hourly: Check SLA → Alert breaches → Slack #support
  6 PM: Check escalations → Alert → Slack #ops-alerts

Team Workflows:
  Webhook → Route by type → Generate notification → Slack channel

Infrastructure:
  30 min: System health → Alert if degraded → Slack #ops
  15 min: Security scan → Alert if threats → Slack #security
  5 min: Error monitor → Alert if high error rate → Slack #ops
  Midnight: Backup → Verify → Alert if failed → Slack #ops
  Friday: Team report → Slack #team
```

### Error Handling

| Error Type | Handler | Action |
|------------|---------|--------|
| PostgreSQL query failure | Error Trigger → Slack #ops | Critical: all reporting halted |
| Slack API failure | Retry 2x, then log | Non-critical: continue |
| Backup failure | Immediate Slack #ops alert | Critical: data loss risk |
| Security threshold breach | Immediate Slack #security | Critical: potential attack |
| Webhook payload invalid | Validate + return 400 | Log, do not process |
| Calendar API failure | Retry 2x, then Slack #team | Fallback: manual scheduling |

### Retry Strategy

| Node | Retries | Backoff | Timeout |
|------|---------|---------|---------|
| PostgreSQL queries | 2 | Linear: 5s, 10s | 15s per attempt |
| Slack messages | 2 | Linear: 5s, 10s | 10s per attempt |
| HTTP health checks | 3 | Exponential: 5s, 15s, 45s | 10s per attempt |
| Backup verification | 2 | Linear: 30s, 60s | 300s per attempt |

### Monitoring Strategy

- **Report Delivery**: Track if all daily reports sent successfully
- **SLA Compliance**: Dashboard showing SLA breach rate, avg resolution time
- **Ticket Volume**: Trending ticket count by category, priority
- **System Health Dashboard**: Real-time CPU, memory, disk, error rate
- **Security Dashboard**: Failed login trend, suspicious IP list, rate limit abuse
- **Backup Status**: Success/failure rate, backup size trend, restore test schedule

### Security Considerations

- Webhook endpoints authenticated via HMAC or API key
- Security scanner runs independently with elevated read-only access
- Backup encrypted at rest (AES-256) and in transit (TLS)
- SLA data retained for compliance audit trail
- Support ticket PII masked in Slack messages
- Calendar events use service account, not personal accounts

### Scaling Considerations

- Scheduled reports use database materialized views for performance
- SLA monitoring uses indexed queries on `created_at` + `sla_deadline`
- Security scanner can be distributed across multiple n8n workers
- Backup uses `pg_dump` with parallel compression
- Error monitor aggregates before alerting (avoid alert storms)

---

## 12. DATABASE SCHEMA RECOMMENDATIONS

See Section 7.3 for complete SQL schema. Key design decisions:

- **UUID primary keys** for all tables (distributed-safe)
- **JSONB columns** for flexible data (market_data, predictions, milestones)
- **Timestamptz** for all timestamps (timezone-safe)
- **Partitioning** on `workflow_executions` and `audit_log` by month
- **Indexes** on: email, customer_id, plan, status, created_at, event_type
- **Row-level security** for multi-tenant data isolation
- **Soft deletes** on customers (status='deleted' instead of DELETE)

---

## 13. MONITORING & OBSERVABILITY PLAN

### 13.1 n8n Execution Monitoring

- Enable execution logging to database for all workflows
- Set execution retention: 30 days (completed), 90 days (failed)
- Configure execution webhooks for external monitoring

### 13.2 Metrics to Track

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Workflow execution success rate | n8n | < 95% |
| Average execution duration | n8n | > 30s (webhook) or > 5min (scheduled) |
| Failed execution count (1h) | n8n | > 5 |
| Stripe webhook processing time | Custom | > 10s |
| Email delivery rate | SMTP provider | < 98% |
| Slack message delivery rate | Slack API | < 99% |
| API endpoint latency | Health check | > 500ms |
| Database connection pool usage | PostgreSQL | > 80% |
| Error rate by service | Error monitor | > 2% |
| SLA breach rate | Support tickets | > 5% |
| Backup success rate | Backup monitor | < 100% |
| Security event count (1h) | Security scanner | > 10 |

### 13.3 Alert Escalation

| Level | Channel | Condition |
|-------|---------|-----------|
| P0 Critical | Slack #ops-alerts + PagerDuty | Workflow failures, backup failures, security breaches |
| P1 High | Slack #ops-alerts | API degradation, high error rates, SLA breaches |
| P2 Medium | Slack respective channel | Individual workflow failures, non-critical errors |
| P3 Low | Log only | Transient failures, retries successful |

### 13.4 Dashboards

- **Executive Dashboard**: MRR, ARR, churn rate, customer count, NPS
- **Operations Dashboard**: System health, error rates, SLA compliance, backup status
- **Sales Dashboard**: Lead pipeline, conversion rates, demo metrics, deal velocity
- **Platform Dashboard**: Prediction accuracy, data freshness, API health, model errors

---

## 14. SECURITY & ACCESS-CONTROL PLAN

### 14.1 n8n Access Control

- **Admin access**: Limited to DevOps/SRE team (2-3 people)
- **Workflow edit**: Engineers with specific project access
- **Workflow view**: All team members
- **Execution view**: Admins + relevant team members
- **Credential management**: Admins only, with audit logging

### 14.2 Webhook Security

| Workflow | Authentication Method |
|----------|----------------------|
| WF-1 (Sales) | HMAC-SHA256 signature verification |
| WF-2 (Billing) | Stripe webhook HMAC (`stripe-signature` header) |
| WF-3 (Platform) | API key in `x-api-key` header |
| WF-4 (Operations) | HMAC-SHA256 or API key |

### 14.3 Data Protection

- **Credentials**: Stored in n8n encrypted credential vault, never in workflow code
- **API keys**: Rotated quarterly, stored in credential vault
- **PII**: Encrypted at rest in PostgreSQL, masked in Slack messages
- **Backups**: Encrypted with AES-256, stored in separate region
- **Audit trail**: Every credential access logged

### 14.4 Network Security

- n8n runs in internal network, not publicly accessible
- Webhooks accessible only via reverse proxy (Nginx) with rate limiting
- PostgreSQL accessible only from n8n and backend containers
- Slack/email traffic outbound only (no inbound connections)

---

## 15. DISASTER RECOVERY & BACKUP STRATEGY

### 15.1 n8n Workflow Backup

- **Frequency**: Daily at midnight (automated via WF-4)
- **Method**: n8n export API → JSON files → S3/GCS
- **Retention**: 30 days of daily exports
- **Restore time**: < 5 minutes (import JSON + activate)

### 15.2 Database Backup

- **Frequency**: Daily full backup + hourly WAL archiving
- **Method**: `pg_dump` with parallel compression
- **Retention**: 30 days daily, 12 weeks weekly, 12 months monthly
- **Restore time**: < 30 minutes for full restore
- **Testing**: Monthly restore test to verify backup integrity

### 15.3 Workflow Execution Logs

- **Frequency**: Continuous (real-time replication)
- **Method**: PostgreSQL streaming replication to standby
- **Retention**: 90 days
- **Use case**: Post-incident analysis, compliance audit

### 15.4 Recovery Procedures

| Scenario | RTO | RPO | Procedure |
|----------|-----|-----|-----------|
| n8n crash | 5 min | 0 (queue mode) | Restart container, reimport workflows |
| Database failure | 30 min | 1 hour | Restore from latest backup + WAL replay |
| Complete outage | 2 hours | 1 hour | Full restore: DB → n8n → workflows → activate |
| Workflow corruption | 5 min | 0 | Import latest workflow export |
| Credential leak | 15 min | N/A | Rotate all credentials, reimport |

---

## APPENDIX A: WEBHOOK PAYLOAD FORMATS

### Lead Capture
```json
POST /webhook/lead-capture
{
  "name": "John Smith",
  "email": "john@gov.example",
  "company": "Ministry of Finance",
  "companySize": "201-500",
  "industry": "Government",
  "source": "demo_request",
  "phone": "+1-555-0100",
  "message": "Interested in debt optimization"
}
```

### Stripe Webhook
```json
POST /webhook/stripe
Header: stripe-signature: t=1234567890,v1=abc123...
{
  "id": "evt_...",
  "type": "checkout.session.completed",
  "data": {
    "object": {
      "customer": "cus_...",
      "subscription": "sub_...",
      "amount_total": 19900,
      "currency": "usd",
      "metadata": { "plan": "pro" },
      "customer_details": { "email": "customer@example.com" }
    }
  }
}
```

### Support Ticket
```json
POST /webhook/support-ticket
{
  "ticketId": "t_123",
  "subject": "Cannot access portfolio",
  "category": "bug",
  "customerEmail": "user@gov.example",
  "customerId": "cus_123",
  "description": "Getting 403 error on portfolio page"
}
```

### Model Error
```json
POST /webhook/model-error
{
  "model": "yield_curve",
  "errorType": "prediction_drift",
  "errorRate": 0.08,
  "affectedCount": 45,
  "details": "Predictions diverging from actuals by >2%"
}
```

---

## APPENDIX B: NAMING CONVENTIONS

### Workflow Names
```
WF-1: Quantive — Sales & CRM
WF-2: Quantive — Billing & Customer Lifecycle
WF-3: Quantive — Platform & AI
WF-4: Quantive — Operations & Internal
```

### Node Names
```
Pattern: [Action] [Object] [Qualifier]
Examples:
  ✅ "Fetch FRED Data"
  ✅ "Send Invoice Receipt"
  ✅ "Slack Market Alerts"
  ✅ "PostgreSQL Persist Lead"
  ❌ "Code" (too vague)
  ❌ "Process Data" (too vague)
  ❌ "Node1" (not descriptive)
```

### Webhook Paths
```
Pattern: /webhook/[resource]-[action]
Examples:
  /webhook/lead-capture
  /webhook/stripe
  /webhook/support-ticket
  /webhook/model-error
  /webhook/customer-health
```

### Slack Channels
```
Pattern: #[domain]-[type]
Examples:
  #sales-alerts (deal/lead events)
  #billing-alerts (payment events)
  #market-alerts (market events)
  #ops-alerts (system events)
  #metrics (numeric data)
  #team (team notifications)
```

---

## APPENDIX C: EXECUTION CHECKLIST

### Pre-Deployment
- [ ] All 13 credentials created in n8n
- [ ] All 19 Slack channels created
- [ ] Database schema applied
- [ ] n8n queue mode enabled
- [ ] Webhook URLs configured in external systems (Stripe, website, etc.)
- [ ] Error alert emails configured
- [ ] Test webhooks sent and verified

### Deployment
- [ ] Import WF-2 first (Billing — most critical)
- [ ] Test Stripe webhook with `stripe trigger`
- [ ] Import WF-1 (Sales)
- [ ] Test lead capture webhook
- [ ] Import WF-3 (Platform)
- [ ] Test market data poll
- [ ] Import WF-4 (Operations)
- [ ] Test support ticket webhook
- [ ] Verify all scheduled triggers firing
- [ ] Verify all Slack messages delivering
- [ ] Verify all emails sending

### Post-Deployment
- [ ] Monitor execution success rate for 24h
- [ ] Review error logs
- [ ] Verify MRR calculation matches Stripe dashboard
- [ ] Verify backup completing successfully
- [ ] Run full disaster recovery drill

---

*End of Audit & Redesign Document*
*Total workflows: 4 (consolidated from 4)*
*Total nodes: 95 (reduced from 125 by eliminating mock code nodes)*
*Total triggers: 29 (webhooks + scheduled)*
*Coverage: Sales, Billing, Platform, AI, Support, Management, Security, Operations*

---

## 16. RECONCILIATION — AS-DELIVERED VS DOCUMENTED (POST-IMPLEMENTATION REVIEW)

> Sections 1–15 above are the design audit produced in response to the brief. After the workflows were built, a deep file-level review was performed and the delivered artifacts were hardened to match the documented guarantees. This section records what was actually delivered and every gap that was closed.

### 16.1 Delivered Files

| File | Workflow | Nodes | Description |
|---|---|---|---|
| `workflows/00-error-handler.json` | WF-0 Error Handler | 7 | Central error handler (via `settings.errorWorkflow`) |
| `workflows/01-sales-crm.json` | WF-1 Sales & CRM | 24 | 4 HMAC webhooks + follow-up cron |
| `workflows/02-billing-lifecycle.json` | WF-2 Billing & Lifecycle | 18 | Stripe webhook + MRR daily + re-engagement |
| `workflows/03-platform-ai.json` | WF-3 Platform & AI | 29 | Market/AI, news, watchlist, API health, weekly |
| `workflows/04-operations-internal.json` | WF-4 Operations & Internal | 33 | Digest, weekly, SLA, security, backup, errors, support |
| **Total** | | **111** | 5 files, all validated as importable JSON |

Supporting artifacts: `schemas/database-schema.sql`, `credentials/CREDENTIALS.md`, `README.md`, `.env.example`.

### 16.2 Guarantees Closed Since Original Audit

| # | Gap found in delivered JSON | Fix applied |
|---|---|---|
| 1 | 6 webhooks with zero authentication | WF-1 ×4 internal webhooks + WF-4 support webhook now verify `x-quantive-signature` (HMAC-SHA256 over `JSON.stringify(body)` with `WEBHOOK_SECRET`); WF-2 Stripe webhook verifies `stripe-signature` with 5-min timestamp tolerance and `rawBody` enabled |
| 2 | No workflow wired to error handling | All of WF-1..WF-4 set `settings.errorWorkflow: "wf0-error-handler"` |
| 3 | No retry logic on external calls | `retryOnFail`/`maxTries`/`waitBetweenTries` on WF-3 external-fetch nodes (FRED, NewsAPI, OpenAI, health pings) |
| 4 | No success observability | Every flow terminal writes to `workflows.workflow_executions` (status, duration, metadata) feeding the WF-4 daily digest and error monitor |
| 5 | Missing workflow metadata | `description` + tags added on all 5 workflows |
| 6 | WF-3 `Check API Health` syntax error (`...});n`) | Fixed; validated to parse |
| 7 | WF-3 dead `const postgres = Postgres.main;` in `List Market Instruments` | Removed |
| 8 | WF-2 `Report MRR` `${{ $json.mrr }}` text | Rewritten to safe plain-text expression |
| 9 | WF-2 `Prepare Notification` `totalMRR` undefined for some events | `Track MRR` now always recomputes MRR; `Prepare Notification` defaults (`totalMRR = 0`) |
| 10 | WF-4 `Prepare SLA Alert` crash when no breaches | Guarded (`return []` when `hasBreaches=false`) |
| 11 | WF-4 security/error monitors posting "undefined" when clean | Gated — return `[]` when no alerts/errors |
| 12 | WF-4 `Alert if Urgent` fragile `$('Support Ticket Webhook')` cross-reference | `Create Support Ticket` now returns subject/email/priority on the same item |
| 13 | WF-1 `Get Pending Follow-ups` single `{followups:[]}` item breaking downstream | Query maps rows → items so `[]` flows cleanly |
| 14 | WF-0 `| capitalize` filter (unsupported) | Removed |
| 15 | Slack side-effect nodes could abort flows | `onError: "continueRegularOutput"` on all notification nodes |

### 16.3 Open Deployment Requirements

1. **`Postgres.main` helper** — All DB code nodes use the non-standard global `Postgres.main` (`Postgres.main.query(text, params)`). A bootstrap/plugin that exposes this global using the `postgres-main` credential is a hard deployment prerequisite. Documented in `README.md`.
2. **Webhook signing** — Callers of the internal webhooks must send `x-quantive-signature: HMAC-SHA256(secret=WEBHOOK_SECRET, body=JSON.stringify(payload))` (hex). Stripe requires `STRIPE_WEBHOOK_SECRET` configured.
3. **Slack channels** — The channels listed in Section 16.4 must exist.
4. **Schema** — `schemas/database-schema.sql` must be applied (includes `workflows` schema, `workflow_executions`, `workflow_errors`, and all business tables referenced in the code).

### 16.4 Slack Channels Actually Used

`sales-leads`, `sales-demos`, `sales-closed`, `sales-followups`, `billing-events`, `metrics-daily`, `customer-success`, `market-news`, `watchlist-alerts`, `api-alerts`, `platform-weekly`, `daily-digest`, `weekly-report`, `support-alerts`, `security-alerts`, `ops-notifications`, `platform-alerts`.

### 16.5 Validation Performed

All 5 JSON files are parseable (`ConvertFrom-Json`), every node referenced in `connections` exists, and `settings.errorWorkflow` targets the WF-0 id (`wf0-error-handler`) in all four master workflows. Verification script output:

```
00-error-handler.json : 7 nodes, all connections resolve
01-sales-crm.json     : 24 nodes, all connections resolve
02-billing-lifecycle  : 18 nodes, all connections resolve
03-platform-ai.json   : 29 nodes, all connections resolve
04-operations-internal: 33 nodes, all connections resolve
```
