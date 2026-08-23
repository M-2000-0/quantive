"""API endpoint tests (FastAPI TestClient + async job polling)."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from quantive.api.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _create_synthetic_portfolio(client, seed=42):
    r = client.post("/portfolios", json={"synthetic": True, "seed": seed, "name": "Synthetic Portfolio"})
    assert r.status_code == 201
    return r.json()


def _create_problem(client, portfolio_id):
    r = client.post("/optimization", json={
        "portfolio_id": portfolio_id,
        "name": "API Test Problem",
        "financing_requirement": 120000.0,
    })
    assert r.status_code == 201
    return r.json()


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["health"] == "ok"


def test_create_and_get_portfolio(client):
    pf = _create_synthetic_portfolio(client)
    r = client.get(f"/portfolios/{pf['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == pf["id"]
    assert len(body["instruments"]) >= 50
    assert "Synthetic Demonstration Portfolio" in body["description"]


def test_upload_custom_portfolio(client):
    payload = {
        "synthetic": False,
        "name": "Custom Portfolio",
        "instruments": [{
            "id": "custom-1",
            "name": "Custom Bond",
            "currency": "USD",
            "principal": 100.0,
            "coupon": 0.04,
            "rate_type": "fixed",
            "maturity_date": "2040-01-01",
            "issue_date": "2024-01-01",
            "liquidity": 0.9,
            "market_capacity": 100.0,
        }],
    }
    r = client.post("/portfolios", json=payload)
    assert r.status_code == 201
    assert r.json()["instruments"][0]["id"] == "custom-1"


def test_get_missing_portfolio_404(client):
    r = client.get("/portfolios/nope")
    assert r.status_code == 404


def test_create_and_get_optimization(client):
    pf = _create_synthetic_portfolio(client)
    prob = _create_problem(client, pf["id"])
    r = client.get(f"/optimization/{prob['id']}")
    assert r.status_code == 200
    assert r.json()["portfolio_id"] == pf["id"]
    assert len(r.json()["scenarios"]) == 6


def test_run_and_poll_job(client):
    pf = _create_synthetic_portfolio(client, seed=5)
    prob = _create_problem(client, pf["id"])
    r = client.post(f"/optimization/{prob['id']}/run")
    assert r.status_code == 202
    job_id = r.json()["job_id"]

    status = "pending"
    for _ in range(180):
        jr = client.get(f"/optimization/jobs/{job_id}")
        assert jr.status_code == 200
        status = jr.json()["status"]
        if status in ("completed", "failed"):
            break
        time.sleep(1)
    assert status == "completed"


def test_results_endpoints_after_run(client):
    pf = _create_synthetic_portfolio(client, seed=11)
    prob = _create_problem(client, pf["id"])
    client.post(f"/optimization/{prob['id']}/run")
    job_id = client.post(f"/optimization/{prob['id']}/run").json()["job_id"]
    for _ in range(180):
        if client.get(f"/optimization/jobs/{job_id}").json()["status"] in ("completed", "failed"):
            break
        time.sleep(1)

    r = client.get(f"/optimization/{prob['id']}/results")
    assert r.status_code == 200
    strategy = r.json()["result"]["strategy"]
    assert strategy["feasible"] is True
    assert strategy["solver_type"] in ("classical", "heuristic", "quantum_inspired")

    r = client.get(f"/optimization/{prob['id']}/strategies")
    assert r.status_code == 200
    strategies = r.json()
    assert len(strategies) == 4
    assert {s["profile"] for s in strategies} == {"best_overall", "lowest_risk", "lowest_cost", "stress_resilient"}

    r = client.get(f"/optimization/{prob['id']}/benchmark")
    assert r.status_code == 200
    rows = r.json()["rows"]
    assert len(rows) == 3
    assert [row["rank"] for row in rows] == [1, 2, 3]

    r = client.get(f"/optimization/{prob['id']}/scenarios")
    assert r.status_code == 200
    assert len(r.json()) == 6

    r = client.get(f"/optimization/{prob['id']}/stress")
    assert r.status_code == 200
    stress = r.json()
    assert "strategy-best_overall" in stress


def test_results_before_run_404(client):
    pf = _create_synthetic_portfolio(client, seed=13)
    prob = _create_problem(client, pf["id"])
    r = client.get(f"/optimization/{prob['id']}/results")
    assert r.status_code == 404


def test_job_404(client):
    assert client.get("/optimization/jobs/nope").status_code == 404


def test_missing_job_status_has_no_result_flag(client):
    pf = _create_synthetic_portfolio(client, seed=17)
    prob = _create_problem(client, pf["id"])
    r = client.post(f"/optimization/{prob['id']}/run")
    body = client.get(f"/optimization/jobs/{r.json()['job_id']}").json()
    assert "has_result" in body