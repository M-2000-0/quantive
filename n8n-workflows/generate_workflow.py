#!/usr/bin/env python3
"""Generate the Quantive Stripe Billing n8n workflow JSON file."""
import json
import os

def build_workflow():
    workflow = {
        "name": "Quantive Stripe Billing - Complete Sovereign Debt Platform",
        "nodes": [],
        "connections": {},
        "active": False,
        "settings": {
            "executionOrder": "v1",
            "saveManualExecutions": True,
            "callerPolicy": "workflowsFromSameOwner"
        },
        "staticData": None,
        "tags": [{"name": "billing"}, {"name": "stripe"}, {"name": "quantive"}],
        "pinData": {},
        "versionId": "1",
        "id": "quantive-stripe-billing-complete"
    }

    nodes = []

    # SECTION 1: Stripe Webhook Receiver
    nodes.append({
        "parameters": {"httpMethod": "POST", "path": "stripe-billing", "responseMode": "responseNode", "options": {}},
        "id": "a1b2c3d4-0001-0000-0000-000000000001",
        "name": "Stripe Webhook Receiver",
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 2,
        "position": [0, 0],
        "webhookId": "stripe-billing-webhook"
    })

    nodes.append({
        "parameters": {"jsCode": "const crypto = require('crypto');\nconst webhookSecret = $env.STRIPE_WEBHOOK_SECRET;\nconst signature = $input.first().headers['stripe-signature'];\nconst rawBody = $input.first().rawBody || JSON.stringify($input.first().json.body);\nconst timestamp = signature?.match(/t=(\\d+)/)?.[1];\nconst signatures = signature?.match(/v1=([a-f0-9]+)/g);\n\nif (!webhookSecret || !signature || !timestamp || !signatures) {\n  throw new Error('Invalid webhook signature - missing required components');\n}\n\nconst signedPayload = `${timestamp}.${rawBody}`;\nconst expectedSignature = crypto.createHmac('sha256', webhookSecret).update(signedPayload).digest('hex');\n\nlet isValid = false;\nfor (const sig of signatures) {\n  const v1 = sig.replace('v1=', '');\n  if (crypto.timingSafeEqual(Buffer.from(expectedSignature, 'hex'), Buffer.from(v1, 'hex'))) {\n    isValid = true;\n    break;\n  }\n}\n\nif (!isValid) {\n  throw new Error('Invalid webhook signature - HMAC verification failed');\n}\n\nconst event = $input.first().json.body;\nreturn [{\n  json: {\n    eventType: event.type,\n    eventId: event.id,\n    data: event.data,\n    created: event.created,\n    apiVersion: event.api_version,\n    livemode: event.livemode\n  }\n}];"},
        "id": "a1b2c3d4-0001-0000-0000-000000000002",
        "name": "Verify Stripe Signature",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [250, 0]
    })

    nodes.append({
        "parameters": {
            "rules": {
                "rules": [
                    {"value": "checkout.session.completed", "output": 0},
                    {"value": "customer.subscription.created", "output": 1},
                    {"value": "customer.subscription.updated", "output": 1},
                    {"value": "customer.subscription.deleted", "output": 2},
                    {"value": "invoice.payment_succeeded", "output": 3},
                    {"value": "invoice.payment_failed", "output": 4}
                ],
                "fallbackOutput": 5
            },
            "dataType": "string",
            "value1": "={{ $json.eventType }}"
        },
        "id": "a1b2c3d4-0001-0000-0000-000000000003",
        "name": "Route by Event Type",
        "type": "n8n-nodes-base.switch",
        "typeVersion": 3,
        "position": [500, 0]
    })

    nodes.append({
        "parameters": {
            "respondWith": "json",
            "responseBody": "={{ JSON.stringify({ received: true, event: $json.eventId, timestamp: new Date().toISOString() }) }}",
            "options": {"responseCode": 200}
        },
        "id": "a1b2c3d4-0001-0000-0000-000000000004",
        "name": "Webhook Response OK",
        "type": "n8n-nodes-base.respondToWebhook",
        "typeVersion": 1,
        "position": [750, 0]
    })

    # SECTION 2: Checkout Flow
    nodes.append({
        "parameters": {
            "method": "GET",
            "url": "=https://{{ $env.QUANTIVE_BASE_URL }}/api/billing/checkout/{{ $json.data.object.id }}",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "options": {"timeout": 30000}
        },
        "id": "a1b2c3d4-0002-0000-0000-000000000001",
        "name": "Fetch Checkout Session",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [750, 200],
        "credentials": {"httpHeaderAuth": {"id": "REPLACE_WITH_HEADER_AUTH_CREDENTIAL_ID", "name": "Quantive API Auth"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const checkout = $input.first().json;\nconst metadata = checkout.metadata || {};\nconst customer = checkout.customer_details || {};\nconst lineItems = checkout.line_items || {};\n\nconst customerEmail = customer.email || metadata.customer_email || null;\nconst planId = metadata.plan_id || lineItems.data?.[0]?.price?.id || 'unknown';\nconst amountTotal = checkout.amount_total || 0;\nconst currency = checkout.currency || 'usd';\nconst customerId = checkout.customer || null;\nconst sessionId = checkout.id;\nconst paymentStatus = checkout.payment_status || 'unpaid';\nconst subscriptionId = checkout.subscription || null;\n\nif (!customerEmail) {\n  throw new Error('No customer email found in checkout session');\n}\n\nreturn [{\n  json: {\n    sessionId, customerEmail, planId, amountTotal,\n    currency, customerId, paymentStatus, subscriptionId,\n    metadata, createdAt: new Date().toISOString()\n  }\n}];"},
        "id": "a1b2c3d4-0002-0000-0000-000000000002",
        "name": "Extract Checkout Data",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1000, 200]
    })

    nodes.append({
        "parameters": {
            "method": "POST",
            "url": "=https://{{ $env.QUANTIVE_BASE_URL }}/api/automation/webhooks/external-run",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ event: 'checkout.completed', payload: $json, hmac: crypto.createHmac('sha256', $env.QUANTIVE_WEBHOOK_SECRET).update(JSON.stringify($json)).digest('hex'), timestamp: new Date().toISOString(), source: 'stripe-checkout' }) }}",
            "options": {"timeout": 30000}
        },
        "id": "a1b2c3d4-0002-0000-0000-000000000003",
        "name": "Trigger Backend Checkout Webhook",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1250, 200],
        "credentials": {"httpHeaderAuth": {"id": "REPLACE_WITH_HEADER_AUTH_CREDENTIAL_ID", "name": "Quantive API Auth"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "operation": "insert",
            "table": "billing_events",
            "columns": "event_type, event_id, session_id, customer_email, plan_id, amount_total, currency, customer_id, subscription_id, metadata, created_at",
            "options": {}
        },
        "id": "a1b2c3d4-0002-0000-0000-000000000004",
        "name": "Insert Checkout Billing Event",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1500, 200],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    # SECTION 3: Subscription Management
    nodes.append({
        "parameters": {"jsCode": "const subscription = $input.first().json.data.object;\nreturn [{\n  json: {\n    subscriptionId: subscription.id, customerId: subscription.customer, status: subscription.status,\n    planId: subscription.items?.data?.[0]?.price?.id || subscription.plan?.id || 'unknown',\n    currentPeriodStart: subscription.current_period_start, currentPeriodEnd: subscription.current_period_end,\n    trialStart: subscription.trial_start, trialEnd: subscription.trial_end,\n    canceledAt: subscription.canceled_at, cancelAtPeriodEnd: subscription.cancel_at_period_end,\n    metadata: subscription.metadata || {}, livemode: subscription.livemode || false,\n    startDate: subscription.start_date, collectionMethod: subscription.collection_method || 'charge_automatically',\n    eventType: $input.first().json.eventType, processedAt: new Date().toISOString()\n  }\n}];"},
        "id": "a1b2c3d4-0003-0000-0000-000000000001",
        "name": "Extract Subscription Data",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [750, 450]
    })

    nodes.append({
        "parameters": {
            "method": "POST",
            "url": "=https://{{ $env.QUANTIVE_BASE_URL }}/api/billing/webhook/stripe",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ event: $json.eventType, subscription: { id: $json.subscriptionId, customer: $json.customerId, status: $json.status, plan_id: $json.planId, current_period_end: $json.currentPeriodEnd, trial_end: $json.trialEnd, canceled_at: $json.canceledAt, cancel_at_period_end: $json.cancelAtPeriodEnd, metadata: $json.metadata }, hmac: crypto.createHmac('sha256', $env.QUANTIVE_WEBHOOK_SECRET).update(JSON.stringify($json)).digest('hex'), timestamp: new Date().toISOString() }) }}",
            "options": {"timeout": 30000}
        },
        "id": "a1b2c3d4-0003-0000-0000-000000000002",
        "name": "Forward to Billing Webhook",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1000, 450],
        "credentials": {"httpHeaderAuth": {"id": "REPLACE_WITH_HEADER_AUTH_CREDENTIAL_ID", "name": "Quantive API Auth"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "rules": {
                "rules": [
                    {"value": "active", "output": 0}, {"value": "past_due", "output": 1},
                    {"value": "canceled", "output": 2}, {"value": "trialing", "output": 3},
                    {"value": "incomplete", "output": 4}, {"value": "incomplete_expired", "output": 4},
                    {"value": "unpaid", "output": 1}
                ],
                "fallbackOutput": 5
            },
            "dataType": "string",
            "value1": "={{ $json.status }}"
        },
        "id": "a1b2c3d4-0003-0000-0000-000000000003",
        "name": "Route by Subscription Status",
        "type": "n8n-nodes-base.switch",
        "typeVersion": 3,
        "position": [1250, 450]
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE users SET subscription_tier = CASE\n  WHEN $1 LIKE '%enterprise%' THEN 'enterprise'\n  WHEN $1 LIKE '%professional%' THEN 'professional'\n  WHEN $1 LIKE '%starter%' THEN 'starter'\n  WHEN $1 LIKE '%basic%' THEN 'basic'\n  ELSE 'free'\nEND, subscription_id = $2, subscription_status = $3,\nsubscription_current_period_end = to_timestamp($4), updated_at = NOW()\nWHERE stripe_customer_id = $5;\n\nINSERT INTO subscription_history (subscription_id, customer_id, status, plan_id, current_period_end, changed_at)\nVALUES ($2, $5, $3, $1, to_timestamp($4), NOW());",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $json.planId }}"}, {"name": "$2", "value": "={{ $json.subscriptionId }}"},
                {"name": "$3", "value": "={{ $json.status }}"}, {"name": "$4", "value": "={{ $json.currentPeriodEnd }}"},
                {"name": "$5", "value": "={{ $json.customerId }}"}
            ]}
        },
        "id": "a1b2c3d4-0003-0000-0000-000000000004",
        "name": "Update User Tier - Active",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1550, 350],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE subscriptions SET status = 'past_due', updated_at = NOW() WHERE subscription_id = $1;\n\nINSERT INTO dunning_cases (subscription_id, customer_id, status, attempt, max_attempts, schedule_hours, next_attempt_at, created_at)\nVALUES ($1, $2, 'open', 0, 3, 6, NOW() + INTERVAL '6 hours', NOW())\nON CONFLICT (subscription_id) DO UPDATE SET status = 'open', attempt = 0, updated_at = NOW();",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $json.subscriptionId }}"},
                {"name": "$2", "value": "={{ $json.customerId }}"}
            ]}
        },
        "id": "a1b2c3d4-0003-0000-0000-000000000005",
        "name": "Create Dunning Case",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1550, 480],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE subscriptions SET status = 'canceled', canceled_at = NOW(), updated_at = NOW() WHERE subscription_id = $1;\n\nUPDATE users SET subscription_tier = 'free', subscription_status = 'canceled', updated_at = NOW() WHERE stripe_customer_id = $2;",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $json.subscriptionId }}"},
                {"name": "$2", "value": "={{ $json.customerId }}"}
            ]}
        },
        "id": "a1b2c3d4-0003-0000-0000-000000000006",
        "name": "Handle Subscription Cancellation",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1550, 610],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE subscriptions SET status = 'trialing', trial_start = to_timestamp($3), trial_end = to_timestamp($4), updated_at = NOW() WHERE subscription_id = $1;\n\nINSERT INTO subscription_history (subscription_id, customer_id, status, plan_id, trial_start, trial_end, changed_at)\nVALUES ($1, $2, 'trialing', $5, to_timestamp($3), to_timestamp($4), NOW());",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $json.subscriptionId }}"}, {"name": "$2", "value": "={{ $json.customerId }}"},
                {"name": "$3", "value": "={{ $json.trialStart }}"}, {"name": "$4", "value": "={{ $json.trialEnd }}"},
                {"name": "$5", "value": "={{ $json.planId }}"}
            ]}
        },
        "id": "a1b2c3d4-0003-0000-0000-000000000007",
        "name": "Handle Subscription Trialing",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1550, 740],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE subscriptions SET status = $1, updated_at = NOW() WHERE subscription_id = $2;\n\nINSERT INTO subscription_history (subscription_id, customer_id, status, changed_at)\nVALUES ($2, $3, $1, NOW());",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $json.status }}"}, {"name": "$2", "value": "={{ $json.subscriptionId }}"},
                {"name": "$3", "value": "={{ $json.customerId }}"}
            ]}
        },
        "id": "a1b2c3d4-0003-0000-0000-000000000008",
        "name": "Handle Other Subscription Status",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1550, 870],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    # SECTION 4: Payment Processing
    nodes.append({
        "parameters": {"jsCode": "const invoice = $input.first().json.data.object;\nreturn [{\n  json: {\n    invoiceId: invoice.id, customerId: invoice.customer, subscriptionId: invoice.subscription,\n    amountPaid: invoice.amount_paid || 0, amountDue: invoice.amount_due || 0,\n    currency: invoice.currency || 'usd', status: invoice.status, attemptCount: invoice.attempt_count || 0,\n    billingReason: invoice.billing_reason || 'unknown', paymentIntentId: invoice.payment_intent,\n    hostedInvoiceUrl: invoice.hosted_invoice_url, invoicePdf: invoice.invoice_pdf,\n    periodStart: invoice.period_start, periodEnd: invoice.period_end,\n    metadata: invoice.metadata || {}, eventType: $input.first().json.eventType,\n    processedAt: new Date().toISOString()\n  }\n}];"},
        "id": "a1b2c3d4-0004-0000-0000-000000000001",
        "name": "Extract Invoice Data",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [750, 1050]
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "INSERT INTO invoice_history (invoice_id, customer_id, subscription_id, amount_paid, amount_due, currency, status, attempt_count, billing_reason, payment_intent_id, hosted_invoice_url, invoice_pdf, period_start, period_end, metadata, event_type, created_at)\nVALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, to_timestamp($13), to_timestamp($14), $15, $16, NOW())\nON CONFLICT (invoice_id) DO UPDATE SET amount_paid = $4, amount_due = $5, status = $7, updated_at = NOW();\n\nUPDATE customers SET total_paid = total_paid + $4, last_payment_at = NOW(), updated_at = NOW() WHERE stripe_customer_id = $2;",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $json.invoiceId }}"}, {"name": "$2", "value": "={{ $json.customerId }}"},
                {"name": "$3", "value": "={{ $json.subscriptionId }}"}, {"name": "$4", "value": "={{ $json.amountPaid }}"},
                {"name": "$5", "value": "={{ $json.amountDue }}"}, {"name": "$6", "value": "={{ $json.currency }}"},
                {"name": "$7", "value": "={{ $json.status }}"}, {"name": "$8", "value": "={{ $json.attemptCount }}"},
                {"name": "$9", "value": "={{ $json.billingReason }}"}, {"name": "$10", "value": "={{ $json.paymentIntentId }}"},
                {"name": "$11", "value": "={{ $json.hostedInvoiceUrl }}"}, {"name": "$12", "value": "={{ $json.invoicePdf }}"},
                {"name": "$13", "value": "={{ $json.periodStart }}"}, {"name": "$14", "value": "={{ $json.periodEnd }}"},
                {"name": "$15", "value": "={{ JSON.stringify($json.metadata) }}"},
                {"name": "$16", "value": "={{ $json.eventType }}"}
            ]}
        },
        "id": "a1b2c3d4-0004-0000-0000-000000000002",
        "name": "Log Payment Success",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1050, 950],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const inv = $input.first().json;\nconst email = inv.metadata?.customer_email || 'billing@quantive.com';\nconst name = inv.metadata?.customer_name || 'Valued Customer';\nconst amt = (inv.amountDue / 100).toFixed(2);\nconst cur = inv.currency.toUpperCase();\nconst attempt = inv.attemptCount;\nconst url = inv.hostedInvoiceUrl;\nreturn [{\n  json: {\n    customerEmail: email,\n    subject: `Action Required: Payment Failed for Your Quantive Subscription (Attempt ${attempt}/3)`,\n    body: `Dear ${name},\\n\\nWe were unable to process your payment of ${cur} ${amt} for your Quantive subscription.\\n\\nThis is attempt ${attempt} of 3. If payment is not resolved, your subscription will be canceled.\\n\\nPlease update your payment method:\\n${url}\\n\\nContact billing@quantive.com for assistance.\\n\\nThe Quantive Billing Team`,\n    invoiceId: inv.invoiceId, customerId: inv.customerId, attemptCount: attempt\n  }\n}];"},
        "id": "a1b2c3d4-0004-0000-0000-000000000003",
        "name": "Generate Failed Payment Email",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1050, 1100]
    })

    nodes.append({
        "parameters": {
            "fromEmail": "billing@quantive.com", "toEmail": "={{ $json.customerEmail }}",
            "subject": "={{ $json.subject }}", "emailType": "text", "message": "={{ $json.body }}",
            "options": {"appendAttribution": False}
        },
        "id": "a1b2c3d4-0004-0000-0000-000000000004",
        "name": "Send Failed Payment Email",
        "type": "n8n-nodes-base.emailSend",
        "typeVersion": 2.1,
        "position": [1300, 1100],
        "credentials": {"smtp": {"id": "REPLACE_WITH_SMTP_CREDENTIAL_ID", "name": "Quantive SMTP"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const inv = $input.first().json;\nreturn [{\n  json: {\n    text: `Payment Failed: Invoice ${inv.invoiceId} - Amount: ${(inv.amountDue / 100).toFixed(2)} ${inv.currency.toUpperCase()}`,\n    blocks: [\n      { type: 'header', text: { type: 'plain_text', text: ':rotating_light: Payment Failed Alert', emoji: true } },\n      { type: 'section', fields: [\n        { type: 'mrkdwn', text: `*Invoice:*\\n${inv.invoiceId}` },\n        { type: 'mrkdwn', text: `*Customer:*\\n${inv.customerId}` },\n        { type: 'mrkdwn', text: `*Amount:*\\n${(inv.amountDue / 100).toFixed(2)} ${inv.currency.toUpperCase()}` },\n        { type: 'mrkdwn', text: `*Attempt:*\\n${inv.attemptCount}/3` }\n      ]}\n    ]\n  }\n}];"},
        "id": "a1b2c3d4-0004-0000-0000-000000000005",
        "name": "Format Slack Payment Alert",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1050, 1250]
    })

    nodes.append({
        "parameters": {
            "channel": "#billing-alerts", "text": "={{ $json.text }}",
            "otherOptions": {"blocks": "={{ JSON.stringify($json.blocks) }}", "unfurl_links": False, "unfurl_media": False}
        },
        "id": "a1b2c3d4-0004-0000-0000-000000000006",
        "name": "Send Slack Payment Alert",
        "type": "n8n-nodes-base.slack",
        "typeVersion": 2.2,
        "position": [1300, 1250],
        "credentials": {"slackApi": {"id": "REPLACE_WITH_SLACK_CREDENTIAL_ID", "name": "Quantive Slack"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "INSERT INTO dunning_cases (subscription_id, customer_id, invoice_id, status, attempt, max_attempts, schedule_hours, next_attempt_at, created_at)\nVALUES ($1, $2, $3, 'open', 0, 3, 6, NOW() + INTERVAL '6 hours', NOW())\nON CONFLICT (subscription_id) DO UPDATE SET status = 'open', invoice_id = $3, attempt = 0, next_attempt_at = NOW() + INTERVAL '6 hours', updated_at = NOW();\n\nINSERT INTO payment_failures (invoice_id, customer_id, subscription_id, amount_due, currency, attempt_count, billing_reason, created_at)\nVALUES ($3, $2, $1, $4, $5, $6, $7, NOW());",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $json.subscriptionId }}"}, {"name": "$2", "value": "={{ $json.customerId }}"},
                {"name": "$3", "value": "={{ $json.invoiceId }}"}, {"name": "$4", "value": "={{ $json.amountDue }}"},
                {"name": "$5", "value": "={{ $json.currency }}"}, {"name": "$6", "value": "={{ $json.attemptCount }}"},
                {"name": "$7", "value": "={{ $json.billingReason }}"}
            ]}
        },
        "id": "a1b2c3d4-0004-0000-0000-000000000007",
        "name": "Create Dunning Case from Payment Failure",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1550, 1050],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "method": "POST",
            "url": "=https://{{ $env.QUANTIVE_BASE_URL }}/api/automation/webhooks/external-run",
            "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
            "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ event: 'invoice.payment_failed', payload: { invoice_id: $json.invoiceId, customer_id: $json.customerId, subscription_id: $json.subscriptionId, amount_due: $json.amountDue, currency: $json.currency, attempt_count: $json.attemptCount, billing_reason: $json.billingReason }, hmac: crypto.createHmac('sha256', $env.QUANTIVE_WEBHOOK_SECRET).update(JSON.stringify($json)).digest('hex'), timestamp: new Date().toISOString(), source: 'stripe-payment-failure' }) }}",
            "options": {"timeout": 30000}
        },
        "id": "a1b2c3d4-0004-0000-0000-000000000008",
        "name": "Notify Backend Payment Failure",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1800, 1050],
        "credentials": {"httpHeaderAuth": {"id": "REPLACE_WITH_HEADER_AUTH_CREDENTIAL_ID", "name": "Quantive API Auth"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    # SECTION 5: Failed-Payment Recovery (Dunning)
    nodes.append({
        "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": 6}]}},
        "id": "a1b2c3d4-0005-0000-0000-000000000001",
        "name": "Dunning Schedule - Every 6 Hours",
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": [0, 1500]
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "SELECT dc.id as dunning_id, dc.subscription_id, dc.customer_id, dc.invoice_id, dc.status, dc.attempt, dc.max_attempts, dc.next_attempt_at, s.plan_id, s.status as subscription_status, u.email as customer_email, u.full_name as customer_name, ih.amount_due, ih.currency, ih.hosted_invoice_url\nFROM dunning_cases dc\nJOIN subscriptions s ON dc.subscription_id = s.subscription_id\nJOIN users u ON dc.customer_id = u.stripe_customer_id\nLEFT JOIN invoice_history ih ON dc.invoice_id = ih.invoice_id\nWHERE dc.status = 'open' AND dc.attempt < dc.max_attempts AND dc.next_attempt_at <= NOW()\nORDER BY dc.next_attempt_at ASC LIMIT 50;"
        },
        "id": "a1b2c3d4-0005-0000-0000-000000000002",
        "name": "Fetch Open Dunning Cases",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [250, 1500],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const cases = $input.all();\nif (!cases || cases.length === 0) {\n  return [{ json: { noCases: true, message: 'No open dunning cases' } }];\n}\nreturn cases.map(item => {\n  const c = item.json;\n  const attempt = (c.attempt || 0) + 1;\n  const maxAttempts = c.max_attempts || 3;\n  const scheduleHours = attempt === 1 ? 6 : attempt === 2 ? 12 : 24;\n  const nextAttempt = new Date(Date.now() + scheduleHours * 60 * 60 * 1000);\n  return {\n    json: { ...c, attempt, maxAttempts, scheduleHours, nextAttempt: nextAttempt.toISOString(),\n      shouldCancel: attempt >= maxAttempts, amountFormatted: c.amount_due ? (c.amount_due / 100).toFixed(2) : '0.00' }\n  };\n});"},
        "id": "a1b2c3d4-0005-0000-0000-000000000003",
        "name": "Process Dunning Cases",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [500, 1500]
    })

    nodes.append({
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [{"id": "condition-attempt-check", "leftValue": "={{ $json.shouldCancel }}", "rightValue": False, "operator": {"type": "boolean", "operation": "equals"}}],
                "combinator": "and"
            }
        },
        "id": "a1b2c3d4-0005-0000-0000-000000000004",
        "name": "Is Attempt Below Max?",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [750, 1500]
    })

    nodes.append({
        "parameters": {"jsCode": "const c = $input.first().json;\nconst attempt = c.attempt;\nconst name = c.customer_name || 'Valued Customer';\nconst amt = c.amountFormatted;\nconst cur = (c.currency || 'usd').toUpperCase();\nconst url = c.hosted_invoice_url || 'https://dashboard.quantive.com/billing';\nconst subjects = { 1: 'Action Required: Payment Reminder', 2: 'URGENT: Second Notice - Payment Overdue', 3: 'FINAL NOTICE: Subscription Will Be Canceled' };\nconst bodies = {\n  1: `Dear ${name},\\n\\nThis is a friendly reminder that your payment of ${cur} ${amt} could not be processed.\\n\\nPlease update your payment method within 24 hours.\\n\\nUpdate: ${url}\\n\\nThe Quantive Billing Team`,\n  2: `Dear ${name},\\n\\nThis is your second notice. Your payment of ${cur} ${amt} remains outstanding.\\n\\nYour subscription is at risk of suspension. Update immediately: ${url}\\n\\nThe Quantive Billing Team`,\n  3: `Dear ${name},\\n\\nFINAL NOTICE. Your payment of ${cur} ${amt} has been overdue.\\n\\nIf not paid within 72 hours, your subscription will be canceled.\\n\\nLast chance: ${url}\\n\\nThe Quantive Billing Team`\n};\nreturn [{ json: { customerEmail: c.customer_email, subject: subjects[attempt] || subjects[3], body: bodies[attempt] || bodies[3], attempt } }];"},
        "id": "a1b2c3d4-0005-0000-0000-000000000005",
        "name": "Generate Dunning Email",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1000, 1400]
    })

    nodes.append({
        "parameters": {
            "fromEmail": "billing@quantive.com", "toEmail": "={{ $json.customerEmail }}",
            "subject": "={{ $json.subject }}", "emailType": "text", "message": "={{ $json.body }}",
            "options": {"appendAttribution": False}
        },
        "id": "a1b2c3d4-0005-0000-0000-000000000006",
        "name": "Send Dunning Email",
        "type": "n8n-nodes-base.emailSend",
        "typeVersion": 2.1,
        "position": [1250, 1400],
        "credentials": {"smtp": {"id": "REPLACE_WITH_SMTP_CREDENTIAL_ID", "name": "Quantive SMTP"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE dunning_cases SET attempt = $1, next_attempt_at = NOW() + ($2 || ' hours')::INTERVAL, updated_at = NOW() WHERE id = $3;",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $json.attempt }}"},
                {"name": "$2", "value": "={{ $json.attempt === 1 ? '6' : $json.attempt === 2 ? '12' : '24' }}"},
                {"name": "$3", "value": "={{ $('Process Dunning Cases').item.json.dunning_id }}"}
            ]}
        },
        "id": "a1b2c3d4-0005-0000-0000-000000000007",
        "name": "Update Dunning Attempt",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1500, 1400],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "method": "DELETE",
            "url": "=https://api.stripe.com/v1/subscriptions/{{ $('Process Dunning Cases').item.json.subscription_id }}",
            "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
            "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ prorate: true, invoice_now: true }) }}",
            "options": {"timeout": 30000}
        },
        "id": "a1b2c3d4-0005-0000-0000-000000000008",
        "name": "Cancel Subscription - Max Attempts",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1000, 1650],
        "credentials": {"httpHeaderAuth": {"id": "REPLACE_WITH_STRIPE_API_CREDENTIAL_ID", "name": "Stripe API Auth"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE dunning_cases SET status = 'closed', close_reason = 'max_attempts_reached', closed_at = NOW(), updated_at = NOW() WHERE id = $1;\n\nUPDATE subscriptions SET status = 'canceled', canceled_at = NOW(), cancellation_reason = 'payment_failure', updated_at = NOW() WHERE subscription_id = $2;\n\nUPDATE users SET subscription_tier = 'free', subscription_status = 'canceled', updated_at = NOW() WHERE stripe_customer_id = $3;",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $('Process Dunning Cases').item.json.dunning_id }}"},
                {"name": "$2", "value": "={{ $('Process Dunning Cases').item.json.subscription_id }}"},
                {"name": "$3", "value": "={{ $('Process Dunning Cases').item.json.customer_id }}"}
            ]}
        },
        "id": "a1b2c3d4-0005-0000-0000-000000000009",
        "name": "Close Dunning & Update Subscription",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1250, 1650],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    # SECTION 6: Cancellation Handling
    nodes.append({
        "parameters": {"jsCode": "const subscription = $input.first().json.data.object;\nreturn [{\n  json: {\n    subscriptionId: subscription.id, customerId: subscription.customer,\n    cancellationReason: subscription.cancellation_details?.reason || 'not_provided',\n    cancellationComment: subscription.cancellation_details?.comment || '',\n    canceledAt: subscription.canceled_at, cancelAtPeriodEnd: subscription.cancel_at_period_end,\n    currentPeriodEnd: subscription.current_period_end, metadata: subscription.metadata || {},\n    customerEmail: subscription.metadata?.customer_email || null,\n    customerName: subscription.metadata?.customer_name || null,\n    processedAt: new Date().toISOString()\n  }\n}];"},
        "id": "a1b2c3d4-0006-0000-0000-000000000001",
        "name": "Extract Cancellation Reason",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [750, 1900]
    })

    nodes.append({
        "parameters": {
            "method": "POST",
            "url": "=https://{{ $env.QUANTIVE_BASE_URL }}/api/billing/cancel-subscription",
            "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
            "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ subscription_id: $json.subscriptionId, customer_id: $json.customerId, reason: $json.cancellationReason, comment: $json.cancellationComment, canceled_at: $json.canceledAt, hmac: crypto.createHmac('sha256', $env.QUANTIVE_WEBHOOK_SECRET).update(JSON.stringify($json)).digest('hex') }) }}",
            "options": {"timeout": 30000}
        },
        "id": "a1b2c3d4-0006-0000-0000-000000000002",
        "name": "Notify Backend Cancellation",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1000, 1900],
        "credentials": {"httpHeaderAuth": {"id": "REPLACE_WITH_HEADER_AUTH_CREDENTIAL_ID", "name": "Quantive API Auth"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const c = $input.first().json;\nconst name = c.customerName || 'Valued Customer';\nconst email = c.customerEmail || 'customer@example.com';\nconst reasons = { 'canceled': 'You have chosen to cancel.', 'payment_failed': 'Canceled due to payment failures.', 'requested_by_customer': 'You requested cancellation.', 'not_provided': 'Your subscription has been canceled.' };\nconst reasonText = reasons[c.cancellationReason] || `Canceled: ${c.cancellationReason}.`;\nreturn [{\n  json: {\n    customerEmail: email,\n    subject: 'Quantive Subscription Cancellation Confirmation',\n    body: `Dear ${name},\\n\\n${reasonText}\\n\\nSubscription ID: ${c.subscriptionId}\\nCanceled: ${new Date(c.canceledAt * 1000).toLocaleDateString()}\\nAccess Until: ${new Date(c.currentPeriodEnd * 1000).toLocaleDateString()}\\n\\nYour data is retained for 30 days. Resubscribe at https://quantive.com/pricing\\n\\nThe Quantive Team`\n  }\n}];"},
        "id": "a1b2c3d4-0006-0000-0000-000000000003",
        "name": "Generate Cancellation Confirmation Email",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1250, 1800]
    })

    nodes.append({
        "parameters": {
            "fromEmail": "billing@quantive.com", "toEmail": "={{ $json.customerEmail }}",
            "subject": "={{ $json.subject }}", "emailType": "text", "message": "={{ $json.body }}",
            "options": {"appendAttribution": False}
        },
        "id": "a1b2c3d4-0006-0000-0000-000000000004",
        "name": "Send Cancellation Confirmation",
        "type": "n8n-nodes-base.emailSend",
        "typeVersion": 2.1,
        "position": [1500, 1800],
        "credentials": {"smtp": {"id": "REPLACE_WITH_SMTP_CREDENTIAL_ID", "name": "Quantive SMTP"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE subscriptions SET status = 'canceled', canceled_at = to_timestamp($1), cancellation_reason = $2, cancellation_comment = $3, updated_at = NOW() WHERE subscription_id = $4;\n\nUPDATE users SET subscription_tier = 'free', subscription_status = 'canceled', subscription_canceled_at = to_timestamp($1), updated_at = NOW() WHERE stripe_customer_id = $5;\n\nINSERT INTO subscription_history (subscription_id, customer_id, status, cancellation_reason, changed_at) VALUES ($4, $5, 'canceled', $2, NOW());",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $('Extract Cancellation Reason').item.json.canceledAt }}"},
                {"name": "$2", "value": "={{ $('Extract Cancellation Reason').item.json.cancellationReason }}"},
                {"name": "$3", "value": "={{ $('Extract Cancellation Reason').item.json.cancellationComment }}"},
                {"name": "$4", "value": "={{ $('Extract Cancellation Reason').item.json.subscriptionId }}"},
                {"name": "$5", "value": "={{ $('Extract Cancellation Reason').item.json.customerId }}"}
            ]}
        },
        "id": "a1b2c3d4-0006-0000-0000-000000000005",
        "name": "Update Subscription Status - Canceled",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1500, 1950],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const c = $('Extract Cancellation Reason').first().json;\nreturn [{\n  json: {\n    text: `Subscription Canceled: ${c.subscriptionId} - Customer: ${c.customerId} - Reason: ${c.cancellationReason}`,\n    blocks: [\n      { type: 'header', text: { type: 'plain_text', text: ':chart_with_downwards_trend: Subscription Canceled', emoji: true } },\n      { type: 'section', fields: [\n        { type: 'mrkdwn', text: `*Subscription:*\\n${c.subscriptionId}` },\n        { type: 'mrkdwn', text: `*Customer:*\\n${c.customerId}` },\n        { type: 'mrkdwn', text: `*Reason:*\\n${c.cancellationReason}` },\n        { type: 'mrkdwn', text: `*Canceled At:*\\n${new Date(c.canceledAt * 1000).toLocaleDateString()}` }\n      ]}\n    ]\n  }\n}];"},
        "id": "a1b2c3d4-0006-0000-0000-000000000006",
        "name": "Format Churn Alert",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1750, 1900]
    })

    nodes.append({
        "parameters": {
            "channel": "#churn-alerts", "text": "={{ $json.text }}",
            "otherOptions": {"blocks": "={{ JSON.stringify($json.blocks) }}", "unfurl_links": False, "unfurl_media": False}
        },
        "id": "a1b2c3d4-0006-0000-0000-000000000007",
        "name": "Send Churn Alert to Slack",
        "type": "n8n-nodes-base.slack",
        "typeVersion": 2.2,
        "position": [2000, 1900],
        "credentials": {"slackApi": {"id": "REPLACE_WITH_SLACK_CREDENTIAL_ID", "name": "Quantive Slack"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    # SECTION 7: Upgrade/Downgrade
    nodes.append({
        "parameters": {"jsCode": "const sub = $input.first().json.data?.object || $input.first().json;\nconst oldPlanId = sub.items?.data?.[0]?.price?.id || sub.old_plan?.id || 'unknown';\nconst newPlanId = sub.items?.data?.[0]?.price?.id || sub.plan?.id || 'unknown';\nconst oldAmount = (sub.old_plan?.amount || 0) / 100;\nconst newAmount = (sub.plan?.amount || 0) / 100;\nconst isUpgrade = newAmount > oldAmount && oldAmount > 0;\nconst isDowngrade = newAmount < oldAmount && oldAmount > 0;\nreturn [{\n  json: {\n    subscriptionId: sub.id, customerId: sub.customer, oldPlanId, newPlanId, isUpgrade, isDowngrade,\n    oldAmount, newAmount, effectiveDate: sub.current_period_end,\n    metadata: sub.metadata || {}, processedAt: new Date().toISOString()\n  }\n}];"},
        "id": "a1b2c3d4-0007-0000-0000-000000000001",
        "name": "Compare Old vs New Plan",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [750, 2200]
    })

    nodes.append({
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [{"id": "condition-is-upgrade", "leftValue": "={{ $json.isUpgrade }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}],
                "combinator": "and"
            }
        },
        "id": "a1b2c3d4-0007-0000-0000-000000000002",
        "name": "Is Upgrade?",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [1000, 2200]
    })

    nodes.append({
        "parameters": {"jsCode": "const c = $input.first().json;\nreturn [{ json: { ...c, changeType: 'upgrade', effectiveImmediately: true } }];"},
        "id": "a1b2c3d4-0007-0000-0000-000000000003",
        "name": "Handle Upgrade",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1250, 2100]
    })

    nodes.append({
        "parameters": {"jsCode": "const c = $input.first().json;\nreturn [{ json: { ...c, changeType: 'downgrade', effectiveImmediately: false, effectiveDate: c.effectiveDate } }];"},
        "id": "a1b2c3d4-0007-0000-0000-000000000004",
        "name": "Handle Downgrade",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1250, 2300]
    })

    nodes.append({
        "parameters": {"jsCode": "const c = $input.first().json;\nconst name = c.metadata?.customer_name || 'Valued Customer';\nconst isUpgrade = c.changeType === 'upgrade';\nreturn [{\n  json: {\n    customerEmail: c.metadata?.customer_email || 'customer@example.com',\n    subject: isUpgrade ? 'Your Quantive Plan Has Been Upgraded' : 'Your Quantive Plan Change is Scheduled',\n    body: `Dear ${name},\\n\\nYour plan has been ${isUpgrade ? 'upgraded' : 'changed'}.\\n\\nPrevious: ${c.oldPlanId}\\nNew: ${c.newPlanId}\\n${isUpgrade ? 'Effective immediately.' : `Effective: ${new Date(c.effectiveDate * 1000).toLocaleDateString()}`}\\n\\nThe Quantive Team`\n  }\n}];"},
        "id": "a1b2c3d4-0007-0000-0000-000000000005",
        "name": "Generate Plan Change Email",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1500, 2200]
    })

    nodes.append({
        "parameters": {
            "fromEmail": "billing@quantive.com", "toEmail": "={{ $json.customerEmail }}",
            "subject": "={{ $json.subject }}", "emailType": "text", "message": "={{ $json.body }}",
            "options": {"appendAttribution": False}
        },
        "id": "a1b2c3d4-0007-0000-0000-000000000006",
        "name": "Send Plan Change Confirmation",
        "type": "n8n-nodes-base.emailSend",
        "typeVersion": 2.1,
        "position": [1750, 2200],
        "credentials": {"smtp": {"id": "REPLACE_WITH_SMTP_CREDENTIAL_ID", "name": "Quantive SMTP"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "method": "POST",
            "url": "=https://{{ $env.QUANTIVE_BASE_URL }}/api/automation/webhooks/external-run",
            "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
            "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ event: 'subscription.plan_changed', payload: { subscription_id: $('Compare Old vs New Plan').item.json.subscriptionId, customer_id: $('Compare Old vs New Plan').item.json.customerId, old_plan_id: $('Compare Old vs New Plan').item.json.oldPlanId, new_plan_id: $('Compare Old vs New Plan').item.json.newPlanId, change_type: $('Compare Old vs New Plan').item.json.changeType }, hmac: crypto.createHmac('sha256', $env.QUANTIVE_WEBHOOK_SECRET).update(JSON.stringify($('Compare Old vs New Plan').item.json)).digest('hex'), timestamp: new Date().toISOString(), source: 'stripe-plan-change' }) }}",
            "options": {"timeout": 30000}
        },
        "id": "a1b2c3d4-0007-0000-0000-000000000007",
        "name": "Notify Backend Plan Change",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [2000, 2200],
        "credentials": {"httpHeaderAuth": {"id": "REPLACE_WITH_HEADER_AUTH_CREDENTIAL_ID", "name": "Quantive API Auth"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    # SECTION 8: Customer Portal
    nodes.append({
        "parameters": {"httpMethod": "POST", "path": "customer-portal", "responseMode": "responseNode", "options": {}},
        "id": "a1b2c3d4-0008-0000-0000-000000000001",
        "name": "Customer Portal Webhook",
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 2,
        "position": [0, 2600],
        "webhookId": "customer-portal-webhook"
    })

    nodes.append({
        "parameters": {"jsCode": "const req = $input.first().json.body;\nconst customerId = req.customer_id || req.customerId;\nconst email = req.email;\nconst returnUrl = req.return_url || `${$env.QUANTIVE_BASE_URL}/dashboard`;\nif (!customerId && !email) { throw new Error('Either customer_id or email is required'); }\nreturn [{ json: { customerId, email, returnUrl } }];"},
        "id": "a1b2c3d4-0008-0000-0000-000000000002",
        "name": "Extract Portal Request",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [250, 2600]
    })

    nodes.append({
        "parameters": {"jsCode": "const c = $input.first().json;\nlet customerId = c.customerId;\nif (!customerId && c.email) {\n  const resp = await this.helpers.httpRequest({\n    method: 'GET',\n    url: `https://api.stripe.com/v1/customers?email=${encodeURIComponent(c.email)}&limit=1`,\n    headers: { 'Authorization': `Bearer ${$env.STRIPE_SECRET_KEY}` }\n  });\n  if (resp.data && resp.data.length > 0) { customerId = resp.data[0].id; }\n  else { throw new Error(`No Stripe customer found for email: ${c.email}`); }\n}\nreturn [{ json: { customerId, returnUrl: c.returnUrl } }];"},
        "id": "a1b2c3d4-0008-0000-0000-000000000003",
        "name": "Lookup Stripe Customer",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [500, 2600]
    })

    nodes.append({
        "parameters": {
            "method": "POST",
            "url": "https://api.stripe.com/v1/billing_portal/sessions",
            "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
            "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ customer: $json.customerId, return_url: $json.returnUrl, configuration: { business_profile: { headline: 'Manage your Quantive subscription', privacy_policy_url: $env.QUANTIVE_BASE_URL + '/privacy', terms_of_service_url: $env.QUANTIVE_BASE_URL + '/terms' }, features: { customer_update: { enabled: true, allowed_updates: ['email', 'tax_id'] }, invoice_history: { enabled: true }, payment_method_update: { enabled: true }, subscription_cancel: { enabled: true, mode: 'at_period_end', cancellation_reason: { enabled: true, options: ['too_expensive', 'missing_features', 'unused', 'other'] } }, subscription_update: { enabled: true, products: [{ product: $env.STRIPE_PRODUCT_STARTER, prices: [$env.STRIPE_PRICE_STARTER_MONTHLY, $env.STRIPE_PRICE_STARTER_YEARLY] }, { product: $env.STRIPE_PRODUCT_PROFESSIONAL, prices: [$env.STRIPE_PRICE_PROFESSIONAL_MONTHLY, $env.STRIPE_PRICE_PROFESSIONAL_YEARLY] }, { product: $env.STRIPE_PRODUCT_ENTERPRISE, prices: [$env.STRIPE_PRICE_ENTERPRISE_MONTHLY, $env.STRIPE_PRICE_ENTERPRISE_YEARLY] }] } } } }) }}",
            "options": {"timeout": 30000}
        },
        "id": "a1b2c3d4-0008-0000-0000-000000000004",
        "name": "Create Stripe Portal Session",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [750, 2600],
        "credentials": {"httpHeaderAuth": {"id": "REPLACE_WITH_STRIPE_API_CREDENTIAL_ID", "name": "Stripe API Auth"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "respondWith": "json",
            "responseBody": "={{ JSON.stringify({ portal_url: $json.url, expires_at: $json.expires_at }) }}",
            "options": {"responseCode": 200}
        },
        "id": "a1b2c3d4-0008-0000-0000-000000000005",
        "name": "Return Portal URL",
        "type": "n8n-nodes-base.respondToWebhook",
        "typeVersion": 1,
        "position": [1000, 2600]
    })

    # SECTION 9: Subscription Status Check
    nodes.append({
        "parameters": {"rule": {"interval": [{"field": "hours", "hoursInterval": 1}]}},
        "id": "a1b2c3d4-0009-0000-0000-000000000001",
        "name": "Status Check Schedule - Hourly",
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": [0, 2900]
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "SELECT s.subscription_id, s.customer_id, s.status as current_status, s.plan_id, s.current_period_end, s.last_checked_at, u.email as customer_email\nFROM subscriptions s\nJOIN users u ON s.customer_id = u.stripe_customer_id\nWHERE s.status IN ('active', 'past_due') AND (s.last_checked_at IS NULL OR s.last_checked_at < NOW() - INTERVAL '30 minutes')\nORDER BY s.last_checked_at ASC NULLS FIRST LIMIT 100;"
        },
        "id": "a1b2c3d4-0009-0000-0000-000000000002",
        "name": "Fetch Active Subscriptions",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [250, 2900],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const subs = $input.all();\nif (!subs || subs.length === 0) { return [{ json: { noSubscriptions: true } }]; }\nreturn subs.map(item => ({\n  json: { subscriptionId: item.json.subscription_id, customerId: item.json.customer_id, currentStatus: item.json.current_status,\n    planId: item.json.plan_id, currentPeriodEnd: item.json.current_period_end, customerEmail: item.json.customer_email }\n}));"},
        "id": "a1b2c3d4-0009-0000-0000-000000000003",
        "name": "Prepare Subscription Checks",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [500, 2900]
    })

    nodes.append({
        "parameters": {
            "method": "GET",
            "url": "=https://api.stripe.com/v1/subscriptions/{{ $json.subscriptionId }}",
            "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
            "options": {"timeout": 15000}
        },
        "id": "a1b2c3d4-0009-0000-0000-000000000004",
        "name": "Check Subscription Status via Stripe",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [750, 2900],
        "credentials": {"httpHeaderAuth": {"id": "REPLACE_WITH_STRIPE_API_CREDENTIAL_ID", "name": "Stripe API Auth"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const stripeSub = $input.first().json;\nconst localSub = $('Prepare Subscription Checks').first().json;\nconst stripeStatus = stripeSub.status;\nconst localStatus = localSub.currentStatus;\nconst statusChanged = stripeStatus !== localStatus;\nconst statusDegraded = statusChanged && ((localStatus === 'active' && ['past_due', 'canceled', 'unpaid'].includes(stripeStatus)) || (localStatus === 'past_due' && ['canceled', 'unpaid'].includes(stripeStatus)));\nreturn [{\n  json: { subscriptionId: localSub.subscriptionId, customerId: localSub.customerId, localStatus, stripeStatus, statusChanged, statusDegraded,\n    planId: stripeSub.items?.data?.[0]?.price?.id || localSub.planId, currentPeriodEnd: stripeSub.current_period_end, customerEmail: localSub.customerEmail }\n}];"},
        "id": "a1b2c3d4-0009-0000-0000-000000000005",
        "name": "Compare Status",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1000, 2900]
    })

    nodes.append({
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [{"id": "condition-status-changed", "leftValue": "={{ $json.statusChanged }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}],
                "combinator": "and"
            }
        },
        "id": "a1b2c3d4-0009-0000-0000-000000000006",
        "name": "Status Changed?",
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [1250, 2900]
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE subscriptions SET status = $1, current_period_end = to_timestamp($2), last_checked_at = NOW(), updated_at = NOW() WHERE subscription_id = $3;\n\nINSERT INTO subscription_history (subscription_id, customer_id, status, previous_status, changed_at, change_source) VALUES ($3, $4, $1, $5, NOW(), 'hourly_check');",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $json.stripeStatus }}"}, {"name": "$2", "value": "={{ $json.currentPeriodEnd }}"},
                {"name": "$3", "value": "={{ $json.subscriptionId }}"}, {"name": "$4", "value": "={{ $json.customerId }}"},
                {"name": "$5", "value": "={{ $json.localStatus }}"}
            ]}
        },
        "id": "a1b2c3d4-0009-0000-0000-000000000007",
        "name": "Update Local Status",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1500, 2800],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const c = $input.first().json;\nreturn [{\n  json: {\n    text: `Subscription Status Degraded: ${c.subscriptionId} - ${c.localStatus} -> ${c.stripeStatus}`,\n    blocks: [\n      { type: 'header', text: { type: 'plain_text', text: ':warning: Subscription Status Degraded', emoji: true } },\n      { type: 'section', fields: [\n        { type: 'mrkdwn', text: `*Subscription:*\\n${c.subscriptionId}` },\n        { type: 'mrkdwn', text: `*Customer:*\\n${c.customerId}` },\n        { type: 'mrkdwn', text: `*Previous:*\\n${c.localStatus}` },\n        { type: 'mrkdwn', text: `*New:*\\n${c.stripeStatus}` }\n      ]}\n    ]\n  }\n}];"},
        "id": "a1b2c3d4-0009-0000-0000-000000000008",
        "name": "Format Status Degradation Alert",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1500, 3000]
    })

    nodes.append({
        "parameters": {
            "channel": "#billing-alerts", "text": "={{ $json.text }}",
            "otherOptions": {"blocks": "={{ JSON.stringify($json.blocks) }}", "unfurl_links": False, "unfurl_media": False}
        },
        "id": "a1b2c3d4-0009-0000-0000-000000000009",
        "name": "Send Status Degradation Alert",
        "type": "n8n-nodes-base.slack",
        "typeVersion": 2.2,
        "position": [1750, 3000],
        "credentials": {"slackApi": {"id": "REPLACE_WITH_SLACK_CREDENTIAL_ID", "name": "Quantive Slack"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "UPDATE subscriptions SET last_checked_at = NOW() WHERE subscription_id = $1;",
            "additionalFields": {"queryValues": [{"name": "$1", "value": "={{ $json.subscriptionId }}"}]}
        },
        "id": "a1b2c3d4-0009-0000-0000-000000000010",
        "name": "Update Last Checked",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1750, 2800],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    # SECTION 10: Revenue Tracking (MRR)
    nodes.append({
        "parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": "0 0 * * *"}]}},
        "id": "a1b2c3d4-0010-0000-0000-000000000001",
        "name": "MRR Schedule - Daily Midnight",
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": [0, 3300]
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "WITH active_subs AS (SELECT s.subscription_id, s.plan_id, s.status, p.amount_monthly, p.amount_yearly, p.billing_interval FROM subscriptions s JOIN plans p ON s.plan_id = p.plan_id WHERE s.status IN ('active', 'trialing') AND s.current_period_end > EXTRACT(EPOCH FROM NOW())),\nrevenue_calc AS (SELECT plan_id, COUNT(*) as subscriber_count, SUM(CASE WHEN billing_interval = 'yearly' THEN amount_yearly / 12.0 ELSE amount_monthly END) as monthly_revenue FROM active_subs GROUP BY plan_id),\ntotal_mrr AS (SELECT SUM(monthly_revenue) as total_mrr FROM revenue_calc),\nchurn_data AS (SELECT COUNT(*) as churned_count FROM subscriptions WHERE status = 'canceled' AND canceled_at >= NOW() - INTERVAL '30 days'),\nnew_subs AS (SELECT COUNT(*) as new_count FROM subscriptions WHERE created_at >= NOW() - INTERVAL '30 days' AND status IN ('active', 'trialing'))\nSELECT (SELECT total_mrr FROM total_mrr) as mrr, (SELECT total_mrr FROM total_mrr) * 12 as arr,\n(SELECT subscriber_count FROM revenue_calc) as total_subscribers,\n(SELECT new_count FROM new_subs) as new_subscribers_30d, (SELECT churned_count FROM churn_data) as churned_30d,\nCASE WHEN (SELECT subscriber_count FROM revenue_calc) > 0 THEN ROUND((SELECT churned_count FROM churn_data)::numeric / NULLIF((SELECT subscriber_count FROM revenue_calc) + (SELECT churned_count FROM churn_data), 0) * 100, 2) ELSE 0 END as churn_rate_pct;"
        },
        "id": "a1b2c3d4-0010-0000-0000-000000000002",
        "name": "Calculate MRR Metrics",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [250, 3300],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const m = $input.first().json;\nconst mrr = parseFloat(m.mrr) || 0;\nconst arr = parseFloat(m.arr) || 0;\nconst totalSubs = parseInt(m.total_subscribers) || 0;\nconst newSubs = parseInt(m.new_subscribers_30d) || 0;\nconst churned = parseInt(m.churned_30d) || 0;\nconst churnRate = parseFloat(m.churn_rate_pct) || 0;\nconst arpu = totalSubs > 0 ? mrr / totalSubs : 0;\nconst ltv = arpu > 0 && churnRate > 0 ? arpu / (churnRate / 100) : 0;\nreturn [{\n  json: {\n    snapshotDate: new Date().toISOString().split('T')[0], snapshotTimestamp: new Date().toISOString(),\n    mrr: Math.round(mrr * 100) / 100, arr: Math.round(arr * 100) / 100,\n    totalSubscribers: totalSubs, newSubscribers: newSubs, churnedSubscribers: churned,\n    churnRate: Math.round(churnRate * 100) / 100, netRevenue: Math.round(mrr * 100) / 100,\n    arpu: Math.round(arpu * 100) / 100, ltv: Math.round(ltv * 100) / 100,\n    expansionRevenue: 0, contractionRevenue: 0\n  }\n}];"},
        "id": "a1b2c3d4-0010-0000-0000-000000000003",
        "name": "Compute Revenue Metrics",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [500, 3300]
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "INSERT INTO revenue_snapshots (snapshot_date, snapshot_timestamp, mrr, arr, total_subscribers, new_subscribers_30d, churned_subscribers_30d, churn_rate_pct, net_revenue, arpu, ltv, expansion_revenue, contraction_revenue, created_at)\nVALUES ($1::date, $2::timestamptz, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW())\nON CONFLICT (snapshot_date) DO UPDATE SET mrr = $3, arr = $4, total_subscribers = $5, new_subscribers_30d = $6, churned_subscribers_30d = $7, churn_rate_pct = $8, net_revenue = $9, arpu = $10, ltv = $11, expansion_revenue = $12, contraction_revenue = $13, updated_at = NOW();",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $json.snapshotDate }}"}, {"name": "$2", "value": "={{ $json.snapshotTimestamp }}"},
                {"name": "$3", "value": "={{ $json.mrr }}"}, {"name": "$4", "value": "={{ $json.arr }}"},
                {"name": "$5", "value": "={{ $json.totalSubscribers }}"}, {"name": "$6", "value": "={{ $json.newSubscribers }}"},
                {"name": "$7", "value": "={{ $json.churnedSubscribers }}"}, {"name": "$8", "value": "={{ $json.churnRate }}"},
                {"name": "$9", "value": "={{ $json.netRevenue }}"}, {"name": "$10", "value": "={{ $json.arpu }}"},
                {"name": "$11", "value": "={{ $json.ltv }}"}, {"name": "$12", "value": "={{ $json.expansionRevenue }}"},
                {"name": "$13", "value": "={{ $json.contractionRevenue }}"}
            ]}
        },
        "id": "a1b2c3d4-0010-0000-0000-000000000004",
        "name": "Insert Revenue Snapshot",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [750, 3300],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "method": "POST",
            "url": "=https://{{ $env.QUANTIVE_BASE_URL }}/api/automation/webhooks/external-run",
            "authentication": "genericCredentialType", "genericAuthType": "httpHeaderAuth",
            "sendBody": True, "specifyBody": "json",
            "jsonBody": "={{ JSON.stringify({ event: 'revenue.daily_snapshot', payload: $json, hmac: crypto.createHmac('sha256', $env.QUANTIVE_WEBHOOK_SECRET).update(JSON.stringify($json)).digest('hex'), timestamp: new Date().toISOString(), source: 'revenue-tracking' }) }}",
            "options": {"timeout": 30000}
        },
        "id": "a1b2c3d4-0010-0000-0000-000000000005",
        "name": "Notify Backend Revenue Snapshot",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [1000, 3300],
        "credentials": {"httpHeaderAuth": {"id": "REPLACE_WITH_HEADER_AUTH_CREDENTIAL_ID", "name": "Quantive API Auth"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const m = $input.first().json;\nreturn [{\n  json: {\n    text: `Daily MRR: $${m.mrr.toLocaleString()} | ARR: $${m.arr.toLocaleString()} | Subscribers: ${m.totalSubscribers} | Churn: ${m.churnRate}%`,\n    blocks: [\n      { type: 'header', text: { type: 'plain_text', text: ':bar_chart: Daily MRR Report', emoji: true } },\n      { type: 'section', fields: [\n        { type: 'mrkdwn', text: `*MRR:*\\n$${m.mrr.toLocaleString()}` },\n        { type: 'mrkdwn', text: `*ARR:*\\n$${m.arr.toLocaleString()}` },\n        { type: 'mrkdwn', text: `*Subscribers:*\\n${m.totalSubscribers}` },\n        { type: 'mrkdwn', text: `*New (30d):*\\n${m.newSubscribers}` },\n        { type: 'mrkdwn', text: `*Churned (30d):*\\n${m.churnedSubscribers}` },\n        { type: 'mrkdwn', text: `*Churn Rate:*\\n${m.churnRate}%` },\n        { type: 'mrkdwn', text: `*ARPU:*\\n$${m.arpu.toFixed(2)}` },\n        { type: 'mrkdwn', text: `*LTV:*\\n$${m.ltv.toFixed(2)}` }\n      ]}\n    ]\n  }\n}];"},
        "id": "a1b2c3d4-0010-0000-0000-000000000006",
        "name": "Format MRR Slack Report",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1000, 3450]
    })

    nodes.append({
        "parameters": {
            "channel": "#metrics", "text": "={{ $json.text }}",
            "otherOptions": {"blocks": "={{ JSON.stringify($json.blocks) }}", "unfurl_links": False, "unfurl_media": False}
        },
        "id": "a1b2c3d4-0010-0000-0000-000000000007",
        "name": "Send Daily MRR to Slack",
        "type": "n8n-nodes-base.slack",
        "typeVersion": 2.2,
        "position": [1250, 3450],
        "credentials": {"slackApi": {"id": "REPLACE_WITH_SLACK_CREDENTIAL_ID", "name": "Quantive Slack"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    # SECTION 11: Churn Analysis
    nodes.append({
        "parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": "0 9 * * 1"}]}},
        "id": "a1b2c3d4-0011-0000-0000-000000000001",
        "name": "Churn Analysis Schedule - Weekly",
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.2,
        "position": [0, 3800]
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "WITH churned_subs AS (\n  SELECT s.subscription_id, s.plan_id, s.canceled_at, s.cancellation_reason, s.start_date, p.plan_name, p.amount_monthly,\n    EXTRACT(EPOCH FROM (s.canceled_at - s.start_date)) / 86400 as lifespan_days\n  FROM subscriptions s JOIN plans p ON s.plan_id = p.plan_id JOIN users u ON s.customer_id = u.stripe_customer_id\n  WHERE s.status = 'canceled' AND s.canceled_at >= NOW() - INTERVAL '30 days'\n),\nreason_breakdown AS (SELECT cancellation_reason, COUNT(*) as count, ROUND(COUNT(*)::numeric / NULLIF((SELECT COUNT(*) FROM churned_subs), 0) * 100, 1) as pct FROM churned_subs GROUP BY cancellation_reason),\nplan_breakdown AS (SELECT plan_id, plan_name, COUNT(*) as churned_count, AVG(lifespan_days) as avg_lifespan_days FROM churned_subs GROUP BY plan_id, plan_name)\nSELECT (SELECT COUNT(*) FROM churned_subs) as total_churned, (SELECT AVG(lifespan_days) FROM churned_subs) as avg_customer_lifespan_days,\n(SELECT SUM(COALESCE(amount_monthly, 0)) FROM churned_subs) as lost_monthly_revenue,\n(SELECT json_agg(reason_breakdown) FROM reason_breakdown) as reason_breakdown,\n(SELECT json_agg(plan_breakdown) FROM plan_breakdown) as plan_breakdown;"
        },
        "id": "a1b2c3d4-0011-0000-0000-000000000002",
        "name": "Analyze Churned Subscriptions",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [250, 3800],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const data = $input.first().json;\nconst totalChurned = parseInt(data.total_churned) || 0;\nconst avgLifespan = parseFloat(data.avg_customer_lifespan_days) || 0;\nconst lostRevenue = parseFloat(data.lost_monthly_revenue) || 0;\nconst reportDate = new Date().toISOString().split('T')[0];\nlet reasonBreakdown = [];\ntry { reasonBreakdown = typeof data.reason_breakdown === 'string' ? JSON.parse(data.reason_breakdown) : data.reason_breakdown || []; } catch(e) {}\nlet planBreakdown = [];\ntry { planBreakdown = typeof data.plan_breakdown === 'string' ? JSON.parse(data.plan_breakdown) : data.plan_breakdown || []; } catch(e) {}\nconst emailBody = `Quantive Weekly Churn Analysis Report\\nReport Period: Last 30 days\\n\\nTotal Churned: ${totalChurned}\\nAvg Lifespan: ${avgLifespan.toFixed(1)} days\\nLost Monthly Revenue: $${lostRevenue.toFixed(2)}\\n\\nChurn Reasons:\\n${reasonBreakdown.map(r => `- ${r.cancellation_reason || 'Not provided'}: ${r.count} (${r.pct}%)`).join('\\n')}\\n\\nChurn by Plan:\\n${planBreakdown.map(p => `- ${p.plan_name || p.plan_id}: ${p.churned_count} churned`).join('\\n')}\\n\\nAutomatically generated by Quantive billing system.`;\nreturn [{ json: { reportDate, emailBody, totalChurned, avgLifespan, lostRevenue, reasonBreakdown, planBreakdown } }];"},
        "id": "a1b2c3d4-0011-0000-0000-000000000003",
        "name": "Compute Churn Analysis",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [500, 3800]
    })

    nodes.append({
        "parameters": {
            "fromEmail": "analytics@quantive.com", "toEmail": "admin@quantive.com",
            "subject": "=Quantive Weekly Churn Analysis Report - {{ $json.reportDate }}",
            "emailType": "text", "message": "={{ $json.emailBody }}",
            "options": {"appendAttribution": False}
        },
        "id": "a1b2c3d4-0011-0000-0000-000000000004",
        "name": "Send Churn Report Email",
        "type": "n8n-nodes-base.emailSend",
        "typeVersion": 2.1,
        "position": [750, 3800],
        "credentials": {"smtp": {"id": "REPLACE_WITH_SMTP_CREDENTIAL_ID", "name": "Quantive SMTP"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "INSERT INTO churn_analysis (analysis_date, analysis_type, period_start, period_end, total_churned, avg_customer_lifespan_days, lost_monthly_revenue, reason_breakdown, plan_breakdown, created_at)\nVALUES ($1::date, 'weekly', $2::timestamptz, NOW(), $3, $4, $5, $6::jsonb, $7::jsonb, NOW());",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $json.reportDate }}"},
                {"name": "$2", "value": "={{ new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString() }}"},
                {"name": "$3", "value": "={{ $json.totalChurned }}"}, {"name": "$4", "value": "={{ $json.avgLifespan }}"},
                {"name": "$5", "value": "={{ $json.lostRevenue }}"},
                {"name": "$6", "value": "={{ JSON.stringify($json.reasonBreakdown) }}"},
                {"name": "$7", "value": "={{ JSON.stringify($json.planBreakdown) }}"}
            ]}
        },
        "id": "a1b2c3d4-0011-0000-0000-000000000005",
        "name": "Insert Churn Analysis Record",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1000, 3800],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    # SECTION 12: API Error Monitoring
    nodes.append({
        "parameters": {"jsCode": "try {\n  const error = $input.first().json;\n  const errorType = error.error?.type || error.error?.code || error.message || 'unknown';\n  const statusCode = error.statusCode || error.status || 0;\n  const errorMessage = error.error?.message || error.message || 'Unknown error';\n  const endpoint = error.options?.url || 'unknown';\n  let category = 'unknown'; let severity = 'medium'; let shouldRetry = false; let retryAfter = 0;\n  if (statusCode === 429 || errorType === 'rate_limit_error') { category = 'rate_limit'; severity = 'medium'; shouldRetry = true; retryAfter = parseInt(error.headers?.['retry-after'] || '60'); }\n  else if (statusCode >= 500 || errorType === 'api_error') { category = 'api_error'; severity = 'high'; shouldRetry = true; retryAfter = 30; }\n  else if (statusCode === 401 || statusCode === 403) { category = 'auth_error'; severity = 'critical'; }\n  else if (statusCode === 402) { category = 'payment_required'; severity = 'high'; }\n  else if (statusCode === 404) { category = 'not_found'; severity = 'low'; }\n  else if (errorType === 'stripe_card_error') { category = 'card_error'; severity = 'medium'; }\n  else if (statusCode >= 400 && statusCode < 500) { category = 'client_error'; severity = 'medium'; }\n  return [{ json: { errorType, statusCode, errorMessage, endpoint, timestamp: new Date().toISOString(), category, severity, shouldRetry, retryAfter, fullError: error } }];\n} catch (e) { return [{ json: { errorType: 'catch_error', statusCode: 0, errorMessage: e.message, category: 'other', severity: 'low', shouldRetry: false, retryAfter: 0 } }]; }"},
        "id": "a1b2c3d4-0012-0000-0000-000000000001",
        "name": "Catch & Classify API Errors",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [0, 4200]
    })

    nodes.append({
        "parameters": {
            "rules": {
                "rules": [
                    {"value": "rate_limit", "output": 0}, {"value": "api_error", "output": 0},
                    {"value": "auth_error", "output": 1}, {"value": "payment_required", "output": 1},
                    {"value": "card_error", "output": 2}, {"value": "not_found", "output": 2},
                    {"value": "client_error", "output": 2}
                ],
                "fallbackOutput": 3
            },
            "dataType": "string",
            "value1": "={{ $json.category }}"
        },
        "id": "a1b2c3d4-0012-0000-0000-000000000002",
        "name": "Route by Error Type",
        "type": "n8n-nodes-base.switch",
        "typeVersion": 3,
        "position": [250, 4200]
    })

    nodes.append({
        "parameters": {"jsCode": "const error = $input.first().json;\nconst retryDelay = error.retryAfter || 30;\nconst retryCount = (error.fullError?.retryCount || 0) + 1;\nconst maxRetries = 3;\nif (retryCount >= maxRetries) { return [{ json: { ...error, retryExhausted: true } }]; }\nconst exponentialBackoff = Math.min(retryDelay * Math.pow(2, retryCount - 1), 300);\nreturn [{ json: { ...error, shouldRetry: true, retryDelay: exponentialBackoff, retryCount, maxRetries } }];"},
        "id": "a1b2c3d4-0012-0000-0000-000000000003",
        "name": "Calculate Retry Backoff",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [500, 4100]
    })

    nodes.append({
        "parameters": {"amount": "={{ $json.retryDelay }}", "unit": "seconds"},
        "id": "a1b2c3d4-0012-0000-0000-000000000004",
        "name": "Wait Before Retry",
        "type": "n8n-nodes-base.wait",
        "typeVersion": 1.1,
        "position": [750, 4100]
    })

    nodes.append({
        "parameters": {"jsCode": "const e = $input.first().json;\nreturn [{\n  json: {\n    text: `Backend Error: ${e.errorType} (${e.statusCode}) - ${e.errorMessage}`,\n    blocks: [\n      { type: 'header', text: { type: 'plain_text', text: ':rotating_light: Backend Error Alert', emoji: true } },\n      { type: 'section', fields: [\n        { type: 'mrkdwn', text: `*Error Type:*\\n${e.errorType}` },\n        { type: 'mrkdwn', text: `*Category:*\\n${e.category}` },\n        { type: 'mrkdwn', text: `*Status:*\\n${e.statusCode}` },\n        { type: 'mrkdwn', text: `*Severity:*\\n${e.severity}` },\n        { type: 'mrkdwn', text: `*Endpoint:*\\n${e.endpoint}` },\n        { type: 'mrkdwn', text: `*Time:*\\n${e.timestamp}` }\n      ]}\n    ]\n  }\n}];"},
        "id": "a1b2c3d4-0012-0000-0000-000000000005",
        "name": "Format Backend Error Alert",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [500, 4250]
    })

    nodes.append({
        "parameters": {
            "channel": "#backend-alerts", "text": "={{ $json.text }}",
            "otherOptions": {"blocks": "={{ JSON.stringify($json.blocks) }}", "unfurl_links": False, "unfurl_media": False}
        },
        "id": "a1b2c3d4-0012-0000-0000-000000000006",
        "name": "Send Backend Error Slack",
        "type": "n8n-nodes-base.slack",
        "typeVersion": 2.2,
        "position": [750, 4250],
        "credentials": {"slackApi": {"id": "REPLACE_WITH_SLACK_CREDENTIAL_ID", "name": "Quantive Slack"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const e = $input.first().json;\nreturn [{\n  json: {\n    text: `<!channel> CRITICAL ERROR: ${e.errorType} (${e.statusCode}) - ${e.errorMessage}`,\n    blocks: [\n      { type: 'header', text: { type: 'plain_text', text: ':rotating_light::rotating_light: CRITICAL ERROR - PAGE ON-CALL :rotating_light::rotating_light:', emoji: true } },\n      { type: 'section', fields: [\n        { type: 'mrkdwn', text: `*Error Type:*\\n${e.errorType}` },\n        { type: 'mrkdwn', text: `*Status:*\\n${e.statusCode}` },\n        { type: 'mrkdwn', text: `*Severity:*\\n${e.severity}` },\n        { type: 'mrkdwn', text: `*Endpoint:*\\n${e.endpoint}` }\n      ]},\n      { type: 'section', text: { type: 'mrkdwn', text: `*Error:*\\n\\`${e.errorMessage}\\`\\n\\n<!channel> Immediate attention required.` } }\n    ]\n  }\n}];"},
        "id": "a1b2c3d4-0012-0000-0000-000000000007",
        "name": "Format Critical Error Page",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [500, 4400]
    })

    nodes.append({
        "parameters": {
            "channel": "#on-call-alerts", "text": "={{ $json.text }}",
            "otherOptions": {"blocks": "={{ JSON.stringify($json.blocks) }}", "unfurl_links": False, "unfurl_media": False}
        },
        "id": "a1b2c3d4-0012-0000-0000-000000000008",
        "name": "Page On-Call via Slack",
        "type": "n8n-nodes-base.slack",
        "typeVersion": 2.2,
        "position": [750, 4400],
        "credentials": {"slackApi": {"id": "REPLACE_WITH_SLACK_CREDENTIAL_ID", "name": "Quantive Slack"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    nodes.append({
        "parameters": {"jsCode": "const e = $input.first().json;\nreturn [{ json: { ...e, loggedAt: new Date().toISOString(), actionTaken: 'logged_only' } }];"},
        "id": "a1b2c3d4-0012-0000-0000-000000000009",
        "name": "Log Non-Critical Errors",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [500, 4550]
    })

    nodes.append({
        "parameters": {
            "operation": "executeQuery",
            "query": "INSERT INTO error_logs (error_type, error_code, error_message, endpoint, status_code, category, severity, full_error, created_at)\nVALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, NOW());",
            "additionalFields": {"queryValues": [
                {"name": "$1", "value": "={{ $json.errorType }}"}, {"name": "$2", "value": "={{ $json.errorCode || 'N/A' }}"},
                {"name": "$3", "value": "={{ $json.errorMessage }}"}, {"name": "$4", "value": "={{ $json.endpoint }}"},
                {"name": "$5", "value": "={{ $json.statusCode }}"}, {"name": "$6", "value": "={{ $json.category }}"},
                {"name": "$7", "value": "={{ $json.severity }}"},
                {"name": "$8", "value": "={{ JSON.stringify($json.fullError || $json) }}"}
            ]}
        },
        "id": "a1b2c3d4-0012-0000-0000-000000000010",
        "name": "Log Error to Database",
        "type": "n8n-nodes-base.postgres",
        "typeVersion": 2.5,
        "position": [1000, 4200],
        "credentials": {"postgres": {"id": "REPLACE_WITH_POSTGRES_CREDENTIAL_ID", "name": "Quantive Postgres"}},
        "retryOnFail": True, "maxTries": 3, "onError": "continueRegularOutput"
    })

    workflow["nodes"] = nodes

    # CONNECTIONS
    workflow["connections"] = {
        "Stripe Webhook Receiver": {"main": [[{"node": "Verify Stripe Signature", "type": "main", "index": 0}]]},
        "Verify Stripe Signature": {"main": [[{"node": "Route by Event Type", "type": "main", "index": 0}]]},
        "Route by Event Type": {"main": [
            [{"node": "Fetch Checkout Session", "type": "main", "index": 0}],
            [{"node": "Extract Subscription Data", "type": "main", "index": 0}],
            [{"node": "Extract Cancellation Reason", "type": "main", "index": 0}],
            [{"node": "Extract Invoice Data", "type": "main", "index": 0}],
            [{"node": "Extract Invoice Data", "type": "main", "index": 0}],
            [{"node": "Webhook Response OK", "type": "main", "index": 0}]
        ]},
        "Fetch Checkout Session": {"main": [[{"node": "Extract Checkout Data", "type": "main", "index": 0}]]},
        "Extract Checkout Data": {"main": [[{"node": "Trigger Backend Checkout Webhook", "type": "main", "index": 0}]]},
        "Trigger Backend Checkout Webhook": {"main": [[{"node": "Insert Checkout Billing Event", "type": "main", "index": 0}]]},
        "Extract Subscription Data": {"main": [[{"node": "Forward to Billing Webhook", "type": "main", "index": 0}]]},
        "Forward to Billing Webhook": {"main": [[{"node": "Route by Subscription Status", "type": "main", "index": 0}]]},
        "Route by Subscription Status": {"main": [
            [{"node": "Update User Tier - Active", "type": "main", "index": 0}],
            [{"node": "Create Dunning Case", "type": "main", "index": 0}],
            [{"node": "Handle Subscription Cancellation", "type": "main", "index": 0}],
            [{"node": "Handle Subscription Trialing", "type": "main", "index": 0}],
            [{"node": "Handle Other Subscription Status", "type": "main", "index": 0}],
            [{"node": "Handle Other Subscription Status", "type": "main", "index": 0}]
        ]},
        "Extract Invoice Data": {"main": [[
            {"node": "Log Payment Success", "type": "main", "index": 0},
            {"node": "Generate Failed Payment Email", "type": "main", "index": 0},
            {"node": "Format Slack Payment Alert", "type": "main", "index": 0},
            {"node": "Create Dunning Case from Payment Failure", "type": "main", "index": 0},
            {"node": "Notify Backend Payment Failure", "type": "main", "index": 0}
        ]]},
        "Generate Failed Payment Email": {"main": [[{"node": "Send Failed Payment Email", "type": "main", "index": 0}]]},
        "Format Slack Payment Alert": {"main": [[{"node": "Send Slack Payment Alert", "type": "main", "index": 0}]]},
        "Dunning Schedule - Every 6 Hours": {"main": [[{"node": "Fetch Open Dunning Cases", "type": "main", "index": 0}]]},
        "Fetch Open Dunning Cases": {"main": [[{"node": "Process Dunning Cases", "type": "main", "index": 0}]]},
        "Process Dunning Cases": {"main": [[{"node": "Is Attempt Below Max?", "type": "main", "index": 0}]]},
        "Is Attempt Below Max?": {"main": [
            [{"node": "Generate Dunning Email", "type": "main", "index": 0}],
            [{"node": "Cancel Subscription - Max Attempts", "type": "main", "index": 0}]
        ]},
        "Generate Dunning Email": {"main": [[{"node": "Send Dunning Email", "type": "main", "index": 0}]]},
        "Send Dunning Email": {"main": [[{"node": "Update Dunning Attempt", "type": "main", "index": 0}]]},
        "Cancel Subscription - Max Attempts": {"main": [[{"node": "Close Dunning & Update Subscription", "type": "main", "index": 0}]]},
        "Extract Cancellation Reason": {"main": [[
            {"node": "Notify Backend Cancellation", "type": "main", "index": 0},
            {"node": "Generate Cancellation Confirmation Email", "type": "main", "index": 0},
            {"node": "Update Subscription Status - Canceled", "type": "main", "index": 0},
            {"node": "Format Churn Alert", "type": "main", "index": 0}
        ]]},
        "Generate Cancellation Confirmation Email": {"main": [[{"node": "Send Cancellation Confirmation", "type": "main", "index": 0}]]},
        "Format Churn Alert": {"main": [[{"node": "Send Churn Alert to Slack", "type": "main", "index": 0}]]},
        "Compare Old vs New Plan": {"main": [[{"node": "Is Upgrade?", "type": "main", "index": 0}]]},
        "Is Upgrade?": {"main": [
            [{"node": "Handle Upgrade", "type": "main", "index": 0}],
            [{"node": "Handle Downgrade", "type": "main", "index": 0}]
        ]},
        "Handle Upgrade": {"main": [[{"node": "Generate Plan Change Email", "type": "main", "index": 0}]]},
        "Handle Downgrade": {"main": [[{"node": "Generate Plan Change Email", "type": "main", "index": 0}]]},
        "Generate Plan Change Email": {"main": [
            [{"node": "Send Plan Change Confirmation", "type": "main", "index": 0}],
            [{"node": "Notify Backend Plan Change", "type": "main", "index": 0}]
        ]},
        "Customer Portal Webhook": {"main": [[{"node": "Extract Portal Request", "type": "main", "index": 0}]]},
        "Extract Portal Request": {"main": [[{"node": "Lookup Stripe Customer", "type": "main", "index": 0}]]},
        "Lookup Stripe Customer": {"main": [[{"node": "Create Stripe Portal Session", "type": "main", "index": 0}]]},
        "Create Stripe Portal Session": {"main": [[{"node": "Return Portal URL", "type": "main", "index": 0}]]},
        "Status Check Schedule - Hourly": {"main": [[{"node": "Fetch Active Subscriptions", "type": "main", "index": 0}]]},
        "Fetch Active Subscriptions": {"main": [[{"node": "Prepare Subscription Checks", "type": "main", "index": 0}]]},
        "Prepare Subscription Checks": {"main": [[{"node": "Check Subscription Status via Stripe", "type": "main", "index": 0}]]},
        "Check Subscription Status via Stripe": {"main": [[{"node": "Compare Status", "type": "main", "index": 0}]]},
        "Compare Status": {"main": [[{"node": "Status Changed?", "type": "main", "index": 0}]]},
        "Status Changed?": {"main": [
            [{"node": "Update Local Status", "type": "main", "index": 0}, {"node": "Format Status Degradation Alert", "type": "main", "index": 0}],
            [{"node": "Update Last Checked", "type": "main", "index": 0}]
        ]},
        "Format Status Degradation Alert": {"main": [[{"node": "Send Status Degradation Alert", "type": "main", "index": 0}]]},
        "MRR Schedule - Daily Midnight": {"main": [[{"node": "Calculate MRR Metrics", "type": "main", "index": 0}]]},
        "Calculate MRR Metrics": {"main": [[{"node": "Compute Revenue Metrics", "type": "main", "index": 0}]]},
        "Compute Revenue Metrics": {"main": [
            [{"node": "Insert Revenue Snapshot", "type": "main", "index": 0}],
            [{"node": "Format MRR Slack Report", "type": "main", "index": 0}]
        ]},
        "Insert Revenue Snapshot": {"main": [[{"node": "Notify Backend Revenue Snapshot", "type": "main", "index": 0}]]},
        "Format MRR Slack Report": {"main": [[{"node": "Send Daily MRR to Slack", "type": "main", "index": 0}]]},
        "Churn Analysis Schedule - Weekly": {"main": [[{"node": "Analyze Churned Subscriptions", "type": "main", "index": 0}]]},
        "Analyze Churned Subscriptions": {"main": [[{"node": "Compute Churn Analysis", "type": "main", "index": 0}]]},
        "Compute Churn Analysis": {"main": [
            [{"node": "Send Churn Report Email", "type": "main", "index": 0}],
            [{"node": "Insert Churn Analysis Record", "type": "main", "index": 0}]
        ]},
        "Catch & Classify API Errors": {"main": [[{"node": "Route by Error Type", "type": "main", "index": 0}]]},
        "Route by Error Type": {"main": [
            [{"node": "Calculate Retry Backoff", "type": "main", "index": 0}],
            [{"node": "Format Backend Error Alert", "type": "main", "index": 0}],
            [{"node": "Format Critical Error Page", "type": "main", "index": 0}],
            [{"node": "Log Non-Critical Errors", "type": "main", "index": 0}]
        ]},
        "Format Backend Error Alert": {"main": [[{"node": "Send Backend Error Slack", "type": "main", "index": 0}]]},
        "Format Critical Error Page": {"main": [[{"node": "Page On-Call via Slack", "type": "main", "index": 0}]]},
        "Log Non-Critical Errors": {"main": [[{"node": "Log Error to Database", "type": "main", "index": 0}]]}
    }

    return workflow


if __name__ == "__main__":
    workflow = build_workflow()
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "workflows", "01-stripe-billing.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)
    node_count = len(workflow["nodes"])
    connection_count = sum(len(c.get("main", [])) for c in workflow["connections"].values())
    print(f"Generated: {output_path}")
    print(f"Nodes: {node_count}")
    print(f"Connection groups: {connection_count}")
    file_size = os.path.getsize(output_path)
    print(f"File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
