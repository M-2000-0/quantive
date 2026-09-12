# Quantive n8n Workflows — Setup Guide

## Overview

4 master workflow files containing **61 independent workflows** (413 nodes total) for the Quantive sovereign debt optimization platform.

| File | Size | Nodes | Workflows |
|------|------|-------|-----------|
| `01-stripe-billing.json` | 104.9 KB | 84 | 12 |
| `02-onboarding-support.json` | 81.6 KB | 89 | 14 |
| `03-platform-ai.json` | 91.9 KB | 109 | 14 |
| `04-management-internal.json` | 124.6 KB | 131 | 21 |
| **Total** | **403 KB** | **413** | **61** |

---

## Complete Workflow List

### File 1: Stripe & Billing (12 workflows)

| # | Workflow | Trigger | Purpose |
|---|----------|---------|---------|
| 1 | Stripe Webhook Receiver | Webhook | Routes all Stripe events |
| 2 | Checkout Flow | Stripe event | Handles checkout.session.completed |
| 3 | Subscription Management | Stripe events | Created/updated/deleted handling |
| 4 | Payment Processing | Stripe events | Success/failure handling |
| 5 | Failed-Payment Recovery | Schedule (6h) | Dunning email cadence |
| 6 | Cancellation Handling | Stripe event | Cancellation processing |
| 7 | Upgrade/Downgrade | Stripe events | Plan change handling |
| 8 | Customer Portal | Webhook | Stripe portal session creation |
| 9 | Subscription Status Check | Schedule (1h) | Status monitoring |
| 10 | Revenue Tracking (MRR) | Schedule (daily) | MRR/ARR calculation |
| 11 | Churn Analysis | Schedule (weekly) | Churn metrics |
| 12 | API Error Monitoring | Code | Error classification & alerts |

### File 2: Onboarding & Customer Support (14 workflows)

| # | Workflow | Trigger | Purpose |
|---|----------|---------|---------|
| 1 | Account Creation | Webhook | New user setup |
| 2 | Subscription Activation | After creation | Tier activation |
| 3 | Welcome Email | Immediate | Welcome with links |
| 4 | Login Instructions | Wait 5min | Login guidance |
| 5 | Tier Assignment | Webhook | Feature management |
| 6 | Onboarding Sequence | Schedule (1h) | 5-step drip campaign |
| 7 | Usage Tracking | Schedule (6h) | Usage monitoring |
| 8 | Re-engagement | Schedule (daily) | Inactive user outreach |
| 9 | AI Support | Webhook | Automated support |
| 10 | FAQ Automation | Code | FAQ matching |
| 11 | Ticket Classification | Webhook | Priority routing |
| 12 | Bug Tracking | Webhook | Bug-to-issue pipeline |
| 13 | Payment Support | Webhook | Payment operations |
| 14 | Escalation Alerts | Code | Auto-escalation |

### File 3: Quantive Platform & AI (14 workflows)

| # | Workflow | Trigger | Purpose |
|---|----------|---------|---------|
| 1 | Market Data Ingestion | Schedule (4h) | Treasury/FRED/FX data |
| 2 | Prediction Refreshes | Schedule (2h) | Model predictions |
| 3 | Watchlist Updates | Schedule (1h) | Price monitoring |
| 4 | News Ingestion | Schedule (2h) | News aggregation |
| 5 | Stock/News Matching | Schedule (2h) | News-to-stock matching |
| 6 | Prediction Explanations | Webhook | AI explanations |
| 7 | Model Error Tracking | Schedule (6h) | Error metrics |
| 8 | Data Quality Monitoring | Schedule (1h) | Quality checks |
| 9 | Market Summaries | Schedule (daily 6AM) | Daily market digest |
| 10 | News Summaries | Schedule (daily 6:30AM) | News digest |
| 11 | Stock Explanations | Webhook | Stock analysis |
| 12 | Signal Analysis | Schedule (4h) | Signal strength |
| 13 | Conflicting-Signal Detection | Code | Conflict detection |
| 14 | Daily Reports + Market Alerts | Schedule + Webhook | Reports & alerts |

### File 4: Management & Internal (21 workflows)

