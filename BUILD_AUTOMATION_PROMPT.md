# Building Quantive's Automation Layer — Connect to the Existing App

## What this document is
A build brief for an LLM/agent that implements the Quantive automation workflows (the Onboarding, Quantive Platform, AI, Customer Support, Management, and Internal blocks) as real, connected code on top of the existing backend. The goal: each workflow touches real app data and real app endpoints, with only minor integration work needed to wire it up — not a rewrite, not a separate n8n universe.

## What already exists (do not reimplement these)

### App skeleton
- FastAPI backend at `backend/app/main.py`, served by uvicorn on port 8000.
- Auth: `app/api/auth.py` — register/login with JWT access + refresh tokens (httponly cookies, secure-gated via `settings.SECURE_COOKIES`), role-based, org-scoped.
- RBAC: `app/security/rbac_middleware.py` + `app/security/portfolio_rbac.py` — server-side role checks on endpoints.
- Pages: Jinja2 templates in `app/templates/pages/`, sidebar in `app/templates/base.html`. New pages are `@app.get("/some-path", response_class=HTMLResponse)` + a template + a sidebar link.
- Static: `/static/css/quantive.css`, `/static/js/*.js`.

### Automation infrastructure (already built — use it)
- **Automation registry + run history**: `app/api/automation_api.py` — endpoints:
  - `GET /api/automation` — list automations + categories.
  - `POST /api/automation/{key}/run` — manual trigger (admin only).
  - `POST /api/automation/{key}/toggle` — enable/disable (admin only).
  - `GET /api/automation/{key}/runs` — run history for one automation.
  - `GET /api/automation/runs/recent` — recent runs across all.
  - `GET /api/automation/leads` + `POST /api/automation/leads` — CRM leads.
  - `POST /api/automation/webhooks/lead` — public lead-capture webhook.
  - `GET /api/automation/onboarding`, `/api/automation/dunning`, `/api/automation/mrr` — views.
  - `POST /api/automation/webhooks/external-run` — n8n bridge: records an external workflow run as a real `AutomationRun` (HMAC-verified via `x-quantive-signature` when `QUANTIVE_WEBHOOK_SECRET` is set).
- **Automation engine**: `app/services/automation_engine.py` — 6 built-in runners:
  - `lead_capture_score` — scores unscored leads, auto-creates deals for hot leads, emails sales.
  - `onboarding` — 5-step onboarding sequence with step emails (24h cadence).
  - `dunning` — 3-attempt failed-payment recovery cadence.
  - `mrr_tracker` — records MRR events + rollups.
  - `support_triage` — auto-classifies tickets, escalates urgent.
  - `health_check` — pings critical endpoints, records latency/status.
- **Automation scheduler**: `app/services/automation_scheduler.py` — asyncio task started from the lifespan, ticks every 30s, runs each enabled automation on its `interval_minutes`, each run in its own DB session via `asyncio.to_thread` so the event loop stays responsive.
- **Models**: `app/models/automation.py` — `Automation`, `AutomationRun`, `Lead`, `OnboardingSequence`, `DunningCase`, `MrrEvent`.
- **Email**: `app/email_service.py` — async `send_email(EmailMessage)` with SendGrid/Resend/log-only provider detection. Fire-and-forget safe. Used by automations via `app.services.automation_engine._send_automation_email`.
- **Notifications**: `app/services/notification_dispatcher.py` — multi-channel (email via `app.email_service`, SMS via Twilio when configured, WebSocket push). Used by market alerts.

### Supporting data models that automations will read/write
- `app/models/` — Portfolio, DebtInstrument, OptimizationJob, User, Organization, UserRole, SubscriptionRow, UsageRow, Deal, SupportTicket, SupportMessage, Task, Meeting, ActivityLog, UserAlert, AlertHistory, etc.
- `app/billing.py` — subscription tiers (free/pro/enterprise), `check_limit`, `get_subscription`, `PLAN_DETAILS`, Stripe checkout + webhooks.
- `app/services/` — a large set of domain services (market_data_service, news_ingestion, discovery_engine, bubble_detector, compliance_checker, portfolio_optimizer, signal_outcome_tracker, sentiment_analyzer, daily_digest, weekly_digest, pdf_export, etc.). Each is importable and mostly stateless per-call.

