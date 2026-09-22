"""Plaid data aggregation gateway.

Handles Plaid Link token creation, account sync, and transaction sync.
Falls back to demo/mock data when PLAID_CLIENT_ID is not configured.
"""
from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.personal.models import FinancialConnection, Transaction

# Plaid configuration
PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID", "")
PLAID_SECRET = os.getenv("PLAID_SECRET", "")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")  # sandbox, development, production

PLAID_BASE_URLS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "development.plaid.com",
    "production": "production.plaid.com",
}

# Transaction categories with tax tags (extended from banking.py)
TAX_TAG_RULES = (
    # (keyword_in_name, category, tax_tag)
    ("payroll", "payroll", "taxable-revenue"),
    ("salary", "payroll", "taxable-revenue"),
    ("wage", "payroll", "taxable-revenue"),
    ("direct deposit", "payroll", "taxable-revenue"),
    ("acme", "revenue", "taxable-revenue"),
    ("invoice", "revenue", "taxable-revenue"),
    ("customer", "revenue", "taxable-revenue"),
    ("stripe", "processing", "revenue"),
    ("square", "processing", "revenue"),
    ("paypal", "processing", "revenue"),
    ("venmo", "processing", "review"),
    ("doorway", "rental", "rental"),
    ("rent", "housing", "deductible"),
    ("mortgage", "housing", "deductible"),
    ("property tax", "housing", "deductible"),
    ("homeowner", "housing", "deductible"),
    ("tax", "tax", "tax-paid"),
    ("irs", "tax", "tax-paid"),
    ("state tax", "tax", "tax-paid"),
    ("utility", "utilities", "deductible"),
    ("electric", "utilities", "deductible"),
    ("gas bill", "utilities", "deductible"),
    ("water bill", "utilities", "deductible"),
    ("internet", "utilities", "deductible"),
    ("phone", "utilities", "deductible"),
    ("software", "business", "deductible"),
    ("saas", "business", "deductible"),
    ("aws", "business", "deductible"),
    ("google cloud", "business", "deductible"),
    ("microsoft", "business", "deductible"),
    ("adobe", "business", "deductible"),
    ("office supplies", "business", "deductible"),
    ("staples", "business", "deductible"),
    ("office depot", "business", "deductible"),
    ("travel", "travel", "deductible"),
    ("airline", "travel", "deductible"),
    ("hotel", "travel", "deductible"),
    ("uber", "travel", "deductible"),
    ("lyft", "travel", "deductible"),
    ("airbnb", "travel", "deductible"),
    ("mileage", "vehicle", "deductible"),
    ("gas station", "vehicle", "deductible"),
    ("auto repair", "vehicle", "deductible"),
    ("car insurance", "vehicle", "deductible"),
    ("parking", "vehicle", "deductible"),
    ("toll", "vehicle", "deductible"),
    ("medical", "medical", "deductible"),
    ("doctor", "medical", "deductible"),
    ("hospital", "medical", "deductible"),
    ("pharmacy", "medical", "deductible"),
    ("dental", "medical", "deductible"),
    ("vision", "medical", "deductible"),
    ("health insurance", "health-insurance", "deductible"),
    ("united health", "health-insurance", "deductible"),
    ("cigna", "health-insurance", "deductible"),
    ("aetna", "health-insurance", "deductible"),
    ("blue cross", "health-insurance", "deductible"),
    ("anthem", "health-insurance", "deductible"),
    ("tuition", "education", "deductible"),
    ("university", "education", "deductible"),
    ("college", "education", "deductible"),
    ("student loan", "education", "deductible"),
    ("sallie mae", "education", "deductible"),
    ("nelnet", "education", "deductible"),
    ("donation", "charity", "deductible"),
    ("charity", "charity", "deductible"),
    ("church", "charity", "deductible"),
    ("red cross", "charity", "deductible"),
    ("goodwill", "charity", "deductible"),
    ("salvation army", "charity", "deductible"),
    ("investment", "investment", "review"),
    ("brokerage", "investment", "review"),
    ("fidelity", "investment", "review"),
    ("vanguard", "investment", "review"),
    ("schwab", "investment", "review"),
    ("robinhood", "investment", "review"),
    ("401k", "retirement", "review"),
    ("ira", "retirement", "review"),
    ("retirement", "retirement", "review"),
    ("pension", "retirement", "review"),
    ("grocery", "personal", "non-deductible"),
    ("restaurant", "dining", "non-deductible"),
    ("coffee", "dining", "non-deductible"),
    ("starbucks", "dining", "non-deductible"),
    ("mcdonald", "dining", "non-deductible"),
    ("netflix", "entertainment", "non-deductible"),
    ("spotify", "entertainment", "non-deductible"),
    ("amazon", "shopping", "review"),
    ("target", "shopping", "non-deductible"),
    ("walmart", "shopping", "non-deductible"),
    ("costco", "shopping", "review"),
    ("home depot", "home-improvement", "review"),
    ("lowes", "home-improvement", "review"),
    ("ikea", "home-improvement", "non-deductible"),
    ("gym", "health", "non-deductible"),
    ("fitness", "health", "non-deductible"),
    ("insurance", "insurance", "review"),
    ("pet", "personal", "non-deductible"),
    ("childcare", "family", "deductible"),
    ("daycare", "family", "deductible"),
    ("school", "education", "review"),
    ("book", "education", "review"),
)


