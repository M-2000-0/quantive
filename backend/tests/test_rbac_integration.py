"""
RBAC Middleware Integration Test
================================
Tests that the RBAC middleware correctly enforces permissions
on API endpoints.
"""

from fastapi.testclient import TestClient


def test_unauthenticated_get_portfolios(client):
    resp = client.get("/api/portfolios")
    assert resp.status_code == 401


def test_unauthenticated_post_portfolios(client):
    resp = client.post("/api/portfolios", json={"name": "test"})
    assert resp.status_code in (401, 403)


def test_health_bypasses_rbac(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_register_admin(client):
    resp = client.post("/api/auth/register", json={
        "email": "rbac_admin@test.com",
        "password": "AdminPass1!",
        "name": "RBAC Admin",
    })
    assert resp.status_code == 201
    assert "access_token" in resp.json()


def _get_admin_token(client):
    resp = client.post("/api/auth/register", json={
        "email": "rbac_admin2@test.com",
        "password": "AdminPass1!",
        "name": "RBAC Admin 2",
    })
    if resp.status_code == 201:
        return resp.json()["access_token"]
    resp = client.post("/api/auth/login", json={
        "email": "rbac_admin2@test.com",
        "password": "AdminPass1!",
    })
    return resp.json()["access_token"]


def test_admin_get_portfolios(client):
    token = _get_admin_token(client)
    resp = client.get("/api/portfolios", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code != 403


def test_admin_get_risk(client):
    token = _get_admin_token(client)
    resp = client.get("/api/risk", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 404)


def test_admin_get_market_data(client):
    token = _get_admin_token(client)
    resp = client.get("/api/market-data", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 404)


def test_admin_get_rbac_roles(client):
    token = _get_admin_token(client)
    resp = client.get("/api/rbac/roles", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_admin_get_rbac_status(client):
    token = _get_admin_token(client)
    resp = client.get("/api/rbac/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_rbac_status_shows_correct_role(client):
    token = _get_admin_token(client)
    resp = client.get("/api/rbac/status", headers={"Authorization": f"Bearer {token}"})
    body = resp.json()
    assert "current_user_role" in body
    assert body["current_user_role"] == "system_admin"
    assert isinstance(body.get("current_user_permissions"), list)


def test_rbac_roles_listing(client):
    token = _get_admin_token(client)
    resp = client.get("/api/rbac/roles", headers={"Authorization": f"Bearer {token}"})
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 6
    role_names = [r["name"] for r in body]
    assert "system_admin" in role_names
    assert "public_view" in role_names
    assert all("permissions" in r for r in body)


def test_rbac_permissions_endpoint(client):
    token = _get_admin_token(client)
    resp = client.get("/api/rbac/permissions", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "total_permissions" in body


def test_rbac_hierarchy(client):
    token = _get_admin_token(client)
    resp = client.get("/api/rbac/hierarchy", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    if "hierarchy" in body:
        assert len(body["hierarchy"]) == 6
        assert body["hierarchy"][0]["role"] == "system_admin"
        assert body["hierarchy"][5]["role"] == "public_view"


def test_rbac_permission_check_admin_has_portfolio_write(client):
    token = _get_admin_token(client)
    resp = client.get(
        "/api/rbac/check?role=system_admin&permission=portfolio:write",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body.get("has_permission") is True


def test_rbac_permission_check_public_view_no_portfolio_write(client):
    token = _get_admin_token(client)
    resp = client.get(
        "/api/rbac/check?role=public_view&permission=portfolio:write",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body.get("has_permission") is False


def test_rbac_permission_check_analyst_has_simulation(client):
    token = _get_admin_token(client)
    resp = client.get(
        "/api/rbac/check?role=analyst&permission=simulation:run",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body.get("has_permission") is True


def test_rbac_permission_check_auditor_no_optimization(client):
    token = _get_admin_token(client)
    resp = client.get(
        "/api/rbac/check?role=auditor&permission=optimization:execute",
        headers={"Authorization": f"Bearer {token}"},
    )
    body = resp.json()
    assert resp.status_code == 200
    assert body.get("has_permission") is False


def test_rbac_users_listing(client):
    token = _get_admin_token(client)
    resp = client.get("/api/rbac/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)


def test_403_response_format():
    from app.security.rbac_middleware import map_db_role, has_permission, match_route_permission

    rbac_role = map_db_role("viewer")
    required = match_route_permission("/api/portfolios", "POST")
    assert required == "portfolio:write"
    assert not has_permission(rbac_role, required)
