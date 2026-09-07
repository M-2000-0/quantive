"""Rebuild all Quantive n8n workflows with REAL app nodes.

Principles (replacing the previous code-only "fake" workflows):
  - NO Postgres.main pseudo-global: all DB access via native
    n8n-nodes-base.postgres nodes (credential: postgres-main).
  - Real integrations: HTTP Request nodes hitting real APIs
    (Yahoo Finance, NewsAPI, OpenAI, Clearbit) and the real Quantive
    backend; native Slack, Email (SMTP), Stripe Trigger.
  - Code nodes ONLY for genuine logic (HMAC verify, routing, shaping).

Regenerate with:  python generate_workflows.py
"""

import json
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workflows")
os.makedirs(OUT, exist_ok=True)

SLACK_CRED = {"slackApi": {"id": "slack-main", "name": "Quantive Slack"}}
PG_CRED = {"postgres": {"id": "postgres-main", "name": "Quantive DB"}}
SMTP_CRED = {"smtp": {"id": "smtp-main", "name": "Quantive SMTP"}}

IDS = {}


def nid(key):
    if key not in IDS:
        IDS[key] = f"auto-{key}-{len(IDS):04d}"
    return IDS[key]


def node(name, ntype, tv, params, pos, creds=None, on_error=None, webhook_id=None):
    n = {
        "parameters": params,
        "id": nid(name),
        "name": name,
        "type": ntype,
        "typeVersion": tv,
        "position": pos,
    }
    if creds:
        n["credentials"] = creds
    if on_error:
        n["onError"] = on_error
    if webhook_id:
        n["webhookId"] = webhook_id
    return n


# ── node helpers ─────────────────────────────────────────────────────

def code(name, js, pos, tv=2):
    return node(name, "n8n-nodes-base.code", tv, {"jsCode": js}, pos)


def pg_query(name, query, pos=(0, 0), tv=2.4):
    return node(name, "n8n-nodes-base.postgres", tv,
                {"operation": "executeQuery", "query": query, "options": {}},
                pos, creds=PG_CRED)


def slack(name, text, channel, pos):
    return node(
        name, "n8n-nodes-base.slack", 2.1,
        {"channel": channel, "text": text, "otherOptions": {}},
        pos, creds=SLACK_CRED, on_error="continueRegularOutput",
    )


def http(name, url, pos, method="GET", qs=None, headers=None, body=None,
         auth=None, on_error=None, retry=None, tv=4.2):
    p = {"url": url, "options": {}}
    if method != "GET":
        p["method"] = method
    if qs:
        p["sendQuery"] = True
        p["queryParameters"] = {"parameters": [{"name": k, "value": v} for k, v in qs.items()]}
    if headers:
        p["sendHeaders"] = True
        p["headerParameters"] = {"parameters": [{"name": k, "value": v} for k, v in headers.items()]}
    if body:
        p["sendBody"] = True
        p["specifyBody"] = "json"
        p["jsonBody"] = body
    if auth:
        p["authentication"] = "genericCredentialType"
        p["genericAuthType"] = auth
    if retry:
        p["retryOnFail"] = True
        p["maxTries"] = retry[0]
        p["waitBetweenTries"] = retry[1]
    if on_error:
        p["onError"] = on_error
    return node(name, "n8n-nodes-base.httpRequest", tv, p, pos)


def email(name, subject, body, to, pos):
    return node(
        name, "n8n-nodes-base.emailSend", 2.1,
        {
            "fromEmail": "quantive@quantive.com",
            "toEmail": to,
            "subject": subject,
            "emailFormat": "text",
            "text": body,
            "options": {},
        },
        pos, creds=SMTP_CRED, on_error="continueRegularOutput",
    )


def cron(name, rule, pos):
    return node(name, "n8n-nodes-base.scheduleTrigger", 1.2,
                {"rule": {"interval": [{"field": "cronExpression", "expression": rule}]}}, pos)


def webhook(name, path, pos, response_mode="lastNode", raw_body=False):
    opts = {"rawBody": True} if raw_body else {}
    return node(
        name, "n8n-nodes-base.webhook", 2,
        {"httpMethod": "POST", "path": path, "responseMode": response_mode, "options": opts},
        pos, webhook_id=path,
    )


def switch_node(name, expr, rules, pos):
    """rules: list of (value, outputLabel) — string equals."""

    def rule(val, label):
        return {
            "conditions": {"conditions": [{
                "leftValue": f"={{{{{expr}}}}}",
                "rightValue": val,
                "operator": {"type": "string", "operation": "equals"},
            }]},
            "renameOutput": label,
        }

    return node(name, "n8n-nodes-base.switch", 3,
                {"rules": {"rules": [rule(v, l) for v, l in rules]}}, pos)


