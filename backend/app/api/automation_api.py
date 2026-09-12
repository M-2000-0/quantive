"""Automation API — registry, run history, CRM leads, and manual triggers.

These endpoints power the /automation page: everything the n8n JSON
workflows pretended to do, visible and runnable in the app.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.automation import (
    Automation,
    AutomationRun,
    DunningCase,
    Lead,
    MrrEvent,
    OnboardingSequence,
)
from app.security import get_current_user, require_role, UserRole
from app.services import automation_engine

router = APIRouter(prefix="/api/automation", tags=["automation-engine"])


# ── Registry ────────────────────────────────────────────────────────────

def _auto_dict(a: Automation) -> dict:
    return {
        "key": a.key,
        "name": a.name,
        "description": a.description,
        "category": a.category,
        "interval_minutes": a.interval_minutes,
        "enabled": a.enabled,
        "last_run_at": a.last_run_at.isoformat() if a.last_run_at else None,
        "last_status": a.last_status,
    }


@router.get("")
def list_automations(user=Depends(get_current_user), db: Session = Depends(get_db)):
    automation_engine.ensure_automations(db)
    autos = db.query(Automation).order_by(Automation.category, Automation.key).all()
    return {"automations": [_auto_dict(a) for a in autos],
            "categories": sorted({a.category for a in autos})}


@router.post("/{key}/run")
def run_now(key: str, user=Depends(require_role(UserRole.ADMIN)), db: Session = Depends(get_db)):
    """Manually trigger an automation (admin only)."""
    try:
        result = automation_engine.run_automation(key, db, trigger="manual")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown automation: {key}")
    return result


@router.post("/{key}/toggle")
def toggle_automation(key: str, user=Depends(require_role(UserRole.ADMIN)),
                      db: Session = Depends(get_db)):
    a = db.query(Automation).filter(Automation.key == key).first()
    if not a:
        raise HTTPException(status_code=404, detail=f"Unknown automation: {key}")
    a.enabled = not a.enabled
    db.commit()
    return {"key": key, "enabled": a.enabled}


# ── Run history ─────────────────────────────────────────────────────────

@router.get("/{key}/runs")
def run_history(key: str, limit: int = 20,
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    runs = (db.query(AutomationRun)
            .filter(AutomationRun.automation_key == key)
            .order_by(AutomationRun.started_at.desc())
            .limit(min(limit, 100)).all())
    return {"runs": [automation_engine._run_to_dict(r) for r in runs]}


@router.get("/runs/recent")
def recent_runs(limit: int = 50, user=Depends(get_current_user), db: Session = Depends(get_db)):
    runs = (db.query(AutomationRun)
            .order_by(AutomationRun.started_at.desc())
            .limit(min(limit, 200)).all())
    return {"runs": [automation_engine._run_to_dict(r) for r in runs]}


# ── CRM leads ───────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    name: str = ""
    email: EmailStr | None = None
    company: str = ""
    title: str = ""
    source: str = Field(default="website", pattern="^(website|demo|webhook|referral)$")
    notes: str = ""


@router.get("/leads")
def list_leads(stage: str | None = None, user=Depends(get_current_user),
               db: Session = Depends(get_db)):
    q = db.query(Lead)
    if stage:
        q = q.filter(Lead.stage == stage)
    leads = q.order_by(Lead.score.desc(), Lead.created_at.desc()).limit(200).all()
    return {"leads": [{
        "id": l.id, "name": l.name, "email": l.email, "company": l.company,
        "title": l.title, "source": l.source, "stage": l.stage, "score": l.score,
        "score_reasons": l.score_reasons, "converted_deal_id": l.converted_deal_id,
        "created_at": l.created_at.isoformat() if l.created_at else None,
    } for l in leads]}


@router.post("/leads", status_code=201)
def create_lead(data: LeadCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a lead; it will be scored by the next lead_capture_score run."""
    lead = Lead(name=data.name, email=data.email or "", company=data.company,
                title=data.title, source=data.source, notes=data.notes)
    db.add(lead)
    db.commit()
    # Score immediately so the UI reflects it
    result = automation_engine.run_automation("lead_capture_score", db, trigger="manual")
    return {"id": lead.id, "score": lead.score,
            "score_reasons": lead.score_reasons, "run": result}


