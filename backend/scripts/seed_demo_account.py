"""Seed the demo account with realistic data so demos never show empty $0 dashboards.

Creates (idempotently) for demo_stress@test.com:
- an enterprise subscription (unlocks multi-portfolio/instrument limits)
- a sovereign debt portfolio: ~$1.6B across 10 instruments (USD/EUR/GBP/JPY,
  maturities 2027-2056) so the dashboard shows real totals, risk scores,
  maturity distribution and a near-term maturity alert
- three bank accounts (Operating / Reserve / Yield) with realistic balances
- ~90 posted+pending transactions over the last 90 days in categories the
  Qubo scanner rules match (Payroll / Software / Utilities / Travel) plus
  revenue inflows
- a verified BusinessProfile (KYB) for the org
- runs the Qubo business scan to generate tax findings (via HTTP once the
  server is up, or directly in-DB as a fallback)

Usage (from backend/):
    python scripts/seed_demo_account.py          # seed everything
    python scripts/seed_demo_account.py --scan   # also re-run Qubo scan via API

Run the backend BEFORE calling with --scan (the scan needs the HTTP API up);
without --scan the script seeds findings directly in the database.
"""
import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal  # noqa: E402
from app.models import User, Organization, Portfolio, DebtInstrument  # noqa: E402
from app.models.banking import BankAccount, BankTransaction, BusinessProfile  # noqa: E402
from app.models.qubo_tax import QuboFinding  # noqa: E402
from app.models.billing import SubscriptionRow  # noqa: E402

DEMO_EMAIL = "demo_stress@test.com"
TODAY = datetime.now(timezone.utc)


def _days_ago(days: int, hour: int = 10, minute: int = 0) -> datetime:
    d = TODAY - timedelta(days=days)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _uid() -> str:
    import uuid
    return str(uuid.uuid4())


# ── Portfolio ────────────────────────────────────────────────────────────────

INSTRUMENTS = [
    # name, type, ccy, principal (millions USD-scale numbers), coupon %, issue, maturity
    ("Republic Sovereign Bond 2027", "sovereign_bond", "USD", 85_000_000, 4.25, "2023-06-15", "2027-03-15"),
    ("Treasury Note 2028", "treasury_bond", "USD", 120_000_000, 3.90, "2024-02-01", "2028-09-01"),
    ("Infrastructure Concessional Loan", "concessional_loan", "USD", 150_000_000, 1.75, "2022-01-10", "2032-01-10"),
    ("Domestic Bond Series G", "domestic_bond", "USD", 95_000_000, 5.10, "2025-03-20", "2030-03-20"),
    ("Eurobond 2031", "eurobond", "USD", 200_000_000, 6.40, "2024-05-15", "2031-05-15"),
    ("Eurobond 2034 (EUR)", "eurobond", "EUR", 140_000_000, 5.80, "2024-11-01", "2034-11-01"),
    ("Floating Rate Note 2029", "floating_rate_note", "USD", 110_000_000, 4.60, "2025-01-30", "2029-01-30"),
    ("T-Bill Rolling Program", "t_bill", "USD", 60_000_000, 4.10, "2025-08-01", "2026-12-01"),
    ("Inflation-Linked Bond 2036", "inflation_linked", "USD", 130_000_000, 1.25, "2023-09-01", "2036-09-01"),
    ("Gilt-Style Long Bond 2056 (GBP)", "sovereign_bond", "GBP", 500_000_000, 4.75, "2026-01-15", "2056-01-15"),
]


def reset_banking(db, user) -> None:
    """Delete this org's seeded banking rows (idempotency escape hatch).

    Only removes rows this script owns: bank accounts cascade to their
    transactions; findings referencing those transactions are removed too.
    """
    org_id = user.org_id
    accts = db.query(BankAccount).filter(BankAccount.org_id == org_id).all()
    if not accts:
        return
    acct_ids = [a.id for a in accts]
    n_find = db.query(QuboFinding).filter(
        QuboFinding.org_id == org_id, QuboFinding.account_id.in_(acct_ids)).delete(
        synchronize_session=False)
    n_txn = db.query(BankTransaction).filter(
        BankTransaction.org_id == org_id, BankTransaction.account_id.in_(acct_ids)).delete(
        synchronize_session=False)
    n_acct = db.query(BankAccount).filter(
        BankAccount.org_id == org_id).delete(synchronize_session=False)
    db.commit()
    print(f"  [RESET] banking cleared: {n_acct} accounts, {n_txn} transactions, {n_find} findings")


