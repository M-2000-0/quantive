# Quantive × n8n Automation Workflows

## Importing Workflows
1. Open n8n (http://localhost:5678)
2. Go to **Workflows** → **Import from File**
3. Select any `.json` file in this directory

## Workflows Included

| File | Purpose | Trigger |
|------|---------|---------|
| `alert-to-slack.json` | Send Quantive alerts to Slack (#compliance-alerts) | Webhook (`alert.created`) |
| `alert-to-pagerduty.json` | Escalate critical alerts to PagerDuty with 30min acknowledgment timeout | Webhook (`alert.created`) |
| `daily-compliance-digest.json` | Daily email digest of dashboard stats, open alerts, and active cases | Schedule (daily 9 AM) |
| `weekly-risk-report.json` | Generate weekly risk_overview PDF + audit_trail CSV reports | Schedule (weekly Monday 8 AM) |
| `onboarding-email-sequence.json` | Day 1 / Day 3 / Day 7 onboarding email sequence with re-engagement | Webhook (new user registered) |

## Setup Requirements
- **Quantive API**: Update `http://localhost:4000` to your Quantive API URL
- **Auth credentials**: Update login email/password in HTTP Request nodes
- **Slack**: Configure Slack webhook URL in the Slack node
- **PagerDuty**: Replace `YOUR_PAGERDUTY_ROUTING_KEY`
- **Email**: Configure SMTP/ SendGrid credentials in n8n

## Webhook Configuration
To receive Quantive webhooks in n8n:
1. Copy the webhook URL from the n8n workflow (e.g., `https://your-n8n.example.com/webhook/quantive-alert-created`)
2. Register it in Quantive: `POST /api/v1/admin/webhooks` with body `{ "url": "...", "events": ["alert.created"] }`

## Full Automation Map
See `AUTOMATION_MAP.md` for the complete catalog of 55+ automation opportunities.
