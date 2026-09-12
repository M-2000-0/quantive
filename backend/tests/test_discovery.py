"""
Tests for the Discovery / Personalized Opportunities feature.

Covers the 4-pillar scoring engine, greedy diversification, the feedback
loop, and the API endpoints.
"""

import pytest

from app.models import (
    AssetClass,
    DiscoveryAsset,
    DiscoveryFeedback,
    DiscoveryPreference,
    FeedbackAction,
)
from app.services.discovery_engine import DiscoveryEngine, FeedbackLoop, assign_tiers

from tests.conftest import TestingSessionLocal


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Engine unit tests ────────────────────────────────────────────────

def test_seed_universe_popsulates_all_four_classes(db_session):
    engine = DiscoveryEngine(db_session)
    count = engine.seed_universe()
    assert count > 0
    assets = engine.universe()
    classes = {a.asset_class for a in assets}
    assert {AssetClass.STOCK, AssetClass.ETF, AssetClass.CRYPTO, AssetClass.ALTERNATIVE} <= classes


def test_seed_is_idempotent(db_session):
    engine = DiscoveryEngine(db_session)
    engine.seed_universe()
    first = len(engine.universe())
    engine.seed_universe()  # no-op
    assert len(engine.universe()) == first


def test_scoring_produces_pillars_and_bounded_score(db_session):
    engine = DiscoveryEngine(db_session)
    pref = DiscoveryPreference(user_id="u1")
    assets = engine.universe()
    scored = engine.score(assets, pref)
    assert len(scored) == len(assets)
    for r in scored:
        assert {"relevance", "riskfit", "trend", "diversity", "score", "confidence"} <= set(r)
        assert 0.0 <= r["score"] <= 1.0
        assert r["confidence"] in ("high", "medium", "low")


def test_riskfit_reduces_score_for_conservative_user(db_session):
    engine = DiscoveryEngine(db_session)
    pref_conservative = DiscoveryPreference(user_id="uuid-con", max_acceptable_drawdown_pct=0.05,
                                            volatility_tolerance="low")
    pref_aggressive = DiscoveryPreference(user_id="uuid-agg", max_acceptable_drawdown_pct=0.50,
                                          volatility_tolerance="high")

    cons = engine.score(engine.universe(), pref_conservative)
    agg = engine.score(engine.universe(), pref_aggressive)

    # The riskiest stock (NVDA, high drawdown) must fit a conservative user
    # far worse than an aggressive user.
    nvda_con = next(r for r in cons if r["asset"].symbol == "NVDA")
    nvda_agg = next(r for r in agg if r["asset"].symbol == "NVDA")
    assert nvda_con["riskfit"] < nvda_agg["riskfit"]

    # Unit guard: drawdown is percent on the asset (e.g. -35) but a fraction
    # on the user preference (e.g. 0.50). For an aggressive user, NVDA's
    # drawdown (35%) must be within the 50% cap, so riskfit should be high.
    assert nvda_agg["riskfit"] >= 0.8

    # Conservative user (8% cap) must treat crypto (50% drawdown) as a
    # poor fit — near-zero riskfit, regardless of other pillars.
    btc_con = next(r for r in cons if r["asset"].symbol == "BTC")
    assert btc_con["riskfit"] < 0.2


def test_relevance_boosted_by_asset_class_interest(db_session):
    engine = DiscoveryEngine(db_session)
    pref_crypto = DiscoveryPreference(user_id="u-c1", interest_crypto=1.0, interest_stock=0.0, interest_etf=0.0, interest_alternative=0.0)
    pref_stock = DiscoveryPreference(user_id="u-s1", interest_stock=1.0, interest_crypto=0.0, interest_etf=0.0, interest_alternative=0.0)

    cons = next(r for r in engine.score(engine.universe(), pref_crypto) if r["asset"].symbol == "BTC")
    stocks = next(r for r in engine.score(engine.universe(), pref_stock) if r["asset"].symbol == "BTC")
    assert cons["relevance"] >= stocks["relevance"]