def seed_portfolio(db, user) -> Portfolio | None:
    existing = db.query(Portfolio).filter(
        Portfolio.org_id == user.org_id, Portfolio.name == "Republic of Pacifica — Sovereign Debt Portfolio"
    ).first()
    if existing:
        print(f"  [SKIP] portfolio already exists (id={existing.id}, instruments={len(existing.instruments)})")
        return existing
    portfolio = Portfolio(
        name="Republic of Pacifica — Sovereign Debt Portfolio",
        description="Seeded demo portfolio: multi-currency sovereign debt ladder, 2026-2056 maturities",
        org_id=user.org_id,
        created_by=user.id,
    )
    db.add(portfolio)
    db.flush()
    for name, itype, ccy, principal, coupon, issue, maturity in INSTRUMENTS:
        db.add(DebtInstrument(
            portfolio_id=portfolio.id,
            name=name,
            instrument_type=itype,
            currency=ccy,
            principal_outstanding=float(principal),
            coupon_rate=float(coupon),
            issue_date=issue,
            maturity_date=maturity,
            is_callable=False,
            spread_bps=120.0,
        ))
    db.commit()
    db.refresh(portfolio)
    total = sum(float(i.principal_outstanding) for i in portfolio.instruments)
    print(f"  [CREATE] portfolio '{portfolio.name}' with {len(portfolio.instruments)} instruments, total ${total:,.0f}")
    return portfolio


# ── Banking ──────────────────────────────────────────────────────────────────

ACCOUNTS = [
    # name, type, currency (opening funding is posted as a transaction below)
    ("Operating", "operating", "USD"),
    ("Reserve", "reserve", "USD"),
    ("Yield", "yield", "USD"),
]

COUNTERPARTIES = {
    "Software": ["Microsoft 365", "Adobe Creative Cloud", "Datadog", "GitHub Enterprise",
                 "Snowflake", "Slack", "AWS", "Figma", "Notion", "JetBrains"],
    "Utilities": ["Pacific Power & Light", "CityWater Utilities", "MetroGas Co",
                  "FiberNet Telecom", "Waste Management Inc"],
    "Travel": ["United Airlines", "Delta Air Lines", "Hilton Hotels", "Marriott Bonvoy",
               "Hertz Rent-a-Car", "Amtrak", "Uber Business"],
    "Payroll": ["Payroll — Gusto", "ADP Payroll Run"],
    "Uncategorized": ["Office Depot", "WeWork Spaces", "Staples Business Credit"],
}

REVENUE = [
    # counterparty, memo, cents
    ("Acme Corp", "Invoice #2041 — consulting retainer", 124_000_000),
    ("Globex Financial", "Invoice #2042 — advisory services", 86_250_000),
    ("Stripe Payout", "Weekly card processing payout", 48_532_000),
    ("Initech LLC", "Invoice #2043 — platform license", 93_200_000),
    ("Oceanic Partners", "Invoice #2044 — data services", 61_575_000),
    ("Open Doorway", "Commercial rental payout", 32_000_000),
    ("Umbrella Health", "Invoice #2045 — analytics subscription", 44_890_000),
    ("Soylent Energy", "Invoice #2046 — Qubo scan engagement", 77_500_000),
]

MIXED_TAGS = [  # deliberate uncategorized spend so the demo shows the review flow
    ("Office Depot", "Supplies restock — printer paper", 8_450),
    ("WeWork Spaces", "Hot-desk day passes", 21_000),
    ("Courier Express", "Same-day document delivery", 5_525),
]


