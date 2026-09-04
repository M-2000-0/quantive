# Quantive — Full Feature Implementation Plan

> 41 features mapped. 14 exist, 14 partial, 13 missing.
> This plan covers building all 13 missing features and completing all 14 partial features.

---

## Phase 1: Foundation (Weeks 1-2)
**Priority: Critical infrastructure that other features depend on**

### 1.1 News Ingestion Pipeline [MISSING → FULL BUILD]
**Domain:** Platform
**Files to create:**
- `backend/app/models/news.py` — `NewsArticle`, `NewsFeed`, `NewsSource` SQLAlchemy models
- `backend/app/market_data/news_providers.py` — NewsAPI, GDELT, RSS feed connectors
- `backend/app/services/news_ingestion.py` — Ingestion scheduler, deduplication, storage
- `backend/app/api/news.py` — CRUD + search + feed endpoints
- `frontend/src/components/NewsFeed.tsx` — News feed UI component

**Schema:**
```sql
news_sources (id, name, type, url, config_json, is_active, last_fetched_at)
news_articles (id, source_id, title, summary, content, url, published_at, 
               tickers_json, sentiment_score, category, tags_json, 
               ingestion_hash, created_at)
```

**Key decisions:**
- Free sources: NewsAPI (100 req/day free), GDELT (unlimited), Yahoo Finance RSS
- Background ingestion via APScheduler (30-min intervals)
- Content hash deduplication
- SQLite full-text search via FTS5

### 1.2 Task Management System [MISSING → FULL BUILD]
**Domain:** Internal
**Files to create:**
- `backend/app/models/tasks.py` — `Task`, `TaskComment`, `TaskAssignment` models
- `backend/app/api/tasks.py` — CRUD + assign + status + filter endpoints
- `frontend/src/components/TaskManager.tsx` — Kanban board / list view
- `frontend/src/components/TaskCard.tsx` — Individual task card

**Schema:**
```sql
tasks (id, title, description, status, priority, org_id, 
       created_by, assigned_to, due_date, created_at, updated_at)
task_comments (id, task_id, user_id, content, created_at)
```

### 1.3 Meeting Scheduling [MISSING → FULL BUILD]
**Domain:** Internal
**Files to create:**
- `backend/app/models/meetings.py` — `Meeting`, `MeetingAttendee` models
- `backend/app/api/meetings.py` — CRUD + availability check + RSVP endpoints
- `frontend/src/components/MeetingScheduler.tsx` — Calendar view with booking

**Schema:**
```sql
meetings (id, title, description, org_id, created_by, 
          start_time, end_time, location, recurrence_json, created_at)
meeting_attendees (id, meeting_id, user_id, status, created_at)
```

---

## Phase 2: AI & Intelligence (Weeks 2-3)
**Priority: High — core differentiators**

### 2.1 AI Market Summaries [PARTIAL → COMPLETE]
**Domain:** AI
**What exists:** Data aggregation endpoints, LLM policy engine (different scope)
**Files to modify/create:**
- `backend/app/services/market_summary.py` — LLM-powered market summary generator
- `backend/app/api/market_summary.py` — `GET /api/market/summary` endpoint
- `frontend/src/components/MarketSummaryCard.tsx` — AI summary display

**Approach:** Combine yield curve + FX + rates + news data → structured prompt → LLM → natural language summary. Fallback to template-based summary.

### 2.2 AI News Summaries [MISSING → FULL BUILD]
**Domain:** AI
**Dependencies:** News Ingestion (1.1)
**Files to create:**
- `backend/app/services/news_summarizer.py` — Article summarization + digest generation
- `backend/app/api/news.py` — Add `GET /api/news/digest` endpoint
- `frontend/src/components/NewsDigest.tsx` — Daily/weekly digest UI

**Approach:** Batch recent articles → LLM summarization → categorize by impact → generate digest.

### 2.3 Stock Explanations [PARTIAL → COMPLETE]
**Domain:** AI
**What exists:** Technical signal factors, strategy-level explainability
**Files to modify/create:**
- `backend/app/services/stock_explainer.py` — "Why this stock" narrative generator
- Extend `backend/app/api/trading_intelligence.py` — Add explanation endpoint
- `frontend/src/components/StockExplanation.tsx` — Narrative explanation UI

**Approach:** Combine technical signals + price data + sector context → LLM → "Based on RSI oversold at 28, MACD crossover, and sector rotation into tech, this stock shows..." narrative.

