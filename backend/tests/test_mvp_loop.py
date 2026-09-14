"""MVP core-loop regression test: the one promise Quantive makes.

register -> portfolio -> optimize -> completed -> list -> dashboard.
If this breaks, the product is broken — hence its own file.
Kept fast on purpose (100 scenarios, single instrument).
"""
import time


def _register(client, email):
    resp = client.post("/api/auth/register", json={
        "email": email,
        "password": "Test@Pass123",
        "name": "MVP",
        "org_name": "MVP Org",
    })
    assert resp.status_code == 201, resp.text
    client.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    return client


def test_mvp_core_loop(auth_client):
    c = auth_client

    p = c.post("/api/portfolios", json={
        "name": "MVP Portfolio",
        "description": "core loop",
        "instruments": [{
            "name": "Bond A", "instrument_type": "treasury_bond", "currency": "USD",
            "principal_outstanding": 1_000_000_000, "coupon_rate": 0.045,
            "maturity_date": "2030-01-01", "issue_date": "2020-01-01",
            "spread_bps": 50,
        }],
    })
    assert p.status_code in (200, 201), p.text
    portfolio_id = p.json()["id"]

    o = c.post("/api/optimizations", json={
        "portfolio_id": portfolio_id,
        "name": "MVP run",
        "optimization_type": "minimize_cost",
        "objectives": {"cost": 1.0},
        "constraints": {},
        "solver_config": {},
        "scenario_config": {"num_scenarios": 100},
        "random_seed": 42,
    })
    assert o.status_code in (200, 201, 202), o.text
    job_id = o.json()["id"]

    deadline = time.time() + 120
    status = "?"
    while time.time() < deadline:
        g = c.get(f"/api/optimizations/{job_id}")
        assert g.status_code == 200, g.text
        status = g.json().get("status", "?")
        if status in ("completed", "COMPLETED", "failed", "FAILED", "cancelled", "CANCELLED"):
            break
        time.sleep(3)
    assert status in ("completed", "COMPLETED"), f"job ended as {status}"

    listing = c.get("/api/portfolios", params={"page_size": 5})
    assert listing.status_code == 200
    assert any(p["id"] == portfolio_id for p in listing.json()["data"])

    dash = c.get("/api/dashboard/summary")
    assert dash.status_code == 200
    assert dash.json()["portfolio_count"] >= 1