| # | Workflow | Trigger | Purpose |
|---|----------|---------|---------|
| 1 | Revenue Dashboard | Schedule (1h) | Revenue metrics |
| 2 | MRR Dashboard | Schedule (1h) | MRR breakdown |
| 3 | Customer Dashboard | Schedule (1h) | Customer metrics |
| 4 | Churn Dashboard | Schedule (6h) | Churn analysis |
| 5 | Sales Pipeline | Schedule (1h) | Pipeline metrics |
| 6 | Demo Tracking | Webhook | Demo management |
| 7 | User Activity | Schedule (1h) | Activity tracking |
| 8 | Prediction Performance | Schedule (daily) | Accuracy metrics |
| 9 | System Monitoring | Schedule (5min) | Health checks |
| 10 | Team Notifications | Webhook | Notification routing |
| 11 | Task Creation | Webhook | Task management |
| 12 | Meeting Scheduling | Webhook | Calendar management |
| 13 | Document Generation | Webhook | Document creation |
| 14 | Contract Workflows | Webhook | Contract lifecycle |
| 15 | Email Automation | Schedule (1h) | Email scheduling |
| 16 | Daily Reports | Schedule (daily 6AM) | Daily team report |
| 17 | Weekly Reports | Schedule (Monday 7AM) | Weekly stakeholder report |
| 18 | Error Alerts | Webhook | Error routing |
| 19 | Backup Monitoring | Schedule (1h) | Backup freshness |
| 20 | Security Monitoring | Schedule (15min) | Security events |
| 21 | Cross-Section Integration Hub | Schedule (daily 8AM) | Executive summary |

---

## Prerequisites

1. **n8n instance** running on Render (or self-hosted)
2. **Quantive backend** running at a reachable URL
3. **PostgreSQL** database accessible from n8n
4. **Slack workspace** with incoming webhooks
5. **SMTP server** for email delivery
6. **Stripe account** with API keys

---

## Step 1: Generate Webhook Secret

```bash
# Generate a shared secret for HMAC verification
openssl rand -hex 32
```

Add this to both:
- n8n environment variables as `QUANTIVE_WEBHOOK_SECRET`
- Quantive backend `.env.production` as `QUANTIVE_WEBHOOK_SECRET`

---

## Step 2: Configure n8n Environment Variables

Set these in your n8n Render dashboard or `.env` file:

```bash
# ── Quantive Backend ──────────────────────────────────────────────
QUANTIVE_BASE_URL=https://your-quantive-backend.onrender.com
QUANTIVE_API_TOKEN=your-jwt-token-here
QUANTIVE_WEBHOOK_SECRET=<generated-in-step-1>

# ── Database ──────────────────────────────────────────────────────
DB_HOST=your-postgres-host.render.com
DB_PORT=5432
DB_USER=quantive
DB_PASSWORD=your-db-password
DB_NAME=quantive

# ── Slack ─────────────────────────────────────────────────────────
SLACK_WEBHOOK_URL=<your-slack-webhook-url>

# ── SMTP ──────────────────────────────────────────────────────────
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=notifications@yourdomain.gov

# ── External APIs ─────────────────────────────────────────────────
FRED_API_KEY=your-fred-api-key
NEWS_API_KEY=your-newsapi-key
ALPHA_VANTAGE_KEY=your-alpha-vantage-key

# ── Stripe ────────────────────────────────────────────────────────
STRIPE_SECRET_KEY=sk_live_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
```

---

## Step 3: Create n8n Credentials

### 3.1 Quantive API Token (HTTP Header Auth)
1. Go to n8n → Settings → Credentials
2. Create new: **Header Auth**
3. Name: `Quantive API Token`
4. Header Name: `Authorization`
5. Header Value: `Bearer YOUR_JWT_TOKEN`

### 3.2 Quantive Database (Postgres)
1. Go to n8n → Settings → Credentials
2. Create new: **Postgres**
3. Name: `Quantive Database`
4. Host: `your-postgres-host.render.com`
5. Port: `5432`
6. Database: `quantive`
7. User: `quantive`
8. Password: `your-db-password`

### 3.3 Stripe API
1. Go to n8n → Settings → Credentials
2. Create new: **Stripe API**
3. Name: `Stripe API`
4. API Key: `sk_live_your_stripe_key`

### 3.4 SMTP
1. Go to n8n → Settings → Credentials
2. Create new: **SMTP**
3. Name: `Quantive SMTP`
4. Host: `smtp.gmail.com`
5. Port: `587`
6. User: `your-email@gmail.com`
7. Password: `your-app-password`

---

## Step 4: Import Workflows

1. Go to n8n → Workflows
2. Click **Import from File**
3. Import each of the 4 workflow files:
   - `01-stripe-billing.json` (12 workflows, 84 nodes)
   - `02-onboarding-support.json` (14 workflows, 89 nodes)
   - `03-platform-ai.json` (14 workflows, 109 nodes)
   - `04-management-internal.json` (21 workflows, 131 nodes)

4. For each workflow:
   - Open the workflow
   - Click **Edit** on each node
   - Select the correct credentials from Step 3
   - Update any `your-domain.com` placeholders
   - Save the workflow

---

## Step 5: Configure Credential References

Replace these placeholders in each workflow:

