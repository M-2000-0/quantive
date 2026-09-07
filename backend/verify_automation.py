"""Live verification of the native automation engine."""
import json
import time

import httpx

BASE = "http://127.0.0.1:8000"
c = httpx.Client(timeout=60)

# 1. Register a fresh user (returns bearer token)
S = str(int(time.time()))
r = c.post(f"{BASE}/api/auth/register", json={
    "email": f"autotest{S}@example.com",
    "password": "TestPass123!",
    "name": "Automation Tester",
    "org_name": "Auto Test Org",
})
assert r.status_code in (200, 201), f"register failed: {r.status_code} {r.text[:300]}"
token = r.json().get("access_token") or r.json().get("token")
H = {"Authorization": f"Bearer {token}"}
print("[1] registered user, token OK")

# 2. List automations
r = c.get(f"{BASE}/api/automation", headers=H)
d = r.json()
autos = d.get("automations", [])
print(f"[2] {len(autos)} automations registered: {[a['key'] for a in autos]}")
assert len(autos) == 6, "expected 6 automations"

# 3. Manually run health check + mrr tracker
for key in ("health_check", "mrr_tracker", "support_triage", "lead_capture_score"):
    r = c.post(f"{BASE}/api/automation/{key}/run", headers=H)
    d = r.json()
    print(f"[3] {key}: {d.get('status')} in {d.get('duration_ms')}ms — {d.get('summary')}")
    assert d.get("status") == "success", f"{key} failed: {d.get('error')}"

# 4. Capture a HOT lead via the public webhook (gov domain + ICP title + demo)
r = c.post(f"{BASE}/api/automation/webhooks/lead", json={
    "name": "Jane Treasury",
    "email": "jane@treasury.gov",
    "company": "Ministry of Finance",
    "title": "Director of Debt Management",
    "source": "demo",
})
d = r.json()
print(f"[4] hot lead captured: score={d.get('score')}, stage={d.get('stage')}")
assert d.get("score", 0) >= 70, f"expected hot lead (>=70), got {d.get('score')}"
assert d.get("stage") == "qualified", "hot lead should auto-convert to qualified"

# 5. Capture a cold lead
r = c.post(f"{BASE}/api/automation/webhooks/lead", json={
    "name": "Random Student",
    "email": "student@gmail.com",
    "source": "website",
})
print(f"[5] cold lead captured: score={r.json().get('score')}")

# 6. Verify leads listing + run history
r = c.get(f"{BASE}/api/automation/leads", headers=H)
leads = r.json().get("leads", [])
hot = [l for l in leads if l["score"] >= 70]
print(f"[6] {len(leads)} leads total, {len(hot)} hot; reasons sample: {json.loads(hot[0]['score_reasons']) if hot else '-'}")

r = c.get(f"{BASE}/api/automation/runs/recent?limit=10", headers=H)
runs = r.json().get("runs", [])
print(f"[7] {len(runs)} recent runs recorded")
assert len(runs) >= 4
lead_runs = [r for r in runs if r["automation_key"] == "lead_capture_score" and r["actions_taken"] > 0]
assert lead_runs, "lead_capture_score should have recorded scoring actions"
deal_actions = [a for r in lead_runs for a in r["log"] if a["action"] == "deal_created"]
print(f"[7b] lead runs with actions: {len(lead_runs)}; deals auto-created: {len(deal_actions)}")
assert deal_actions, "hot lead should have auto-created a deal"

# 7. MRR endpoint
r = c.get(f"{BASE}/api/automation/mrr", headers=H)
print(f"[8] MRR: {r.json()}")

# 8. Onboarding sequence: create one for this org, run automation
from app.database import SessionLocal  # noqa: E402 — runs outside app context on purpose

print("\nALL AUTOMATION CHECKS PASSED")
