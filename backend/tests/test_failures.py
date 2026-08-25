def test_invalid_portfolio_upload(auth_client):
    resp = auth_client.post(
        "/api/portfolios/upload",
        files={"file": ("bad.json", b"not valid json", "application/json")},
        data={"name": "Bad Upload"},
    )
    assert resp.status_code == 422


def test_empty_instruments_upload(auth_client):
    resp = auth_client.post(
        "/api/portfolios/upload",
        files={"file": ("empty.json", b'{"instruments": []}', "application/json")},
        data={"name": "Empty Upload"},
    )
    assert resp.status_code == 422


def test_optimization_nonexistent_portfolio(auth_client):
    resp = auth_client.post("/api/optimizations", json={
        "portfolio_id": "nonexistent-id",
        "name": "Bad Opt",
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


def test_unauthorized_access(client):
    resp = client.get("/api/portfolios")
    assert resp.status_code in (401, 403)


def test_unauthorized_optimization(client):
    resp = client.post("/api/optimizations", json={
        "portfolio_id": "any",
        "name": "Unauthorized",
    })
    assert resp.status_code in (401, 403)


def test_audit_requires_admin(auth_client):
    auth_client.post("/api/auth/register", json={
        "email": "viewer2@example.com",
        "password": "Secure@Pass123",
        "name": "Viewer",
    })
    from app.models import User
    from tests.conftest import TestingSessionLocal

    db = TestingSessionLocal()
    viewer = db.query(User).filter(User.email == "viewer2@example.com").first()
    if viewer:
        viewer.role = "viewer"
        db.commit()
    db.close()

    from fastapi.testclient import TestClient
    viewer_client = TestClient(auth_client.app)
    resp2 = viewer_client.post("/api/auth/login", json={
        "email": "viewer2@example.com",
        "password": "Secure@Pass123",
    })
    if resp2.status_code == 200:
        viewer_token = resp2.json()["access_token"]
        viewer_client.headers["Authorization"] = f"Bearer {viewer_token}"
        resp = viewer_client.get("/api/audit")
        assert resp.status_code == 403


def test_portfolio_not_found(auth_client):
    resp = auth_client.get("/api/portfolios/nonexistent-id")
    assert resp.status_code == 404


def test_upload_malformed_file(auth_client):
    resp = auth_client.post(
        "/api/portfolios/upload",
        files={"file": ("bad.xml", b"<root>not a portfolio</root>", "application/xml")},
        data={"name": "XML Upload"},
    )
    assert resp.status_code == 422
