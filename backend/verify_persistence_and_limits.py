"""Verify: billing persistence tables + plan-limit enforcement + n8n bridge.

Run with the server up:  python verify_persistence_and_limits.py
"""
import json
import os
import sqlite3
import time

import httpx

BASE = "http://127.0.0.1:8000"
c = httpx.Client(timeout=60)
S = str(int(time.time()))
EMAIL = f"verify_pl_{S}@quantive.dev"
PASSWORD = "Str0ng!Passw0rd!"
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail else ""))


# ── 1. Billing tables exist in SQLite (persistence layer deployed) ──────
db = sqlite3.connect(os.path.join(os.path.dirname(__file__), "quantive.db"))
tables = {r[0] for r in db.execute(
    "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
check("billing_subscriptions table exists", "billing_subscriptions" in tables)
check("billing_usage table exists", "billing_usage" in tables)
cols = {r[1] for r in db.execute(
    "PRAGMA table_info(billing_subscriptions)").fetchall()}
check("subscription columns present",
      {"org_id", "tier", "status", "stripe_subscription_id"} <= cols)
db.close()

# ── 2. Register a fresh user (free tier) ────────────────────────────────
r = c.post(f"{BASE}/api/auth/register", json={
    "email": EMAIL, "password": PASSWORD, "name": "PL Verify",
    "org_name": "PL Verify Org",
})
check("register 201", r.status_code == 201, f"got {r.status_code} {r.text[:120]}")
token = r.json().get("access_token", "")

# CSRF cookie: GET a non-API page so the middleware sets the cookie in the
# response, which httpx stores in its cookie jar automatically.
c.get(f"{BASE}/login")
csrf = c.cookies.get("csrf_token", "")
# Also try fetching from a static page endpoint if /login redirects
if not csrf:
    c.get(f"{BASE}/")
    csrf = c.cookies.get("csrf_token", "")
H = {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}
print(f"(csrf token acquired: {'yes' if csrf else 'NO'})\n")

# For /api/* routes, CSRF only needs the header. But httpx doesn't auto-send
# cookies from its jar on POST unless we pass them explicitly, so we add the
# Cookie header manually to be safe (also satisfies the non-API path check).

def api_post(url, json_body, extra_headers=None):
    h = {**H, **(extra_headers or {})}
    if csrf:
        h.setdefault("Cookie", f"csrf_token={csrf}")
    return c.post(url, headers=h, json=json_body)

# ── 3. Plan limits: free = max 1 portfolio ─────────────────────────────
r1 = api_post(f"{BASE}/api/portfolios", {
    "name": "First", "description": "",
})
check("1st portfolio allowed (free)", r1.status_code == 201,
      f"got {r1.status_code} {r1.text[:120]}")
pid = r1.json().get("id") if r1.status_code == 201 else ""

r2 = api_post(f"{BASE}/api/portfolios", {
    "name": "Second", "description": "",
})
body = {}
try:
    detail = r2.json().get("detail", {})
    body = detail if isinstance(detail, dict) else {"raw": r2.text[:150]}
except Exception:
    body = {"raw": r2.text[:150]}
check("2nd portfolio blocked 403 plan_limit_reached",
      r2.status_code == 403 and body.get("error") == "plan_limit_reached",
      f"got {r2.status_code} err={body.get('error')} resource={body.get('resource')}")

# ── 4. Plan limits: free = max 5 instruments per portfolio ──────────────
last = None
for i in range(6):
    last = api_post(f"{BASE}/api/portfolios/{pid}/instruments", {
        "name": f"Bond {i}", "instrument_type": "treasury_bond", "currency": "USD",
        "principal_outstanding": 1_000_000, "coupon_rate": 4.0,
        "maturity_date": "2030-01-01", "issue_date": "2024-01-01",
        "is_callable": False, "spread_bps": 0,
    })
    if last.status_code != 201:
        break
detail = (last.json().get("detail", {}) if last.status_code != 201 else {})
detail = detail if isinstance(detail, dict) else {}
check("6th instrument blocked (free max 5)",
      last.status_code == 403 and detail.get("resource") == "max_instruments",
      f"got {last.status_code} err={detail.get('error')} body={last.text[:150]}")

# ── 5. Plan limits: free = max 100 scenarios on /api/v1/simulate ────────
r = api_post(f"{BASE}/api/v1/simulate", {
    "yield_curve": {"3M": 4.3, "2Y": 4.2, "5Y": 4.1, "10Y": 4.0, "30Y": 4.3},
    "n_paths": 200, "horizon_months": 12,
})
detail = r.json().get("detail", {}) if r.status_code != 200 else {}
detail = detail if isinstance(detail, dict) else {}
check("simulate n_paths=200 blocked on free (max 100)",
      r.status_code == 403 and detail.get("resource") == "max_scenarios",
      f"got {r.status_code} err={detail.get('error')}")

# Free tier allows max 100 scenarios/day. If we've already consumed the quota
# in a previous run, this will 403. That's fine — the important thing is the
# limit enforcement is wired (proven by the 200-block above).
r = api_post(f"{BASE}/api/v1/simulate", {
    "yield_curve": {"3M": 4.3, "2Y": 4.2, "5Y": 4.1, "10Y": 4.0, "30Y": 4.3},
    "n_paths": 10, "horizon_months": 12,
})
check("simulate rejects n_paths < 100 (size validation)",
      r.status_code == 422,
      f"got {r.status_code} {r.text[:120]}")

# ── 6. n8n bridge: external-run recorded and visible in history ────────
r = api_post(f"{BASE}/api/automation/webhooks/external-run", {
    "workflow": "platform-ai", "status": "success", "duration_ms": 1234,
    "summary": "verify bridge run",
    "actions": [{"action": "probe", "detail": "verify_persistence_and_limits"}],
})
check("external-run 201", r.status_code == 201,
      f"got {r.status_code} {r.text[:120]}")

r = c.get(f"{BASE}/api/automation/runs/recent?limit=10", headers=H)
if csrf:
    r = c.get(f"{BASE}/api/automation/runs/recent?limit=10", headers={**H, "Cookie": f"csrf_token={csrf}"})
runs = r.json() if r.status_code == 200 else []
if isinstance(runs, dict):
    runs = runs.get("runs", runs.get("items", []))
found = any((x.get("automation_key") == "n8n:platform-ai") for x in runs)
check("n8n run visible in /automation history", found, f"runs={len(runs)}")

# ── 7. Bridge rejects bad payload shape ────────────────────────────────
r = api_post(f"{BASE}/api/automation/webhooks/external-run", {"workflow": ""})
check("external-run rejects empty workflow 422", r.status_code == 422,
      f"got {r.status_code}")

# ── 8. Pro limits via persisted subscription (DB roundtrip) ────────────
from app.database import SessionLocal
from app.models import User, billing as billing_models

d = SessionLocal()
user = d.query(User).filter(User.email == EMAIL).first()
assert user and user.org_id, "test user not found"
d.add(billing_models.SubscriptionRow(
    id=f"verify-pro-{S}",
    org_id=user.org_id,
    user_id=user.id,
    tier="pro",
    billing_cycle="monthly",
    status="active",
    created_at="2026-01-01T00:00:00+00:00",
    updated_at="2026-01-01T00:00:00+00:00",
    current_period_start="2026-01-01T00:00:00+00:00",
    current_period_end="2027-01-01T00:00:00+00:00",
))
d.commit()
d.close()
r2b = api_post(f"{BASE}/api/portfolios", {
    "name": "Second-as-pro", "description": "",
})
check("2nd portfolio allowed once subscription row says pro",
      r2b.status_code == 201,
      f"got {r2b.status_code} — proves limit check reads the persisted subscription")

failed = [n for n, ok_, _ in results if not ok_]
print(f"\n{'ALL ' + str(len(results)) + ' CHECKS PASSED' if not failed else 'FAILED: ' + ', '.join(failed)}")
raise SystemExit(1 if failed else 0)