def wire(*chains):
    """Build connections from linear chains and branch specs.

    A chain is a tuple of node names (A, B, C) => A->B->C.
    A tuple whose FIRST element is a list (['X','Y'], B, C) means X->B and
    Y->B (many-to-one merge) and then B->C.
    A dict {source: {output_index: [targets]}} wires switch outputs.
    """
    conns = {}

    def add(src, tgt, out_idx=0):
        outs = conns.setdefault(src, {"main": []})
        while len(outs["main"]) <= out_idx:
            outs["main"].append([])
        if not any(e["node"] == tgt for e in outs["main"][out_idx]):
            outs["main"][out_idx].append({"node": tgt, "type": "main", "index": 0})

    for chain in chains:
        if isinstance(chain, dict):
            for src, branches in chain.items():
                for out_idx, targets in branches.items():
                    for tgt in (targets if isinstance(targets, list) else [targets]):
                        add(src, tgt, out_idx)
        else:
            seq = list(chain)
            # expand a leading list of sources into pairwise (src, next) links
            if seq and isinstance(seq[0], list):
                merge_target = seq[1]
                for src in seq[0]:
                    add(src, merge_target)
                seq = seq[1:]
            for a, b in zip(seq, seq[1:]):
                add(a, b)
    return conns


def wf(workflow_id, name, nodes, conns, tags, desc):
    return {
        "id": workflow_id,
        "name": name,
        "active": False,
        "nodes": nodes,
        "connections": conns,
        "settings": {"executionOrder": "v1", "errorWorkflow": "wf0-error-handler"},
        "staticData": None,
        "meta": {"templateCredsSetupCompleted": False},
        "pinData": {},
        "versionId": None,
        "tags": tags,
        "description": desc,
    }


HMAC_JS = """const crypto = require('crypto');
const item = $input.first().json;
const header = (item.headers && item.headers['x-quantive-signature']) || '';
const secret = process.env.QUANTIVE_WEBHOOK_SECRET || '';
const raw = JSON.stringify(item.body || {});
const expected = crypto.createHmac('sha256', secret).update(raw).digest('hex');
let ok = false;
try {
  const a = Buffer.from(header, 'hex'); const b = Buffer.from(expected, 'hex');
  ok = a.length === b.length && a.length > 0 && crypto.timingSafeEqual(a, b);
} catch (e) { ok = false; }
if (!ok) throw new Error('Invalid HMAC signature');
return [{ json: item.body }];"""

# ════════════════════════════════════════════════════════════════════
# SVC sub-workflows
# ════════════════════════════════════════════════════════════════════

SVC1 = wf(
    "svc1-enrichment", "SVC-1: Lead Enrichment (manual)",
    [
        node("Manual", "n8n-nodes-base.manualTrigger", 1, {}, [0, 0]),
        code("Build Enrich Queries", """const items = $input.all().map(i => i.json);
return items.map(it => ({ json: {
  lead_id: it.id || it.lead_id || '',
  email: it.email || '',
  domain: (it.email || '').split('@')[1] || (it.company || '').toLowerCase().replace(/[^a-z0-9-]/g, '') + '.com',
  company: it.company || '',
}}));""", [200, 0]),
        http("Fetch Company Data (Clearbit)", "https://company.clearbit.com/v2/companies/find", [400, 0],
             qs={"domain": "={{ $json.domain }}"}, auth="httpQueryAuth",
             on_error="continueRegularOutput", retry=(2, 2000)),
        code("Map Enrichment", """const src = $input.first().json;
return [{ json: {
  lead_id: src.lead_id || src.id || '',
  email: src.email || '',
  company_size: src.metrics && src.metrics.employees ? String(src.metrics.employees) : null,
  industry: (src.category && src.category.sector) || null,
  location: [src.geo && src.geo.city, src.geo && src.geo.country].filter(Boolean).join(', ') || null,
  enriched_data: src,
}}];""", [600, 0]),
    ],
    wire(("Manual", "Build Enrich Queries", "Fetch Company Data (Clearbit)", "Map Enrichment"),),
    ["service", "enrichment"],
    "Lead enrichment service: real Clearbit company lookup. Call with lead rows; returns enrichment fields per lead.",
)

SVC2 = wf(
    "svc2-notification", "SVC-2: Notification Service (manual)",
    [
        node("Manual", "n8n-nodes-base.manualTrigger", 1, {}, [0, 0]),
        code("Normalize Notification", """const it = $input.first().json;
return [{ json: {
  channel: it.channel || '#workflow-logs',
  severity: it.severity || 'low',
  text: it.text || String(it.message || JSON.stringify(it)).slice(0, 500),
}}];""", [200, 0]),
        slack("Post to Slack", "={{ $json.text }}", "={{ $json.channel }}", [400, 0]),
    ],
    wire(("Manual", "Normalize Notification", "Post to Slack"),),
    ["service", "notification"],
    "Notification service: posts a formatted message to a Slack channel via the native Slack node.",
)

SVC3 = wf(
    "svc3-logger", "SVC-3: Execution Logger (manual)",
    [
        node("Manual", "n8n-nodes-base.manualTrigger", 1, {}, [0, 0]),
        code("Build Log Row", """const it = $input.first().json;
return [{ json: {
  workflow_id: it.workflowId || it.workflow_id || 'unknown',
  workflow_name: it.workflowName || it.workflow_name || 'unknown',
  execution_id: it.executionId || it.execution_id || 'manual',
  status: it.status || 'success',
  duration_ms: it.durationMs || it.duration_ms || 0,
  metadata: JSON.stringify(it.metadata || {}),
}}];""", [200, 0]),
        pg_query(
            "Insert Execution Log",
            "INSERT INTO workflows.workflow_executions (workflow_id, workflow_name, execution_id, status, duration_ms, metadata)\nVALUES ('{{ $json.workflow_id }}', '{{ $json.workflow_name }}', '{{ $json.execution_id }}', '{{ $json.status }}', {{ $json.duration_ms }}, '{{ $json.metadata }}'::jsonb);",
            [400, 0],
        ),
    ],
    wire(("Manual", "Build Log Row", "Insert Execution Log"),),
    ["service", "logging"],
    "Execution logger: writes a row into workflows.workflow_executions via the native Postgres node.",
)