### The n8n bridge (already built — use it)
- `POST /api/automation/webhooks/external-run` accepts `workflow`, `status`, `duration_ms`, `summary`, `actions[]` and persists it as `AutomationRun(automation_key=f"n8n:{workflow}", trigger="external")`. This is the reconnect point if you want n8n to drive some workflows while the app records them as first-class runs. HMAC verification is optional (only when `QUANTIVE_WEBHOOK_SECRET` is set).

## What to build

Build the automation workflows as **native app automations** that extend `app/services/automation_engine.py`'s pattern: a `_run_<name>(db, ctx)` function registered in `_RUNNERS`, with a registry entry in `BUILTIN_AUTOMATIONS`, and a scheduler entry via `interval_minutes`. Each workflow must operate on real app data and call real app services. Do NOT build a separate n8n instance or a separate workflow engine — the app already has the scheduler and run-history infrastructure.

### Onboarding (5-step sequence — already partially built, expand it)

The `onboarding` runner already exists: it advances `OnboardingSequence` records step by step, sends step emails via `_send_automation_email`, and checks org progress via `_org_has_progress`. Expand it to:

- Step 1 "Welcome" — email sent on registration. Trigger the sequence creation from `app/api/auth.py` register path (or from a new `POST /api/auth/onboarding-start` that the welcome page calls). Store `OnboardingSequence(org_id, user_email, step=0, started_at=now)`.
- Step 2 "Import your data" — detect progress by checking `DebtInstrument` count for the org > 0. If no instruments after N days, re-email or surface an in-app reminder via `ActivityLog` + a notification.
- Step 3 "Run your first optimization" — detect by `OptimizationJob` count > 0 for the org.
- Step 4 "Explore risk analytics" — detect by presence of a portfolio with a risk scan / maturity ladder run.
- Step 5 "Set up reports" — detect by a `scheduled_reports` entry or a morning-digest opt-in flag on the user/profile.
- Add an in-app onboarding widget on the dashboard: read `OnboardingSequence` for the current user's org, show current step + "Mark step complete" buttons that call a new `POST /api/automation/onboarding/advance` endpoint (admin or self, scoped to own org). This is the minor integration touch: one new endpoint + one sidebar/dashboard widget + the existing email flow.

### Quantive Platform (market data, predictions, watchlists, news, alerts)

These are mostly already running as background services. The automation angle is to make them visible and controllable as automations in the `/automation` dashboard, and to wire their health into `health_check`. Specifically:

- **Market-data ingestion**: `app/services/market_data_service.py` + `app/api/market_monitor_api.py` already exist. Add an `automation` row `market_data_ingest` (or fold into `health_check`) that records the last successful ingest timestamp from the market-monitor tables and flags if it's stale beyond the expected interval. This is the "data freshness" signal.
- **Prediction refreshes**: if there's a prediction/model refresh path (look at `app/services/model_monitor.py`, `app/services/model_retraining.py`, `app/api/model_validation_api.py`), add an automation `prediction_refresh` that records last refresh + model version + validation score, and surfaces stale models.
- **Watchlist updates**: `app/api/market_monitor_api.py` watchlist endpoints already exist. Add a light automation `watchlist_sync` that records last watchlist update + count, for the Management "watchlist updates" visibility.
- **News ingestion**: `app/services/news_ingestion.py` + `app/services/news_scheduler.py` already run hourly. Add an automation `news_ingestion` that records articles ingested in the last cycle (pull from whatever store news lands in) and surfaces volume + any ingestion failures.
- **Stock/news matching**: if present (look at `app/services/discovery_engine.py`, `app/services/pattern_detector.py`, `app/api/discovery_api.py`), add an automation `signal_generation` that records signals generated in the last cycle.
- **Prediction explanations**: if present (look at `app/api/ai_advisor.py`, `app/services/stock_explainer.py`), add an automation `explanation_generation` that records explanations generated.
- **Model-error tracking + data-quality monitoring + API-error alerts**: `app/services/error_monitor.py`, `app/api/error_monitor.py`, `app/api/data_quality.py`, `app/api/model_validation_api.py` already exist. Add an automation `error_monitoring` that reads the error store and surfaces open errors + error rate, and feeds into the `health_check` status.

The point: these become visible, toggleable rows in `/automation` with real run history, not separate dashboards. The data flows already exist; the automation wrapper is the thin layer that records run metadata + exposes on/off toggles + health.

### AI (market summaries, news summaries, stock explanations, signal analysis, conflicting-signal detection, daily reports, market alerts)