### 2.4 Conflicting-Signal Detection [PARTIAL → COMPLETE]
**Domain:** AI
**What exists:** Composite scoring that averages out disagreements
**Files to modify/create:**
- `backend/app/services/signal_conflict.py` — Conflict detection engine
- Extend `backend/app/api/trading_intelligence.py` — Add conflict analysis endpoint
- `frontend/src/components/SignalConflictAlert.tsx` — Conflict visualization

**Approach:** Compare individual indicator signals (RSI, MACD, MA, BB). If disagreement > threshold → flag as conflicting. Calculate agreement score. Cross-timeframe analysis.

### 2.5 Prediction Refreshes [PARTIAL → COMPLETE]
**Domain:** Platform
**What exists:** ML models, ModelVersion table
**Files to modify/create:**
- `backend/app/services/model_retraining.py` — Scheduled retraining pipeline
- `backend/app/jobs/retraining_job.py` — Background retraining task
- Extend `backend/app/api/optimizations.py` — Add model lifecycle endpoints

**Approach:** APScheduler triggers nightly retraining. ModelVersion populated automatically. Drift detection triggers early retraining. A/B testing via ModelExperiment table.

### 2.6 Model-Error Tracking [PARTIAL → COMPLETE]
**Domain:** Platform
**What exists:** prediction_drift table (unused), ModelVersion table
**Files to modify/create:**
- `backend/app/services/model_monitor.py` — Prediction-vs-actual comparison, drift recording
- `backend/app/api/model_monitor.py` — Monitoring dashboard endpoints
- `frontend/src/components/ModelPerformanceDashboard.tsx` — Accuracy/drift visualization

**Approach:** After each prediction batch, compare predicted vs actual values. Record drift_score in prediction_drift table. Alert when drift exceeds threshold.

---

## Phase 3: Customer Support (Weeks 3-4)
**Priority: High — customer-facing**

### 3.1 AI Support Chatbot [PARTIAL → COMPLETE]
**Domain:** Support
**What exists:** Sovereign debt AI advisor (different scope)
**Files to create:**
- `backend/app/models/support.py` — `SupportTicket`, `SupportMessage`, `FAQItem` models
- `backend/app/services/support_chatbot.py` — AI-powered support chatbot
- `backend/app/api/support.py` — Chat + ticket + FAQ endpoints
- `frontend/src/components/SupportChat.tsx` — Live chat widget
- `frontend/src/components/HelpCenter.tsx` — Help center page

**Approach:** RAG-based chatbot using existing Ollama infrastructure. Knowledge base of product FAQs. Escalation to human agent when confidence < threshold.

### 3.2 FAQ Automation [MISSING → FULL BUILD]
**Domain:** Support
**Files to create:**
- `backend/app/models/support.py` — `FAQItem`, `FAQCategory` models (same file as 3.1)
- `backend/app/api/support.py` — FAQ CRUD + search + suggest endpoints
- `frontend/src/components/FAQCenter.tsx` — Searchable FAQ with categories

**Schema:**
```sql
faq_categories (id, name, description, sort_order, created_at)
faq_items (id, category_id, question, answer, helpful_count, 
           created_by, is_published, created_at, updated_at)
```

### 3.3 Ticket Classification [MISSING → FULL BUILD]
**Domain:** Support
**Files to create:**
- Extend `backend/app/models/support.py` — Add ticket fields
- `backend/app/services/ticket_classifier.py` — Rule-based + LLM ticket categorization
- Extend `backend/app/api/support.py` — Ticket CRUD + classification + routing

**Approach:** Keyword-based initial classification → LLM refinement → auto-assign based on category. Priority scoring based on sentiment + keywords + customer tier.

### 3.4 Bug Tracking [MISSING → FULL BUILD]
**Domain:** Support
**Files to create:**
- Extend `backend/app/models/support.py` — `BugReport` model
- Extend `backend/app/api/support.py` — Bug CRUD + status lifecycle
- `frontend/src/components/BugTracker.tsx` — Bug list + detail view

**Schema:**
```sql
bug_reports (id, title, description, severity, status, 
             reported_by, assigned_to, org_id, steps_to_reproduce,
             expected_behavior, actual_behavior, created_at, updated_at)
```

### 3.5 Payment-Support Workflows [PARTIAL → COMPLETE]
**Domain:** Support
**What exists:** Stripe billing, subscription management
**Files to modify/create:**
- `backend/app/services/payment_support.py` — Refund processing, billing dispute handling
- Extend `backend/app/api/billing_routes.py` — Add support endpoints
- `frontend/src/components/PaymentSupport.tsx` — Payment issue form + status

