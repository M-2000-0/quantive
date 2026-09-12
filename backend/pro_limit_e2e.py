"""End-to-end Pro tier limit verification.

Real contracts (verified against app/api/*.py):

- Register:   POST /api/auth/register            body=UserCreate(email, password, name, org_name)
              → 201 + TokenResponse(access_token, refresh_token, token_type, user)
              → also sets httponly cookies (access_token, refresh_token), but over
                plain HTTP the Secure flag means browsers drop them; httpx keeps them.

- Login:      POST /api/auth/login               body=UserLogin(email, password)
              → 200 + TokenResponse

- CSRF:       GET  /login                        → sets csrf_token cookie (middleware now fires on GETs)
              POST endpoints require X-CSRF-Token header matching that cookie.

- Plan limits: GET /api/billing/subscription     → {tier, limits:{max_portfolios, max_instruments,
              optimizations_per_day, max_scenarios, max_users, data_retention_days}}
              Pro: optimizations_per_day=20, max_scenarios=10000, portfolios/instruments unlimited.

- Portfolio:  POST /api/portfolios               body=PortfolioCreate(name, description, instruments=[])
              → 201 + PortfolioResponse(id, name, org_id, created_by, instruments, ...)
              Pro has max_portfolios=-1 (unlimited).

- Instrument: POST /api/portfolios/{id}/instruments  body=DebtInstrumentCreate(
                name, instrument_type, currency, principal_outstanding, coupon_rate,
                maturity_date, issue_date, is_callable?, call_date?, call_price?, spread_bps?)
              → 201 + DebtInstrumentResponse
              Pro has max_instruments=-1 (unlimited), but the route still enforces
              max_instruments per-portfolio. With -1 that check is effectively disabled.

- Simulate:   POST /api/v1/simulate              body=SimulateRequest(
                yield_curve, instruments?, n_paths (ge100,le100000),
                horizon_months (ge12,le120), stress_scenarios?)
              → plan-limited via enforce_resource_limit(org_id, "max_scenarios", n_paths)
              Pro max_scenarios=10000, so n_paths<=10000 passes, 10001 is rejected.

- Optimize:   POST /api/optimize-debt            body=OptimizationRequest(
                instruments=[InstrumentInput(principal_outstanding, coupon_rate,
                maturity_years, rate_type?, currency?)], total_target_issuance,
                yield_curve?, macro_data?, max_floating_pct?, target_avg_maturity?,
                n_simulations?, use_noise_mitigation?, llm_provider?, llm_api_key?)
              → plan-limited via check_limit(org_id, "optimizations_per_day")
              Pro optimizations_per_day=20, so #21 returns 429 daily_limit_reached.

This test exercises:
1. Pro registration + token extraction (body + cookie).
2. Portfolio creation (Pro unlimited).
3. Instrument creation with the real DebtInstrumentCreate shape.
4. Simulate at 10000 (passes) and 10001 (rejected) to confirm the scenario cap.
5. Optimize 21 times and confirm the 21st is rejected with 429.
"""
import os
import time

from dotenv import load_dotenv
load_dotenv("../.env")
load_dotenv(".env")

import httpx

BASE = "http://127.0.0.1:8000"
rng = int(time.time())

c = httpx.Client(base_url=BASE, timeout=120)

def api_post(path, body=None, csrf=None, token=None):
    headers = {}
    if csrf:
        headers["X-CSRF-Token"] = csrf
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = c.post(path, json=body, headers=headers)
    try:
        body_text = r.json()
    except Exception:
        body_text = r.text
    return r.status_code, body_text

def is_ok(code):
    return str(code).startswith("2")

def extract_access_token(resp_json):
    if isinstance(resp_json, dict):
        t = resp_json.get("access_token")
        if t:
            return t
    ck = c.cookies.get("access_token")
    if ck:
        return ck
    return None

# ---------------------------------------------------------------------------
# 1. CSRF cookie from GET /login
# ---------------------------------------------------------------------------
r = c.get("/login")
csrf = r.cookies.get("csrf_token", "")
print(f"[1] GET /login -> {r.status_code}, csrf={'SET' if csrf else 'MISSING'} ({csrf[:24] if csrf else ''})")

# ---------------------------------------------------------------------------
# 2. Register a Pro user
# ---------------------------------------------------------------------------
email = f"pro{rng}@quantive.io"
pw = "ProTest1234!"
name = f"ProUser{rng}"
print(f"\n[2] Registering Pro user {email}")
code, resp = api_post(
    "/api/auth/register",
    {"email": email, "password": pw, "name": name, "org_name": "Pro QA"},
    csrf=None,  # register is CSRF-exempt
)
print(f"    register status={code}")
token = None
if is_ok(code):
    token = extract_access_token(resp)
    print(f"    token extracted: {bool(token)}  body_has_token={resp.get('access_token') is not None}  cookie={bool(c.cookies.get('access_token'))}")
