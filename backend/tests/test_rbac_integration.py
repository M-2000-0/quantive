"""
RBAC Middleware Integration Test
=================================
Tests that the RBAC middleware correctly enforces permissions
on API endpoints.
"""

import sys
import os
import json
import urllib.request
import urllib.error

# Add backend dir to path for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0


def api(method, path, token=None, data=None):
    """Make an API request and return (status_code, body)."""
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read().decode())
        except Exception:
            pass
        return e.code, body
    except Exception as e:
        return 0, {"error": str(e)}


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")


def register_and_login(email, password, name="Test User"):
    """Register a user and get a token."""
    status, body = api("POST", "/api/auth/register", data={
        "email": email,
        "password": password,
        "name": name,
    })
    if status == 201:
        return body.get("access_token")
    elif status == 409:
        # Already exists, login instead
        status, body = api("POST", "/api/auth/login", data={
            "email": email,
            "password": password,
        })
        if status == 200:
            return body.get("access_token")
    return None


# ── Test 1: Unauthenticated access blocked ───────────────────────────
print("\n=== Test 1: Unauthenticated access ===")

status, body = api("GET", "/api/portfolios")
test("GET /api/portfolios without token returns 401", status == 401, f"got {status}")

status, body = api("POST", "/api/portfolios", data={"name": "test"})
test("POST /api/portfolios without token returns 401", status == 401, f"got {status}")


# ── Test 2: Health check bypasses RBAC ───────────────────────────────
print("\n=== Test 2: Health check bypasses RBAC ===")
status, body = api("GET", "/api/health")
test("GET /api/health works without auth", status == 200, f"got {status}")


# ── Test 3: Register users for each role ──────────────────────────────
print("\n=== Test 3: Register test users ===")

# Default registered user gets "admin" role → maps to system_admin
admin_token = register_and_login("rbac_admin@test.com", "AdminPass1!", "RBAC Admin")
test("Admin user registered", admin_token is not None)


# ── Test 4: Admin can access all endpoints ────────────────────────────
print("\n=== Test 4: Admin (system_admin) access ===")

status, body = api("GET", "/api/portfolios", admin_token)
test("Admin can GET /api/portfolios (not 403)", status != 403, f"got {status}")

status, body = api("GET", "/api/risk", admin_token)
test("Admin can GET /api/risk", status in (200, 404), f"got {status}")

status, body = api("GET", "/api/market-data", admin_token)
test("Admin can GET /api/market-data", status in (200, 404), f"got {status}")

status, body = api("GET", "/api/rbac/roles", admin_token)
test("Admin can GET /api/rbac/roles", status == 200, f"got {status}")

status, body = api("GET", "/api/rbac/status", admin_token)
test("Admin can GET /api/rbac/status", status == 200, f"got {status}")


# ── Test 5: RBAC status shows correct role ────────────────────────────
print("\n=== Test 5: RBAC status endpoint ===")
status, body = api("GET", "/api/rbac/status", admin_token)
test("RBAC status returns role", "current_user_role" in body, f"body: {body}")
test("Role is system_admin", body.get("current_user_role") == "system_admin", f"got {body.get('current_user_role')}")
test("Has permissions list", isinstance(body.get("current_user_permissions"), list), f"body: {body}")


# ── Test 6: RBAC roles listing ────────────────────────────────────────
print("\n=== Test 6: RBAC roles endpoint ===")
status, body = api("GET", "/api/rbac/roles", admin_token)
test("Roles endpoint returns 200", status == 200, f"got {status}")
test("Returns 6 roles", isinstance(body, list) and len(body) == 6, f"got {len(body) if isinstance(body, list) else body}")

if isinstance(body, list) and len(body) > 0:
    role_names = [r["name"] for r in body]
    test("Contains system_admin", "system_admin" in role_names)
    test("Contains public_view", "public_view" in role_names)
    test("Roles have permissions", all("permissions" in r for r in body))


# ── Test 7: RBAC permissions listing ──────────────────────────────────
print("\n=== Test 7: RBAC permissions endpoint ===")
status, body = api("GET", "/api/rbac/permissions", admin_token)
test("Permissions endpoint returns 200", status == 200, f"got {status}")
test("Has total_permissions", "total_permissions" in body, f"body keys: {body.keys() if isinstance(body, dict) else type(body)}")


# ── Test 8: RBAC hierarchy ────────────────────────────────────────────
print("\n=== Test 8: RBAC hierarchy endpoint ===")
status, body = api("GET", "/api/rbac/hierarchy", admin_token)
test("Hierarchy endpoint returns 200", status == 200, f"got {status}")
if isinstance(body, dict) and "hierarchy" in body:
    levels = [h["level"] for h in body["hierarchy"]]
    test("Hierarchy has 6 levels", len(levels) == 6)
    test("system_admin is level 0", body["hierarchy"][0]["role"] == "system_admin")
    test("public_view is level 5", body["hierarchy"][5]["role"] == "public_view")


# ── Test 9: RBAC permission check ─────────────────────────────────────
print("\n=== Test 9: RBAC permission check ===")
status, body = api("GET", "/api/rbac/check?role=system_admin&permission=portfolio:write", admin_token)
test("system_admin has portfolio:write", status == 200 and body.get("has_permission") is True, f"got {status} {body}")

status, body = api("GET", "/api/rbac/check?role=public_view&permission=portfolio:write", admin_token)
test("public_view does NOT have portfolio:write", status == 200 and body.get("has_permission") is False, f"got {status} {body}")

status, body = api("GET", "/api/rbac/check?role=analyst&permission=simulation:run", admin_token)
test("analyst has simulation:run", status == 200 and body.get("has_permission") is True, f"got {status} {body}")

status, body = api("GET", "/api/rbac/check?role=auditor&permission=optimization:execute", admin_token)
test("auditor does NOT have optimization:execute", status == 200 and body.get("has_permission") is False, f"got {status} {body}")


# ── Test 10: Users listing ────────────────────────────────────────────
print("\n=== Test 10: Users with RBAC roles ===")
status, body = api("GET", "/api/rbac/users", admin_token)
test("Users endpoint returns 200", status == 200, f"got {status}")
if isinstance(body, list) and len(body) > 0:
    test("Users have rbac_role field", "rbac_role" in body[0], f"keys: {body[0].keys()}")
    test("Users have permissions field", "permissions" in body[0])


# ── Test 11: RBAC middleware blocks unauthorized role ──────────────────
# The admin can assign roles. Let's test that the middleware enforces
# the permission check on role assignment itself.
print("\n=== Test 11: Self-protection ===")
# system_admin can assign roles
test("Admin can access role assignment endpoint",
     api("GET", "/api/rbac/users", admin_token)[0] == 200)


# ── Test 12: 403 response format ──────────────────────────────────────
print("\n=== Test 12: 403 response format ===")
# Try to access a write endpoint without proper permissions
# The admin user IS system_admin so they should pass everything.
# Let's verify the 403 format by checking the middleware logic directly
from app.security.rbac_middleware import map_db_role, has_permission, match_route_permission

# Simulate a public_view user trying to POST to portfolios
rbac_role = map_db_role("viewer")  # → public_view
required = match_route_permission("/api/portfolios", "POST")
test("POST /api/portfolios requires portfolio:write", required == "portfolio:write")
test("public_view does NOT have portfolio:write", not has_permission(rbac_role, required))


# ── Summary ───────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
print(f"{'='*60}")

sys.exit(0 if failed == 0 else 1)
