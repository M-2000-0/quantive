"""Seed two test users (patricio + chris) with enterprise-tier access."""
import sys, os, secrets
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal, engine
from app.models import User, Organization
from app.models.billing import SubscriptionRow
from app.security import hash_password
from sqlalchemy import text

# Ensure tables exist
from app.database import Base
import app.models  # noqa
Base.metadata.create_all(engine, checkfirst=True)

PASSWORD = "QuantumComp"
pw_hash = hash_password(PASSWORD)
now = datetime.now(timezone.utc)

users = [
    {"name": "Patricio", "email": "patricio@quantive.com", "org_name": "Patricio's Organization"},
    {"name": "Chris",    "email": "chris@quantive.com",    "org_name": "Chris's Organization"},
]

db = SessionLocal()
try:
    for u in users:
        existing = db.query(User).filter(User.email == u["email"]).first()
        if existing:
            print(f"  [SKIP] {u['email']} already exists (id={existing.id})")
            # Ensure enterprise subscription exists
            sub = db.query(SubscriptionRow).filter(
                SubscriptionRow.org_id == existing.org_id,
                SubscriptionRow.status == "active",
            ).first()
            if not sub:
                sub_id = secrets.token_urlsafe(16)
                db.add(SubscriptionRow(
                    id=sub_id, org_id=existing.org_id, user_id=existing.id,
                    tier="enterprise", billing_cycle="yearly",
                    stripe_customer_id="", stripe_subscription_id="",
                    status="active",
                    current_period_start=now.isoformat(),
                    current_period_end=(now + timedelta(days=365)).isoformat(),
                    created_at=now.isoformat(), updated_at=now.isoformat(),
                ))
                db.commit()
                print(f"  [FIX] Added enterprise subscription for {u['email']}")
            else:
                print(f"  [OK] {u['email']} already has active subscription (tier={sub.tier})")
            continue

        # Create org
        org = Organization(name=u["org_name"])
        db.add(org)
        db.flush()

        # Create user
        user = User(
            email=u["email"],
            password_hash=pw_hash,
            name=u["name"],
            role="admin",
            is_active=True,
            email_verified=True,
            org_id=org.id,
        )
        db.add(user)
        db.flush()

        # Create enterprise subscription
        sub_id = secrets.token_urlsafe(16)
        db.add(SubscriptionRow(
            id=sub_id, org_id=org.id, user_id=user.id,
            tier="enterprise", billing_cycle="yearly",
            stripe_customer_id="", stripe_subscription_id="",
            status="active",
            current_period_start=now.isoformat(),
            current_period_end=(now + timedelta(days=365)).isoformat(),
            created_at=now.isoformat(), updated_at=now.isoformat(),
        ))
        db.commit()
        print(f"  [CREATE] {u['email']} | password={PASSWORD} | role=admin | tier=enterprise | org={org.id}")

    print("\nDone. Users can now log in at /login")
    print("  patricio@quantive.com / QuantumComp")
    print("  chris@quantive.com    / QuantumComp")
finally:
    db.close()
