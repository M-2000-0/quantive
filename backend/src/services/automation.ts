import fs from "fs";
import path from "path";
import { prisma } from "../config/database";
import { logger } from "../config/logger";

export interface AutomationTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  triggerEvent: string;
  icon: string;
  configSchema: Record<string, { label: string; type: string; required: boolean; default?: string }>;
  n8nWorkflowFile: string;
}

const TEMPLATES: AutomationTemplate[] = [
  {
    id: "alert-slack",
    name: "Alert → Slack",
    description: "Send real-time compliance alerts to a Slack channel. Critical alerts get a separate high-priority message.",
    category: "notifications",
    triggerEvent: "alert.created",
    icon: "slack",
    configSchema: { webhookUrl: { label: "Slack Webhook URL", type: "string", required: true }, channel: { label: "Channel", type: "string", required: true, default: "#compliance-alerts" } },
    n8nWorkflowFile: "alert-to-slack.json",
  },
  {
    id: "alert-pagerduty",
    name: "Critical Alert → PagerDuty",
    description: "Escalate CRITICAL alerts to PagerDuty with automatic 30-minute acknowledgment timeout and re-escalation.",
    category: "notifications",
    triggerEvent: "alert.created",
    icon: "pagerduty",
    configSchema: { routingKey: { label: "PagerDuty Routing Key", type: "string", required: true }, escalationDelay: { label: "Escalation Delay (min)", type: "number", required: true, default: "30" } },
    n8nWorkflowFile: "alert-to-pagerduty.json",
  },
  {
    id: "alert-teams",
    name: "Alert → Microsoft Teams",
    description: "Post compliance alerts to a Microsoft Teams channel via incoming webhook.",
    category: "notifications",
    triggerEvent: "alert.created",
    icon: "teams",
    configSchema: { webhookUrl: { label: "Teams Webhook URL", type: "string", required: true } },
    n8nWorkflowFile: "alert-to-teams.json",
  },
  {
    id: "alert-jira",
    name: "Alert → Jira Issue",
    description: "Automatically create a Jira issue when a high or critical risk alert is triggered.",
    category: "ticketing",
    triggerEvent: "alert.created",
    icon: "jira",
    configSchema: { jiraUrl: { label: "Jira URL", type: "string", required: true }, project: { label: "Project Key", type: "string", required: true }, apiToken: { label: "API Token", type: "string", required: true }, issueType: { label: "Issue Type", type: "string", required: true, default: "Task" } },
    n8nWorkflowFile: "alert-to-jira.json",
  },
  {
    id: "alert-discord",
    name: "Alert → Discord",
    description: "Send compliance alerts to a Discord channel via webhook.",
    category: "notifications",
    triggerEvent: "alert.created",
    icon: "discord",
    configSchema: { webhookUrl: { label: "Discord Webhook URL", type: "string", required: true } },
    n8nWorkflowFile: "alert-to-discord.json",
  },
  {
    id: "alert-email",
    name: "Alert Email Notification",
    description: "Send formatted HTML email alerts to compliance team via SMTP/SendGrid.",
    category: "email",
    triggerEvent: "alert.created",
    icon: "email",
    configSchema: { toEmail: { label: "Recipient Email", type: "string", required: true }, smtpHost: { label: "SMTP Host", type: "string", required: false, default: "smtp.sendgrid.net" } },
    n8nWorkflowFile: "alert-email-notification.json",
  },
  {
    id: "alert-sms",
    name: "High-Value Alert → SMS",
    description: "Send SMS via Twilio for transactions exceeding $1M in value.",
    category: "notifications",
    triggerEvent: "alert.created",
    icon: "sms",
    configSchema: { twilioAccountSid: { label: "Twilio Account SID", type: "string", required: true }, twilioAuthToken: { label: "Twilio Auth Token", type: "string", required: true }, fromNumber: { label: "From Number", type: "string", required: true }, toNumber: { label: "To Number", type: "string", required: true }, minValueUsd: { label: "Min Value (USD)", type: "number", required: false, default: "1000000" } },
    n8nWorkflowFile: "high-value-sms-alert.json",
  },
  {
    id: "alert-escalation",
    name: "Alert Escalation Path",
    description: "Automatically escalate alerts that are not acknowledged within a configurable time window.",
    category: "workflow",
    triggerEvent: "alert.created",
    icon: "escalation",
    configSchema: { ackTimeoutMin: { label: "Acknowledgment Timeout (min)", type: "number", required: true, default: "30" }, escalateTo: { label: "Escalate To (email)", type: "string", required: true } },
    n8nWorkflowFile: "alert-escalation-path.json",
  },
  {
    id: "alert-digest-daily",
    name: "Daily Alert Digest",
    description: "Aggregate all open alerts into a daily summary email sent every morning.",
    category: "email",
    triggerEvent: "schedule",
    icon: "digest",
    configSchema: { toEmail: { label: "Recipient Email", type: "string", required: true }, time: { label: "Send Time (HH:MM)", type: "string", required: false, default: "09:00" } },
    n8nWorkflowFile: "daily-compliance-digest.json",
  },
  {
    id: "alert-digest-weekly",
    name: "Weekly Suspicious Activity Digest",
    description: "Weekly summary of all suspicious activity including open alerts and active cases.",
    category: "email",
    triggerEvent: "schedule",
    icon: "digest",
    configSchema: { toEmail: { label: "Recipient Email", type: "string", required: true }, dayOfWeek: { label: "Day of Week", type: "string", required: false, default: "Monday" } },
    n8nWorkflowFile: "weekly-suspicious-activity-digest.json",
  },
  {
    id: "onboarding-email",
    name: "Onboarding Email Sequence",
    description: "Send a 5-part onboarding email sequence (Day 0, 1, 3, 5, 7) to new users.",
    category: "onboarding",
    triggerEvent: "user.created",
    icon: "email",
    configSchema: { fromEmail: { label: "From Email", type: "string", required: true, default: "onboarding@quantive.io" } },
    n8nWorkflowFile: "onboarding-email-sequence.json",
  },
  {
    id: "onboarding-demo-auto",
    name: "Auto-Load Demo Data",
    description: "Automatically load demo data for organizations that have no transactions after 24 hours.",
    category: "onboarding",
    triggerEvent: "schedule",
    icon: "demo",
    configSchema: { delayHours: { label: "Delay Before Auto-Load (hours)", type: "number", required: false, default: "24" } },
    n8nWorkflowFile: "auto-load-demo-data.json",
  },
  {
    id: "onboarding-progress",
    name: "Stuck User Alert",
    description: "Notify admins when a user's onboarding progress is stuck below 50% after 7 days.",
    category: "onboarding",
    triggerEvent: "schedule",
    icon: "alert",
    configSchema: { notifyEmail: { label: "Admin Email", type: "string", required: true } },
    n8nWorkflowFile: "stuck-user-onboarding-alert.json",
  },
  {
    id: "report-weekly",
    name: "Weekly Risk Report",
    description: "Generate risk_overview PDF and audit_trail CSV reports every Monday morning.",
    category: "reporting",
    triggerEvent: "schedule",
    icon: "report",
    configSchema: { dayOfWeek: { label: "Day of Week", type: "string", required: false, default: "Monday" }, time: { label: "Time", type: "string", required: false, default: "08:00" } },
    n8nWorkflowFile: "weekly-risk-report.json",
  },
  {
    id: "report-monthly",
    name: "Monthly Compliance Report",
    description: "Generate a comprehensive monthly compliance report covering all activity.",
    category: "reporting",
    triggerEvent: "schedule",
    icon: "report",
    configSchema: { dayOfMonth: { label: "Day of Month", type: "number", required: false, default: "1" }, toEmail: { label: "Email To", type: "string", required: true } },
    n8nWorkflowFile: "monthly-compliance-report.json",
  },
  {
    id: "report-sar",
    name: "Automated SAR Filing",
    description: "When a high-risk case is closed, auto-generate a Suspicious Activity Report and file it.",
    category: "reporting",
    triggerEvent: "case.closed",
    icon: "report",
    configSchema: { autoFile: { label: "Auto-File with FinCEN", type: "boolean", required: false, default: "false" } },
    n8nWorkflowFile: "automated-sar-filing.json",
  },
  {
    id: "report-delivery",
    name: "Report Email Delivery",
    description: "Automatically email generated reports to compliance team as PDF attachments.",
    category: "reporting",
    triggerEvent: "report.generated",
    icon: "email",
    configSchema: { toEmail: { label: "Recipient Email", type: "string", required: true } },
    n8nWorkflowFile: "report-email-delivery.json",
  },
  {
    id: "ingest-csv",
    name: "CSV Transaction Import",
    description: "Import transactions from CSV/Excel files via drag-and-drop or file watch.",
    category: "ingestion",
    triggerEvent: "manual",
    icon: "csv",
    configSchema: { sourceFolder: { label: "Watch Folder Path", type: "string", required: false } },
    n8nWorkflowFile: "csv-transaction-import.json",
  },
  {
    id: "ingest-etherscan",
    name: "Etherscan Wallet Polling",
    description: "Poll Etherscan API for new transactions from watched wallets every 5 minutes.",
    category: "ingestion",
    triggerEvent: "schedule",
    icon: "blockchain",
    configSchema: { apiKey: { label: "Etherscan API Key", type: "string", required: true }, pollIntervalMin: { label: "Poll Interval (min)", type: "number", required: false, default: "5" } },
    n8nWorkflowFile: "etherscan-wallet-polling.json",
  },
  {
    id: "ingest-multichain",
    name: "Multi-Chain Aggregator",
    description: "Aggregate transactions from Ethereum, Solana, Polygon into a single ingestion pipeline.",
    category: "ingestion",
    triggerEvent: "schedule",
    icon: "blockchain",
    configSchema: { chains: { label: "Chains (comma-separated)", type: "string", required: true, default: "ethereum,solana,polygon" }, pollIntervalMin: { label: "Poll Interval (min)", type: "number", required: false, default: "30" } },
    n8nWorkflowFile: "multi-chain-aggregator.json",
  },
  {
    id: "ingest-s3",
    name: "S3 File Watcher",
    description: "Watch an S3 bucket for new transaction CSV files and auto-ingest them.",
    category: "ingestion",
    triggerEvent: "webhook",
    icon: "storage",
    configSchema: { bucket: { label: "S3 Bucket Name", type: "string", required: true }, region: { label: "AWS Region", type: "string", required: false, default: "us-east-1" } },
    n8nWorkflowFile: "s3-file-watcher.json",
  },
  {
    id: "ingest-alchemy",
    name: "Alchemy Webhook → Quantive",
    description: "Forward Alchemy blockchain webhooks directly into Quantive's ingestion pipeline.",
    category: "ingestion",
    triggerEvent: "webhook",
    icon: "blockchain",
    configSchema: { alchemyWebhookUrl: { label: "Alchemy Webhook URL", type: "string", required: true } },
    n8nWorkflowFile: "alchemy-webhook-ingest.json",
  },
  {
    id: "compliance-assessment",
    name: "Quarterly Compliance Assessment",
    description: "Run a full compliance framework assessment every quarter and email the results.",
    category: "compliance",
    triggerEvent: "schedule",
    icon: "compliance",
    configSchema: { toEmail: { label: "Report Email", type: "string", required: true } },
    n8nWorkflowFile: "quarterly-compliance-assessment.json",
  },
  {
    id: "compliance-gap",
    name: "Compliance Gap Remediation",
    description: "Create Jira tickets for each compliance gap identified in assessments.",
    category: "compliance",
    triggerEvent: "schedule",
    icon: "compliance",
    configSchema: { jiraUrl: { label: "Jira URL", type: "string", required: true }, project: { label: "Project Key", type: "string", required: true } },
    n8nWorkflowFile: "compliance-gap-remediation.json",
  },
  {
    id: "compliance-monitor",
    name: "Regulatory Change Monitor",
    description: "Monitor regulatory frameworks for updates and notify when requirements change.",
    category: "compliance",
    triggerEvent: "schedule",
    icon: "compliance",
    configSchema: { notifyEmail: { label: "Notify Email", type: "string", required: true } },
    n8nWorkflowFile: "regulatory-change-monitor.json",
  },
  {
    id: "compliance-evidence",
    name: "Evidence Collection Automation",
    description: "Auto-generate compliance evidence reports for each framework requirement.",
    category: "compliance",
    triggerEvent: "schedule",
    icon: "compliance",
    configSchema: { frameworks: { label: "Frameworks (comma-separated)", type: "string", required: false, default: "fatf,mica,fincen" } },
    n8nWorkflowFile: "compliance-evidence-collection.json",
  },
  {
    id: "risk-sanctioned-freeze",
    name: "Sanctioned Address Freeze",
    description: "Automatically freeze sanctioned addresses via Fireblocks/BitGo custody API.",
    category: "risk",
    triggerEvent: "alert.created",
    icon: "risk",
    configSchema: { custodyApiKey: { label: "Custody API Key", type: "string", required: true }, custodyApiUrl: { label: "Custody API URL", type: "string", required: true } },
    n8nWorkflowFile: "sanctioned-address-freeze.json",
  },
  {
    id: "risk-mixer-fincen",
    name: "Mixer Interaction → FinCEN SAR",
    description: "Auto-compile and file Suspicious Activity Reports for mixer/tumbler interactions.",
    category: "risk",
    triggerEvent: "alert.created",
    icon: "risk",
    configSchema: { fincenApiKey: { label: "FinCEN API Key", type: "string", required: true }, filerEIN: { label: "Filer EIN", type: "string", required: true } },
    n8nWorkflowFile: "mixer-fincen-sar.json",
  },
  {
    id: "risk-threat-intel",
    name: "Threat Intelligence Sharing",
    description: "Push flagged addresses to MISP/OpenCTI threat intelligence platforms.",
    category: "risk",
    triggerEvent: "alert.created",
    icon: "risk",
    configSchema: { mispUrl: { label: "MISP URL", type: "string", required: true }, mispApiKey: { label: "MISP API Key", type: "string", required: true } },
    n8nWorkflowFile: "threat-intel-sharing.json",
  },
  {
    id: "risk-chainalysis",
    name: "Blockchain Analytics Enrichment",
    description: "Send transactions to Chainalysis/Elliptic for additional risk scoring.",
    category: "risk",
    triggerEvent: "transaction.ingested",
    icon: "risk",
    configSchema: { analyticsApiKey: { label: "Analytics API Key", type: "string", required: true }, provider: { label: "Provider", type: "string", required: false, default: "chainalysis" } },
    n8nWorkflowFile: "blockchain-analytics-enrichment.json",
  },
  {
    id: "risk-wallet-rescore",
    name: "Wallet Risk Re-Scoring",
    description: "Daily wallet risk re-assessment with external scoring data.",
    category: "risk",
    triggerEvent: "schedule",
    icon: "risk",
    configSchema: { minRiskThreshold: { label: "Min Risk Threshold", type: "number", required: false, default: "0.5" } },
    n8nWorkflowFile: "wallet-risk-rescoring.json",
  },
  {
    id: "audit-siem-splunk",
    name: "Audit Log → Splunk",
    description: "Stream audit logs to Splunk for centralized SIEM monitoring every 15 minutes.",
    category: "audit",
    triggerEvent: "schedule",
    icon: "audit",
    configSchema: { splunkUrl: { label: "Splunk HEC URL", type: "string", required: true }, splunkToken: { label: "Splunk HEC Token", type: "string", required: true } },
    n8nWorkflowFile: "audit-log-to-splunk.json",
  },
  {
    id: "audit-siem-datadog",
    name: "Audit Log → Datadog",
    description: "Stream audit logs to Datadog for monitoring and alerting.",
    category: "audit",
    triggerEvent: "schedule",
    icon: "audit",
    configSchema: { datadogApiKey: { label: "Datadog API Key", type: "string", required: true }, datadogSite: { label: "Datadog Site", type: "string", required: false, default: "datadoghq.com" } },
    n8nWorkflowFile: "audit-log-to-datadog.json",
  },
  {
    id: "audit-archive",
    name: "Immutable Audit Archive",
    description: "Archive audit logs daily to append-only S3 bucket for compliance retention.",
    category: "audit",
    triggerEvent: "schedule",
    icon: "audit",
    configSchema: { archiveBucket: { label: "Archive S3 Bucket", type: "string", required: true }, archiveRegion: { label: "AWS Region", type: "string", required: false, default: "us-east-1" } },
    n8nWorkflowFile: "immutable-audit-archive.json",
  },
  {
    id: "audit-user-activity",
    name: "User Activity Report",
    description: "Weekly per-user activity report sent to managers.",
    category: "audit",
    triggerEvent: "schedule",
    icon: "audit",
    configSchema: { toEmail: { label: "Manager Email", type: "string", required: true } },
    n8nWorkflowFile: "user-activity-report.json",
  },
  {
    id: "stripe-sync",
    name: "Stripe → Plan Sync",
    description: "Sync Stripe subscription events to update organization plans in real-time.",
    category: "subscription",
    triggerEvent: "webhook",
    icon: "stripe",
    configSchema: { stripeWebhookSecret: { label: "Stripe Webhook Secret", type: "string", required: true } },
    n8nWorkflowFile: "stripe-subscription-sync.json",
  },
  {
    id: "stripe-downgrade",
    name: "Payment Failed → Downgrade",
    description: "Automatically downgrade organizations when payment fails and send notice.",
    category: "subscription",
    triggerEvent: "webhook",
    icon: "stripe",
    configSchema: { downgradePlan: { label: "Downgrade To Plan", type: "string", required: false, default: "free" } },
    n8nWorkflowFile: "payment-failed-downgrade.json",
  },
  {
    id: "stripe-expiry",
    name: "Subscription Expiry Notice",
    description: "Send renewal reminders before subscription expires.",
    category: "subscription",
    triggerEvent: "schedule",
    icon: "email",
    configSchema: { remindDaysBefore: { label: "Remind Days Before", type: "number", required: false, default: "7" } },
    n8nWorkflowFile: "subscription-expiry-notice.json",
  },
  {
    id: "credit-limit",
    name: "Credit Limit Warning",
    description: "Warn organizations via email when they approach their monthly credit limit.",
    category: "subscription",
    triggerEvent: "schedule",
    icon: "email",
    configSchema: { warnAtPercent: { label: "Warn At %", type: "number", required: false, default: "80" } },
    n8nWorkflowFile: "credit-limit-warning.json",
  },
  {
    id: "health-webhooks",
    name: "Webhook Health Monitor",
    description: "Daily check for deactivated webhook endpoints and notify admin.",
    category: "system",
    triggerEvent: "schedule",
    icon: "health",
    configSchema: { notifyEmail: { label: "Admin Email", type: "string", required: true } },
    n8nWorkflowFile: "webhook-health-monitor.json",
  },
  {
    id: "health-queue",
    name: "Queue Backlog Monitor",
    description: "Monitor BullMQ queue sizes and alert if backlog exceeds threshold.",
    category: "system",
    triggerEvent: "schedule",
    icon: "health",
    configSchema: { maxBacklog: { label: "Max Backlog Before Alert", type: "number", required: false, default: "100" }, notifyEmail: { label: "Notify Email", type: "string", required: true } },
    n8nWorkflowFile: "queue-backlog-monitor.json",
  },
  {
    id: "okta-sync",
    name: "Okta SSO User Sync",
    description: "Sync user directory from Okta to Quantive every hour via SCIM.",
    category: "system",
    triggerEvent: "schedule",
    icon: "sso",
    configSchema: { oktaDomain: { label: "Okta Domain", type: "string", required: true }, oktaApiToken: { label: "Okta API Token", type: "string", required: true } },
    n8nWorkflowFile: "okta-sso-user-sync.json",
  },
];

