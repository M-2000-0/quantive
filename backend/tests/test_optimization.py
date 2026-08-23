import time

from fastapi.testclient import TestClient


def test_create_optimization(auth_client, sample_portfolio_data):
    portfolio_resp = auth_client.post("/api/portfolios", json=sample_portfolio_data)
    portfolio_id = portfolio_resp.json()["id"]

    resp = auth_client.post("/api/optimizations", json={
        "portfolio_id": portfolio_id,
        "name": "Test Optimization",
        "optimization_type": "minimize_cost",
        "scenario_config": {"num_scenarios": 100},
        "random_seed": 42,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] in ("queued", "running", "completed")
    assert data["name"] == "Test Optimization"


def test_optimization_completes(auth_client, sample_portfolio_data):
    portfolio_resp = auth_client.post("/api/portfolios", json=sample_portfolio_data)
    portfolio_id = portfolio_resp.json()["id"]

    resp = auth_client.post("/api/optimizations", json={
        "portfolio_id": portfolio_id,
        "name": "Full Test",
        "optimization_type": "minimize_cost",
        "scenario_config": {"num_scenarios": 100},
        "random_seed": 42,
    })
    job_id = resp.json()["id"]

    for _ in range(120):
        time.sleep(1)
        status_resp = auth_client.get(f"/api/optimizations/{job_id}")
        status = status_resp.json()["status"]
        if status in ("completed", "failed"):
            break

    assert status == "completed", f"Job ended with status: {status}"

    strategies = auth_client.get(f"/api/optimizations/{job_id}/strategies")
    assert strategies.status_code == 200
    assert len(strategies.json()) > 0

    benchmarks = auth_client.get(f"/api/optimizations/{job_id}/benchmarks")
    assert benchmarks.status_code == 200
    assert len(benchmarks.json()) > 0

    report = auth_client.get(f"/api/optimizations/{job_id}/report")
    assert report.status_code == 200
    assert "strategies" in report.json()
    assert "benchmarks" in report.json()


def test_list_optimizations(auth_client, sample_portfolio_data):
    portfolio_resp = auth_client.post("/api/portfolios", json=sample_portfolio_data)
    auth_client.post("/api/optimizations", json={
        "portfolio_id": portfolio_resp.json()["id"],
        "name": "Listed Optimization",
    })
    resp = auth_client.get("/api/optimizations")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_optimization_invalid_portfolio(auth_client):
    resp = auth_client.post("/api/optimizations", json={
        "portfolio_id": "nonexistent",
        "name": "Bad Optimization",
    })
    assert resp.status_code == 404


def test_optimization_invalid_constraints(auth_client, sample_portfolio_data):
    portfolio_resp = auth_client.post("/api/portfolios", json=sample_portfolio_data)
    resp = auth_client.post("/api/optimizations", json={
        "portfolio_id": portfolio_resp.json()["id"],
        "name": "Bad Constraints",
        "constraints": {"max_budget": -100},
    })
    assert resp.status_code == 422


def test_optimization_viewer_forbidden(auth_client, sample_portfolio_data):
    auth_client.post("/api/auth/register", json={
        "email": "viewer@example.com",
        "password": "securepass123",
        "name": "Viewer",
    })
    from app.models import User
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    viewer = db.query(User).filter(User.email == "viewer@example.com").first()
    if viewer:
        viewer.role = "viewer"
        db.commit()
    db.close()

    viewer_client = TestClient(auth_client.app)
    resp2 = viewer_client.post("/api/auth/login", json={
        "email": "viewer@example.com",
        "password": "securepass123",
    })
    viewer_token = resp2.json()["access_token"]
    viewer_client.headers["Authorization"] = f"Bearer {viewer_token}"

    portfolio_resp = auth_client.post("/api/portfolios", json=sample_portfolio_data)
    resp = viewer_client.post("/api/optimizations", json={
        "portfolio_id": portfolio_resp.json()["id"],
        "name": "Viewer Optimization",
    })
    assert resp.status_code == 403


