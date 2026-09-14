"""Qubo business tax tests: rule matching, scan idempotency, review flow,
jurisdiction fallback, org isolation."""
from app.api.qubo_biz import BIZ_RULES, RULES_VERSION, match_rules


def _register(client, email, org="Qubo Biz Org"):
    resp = client.post("/api/auth/register", json={
        "email": email,
        "password": "Test@Pass123",
        "name": "Qubo Biz",
        "org_name": org,
    })
    assert resp.status_code == 201, resp.text
    client.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    return client


def test_matcher_is_pure_and_conservative():
    assert [r["rule_id"] for r in match_rules("Payroll", "out")] == ["QBIZ-2026-wages"]
    assert match_rules("Payroll", "in") == []  # inflows are never findings
    assert match_rules("Revenue", "out") == []
    assert match_rules("Uncategorized", "out") == []
    assert match_rules("Anything", "out") == []
    assert set(BIZ_RULES) == {"Payroll", "Software", "Utilities", "Travel"}


def test_scan_finds_payroll_and_is_idempotent(auth_client):
    auth_client.post("/api/banking/seed")
    first = auth_client.post("/api/qubo/business/scan", json={"jurisdiction": "US"})
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["rules_version"] == RULES_VERSION
    assert body["created"] == 1  # only the posted payroll outflow qualifies
    assert body["generic_guidance"] is False

    second = auth_client.post("/api/qubo/business/scan", json={"jurisdiction": "US"})
    assert second.json()["created"] == 0
    assert second.json()["total"] == 1


def test_findings_carry_rule_refs_not_promises(auth_client):
    auth_client.post("/api/banking/seed")
    auth_client.post("/api/qubo/business/scan", json={"jurisdiction": "US"})
    findings = auth_client.get("/api/qubo/business/findings").json()["findings"]
    assert len(findings) == 1
    f = findings[0]
    assert f["rule_id"] == "QBIZ-2026-wages"
    assert f["tax_year"] == 2026
    assert f["amount_cents"] == 3_820_000  # the outflow that may qualify
    assert f["status"] == "new"
    assert "verify" in " ".join(f["requirements"]["sources"]).lower()


def test_review_flow(auth_client):
    auth_client.post("/api/banking/seed")
    auth_client.post("/api/qubo/business/scan", json={"jurisdiction": "US"})
    fid = auth_client.get("/api/qubo/business/findings").json()["findings"][0]["id"]

    accepted = auth_client.post(f"/api/qubo/business/findings/{fid}/review", json={"status": "accepted"})
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    overview = auth_client.get("/api/qubo/business/overview").json()
    assert overview["counts"]["accepted"] == 1
    assert overview["accepted_cents"] == 3_820_000
    assert "not promised savings" in overview["note"]

    bad = auth_client.post(f"/api/qubo/business/findings/{fid}/review", json={"status": "maybe"})
    assert bad.status_code == 422


def test_generic_jurisdiction_fallback(auth_client):
    auth_client.post("/api/banking/seed")
    resp = auth_client.post("/api/qubo/business/scan", json={"jurisdiction": "ZZ"})
    assert resp.status_code == 200
    assert resp.json()["generic_guidance"] is True
    findings = auth_client.get("/api/qubo/business/findings").json()["findings"]
    assert "Generic guidance only" in findings[0]["detail"]


def test_org_isolation_and_auth(client):
    assert client.get("/api/qubo/business/overview").status_code == 401
    org_a = _register(client, "qa@example-bank.com", org="Org QA")
    org_a.post("/api/banking/seed")
    org_a.post("/api/qubo/business/scan", json={"jurisdiction": "US"})
    fid = org_a.get("/api/qubo/business/findings").json()["findings"][0]["id"]

    del client.headers["Authorization"]
    org_b = _register(client, "qb@example-bank.com", org="Org QB")
    assert org_b.get("/api/qubo/business/findings").json()["findings"] == []
    assert org_b.post(f"/api/qubo/business/findings/{fid}/review", json={"status": "accepted"}).status_code == 404