# ── Onboarding / dunning / MRR views ────────────────────────────────────

@router.get("/onboarding")
def onboarding_status(user=Depends(get_current_user), db: Session = Depends(get_db)):
    seqs = db.query(OnboardingSequence).order_by(OnboardingSequence.started_at.desc()).limit(100).all()
    return {"sequences": [{
        "org_id": s.org_id, "user_email": s.user_email, "step": s.step,
        "emails_sent": s.emails_sent, "completed": s.completed,
        "started_at": s.started_at.isoformat() if s.started_at else None,
    } for s in seqs]}


@router.get("/dunning")
def dunning_status(user=Depends(get_current_user), db: Session = Depends(get_db)):
    cases = db.query(DunningCase).order_by(DunningCase.created_at.desc()).limit(100).all()
    open_count = sum(1 for c in cases if c.status == "open")
    recovered = sum(1 for c in cases if c.status == "recovered")
    return {"cases": [{
        "org_id": c.org_id, "user_email": c.user_email,
        "amount_display": f"${c.amount_cents / 100:,.0f}",
        "attempt": c.attempt, "status": c.status,
        "next_action_at": c.next_action_at.isoformat() if c.next_action_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    } for c in cases],
        "open": open_count, "recovered": recovered}


@router.get("/mrr")
def mrr_summary(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return automation_engine.mrr_rollups(db)


# ── Webhook: capture a lead from external systems ────────────────────────

@router.post("/webhooks/lead", status_code=201)
def lead_webhook(data: LeadCreate, db: Session = Depends(get_db)):
    """Public lead-capture endpoint (e.g., website form, n8n, partner site).

    Scored automatically by the lead_capture_score automation.
    """
    lead = Lead(name=data.name, email=data.email or "", company=data.company,
                title=data.title, source=data.source or "webhook", notes=data.notes)
    db.add(lead)
    db.commit()
    automation_engine.run_automation("lead_capture_score", db, trigger="manual")
    return {"id": lead.id, "score": lead.score, "stage": lead.stage}


# ── Webhook: n8n → automation run bridge ──────────────────────────────────

class ExternalRunIn(BaseModel):
    """One completed execution of an external (n8n) workflow."""
    workflow: str = Field(..., min_length=1, max_length=58)
    status: str = Field("success", pattern="^(success|failed)$")
    duration_ms: int = Field(0, ge=0, le=86_400_000)
    summary: str = Field("", max_length=500)
    actions: list[dict] = Field(default_factory=list, max_length=200)


def _verify_bridge_signature(raw: bytes, header_sig: str) -> None:
    """HMAC-SHA256 over the raw body, matching the n8n HMAC Code node.

    Enforced only when QUANTIVE_WEBHOOK_SECRET is set; unset means local
    dev, where we accept and log (mirrors the Stripe webhook policy).
    """
    secret = os.environ.get("QUANTIVE_WEBHOOK_SECRET", "")
    if not secret:
        return
    expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, (header_sig or "").strip().lower()):
        raise HTTPException(status_code=401, detail="Invalid bridge signature")


@router.post("/webhooks/external-run", status_code=201)
async def external_run_webhook(request: Request, db: Session = Depends(get_db)):
    """Record an n8n workflow execution as a real AutomationRun.

    The n8n workflows call this after every scheduled cycle, so n8n runs
    appear in the /automation dashboard run history alongside native runs.
    HMAC-verified via x-quantive-signature when a secret is configured.
    """
    raw = await request.body()
    _verify_bridge_signature(raw, request.headers.get("x-quantive-signature", ""))
    try:
        data = ExternalRunIn.model_validate_json(raw)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid payload: {e}")

    now = datetime.now(timezone.utc)
    run = AutomationRun(
        automation_key=f"n8n:{data.workflow}",
        status=data.status,
        trigger="external",
        started_at=now - timedelta(milliseconds=data.duration_ms),
        finished_at=now,
        duration_ms=data.duration_ms,
        items_scanned=len(data.actions),
        actions_taken=len(data.actions),
        summary=data.summary or f"n8n workflow {data.workflow} {data.status}",
        log=json.dumps(data.actions)[:10000],
        error="" if data.status == "success" else (data.summary or "n8n reported failure"),
    )
    db.add(run)
    db.commit()
    return {"id": run.id, "recorded": True}