def seed_banking(db, user) -> bool:
    org_id = user.org_id
    if db.query(BankAccount).filter(BankAccount.org_id == org_id).first():
        print("  [SKIP] banking already seeded for this org")
        return False

    accounts: dict[str, BankAccount] = {}
    for name, atype, ccy in ACCOUNTS:
        acct = BankAccount(
            id=_uid(), org_id=org_id, owner_user_id=user.id,
            name=name, account_type=atype, currency=ccy,
            balance_cents=0, status="active",
            partner_ref=f"sandbox-{_uid().replace('-', '')[:12]}",
            created_at=_days_ago(95),
        )
        db.add(acct)
        accounts[name] = acct
    db.flush()

    def txn(acct, direction, txn_type, cents, counterparty, memo, when, status="posted"):
        category, tax_tag = ("Uncategorized", "review")
        text = f"{counterparty} {memo}".lower()
        for kw, cat, tag in (
            ("payroll", "Payroll", "payroll"), ("acme", "Revenue", "taxable-revenue"),
            ("invoice", "Revenue", "taxable-revenue"), ("stripe", "Revenue", "revenue"),
            ("doorway", "Rental income", "rental"), ("rent", "Rental income", "rental"),
            ("customer", "Revenue", "taxable-revenue"), ("tax", "Tax payment", "tax-paid"),
            ("utility", "Utilities", "deductible"), ("power", "Utilities", "deductible"),
            ("water", "Utilities", "deductible"), ("gas", "Utilities", "deductible"),
            ("telecom", "Utilities", "deductible"), ("waste", "Utilities", "deductible"),
            ("software", "Software", "deductible"),
            ("microsoft", "Software", "deductible"), ("adobe", "Software", "deductible"),
            ("datadog", "Software", "deductible"), ("github", "Software", "deductible"),
            ("snowflake", "Software", "deductible"), ("slack", "Software", "deductible"),
            ("aws", "Software", "deductible"), ("figma", "Software", "deductible"),
            ("notion", "Software", "deductible"), ("jetbrains", "Software", "deductible"),
            ("airlines", "Travel", "deductible"), ("air lines", "Travel", "deductible"),
            ("hilton", "Travel", "deductible"), ("marriott", "Travel", "deductible"),
            ("hertz", "Travel", "deductible"), ("amtrak", "Travel", "deductible"),
            ("uber", "Travel", "deductible"), ("travel", "Travel", "deductible"),
        ):
            if kw in text:
                category, tax_tag = cat, tag
                break
        db.add(BankTransaction(
            id=_uid(), org_id=org_id, account_id=acct.id,
            direction=direction, txn_type=txn_type, amount_cents=cents,
            fee_cents=0, counterparty=counterparty, memo=memo,
            category=category, tax_tag=tax_tag, status=status,
            idempotency_key=f"demo-seed-{len(demo_txn_keys)}",
            created_at=when,
        ))
        demo_txn_keys.append(True)
        if status == "posted":
            acct.balance_cents += cents if direction == "in" else -cents

    demo_txn_keys: list = []

    # Opening funding on operating (95 days ago)
    txn(accounts["Operating"], "in", "opening_balance", 2_000_000_000,
        "Quantive Partner Bank", "Initial treasury funding", _days_ago(94, 9))

    # Recurring semi-monthly payroll (3 runs, ~$82k each)
    for days in (82, 52, 22):
        txn(accounts["Operating"], "out", "payroll", 8_215_400,
            "Payroll — Gusto", "Semi-monthly payroll — 34 employees", _days_ago(days, 8))

    # Monthly HQ lease ("lease" keyword stays Uncategorized → shows in review flow)
    for days in (80, 50, 20):
        txn(accounts["Operating"], "out", "ach_out", 1_850_000,
            "Harbor Point Properties", "HQ lease — Harbor Point Suite 900", _days_ago(days, 7))

    # Software subscriptions — staggered over 90 days
    for i, (cp, memo, cents) in enumerate([
        ("Microsoft 365", "Monthly E5 licenses — 34 seats", 129_200),
        ("Adobe Creative Cloud", "Teams plan monthly — 10 seats", 89_990),
        ("Datadog", "Infrastructure monitoring monthly", 312_000),
        ("GitHub Enterprise", "Cloud seats monthly", 134_900),
        ("Snowflake", "Data warehouse usage monthly", 589_000),
        ("Slack", "Business+ monthly", 127_500),
        ("AWS", "Cloud compute monthly", 745_000),
        ("Figma", "Organization plan monthly", 91_200),
        ("Notion", "Team plan monthly", 48_000),
        ("JetBrains", "All Products Pack — 12 seats", 239_900),
    ]):
        txn(accounts["Operating"], "out", "ach_out", cents, cp, memo,
            _days_ago(88 - i * 6, 11))

    # Utilities — 3 months each
    for days in (75, 45, 15):
        txn(accounts["Operating"], "out", "ach_out", 148_320,
            "Pacific Power & Light", "HQ electricity", _days_ago(days, 9))
    for days in (74, 44, 14):
        txn(accounts["Operating"], "out", "ach_out", 42_100,
            "CityWater Utilities", "HQ water & sewer", _days_ago(days, 9))
    for days in (73, 43, 13):
        txn(accounts["Operating"], "out", "ach_out", 96_450,
            "MetroGas Co", "HQ heating gas", _days_ago(days, 10))
    for days in (70, 40, 10):
        txn(accounts["Operating"], "out", "ach_out", 189_900,
            "FiberNet Telecom", "Dedicated fiber 1Gbps", _days_ago(days, 10))

    # Travel — quarterly roadshow + monthly trips
    txn(accounts["Operating"], "out", "ach_out", 864_000,
        "United Airlines", "Q2 investor roadshow — 6 flights", _days_ago(66, 12))
    txn(accounts["Operating"], "out", "ach_out", 412_500,
        "Hilton Hotels", "Roadshow lodging — 6 nights", _days_ago(65, 12))
    txn(accounts["Operating"], "out", "ach_out", 128_900,
        "Delta Air Lines", "Regulator meetings — Washington DC", _days_ago(37, 12))
    txn(accounts["Operating"], "out", "ach_out", 96_400,
        "Marriott Bonvoy", "DC lodging — 3 nights", _days_ago(36, 12))
    txn(accounts["Operating"], "out", "ach_out", 74_200,
        "Hertz Rent-a-Car", "Site visit — Sacramento", _days_ago(28, 12))
    txn(accounts["Operating"], "out", "ach_out", 58_300,
        "Uber Business", "Ground transport monthly", _days_ago(18, 12))
    txn(accounts["Operating"], "out", "ach_out", 112_700,
        "Amtrak", "Regional rail — client visits", _days_ago(8, 12))

    # Revenue inflows (operating)
    for i, (cp, memo, cents) in enumerate(REVENUE):
        txn(accounts["Operating"], "in", "invoice", cents, cp, memo,
            _days_ago(87 - i * 9, 14))

    # One pending invoice (shows the pending state in UI)
    txn(accounts["Operating"], "in", "invoice", 65_500_000,
        "Northwind Traders", "Invoice #2047 — pending clearance", _days_ago(3, 15), status="pending")

    # Deliberate uncategorized outflows (review flow in Qubo/insights)
    for i, (cp, memo, cents) in enumerate(MIXED_TAGS):
        txn(accounts["Operating"], "out", "ach_out", cents, cp, memo,
            _days_ago(30 - i * 4, 16))

    # Reserve account: quarterly set-aside transfers in + tax payment out
    txn(accounts["Reserve"], "in", "transfer_in", 300_000_000,
        "Operating", "Quarterly tax set-aside sweep", _days_ago(60, 9))
    txn(accounts["Reserve"], "in", "transfer_in", 300_000_000,
        "Operating", "Quarterly tax set-aside sweep", _days_ago(30, 9))
    txn(accounts["Reserve"], "out", "payout", 190_000_000,
        "Dept of Revenue — Estimated Tax", "Q2 estimated tax payment", _days_ago(55, 9))

    # Yield account: monthly interest credits
    for days in (85, 55, 25):
        txn(accounts["Yield"], "in", "adjustment", 5_412_00,
            "Partner Bank Yield Pocket", "Monthly interest credit (~4.3% APY)", _days_ago(days, 6))

    # Internal transfers Operating -> Yield (sweep out and credit in)
    txn(accounts["Operating"], "out", "transfer_out", 150_000_000,
        "Yield", "Monthly idle-cash sweep to yield", _days_ago(33, 9))
    txn(accounts["Yield"], "in", "transfer_in", 150_000_000,
        "Operating", "Monthly idle-cash sweep to yield", _days_ago(33, 9))

    db.commit()
    totals = {n: accounts[n].balance_cents for n in accounts}
    total = sum(totals.values())
    print(f"  [CREATE] 3 accounts, ~60 transactions; balances: "
          + ", ".join(f"{n} ${c/100:,.0f}" for n, c in totals.items())
          + f" (total ${total/100:,.0f})")
    return True


