# Quantive n8n Automation Map

Complete catalog of automation opportunities across the Quantive platform.

## Categories

### 1. Alert-Driven Notifications (7 workflows)
| Workflow | Trigger | Action | Priority |
|----------|---------|--------|----------|
| Alert → Slack/Teams/Discord | `alert.created` webhook | Send formatted message with severity, reason, link | High |
| Critical Alert → PagerDuty | `alert.created` (CRITICAL) | Create PagerDuty incident | High |
| Alert → Jira Ticket | `alert.created` (HIGH/CRITICAL) | Create Jira issue with case details | Medium |
| Alert Escalation Path | `alert.created` + 30min wait | Escalate if not acknowledged | Medium |
| Alert Triage Auto-Response | `alert.created` | Auto-dismiss false positives via wallet history lookup | Low |
| High-Value Transaction Alert | `alert.created` (value > $1M) | Twilio SMS + email to compliance officer | Medium |
| Daily/Weekly Alert Digest | Schedule | Aggregate open alerts, send summary email | Low |

### 2. Transaction Ingestion (6 workflows)
| Workflow | Trigger | Action |
|----------|---------|--------|
| CSV/Excel Bulk Import | Manual n8n form | Parse CSV → POST /ingest-batch |
| Etherscan Wallet Polling | Schedule (5 min) | Fetch txs from Etherscan → POST /ingest |
| Alchemy Webhook → Quantive | Alchemy webhook | Normalize → POST /ingest |
| Multi-Chain Aggregator | Schedule (30 min) | Poll Ethereum, Solana, Polygon → batch ingest |
| Chain-agnostic External Poller | Schedule (2 min) | Fetch from any RPC → POST /ingest-batch |
| S3 File Watcher | S3 create event | Read CSV → batch ingest |

### 3. Report Automation (6 workflows)
| Workflow | Trigger | Action |
|----------|---------|--------|
| Weekly/Monthly Compliance Report | Schedule | Generate PDF risk_overview |
| Report Delivery to Email | After report generated | Fetch file URL, email as attachment |
| Report Archive to Google Drive | After report generated | Copy from local/S3 to Drive |
| Automated SAR Filing | `case.closed` (high risk) | Generate audit_trail, format SAR |
| Monthly Board Report | Schedule (1st) | Generate PDF, upload to Slides |
| Report Queue Monitor | Schedule (5 min) | Alert if report backlog > threshold |

### 4. Email/Notifications (gap-fill — 6 workflows)
| Workflow | Trigger | Action |
|----------|---------|--------|
| User Welcome Email | New user registered | SendGrid/SMTP welcome |
| Password Reset | Frontend webhook | Generate token, email reset link |
| Alert Notification Email | `alert.created` | HTML email to compliance team |
| Daily Summary Digest | Schedule | Dashboard stats → email |
| Weekly Suspicious Activity Digest | Schedule | Open alerts + cases → email |
| Credit Limit Warning | Schedule | Check usage, warn if near limit |

### 5. Compliance (5 workflows)
| Workflow | Trigger | Action |
|----------|---------|--------|
| Quarterly Compliance Assessment | Schedule | Run assessment, generate report, email |
| Compliance Gap Remediation | Schedule | Create Jira tickets for each gap |
| Regulatory Change Monitor | Schedule | Compare frameworks, notify of changes |
| Evidence Collection | Schedule/webhook | Auto-generate required reports as evidence |
| FATF Travel Rule Check | `transaction.ingested` | Verify originator/beneficiary data |

### 6. Onboarding (5 workflows)
| Workflow | Trigger | Action |
|----------|---------|--------|
| Onboarding Email Sequence | New user | Day 1/3/7 email sequence |
| Stuck User Alert | Schedule | Notify admin if <50% progress after 7 days |
| Auto-Load Demo Data | 24h after registration | POST /demo/generate if no data |
| Onboarding Completion | Onboarding complete | Congrats email + Calendly scheduling |
| Team Invite Automation | Manual form | Create user, send invite email |

### 7. Risk & External Actions (6 workflows)
| Workflow | Trigger | Action |
|----------|---------|--------|
| Sanctioned Address Freeze | `alert.created` (SANCTIONED) | Freeze via Fireblocks/BitGo API |
| Mixer → FinCEN Report | `alert.created` (MIXER) | Compile SAR, file via FinCEN API |
| High-Value Compliance Check | `transaction.ingested` ($10K+) | Counterparty wallet lookup |
| Wallet Risk Re-scoring | Schedule (daily) | Identify and update risk scores |
| Threat Intel Sharing | `alert.created` (sanctioned/mixer) | Push to MISP/OpenCTI |
| Blockchain Analytics Enrichment | `transaction.ingested` | Chainalysis/Elliptic enrichment |

### 8. Audit & SIEM (4 workflows)
| Workflow | Trigger | Action |
|----------|---------|--------|
| Audit Log → Splunk | Schedule (15 min) | Export audit logs to Splunk/ES |
| Suspicious Activity Alerting | Polling audit logs | Detect failed logins, notify security |
| Immutable Audit Archive | Schedule (daily) | Export logs to append-only S3 |
| User Activity Report | Schedule (weekly) | Per-user activity digest |

### 9. Stripe/Subscription (3 workflows)
| Workflow | Trigger | Action |
|----------|---------|--------|
| Subscription Sync | Stripe webhook | Update org plan in Quantive |
| Payment Failed → Downgrade | Stripe webhook | Downgrade plan, throttle access |
| Subscription Expiry Notice | Stripe webhook | Send upgrade link email |

### 10. System Health (3 workflows)
| Workflow | Trigger | Action |
|----------|---------|--------|
| Webhook Health Monitor | Schedule (1h) | Check deactivated endpoints, notify admin |
| BullMQ Queue Monitor | Schedule (5 min) | Alert if queue backlog > threshold |
| Okta SSO User Sync | Schedule (1h) | Sync user list via SCIM |

Total: **55+ automation workflows**

## Implementation Priority

Phase 1 (Quick wins):
1. Alert → Slack/Teams
2. Daily digest email
3. Auto-load demo data
4. Webhook health monitor

Phase 2 (Core compliance):
5. Critical Alert → PagerDuty
6. Weekly risk report
7. Audit log → SIEM
8. Onboarding email sequence

Phase 3 (Advanced):
9. Multi-chain ingestion
10. Sanctioned address freeze
11. Compliance assessment automation
12. FATF Travel Rule checks