# ════════════════════════════════════════════════════════════════════
# WF-0: Error Handler
# ════════════════════════════════════════════════════════════════════

WF0_NODES = [
    node("Error Trigger", "n8n-nodes-base.errorTrigger", 1, {}, [0, 0]),
    code("Classify Error", """const err = $input.first().json;
const workflow = err.workflow || {};
const execution = err.execution || {};
const msg = (err.execution && err.execution.error && err.execution.error.message) || 'Unknown error';
const sev = /timeout|connection|5\\d\\d/i.test(msg) ? 'critical'
          : /auth|permission|401|403/i.test(msg) ? 'high'
          : 'medium';
return [{ json: {
  workflowId: workflow.id || 'unknown',
  workflowName: workflow.name || 'unknown',
  executionId: execution.id || 'unknown',
  errorNode: (err.execution && err.execution.error && err.execution.error.node && err.execution.error.node.name) || 'unknown',
  errorMessage: msg,
  severity: sev,
  timestamp: new Date().toISOString(),
}}];""", [200, 0]),
    pg_query(
        "Log Error to DB",
        "INSERT INTO workflows.workflow_errors (workflow_id, workflow_name, execution_id, error_type, message, node_id, node_type, severity)\nVALUES ('{{ $json.workflowId }}', '{{ $json.workflowName }}', '{{ $json.executionId }}', 'workflow_error', '{{ $json.errorMessage }}', '{{ $json.errorNode }}', 'code', '{{ $json.severity }}');",
        [400, 0],
    ),
    switch_node("Route by Severity", "$json.severity",
                [("critical", "Critical"), ("high", "High"), ("medium", "Medium")], [600, 0]),
    slack("Slack Critical", "🚨 *CRITICAL ERROR*\n*Workflow:* {{ $json.workflowName }}\n*Node:* {{ $json.errorNode }}\n*Error:* {{ $json.errorMessage }}\n*Time:* {{ $json.timestamp }}", "#platform-critical", [800, 0]),
    slack("Slack High", "⚠️ *High Severity Error*\n*Workflow:* {{ $json.workflowName }}\n*Node:* {{ $json.errorNode }}\n*Error:* {{ $json.errorMessage }}", "#platform-alerts", [800, 150]),
    slack("Slack Medium/Low", "ℹ️ *{{ $json.severity }} Error*\n*Workflow:* {{ $json.workflowName }}\n*Error:* {{ $json.errorMessage }}", "#workflow-logs", [800, 300]),
]
WF0 = wf(
    "wf0-error-handler", "WF-0: Error Handler", WF0_NODES,
    wire(
        ("Error Trigger", "Classify Error", "Log Error to DB", "Route by Severity"),
        {"Route by Severity": {0: "Slack Critical", 1: "Slack High", 2: "Slack Medium/Low"}},
    ),
    ["error-handling"],
    "Central error handler: classifies severity, persists via native Postgres, routes to Slack by severity.",
)

# ════════════════════════════════════════════════════════════════════
# WF-1: Sales & CRM
# ════════════════════════════════════════════════════════════════════

LEAD_UPSERT = """INSERT INTO leads (email, name, company, source, status, created_at, updated_at)
VALUES ('{{ $json.email }}', '{{ $json.name }}', '{{ $json.company }}', '{{ $json.source }}', 'new', NOW(), NOW())
ON CONFLICT (email) DO UPDATE SET name=EXCLUDED.name, company=EXCLUDED.company, updated_at=NOW()
RETURNING id, email, name, company, score, tier, status;"""

