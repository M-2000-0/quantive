"""Quantive Banking API tests: ledger integrity, 0-fee enforcement,
idempotency, org isolation, KYB flow, AI CFO endpoints."""
import app.database as database_module

from app.models import User, UserRole


def _register(client, email, name="Test User", org="Test Org"):
    resp = client.post("/api/auth/register", json={
        "email": email,
        "password": "Test@Pass123",
        "name": name,
        "org_name": org,
    })
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def _set_role(email, role):
    # Uses the (test-overridden) SessionLocal so we hit the same
    # in-memory DB the TestClient sees.
    session = database_module.SessionLocal()
    try:
        user = session.query(User).filter(User.email == email).first()
        assert user is not None
        user.role = role
        session.commit()
    finally:
        session.close()


def _demote_to_viewer(email):
    _set_role(email, UserRole.VIEWER)


def test_seed_and_overview_match_landing_story(auth_client):
    seed = auth_client.post("/api/banking/seed")
    assert seed.status_code == 201, seed.text
    assert seed.json()["balance_cents"] == 18_429_000  # $184,290.00

    overview = auth_client.get("/api/banking/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["total_balance_cents"] == 18_429_000
    assert body["fees_paid_30d_cents"] == 0  # structurally zero
    assert body["moved_30d_cents"] > 0
    assert body["pending_count"] == 1  # Stripe payout still pending
    assert len(body["recent"]) == 5


def test_seed_is_one_time(auth_client):
    assert auth_client.post("/api/banking/seed").status_code == 201
    again = auth_client.post("/api/banking/seed")
    assert again.status_code == 409


def test_open_account_and_internal_transfer_is_double_entry(auth_client):
    auth_client.post("/api/banking/seed")
    reserve = auth_client.post("/api/banking/accounts", json={"name": "Reserve", "account_type": "reserve"})
    assert reserve.status_code == 201
    reserve_id = reserve.json()["id"]

    accounts = auth_client.get("/api/banking/accounts").json()["accounts"]
    operating = next(a for a in accounts if a["account_type"] == "operating")

    move = auth_client.post("/api/banking/transfers", json={
        "from_account_id": operating["id"],
        "to_account_id": reserve_id,
        "amount_cents": 2_000_000,  # $20,000
        "memo": "Yield buffer",
        "idempotency_key": "move-1",
    })
    assert move.status_code == 201, move.text
    assert move.json()["fee_cents"] == 0
    assert len(move.json()["transactions"]) == 2  # debit + credit legs

    accounts = auth_client.get("/api/banking/accounts").json()["accounts"]
    balances = {a["id"]: a["balance_cents"] for a in accounts}
    assert balances[operating["id"]] == 18_429_000 - 2_000_000
    assert balances[reserve_id] == 2_000_000


def test_transfer_idempotency_replays_without_double_spend(auth_client):
    auth_client.post("/api/banking/seed")
    operating = next(
        a for a in auth_client.get("/api/banking/accounts").json()["accounts"]
        if a["account_type"] == "operating"
    )
    payload = {
        "from_account_id": operating["id"],
        "counterparty": "Vendor Co",
        "amount_cents": 100_000,
        "idempotency_key": "ext-1",
    }
    first = auth_client.post("/api/banking/transfers", json=payload)
    assert first.status_code == 201
    second = auth_client.post("/api/banking/transfers", json=payload)
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    balance = next(
        a for a in auth_client.get("/api/banking/accounts").json()["accounts"]
        if a["id"] == operating["id"]
    )["balance_cents"]
    assert balance == 18_429_000 - 100_000  # charged exactly once


def test_transfer_validations(auth_client):
    auth_client.post("/api/banking/seed")
    operating = next(
        a for a in auth_client.get("/api/banking/accounts").json()["accounts"]
        if a["account_type"] == "operating"
    )
    # insufficient funds
    poor = auth_client.post("/api/banking/transfers", json={
        "from_account_id": operating["id"], "counterparty": "X",
        "amount_cents": 99_999_999_999,
    })
    assert poor.status_code == 422
    # external without counterparty
    missing = auth_client.post("/api/banking/transfers", json={
        "from_account_id": operating["id"], "amount_cents": 100,
    })
    assert missing.status_code == 422
    # self transfer
    selfie = auth_client.post("/api/banking/transfers", json={
        "from_account_id": operating["id"], "to_account_id": operating["id"],
        "amount_cents": 100,
    })
    assert selfie.status_code == 422
    # unknown account
    ghost = auth_client.post("/api/banking/transfers", json={
        "from_account_id": "00000000-0000-0000-0000-000000000000",
        "counterparty": "X", "amount_cents": 100,
    })
    assert ghost.status_code == 404


def test_org_isolation(client):
    org_a = _register(client, "a@example-bank.com", org="Org A")
    org_a.post("/api/banking/seed")
    acct_a = org_a.get("/api/banking/accounts").json()["accounts"][0]["id"]

    # wipe auth, register org B on the same client
    del client.headers["Authorization"]
    org_b = _register(client, "b@example-bank.com", org="Org B")
    assert org_b.get("/api/banking/accounts").json()["accounts"] == []
    # B cannot see or move A's money
    assert org_b.get(f"/api/banking/accounts/{acct_a}").status_code == 404
    assert org_b.post("/api/banking/transfers", json={
        "from_account_id": acct_a, "counterparty": "Thief", "amount_cents": 100,
    }).status_code == 404


def test_auto_categorization_and_manual_override(auth_client):
    auth_client.post("/api/banking/seed")
    operating = next(
        a for a in auth_client.get("/api/banking/accounts").json()["accounts"]
        if a["account_type"] == "operating"
    )
    txns = auth_client.get(f"/api/banking/accounts/{operating['id']}/transactions").json()["transactions"]
    payroll = next(t for t in txns if t["counterparty"] == "Payroll")
    assert payroll["category"] == "Payroll"
    assert payroll["tax_tag"] == "payroll"
    assert payroll["fee_cents"] == 0

    fixed = auth_client.post(f"/api/banking/transactions/{payroll['id']}/categorize", json={
        "category": "Contractors", "tax_tag": "deductible",
    })
    assert fixed.status_code == 200
    assert fixed.json()["category"] == "Contractors"


def test_insights_shape_and_disclaimer(auth_client):
    auth_client.post("/api/banking/seed")
    resp = auth_client.get("/api/banking/insights")
    assert resp.status_code == 200
    body = resp.json()
    assert "disclaimer" in body
    kinds = {c["id"] for c in body["insights"]}
    assert {"runway", "payroll", "tax"} <= kinds


def test_kyb_flow_and_admin_gate(client):
    admin = _register(client, "owner@example-bank.com", org="KYB Org")
    admin_token = client.headers["Authorization"]
    assert admin.get("/api/banking/profile").json()["kyb_status"] == "draft"

    put = admin.put("/api/banking/profile", json={
        "legal_name": "Acme Corp LLC", "entity_type": "llc",
        "country": "US", "industry": "Software", "tax_id_last4": "1234",
    })
    assert put.status_code == 200
    assert put.json()["kyb_status"] == "draft"

    # incomplete profile cannot submit (separate org — restore admin token after)
    del client.headers["Authorization"]
    rookie = _register(client, "rookie@example-bank.com", org="Rookie Org")
    assert rookie.post("/api/banking/profile/submit").status_code == 422
    client.headers["Authorization"] = admin_token

    submitted = admin.post("/api/banking/profile/submit")
    assert submitted.status_code == 200
    assert submitted.json()["kyb_status"] == "pending"

    # non-admin cannot decide
    _demote_to_viewer("owner@example-bank.com")
    assert admin.post("/api/banking/profile/verify").status_code == 403

    # fresh admin approves (role is read from DB per request, so
    # re-promote via DB then verify)
    _set_role("owner@example-bank.com", UserRole.ADMIN)
    decided = admin.post("/api/banking/profile/verify", params={"approved": True})
    assert decided.status_code == 200
    assert decided.json()["kyb_status"] == "verified"

    # verified profiles lock
    locked = admin.put("/api/banking/profile", json={"legal_name": "Changed"})
    assert locked.status_code == 422


def test_unauthenticated_is_rejected(client):
    assert client.get("/api/banking/overview").status_code == 401
    assert client.post("/api/banking/seed").status_code == 401
