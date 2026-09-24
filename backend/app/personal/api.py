"""Quantive Personal API. Prefix: /api/personal. Personal-DB only.

Auth: reuses enterprise JWT (app.security.get_current_user) for identity,
but NEVER touches sovereign tables. Billing: shared app.billing (personal tier).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.personal.database import get_personal_db
from app.personal.models import (
    PersonalAudit, PersonalDocument, PersonalOpportunity, PersonalProfile, PersonalTask, ProfileFact,
)
from app.personal.onboarding_questions import QUESTIONS, visible_questions
from app.personal.opportunity_engine import detect
from app.personal import qubo as qubo_engine
from app.personal.qubo import AGE_BRACKETS
from app.personal.schemas import FactUpsert, OnboardingAnswer
from app.personal.scoring import compute_score
from app.security import get_current_user

router = APIRouter(prefix="/api/personal", tags=["personal"])


def _uid(user) -> str:
    return str(getattr(user, "id", ""))


def _personal_plan(user):
    """Return (tier, limits) for Personal enforcement.

    No subscription -> Starter caps (not unlimited): the product must feel
    limited until the user chooses a plan. Never fail open to unlimited.
    """
    try:
        from app import billing as _billing
        org_id = str(getattr(user, "org_id", "") or _uid(user))
        sub = _billing.get_subscription(org_id)
        if not sub:
            starter = _billing.PLAN_DETAILS.get(_billing.PlanTier.PERSONAL_2K, {})
            return "none", (starter.get("limits", {}) or {})
        details = _billing.PLAN_DETAILS.get(sub.tier, {})
        return sub.tier.value, (details.get("limits", {}) or {})
    except Exception:
        return "none", {"personal_opportunities": 3, "personal_documents": 10,
                        "personal_asks_per_month": 20, "personal_gov_access": 0,
                        "personal_annual_report": 0}


def _limit_allows(limits: dict, key: str, current: int) -> bool:
    lim = limits.get(key, -1)
    if lim in (None, -1):
        return True
    try:
        return current < int(lim)
    except Exception:
        return True


def _audit(db: Session, user_id: str, action: str, entity: str = "", entity_id: str = "", meta: dict | None = None):
    db.add(PersonalAudit(user_id=user_id, action=action, entity=entity, entity_id=entity_id, meta=meta or {}))
    db.commit()


def _profile(db: Session, user_id: str) -> PersonalProfile:
    p = db.query(PersonalProfile).filter(PersonalProfile.user_id == user_id).first()
    if p is None:
        p = PersonalProfile(id=f"pp_{user_id[:24]}", user_id=user_id, display_name="",
                            onboarding_status="not_started", onboarding_current=0)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def _answers(db: Session, user_id: str) -> dict[str, Any]:
    rows = db.query(ProfileFact).filter(ProfileFact.user_id == user_id,
                                        ProfileFact.source == "onboarding").all()
    out: dict[str, Any] = {}
    for r in rows:
        vj = r.value_json or {}
        out[r.key] = vj.get("values", r.value)
    return out


@router.get("/score")
def score(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    user_id = _uid(user)
    tier, limits = _personal_plan(user)
    answers = _answers(db, user_id)
    vis = visible_questions(answers)
    facts_count = len([k for k in answers if answers[k] not in (None, "", [])])
    tasks_open = db.query(PersonalTask).filter(PersonalTask.user_id == user_id,
                                               PersonalTask.status == "open").count()
    docs_pending = db.query(PersonalDocument).filter(PersonalDocument.user_id == user_id,
                                                     PersonalDocument.review_status != "confirmed").count()
    docs_total = db.query(PersonalDocument).filter(PersonalDocument.user_id == user_id).count()
    opps = detect(db, user_id, tier=tier)
    needs_review = sum(1 for o in opps if not o.reviewed and not o.dismissed)
    calc = compute_score(facts_count=facts_count, visible_total=len(vis),
                         open_actions=tasks_open, doc_gaps=docs_pending, needs_review=needs_review)
    p = _profile(db, user_id)
    p.score = calc["score"]
    p.score_detail = calc
    db.commit()
    return {"score": calc["score"], "completeness": calc["completeness"],
            "open_actions": tasks_open, "opportunities": len(opps),
            "doc_gaps": docs_pending, "needs_review": needs_review, "message": calc["message"],
            "tier": tier, "limits": limits, "docs_total": docs_total,
            "gov_access": bool((limits or {}).get("personal_gov_access"))}


@router.get("/onboarding")
def onboarding_get(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    user_id = _uid(user)
    p = _profile(db, user_id)
    answers = _answers(db, user_id)
    vis = visible_questions(answers)
    # current = first unanswered visible question
    current = 0
    for i, q in enumerate(vis):
        if q["id"] not in answers:
            current = i
            break
        current = i + 1
    return {"status": p.onboarding_status, "current": min(current, len(vis)),
            "total": len(vis), "baseline_max": 24,
            "questions": vis, "answers": answers}


@router.post("/onboarding/answer")
def onboarding_answer(payload: OnboardingAnswer, user=Depends(get_current_user),
                      db: Session = Depends(get_personal_db)):
    user_id = _uid(user)
    q = next((x for x in QUESTIONS if x["id"] == payload.question_id), None)
    if not q:
        raise HTTPException(404, "Unknown question")
    vals = payload.answer if isinstance(payload.answer, list) else [payload.answer]
    vals = [str(v) for v in vals]
    row = db.query(ProfileFact).filter(ProfileFact.user_id == user_id,
                                       ProfileFact.key == payload.question_id).first()
    if row is None:
        row = ProfileFact(user_id=user_id, category=q.get("group", "general"),
                          key=payload.question_id, source="onboarding")
        db.add(row)
    row.value = vals[0] if vals else ""
    row.value_json = {"values": vals}
    row.confidence = "user_reported"
    row.status = "confirmed"
    row.fact_date = datetime.now(timezone.utc).date().isoformat()
    p = _profile(db, user_id)
    if p.onboarding_status == "not_started":
        p.onboarding_status = "in_progress"
    db.commit()
    _audit(db, user_id, "onboarding.answer", "question", payload.question_id)
    tier, _ = _personal_plan(user)
    detect(db, user_id, tier=tier)  # refresh opportunities eagerly
    return onboarding_get(user=user, db=db)


@router.post("/onboarding/complete")
def onboarding_complete(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    user_id = _uid(user)
    p = _profile(db, user_id)
    p.onboarding_status = "completed"
    # Ensure completeness task closes, review task opens
    if not db.query(PersonalTask).filter(PersonalTask.user_id == user_id,
                                         PersonalTask.title == "Review your first opportunities").first():
        db.add(PersonalTask(user_id=user_id, title="Review your first opportunities",
                            reason="Onboarding complete — confirm what Quantive inferred.",
                            priority="high", link="/personal/opportunities"))
    db.commit()
    _audit(db, user_id, "onboarding.complete")
    tier, _ = _personal_plan(user)
    detect(db, user_id, tier=tier)
    return {"status": "completed"}


@router.get("/profile")
def profile_get(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    user_id = _uid(user)
    rows = db.query(ProfileFact).filter(ProfileFact.user_id == user_id).order_by(ProfileFact.category).all()
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r.category, []).append({
            "id": r.id, "key": r.key, "value": r.value, "value_json": r.value_json,
            "source": r.source, "confidence": r.confidence, "status": r.status})
    return {"groups": grouped}


@router.put("/profile/facts")
def fact_upsert(payload: FactUpsert, user=Depends(get_current_user),
                db: Session = Depends(get_personal_db)):
    user_id = _uid(user)
    row = db.query(ProfileFact).filter(ProfileFact.user_id == user_id,
                                       ProfileFact.category == payload.category,
                                       ProfileFact.key == payload.key).first()
    if row is None:
        row = ProfileFact(user_id=user_id, category=payload.category, key=payload.key)
        db.add(row)
    row.value = payload.value
    row.value_json = payload.value_json
    row.source = payload.source
    row.confidence = payload.confidence
    row.status = payload.status
    db.commit()
    db.refresh(row)
    _audit(db, user_id, "profile.fact_upsert", payload.key, row.id)
    tier, _ = _personal_plan(user)
    detect(db, user_id, tier=tier)
    return {"id": row.id}


@router.delete("/profile/facts/{fact_id}")
def fact_delete(fact_id: str, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    user_id = _uid(user)
    row = db.query(ProfileFact).filter(ProfileFact.id == fact_id,
                                       ProfileFact.user_id == user_id).first()
    if not row:
        raise HTTPException(404, "Not found")
    db.delete(row)
    db.commit()
    _audit(db, user_id, "profile.fact_delete", row.key, fact_id)
    tier, _ = _personal_plan(user)
    detect(db, user_id, tier=tier)
    return {"deleted": True}


@router.get("/opportunities")
def opps_list(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    tier, limits = _personal_plan(user)
    rows = detect(db, _uid(user), tier=tier)
    cap = (limits or {}).get("personal_opportunities", -1)
    items = [{"id": o.id, "title": o.title, "category": o.category, "relevance": o.relevance,
             "status": o.status, "why": o.why, "needs_info": o.needs_info or [],
             "needs_docs": o.needs_docs or [], "rule_refs": o.rule_refs or [],
             "next_action": o.next_action} for o in rows if not o.dismissed]
    if cap not in (None, -1):
        try:
            return items[:int(cap)]
        except Exception:
            return items
    return items


@router.post("/opportunities/{opp_id}/review")
def opp_review(opp_id: str, payload: dict, user=Depends(get_current_user),
               db: Session = Depends(get_personal_db)):
    user_id = _uid(user)
    row = db.query(PersonalOpportunity).filter(PersonalOpportunity.id == opp_id,
                                               PersonalOpportunity.user_id == user_id).first()
    if not row:
        raise HTTPException(404, "Not found")
    action = (payload or {}).get("action", "reviewed")
    if action == "dismiss":
        row.dismissed = True
    elif action == "not_applicable":
        row.status = "not_applicable"
    else:
        row.status = "reviewed"
        row.reviewed = True
    db.commit()
    _audit(db, user_id, "opportunity.review", row.title, opp_id, {"action": action})
    return {"status": row.status}


@router.get("/tasks")
def tasks_list(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    user_id = _uid(user)
    # Ensure baseline tasks exist
    if not db.query(PersonalTask).filter(PersonalTask.user_id == user_id).first():
        db.add_all([
            PersonalTask(user_id=user_id, title="Complete tax profile",
                         reason="Quantive needs additional information about your situation.",
                         priority="high", link="/personal/onboarding"),
            PersonalTask(user_id=user_id, title="Confirm important profile facts",
                         reason="You own your profile — review what Quantive inferred.",
                         priority="medium", link="/personal/profile"),
        ])
        db.commit()
    rows = db.query(PersonalTask).filter(PersonalTask.user_id == user_id).all()
    return [{"id": t.id, "title": t.title, "reason": t.reason, "priority": t.priority,
             "status": t.status, "due": t.due, "link": t.link} for t in rows]


@router.post("/tasks/{task_id}/close")
def task_close(task_id: str, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    row = db.query(PersonalTask).filter(PersonalTask.id == task_id,
                                        PersonalTask.user_id == _uid(user)).first()
    if not row:
        raise HTTPException(404, "Not found")
    row.status = "done"
    db.commit()
    return {"status": "done"}


@router.get("/documents")
def docs_list(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    rows = db.query(PersonalDocument).filter(PersonalDocument.user_id == _uid(user)).all()
    _, limits = _personal_plan(user)
    cats: dict[str, int] = {}
    for r in rows:
        cats[r.category] = cats.get(r.category, 0) + 1
    doc_cap = (limits or {}).get("personal_documents", -1)
    return {"categories": cats, "total": len(rows), "cap": doc_cap,
            "documents": [
        {"id": r.id, "filename": r.filename, "category": r.category,
         "status": r.status, "review_status": r.review_status} for r in rows]}


@router.post("/documents")
def doc_register(payload: dict, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    user_id = _uid(user)
    _, limits = _personal_plan(user)
    current = db.query(PersonalDocument).filter(PersonalDocument.user_id == user_id).count()
    if not _limit_allows(limits, "personal_documents", current):
        raise HTTPException(403, "Starter plan limit reached (10 documents). Upgrade to Personal or Sovereign for unlimited documents.")
    # Metadata only — never invent extracted content.
    row = PersonalDocument(user_id=user_id, filename=str(payload.get("filename", "unnamed")),
                           category=str(payload.get("category", "other")),
                           storage_path=str(payload.get("storage_path", "")),
                           status="uploaded", extracted={}, related_opps=[])
    db.add(row)
    db.commit()
    db.refresh(row)
    _audit(db, user_id, "document.register", row.category, row.id)
    return {"id": row.id, "status": "uploaded"}


@router.post("/intelligence/ask")
def intelligence_ask(payload: dict, user=Depends(get_current_user),
                     db: Session = Depends(get_personal_db)):
    """Structured (non-LLM) answer: cites profile facts + rule refs, flags uncertainty.

    Full LLM orchestration can plug in later behind this contract.
    Starter (2k) is capped at 20 asks/month — counted via PersonalAudit.
    """
    user_id = _uid(user)
    q = str(payload.get("question", "")).strip()
    if not q:
        raise HTTPException(400, "question required")
    _, limits = _personal_plan(user)
    ask_cap = (limits or {}).get("personal_asks_per_month", -1)
    if ask_cap not in (None, -1):
        try:
            from datetime import timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            used = db.query(PersonalAudit).filter(
                PersonalAudit.user_id == user_id,
                PersonalAudit.action == "intelligence.ask",
                PersonalAudit.created_at >= cutoff).count()
            if used >= int(ask_cap):
                raise HTTPException(403, "Starter plan limit reached (20 questions/month). Upgrade for unlimited intelligence.")
        except HTTPException:
            raise
        except Exception:
            pass
    rows = db.query(ProfileFact).filter(ProfileFact.user_id == user_id).all()
    known = [f"{r.category}.{r.key}={r.value}" for r in rows[:12]]
    tier, _ = _personal_plan(user)
    opps = detect(db, user_id, tier=tier)
    _audit(db, user_id, "intelligence.ask", "question", "", {"q": q[:140]})
    used = 0
    try:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        used = db.query(PersonalAudit).filter(
            PersonalAudit.user_id == user_id,
            PersonalAudit.action == "intelligence.ask",
            PersonalAudit.created_at >= cutoff).count()
    except Exception:
        used = 0
    gov_note = ("Sovereign context: your bracket's aggregated investing vs spending trend is available in Gov insights."
                if tier == "personal_10k" else
                "Sovereign Gov-grade trends are not included in your plan.")
    seen_refs: list[str] = []
    for o in opps[:5]:
        for r in (o.rule_refs or []):
            if r not in seen_refs:
                seen_refs.append(r)
    return {
        "answer_kind": "structured_preview",
        "confidence": "potential",
        "tier": tier,
        "what_i_know": known,
        "what_i_need": ["applicable tax regime", "whether the expense is attributable to qualifying activity"],
        "related_opportunities": [o.title for o in opps[:5]],
        "rule_refs": seen_refs[:4] or ["GEN-2026-home-office"],
        "next_step": "Answer 2 questions in onboarding/tax section.",
        "gov_note": gov_note,
        "asks_used_30d": used,
        "asks_cap": ask_cap,
        "cta": "/personal/onboarding",
        "disclaimer": "General information only — not professional tax advice. Verify against current rules or a qualified professional.",
    }


@router.get("/report")
def report(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    user_id = _uid(user)
    tier, limits = _personal_plan(user)
    answers = _answers(db, user_id)
    vis = visible_questions(answers)
    opps = detect(db, user_id, tier=tier)
    tasks = db.query(PersonalTask).filter(PersonalTask.user_id == user_id,
                                          PersonalTask.status == "open").all()
    docs = db.query(PersonalDocument).filter(PersonalDocument.user_id == user_id).all()
    full_report = bool((limits or {}).get("personal_annual_report", 1))
    gov = bool((limits or {}).get("personal_gov_access"))
    from app.personal.tax_packs import normalize_country as _norm
    juris = _norm(str((answers.get("country") or [""])[0] if isinstance(answers.get("country"), list) else (answers.get("country") or "")))
    base = {
        "tax_year": 2026,
        "tier": tier,
        "jurisdiction": juris,
        "jurisdiction_note": ("Country-specific pack" if juris != "GEN"
                              else "Generic rules only — set your country in onboarding for specific guidance."),
        "summary_only": not full_report,
        "gov_access": gov,
        "profile_completeness": round(100 * len(answers) / max(1, len(vis))),
        "potential_opportunities": len(opps),
        "documentation_issues": sum(1 for d in docs if d.review_status != "confirmed"),
        "items_requiring_review": sum(1 for o in opps if not o.reviewed),
        "open_tasks": [{"title": t.title, "reason": t.reason} for t in tasks],
        "opportunities": [o.title for o in opps],
        "cpa_questions": ["Confirm applicable tax regime", "Confirm documentation sufficiency"],
        "note": "Counts and readiness only — no savings claimed without verified rules and data.",
    }
    if not full_report:
        base["upgrade_note"] = ("Starter includes a summary only — full annual intelligence report "
                                "requires Personal ($5k) or Sovereign ($10k).")
    if gov:
        base["gov_brief"] = ("Aggregated Qubo signal: brackets similar to yours are allocating more "
                             "toward investments vs spending this quarter (aggregates only, no individual data).")
    return base


@router.get("/qubo/status")
def qubo_status(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Current user's Qubo consent + bracket (patterns-not-people contract)."""
    user_id = _uid(user)
    return {"opt_in": qubo_engine.is_opted_in(db, user_id),
            "age_bracket": qubo_engine.get_bracket(db, user_id),
            "brackets": AGE_BRACKETS,
            "privacy": qubo_engine.PRIVACY_NOTE}