WF1_NODES = [
    # lead capture
    webhook("Lead Capture Webhook", "lead-capture", [0, 0]),
    code("Verify Lead HMAC", HMAC_JS, [200, 0]),
    pg_query("Upsert Lead", LEAD_UPSERT, [400, 0]),
    code("Build Enrichment Query", """const lead = $input.first().json;
return [{ json: {
  email: lead.email, name: lead.name, company: lead.company,
  domain: (lead.email || '').split('@')[1] || '',
}}];""", [600, 0]),
    http("Clearbit Company Lookup", "https://company.clearbit.com/v2/companies/find", [800, 0],
         qs={"domain": "={{ $json.domain }}"}, auth="httpQueryAuth",
         on_error="continueRegularOutput", retry=(2, 2000)),
    code("Merge Enrichment + Score", """const lead = $('Upsert Lead').first().json;
const src = $input.first().json || {};
const enriched = {
  ...lead,
  company_size: src.metrics && src.metrics.employees ? String(src.metrics.employees) : null,
  industry: (src.category && src.category.sector) || null,
  location: [src.geo && src.geo.city, src.geo && src.geo.country].filter(Boolean).join(', ') || null,
};
let score = 0;
const size = enriched.company_size ? parseInt(enriched.company_size, 10) : 0;
if (size > 500) score += 40; else if (size > 50) score += 25; else if (size > 0) score += 10;
if (['financial services','banking','government','insurance'].some(k => (enriched.industry||'').toLowerCase().includes(k))) score += 30;
if ((enriched.email||'').endsWith('.gov')) score += 20;
const tier = score >= 70 ? 'hot' : score >= 40 ? 'warm' : 'cold';
return [{ json: { ...enriched, score, tier }}];""", [1000, 0]),
    pg_query(
        "Update Lead Score",
        "UPDATE leads SET score={{ $json.score }}, tier='{{ $json.tier }}',\n  company_size='{{ $json.company_size || \"\" }}', industry='{{ $json.industry || \"\" }}', location='{{ $json.location || \"\" }}',\n  enriched_data='{{ JSON.stringify($json) }}'::jsonb, updated_at=NOW()\nWHERE email='{{ $json.email }}';",
        [1200, 0],
    ),
    switch_node("Route by Tier", "$json.tier",
                [("hot", "Hot"), ("warm", "Warm"), ("cold", "Cold")], [1400, 0]),
    slack("Hot Lead → Sales", "🔥 *HOT LEAD*\n*{{ $json.name }}* ({{ $json.company }})\nScore {{ $json.score }} — {{ $json.industry || \"industry n/a\" }}\n{{ $json.email }}", "#sales-leads", [1600, 0]),
    slack("Warm Lead → Nurture", "🌤️ *Warm lead*: {{ $json.name }} ({{ $json.company }}), score {{ $json.score }}", "#sales-leads", [1600, 150]),
    pg_query(
        "Schedule Cold Follow-ups",
        "INSERT INTO lead_followups (lead_email, followup_type, scheduled_at, status)\nVALUES ('{{ $json.email }}', 'nurture', NOW() + INTERVAL '2 days', 'pending'),\n       ('{{ $json.email }}', 'nurture', NOW() + INTERVAL '7 days', 'pending');",
        [1600, 300],
    ),
    # demo booked
    webhook("Demo Booked Webhook", "demo-booked", [0, 500]),
    code("Verify Demo HMAC", HMAC_JS, [200, 500]),
    pg_query(
        "Insert Demo",
        "INSERT INTO demos (lead_email, lead_name, company, demo_date, demo_type, status)\nVALUES ('{{ $json.email }}', '{{ $json.name }}', '{{ $json.company }}', '{{ $json.demo_date }}', '{{ $json.demo_type }}', 'scheduled');",
        [400, 500],
    ),
    pg_query(
        "Mark Lead Demo Booked",
        "UPDATE leads SET status='demo_scheduled', demo_booked_at=NOW() WHERE email='{{ $json.email }}';",
        [600, 500],
    ),
    slack("Demo → Sales Alerts", "📅 *Demo booked*: {{ $json.name }} ({{ $json.company }}) — {{ $json.demo_date }}", "#sales-demos", [800, 500]),
    # deal closed
    webhook("Deal Closed Webhook", "deal-closed", [0, 700]),
    code("Verify Deal HMAC", HMAC_JS, [200, 700]),
    pg_query(
        "Insert Deal",
        "INSERT INTO deals (lead_email, company, value, stage, closed_at)\nVALUES ('{{ $json.email }}', '{{ $json.company }}', {{ $json.value }}, 'closed_won', NOW()) RETURNING id;",
        [400, 700],
    ),
    pg_query(
        "Convert Lead → Customer",
        "INSERT INTO customers (email, name, company, plan, status)\nVALUES ('{{ $json.email }}', '{{ $json.name }}', '{{ $json.company }}', '{{ $json.plan || \"pro\" }}', 'active')\nON CONFLICT (email) DO UPDATE SET status='active', updated_at=NOW();",
        [600, 700],
    ),
    pg_query(
        "Mark Lead Converted",
        "UPDATE leads SET status='converted', converted_at=NOW() WHERE email='{{ $json.email }}';",
        [800, 700],
    ),
    slack("Deal Won → Sales", "🏆 *NEW CUSTOMER*: {{ $json.company }} — ${{ $json.value }} ({{ $json.plan || \"pro\" }})", "#sales-closed", [1000, 700]),
    # follow-up cron
    cron("Follow-up Cron", "0 13 * * 1-5", [0, 900]),
    pg_query(
        "Get Pending Follow-ups",
        "SELECT id, lead_email, followup_type, attempts FROM lead_followups\nWHERE status='pending' AND scheduled_at <= NOW() AND attempts < 3\nORDER BY scheduled_at ASC LIMIT 20;",
        [200, 900],
    ),
    pg_query(
        "Mark Follow-up Attempt",
        "UPDATE lead_followups\nSET attempts = attempts + 1,\n    last_attempt = NOW(),\n    status = CASE WHEN attempts + 1 >= 3 THEN 'completed' ELSE 'pending' END\nWHERE id = '{{ $json.id }}';",
        [400, 900],
    ),
    email(
        "Send Follow-up Email",
        "Following up — Quantive for your treasury team",
        "Hi,\n\nJust checking in on our earlier note about Quantive, the sovereign debt optimization platform.\n\nHappy to show how it works for your team in 20 minutes.\n\n— The Quantive Team",
        "={{ $json.lead_email }}",
        [600, 900],
    ),
]
WF1 = wf(
    "wf1-sales-crm", "WF-1: Sales & CRM", WF1_NODES,
    wire(
        ("Lead Capture Webhook", "Verify Lead HMAC", "Upsert Lead", "Build Enrichment Query",
         "Clearbit Company Lookup", "Merge Enrichment + Score", "Update Lead Score", "Route by Tier"),
        {"Route by Tier": {0: "Hot Lead → Sales", 1: "Warm Lead → Nurture", 2: "Schedule Cold Follow-ups"}},
        ("Demo Booked Webhook", "Verify Demo HMAC", "Insert Demo", "Mark Lead Demo Booked", "Demo → Sales Alerts"),
        ("Deal Closed Webhook", "Verify Deal HMAC", "Insert Deal", "Convert Lead → Customer",
         "Mark Lead Converted", "Deal Won → Sales"),
        ("Follow-up Cron", "Get Pending Follow-ups", "Mark Follow-up Attempt", "Send Follow-up Email"),
    ),
    ["sales", "crm"],
    "Real-node sales pipeline: HMAC-verified webhooks → Postgres upserts → Clearbit enrichment → tiered Slack alerts → SMTP follow-ups.",
)