def test_diversification_enforces_cross_class_breadth(db_session):
    engine = DiscoveryEngine(db_session)
    pref = DiscoveryPreference(user_id="u-div")
    scored = engine.score(engine.universe(), pref)
    selected = engine._diversify(scored, 10)
    assert len(selected) <= 10
    from collections import Counter
    counts = Counter(r["asset"].asset_class for r in selected)
    assert all(c <= 3 for c in counts.values())


def test_tiers_assigned(db_session):
    engine = DiscoveryEngine(db_session)
    pref = DiscoveryPreference(user_id="u-tier")
    scored = engine.score(engine.universe(), pref)
    selected = engine._diversify(scored, 8)
    assign_tiers(selected)
    assert all(r.get("tier") in ("strong_match", "worth_exploring", "stretch_opportunity") for r in selected)


def test_feedback_loop_adapts_weights(db_session):
    import app.services.discovery_engine as de
    engine = DiscoveryEngine(db_session)
    engine.seed_universe()
    pref = DiscoveryPreference(user_id="u-fb")
    db_session.add(pref)
    db_session.commit()
    db_session.refresh(pref)

    asset = db_session.query(DiscoveryAsset).filter(DiscoveryAsset.symbol == "BTC").first()
    loop = FeedbackLoop()
    loop.record(db_session, "u-fb", pref, asset, FeedbackAction.TOO_RISKY)

    assert de.MIN_PILLAR_WEIGHT <= pref.weight_riskfit <= de.MAX_PILLAR_WEIGHT
    total = pref.weight_relevance + pref.weight_riskfit + pref.weight_trend + pref.weight_diversity
    assert abs(total - 1.0) < 0.02

    fb = db_session.query(DiscoveryFeedback).filter(DiscoveryFeedback.user_id == "u-fb").all()
    assert len(fb) == 1
    assert fb[0].action == FeedbackAction.TOO_RISKY


# ── API tests ────────────────────────────────────────────────────────

def test_opportunities_endpoint_requires_auth(client):
    resp = client.get("/api/discovery/opportunities")
    assert resp.status_code in (401, 307)  # unauthorized


def test_opportunities_endpoint_returns_personalized(auth_client):
    resp = auth_client.get("/api/discovery/opportunities")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 3
    assert "opportunities" in body
    assert "tiers" in body
    assert "profile_weights" in body
    for opp in body["opportunities"]:
        assert opp["asset_class"] in ("stock", "etf", "crypto", "alternative")
        assert 0.0 <= opp["score"] <= 1.0
        assert opp["confidence"]
    classes = {o["asset_class"] for o in body["opportunities"]}
    assert len(classes) >= 2


def test_opportunities_can_filter_by_asset_class(auth_client):
    resp = auth_client.get("/api/discovery/opportunities?asset_class=crypto")
    assert resp.status_code == 200
    body = resp.json()
    assert all(o["asset_class"] == "crypto" for o in body["opportunities"])


def test_assets_endpoint(auth_client):
    resp = auth_client.get("/api/discovery/assets")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0
    classes = {a["asset_class"] for a in body}
    assert classes >= {"stock", "etf", "crypto", "alternative"}


def test_feedback_endpoint_records_and_adapts(auth_client):
    resp = auth_client.get("/api/discovery/opportunities")
    assert resp.status_code == 200
    targets = resp.json()["opportunities"]
    assert targets

    target = targets[0]
    fb = auth_client.post("/api/discovery/feedback", json={
        "asset_symbol": target["symbol"],
        "action": "dismissed",
        "reason": "not what I'm looking for",
        "surfaced_rank": 1,
    })
    assert fb.status_code == 200
    body = fb.json()
    assert body["status"] == "recorded"
    assert "updated_weights" in body
    assert abs(sum(body["updated_weights"].values()) - 1.0) < 0.02


def test_feedback_unknown_asset_404(auth_client):
    resp = auth_client.post("/api/discovery/feedback", json={
        "asset_symbol": "NOT_A_REAL_SYMBOL_XYZ",
        "action": "liked",
    })
    assert resp.status_code == 404
