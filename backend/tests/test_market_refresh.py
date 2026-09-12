"""Persisted market snapshots + scheduled refresh."""
import time
from datetime import datetime, timedelta, timezone

from app.market_data import fx_rates, yield_curve
from app.models.market import MarketSnapshot


def _stubbed(monkeypatch, yields=None, fx=None):
    yields = yields or {"maturities": [{"label": "10Y", "rate_pct": 4.3}], "is_fallback": False}
    fx = fx or {"rates": {"USD": 1.08, "EUR": 1.0}, "is_fallback": False}
    monkeypatch.setattr(yield_curve, "fetch_treasury_yield_curve", lambda use_cache=False: yields)
    monkeypatch.setattr(fx_rates, "fetch_ecb_rates", lambda use_cache=False: fx)


def test_refresh_persists_ok(auth_client, monkeypatch):
    _stubbed(monkeypatch)
    from app.services import automation_engine
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        result = automation_engine.run_automation("market_refresh", db, trigger="manual")
    finally:
        db.close()
    assert result["status"] == "success", result
    assert result["actions_taken"] >= 2

    db = TestingSessionLocal()
    try:
        snaps = db.query(MarketSnapshot).all()
    finally:
        db.close()
    by_source = {s.source: s for s in snaps}
    assert by_source["treasury_yields"].status == "ok"
    assert by_source["fx_rates"].status == "ok"
    assert by_source["treasury_yields"].record_count == 1


def test_fallback_classified(auth_client, monkeypatch):
    _stubbed(monkeypatch,
             yields={"maturities": [{"label": "10Y"}], "is_fallback": True},
             fx={"rates": {"USD": 1.0}, "is_fallback": True})
    from app.services import automation_engine
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        automation_engine.run_automation("market_refresh", db, trigger="manual")
        statuses = {s.source: s.status for s in db.query(MarketSnapshot).all()}
    finally:
        db.close()
    assert statuses == {"treasury_yields": "fallback", "fx_rates": "fallback"}


def test_fetcher_crash_records_error(auth_client, monkeypatch):
    def boom(use_cache=False):
        raise ConnectionError("down")

    monkeypatch.setattr(yield_curve, "fetch_treasury_yield_curve", boom)
    monkeypatch.setattr(fx_rates, "fetch_ecb_rates", boom)
    from app.services import automation_engine
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        result = automation_engine.run_automation("market_refresh", db, trigger="manual")
        rows = db.query(MarketSnapshot).all()
    finally:
        db.close()
    assert result["status"] == "success"  # never crashes the scheduler
    assert {s.status for s in rows} == {"error"}


def test_pruning(auth_client, monkeypatch):
    _stubbed(monkeypatch)
    from app.services import automation_engine
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        old = MarketSnapshot(source="treasury_yields", status="ok", payload={},
                             record_count=0,
                             fetched_at=datetime.now(timezone.utc) - timedelta(days=60))
        db.add(old)
        db.commit()
        automation_engine.run_automation("market_refresh", db, trigger="manual")
        remaining_old = db.query(MarketSnapshot).filter(
            MarketSnapshot.fetched_at < datetime.now(timezone.utc) - timedelta(days=30)).count()
    finally:
        db.close()
    assert remaining_old == 0


def test_snapshots_endpoint(auth_client, monkeypatch):
    _stubbed(monkeypatch)
    from app.services import automation_engine
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        automation_engine.run_automation("market_refresh", db, trigger="manual")
    finally:
        db.close()

    r = auth_client.get("/api/data-quality/snapshots")
    assert r.status_code == 200, r.text
    by_source = {s["source"]: s for s in r.json()["snapshots"]}
    assert by_source["treasury_yields"]["stale"] is False
    assert by_source["treasury_yields"]["records"] == 1


def test_agent_market_snapshot_tool(auth_client, monkeypatch):
    _stubbed(monkeypatch)
    from app.services import automation_engine
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    try:
        automation_engine.run_automation("market_refresh", db, trigger="manual")
    finally:
        db.close()

    r = auth_client.post("/api/agent/runs", json={
        "goal": "Check market data",
        "steps": [{"tool": "market_snapshot", "args": {"source": "fx_rates"}}],
    })
    assert r.status_code == 202, r.text
    run_id = r.json()["id"]
    deadline = time.time() + 15
    last = None
    while time.time() < deadline:
        last = auth_client.get(f"/api/agent/runs/{run_id}").json()
        if last["status"] == "completed":
            break
        time.sleep(0.05)
    assert last["status"] == "completed", last
    assert last["steps"][0]["output"]["records"] == 2
