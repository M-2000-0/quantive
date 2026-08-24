import json
import os
import time

import pytest

DEMO_PATH = os.path.join(os.path.dirname(__file__), "..", "demo", "synthetic_portfolio.json")


@pytest.mark.slow
def test_e2e_full_workflow(client):
    resp = client.post("/api/auth/register", json={
        "email": "analyst@treasury.gov",
        "password": "SecureP@ss123",
        "name": "Treasury Analyst",
        "org_name": "Ministry of Finance",
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"

    with open(DEMO_PATH) as f:
        portfolio_data = json.load(f)

    portfolio_data["description"] = "Synthetic sovereign portfolio for E2E test. ALL DATA IS SYNTHETIC."
    resp = client.post("/api/portfolios", json=portfolio_data)
    assert resp.status_code == 201
    portfolio = resp.json()
    assert len(portfolio["instruments"]) == 72
    portfolio_id = portfolio["id"]

    resp = client.get(f"/api/portfolios/{portfolio_id}")
    assert resp.status_code == 200

    resp = client.post("/api/optimizations", json={
        "portfolio_id": portfolio_id,
        "name": "E2E Sovereign Debt Optimization",
        "optimization_type": "minimize_cost",
        "objectives": {"type": "minimize_cost", "risk_aversion": 1.0},
        "constraints": {
            "max_single_instrument_pct": 0.25,
            "min_diversification": 3,
        },
        "solver_config": {"solvers": ["greedy", "mean_variance", "scenario_based"]},
        "scenario_config": {
            "num_scenarios": 500,
            "horizon_years": 5,
            "rate_volatility": 0.02,
            "inflation_mean": 0.03,
        },
        "random_seed": 42,
    })
    assert resp.status_code == 201
    job = resp.json()
    job_id = job["id"]

    completed = False
    for _ in range(120):
        time.sleep(1)
        status_resp = client.get(f"/api/optimizations/{job_id}")
        status_data = status_resp.json()
        if status_data["status"] == "completed":
            completed = True
            break
        assert status_data["status"] != "failed", f"Job failed: {status_data.get('error_message')}"

    assert completed, "Optimization did not complete within timeout"

    strategies = client.get(f"/api/optimizations/{job_id}/strategies")
    assert strategies.status_code == 200
    strat_list = strategies.json()
    assert len(strat_list) >= 2
    for s in strat_list:
        assert "allocations" in s
        assert "metrics" in s
        assert "stress_test_results" in s
        assert s["stress_test_results"] is not None

    benchmarks = client.get(f"/api/optimizations/{job_id}/benchmarks")
    assert benchmarks.status_code == 200
    bench_list = benchmarks.json()
    assert len(bench_list) >= 2
    solver_names = {b["solver_name"] for b in bench_list}
    assert "greedy" in solver_names

    report = client.get(f"/api/optimizations/{job_id}/report")
    assert report.status_code == 200
    report_data = report.json()
    assert report_data["job_name"] == "E2E Sovereign Debt Optimization"
    assert len(report_data["strategies"]) >= 2
    assert len(report_data["benchmarks"]) >= 2
    assert report_data["portfolio"]["num_instruments"] == 72

    audit = client.get("/api/audit")
    assert audit.status_code == 200
    audit_events = audit.json()
    assert len(audit_events) > 0
    actions = {e["action"] for e in audit_events}
    assert "portfolio.created" in actions or "portfolio.uploaded" in actions
    assert "optimization.created" in actions

    print("\n=== E2E Test Complete ===")
    print(f"Portfolio: {portfolio['name']} ({len(portfolio['instruments'])} instruments)")
    print(f"Job: {job['name']} - Status: completed")
    print(f"Strategies: {len(strat_list)}")
    print(f"Benchmarks: {len(bench_list)}")
    print(f"Audit events: {len(audit_events)}")