These map to existing services. Build automations that run them on a schedule and record the outputs:

- **Market summaries**: `app/services/market_summary.py` — add an automation `market_summary` that runs on a schedule (e.g., every 6h), calls the summary service, and stores the generated summary (or its ID/hash) in an `AutomationRun` summary + a summary store table if one doesn't exist. If there's no summary store, add a small `MarketSummary` model.
- **News summaries**: `app/services/news_summarizer.py` — automation `news_summary` that summarizes the latest ingested news batch.
- **Stock explanations**: `app/services/stock_explainer.py` — automation `stock_explanation` that generates/re-generates explanations for tracked stocks.
- **Signal analysis + conflicting-signal detection**: `app/services/signal_conflict.py`, `app/services/signal_outcome_tracker.py` — automation `signal_analysis` that runs signal scoring + conflict detection and records results.
- **Daily reports**: `app/services/daily_digest.py` + `app/api/daily_digest_api.py` — already exists. Add an automation `daily_digest` that triggers the digest generation and records it. If the digest sends email, that's via `app.email_service` (already wired).
- **Market alerts**: `app/services/market_monitor_alerts.py` + `app/services/notification_dispatcher.py` — already exists. Add an automation `alert_evaluation` that runs the alert checker and records alerts fired.

The integration touch here is small: each is "call the existing service, persist a run record + a lightweight output record, send any notifications via the dispatcher." Don't rebuild the summarization/analysis — call what's there.

### Customer Support (AI support, FAQ automation, ticket classification, bug tracking, payment-support workflows, escalation alerts)

- **AI support + FAQ automation**: if there's an AI support endpoint (look at `app/api/support.py`, `app/services/` for support), build an automation `support_triage` (already exists — expand it) that classifies open `SupportTicket`s by urgency keywords, auto-answers FAQ-type tickets via the AI support endpoint if available, and escalates urgent ones. Store classification + auto-reply on the ticket.
- **Ticket classification**: expand `_run_support_triage` to write classification + priority to the `SupportTicket` record (look at `app/models/support.py`).
- **Bug tracking**: if a bug-tracking model/endpoint exists, add an automation `bug_triage` that scans new tickets tagged as bugs, creates a tracked bug record, and routes to the right owner. If no bug tracker exists, add a minimal `Bug` model + a few endpoints.
- **Payment-support workflows**: automation `payment_support` that detects failed-payment / past_due orgs (from `DunningCase` or billing state), creates a support ticket tagged `payment`, and triggers the dunning flow if not already running. This connects support ↔ billing.
- **Escalation alerts**: the notification dispatcher already does multi-channel alerts. Add an automation `escalation` that, when a high-priority ticket or a payment failure is unresolved past a threshold, sends an escalation via email + (if Twilio configured) SMS to the on-call/support team. Use the dispatcher's `_send_email` / `_send_sms` pattern.

The integration touch: support automations read/write `SupportTicket` + `SupportMessage`, use the notification dispatcher for escalation, and use the billing models for payment detection.

### Management (revenue dashboard, MRR dashboard, customer dashboard, churn dashboard, sales pipeline, demo tracking, user activity, prediction performance, system monitoring)

These become views + a couple of automations that feed them:

- **MRR dashboard**: `app/services/automation_engine.py:mrr_rollups(db)` already returns MRR rollups. Add an automation `mrr_tracker` (already exists) + management endpoints `GET /api/management/mrr`, `GET /api/management/churn`, `GET /api/management/revenue` that call `mrr_rollups` + billing queries. If a `Deal`/`SubscriptionRow` store is present, compute new/upgrade/downgrade/churn from MRR events.
- **Customer dashboard**: `GET /api/management/customers` — list orgs with subscription tier, active user count, last activity, onboarding step, open support tickets. Pull from `Organization`, `User`, `OnboardingSequence`, `SupportTicket`, `SubscriptionRow`.
- **Churn dashboard**: derive from MRR events (churn = MRR lost) + inactive orgs (no login/activity in N days).
- **Sales pipeline**: `app/models/management.py:Deal` already exists. Add `GET /api/management/pipeline` — list deals by stage, value, source, lead origin. The `lead_capture_score` automation already auto-creates deals.
- **Demo tracking**: if a `Demo`/demo-booking model exists (look at `app/models/management.py`, `app/api/demo.py`), add endpoints to list/update demos. If not, add a minimal `Demo` model + lead-booking endpoint.
- **User activity**: `app/models/social.py:ActivityLog` already exists. Add `GET /api/management/user-activity` — recent activity across the org.
- **Prediction performance**: if model validation/monitoring exists, add `GET /api/management/prediction-performance` — last validation scores, drift, error rate.
- **System monitoring**: fold into `health_check` automation + `GET /api/management/system` — component health (market data freshness, news ingestion, prediction freshness, error count, DB health).