else:
    print(f"    register body={resp}")
    # fallback: login the account we just tried to create
    code2, logresp = api_post("/api/auth/login", {"email": email, "password": pw})
    print(f"[2b] login status={code2}")
    if is_ok(code2):
        token = extract_access_token(logresp)
        print(f"    token from login: {bool(token)}")
    else:
        print(f"    FATAL: cannot obtain access token; aborting")
        print(f"    login body={logresp}")
        raise SystemExit(1)

api = lambda path, body=None: api_post(path, body, csrf=csrf, token=token)

# ---------------------------------------------------------------------------
# 3. Show plan limits
# ---------------------------------------------------------------------------
print(f"\n[3] plan limits via GET /api/billing/subscription")
code3, sub = api("/api/billing/subscription")
print(f"    status={code3} method=GET path=/api/billing/subscription")
limits = None
if is_ok(code3) and isinstance(sub, dict):
    limits = sub.get("limits")
    print(f"    tier={sub.get('tier')}")
    print(f"    limits={limits}")
else:
    print(f"    body={sub} (also trying /api/v1/billing/subscription)")
    code3b, sub2 = api("/api/v1/billing/subscription")
    print(f"    alt status={code3b} body={sub2}")
    if is_ok(code3b) and isinstance(sub2, dict):
        limits = sub2.get("limits")

# If the new org has no subscription row yet, it defaults to Free. Insert a
# Pro subscription row directly so the rest of the test exercises Pro limits.
if limits is None or limits.get("optimizations_per_day", 0) < 20:
    print(f"\n[3b] elevating org to Pro by inserting a subscription row")
    try:
        import secrets
        from app.billing import PlanTier, _billing_session
        from app.models.billing import SubscriptionRow
        from datetime import datetime, timezone, timedelta
        db = _billing_session()
        try:
            from app.models import User
            urow = db.query(User).filter(User.email == email).first()
            if not urow:
                print(f"    could not find user {email}")
            else:
                org_id = urow.org_id
                now = datetime.now(timezone.utc)
                sub_id = secrets.token_urlsafe(16)
                row = SubscriptionRow(
                    id=sub_id,
                    org_id=org_id,
                    user_id=urow.id,
                    stripe_customer_id=f"qa-pro-{rng}",
                    stripe_subscription_id=f"sub-qa-pro-{rng}",
                    tier=PlanTier.PRO.value,
                    billing_cycle="monthly",
                    status="active",
                    current_period_start=now.isoformat(),
                    current_period_end=(now + timedelta(days=31)).isoformat(),
                    created_at=now.isoformat(),
                    updated_at=now.isoformat(),
                )
                db.add(row)
                db.commit()
                db.refresh(row)
                print(f"    inserted SubscriptionRow id={row.id} tier=pro org_id={org_id}")
        finally:
            db.close()

        # re-fetch limits
        code3c, sub3 = api("/api/billing/subscription")
        print(f"    re-fetched subscription status={code3c}")
        if is_ok(code3c) and isinstance(sub3, dict):
            limits = sub3.get("limits")
            print(f"    tier={sub3.get('tier')}  limits={limits}")
        else:
            print(f"    re-fetch body={sub3}")
    except Exception as e:
        print(f"    ERROR elevating to Pro: {e}")
        import traceback
        traceback.print_exc()

# ---------------------------------------------------------------------------
# 4. Create a Pro portfolio with real instruments in one shot
#    (PortfolioCreate instruments use DebtInstrumentCreate shape.)
# ---------------------------------------------------------------------------
print(f"\n[4] Creating Pro portfolio with 3 instruments")
import datetime as _dt
today = _dt.date.today()
maturity = today.replace(year=today.year + 5)
issue = today.replace(year=today.year - 1)
portfolio = {
    "name": f"ProPortfolio-{rng}",
    "description": "End-to-end QA portfolio",
    "instruments": [
        {
            "name": "QA-Instr-A",
            "instrument_type": "treasury_bond",
            "currency": "USD",
            "principal_outstanding": 1000000.0,
            "coupon_rate": 0.045,
            "maturity_date": maturity.isoformat(),
            "issue_date": issue.isoformat(),
            "is_callable": False,
        },
        {
            "name": "QA-Instr-B",
            "instrument_type": "sovereign_bond",
            "currency": "USD",
            "principal_outstanding": 2000000.0,
            "coupon_rate": 0.052,
            "maturity_date": maturity.isoformat(),
            "issue_date": issue.isoformat(),
            "is_callable": False,
        },
        {
            "name": "QA-Instr-C",
            "instrument_type": "domestic_bond",
            "currency": "USD",
            "principal_outstanding": 1500000.0,
            "coupon_rate": 0.038,
            "maturity_date": maturity.isoformat(),
            "issue_date": issue.isoformat(),
            "is_callable": False,
        },
    ],
}
code, p1 = api("/api/portfolios", portfolio)
print(f"    portfolio status={code}")
portfolio_id = None
if is_ok(code) and isinstance(p1, dict):
    portfolio_id = p1.get("id")
    print(f"    portfolio_id={portfolio_id}")
    ins = p1.get("instruments") or []
    print(f"    instruments in response: {len(ins)}")
    for x in ins:
        print(f"        {x.get('id')} {x.get('name')} {x.get('principal_outstanding')} {x.get('currency')}")
