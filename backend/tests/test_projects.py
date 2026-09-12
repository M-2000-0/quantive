"""Project workspaces + documents + project-scoped agent runs."""
import time


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


def test_project_lifecycle(auth_client):
    r = auth_client.post("/api/projects", json={"name": "Acme", "description": "d"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    g = auth_client.get(f"/api/projects/{pid}")
    assert g.status_code == 200
    assert g.json()["name"] == "Acme"
    assert g.json()["runs"] == []

    d = auth_client.post(f"/api/projects/{pid}/documents", json={
        "folder": "proposals", "title": "Q3 proposal", "body_text": "terms..."})
    assert d.status_code == 201, d.text

    bad = auth_client.post(f"/api/projects/{pid}/documents", json={
        "folder": "nope", "title": "valid title", "body_text": ""})
    assert bad.status_code == 400

    docs = auth_client.get(f"/api/projects/{pid}/documents?folder=proposals")
    assert len(docs.json()["documents"]) == 1

    g2 = auth_client.get(f"/api/projects/{pid}")
    assert g2.json()["documents_by_folder"] == {"proposals": 1}

    a = auth_client.patch(f"/api/projects/{pid}", json={"status": "archived"})
    assert a.json()["status"] == "archived"


def test_project_run_links_and_resumes(auth_client):
    pid = auth_client.post("/api/projects", json={"name": "Acme2"}).json()["id"]
    r = auth_client.post(f"/api/projects/{pid}/runs", json={
        "goal": "Summarize workspace",
        "steps": [{"tool": "project_summary", "args": {"project_id": pid}}],
    })
    assert r.status_code == 202, r.text
    done = _wait(auth_client, r.json()["id"])
    assert done["steps"][0]["output"]["ok"] is True
    assert done["steps"][0]["output"]["name"] == "Acme2"

    # Continuity: second run in the same project sees the first.
    r2 = auth_client.post(f"/api/projects/{pid}/runs", json={
        "goal": "Again",
        "steps": [{"tool": "project_summary", "args": {"project_id": pid}}],
    })
    done2 = _wait(auth_client, r2.json()["id"])
    assert done2["steps"][0]["output"]["runs"] == 2

    g = auth_client.get(f"/api/projects/{pid}")
    assert len(g.json()["runs"]) == 2


def test_project_isolation(client):
    from app.config import get_settings
    from app.security.csrf import generate_csrf_token

    s = get_settings()
    t = generate_csrf_token(s.SECRET_KEY)
    client.headers["X-CSRF-Token"] = t
    client.cookies.set("csrf_token", t)
    r1 = client.post("/api/auth/register", json={
        "email": "p1@x.y", "password": "Test@Pass123", "name": "P1", "org_name": "OrgP1"})
    tok1 = r1.json()["access_token"]
    r2 = client.post("/api/auth/register", json={
        "email": "p2@x.y", "password": "Test@Pass123", "name": "P2", "org_name": "OrgP2"})
    tok2 = r2.json()["access_token"]

    client.headers["Authorization"] = f"Bearer {tok1}"
    pid = client.post("/api/projects", json={"name": "Secret"}).json()["id"]

    client.headers["Authorization"] = f"Bearer {tok2}"
    assert client.get(f"/api/projects/{pid}").status_code == 404
    assert client.post(f"/api/projects/{pid}/runs",
                       json={"goal": "x", "steps": []}).status_code in (404, 422)