def seed_profile(db, user) -> bool:
    org_id = user.org_id
    profile = db.query(BusinessProfile).filter(BusinessProfile.org_id == org_id).first()
    if profile:
        changed = False
        if profile.kyb_status != "verified":
            profile.kyb_status = "verified"
            profile.kyb_notes = "Demo org — auto-verified at seed time"
            profile.decided_at = TODAY
            changed = True
        if not profile.legal_name:
            profile.legal_name = "Republic of Pacifica Debt Management Office"
            profile.dba = "Pacifica DMO"
            profile.entity_type = "Sovereign Agency"
            profile.industry = "Public Finance"
            profile.tax_id_last4 = "0426"
            changed = True
        if changed:
            db.commit()
            print("  [FIX] BusinessProfile completed + verified")
        else:
            print("  [SKIP] BusinessProfile already verified")
        return False
    db.add(BusinessProfile(
        id=_uid(), org_id=org_id,
        legal_name="Republic of Pacifica Debt Management Office",
        dba="Pacifica DMO",
        entity_type="Sovereign Agency",
        country="US",
        industry="Public Finance",
        tax_id_last4="0426",
        kyb_status="verified",
        kyb_notes="Demo org — auto-verified at seed time",
        details={},
        submitted_at=_days_ago(90),
        decided_at=_days_ago(89),
        created_at=_days_ago(91),
    ))
    db.commit()
    print("  [CREATE] BusinessProfile (verified)")
    return True