### 3.6 Escalation Alerts [PARTIAL → COMPLETE]
**Domain:** Support
**What exists:** Approval/security escalation (different context)
**Files to modify/create:**
- Extend `backend/app/services/support_chatbot.py` — SLA tracking + escalation
- Extend `backend/app/models/support.py` — Add escalation fields to tickets
- `frontend/src/components/EscalationDashboard.tsx` — SLA breach monitoring

---

## Phase 4: Management Dashboards (Weeks 4-5)
**Priority: Medium — business intelligence**

### 4.1 Revenue Dashboard [MISSING → FULL BUILD]
**Domain:** Management
**Files to create:**
- `backend/app/services/revenue_analytics.py` — Revenue aggregation, ARR calculation
- `backend/app/api/revenue.py` — Revenue metrics endpoints
- `frontend/src/components/RevenueDashboard.tsx` — Revenue charts + metrics

**Approach:** Query billing/subscription data → aggregate revenue by period → calculate ARR, growth rate, expansion revenue, contraction. Charts: revenue over time, by tier, by region.

### 4.2 MRR Dashboard [MISSING → FULL BUILD]
**Domain:** Management
**Files to create:**
- Extend `backend/app/services/revenue_analytics.py` — MRR calculation
- Extend `backend/app/api/revenue.py` — MRR endpoints
- `frontend/src/components/MRRDashboard.tsx` — MRR trends + breakdown

**MRR components:** New MRR, Expansion MRR, Churned MRR, Contraction MRR, Net MRR. Churn rate, expansion rate, quick ratio.

### 4.3 Customer Dashboard [MISSING → FULL BUILD]
**Domain:** Management
**Files to create:**
- `backend/app/services/customer_analytics.py` — Customer metrics aggregation
- `backend/app/api/customers.py` — Customer list + metrics endpoints
- `frontend/src/components/CustomerDashboard.tsx` — Customer analytics

**Metrics:** Total customers, active/inactive, by plan tier, signup trends, usage patterns, health scores.

### 4.4 Churn Dashboard [MISSING → FULL BUILD]
**Domain:** Management
**Files to create:**
- Extend `backend/app/services/customer_analytics.py` — Churn prediction + metrics
- Extend `backend/app/api/customers.py` — Churn endpoints
- `frontend/src/components/ChurnDashboard.tsx` — Churn metrics + at-risk list

**Metrics:** Monthly churn rate, churn reasons, at-risk customers (usage decline), retention rate, lifetime value.

### 4.5 Sales Pipeline [MISSING → FULL BUILD]
**Domain:** Management
**Files to create:**
- `backend/app/models/pipeline.py` — `Deal`, `PipelineStage` models
- `backend/app/api/pipeline.py` — Deal CRUD + pipeline aggregation
- `frontend/src/components/SalesPipeline.tsx` — Kanban pipeline view

**Schema:**
```sql
pipeline_stages (id, name, sort_order, org_id, created_at)
deals (id, name, company, value, currency, stage_id, 
       owner_id, org_id, expected_close_date, probability,
       created_at, updated_at)
```

### 4.6 Demo Tracking [PARTIAL → COMPLETE]
**Domain:** Management
**What exists:** DemoModeBanner (UI only)
**Files to modify/create:**
- `backend/app/models/demo.py` — `DemoRequest`, `DemoOutcome` models
- `backend/app/api/demo.py` — Request + scheduling + outcome endpoints
- `frontend/src/components/DemoTracker.tsx` — Demo pipeline view

### 4.7 Prediction Performance [PARTIAL → COMPLETE]
**Domain:** Management
**What exists:** Backtesting for trading strategies
**Files to modify/create:**
- Extend `backend/app/services/model_monitor.py` — Model performance aggregation
- Extend `backend/app/api/model_monitor.py` — Performance comparison endpoints
- Extend `frontend/src/components/ModelPerformanceDashboard.tsx` — Model comparison view

### 4.8 Email Automation [PARTIAL → COMPLETE]
**Domain:** Management
**What exists:** Transactional email service (SendGrid/Resend)
**Files to modify/create:**
- `backend/app/services/email_campaigns.py` — Campaign + sequence + drip logic
- `backend/app/models/email.py` — `EmailCampaign`, `EmailSequence`, `EmailEvent` models
- `backend/app/api/email_campaigns.py` — Campaign CRUD + analytics
- `frontend/src/components/EmailCampaignManager.tsx` — Campaign builder + analytics