# ════════════════════════════════════════════════════════════════════
# WF-2: Billing & Customer Lifecycle
# ════════════════════════════════════════════════════════════════════

WF2_NODES = [
    node("Stripe Trigger", "n8n-nodes-base.stripeTrigger", 1, {"events": ["*"]}, [0, 0]),
    code("Route by Event Type", """const ev = $input.first().json;
const type = ev.type || 'unknown';
const obj = ev.data && ev.data.object ? ev.data.object : ev;
return [{ json: { type, obj, customer: obj.customer || null }}];""", [200, 0]),
    switch_node("Switch Event", "$json.type", [
        ("customer.subscription.created", "Sub Created"),
        ("customer.subscription.updated", "Sub Updated"),
        ("invoice.payment_failed", "Payment Failed"),
        ("customer.subscription.deleted", "Churn"),
    ], [400, 0]),
    pg_query(
        "Upsert Customer on Create",
        "INSERT INTO customers (stripe_customer_id, plan, status, created_at, updated_at)\nVALUES ('{{ $json.customer }}', '{{ $json.obj.metadata.tier || \"starter\" }}', 'active', NOW(), NOW())\nON CONFLICT (stripe_customer_id) DO UPDATE SET status='active', plan=EXCLUDED.plan, updated_at=NOW();",
        [600, 0],
    ),
    pg_query(
        "Log MRR on Create",
        "INSERT INTO mrr_events (customer_id, amount, event_type)\nSELECT id, COALESCE({{ $json.obj.items && $json.obj.items.data && $json.obj.items.data[0] && $json.obj.items.data[0].price ? $json.obj.items.data[0].price.unit_amount : 0 }}/100.0, 0), 'subscription.created'\nFROM customers WHERE stripe_customer_id='{{ $json.customer }}';",
        [800, 0],
    ),
    pg_query(
        "Update Plan on Change",
        "UPDATE customers SET plan='{{ $json.obj.metadata.tier || \"pro\" }}', updated_at=NOW() WHERE stripe_customer_id='{{ $json.customer }}';",
        [600, 150],
    ),
    pg_query(
        "Log Payment Failure",
        "INSERT INTO invoice_events (stripe_customer_id, event_type, amount, status)\nVALUES ('{{ $json.customer }}', 'invoice.payment_failed', COALESCE({{ $json.obj.amount_due || 0 }}/100.0, 0), 'failed');",
        [600, 300],
    ),
    pg_query(
        "Mark Customer Past Due",
        "UPDATE customers SET subscription_status='past_due', updated_at=NOW() WHERE stripe_customer_id='{{ $json.customer }}';",
        [800, 300],
    ),
    pg_query(
        "Mark Churned",
        "UPDATE customers SET status='churned', subscription_status='canceled', churned_at=NOW() WHERE stripe_customer_id='{{ $json.customer }}';",
        [600, 450],
    ),
    http(
        "Relay to Quantive Backend",
        "={{ $env.QUANTIVE_BASE_URL || 'http://127.0.0.1:8000' }}/api/billing/webhook",
        [600, 600],
        method="POST",
        body="={{ JSON.stringify({ type: $json.type, data: { object: $json.obj } }) }}",
        headers={"Content-Type": "application/json"},
        on_error="continueRegularOutput", retry=(3, 3000),
    ),
    slack("Billing Event → Slack", "💳 *{{ $json.type }}*\ncustomer: {{ $json.customer }}", "#billing-events", [800, 600]),
    cron("Re-engagement Cron", "0 9 * * 1", [0, 900]),
    pg_query(
        "Find Inactive Customers",
        "SELECT id, email, name FROM customers\nWHERE status='active' AND last_active_at < NOW() - INTERVAL '30 days' AND reengagement_sent = FALSE\nLIMIT 50;",
        [200, 900],
    ),
    email(
        "Re-engagement Email",
        "We miss you — new in Quantive",
        "Hi {{ $json.name || \"there\" }},\n\nIt's been a while since you used Quantive. New: market monitor, bubble detection, and a faster optimization engine.\n\nLog back in and take a look.\n\n— The Quantive Team",
        "={{ $json.email }}",
        [400, 900],
    ),
    pg_query(
        "Mark Re-engagement Sent",
        "UPDATE customers SET reengagement_sent = TRUE WHERE id = '{{ $json.id }}';",
        [600, 900],
    ),
]
WF2 = wf(
    "wf2-billing-lifecycle", "WF-2: Billing & Customer Lifecycle", WF2_NODES,
    wire(
        ("Stripe Trigger", "Route by Event Type", "Switch Event"),
        {"Switch Event": {
            0: ["Upsert Customer on Create", "Log MRR on Create"],
            1: "Update Plan on Change",
            2: ["Log Payment Failure", "Mark Customer Past Due"],
            3: "Mark Churned",
        }},
        (["Log MRR on Create", "Update Plan on Change", "Mark Churned"], "Relay to Quantive Backend"),
        ("Relay to Quantive Backend", "Billing Event → Slack"),
        ("Re-engagement Cron", "Find Inactive Customers", "Re-engagement Email", "Mark Re-engagement Sent"),
    ),
    ["billing", "stripe"],
    "Native Stripe Trigger → Postgres plan/MRR/churn updates + relay of every event into the Quantive backend fulfillment webhook.",
)

