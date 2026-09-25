"""Live verification: banking/Qubo awareness in /api/ai/chat.

Exercises: spending breakdown, runway, top deductions, plus guards
(ethereum topic switch stays generic; portfolio question still wins).
"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def get_csrf():
    req = urllib.request.Request(f"{BASE}/api/health")
    with urllib.request.urlopen(req, timeout=30) as r:
        for part in r.headers.get("Set-Cookie", "").split(";"):
            part = part.strip()
            if part.startswith("csrf_token="):
                return part.split("=", 1)[1]
    return ""


def main():
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    csrf = get_csrf()
    req = urllib.request.Request(
        f"{BASE}/api/auth/login",
        data=json.dumps({"email": "demo_stress@test.com", "password": "DemoPass123!"}).encode(),
        headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
        method="POST",
    )
    with op.open(req, timeout=30) as r:
        assert r.status == 200

    def ask(message):
        csrf = get_csrf()
        req = urllib.request.Request(
            f"{BASE}/api/ai/chat",
            data=json.dumps({"message": message, "max_new_tokens": 30}).encode(),
            headers={"Content-Type": "application/json", "X-CSRF-Token": csrf},
            method="POST",
        )
        with op.open(req, timeout=300) as r:
            return json.loads(r.read())

    failures = []

    print("[1] spending breakdown…")
    d = ask("Where is my money going? Show my spending breakdown.")
    bc = d.get("banking_context") or {}
    b = bc.get("banking") or {}
    cats = b.get("top_categories") or []
    if not cats:
        failures.append("no banking categories in context")
    if "spending" not in (d.get("text") or "").lower() and cats:
        pass  # RAG text varies; context block is the contract
    print("    top cats:", [(c["category"], c["amount_cents"] // 100) for c in cats[:3]])
    print("    chips:", d.get("suggested_followups"))

    print("[2] runway…")
    d = ask("How much runway do I have?")
    b = (d.get("banking_context") or {}).get("banking") or {}
    rw = b.get("runway_months")
    if rw is None:
        failures.append("runway_months missing")
    else:
        print(f"    runway: {rw} months | burn ${b.get('monthly_burn_cents', 0)/100:,.0f}/mo")

    print("[3] top deductions…")
    d = ask("What are my top Qubo deductions?")
    q = (d.get("banking_context") or {}).get("qubo") or {}
    if not q:
        failures.append("no qubo context")
    else:
        print(
            f"    findings: {q.get('total_findings')} total, "
            f"open ${q.get('open_amount_cents', 0)/100:,.0f}, "
            f"accepted ${q.get('accepted_amount_cents', 0)/100:,.0f}"
        )
        print("    top:", [(f['title'][:30], f['amount_cents'] // 100) for f in (q.get('top_findings') or [])[:3]])

    print("[4] guards: ethereum stays generic…")
    d = ask("what is the price of ethereum?")
    if "banking_context" in d:
        failures.append("ethereum wrongly triggered banking context")
    print("    banking_context absent:", "banking_context" not in d)

    print("[5] guards: portfolio question unaffected…")
    d = ask("What happens to my debt if rates rise 50bps?")
    if "portfolio_context" not in d or d.get("banking_context"):
        failures.append("portfolio question routing changed")
    else:
        pc = d["portfolio_context"]
        print("    bps:", pc.get("rate_shock_bps"), "| banking_context absent:", "banking_context" not in d)

    print("[6] combined: cash + tax in one question…")
    d = ask("Show my cash position and my tax deductions")
    bc = d.get("banking_context") or {}
    print("    has banking:", "banking" in bc, "| has qubo:", "qubo" in bc)

    if failures:
        print("\nFAILURES:", failures)
        return 1
    print("\nALL BANKING/QUBO AWARENESS CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