### 4.9 Error Alerts [PARTIAL → COMPLETE]
**Domain:** Management
**What exists:** Sentry, ErrorBoundary, SOC2 alerting
**Files to modify/create:**
- `backend/app/services/error_monitor.py` — Error rate tracking, threshold alerts
- `backend/app/api/error_monitor.py` — Error metrics + alert endpoints
- `frontend/src/components/ErrorMonitorDashboard.tsx` — Error rate visualization

---

## Phase 5: Internal Operations (Week 5)
**Priority: Low — internal tooling**

### 5.1 Backup Monitoring [PARTIAL → COMPLETE]
**Domain:** Internal
**What exists:** Backup system, DR dashboard (mock data)
**Files to modify/create:**
- Extend `backend/app/backup.py` — Add verification + status tracking
- `backend/app/api/backup.py` — Backup status + verify endpoints
- Wire `frontend/src/components/DisasterRecovery.tsx` to real backup data

### 5.2 Wire Existing Components
Several existing components use mock data and need wiring to real backend endpoints:
- `PerformanceMonitor.tsx` → wire to `/api/health/status`
- `SystemAvailabilityDashboard.tsx` → wire to health endpoints
- `EngagementAnalytics.tsx` → wire to activity log API
- `AlertPreferences.tsx` → wire to notification rules API

---

## Implementation Order (Dependency Graph)

```
Week 1-2: Foundation
├── News Ingestion (1.1) ─────────────┐
├── Task Management (1.2)              │
├── Meeting Scheduling (1.3)           │
└── Prediction Refreshes (2.5) ────────┘

Week 2-3: AI & Intelligence
├── AI Market Summaries (2.1) ─────────┐
├── AI News Summaries (2.2) ← depends on 1.1
├── Stock Explanations (2.3)            │
├── Conflicting-Signal Detection (2.4)  │
└── Model-Error Tracking (2.6) ← depends on 2.5

Week 3-4: Customer Support
├── AI Support Chatbot (3.1) ← depends on 2.1
├── FAQ Automation (3.2) ← same models as 3.1
├── Ticket Classification (3.3) ← same models as 3.1
├── Bug Tracking (3.4) ← same models as 3.1
├── Payment Support (3.5)
└── Escalation Alerts (3.6) ← depends on 3.3

Week 4-5: Management Dashboards
├── Revenue Dashboard (4.1)
├── MRR Dashboard (4.2) ← depends on 4.1
├── Customer Dashboard (4.3)
├── Churn Dashboard (4.4) ← depends on 4.3
├── Sales Pipeline (4.5)
├── Demo Tracking (4.6)
├── Prediction Performance (4.7) ← depends on 2.6
├── Email Automation (4.8)
└── Error Alerts (4.9)

Week 5: Internal Operations
├── Backup Monitoring (5.1)
└── Wire Mock Components (5.2)
```

---

## New Database Tables (14 total)

| Table | Feature | Migration |
|-------|---------|-----------|
| news_sources | News Ingestion | 005_news.py |
| news_articles | News Ingestion | 005_news.py |
| tasks | Task Management | 006_tasks.py |
| task_comments | Task Management | 006_tasks.py |
| meetings | Meeting Scheduling | 007_meetings.py |
| meeting_attendees | Meeting Scheduling | 007_meetings.py |
| support_tickets | Support System | 008_support.py |
| support_messages | Support System | 008_support.py |
| faq_categories | FAQ Automation | 008_support.py |
| faq_items | FAQ Automation | 008_support.py |
| bug_reports | Bug Tracking | 008_support.py |
| email_campaigns | Email Automation | 009_campaigns.py |
| email_events | Email Automation | 009_campaigns.py |
| deals | Sales Pipeline | 010_pipeline.py |

---

## Estimated Effort

| Phase | Features | Effort |
|-------|----------|--------|
| Phase 1: Foundation | 3 new | 3-4 days |
| Phase 2: AI & Intelligence | 4 complete + 2 new | 4-5 days |
| Phase 3: Customer Support | 1 complete + 5 new | 4-5 days |
| Phase 4: Management | 5 complete + 4 new | 5-6 days |
| Phase 5: Internal | 1 complete + wiring | 2-3 days |
| **Total** | **13 new + 14 complete** | **18-23 days** |

---

## Tech Stack for New Features

| Concern | Technology |
|---------|-----------|
| Background jobs | APScheduler (already in requirements) |
| News APIs | NewsAPI, GDELT, RSS (feedparser) |
| AI/LLM | Ollama (existing), OpenAI/Anthropic (existing) |
| Support chat | WebSocket (existing infrastructure) |
| Charts | Recharts (already in frontend) |
| Email campaigns | SendGrid/Resend (existing email_service.py) |
| Migrations | Alembic (existing) |
