"""End-to-end verification: Pro plan optimization limits.

Steps:
  1. Register a fresh user (real DB record, real JWT)
  2. Confirm unauthenticated optimization is rejected (401)
  3. Create a REAL Stripe test-mode one-time payment ($499) with fulfillment metadata
  4. Confirm the PaymentIntent with Stripe's test payment method (real money movement in test mode)
  5. Fulfill via the admin webhook simulator (fetches the real paid object from Stripe)
  6. Run 20 optimizations — all must succeed
  7. The 21st must be blocked with 429 + limit details

Secrets are read from the environment (.env); key material is never printed.
"""
import json
import os
import sys
import time

from dotenv import load_dotenv

# Load the same env files the server loads so Stripe calls authenticate
load_dotenv("../.env")
load_dotenv(".env")

import httpx

BASE = "http://127.0.0.1:8000"
SUFFIX = str(int(time.time()))
EMAIL = f"limitcheck-{SUFFIX}@quantive.com"
PASSWORD = "LimitCheck2026!"
NAME = "Limit Check"
ORG = f"Limit Check Org {SUFFIX}"

results = []


def check(label, ok, detail=""):
    results.append((label, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}: {label}" + (f" — {detail}" if detail else ""))


client = httpx.Client(timeout=120)

# ── 1. Register ──────────────────────────────────────────────────────
r = client.post(f"{BASE}/api/auth/register", json={
    "email": EMAIL, "password": PASSWORD, "name": NAME, "org_name": ORG,
})
check("register user", r.status_code == 201, f"status={r.status_code}")
tok = r.json().get("access_token", "")
auth = {"Authorization": f"Bearer {tok}"}
org_id = r.json().get("user", {}).get("org_id", "")
print(f"  user: {EMAIL}  org: {org_id}")

# ── 2. Unauthenticated must be rejected ─────────────────────────────
r = client.post(f"{BASE}/api/optimize-debt/quick", json={"use_live_data": False})
check("unauthenticated optimize rejected (401)", r.status_code == 401, f"status={r.status_code}")

# ── 3-5. Real Stripe payment → Pro fulfillment ──────────────────────
r = client.get(f"{BASE}/api/billing/mode", headers=auth)
mode = r.json()
print(f"  billing mode: {mode}")

r = client.post(f"{BASE}/api/billing/checkout", headers=auth, params={
    "tier": "pro", "billing_cycle": "monthly",
})
if r.status_code != 200:
    print("  checkout response:", r.status_code, r.text[:300])
    sys.exit(1)
co = r.json()
mode_name = co.get("mode", "")
check("checkout session created", mode_name == "stripe", f"mode={mode_name}")
session_id = co.get("session_id", "")

# Confirm the session's PaymentIntent with Stripe's test payment method.
import os
sk = os.environ.get("STRIPE_SECRET_KEY", "")
stripe = httpx.Client(base_url="https://api.stripe.com/v1", auth=(sk, ""), timeout=60)

# Payment-mode Checkout defers PaymentIntent creation until the customer
# submits on the hosted page, so pay it the way Stripe's own integration
# tests do: confirm the session's PaymentIntent via the test token.
sess = stripe.get(f"checkout/sessions/{session_id}").json()
pi_id = sess.get("payment_intent")
print(f"  session: {session_id[:24]}…  payment_intent on session: {bool(pi_id)}")

if pi_id:
    # Session already created the PI (payment-mode with automatic methods
    # sometimes creates it upfront) — confirm it directly.
    r2 = stripe.post(f"payment_intents/{pi_id}/confirm", data={
        "payment_method": "pm_card_visa",
        "return_url": "http://127.0.0.1:8000/billing",
    })
    print(f"  confirm status: {r2.status_code}")
    if r2.status_code != 200:
        print("  confirm error:", r2.text[:300])
else:
    # PI not created yet → the hosted page would collect payment. Use the
    # session's test-clock-free path: create a bare PaymentIntent with the
    # same metadata (exactly what a real one-time purchase reports).
    r2 = stripe.post("payment_intents", data={
        "amount": "49900",
        "currency": "usd",
        "payment_method": "pm_card_visa",
        "confirmation_method": "automatic",
        "confirm": "true",
        "return_url": "http://127.0.0.1:8000/billing",
        "metadata[org_id]": org_id,
        "metadata[tier]": "pro",
        "metadata[user_id]": EMAIL,
        "description": "Quantive Pro monthly (limit verification)",
    })
    print(f"  bare-PI create+confirm status: {r2.status_code}")
    if r2.status_code != 200:
        print("  PI error:", r2.text[:300])
        sys.exit(1)
    session_id = r2.json()["id"]

r = client.post(f"{BASE}/api/billing/webhook/simulate", headers=auth, json={"session_id": session_id})
sim = r.json()
print(f"  simulate: {sim}")
check("payment fulfilled → Pro subscription", sim.get("handled") is True, json.dumps(sim.get("result", sim))[:120])

r = client.get(f"{BASE}/api/billing/subscription", headers=auth)
sub = r.json()
plan = sub.get("tier") or sub.get("plan")
check("org is on Pro tier", plan == "pro", f"tier={plan}")

# ── 6. Run 20 optimizations (the Pro daily limit) ────────────────────
payload = {"use_live_data": False, "total_debt_billion": 10}
allowed = 0
first_usage = None
t0 = time.time()
for i in range(1, 21):
    r = client.post(f"{BASE}/api/optimize-debt/quick", headers=auth, json=payload)
    if r.status_code == 200:
        allowed += 1
        b = r.json().get("billing", {})
        if first_usage is None and b.get("usage"):
            first_usage = b["usage"]
    elif r.status_code == 429:
        print(f"  blocked early at #{i}: {r.json()}")
        break
    else:
        print(f"  unexpected status at #{i}: {r.status_code} {r.text[:200]}")
elapsed = time.time() - t0
check("20 optimizations allowed on Pro", allowed == 20, f"allowed={allowed}/20 in {elapsed:.0f}s, usage after 1st: {first_usage}")

# ── 7. The 21st must be blocked ──────────────────────────────────────
r = client.post(f"{BASE}/api/optimize-debt/quick", headers=auth, json=payload)
body = {}
try:
    body = r.json()
except Exception:
    pass
detail = body.get("detail", body)
check("21st optimization blocked (429)", r.status_code == 429, f"status={r.status_code}")
if isinstance(detail, dict):
    check("429 body carries limit details", detail.get("error") == "daily_limit_reached"
          and detail.get("limit") == 20 and detail.get("current") == 20,
          f"error={detail.get('error')} current={detail.get('current')}/{detail.get('limit')} plan={detail.get('plan')}")

# ── Summary ──────────────────────────────────────────────────────────
failed = [x for x in results if not x[1]]
print(f"\n{'=' * 60}\nRESULT: {len(results) - len(failed)}/{len(results)} checks passed")
if failed:
    print("FAILED:")
    for label, _, d in failed:
        print(f"  - {label}: {d}")
    sys.exit(1)
print("Pro plan limits are enforced end-to-end.")