The integration touch: these are read-only aggregate endpoints + 1-2 feeders. The data is already in the models; the work is surfacing it.

### Internal (team notifications, task creation, meeting scheduling, document generation, contract workflows, email automation, daily/weekly reports, error alerts, backup monitoring, security monitoring)

- **Team notifications**: use the notification dispatcher. Add an automation `team_notifications` that, on notable events (new lead scored hot, big optimization savings, payment failure, system alarm), sends a team notification to a configured channel/email list.
- **Task creation**: `app/models/tasks.py:Task` already exists. Add an automation `task_creation` that, on certain triggers (e.g., a high-risk signal, a compliance violation, a payment failure), creates a `Task` assigned to the right owner with a due date. Add `POST /api/tasks` endpoints if not present.
- **Meeting scheduling**: `app/models/tasks.py:Meeting` already exists. Add light endpoints to create/list meetings. Automations can create follow-up meetings (e.g., "onboarding check-in" after step 3).
- **Document generation**: if a doc-generation service exists (look at `app/services/pdf_export.py`, `app/api/pdf_export_api.py`, `app/api/pdf_reports.py`), add an automation `document_generation` that produces periodic reports (daily/weekly) and emails them. If no template engine for docx/markdown, use the existing PDF export path.
- **Contract workflows**: if a contract model exists (`app/models/contract_manager.py`? check `app/services/contract_manager.py`), add an automation `contract_workflows` that tracks contract stages + sends reminders. If not, add a minimal `Contract` model.
- **Email automation**: this is the `onboarding` + `dunning` + `daily_digest` + `team_notifications` automations — all already use `app.email_service`. No new email infrastructure needed.
- **Daily/weekly reports**: `app/services/daily_digest.py` + `app/services/weekly_digest_email.py` + `app/api/daily_digest_api.py` + `app/api/weekly_digest_api.py` — already exist. Add automations `daily_report` + `weekly_report` that trigger generation + distribution, with run records.
- **Error alerts**: `app/services/error_monitor.py` — add an automation `error_alerts` that scans open errors and escalates via the dispatcher.
- **Backup monitoring**: if a backup model/endpoint exists (`app/api/backup_monitor.py`), add an automation `backup_monitoring` that checks last backup age + success and alerts if stale. If not, add a minimal backup-status endpoint + automation.
- **Security monitoring**: fold into `health_check` + an automation `security_monitoring` that checks auth failure spikes (from the threat-tracking path), RBAC denials, and rate-limit hits, and escalates if thresholds are breached.

The integration touch: most of this is "read existing models/services, write a task/ticket/contract if one doesn't exist yet, send notifications via the dispatcher, record a run." A few new minimal models/endpoints are expected (Task assignment, Contract, Demo, Bug) — keep each minimal.

## How to wire each workflow (the repeatable pattern)

For each automation, do this:

