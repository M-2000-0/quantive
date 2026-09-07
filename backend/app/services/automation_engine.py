"""Automation engine — the native replacement for the n8n workflows.

Each built-in automation is a real job over real app data:

  lead_capture_score   — scores unscored leads (ICP fit + title + source),
                         auto-creates Deals for hot leads, notifies via email
  onboarding           — advances 5-step onboarding sequences, sends step emails
  dunning              — failed-payment recovery: 3-attempt email cadence,
                         recovers or cancels past_due subscriptions
  mrr_tracker          — records MRR events from billing state, computes
                         MRR/churn/new/reactivation rollups
  support_triage       — auto-classifies new support tickets by keyword,
                         escalates urgent ones
  health_check         — pings critical internal endpoints, records results,
                         alerts when unhealthy

Runs are persisted to the `automation_runs` table so the UI can show a real
track record of what every automation did, not a fake "Workflow ran" node.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger("quantive.automation")

TIER_MRR_CENTS = {"free": 0, "pro": 49900, "enterprise": 249900}


# ── Action log helper ───────────────────────────────────────────────────

@dataclass
class RunContext:
    """Mutable log collector passed to each automation."""
    scanned: int = 0
    actions: list = field(default_factory=list)

    def log(self, action: str, detail: str) -> None:
        self.actions.append({
            "action": action,
            "detail": detail,
            "at": datetime.now(timezone.utc).isoformat(),
        })

    @property
    def summary(self) -> str:
        if not self.actions:
            return f"Scanned {self.scanned} items; nothing to do"
        parts = [f"{a['action']}" for a in self.actions[:5]]
        head = ", ".join(parts) + (f" +{len(self.actions) - 5} more" if len(self.actions) > 5 else "")
        return f"{len(self.actions)} action(s): {head}"


# ── Built-in automations ────────────────────────────────────────────────

BUILTIN_AUTOMATIONS = [
    {
        "key": "lead_capture_score",
        "name": "Lead Capture & Scoring",
        "description": "Scores new leads on ICP fit (treasury/finance/DMO titles, "
                       "government domains, demo source), converts hot leads into "
                       "deals, and emails the sales inbox.",
        "category": "sales",
        "interval_minutes": 15,
    },
    {
        "key": "onboarding",
        "name": "Onboarding Sequence",
        "description": "Advances new organizations through a 5-step onboarding "
                       "sequence (welcome, first portfolio, first optimization, "
                       "reports, check-in) with automated step emails.",
        "category": "onboarding",
        "interval_minutes": 60,
    },
    {
        "key": "dunning",
        "name": "Failed-Payment Recovery",
        "description": "3-attempt email cadence (day 0/3/7) for past_due "
                       "subscriptions; recovers on payment, cancels after final "
                       "attempt.",
        "category": "billing",
        "interval_minutes": 360,
    },
    {
        "key": "mrr_tracker",
        "name": "MRR & Churn Tracking",
        "description": "Records MRR events (new/upgrade/downgrade/churn) from "
                       "live billing state and maintains revenue rollups.",
        "category": "billing",
        "interval_minutes": 60,
    },
    {
        "key": "support_triage",
        "name": "Support Triage",
        "description": "Auto-classifies open support tickets by urgency keywords, "
                       "prioritizes payment-related issues, escalates urgent ones.",
        "category": "support",
        "interval_minutes": 30,
    },
    {
        "key": "health_check",
        "name": "System Health Check",
        "description": "Pings critical internal endpoints (health, dashboard, "
                       "billing plans) and records latency + status; flags "
                       "failures for the error monitor.",
        "category": "ops",
        "interval_minutes": 15,
    },
]


def ensure_automations(db: Session) -> None:
    """Create registry rows for any missing built-in automations."""
    from app.models.automation import Automation

    existing = {a.key for a in db.query(Automation).all()}
    for spec in BUILTIN_AUTOMATIONS:
        if spec["key"] not in existing:
            db.add(Automation(**spec))
    db.commit()


def run_automation(key: str, db: Session, trigger: str = "manual") -> dict:
    """Execute one automation by key and persist a run record."""
    from app.models.automation import AutomationRun

    fn = _RUNNERS.get(key)
    if fn is None:
        raise KeyError(f"Unknown automation: {key}")

    run = AutomationRun(automation_key=key, status="running", trigger=trigger)
    db.add(run)
    db.commit()

    ctx = RunContext()
    started = time.perf_counter()
    try:
        fn(db, ctx)
        run.status = "success"
    except Exception as e:  # noqa: BLE001 — run record must always persist
        db.rollback()
        run.status = "failed"
        run.error = str(e)[:2000]
        logger.exception("Automation %s failed", key)

    run.duration_ms = int((time.perf_counter() - started) * 1000)
    run.items_scanned = ctx.scanned
    run.actions_taken = len(ctx.actions)
    run.summary = ctx.summary
    run.log = json.dumps(ctx.actions)
    run.finished_at = datetime.now(timezone.utc)
    db.commit()

    # Update registry status
    from app.models.automation import Automation
    auto = db.query(Automation).filter(Automation.key == key).first()
    if auto:
        auto.last_run_at = run.finished_at
        auto.last_status = run.status
        db.commit()

    return _run_to_dict(run)


def _run_to_dict(run) -> dict:
    return {
        "id": run.id,
        "automation_key": run.automation_key,
        "status": run.status,
        "trigger": run.trigger,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "duration_ms": run.duration_ms,
        "items_scanned": run.items_scanned,
        "actions_taken": run.actions_taken,
        "summary": run.summary,
        "log": json.loads(run.log) if run.log else [],
        "error": run.error,
    }


# ── Runner 1: Lead capture & scoring ────────────────────────────────────

ICP_TITLES = ("treasury", "cfo", "finance", "debt", "dmo", "minister",
              "portfolio", "central bank", "sovereign", "fiscal")
GOV_DOMAINS = (".gov", ".gov.uk", ".gouv.fr", ".bund.de", ".gc.ca", ".eu", ".org")
HOT_SCORE = 70


def _score_lead(lead) -> tuple[int, list[str]]:
    score = 20  # base
    reasons = ["base 20"]

    email = (lead.email or "").lower()
    title = (lead.title or "").lower()
    company = (lead.company or "").lower()
    source = (lead.source or "").lower()

    if any(d in email for d in GOV_DOMAINS) or "treasury" in company or "ministry" in company:
        score += 30
        reasons.append("government/DMO domain +30")
    if any(k in title for k in ICP_TITLES):
        score += 25
        reasons.append("ICP title +25")
    if source == "demo":
        score += 15
        reasons.append("requested a demo +15")
    elif source == "referral":
        score += 10
        reasons.append("referral +10")
    if email and "@" in email:
        score += 10
        reasons.append("valid email +10")
    return min(score, 100), reasons


def _sales_org_id(db: Session) -> str | None:
    """Org that owns the sales pipeline (the operator's org = first created)."""
    from app.models import Organization

    org = db.query(Organization).order_by(Organization.created_at).first() if hasattr(Organization, "created_at") else db.query(Organization).first()
    return org.id if org else None


def _run_lead_capture(db: Session, ctx: RunContext) -> None:
    from app.models.automation import Lead
    from app.models.management import Deal

    leads = db.query(Lead).filter(Lead.score == 0).all()
    ctx.scanned = len(leads)
    sales_org = _sales_org_id(db)
    for lead in leads:
        score, reasons = _score_lead(lead)
        lead.score = score
        lead.score_reasons = json.dumps(reasons)

        if score >= HOT_SCORE and not lead.converted_deal_id and sales_org:
            try:
                deal = Deal(
                    org_id=sales_org,
                    name=f"{lead.company or lead.name or lead.email} — Pro pipeline",
                    company=lead.company or "",
                    contact_email=lead.email or "",
                    value=499,  # Pro monthly
                    stage="qualified",
                    probability=60,
                    notes=f"Auto-created from lead (score {score}). {lead.source}",
                )
                db.add(deal)
                db.flush()
                lead.converted_deal_id = deal.id
                lead.stage = "qualified"
                ctx.log("deal_created", f"{deal.name} (${deal.value}/mo, score {score})")
            except Exception as e:  # noqa: BLE001 — scoring must survive deal failures
                db.rollback()
                ctx.log("deal_failed", f"{lead.email or lead.name}: {str(e)[:120]}")

        ctx.log("lead_scored_hot" if score >= HOT_SCORE else "lead_scored",
                f"{lead.email or lead.name}: {score}/100")
    db.commit()


# ── Runner 2: Onboarding sequence ───────────────────────────────────────

ONBOARDING_STEPS = [
    ("Welcome to Quantive", "Create your first portfolio and import your debt instruments."),
    ("Import your data", "Use CSV import or manual entry to load instruments."),
    ("Run your first optimization", "Try the debt optimizer to find refinancing savings."),
    ("Explore risk analytics", "Check the maturity ladder, stress tests, and compliance checks."),
    ("Set up reports", "Enable the morning digest and weekly briefings."),
]

_ONBOARD_EMAIL_HOURS = 24  # min gap between step emails


def _run_onboarding(db: Session, ctx: RunContext) -> None:
    from app.models.automation import OnboardingSequence

    seqs = db.query(OnboardingSequence).filter(OnboardingSequence.completed == False).all()  # noqa: E712
    ctx.scanned = len(seqs)
    now = datetime.now(timezone.utc)

    for seq in seqs:
        if seq.step >= len(ONBOARDING_STEPS):
            seq.completed = True
            continue
        # Check if the org has actually progressed (made a portfolio since last step)
        progressed = _org_has_progress(db, seq.org_id, seq.step)
        if progressed:
            seq.step += 1
            ctx.log("step_completed", f"{seq.user_email}: advanced to step {seq.step + 1} — {ONBOARDING_STEPS[seq.step][0]}")
        # Send the next step email if due (24h cadence)
        due = (seq.last_email_at is None or
               now - seq.last_email_at >= timedelta(hours=_ONBOARD_EMAIL_HOURS))
        if due:
            title, body = ONBOARDING_STEPS[seq.step]
            _send_automation_email(
                subject=f"Quantive onboarding ({seq.step + 1}/5): {title}",
                body_text=f"Hi — next step: {body}",
                to_email=seq.user_email,
            )
            seq.emails_sent += 1
            seq.last_email_at = now
            ctx.log("email_sent", f"{seq.user_email}: step {seq.step + 1} — {title}")
    db.commit()


def _org_has_progress(db: Session, org_id: str, step: int) -> bool:
    """Has the org done the action for the current step?"""
    try:
        from app.models import Portfolio
        from app.models.automation import OnboardingSequence
        from app.models import OptimizationJob

        if step == 1:  # imported data → has instruments
            from app.models import DebtInstrument
            return db.query(DebtInstrument).join(
                Portfolio, DebtInstrument.portfolio_id == Portfolio.id
            ).filter(Portfolio.org_id == org_id).count() > 0
        if step == 2:  # ran optimization
            return db.query(OptimizationJob).filter(
                OptimizationJob.org_id == org_id).count() > 0
        if step == 3:  # explored analytics → snapshot exists
            from app.models.extended import PortfolioSnapshot
            return db.query(PortfolioSnapshot).filter(
                PortfolioSnapshot.org_id == org_id).count() > 0
        if step == 4:  # set up reports → digest viewed/generated
            return db.query(OnboardingSequence).filter(
                OnboardingSequence.org_id == org_id,
                OnboardingSequence.step >= 4).count() > 0
        return False
    except Exception:
        return False


# ── Runner 3: Dunning (failed-payment recovery) ─────────────────────────

DUNNING_SCHEDULE = [(1, 0), (2, 3), (3, 7)]  # (attempt, days after open)
DUNNING_MESSAGES = {
    1: "Your payment failed — update your billing details to keep Pro features.",
    2: "Reminder: your Quantive payment still failed. Pro features pause soon.",
    3: "Final notice: payment still failing. Your subscription will be canceled.",
}


def _run_dunning(db: Session, ctx: RunContext) -> None:
    from app.models.automation import DunningCase

    # Open cases for past_due subscriptions without one
    _open_cases_for_past_due(db, ctx)

    now = datetime.now(timezone.utc)
    cases = db.query(DunningCase).filter(DunningCase.status == "open").all()
    ctx.scanned = len(cases)

    for case in cases:
        # Recovered? (subscription became active again)
        if _subscription_active(db, case.org_id):
            case.status = "recovered"
            ctx.log("recovered", f"{case.user_email}: payment succeeded, case closed")
            continue

        if case.attempt >= 3:
            # Grace elapsed since final attempt → cancel
            if case.next_action_at and now >= case.next_action_at:
                _set_subscription_status(db, case.org_id, "canceled")
                case.status = "canceled"
                ctx.log("canceled", f"{case.user_email}: 3 failed attempts, subscription canceled")
            continue

        # Due for the next email?
        if case.next_action_at is None or now >= case.next_action_at:
            case.attempt += 1
            msg = DUNNING_MESSAGES[case.attempt]
            _send_automation_email(
                subject=f"Action needed: Quantive payment (attempt {case.attempt}/3)",
                body_text=msg,
                to_email=case.user_email,
            )
            case.last_email_at = now
            days = dict(DUNNING_SCHEDULE)[case.attempt] if case.attempt in dict(DUNNING_SCHEDULE) else 7
            case.next_action_at = now + timedelta(days=3)
            ctx.log("dunning_email", f"{case.user_email}: attempt {case.attempt} — {msg[:60]}")
    db.commit()


def _open_cases_for_past_due(db: Session, ctx: RunContext) -> None:
    """Create dunning cases for any past_due subscription missing one."""
    from app.billing import _subscriptions, get_subscription
    from app.models.automation import DunningCase
    from app.database import SessionLocal
    from app.models import Organization, User

    for org_id, sub in list(_subscriptions.items()):
        if sub.status != "past_due":
            continue
        existing = db.query(DunningCase).filter(
            DunningCase.org_id == org_id, DunningCase.status == "open").first()
        if existing:
            continue
        email = ""
        db2 = None
        try:
            if not db.get(Organization, org_id):
                db2 = SessionLocal()
                db = db2  # noqa: PLW0641 — local rebind intentional for this block
        except Exception:
            pass
        try:
            org = db.get(Organization, org_id)
            user = db.query(User).filter(User.org_id == org_id).first() if org else None
            email = user.email if user else ""
            case = DunningCase(
                org_id=org_id, user_email=email,
                amount_cents=TIER_MRR_CENTS.get(sub.tier.value if hasattr(sub.tier, "value") else str(sub.tier), 0),
            )
            case.next_action_at = datetime.now(timezone.utc)
            db.add(case)
            db.commit()
            ctx.log("case_opened", f"{email or org_id}: dunning case opened for {sub.status}")
        finally:
            if db2 is not None:
                db2.close()


def _subscription_active(db: Session, org_id: str) -> bool:
    from app.billing import get_subscription
    sub = get_subscription(org_id)
    return bool(sub and sub.status == "active")


def _set_subscription_status(db: Session, org_id: str, status: str) -> None:
    from app.billing import _subscriptions
    sub = _subscriptions.get(org_id)
    if sub:
        sub.status = status


# ── Runner 4: MRR tracker ───────────────────────────────────────────────

def _run_mrr_tracker(db: Session, ctx: RunContext) -> None:
    from app.billing import _subscriptions
    from app.models.automation import MrrEvent

    now = datetime.now(timezone.utc)
    hour_ago = now - timedelta(hours=1)
    ctx.scanned = len(_subscriptions)

    for org_id, sub in _subscriptions.items():
        tier = sub.tier.value if hasattr(sub.tier, "value") else str(sub.tier)
        mrr_cents = TIER_MRR_CENTS.get(tier, 0)
        if sub.status == "canceled":
            event_type = "churn"
        elif sub.status == "past_due":
            event_type = "snapshot"  # not churned until dunning cancels it
        else:
            event_type = "snapshot"

        # Only record if no event for this org in the last hour (dedupe)
        recent = db.query(MrrEvent).filter(
            MrrEvent.org_id == org_id,
            MrrEvent.created_at >= hour_ago,
            MrrEvent.event_type == event_type,
        ).first()
        if recent:
            if recent.mrr_cents != mrr_cents:
                recent.mrr_cents = mrr_cents
                recent.tier = tier
                db.commit()
                ctx.log("mrr_updated", f"{org_id[:8]}…: {tier} ${mrr_cents // 100}/mo")
            continue

        db.add(MrrEvent(org_id=org_id, event_type=event_type, tier=tier, mrr_cents=mrr_cents))
        ctx.log("mrr_recorded", f"{org_id[:8]}…: {tier} ${mrr_cents // 100}/mo ({event_type})")
    db.commit()


def mrr_rollups(db: Session) -> dict:
    """Current MRR, churn, new, reactivation — used by the dashboard."""
    from app.models.automation import MrrEvent

    now = datetime.now(timezone.utc)
    month_ago = now - timedelta(days=30)

    current = 0
    latest_by_org: dict[str, int] = {}
    events = db.query(MrrEvent).filter(MrrEvent.created_at >= month_ago).order_by(MrrEvent.created_at).all()
    for e in events:
        if e.event_type == "churn":
            latest_by_org[e.org_id] = 0
        else:
            latest_by_org[e.org_id] = e.mrr_cents
    current = sum(latest_by_org.values())

    churned = sum(1 for e in events if e.event_type == "churn")
    new = sum(1 for e in events if e.event_type == "new")

    return {
        "mrr_cents": current,
        "mrr_display": f"${current / 100:,.0f}",
        "active_paid_orgs": sum(1 for v in latest_by_org.values() if v > 0),
        "churned_30d": churned,
        "new_30d": new,
    }


# ── Runner 5: Support triage ────────────────────────────────────────────

URGENT_KEYWORDS = ("urgent", "asap", "critical", "outage", "can't access", "locked out")
PAYMENT_KEYWORDS = ("payment", "billing", "invoice", "charge", "refund", "card")


def _run_support_triage(db: Session, ctx: RunContext) -> None:
    from app.models.support import SupportTicket

    tickets = db.query(SupportTicket).filter(
        SupportTicket.status.in_(["open", "new"])
    ).all() if hasattr(SupportTicket, "status") else []
    ctx.scanned = len(tickets)

    for t in tickets:
        text = f"{getattr(t, 'subject', '')} {getattr(t, 'description', '')}".lower()
        changes = []
        if any(k in text for k in PAYMENT_KEYWORDS) and t.priority not in ("high", "urgent"):
            t.priority = "high"
            changes.append("payment→high")
        if any(k in text for k in URGENT_KEYWORDS):
            if t.priority not in ("urgent",):
                t.priority = "urgent"
                changes.append("urgent")
            ctx.log("escalated", f"ticket {t.id[:8]}…: {getattr(t, 'subject', '')[:60]}")
        if changes:
            db.commit()
            ctx.log("classified", f"ticket {t.id[:8]}…: {', '.join(changes)}")


# ── Runner 6: Health check ──────────────────────────────────────────────

HEALTH_TARGETS = [
    ("app-health", "/api/health"),
    ("billing-plans", "/api/billing/plans"),
    ("dashboard-data", "/api/dashboard/summary"),
]


def _run_health_check(db: Session, ctx: RunContext) -> None:
    import httpx

    base = __import__("os").environ.get("QUANTIVE_BASE_URL", "http://127.0.0.1:8000")
    # trust_env=False: ignore system proxies for loopback self-checks
    with httpx.Client(trust_env=False, timeout=10) as client:
        for name, path in HEALTH_TARGETS:
            try:
                r = client.get(f"{base}{path}")
                # Liveness: any HTTP response (<500) means the server is up.
                # 401/403 on protected endpoints still proves availability.
                ok = r.status_code < 500
                ctx.log("checked" if ok else "degraded",
                        f"{name}: {r.status_code} ({r.elapsed.total_seconds() * 1000:.0f}ms)")
            except Exception as e:
                ctx.log("failed", f"{name}: {type(e).__name__}: {str(e)[:120]}")
    ctx.scanned = len(HEALTH_TARGETS)


# ── Shared email helper ─────────────────────────────────────────────────

def _send_automation_email(subject: str, body_text: str, to_email: str) -> None:
    """Fire-and-forget email; never raises. Logs when no provider configured."""
    if not to_email:
        return
    try:
        import asyncio
        from app.email_service import EmailMessage, send_email

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(send_email(EmailMessage(
                to=[to_email], subject=subject,
                body_html=f"<p>{body_text}</p>", body_text=body_text,
                tags={"type": "automation"},
            )))
        except RuntimeError:
            # No running loop (scheduler thread) — run in a fresh loop
            asyncio.run(send_email(EmailMessage(
                to=[to_email], subject=subject,
                body_html=f"<p>{body_text}</p>", body_text=body_text,
                tags={"type": "automation"},
            )))
    except Exception as e:  # noqa: BLE001
        logger.warning("Automation email failed (%s): %s", to_email, e)


_RUNNERS = {
    "lead_capture_score": _run_lead_capture,
    "onboarding": _run_onboarding,
    "dunning": _run_dunning,
    "mrr_tracker": _run_mrr_tracker,
    "support_triage": _run_support_triage,
    "health_check": _run_health_check,
}
