# Quantive n8n Credentials Setup Guide

## Required Credentials (13 total)

### 1. Slack API (Used by ALL workflows)
- **Type:** Slack API
- **How to create:**
  1. Go to https://api.slack.com/apps → Create New App → From scratch
  2. Name: `Quantive Automation`, Workspace: your workspace
  3. Go to OAuth & Permissions → Add scopes: `chat:write`, `channels:read`, `files:write`
  4. Install to workspace → Copy `Bot User OAuth Token`
  5. In n8n: Credentials → Add → Slack API → Paste token
- **Name in n8n:** `Quantive Slack`
- **Environment variable:** `SLACK_BOT_TOKEN=xoxb-...`

### 2. SMTP (Used by WF-1, WF-2)
- **Type:** SMTP
- **How to create:**
  1. Use your email provider's SMTP settings (Gmail, SendGrid, Mailgun, etc.)
  2. For Gmail: Enable 2FA → App Passwords → Generate
  3. In n8n: Credentials → Add → SMTP
- **Name in n8n:** `Quantive SMTP`
- **Environment variables:**
  ```
  SMTP_HOST=smtp.gmail.com
  SMTP_PORT=587
  SMTP_USER=automation@quantive.com
  SMTP_PASS=your-app-password
  ```

### 3. PostgreSQL (Used by ALL workflows)
- **Type:** PostgreSQL
- **How to create:**
  1. Ensure PostgreSQL is running (Docker or native)
  2. Create database: `CREATE DATABASE quantive;`
  3. Create user: `CREATE USER quantive WITH PASSWORD 'secure_password';`
  4. Grant privileges: `GRANT ALL PRIVILEGES ON DATABASE quantive TO quantive;`
  5. In n8n: Credentials → Add → PostgreSQL
- **Name in n8n:** `Quantive DB`
- **Environment variables:**
  ```
  DB_HOST=localhost
  DB_PORT=5432
  DB_NAME=quantive
  DB_USER=quantive
  DB_PASSWORD=secure_password
  ```

### 4. Stripe Webhook Secret (Used by WF-2)
- **Type:** Header Auth
- **How to create:**
  1. Go to https://dashboard.stripe.com/webhooks
  2. Add endpoint: `https://your-n8n.com/webhook/stripe`
  3. Select events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`, `customer.updated`
  4. Copy signing secret (`whsec_...`)
  5. In n8n: Credentials → Add → Header Auth → Name: `stripe-signature`, Value: `whsec_...`
- **Name in n8n:** `Stripe Webhook Secret`
- **Environment variable:** `STRIPE_WEBHOOK_SECRET=whsec_...`

### 5. Clearbit API Key (Used by WF-1)
- **Type:** HTTP Header Auth
- **How to create:**
  1. Sign up at https://clearbit.com
  2. Go to API dashboard → Copy API key
  3. In n8n: Credentials → Add → Header Auth → Name: `Authorization`, Value: `Bearer sk_...`
- **Name in n8n:** `Clearbit API`
- **Environment variable:** `CLEARBIT_API_KEY=sk_...`

### 6. FRED API Key (Used by WF-3)
- **Type:** HTTP Query Auth
- **How to create:**
  1. Go to https://fred.stlouisfed.org/docs/api/api_key.html
  2. Register for free API key
  3. In n8n: Credentials → Add → HTTP Query Auth → Name: `api_key`, Value: your key
- **Name in n8n:** `FRED API`
- **Environment variable:** `FRED_API_KEY=your_key`

### 7. News API Key (Used by WF-3)
- **Type:** HTTP Query Auth
- **How to create:**
  1. Go to https://newsapi.org/register
  2. Register for free API key
  3. In n8n: Credentials → Add → HTTP Query Auth → Name: `apiKey`, Value: your key
- **Name in n8n:** `News API`
- **Environment variable:** `NEWS_API_KEY=your_key`

### 8. Treasury.gov API (Used by WF-3)
- **Type:** No auth required (public API)
- **Endpoint:** `https://api.fiscaldata.treasury.gov/services/api/fiscal_service/`
- **No credential needed in n8n**

### 9-13. Optional Integrations

| # | Credential | Type | Used For | Priority |
|---|-----------|------|----------|----------|
| 9 | Google Calendar | OAuth2 | Meeting scheduling (WF-4) | Medium |
| 10 | Sentry | HTTP Header | Error tracking (WF-4) | Medium |
| 11 | PostHog | HTTP Header | Analytics (WF-3) | Low |
| 12 | SendGrid | HTTP Header | Alternative to SMTP | Medium |
| 13 | Stripe API Key | HTTP Header | Direct Stripe API calls | High |

---

## Environment Variables (.env)

Create `.env` file in n8n root:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=quantive
DB_USER=quantive
DB_PASSWORD=your_secure_password_here

# Slack
SLACK_BOT_TOKEN=xoxb-your-token

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=automation@quantive.com
SMTP_PASS=your-app-password

# Stripe
STRIPE_WEBHOOK_SECRET=whsec_your_secret

# APIs
CLEARBIT_API_KEY=sk_your_key
FRED_API_KEY=your_key
NEWS_API_KEY=your_key

# App
BASE_URL=https://api.quantive.com
```

---

## Webhook URLs to Configure Externally

Only the paths below exist as webhook trigger nodes in the shipped
workflow JSONs (checked against `workflows/*.json`). All internal
webhooks expect an `x-quantive-signature` HMAC header (see README
"Webhook authentication"); the Stripe webhook expects Stripe's
`stripe-signature` header.

| External System | Webhook URL | Workflow |
|----------------|-------------|----------|
| Website form | `https://your-n8n.com/webhook/lead-capture` | WF-1 |
| Calendly | `https://your-n8n.com/webhook/demo-booked` | WF-1 |
| CRM (HubSpot/Salesforce) | `https://your-n8n.com/webhook/deal-closed` | WF-1 |
| CRM stage changes | `https://your-n8n.com/webhook/deal-stage` | WF-1 |
| Stripe Dashboard | `https://your-n8n.com/webhook/stripe-webhook` | WF-2 |
| App backend (tickets) | `https://your-n8n.com/webhook/support-ticket` | WF-4 |

> The previously listed paths (`user-signup`, `onboarding-event`,
> `watchlist-event`, `stock-event`, `model-error`, `team-event`,
> `task-created`, `contract-event`, `customer-health`, `churn-alert`)
> have **no trigger node in any workflow** — they were removed from
> this table to avoid wiring external systems to endpoints that
> return 404. WF-2's onboarding and re-engagement flows are cron
> driven (schedule triggers), and WF-3 ingests markets/news on
> schedule, not via inbound webhooks.
