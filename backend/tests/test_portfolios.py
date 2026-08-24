def test_create_portfolio(auth_client, sample_portfolio_data):
    resp = auth_client.post("/api/portfolios", json=sample_portfolio_data)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Portfolio"
    assert len(data["instruments"]) == 3


def test_list_portfolios(auth_client, sample_portfolio_data):
    auth_client.post("/api/portfolios", json=sample_portfolio_data)
    resp = auth_client.get("/api/portfolios")
    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["total"] == 1
    assert len(data["data"]) == 1


def test_get_portfolio(auth_client, sample_portfolio_data):
    create_resp = auth_client.post("/api/portfolios", json=sample_portfolio_data)
    portfolio_id = create_resp.json()["id"]
    resp = auth_client.get(f"/api/portfolios/{portfolio_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Portfolio"


def test_get_portfolio_not_found(auth_client):
    resp = auth_client.get("/api/portfolios/nonexistent")
    assert resp.status_code == 404


def test_delete_portfolio(auth_client, sample_portfolio_data):
    create_resp = auth_client.post("/api/portfolios", json=sample_portfolio_data)
    portfolio_id = create_resp.json()["id"]
    resp = auth_client.delete(f"/api/portfolios/{portfolio_id}")
    assert resp.status_code == 204


def test_add_instrument(auth_client, sample_portfolio_data):
    create_resp = auth_client.post("/api/portfolios", json=sample_portfolio_data)
    portfolio_id = create_resp.json()["id"]
    resp = auth_client.post(f"/api/portfolios/{portfolio_id}/instruments", json={
        "name": "New Bond",
        "instrument_type": "treasury_bond",
        "currency": "USD",
        "principal_outstanding": 500000000,
        "coupon_rate": 0.04,
        "maturity_date": "2029-01-01",
        "issue_date": "2019-01-01",
    })
    assert resp.status_code == 201


def test_upload_json_portfolio(auth_client):
    import json
    portfolio_data = {
        "name": "Uploaded Portfolio",
        "instruments": [
            {
                "name": "Uploaded Bond",
                "instrument_type": "treasury_bond",
                "currency": "USD",
                "principal_outstanding": 1000000000,
                "coupon_rate": 0.05,
                "maturity_date": "2030-01-01",
                "issue_date": "2020-01-01",
            }
        ]
    }
    resp = auth_client.post(
        "/api/portfolios/upload",
        files={"file": ("portfolio.json", json.dumps(portfolio_data).encode(), "application/json")},
        data={"name": "Uploaded Portfolio", "description": "From file"},
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Uploaded Portfolio"


def test_portfolios_isolated_by_org(auth_client, sample_portfolio_data):
    auth_client.post("/api/portfolios", json=sample_portfolio_data)

    client2 = __import__("fastapi.testclient", fromlist=["TestClient"]).TestClient(auth_client.app)
    from app.database import get_db
    from tests.conftest import TestingSessionLocal
    def override2():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    auth_client.app.dependency_overrides[get_db] = override2

    resp2 = client2.post("/api/auth/register", json={
        "email": "other@example.com",
        "password": "securepass123",
        "name": "Other User",
        "org_name": "Other Org",
    })
    token2 = resp2.json()["access_token"]
    client2.headers["Authorization"] = f"Bearer {token2}"

    resp = client2.get("/api/portfolios")
    assert resp.json()["meta"]["total"] == 0

    from tests.conftest import override_get_db
    auth_client.app.dependency_overrides[get_db] = override_get_db