export class AutomationService {
  async listTemplates(): Promise<AutomationTemplate[]> {
    return TEMPLATES;
  }

  async getTemplate(id: string): Promise<AutomationTemplate | null> {
    return TEMPLATES.find((t) => t.id === id) || null;
  }

  async listActive(organizationId: string) {
    return prisma.webhookEndpoint.findMany({
      where: { organizationId, isActive: true },
    });
  }

  async activate(organizationId: string, templateId: string, config: Record<string, string>) {
    const template = await this.getTemplate(templateId);
    if (!template) throw Object.assign(new Error("Automation template not found"), { statusCode: 404 });

    const existing = await prisma.webhookEndpoint.findFirst({
      where: { organizationId, url: template.n8nWorkflowFile },
    });
    if (existing) {
      return prisma.webhookEndpoint.update({
        where: { id: existing.id },
        data: { isActive: true, events: JSON.stringify([template.triggerEvent]) },
      });
    }

    return prisma.webhookEndpoint.create({
      data: {
        url: `${config.n8nUrl || "http://localhost:5678/webhook"}/${templateId}`,
        secret: templateId,
        events: JSON.stringify([template.triggerEvent]),
        isActive: true,
        organizationId,
      },
    });
  }

  async deactivate(organizationId: string, webhookId: string) {
    const ep = await prisma.webhookEndpoint.findFirst({
      where: { id: webhookId, organizationId },
    });
    if (!ep) throw Object.assign(new Error("Webhook endpoint not found"), { statusCode: 404 });

    return prisma.webhookEndpoint.update({
      where: { id: webhookId },
      data: { isActive: false },
    });
  }

  getWorkflowJson(templateId: string): string | null {
    try {
      const template = TEMPLATES.find((t) => t.id === templateId);
      if (!template) return null;
      const filePath = path.join(__dirname, "../../../n8n-workflows", template.n8nWorkflowFile);
      if (fs.existsSync(filePath)) {
        return fs.readFileSync(filePath, "utf-8");
      }
      return null;
    } catch {
      return null;
    }
  }
}

export const automationService = new AutomationService();