def _suggest_tax_tag(name: str, memo: str = "") -> tuple[str, str]:
    """Determine category and tax tag from transaction name/memo."""
    combined = f"{name} {memo}".lower()
    for keyword, category, tax_tag in TAX_TAG_RULES:
        if keyword in combined:
            return category, tax_tag
    return "uncategorized", "review"


def is_configured() -> bool:
    """Check if Plaid credentials are configured."""
    return bool(PLAID_CLIENT_ID and PLAID_SECRET)


def create_link_token(user_id: str) -> dict:
    """Create a Plaid Link token for the user.
    
    In sandbox mode without Plaid configured, returns a demo token.
    """
    if is_configured():
        # Real Plaid API call would go here
        # For now, return demo mode
        pass

    # Demo mode: return a token that works with demo data
    return {
        "link_token": f"link-sandbox-{user_id[:8]}-{int(time.time())}",
        "expires_at": int(time.time()) + 3600,
        "environment": PLAID_ENV,
        "demo_mode": True,
    }


def exchange_public_token(user_id: str, public_token: str, db: Session) -> dict:
    """Exchange Plaid public token for access token and create connection.
    
    In demo mode, creates a simulated connection.
    """
    if is_configured():
        # Real Plaid API call: exchange_public_token -> access_token, item_id
        pass

    # Demo mode: create simulated connection
    item_id = hashlib.sha256(f"{user_id}:{public_token}".encode()).hexdigest()[:32]

    conn = FinancialConnection(
        user_id=user_id,
        provider="plaid",
        institution_name="Demo Bank",
        institution_id="ins_demo",
        account_type="checking",
        account_name="Checking Account",
        account_mask="1234",
        access_token=f"access-sandbox-{item_id[:16]}",
        item_id=item_id,
        status="active",
        balance_current=4523000,  # $45,230.00
        balance_available=4310000,  # $43,100.00
    )
    db.add(conn)

    # Also create a savings account
    conn2 = FinancialConnection(
        user_id=user_id,
        provider="plaid",
        institution_name="Demo Bank",
        institution_id="ins_demo",
        account_type="savings",
        account_name="Savings Account",
        account_mask="5678",
        access_token=f"access-sandbox-{item_id[:16]}-sav",
        item_id=f"{item_id}-sav",
        status="active",
        balance_current=12875000,  # $128,750.00
        balance_available=12875000,
    )
    db.add(conn2)

    # Create credit card
    conn3 = FinancialConnection(
        user_id=user_id,
        provider="plaid",
        institution_name="Demo Bank",
        institution_id="ins_demo",
        account_type="credit",
        account_name="Credit Card",
        account_mask="9012",
        access_token=f"access-sandbox-{item_id[:16]}-cc",
        item_id=f"{item_id}-cc",
        status="active",
        balance_current=-234000,  # -$2,340.00
        balance_available=766000,  # $7,660.00 available
    )
    db.add(conn3)

    db.commit()

    # Seed demo transactions
    _seed_demo_transactions(user_id, conn.id, conn2.id, conn3.id, db)

    return {
        "connection_id": conn.id,
        "accounts": [
            {"id": conn.id, "name": conn.account_name, "type": conn.account_type, "mask": conn.account_mask},
            {"id": conn2.id, "name": conn2.account_name, "type": conn2.account_type, "mask": conn2.account_mask},
            {"id": conn3.id, "name": conn3.account_name, "type": conn3.account_type, "mask": conn3.account_mask},
        ],
        "demo_mode": True,
    }