1. Add a registry entry to `BUILTIN_AUTOMATIONS` in `app/services/automation_engine.py`: `{key, name, description, category, interval_minutes}`.
2. Add a runner function `_run_<key>(db: Session, ctx: RunContext) -> None` in the same file (or import it from a new module if it's large).
3. Register it in `_RUNNERS`.
4. If the automation needs its own persisted state (like `OnboardingSequence` or `DunningCase`), add a minimal model in `app/models/automation.py` (or the appropriate models file) and create it via `ensure_automations` or a dedicated ensure function.
5. If the automation produces a meaningful output that should be queryable later (a summary, a report, a classification), add a lightweight model + an endpoint to read it. Don't over-model — store the key output fields, not the full blobs, unless the blob is small.
6. If the automation sends notifications, use the existing `app.email_service.send_email` (async) or the notification dispatcher (`_send_email`/`_send_sms`), in fire-and-forget style (the automation engine's `_send_automation_email` shows the pattern for sending from a non-async context).
7. If the automation needs to call an external system (n8n, a data provider, an AI API), use the app's existing HTTP patterns and record the external call as part of the run's `actions[]` log. If n8n should drive it, have n8n call `POST /api/automation/webhooks/external-run` after each cycle — the app records it as a real run either way.
8. Add any needed UI: a small widget or page section that reads the automation's state/endpoint and shows current status + "run now" + "toggle". The `/automation` page already lists automations + runs; for onboarding, add a widget on the dashboard.

## Connection points to the app (the "minor issues" surface)

These are the places where connecting a workflow will require small, localized changes — list them so the builder knows where the seams are:

- **Auth + org scoping**: every automation that touches user/org data should be scoped to an org. The engine's runners receive `db` and can query `User → org_id`. New endpoints should use `get_current_user` + org scoping. The existing `*_user=Depends(get_current_user)` pattern is the convention.
- **Email**: `app.email_service.send_email` is the single send path. If an automation needs a different email template/identity, extend `EmailMessage` tags or add a template-render helper — don't add a second email sender.
- **Notifications**: `app.services.notification_dispatcher` is the multi-channel path. Use it for alerts/escalations; don't add a second SMS/WS path.
- **Scheduling**: the automation scheduler (`app/services/automation_scheduler.py`) is the scheduler. To add a workflow that runs on a different cadence or needs cron-like scheduling, extend the scheduler or add a second asyncio task in the same style. Don't introduce Celery/APScheduler unless the cron needs genuinely exceed what the current scheduler handles.
- **n8n coexistence**: if n8n is used for some workflows, have it call `POST /api/automation/webhooks/external-run` so its runs appear in the app's run history. Optionally have the app call back to n8n webhooks for triggers — but the app should remain the source of truth for run history + on/off state. Set `QUANTIVE_WEBHOOK_SECRET` in production to enable HMAC verification on the bridge.
- **Billing interaction**: automations that act on subscription state (dunning, payment support, tier-based feature gating) should read from `app.billing.get_subscription` / `SubscriptionRow` and write status via the billing layer, not by mutating Stripe directly. The dunning runner already shows this pattern.
- **Role gates**: admin-only actions (run now, toggle, delete) use `require_role(UserRole.ADMIN)`. Support/team automations may need a new role or a scoping check — add it via the existing RBAC middleware pattern.
- **Pages**: new UI goes in `app/templates/pages/` + a route in `app/main.py` + a sidebar link in `app/templates/base.html`. The `/automation` page already exists — check `app/api/automation_api.py` + the corresponding template for the existing structure before adding a new page.

## Data model gaps to fill (only as needed)

Don't pre-create all of these — add each only when the workflow that needs it is built:

- `MarketSummary` — if no store exists for generated market summaries.
- `Bug` — if no bug-tracking model exists.
- `Contract` — if no contract model exists.
- `Demo` — if no demo-booking model exists (check `app/models/management.py` first).
- `Task` assignment/owner fields — if the existing `Task` model lacks assignment, extend it.
- Onboarding in-app state — `OnboardingSequence` exists; add an in-app widget + advance endpoint.

## Quality bars

- Every automation must record a real `AutomationRun` (success/failed, duration, actions log, summary) — no silent runs.
- Every automation must be toggleable + manually runnable from `/api/automation`.
- Every automation must be org-scoped where it touches user data.
- Every automation that sends email/notifications must go through `app.email_service` or the dispatcher — no side channels.
- Every new model/endpoint should follow the existing conventions (Base model, `get_current_user` auth, Pydantic request schemas in `app/api/` or a schemas file, responses as dicts or response models).
- The builder should run a quick smoke test for each automation: trigger it manually via `POST /api/automation/{key}/run`, then read back the run record + any output it produced.

## Out of scope (skip these to keep integration minor)

- Building a separate n8n instance or visual workflow editor inside the app.
- Rebuilding the market-data ingestion, news ingestion, prediction engine, or AI summarization — call the existing services.
- Replacing the email provider or notification dispatcher.
- Replacing the scheduler.
- Full dashboard redesigns — add small widgets/sections to existing pages.

## Expected deliverable

A set of native automations (registry entries + runners + any needed models/endpoints/UI widgets) covering the Onboarding, Quantive Platform, AI, Customer Support, Management, and Internal blocks, each connected to real app data and real app services, with the only new infrastructure being minimal models/endpoints where the existing ones don't cover a workflow's needs. The n8n bridge (`POST /api/automation/webhooks/external-run`) remains available for any workflow an external n8n instance should drive, with runs recorded in-app.
