"""Quantive Personal tests — isolated from sovereign tables by design.

Uses a temp Personal DB file (never the dev quantive_personal.db) and
function-level calls (no sovereign auth/DB required).
"""
import asyncio

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import billing as billing_mod
from app.personal.database import PersonalBase
from app.personal.models import ProfileFact
from app.personal.onboarding_questions import QUESTIONS, visible_questions
from app.personal.opportunity_engine import detect
from app.personal.scoring import compute_score

import app.personal.api as personal_api


@pytest.fixture()
def pdb(tmp_path):
    url = f"sqlite:///{tmp_path}/personal_test.db"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    PersonalBase.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _stub_user(uid="test_user"):
    return type("StubUser", (), {"id": uid, "org_id": f"org_{uid}"})()


def _add_fact(db, uid, category, key, value):
    db.add(ProfileFact(user_id=uid, category=category, key=key, value=value,
                       value_json={"values": [value]}, source="onboarding",
                       confidence="user_reported", status="confirmed"))
    db.commit()


# ── Onboarding ────────────────────────────────────────────────────

def test_baseline_is_24_questions():
    assert len(QUESTIONS) == 24


def test_adaptive_skip_hides_mortgage_detail():
    vis = visible_questions({"housing": ["rent"]})
    ids = {q["id"] for q in vis}
    assert "mortgage_detail" not in ids
    vis2 = visible_questions({"housing": ["mortgage"]})
    assert "mortgage_detail" in {q["id"] for q in vis2}


# ── Scoring (readiness only, never savings) ───────────────────────

def test_score_caps_at_100_and_floors_at_0():
    assert compute_score(facts_count=99, visible_total=10, open_actions=0,
                         doc_gaps=0, needs_review=0)["score"] == 100
    assert compute_score(facts_count=0, visible_total=10, open_actions=99,
                         doc_gaps=99, needs_review=0)["score"] >= 0


# ── Plan enforcement ──────────────────────────────────────────────

def test_no_subscription_fails_closed_to_starter_caps():
    tier, limits = personal_api._personal_plan(_stub_user("no_sub_new_user_xyz"))
    assert limits.get("personal_opportunities") == 3
    assert limits.get("personal_documents") == 10
    assert limits.get("personal_asks_per_month") == 20
    assert not limits.get("personal_gov_access")


def test_limit_allows_boundary():
    assert personal_api._limit_allows({"personal_documents": 10}, "personal_documents", 9)
    assert not personal_api._limit_allows({"personal_documents": 10}, "personal_documents", 10)
    assert personal_api._limit_allows({}, "personal_documents", 999)


def test_plan_tiers_priced():
    assert billing_mod.PLAN_DETAILS[billing_mod.PlanTier.PERSONAL_2K]["price_yearly"] == 2000
    assert billing_mod.PLAN_DETAILS[billing_mod.PlanTier.PERSONAL]["price_yearly"] == 5000
    assert billing_mod.PLAN_DETAILS[billing_mod.PlanTier.PERSONAL_10K]["price_yearly"] == 10000


# ── Opportunity detector tiers ────────────────────────────────────

def test_detect_base_vs_sovereign(pdb):
    uid = "tier_user"
    _add_fact(pdb, uid, "housing", "housing", "mortgage")
    _add_fact(pdb, uid, "financial", "invest_accounts", "yes")
    base = {o.title for o in detect(pdb, uid)}
    sov = {o.title for o in detect(pdb, uid, tier="personal_10k")}
    assert "Mortgage interest" in base
    assert "Qubo trend alignment" not in base
    assert "Qubo trend alignment" in sov
    assert "Sovereign insight briefing" in sov


def test_gov_insights_locked_without_sovereign(pdb):
    with pytest.raises(HTTPException) as exc:
        personal_api.gov_insights(user=_stub_user("locked_user"), db=pdb)
    assert exc.value.status_code == 403


def test_checkout_rejects_non_personal_tier():
    from starlette.requests import Request
    scope = {"type": "http", "method": "POST", "headers": [],
             "server": ("testserver", 80), "scheme": "http", "path": "/"}
    with pytest.raises(HTTPException) as exc:
        asyncio.run(personal_api.personal_checkout(
            {"tier": "enterprise"}, request=Request(scope),
            user=_stub_user("checkout_user")))
    assert exc.value.status_code == 422


# ── Worldwide jurisdiction packs ────────────────────────────────

def test_every_rule_forces_verification():
    from app.personal.tax_packs import PACKS
    for (juris, year), rules in PACKS.items():
        assert rules, f"empty pack {juris}-{year}"
        for r in rules:
            assert "verif" in r["summary"].lower(), f"{r['id']} lacks verify language"
            assert r["sources"], f"{r['id']} has no sources"
            assert r["jurisdiction"] == juris and r["tax_year"] == year


def _country_user(db, uid, country, extra=()):
    _add_fact(db, uid, "tax", "country", country)
    for category, key, value in extra:
        _add_fact(db, uid, category, key, value)


def test_us_user_gets_us_refs(pdb):
    uid = "us_user"
    _country_user(pdb, uid, "US", [("financial", "donations", "yes"),
                                   ("health", "medical_exp", "yes")])
    refs = [r for o in detect(pdb, uid) for r in (o.rule_refs or [])]
    assert any(r.startswith("US-2026-") for r in refs)
    assert not any(r.startswith(("BD-2026-", "MX-2026-")) for r in refs)


def test_bd_user_gets_bd_refs(pdb):
    uid = "bd_user"
    _country_user(pdb, uid, "BD", [("income", "employment_detail", "yes"),
                                   ("housing", "housing", "mortgage")])
    titles = {o.title for o in detect(pdb, uid)}
    refs = [r for o in detect(pdb, uid) for r in (o.rule_refs or [])]
    assert "House rent allowance" in titles
    assert any(r.startswith("BD-2026-") for r in refs)
    assert not any(r.startswith(("US-2026-", "MX-2026-")) for r in refs)


def test_unknown_country_gets_generic_only(pdb):
    uid = "unknown_user"
    _country_user(pdb, uid, "other", [("housing", "housing", "mortgage"),
                                      ("financial", "donations", "yes")])
    refs = [r for o in detect(pdb, uid) for r in (o.rule_refs or [])]
    assert refs, "expected generic fallback opportunities"
    assert all(r.startswith("GEN-2026-") for r in refs)


def test_mx_mortgage_keeps_mx_ref(pdb):
    uid = "mx_user"
    _country_user(pdb, uid, "MX", [("housing", "housing", "mortgage")])
    refs = [r for o in detect(pdb, uid) for r in (o.rule_refs or [])]
    assert "MX-2026-mortgage-interest" in refs