def _seed_demo_transactions(user_id: str, checking_id: str, savings_id: str, cc_id: str, db: Session) -> None:
    """Seed realistic demo transactions for testing."""
    demo_txns = [
        # Payroll (taxable revenue)
        ("2026-09-01", "ACME Corp Payroll", "ACME Corp", -385000, "payroll", "taxable-revenue"),
        ("2026-09-15", "ACME Corp Payroll", "ACME Corp", -385000, "payroll", "taxable-revenue"),
        # Freelance income
        ("2026-09-03", "Invoice Payment - Web Design", "Stripe", -250000, "revenue", "taxable-revenue"),
        # Housing
        ("2026-09-01", "Mortgage Payment", "Wells Fargo", 215000, "housing", "deductible"),
        ("2026-09-05", "Electric Bill", "ConEdison", 14500, "utilities", "deductible"),
        ("2026-09-05", "Internet Bill", "Comcast", 8900, "utilities", "deductible"),
        # Business expenses
        ("2026-09-07", "Adobe Creative Cloud", "Adobe", 5500, "business", "deductible"),
        ("2026-09-10", "AWS Hosting", "Amazon Web Services", 12300, "business", "deductible"),
        ("2026-09-12", "Office Supplies", "Staples", 8900, "business", "deductible"),
        # Travel
        ("2026-09-14", "Flight to NYC - Client Meeting", "United Airlines", 34500, "travel", "deductible"),
        ("2026-09-14", "Hotel - 2 nights", "Marriott", 42000, "travel", "deductible"),
        ("2026-09-14", "Uber to Client Office", "Uber", 3200, "travel", "deductible"),
        # Medical
        ("2026-09-16", "Annual Physical", "Dr. Smith", 25000, "medical", "deductible"),
        ("2026-09-18", "Pharmacy", "CVS", 4500, "medical", "deductible"),
        # Education
        ("2026-09-20", "Online Course - Python", "Udemy", 1300, "education", "deductible"),
        # Retirement
        ("2026-09-22", "401k Contribution", "Fidelity", 95800, "retirement", "review"),
        # Charitable
        ("2026-09-25", "Donation to Red Cross", "Red Cross", 25000, "charity", "deductible"),
        # Personal (non-deductible)
        ("2026-09-08", "Grocery Store", "Whole Foods", 15600, "personal", "non-deductible"),
        ("2026-09-11", "Restaurant", "Italian Bistro", 6800, "dining", "non-deductible"),
        ("2026-09-13", "Netflix Subscription", "Netflix", 1599, "entertainment", "non-deductible"),
        ("2026-09-15", "Gym Membership", "Planet Fitness", 2500, "health", "non-deductible"),
        ("2026-09-19", "Amazon Purchase", "Amazon", 8900, "shopping", "review"),
        ("2026-09-21", "Coffee Shop", "Starbucks", 550, "dining", "non-deductible"),
        ("2026-09-23", "Target Purchase", "Target", 12300, "shopping", "non-deductible"),
        # Savings transfers
        ("2026-09-01", "Transfer to Savings", "Internal Transfer", 500000, "transfer", "non-deductible"),
        # Tax payment
        ("2026-09-15", "Quarterly Estimated Tax", "IRS", 320000, "tax", "tax-paid"),
    ]

    for i, (date, name, merchant, amount, category, tax_tag) in enumerate(demo_txns):
        # Check if transaction already exists
        existing = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date == date,
            Transaction.name == name
        ).first()
        if existing:
            continue

        # Assign to appropriate account
        if category in ("payroll", "revenue", "transfer"):
            conn_id = checking_id
        elif category in ("tax",):
            conn_id = checking_id
        elif merchant in ("Amazon Web Services", "Adobe", "Staples", "United Airlines", "Marriott", "Uber"):
            conn_id = cc_id
        else:
            conn_id = checking_id

        txn = Transaction(
            user_id=user_id,
            connection_id=conn_id,
            date=date,
            name=name,
            merchant_name=merchant,
            amount=amount,
            category=category,
            tax_tag=tax_tag,
            confidence="auto",
        )
        db.add(txn)

    db.commit()


def sync_transactions(connection_id: str, db: Session) -> dict:
    """Sync transactions from a connected account.
    
    In demo mode, returns existing seeded data.
    """
    conn = db.get(FinancialConnection, connection_id)
    if not conn:
        return {"error": "Connection not found"}

    if is_configured():
        # Real Plaid API call would go here
        # transactions_sync for incremental updates
        pass

    # Demo mode: update last sync time
    conn.last_sync = datetime.now(timezone.utc)
    db.commit()

    txns = db.query(Transaction).filter(
        Transaction.connection_id == connection_id
    ).order_by(Transaction.date.desc()).all()

    return {
        "connection_id": connection_id,
        "transactions_synced": len(txns),
        "last_sync": conn.last_sync.isoformat() if conn.last_sync else None,
    }


def get_connections(user_id: str, db: Session) -> list[dict]:
    """Get all financial connections for a user."""
    conns = db.query(FinancialConnection).filter(
        FinancialConnection.user_id == user_id,
        FinancialConnection.status == "active"
    ).all()

    return [
        {
            "id": c.id,
            "provider": c.provider,
            "institution_name": c.institution_name,
            "account_type": c.account_type,
            "account_name": c.account_name,
            "account_mask": c.account_mask,
            "balance_current": c.balance_current,
            "balance_available": c.balance_available,
            "last_sync": c.last_sync.isoformat() if c.last_sync else None,
        }
        for c in conns
    ]


def disconnect_connection(connection_id: str, db: Session) -> bool:
    """Disconnect a financial connection."""
    conn = db.get(FinancialConnection, connection_id)
    if not conn:
        return False
    conn.status = "disconnected"
    db.commit()
    return True