def seed_subscription(db, user) -> bool:
    sub = db.query(SubscriptionRow).filter(
        SubscriptionRow.org_id == user.org_id,
        SubscriptionRow.status.in_(("active", "trialing")),
    ).first()
    if sub:
        print(f"  [OK] subscription exists (tier={sub.tier})")
        return False
    db.add(SubscriptionRow(
        id=_uid()[:32], org_id=user.org_id, user_id=user.id,
        tier="enterprise", billing_cycle="yearly",
        stripe_customer_id="", stripe_subscription_id="",
        status="active",
        current_period_start=TODAY.isoformat(),
        current_period_end=(TODAY + timedelta(days=365)).isoformat(),
        created_at=TODAY.isoformat(), updated_at=TODAY.isoformat(),
    ))
    db.commit()
    print("  [CREATE] enterprise subscription (unlocks portfolio/instrument limits)")
    return True


# ── Direct-DB Qubo findings (fallback when the API is not reachable) ─────────

from app.api.qubo_biz import BIZ_RULES  # noqa: E402


def seed_findings_direct(db, user) -> int:
    """Create Qubo findings from matching posted outflows, same rules as the scan API."""
    org_id = user.org_id
    if db.query(QuboFinding).filter(QuboFinding.org_id == org_id).first():
        print("  [SKIP] Qubo findings already exist")
        return 0
    txns = (
        db.query(BankTransaction)
        .filter(BankTransaction.org_id == org_id,
                BankTransaction.status == "posted",
                BankTransaction.direction == "out")
        .all()
    )
    created = 0
    for t in txns:
        rule = BIZ_RULES.get(t.category)
        if not rule:
            continue
        detail = rule["detail"]
        if rule.get("us_note"):
            detail += " " + rule["us_note"]
        db.add(QuboFinding(
            id=_uid(), org_id=org_id, account_id=t.account_id, txn_id=t.id,
            rule_id=rule["rule_id"], jurisdiction="US", tax_year=2026,
            category=t.category, title=rule["title"], detail=detail,
            amount_cents=t.amount_cents,
            requirements={"requirements": rule["requirements"], "docs": rule["docs"],
                          "sources": ["IRS publications for the current tax year — verify before acting"]},
            status="new", created_at=t.created_at,
        ))
        created += 1
    db.commit()
    print(f"  [CREATE] {created} Qubo tax findings from {len(txns)} posted outflows")
    return created


def main() -> int:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if not user:
            print(f"ERROR: {DEMO_EMAIL} not found. Register it first (see scripts/demo_stress_test.py).")
            return 1
        org = db.query(Organization).filter(Organization.id == user.org_id).first()
        print(f"Seeding demo data for {DEMO_EMAIL} (org={getattr(org, 'name', user.org_id)})")

        if "--reset-banking" in sys.argv:
            reset_banking(db, user)

        seed_subscription(db, user)
        seed_portfolio(db, user)
        seed_banking(db, user)
        seed_profile(db, user)

        scan_requested = "--scan" in sys.argv
        if scan_requested:
            try:
                import json
                import http.cookiejar
                import urllib.request
                base = os.environ.get("DEMO_API_BASE", "http://127.0.0.1:8000")
                jar = http.cookiejar.CookieJar()
                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

                def req(method, path, body=None):
                    data = json.dumps(body).encode() if body is not None else None
                    r = urllib.request.Request(base + path, data=data, method=method)
                    if body is not None:
                        r.add_header("Content-Type", "application/json")
                    for c in jar:
                        if c.name == "csrf_token":
                            r.add_header("X-CSRF-Token", c.value)
                    with opener.open(r, timeout=60) as resp:
                        return json.loads(resp.read().decode() or "{}")

                req("POST", "/api/auth/login", {"email": DEMO_EMAIL, "password": "DemoPass123!"})
                result = req("POST", "/api/qubo/business/scan", {"jurisdiction": "US", "tax_year": 2026})
                print(f"  [SCAN] via API: created={result.get('created')} total={result.get('total')}")
            except Exception as e:
                print(f"  [WARN] API scan failed ({type(e).__name__}: {e}) — seeding findings directly in DB")
                seed_findings_direct(db, user)
        else:
            seed_findings_direct(db, user)

        print("\nDone. Demo account ready:")
        print("  dashboard  → portfolio totals, risk scores, maturity ladder")
        print("  banking    → 3 accounts with balances + transaction history")
        print("  Qubo       → tax findings ready for review")
        print("  login: demo_stress@test.com / DemoPass123!")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
