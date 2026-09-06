"""QA probes: yearly checkout session shape + duplicate-fulfillment idempotency."""
import os
import time

from dotenv import load_dotenv

load_dotenv("../.env")
load_dotenv(".env")

import httpx

BASE = "http://127.0.0.1:8000"
S = str(int(time.time()))
sk = os.environ.get("STRIPE_SECRET_KEY", "")
stripe = httpx.Client(base_url="https://api.stripe.com/v1", auth=(sk, ""), timeout=60)
c = httpx.Client(timeout=120)

# Fresh user via API (returns bearer token)
r = c.post(f"{BASE}/api/auth/register", json={
    "email": f"qa-yearly-{S}@quantive.com",
    "password": "QaYearly2026!",
    "name": "QA Yearly",
    "org_name": f"QA Yearly Org {S}",
})
tok = r.json()["access_token"]
org_id = r.json()["user"]["org_id"]
auth = {"Authorization": f"Bearer {tok}"}
print("registered:", r.status_code, "org:", org_id)

# ── Probe 1: yearly checkout session shape ──────────────────────────
r = c.post(f"{BASE}/api/billing/checkout", headers=auth, params={"tier": "pro", "billing_cycle": "yearly"})
co = r.json()
print("\n=== PROBE 1: yearly session ===")
print("checkout status:", r.status_code, "| app mode:", co.get("mode"))
sid = co.get("session_id", "")
sess = stripe.get(f"checkout/sessions/{sid}").json()
print("amount_total:", sess.get("amount_total"), "(expect 478800 = $4,788.00)")
print("currency:", sess.get("currency"))
print("stripe mode:", sess.get("mode"), "(expect subscription)")
li = stripe.get(f"checkout/sessions/{sid}/line_items").json()
for item in li.get("data", []):
    price = item.get("price", {})
    print("line item:", item.get("description"),
          "| unit_amount:", price.get("unit_amount"),
          "| interval:", (price.get("recurring") or {}).get("interval"))
print("metadata:", sess.get("metadata"))

# ── Probe 2: duplicate fulfillment idempotency ──────────────────────
# Pay a bare PaymentIntent, then simulate the webhook TWICE. The second
# replay must not create a second subscription or 500.
r = stripe.post("payment_intents", data={
    "amount": "49900", "currency": "usd",
    "payment_method": "pm_card_visa", "confirmation_method": "automatic",
    "confirm": "true", "return_url": f"{BASE}/billing",
    "metadata[org_id]": org_id, "metadata[tier]": "pro",
    "metadata[user_id]": f"qa-yearly-{S}@quantive.com",
    "description": "Quantive Pro monthly (QA idempotency probe)",
})
pi = r.json()
print("\n=== PROBE 2: duplicate fulfillment ===")
print("PI:", pi.get("id"), "status:", pi.get("status"), "amount_received:", pi.get("amount_received"))
r1 = c.post(f"{BASE}/api/billing/webhook/simulate", headers=auth, json={"session_id": pi["id"]})
print("simulate #1:", r1.status_code, r1.json())
r2 = c.post(f"{BASE}/api/billing/webhook/simulate", headers=auth, json={"session_id": pi["id"]})
print("simulate #2:", r2.status_code, r2.json())
r3 = c.get(f"{BASE}/api/billing/subscription", headers=auth)
sub = r3.json()
print("tier after double-fulfillment:", sub.get("tier"), "| status:", (sub.get("subscription") or {}).get("status"))
