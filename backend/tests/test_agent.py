"""Agent substrate tests — registry, runner, approvals, org isolation.

The API executes runs in background threads (202 + poll), so tests poll
GET /runs/{id} until a terminal/non-queued state, mirroring real clients.
"""
import time


TERMINAL = {"completed", "failed", "cancelled"}


def _register(auth_client, portfolio_payload=None):
    if portfolio_payload is None:
        portfolio_payload = {"name": "Agent P", "description": "t"}
    r = auth_client.post("/api/portfolios", json=portfolio_payload)
    assert r.status_code in (200, 201), r.text
    return r.json().get("id") or r.json().get("portfolio", {}).get("id")


def _wait(auth_client, run_id, want=("completed",), timeout=15.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = auth_client.get(f"/api/agent/runs/{run_id}")
        assert r.status_code == 200, r.text
        last = r.json()
        if last["status"] in want:
            return last
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} never reached {want}: {last}")


def test_tools_listed(auth_client):
    r = auth_client.get("/api/agent/tools")
    assert r.status_code == 200, r.text
    names = {t["name"] for t in r.json()["tools"]}
    assert {"portfolio_summary", "risk_summary", "request_external_action"} <= names


def test_read_run_completes(auth_client):
    pid = _register(auth_client)
    r = auth_client.post("/api/agent/runs", json={
        "goal": "Summarize portfolio risk",
        "steps": [
            {"tool": "portfolio_summary", "args": {"portfolio_id": pid}},
            {"tool": "risk_summary", "args": {"portfolio_id": pid}},
        ],
    })
    assert r.status_code == 202, r.text
    body = _wait(auth_client, r.json()["id"], want=("completed",))
    assert all(s["status"] == "completed" for s in body["steps"])
    assert body["steps"][0]["output"]["ok"] is True


def test_unknown_tool_rejected(auth_client):
    r = auth_client.post("/api/agent/runs", json={
        "goal": "bad", "steps": [{"tool": "nope", "args": {}}],
    })
    assert r.status_code == 400


def test_approval_gate_and_approve(auth_client):
    pid = _register(auth_client)
    r = auth_client.post("/api/agent/runs", json={
        "goal": "External action needs human",
        "steps": [
            {"tool": "portfolio_summary", "args": {"portfolio_id": pid}},
            {"tool": "request_external_action",
             "args": {"action_type": "send_email", "payload": {"to": "x@y.z"}}},
        ],
    })
    assert r.status_code == 202, r.text
    run_id = r.json()["id"]
    body = _wait(auth_client, run_id, want=("waiting_approval",))
    assert body["steps"][0]["status"] == "completed"
    assert body["steps"][1]["status"] == "waiting_approval"

    a = auth_client.post(f"/api/agent/runs/{run_id}/steps/1/approve", json={"approved": True})
    assert a.status_code == 200, a.text
    done = _wait(auth_client, run_id, want=("completed",))
    assert done["steps"][1]["output"]["ok"] is True


def test_approval_reject_fails_run(auth_client):
    r = auth_client.post("/api/agent/runs", json={
        "goal": "reject me",
        "steps": [{"tool": "request_external_action", "args": {"action_type": "make_payment"}}],
    })
    run_id = r.json()["id"]
    _wait(auth_client, run_id, want=("waiting_approval",))
    d = auth_client.post(f"/api/agent/runs/{run_id}/steps/0/approve", json={"approved": False})
    assert d.status_code == 200
    assert d.json()["status"] == "failed"


def test_org_isolation(client):
    # Second org's run must not leak to first org's user.
    from app.security.csrf import generate_csrf_token
    from app.config import get_settings

    s = get_settings()
    t = generate_csrf_token(s.SECRET_KEY)
    client.headers["X-CSRF-Token"] = t
    client.cookies.set("csrf_token", t)
    r1 = client.post("/api/auth/register", json={
        "email": "a1@x.y", "password": "Test@Pass123", "name": "A1", "org_name": "OrgA"})
    tok1 = r1.json()["access_token"]
    r2 = client.post("/api/auth/register", json={
        "email": "b1@x.y", "password": "Test@Pass123", "name": "B1", "org_name": "OrgB"})
    tok2 = r2.json()["access_token"]

    client.headers["Authorization"] = f"Bearer {tok2}"
    rr = client.post("/api/agent/runs", json={
        "goal": "B run", "steps": [{"tool": "data_freshness", "args": {}}]})
    other_id = rr.json()["id"]

    client.headers["Authorization"] = f"Bearer {tok1}"
    g = client.get(f"/api/agent/runs/{other_id}")
    assert g.status_code == 404