@router.post("/qubo/consent")
def qubo_consent(payload: dict, user=Depends(get_current_user),
                 db: Session = Depends(get_personal_db)):
    """Explicit opt-in/out (+ optional age bracket). Audited, reversible."""
    user_id = _uid(user)
    opt_in = bool((payload or {}).get("opt_in", False))
    bracket = (payload or {}).get("age_bracket")
    if bracket is not None:
        bracket = str(bracket)
    try:
        out = qubo_engine.set_consent(db, user_id, opt_in, age_bracket=bracket)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _audit(db, user_id, "qubo.consent", "opt_in", "",
           {"opt_in": opt_in, "age_bracket": out.get("age_bracket")})
    return {**out, "brackets": AGE_BRACKETS, "privacy": qubo_engine.PRIVACY_NOTE}


@router.get("/qubo/trends")
def qubo_trends(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Live Qubo aggregates for logged-in users (same engine as public)."""
    data = qubo_engine.public_trends(db)
    data["your_bracket"] = qubo_engine.get_bracket(db, _uid(user))
    data["opt_in"] = qubo_engine.is_opted_in(db, _uid(user))
    return data


@router.get("/gov-insights")
def gov_insights(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Sovereign-tier Gov-grade market view. Aggregates only — same Qubo contract."""
    tier, limits = _personal_plan(user)
    if not (limits or {}).get("personal_gov_access"):
        raise HTTPException(403, "Sovereign plan required ($10k/yr) for Gov-grade market access.")
    user_id = _uid(user)
    live = qubo_engine.public_trends(db)
    bracket = qubo_engine.get_bracket(db, user_id) or "unknown"
    _audit(db, user_id, "gov.view")
    return {
        "tier": tier,
        "bracket": bracket,
        "your_bracket": bracket,
        "is_live": live["is_live"],
        "as_of": live.get("as_of"),
        "contributors_total": live.get("contributors_total", 0),
        "trends": live["trends"],
        "how_to_use": "Compare your allocation against your bracket — informational only, not advice.",
        "privacy": live.get("privacy") or "Aggregates only. No names, conversations, or individual records are ever exposed.",
        "note": live.get("note", ""),
    }


@router.post("/billing/checkout")
async def personal_checkout(payload: dict, request: Request, user=Depends(get_current_user)):
    """Create a checkout session for a Personal tier (2k / 5k / 10k)."""
    from app import billing as _billing
    tier_raw = str((payload or {}).get("tier", "personal"))
    cycle = str((payload or {}).get("billing_cycle", "yearly"))
    try:
        tier = _billing.PlanTier(tier_raw)
    except ValueError:
        raise HTTPException(422, f"Invalid Personal tier: {tier_raw}")
    if tier not in (_billing.PlanTier.PERSONAL_2K, _billing.PlanTier.PERSONAL,
                    _billing.PlanTier.PERSONAL_10K):
        raise HTTPException(422, "Tier is not a Personal plan")
    if cycle not in ("monthly", "yearly"):
        cycle = "yearly"
    org_id = str(getattr(user, "org_id", "") or _uid(user))
    import os as _os
    base_url = _os.environ.get("STRIPE_SUCCESS_BASE_URL", "").rstrip("/") or str(request.base_url).rstrip("/")
    session = await _billing.create_checkout_session(
        org_id=org_id, user_id=_uid(user), tier=tier, billing_cycle=cycle,
        success_url=f"{base_url}/personal/pricing?checkout=success",
        cancel_url=f"{base_url}/personal/pricing?checkout=cancelled",
    )
    return {"tier": tier.value, **session}


@router.get("/billing")
def personal_billing(user=Depends(get_current_user)):
    """Shared billing engine, Personal-tier presentation (2k / 5k / 10k)."""
    from app import billing as _billing
    org_id = str(getattr(user, "org_id", "") or _uid(user))
    sub = _billing.get_subscription(org_id)
    tier = sub.tier.value if sub else "free"
    plans = []
    for key in ("personal_2k", "personal", "personal_10k"):
        try:
            t = _billing.PlanTier(key)
            d = _billing.PLAN_DETAILS[t]
            plans.append({"tier": key, "name": d["name"],
                          "price_yearly": d["price_yearly"],
                          "features": d["features"], "limits": d["limits"]})
        except Exception:
            continue
    current_plan = _billing.PLAN_DETAILS.get(sub.tier, {}) if sub else {}
    return {"product": "Quantive Personal", "price_yearly_usd": 5000,
            "positioning": "annual access — profile, intelligence, docs, reporting (not AI messages)",
            "tier": tier, "status": sub.status if sub else "none",
            "renewal": (sub.current_period_end if sub else None),
            "plans": plans,
            "current_limits": current_plan.get("limits", {}) if current_plan else {},
            "gov_access": bool((current_plan.get("limits", {}) or {}).get("personal_gov_access"))}


# ── Financial Connections ─────────────────────────────────────────────

@router.get("/connections")
def list_connections(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """List all connected financial accounts."""
    from app.personal.plaid_gateway import get_connections
    uid = _uid(user)
    return {"connections": get_connections(uid, db)}


@router.post("/connections/plaid/link-token")
def create_plaid_link_token(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Create a Plaid Link token for connecting bank accounts."""
    from app.personal.plaid_gateway import create_link_token
    uid = _uid(user)
    return create_link_token(uid)


@router.post("/connections/plaid/exchange")
def exchange_plaid_token(payload: dict, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Exchange Plaid public token for access token."""
    from app.personal.plaid_gateway import exchange_public_token
    uid = _uid(user)
    public_token = payload.get("public_token", "")
    if not public_token:
        raise HTTPException(400, "public_token required")
    result = exchange_public_token(uid, public_token, db)
    _audit(db, uid, "connection.plaid_exchange", "connection", result.get("connection_id", ""), {"demo": result.get("demo_mode", False)})
    return result


@router.post("/connections/{connection_id}/sync")
def sync_connection(connection_id: str, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Sync transactions from a connected account."""
    from app.personal.plaid_gateway import sync_transactions
    result = sync_transactions(connection_id, db)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.delete("/connections/{connection_id}")
def disconnect_account(connection_id: str, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Disconnect a financial account."""
    from app.personal.plaid_gateway import disconnect_connection
    uid = _uid(user)
    if not disconnect_connection(connection_id, db):
        raise HTTPException(404, "Connection not found")
    _audit(db, uid, "connection.disconnect", "connection", connection_id, {})
    return {"ok": True}


# ── Transactions ─────────────────────────────────────────────────────

@router.get("/transactions")
def list_transactions(user=Depends(get_current_user), db: Session = Depends(get_personal_db),
                      limit: int = 50, offset: int = 0, category: str = "", tax_tag: str = ""):
    """List transactions with optional filtering."""
    from app.personal.models import Transaction as TxnModel
    uid = _uid(user)
    q = db.query(TxnModel).filter(TxnModel.user_id == uid)
    if category:
        q = q.filter(TxnModel.category == category)
    if tax_tag:
        q = q.filter(TxnModel.tax_tag == tax_tag)
    total = q.count()
    txns = q.order_by(TxnModel.date.desc()).offset(offset).limit(limit).all()
    return {
        "transactions": [
            {
                "id": t.id, "date": t.date, "name": t.name, "merchant_name": t.merchant_name,
                "amount": t.amount, "category": t.category, "tax_tag": t.tax_tag,
                "confidence": t.confidence, "notes": t.notes, "excluded": t.excluded,
                "connection_id": t.connection_id,
            }
            for t in txns
        ],
        "total": total, "limit": limit, "offset": offset,
    }


@router.put("/transactions/{txn_id}/categorize")
def categorize_transaction(txn_id: str, payload: dict, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Manually categorize a transaction."""
    from app.personal.models import Transaction as TxnModel
    uid = _uid(user)
    txn = db.query(TxnModel).filter(TxnModel.id == txn_id, TxnModel.user_id == uid).first()
    if not txn:
        raise HTTPException(404, "Transaction not found")
    if "tax_tag" in payload:
        txn.tax_tag = payload["tax_tag"]
        txn.confidence = "manual"
    if "category" in payload:
        txn.category = payload["category"]
    if "notes" in payload:
        txn.notes = payload["notes"]
    if "excluded" in payload:
        txn.excluded = payload["excluded"]
    db.commit()
    return {"ok": True, "tax_tag": txn.tax_tag, "category": txn.category}


@router.get("/transactions/summary")
def transaction_summary(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Get transaction summary by category and tax tag."""
    from app.personal.models import Transaction as TxnModel
    from sqlalchemy import func
    uid = _uid(user)
    year_start = f"{datetime.now(timezone.utc).year}-01-01"

    by_category = db.query(
        TxnModel.category, func.count(TxnModel.id), func.sum(TxnModel.amount)
    ).filter(
        TxnModel.user_id == uid, TxnModel.date >= year_start, TxnModel.excluded == False
    ).group_by(TxnModel.category).all()

    by_tax_tag = db.query(
        TxnModel.tax_tag, func.count(TxnModel.id), func.sum(TxnModel.amount)
    ).filter(
        TxnModel.user_id == uid, TxnModel.date >= year_start, TxnModel.excluded == False
    ).group_by(TxnModel.tax_tag).all()

    return {
        "by_category": [{"category": c, "count": n, "total": t or 0} for c, n, t in by_category],
        "by_tax_tag": [{"tax_tag": t, "count": n, "total": s or 0} for t, n, s in by_tax_tag],
    }


# ── Compliance Monitoring ────────────────────────────────────────────

@router.get("/compliance/status")
def compliance_status(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Get compliance monitoring status."""
    from app.personal.compliance import get_compliance_status
    uid = _uid(user)
    return get_compliance_status(uid, db)


@router.get("/compliance/withholding")
def compliance_withholding(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Analyze withholding adequacy."""
    from app.personal.compliance import analyze_withholding
    uid = _uid(user)
    return analyze_withholding(uid, db)


@router.post("/compliance/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Acknowledge a compliance alert."""
    from app.personal.models import ComplianceAlert
    uid = _uid(user)
    alert = db.query(ComplianceAlert).filter(
        ComplianceAlert.id == alert_id, ComplianceAlert.user_id == uid
    ).first()
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.acknowledged = True
    db.commit()
    return {"ok": True}


# ── Tax Projection ───────────────────────────────────────────────────

@router.get("/projection")
def tax_projection(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Get current tax projection."""
    from app.personal.tax_projection import project_annual
    uid = _uid(user)
    return project_annual(uid, db)


@router.get("/projection/ytd")
def projection_ytd(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Get year-to-date income and withholding."""
    from app.personal.tax_projection import get_ytd_data
    uid = _uid(user)
    return get_ytd_data(uid, db)


@router.post("/projection/what-if")
def projection_what_if(payload: dict, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Run what-if tax scenarios."""
    from app.personal.tax_projection import what_if
    uid = _uid(user)
    scenario = {
        "additional_income": payload.get("additional_income", 0),
        "additional_deductions": payload.get("additional_deductions", 0),
        "roth_conversion": payload.get("roth_conversion", 0),
        "capital_gain": payload.get("capital_gain", 0),
        "capital_loss": payload.get("capital_loss", 0),
    }
    return what_if(uid, db, scenario)


@router.post("/projection/save")
def save_projection(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Save current projection snapshot."""
    from app.personal.tax_projection import save_projection
    uid = _uid(user)
    tp = save_projection(uid, db)
    return {"id": tp.id, "tax_year": tp.tax_year, "projected_total_tax": tp.projected_total_tax}


# ── Recommendations ──────────────────────────────────────────────────

@router.get("/recommendations")
def list_recommendations(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Get personalized tax recommendations."""
    from app.personal.recommendation_engine import generate_recommendations
    from app.personal.models import Recommendation as RecModel
    uid = _uid(user)
    # Check if recommendations exist, generate if not
    existing = db.query(RecModel).filter(
        RecModel.user_id == uid, RecModel.status == "new"
    ).count()
    if existing == 0:
        recs = generate_recommendations(uid, db)
    else:
        recs = db.query(RecModel).filter(
            RecModel.user_id == uid, RecModel.status != "dismissed"
        ).order_by(RecModel.priority).all()
    return {
        "recommendations": [
            {
                "id": r.id, "title": r.title, "category": r.category,
                "priority": r.priority, "type": r.type, "why": r.why,
                "estimated_savings_min": r.estimated_savings_min,
                "estimated_savings_max": r.estimated_savings_max,
                "confidence": r.confidence, "irc_section": r.irc_section,
                "action_steps": r.action_steps, "risks": r.risks,
                "deadline": r.deadline, "status": r.status,
            }
            for r in recs
        ],
        "total": len(recs),
    }


@router.post("/recommendations/{rec_id}/status")
def update_recommendation(rec_id: str, payload: dict, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Update recommendation status (viewed, accepted, implemented, dismissed)."""
    from app.personal.recommendation_engine import update_recommendation_status
    uid = _uid(user)
    status = payload.get("status", "viewed")
    rec = update_recommendation_status(rec_id, status, uid, db)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return {"ok": True, "status": rec.status}


# ── Recommendation Feedback ───────────────────────────────────────

@router.post("/recommendations/{rec_id}/feedback")
def submit_feedback(rec_id: str, payload: dict, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Submit feedback on a recommendation (thumbs_up, thumbs_down, implemented, dismissed)."""
    from app.personal.models import RecommendationFeedback, Recommendation as RecModel
    uid = _uid(user)
    feedback_type = payload.get("feedback_type", "")
    if feedback_type not in ("thumbs_up", "thumbs_down", "implemented", "dismissed"):
        raise HTTPException(400, "Invalid feedback_type")
    rec = db.query(RecModel).filter(RecModel.id == rec_id, RecModel.user_id == uid).first()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    fb = RecommendationFeedback(
        user_id=uid,
        recommendation_id=rec_id,
        feedback_type=feedback_type,
        comment=payload.get("comment", ""),
        actual_savings=payload.get("actual_savings", 0),
    )
    db.add(fb)
    if feedback_type == "implemented":
        rec.status = "implemented"
    elif feedback_type == "dismissed":
        rec.status = "dismissed"
    db.commit()
    _audit(db, uid, "recommendation.feedback", "recommendation", rec_id, {"feedback": feedback_type})
    return {"ok": True}


@router.get("/recommendations/feedback-stats")
def feedback_stats(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Get feedback statistics for the user's recommendations."""
    from app.personal.models import RecommendationFeedback, Recommendation as RecModel
    uid = _uid(user)
    total = db.query(RecModel).filter(RecModel.user_id == uid).count()
    implemented = db.query(RecModel).filter(RecModel.user_id == uid, RecModel.status == "implemented").count()
    dismissed = db.query(RecModel).filter(RecModel.user_id == uid, RecModel.status == "dismissed").count()
    feedbacks = db.query(RecommendationFeedback).filter(RecommendationFeedback.user_id == uid).all()
    thumbs_up = sum(1 for f in feedbacks if f.feedback_type == "thumbs_up")
    thumbs_down = sum(1 for f in feedbacks if f.feedback_type == "thumbs_down")
    return {
        "total_recommendations": total,
        "implemented": implemented,
        "dismissed": dismissed,
        "thumbs_up": thumbs_up,
        "thumbs_down": thumbs_down,
        "acceptance_rate": round(implemented / max(total, 1) * 100, 1),
    }


# ── Deduction Detector ────────────────────────────────────────────

@router.post("/deductions/scan")
def scan_deductions(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Scan transactions for deduction opportunities."""
    from app.personal.deduction_detector import get_deduction_summary
    uid = _uid(user)
    return get_deduction_summary(uid, db)


@router.get("/api/personal/deductions/summary")
def deduction_summary(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Get deduction detection summary for dashboard."""
    from app.personal.deduction_detector import get_deduction_summary
    uid = _uid(user)
    return get_deduction_summary(uid, db)


@router.post("/api/personal/deductions/claim")
def claim_deduction(payload: dict, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Mark a deduction as claimed (adds to profile facts)."""
    from app.personal.models import ProfileFact
    uid = _uid(user)
    category = payload.get("category", "")
    amount = payload.get("amount", 0)
    irc_section = payload.get("irc_section", "")
    if not category:
        raise HTTPException(400, "category required")
    fact = ProfileFact(
        user_id=uid,
        category="deduction_claimed",
        key=category,
        value=str(amount),
        value_json={"amount": amount, "irc_section": irc_section},
        source="deduction_detector",
        confidence="user_reported",
    )
    db.add(fact)
    db.commit()
    _audit(db, uid, "deduction.claimed", "deduction", category, {"amount": amount, "irc": irc_section})
    return {"ok": True}


# ── Year-End Tax Sprint ───────────────────────────────────────────

@router.get("/sprint/status")
def sprint_status(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Get Tax Sprint status (year-end countdown dashboard)."""
    from app.personal.tax_sprint import get_sprint_status
    uid = _uid(user)
    return get_sprint_status(uid, db)


@router.get("/sprint/actions")
def sprint_actions(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Get available Tax Sprint actions."""
    from app.personal.tax_sprint import get_sprint_actions
    uid = _uid(user)
    return {"actions": get_sprint_actions(uid, db)}


@router.post("/sprint/actions/{action_id}/progress")
def update_sprint_progress(action_id: str, payload: dict, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Update sprint action progress (started, completed)."""
    from app.personal.tax_sprint import update_sprint_progress
    uid = _uid(user)
    status = payload.get("status", "started")
    result = update_sprint_progress(uid, action_id, status, db)
    if not result:
        raise HTTPException(404, "Sprint action not found")
    return {"ok": True, "status": status}


@router.get("/sprint/summary")
def sprint_summary(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Get sprint summary stats for dashboard header."""
    from app.personal.tax_sprint import get_sprint_summary
    uid = _uid(user)
    return get_sprint_summary(uid, db)


# ── Notifications ─────────────────────────────────────────────────

@router.get("/notifications")
def list_notifications(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Get all notifications for the user."""
    from app.personal.notifications import generate_notifications
    uid = _uid(user)
    return {"notifications": generate_notifications(uid, db)}


@router.get("/notifications/summary")
def notification_summary(user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Get notification summary stats."""
    from app.personal.notifications import get_notification_summary
    uid = _uid(user)
    return get_notification_summary(uid, db)


@router.post("/notifications/{notif_id}/read")
def mark_notification_read(notif_id: str, user=Depends(get_current_user), db: Session = Depends(get_personal_db)):
    """Mark a notification as read."""
    from app.personal.notifications import mark_notification_read
    uid = _uid(user)
    ok = mark_notification_read(notif_id, uid, db)
    if not ok:
        raise HTTPException(404, "Notification not found")
    return {"ok": True}