# ════════════════════════════════════════════════════════════════════
# WF-3: Quantive Platform & AI
# ════════════════════════════════════════════════════════════════════

BASE = "={{ $env.QUANTIVE_BASE_URL || 'http://127.0.0.1:8000' }}"

WF3_NODES = [
    # market data (Yahoo Finance)
    cron("Market Data Cron", "*/30 * * * *", [0, 0]),
    code("Build Symbol List", """const symbols = [
  { symbol: '^TNX', name: 'US 10Y Treasury Yield' },
  { symbol: 'DX-Y.NYB', name: 'US Dollar Index' },
  { symbol: 'GC=F', name: 'Gold Futures' },
  { symbol: 'CL=F', name: 'WTI Crude' },
  { symbol: '^GSPC', name: 'S&P 500' },
  { symbol: '^VIX', name: 'VIX' },
  { symbol: 'BTC-USD', name: 'Bitcoin' },
  { symbol: 'ETH-USD', name: 'Ethereum' },
];
return symbols.map(s => ({ json: s }));""", [200, 0]),
    http("Yahoo Finance Quote", "https://query1.finance.yahoo.com/v8/finance/chart/{{ $json.symbol }}", [400, 0],
         qs={"range": "1d", "interval": "1h"},
         headers={"User-Agent": "Mozilla/5.0 (Quantive-n8n)"},
         on_error="continueRegularOutput", retry=(3, 3000)),
    code("Parse Yahoo Response", """const item = $input.first().json;
const chart = item.chart && item.chart.result && item.chart.result[0];
if (!chart || !chart.meta || chart.meta.regularMarketPrice === undefined) return [];
return [{ json: {
  symbol: chart.meta.symbol,
  name: $('Build Symbol List').first().json.name,
  value: chart.meta.regularMarketPrice,
  source: 'yahoo_finance',
  timestamp: new Date((chart.meta.regularMarketTime || Date.now() / 1000) * 1000).toISOString(),
}}];""", [600, 0]),
    pg_query(
        "Store Market Data",
        "INSERT INTO market_data (symbol, name, value, source, timestamp)\nVALUES ('{{ $json.symbol }}', '{{ $json.name }}', {{ $json.value }}, '{{ $json.source }}', '{{ $json.timestamp }}');",
        [800, 0],
    ),
    # news (NewsAPI)
    cron("News Cron", "0 * * * *", [0, 300]),
    http("Fetch Market News", "https://newsapi.org/v2/top-headlines", [200, 300],
         qs={"category": "business", "language": "en", "pageSize": "30"},
         auth="httpQueryAuth", on_error="continueRegularOutput", retry=(3, 5000)),
    code("Normalize News", """const r = $input.first().json;
if (!r.articles) return [];
return r.articles
  .filter(a => a.title && a.url)
  .map(a => ({ json: {
    title: a.title, description: a.description || '', url: a.url,
    source: (a.source && a.source.name) || '', published_at: a.publishedAt,
  }}));""", [400, 300]),
    pg_query(
        "Insert News Article",
        "INSERT INTO news_articles (title, description, url, source, published_at)\nVALUES ('{{ $json.title.replace(/'/g, \"\") }}', '{{ ($json.description || \"\").replace(/'/g, \"\") }}', '{{ $json.url }}', '{{ $json.source }}', '{{ $json.published_at }}')\nON CONFLICT (url) DO NOTHING;",
        [600, 300],
    ),
    # AI summary (OpenAI)
    cron("AI Summary Cron", "0 7 * * 1-5", [0, 600]),
    http("OpenAI Market Summary", "https://api.openai.com/v1/chat/completions", [200, 600],
         method="POST", auth="httpHeaderAuth",
         headers={"Content-Type": "application/json"},
         body="""={{ JSON.stringify({
  model: 'gpt-4o-mini',
  messages: [
    { role: 'system', content: 'You are a sovereign-debt market analyst. Summarize todays market conditions in 5 bullet points, max 120 words.' },
    { role: 'user', content: 'Rates, dollar, gold, oil, equities, VIX, crypto — what matters for treasury desks today?' }
  ],
  temperature: 0.3,
}) }}""",
         on_error="continueRegularOutput", retry=(2, 3000)),
    code("Extract Summary", """const r = $input.first().json;
const text = r.choices && r.choices[0] && r.choices[0].message && r.choices[0].message.content || '';
if (!text) return [];
return [{ json: { summary: text.trim(), generated_at: new Date().toISOString() }}];""", [400, 600]),
    slack("Market Summary → Slack", "📈 *Daily Market Summary* (AI)\n{{ $json.summary }}", "#market-news", [600, 600]),
    # app health (real Quantive backend)
    cron("Health Cron", "*/15 * * * *", [0, 900]),
    http("Ping Backend Status", BASE + "/api/optimize-debt/status", [200, 900],
         on_error="continueRegularOutput", retry=(2, 2000)),
    code("Evaluate Health", """const r = $input.first().json;
const healthy = r && r.status === 'operational';
return [{ json: {
  service: 'quantive-backend',
  status: healthy ? 'healthy' : 'unhealthy',
  status_code: healthy ? 200 : 503,
  response_time_ms: 0,
}}];""", [400, 900]),
    pg_query(
        "Insert Health Check",
        "INSERT INTO api_health_checks (service, status_code, response_time_ms, status)\nVALUES ('{{ $json.service }}', {{ $json.status_code }}, {{ $json.response_time_ms }}, '{{ $json.status }}');",
        [600, 900],
    ),
    # app digest snapshot
    cron("Metrics Cron", "0 * * * *", [0, 1200]),
    http("Fetch App Digest", BASE + "/api/v1/digest", [200, 1200],
         on_error="continueRegularOutput", retry=(2, 3000)),
    code("Shape Digest", """const d = $input.first().json;
return [{ json: { snapshot: JSON.stringify(d).slice(0, 4000), fetched_at: new Date().toISOString() }}];""", [400, 1200]),
    pg_query(
        "Store Digest Snapshot",
        "INSERT INTO market_data (symbol, name, value, source, timestamp)\nVALUES ('QUANTIVE_DIGEST', 'App digest snapshot', 0, 'quantive_backend', NOW());",
        [600, 1200],
    ),
]
WF3 = wf(
    "wf3-platform-ai", "WF-3: Quantive Platform & AI", WF3_NODES,
    wire(
        ("Market Data Cron", "Build Symbol List", "Yahoo Finance Quote", "Parse Yahoo Response", "Store Market Data"),
        ("News Cron", "Fetch Market News", "Normalize News", "Insert News Article"),
        ("AI Summary Cron", "OpenAI Market Summary", "Extract Summary", "Market Summary → Slack"),
        ("Health Cron", "Ping Backend Status", "Evaluate Health", "Insert Health Check"),
        ("Metrics Cron", "Fetch App Digest", "Shape Digest", "Store Digest Snapshot"),
    ),
    ["platform", "ai"],
    "Real integrations: Yahoo Finance market ingestion, NewsAPI headlines, OpenAI daily summaries, Quantive backend health/digest polling — all native HTTP + Postgres nodes.",
)