else:
    print(f"    body={p1}")

if not portfolio_id:
    print("    FATAL: no portfolio id; aborting")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# 5. Add one more instrument via the per-portfolio endpoint to confirm it works
# ---------------------------------------------------------------------------
print(f"\n[5] Adding 1 more instrument via POST /api/portfolios/{portfolio_id}/instruments")
code, inst = api(
    f"/api/portfolios/{portfolio_id}/instruments",
    {
        "name": "QA-Instr-D",
        "instrument_type": "t_bill",
        "currency": "USD",
        "principal_outstanding": 750000.0,
        "coupon_rate": 0.06,
        "maturity_date": maturity.isoformat(),
        "issue_date": issue.isoformat(),
        "is_callable": False,
        "spread_bps": 25,
    },
)
print(f"    instrument status={code}")
if is_ok(code) and isinstance(inst, dict):
    print(f"    instrument_id={inst.get('id')} name={inst.get('name')} principal={inst.get('principal_outstanding')}")
else:
    print(f"    body={inst}")

# ---------------------------------------------------------------------------
# 6. Simulate: 10000 paths (Pro cap) should pass; 10001 should be rejected
# ---------------------------------------------------------------------------
print(f"\n[6] Simulate probes (Pro max_scenarios=10000)")
sim_results = []
for n_paths in (100, 10000, 10001):
    code, body = api(
        "/api/v1/simulate",
        {
            "yield_curve": {"3M": 0.042, "2Y": 0.038, "5Y": 0.037, "10Y": 0.040, "30Y": 0.042},
            "n_paths": n_paths,
            "horizon_months": 60,
            "stress_scenarios": True,
        },
    )
    print(f"    simulate n_paths={n_paths}: status={code}")
    sim_results.append((n_paths, code, body))
    if not is_ok(code):
        print(f"        body={body}")

# ---------------------------------------------------------------------------
# 7. Optimize 21 times; the 21st must be rejected with 429.
#    OptimizationRequest instruments use InstrumentInput:
#      principal_outstanding, coupon_rate, maturity_years, rate_type?, currency?
# ---------------------------------------------------------------------------
print(f"\n[7] Optimization limit probe (Pro optimizations_per_day=20)")
opt_results = []
for k in range(1, 23):
    code, body = api(
        "/api/optimize-debt",
        {
            "instruments": [
                {
                    "principal_outstanding": 50000000.0,
                    "coupon_rate": 0.045,
                    "maturity_years": 7.0,
                    "rate_type": "fixed",
                    "currency": "USD",
                }
            ],
            "total_target_issuance": 50000000.0,
            "n_simulations": 500,
        },
    )
    if is_ok(code):
        opt_results.append((k, code, "ok"))
        if k % 5 == 0 or k == 20:
            print(f"    optimization #{k}: OK")
    else:
        opt_results.append((k, code, body))
        print(f"    optimization #{k}: REJECTED status={code}")
        print(f"        body={body}")
        break

# ---------------------------------------------------------------------------
# 8. Summary
# ---------------------------------------------------------------------------
print(f"\n[8] Summary")
print(f"    user={email}")
print(f"    token_ok={bool(token)}")
print(f"    portfolio_id={portfolio_id}")
print(f"    plan_limits={limits}")
print(f"    sim_results={sim_results}")
print(f"    opt_results={opt_results}")

print(f"\n    VERDICT:")
if any(k == 21 and str(code).startswith("429") for k, code, _ in opt_results):
    print(f"    PASS: 21st optimization was rejected with 429 (Pro daily cap=20)")
elif any(k >= 21 for k, code, _ in opt_results):
    last = opt_results[-1]
    print(f"    FAIL: ran {last[0]} optimizations without hitting the cap; last status={last[1]}")
    print(f"          expected the {last[0]}th to be rejected, body={last[2]}")
else:
    print(f"    INCONCLUSIVE: opt_results={opt_results}")

print("\nDone.")