| Placeholder | Replace With |
|-------------|--------------|
| `REPLACE_WITH_POSTGRES_CREDENTIAL_ID` | Your Postgres credential ID |
| `REPLACE_WITH_STRIPE_CREDENTIAL_ID` | Your Stripe credential ID |
| `REPLACE_WITH_SMTP_CREDENTIAL_ID` | Your SMTP credential ID |
| `REPLACE_WITH_QUANTIVE_CREDENTIAL_ID` | Your HTTP Header Auth credential ID |
| `REPLACE_WITH_SLACK_CREDENTIAL_ID` | Your Slack credential ID |
| `REPLACE_WITH_GITHUB_CREDENTIAL_ID` | Your GitHub credential ID (optional) |

---

## Step 6: Activate Workflows

1. For each imported workflow, toggle the **Active** switch ON
2. Verify the schedule triggers are correct
3. Check webhook URLs are accessible

---

## Step 7: Configure Stripe Webhook

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-n8n-instance.com/webhook/stripe-billing`
3. Select events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the webhook signing secret to `STRIPE_WEBHOOK_SECRET`

---

## Step 8: Verify Workflows

### Manual Test
1. Open each workflow in n8n
2. Click **Execute Workflow** manually
3. Check the execution log for errors
4. Verify data appears in Postgres

### Automated Verification
```bash
# Check if workflows are running
curl https://your-n8n-instance.com/api/v1/executions?limit=10

# Check Quantive backend for n8n bridge entries
curl https://your-quantive-backend.com/api/automation/runs/recent \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Troubleshooting

### Workflow not triggering
- Check schedule trigger is active
- Verify n8n has permission to run scheduled workflows
- Check n8n logs for cron errors

### HTTP Request failures
- Verify `QUANTIVE_BASE_URL` is correct
- Check JWT token hasn't expired
- Verify backend is running and healthy

### Postgres connection errors
- Verify database credentials
- Check if n8n IP is whitelisted
- Test connection with psql

### HMAC verification failed
- Ensure `QUANTIVE_WEBHOOK_SECRET` matches on both sides
- Check the Code node is using the correct secret
- Verify the header name is `X-Quantive-Signature`

### Slack notifications not sending
- Verify `SLACK_WEBHOOK_URL` is correct
- Check Slack app has permission to post to the channel
- Test with a manual webhook call

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        n8n (Render)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │ 01-stripe-billing   │  │ 02-onboarding       │              │
│  │ 84 nodes, 12 flows  │  │ 89 nodes, 14 flows  │              │
│  └──────────┬──────────┘  └──────────┬──────────┘              │
│             │                        │                          │
│  ┌──────────┴──────────┐  ┌──────────┴──────────┐              │
│  │ 03-platform-ai      │  │ 04-management       │              │
│  │ 109 nodes, 14 flows │  │ 131 nodes, 21 flows │              │
│  └──────────┬──────────┘  └──────────┬──────────┘              │
│             │                        │                          │
└─────────────┼────────────────────────┼──────────────────────────┘
              │                        │
              ▼                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Quantive Backend (FastAPI)                    │
├─────────────────────────────────────────────────────────────────┤
│  /api/automation/webhooks/external-run  (HMAC bridge)           │
│  /api/billing/webhook/stripe           (Stripe relay)           │
│  /api/portfolios                       (Portfolio data)         │
│  /api/v1/optimize                      (Optimization)           │
│  /api/market/*                         (Market data)            │
│  /api/compliance/*                     (Compliance)             │
│  /api/health/*                         (Health/backup)          │
│  /api/analytics/*                      (Dashboards)             │
│  /api/security/*                       (Security)               │
└─────────────────────────────────────────────────────────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ PostgreSQL   │ │ Slack        │ │ Email        │ │ Stripe       │
│ (All data)   │ │ (Alerts)     │ │ (Reports)    │ │ (Billing)    │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `QUANTIVE_BASE_URL` | Yes | Backend URL |
| `QUANTIVE_API_TOKEN` | Yes | JWT token for API auth |
| `QUANTIVE_WEBHOOK_SECRET` | Yes | Shared HMAC secret |
| `DB_HOST` | Yes | PostgreSQL host |
| `DB_PORT` | Yes | PostgreSQL port |
| `DB_USER` | Yes | PostgreSQL user |
| `DB_PASSWORD` | Yes | PostgreSQL password |
| `DB_NAME` | Yes | PostgreSQL database |
| `SLACK_WEBHOOK_URL` | Yes | Slack webhook |
| `SMTP_HOST` | Yes | SMTP host |
| `SMTP_PORT` | Yes | SMTP port |
| `SMTP_USER` | Yes | SMTP username |
| `SMTP_PASS` | Yes | SMTP password |
| `SMTP_FROM` | Yes | From email |
| `FRED_API_KEY` | No | FRED API key |
| `NEWS_API_KEY` | No | NewsAPI key |
| `ALPHA_VANTAGE_KEY` | No | Alpha Vantage key |
| `STRIPE_SECRET_KEY` | Yes | Stripe secret |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook secret |