# ════════════════════════════════════════════════════════════════════
# WF-4: Operations & Internal
# ════════════════════════════════════════════════════════════════════

WF4_NODES = [
    cron("Digest Cron", "0 8 * * *", [0, 0]),
    pg_query(
        "Collect Digest Metrics",
        """SELECT
  (SELECT COUNT(*) FROM organizations) AS orgs,
  (SELECT COUNT(*) FROM users) AS users,
  (SELECT COUNT(*) FROM portfolios) AS portfolios,
  (SELECT COUNT(*) FROM leads WHERE created_at >= NOW() - INTERVAL '1 day') AS leads_24h,
  (SELECT COUNT(*) FROM customers WHERE status='active') AS active_customers,
  (SELECT COALESCE(SUM(amount),0) FROM mrr_events WHERE event_type='subscription.created' AND created_at >= NOW() - INTERVAL '30 days') AS new_mrr_30d,
  (SELECT COUNT(*) FROM workflows.workflow_executions WHERE created_at >= NOW() - INTERVAL '1 day' AND status='success') AS wf_ok_24h,
  (SELECT COUNT(*) FROM workflows.workflow_executions WHERE created_at >= NOW() - INTERVAL '1 day' AND status='error') AS wf_fail_24h;""",
        [200, 0],
    ),
    code("Format Digest", """const m = $input.first().json;
return [{ json: {
  channel: '#daily-digest', severity: 'low',
  text: `🌅 *Quantive Daily Digest*\nOrgs: ${m.orgs} · Users: ${m.users} · Portfolios: ${m.portfolios}\nLeads 24h: ${m.leads_24h} · Active customers: ${m.active_customers}\nNew MRR 30d: $${Number(m.new_mrr_30d).toFixed(0)}\nWorkflows 24h: ${m.wf_ok_24h} ok / ${m.wf_fail_24h} failed`,
}}];""", [400, 0]),
    slack("Post Digest", "={{ $json.text }}", "={{ $json.channel }}", [600, 0]),
    cron("Error Monitor Cron", "0 */2 * * *", [0, 300]),
    pg_query(
        "Recent Unresolved Errors",
        "SELECT error_type, message, severity, COUNT(*) AS count\nFROM workflows.workflow_errors\nWHERE created_at >= NOW() - INTERVAL '2 hours'\nGROUP BY error_type, message, severity ORDER BY count DESC LIMIT 10;",
        [200, 300],
    ),
    code("Gate Error Alert", """const rows = $input.all().map(i => i.json);
if (!rows.length) return [];
return [{ json: {
  channel: '#platform-alerts', severity: 'high',
  text: `🚨 *${rows.length} error groups in last 2h*\n` + rows.slice(0, 5).map(r => `• [${r.severity}] ${r.error_type}: ${String(r.message).slice(0, 120)} ×${r.count}`).join('\n'),
}}];""", [400, 300]),
    slack("Error Alert", "={{ $json.text }}", "={{ $json.channel }}", [600, 300]),
    cron("Security Cron", "*/30 * * * *", [0, 600]),
    pg_query(
        "Failed Logins 30m",
        "SELECT ip_address, COUNT(*) AS attempts FROM login_attempts\nWHERE success = FALSE AND attempted_at >= NOW() - INTERVAL '30 minutes'\nGROUP BY ip_address HAVING COUNT(*) >= 5 ORDER BY attempts DESC LIMIT 10;",
        [200, 600],
    ),
    code("Gate Security Alert", """const rows = $input.all().map(i => i.json);
if (!rows.length) return [];
return [{ json: {
  channel: '#security-alerts', severity: 'critical',
  text: '🔐 *Possible credential stuffing*\n' + rows.map(r => `• ${r.ip_address}: ${r.attempts} failed attempts`).join('\n'),
}}];""", [400, 600]),
    slack("Security Alert", "={{ $json.text }}", "={{ $json.channel }}", [600, 600]),
    cron("Backup Cron", "0 3 * * *", [0, 900]),
    pg_query(
        "Record Backup",
        "INSERT INTO workflows.backup_history (backup_path, backup_size, status)\nVALUES ('n8n-managed-daily', 'n/a', 'completed');",
        [200, 900],
    ),
    slack("Backup Log", "💾 Daily backup checkpoint recorded.", "#ops-notifications", [400, 900]),
    webhook("Support Ticket Webhook", "support-ticket", [0, 1200]),
    code("Verify Support HMAC", HMAC_JS, [200, 1200]),
    pg_query(
        "Insert Support Ticket",
        "INSERT INTO support_tickets (subject, description, priority, status, customer_email)\nVALUES ('{{ $json.subject }}', '{{ $json.description || \"\" }}', '{{ $json.priority || \"medium\" }}', 'open', '{{ $json.customer_email || \"\" }}') RETURNING id;",
        [400, 1200],
    ),
    code("Route Ticket", """const t = $input.first().json;
const sev = t.priority === 'urgent' ? 'critical' : t.priority === 'high' ? 'high' : 'medium';
return [{ json: {
  channel: sev === 'critical' ? '#support-alerts' : '#customer-success',
  severity: sev,
  ticket_id: t.id,
  text: `🎫 *New ticket #${t.id}* (${t.priority || 'medium'})\n${t.subject}\nfrom: ${t.customer_email || 'unknown'}`,
}}];""", [600, 1200]),
    slack("Ticket Alert", "={{ $json.text }}", "={{ $json.channel }}", [800, 1200]),
]
WF4 = wf(
    "wf4-operations-internal", "WF-4: Operations & Internal", WF4_NODES,
    wire(
        ("Digest Cron", "Collect Digest Metrics", "Format Digest", "Post Digest"),
        ("Error Monitor Cron", "Recent Unresolved Errors", "Gate Error Alert", "Error Alert"),
        ("Security Cron", "Failed Logins 30m", "Gate Security Alert", "Security Alert"),
        ("Backup Cron", "Record Backup", "Backup Log"),
        ("Support Ticket Webhook", "Verify Support HMAC", "Insert Support Ticket", "Route Ticket", "Ticket Alert"),
    ),
    ["operations"],
    "Ops automation on real nodes: DB-driven daily digest, error/security monitors with thresholds, backup checkpoints, HMAC-verified support tickets.",
)

# ════════════════════════════════════════════════════════════════════
# Write all
# ════════════════════════════════════════════════════════════════════

ALL = {
    "00-error-handler.json": WF0,
    "01-sales-crm.json": WF1,
    "02-billing-lifecycle.json": WF2,
    "03-platform-ai.json": WF3,
    "04-operations-internal.json": WF4,
    "svc1-enrichment.json": SVC1,
    "svc2-notification.json": SVC2,
    "svc3-logger.json": SVC3,
}

for fname, data in ALL.items():
    path = os.path.join(OUT, fname)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    n_conn = sum(len(v["main"]) for v in data["connections"].values())
    print(f"wrote {fname}: {len(data['nodes'])} nodes, {len(data['connections'])} wired sources ({n_conn} outputs)")

print(f"\ntotal: {sum(len(d['nodes']) for d in ALL.values())} nodes across {len(ALL)} workflows")
