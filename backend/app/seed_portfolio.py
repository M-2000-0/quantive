"""
Seed realistic sovereign debt portfolio instruments for the admin user.
Run: cd backend && python -m app.seed_portfolio
"""

import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, engine
from app.models import Base, User, Portfolio, DebtInstrument, DebtInstrumentType

# Realistic Mexico sovereign debt portfolio
INSTRUMENTS = [
    # Short-term (1-2Y)
    {"name": "Bonos De Tesoreria 2026", "type": "t_bill", "currency": "MXN", "principal": 45_000_000_000, "coupon": 10.75, "maturity": "2026-12-18", "issue": "2025-12-18", "floating": False},
    {"name": "CETES 28-day", "type": "t_bill", "currency": "MXN", "principal": 32_000_000_000, "coupon": 10.50, "maturity": "2026-10-09", "issue": "2026-09-11", "floating": False},
    {"name": "Bonos De Tesoreria 2027", "type": "t_bill", "currency": "MXN", "principal": 38_000_000_000, "coupon": 10.25, "maturity": "2027-03-15", "issue": "2025-03-15", "floating": False},
    {"name": "FEGL 2027 Floating", "type": "floating_rate_note", "currency": "MXN", "principal": 28_000_000_000, "coupon": 11.20, "maturity": "2027-06-15", "issue": "2025-06-15", "floating": True},
    {"name": "UDI Bond 2027", "type": "inflation_linked", "currency": "MXN", "principal": 22_000_000_000, "coupon": 5.50, "maturity": "2027-09-20", "issue": "2025-09-20", "floating": False},

    # Medium-term (3-5Y)
    {"name": "MBonos 5Y 2028", "type": "sovereign_bond", "currency": "MXN", "principal": 55_000_000_000, "coupon": 9.75, "maturity": "2028-09-14", "issue": "2023-09-14", "floating": False},
    {"name": "MBonos 3Y 2027", "type": "sovereign_bond", "currency": "MXN", "principal": 42_000_000_000, "coupon": 10.00, "maturity": "2027-12-07", "issue": "2024-12-07", "floating": False},
    {"name": "UDIBONO 2028", "type": "inflation_linked", "currency": "MXN", "principal": 35_000_000_000, "coupon": 5.25, "maturity": "2028-06-15", "issue": "2023-06-15", "floating": False},
    {"name": "FEGL 2028 Floating", "type": "floating_rate_note", "currency": "MXN", "principal": 30_000_000_000, "coupon": 10.85, "maturity": "2028-03-20", "issue": "2024-03-20", "floating": True},
    {"name": "M-Bono 2029", "type": "sovereign_bond", "currency": "MXN", "principal": 48_000_000_000, "coupon": 9.50, "maturity": "2029-06-15", "issue": "2022-06-15", "floating": False},

    # Long-term (7-10Y)
    {"name": "M-Bono 10Y 2033", "type": "sovereign_bond", "currency": "MXN", "principal": 62_000_000_000, "coupon": 8.75, "maturity": "2033-09-14", "issue": "2023-09-14", "floating": False},
    {"name": "M-Bono 7Y 2031", "type": "sovereign_bond", "currency": "MXN", "principal": 50_000_000_000, "coupon": 9.00, "maturity": "2031-12-07", "issue": "2024-12-07", "floating": False},
    {"name": "UDIBONO 10Y 2033", "type": "inflation_linked", "currency": "MXN", "principal": 40_000_000_000, "coupon": 4.75, "maturity": "2033-06-15", "issue": "2023-06-15", "floating": False},
    {"name": "Global USD 2032", "type": "eurobond", "currency": "USD", "principal": 2_500_000_000, "coupon": 6.25, "maturity": "2032-01-21", "issue": "2022-01-21", "floating": False},
    {"name": "Global USD 2030", "type": "eurobond", "currency": "USD", "principal": 1_800_000_000, "coupon": 5.75, "maturity": "2030-07-15", "issue": "2020-07-15", "floating": False},

    # Ultra-long (15-30Y)
    {"name": "M-Bono 20Y 2044", "type": "sovereign_bond", "currency": "MXN", "principal": 38_000_000_000, "coupon": 8.25, "maturity": "2044-12-07", "issue": "2024-12-07", "floating": False},
    {"name": "Global USD 2047", "type": "eurobond", "currency": "USD", "principal": 1_500_000_000, "coupon": 6.85, "maturity": "2047-11-15", "issue": "2017-11-15", "floating": False},
    {"name": "M-Bono 30Y 2052", "type": "sovereign_bond", "currency": "MXN", "principal": 25_000_000_000, "coupon": 8.00, "maturity": "2052-03-15", "issue": "2022-03-15", "floating": False},

    # International
    {"name": "Global EUR 2031", "type": "eurobond", "currency": "EUR", "principal": 1_200_000_000, "coupon": 4.50, "maturity": "2031-04-21", "issue": "2021-04-21", "floating": False},
    {"name": "Global JPY 2030", "type": "eurobond", "currency": "JPY", "principal": 180_000_000_000, "coupon": 1.25, "maturity": "2030-09-20", "issue": "2020-09-20", "floating": False},
]

# Second portfolio: USD-denominated
USD_INSTRUMENTS = [
    {"name": "UST 2Y Treasury", "type": "treasury_bond", "currency": "USD", "principal": 500_000_000, "coupon": 4.15, "maturity": "2028-06-30", "issue": "2026-06-30", "floating": False},
    {"name": "UST 5Y Treasury", "type": "treasury_bond", "currency": "USD", "principal": 750_000_000, "coupon": 4.12, "maturity": "2031-06-30", "issue": "2026-06-30", "floating": False},
    {"name": "UST 10Y Treasury", "type": "treasury_bond", "currency": "USD", "principal": 1_000_000_000, "coupon": 4.30, "maturity": "2036-06-30", "issue": "2026-06-30", "floating": False},
    {"name": "UST 30Y Treasury", "type": "treasury_bond", "currency": "USD", "principal": 500_000_000, "coupon": 4.68, "maturity": "2056-06-30", "issue": "2026-06-30", "floating": False},
    {"name": "TIPS 10Y", "type": "inflation_linked", "currency": "USD", "principal": 300_000_000, "coupon": 2.00, "maturity": "2036-01-15", "issue": "2026-01-15", "floating": False},
    {"name": "UST 2Y Floating", "type": "floating_rate_note", "currency": "USD", "principal": 400_000_000, "coupon": 4.25, "maturity": "2028-03-15", "issue": "2026-03-15", "floating": True},
]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Find admin user
        admin = db.query(User).filter(User.email == "admin@quantive.com").first()
        if not admin:
            print("[ERROR] Admin user not found. Run seed_market_intelligence.py first or register a user.")
            return

        # Check if portfolios exist
        existing = db.query(Portfolio).filter(Portfolio.org_id == admin.org_id).count()
        if existing > 0:
            print(f"[SKIP] Organization already has {existing} portfolios")
            return

        # Create Mexico Sovereign Portfolio
        mx_portfolio = Portfolio(
            name="Mexico Sovereign Debt Portfolio",
            description="MXN-denominated sovereign debt instruments including Bonos, MBonos, UDIBONOS, CETES, and FEGL bonds across all maturities.",
            org_id=admin.org_id,
            created_by=admin.id,
        )
        db.add(mx_portfolio)
        db.flush()

        for inst_data in INSTRUMENTS:
            instrument = DebtInstrument(
                portfolio_id=mx_portfolio.id,
                name=inst_data["name"],
                instrument_type=DebtInstrumentType(inst_data["type"]),
                currency=inst_data["currency"],
                principal_outstanding=inst_data["principal"],
                coupon_rate=inst_data["coupon"],
                maturity_date=inst_data["maturity"],
                issue_date=inst_data["issue"],
                spread_bps=0,
                data_quality="verified",
            )
            db.add(instrument)

        # Create USD Treasury Portfolio
        usd_portfolio = Portfolio(
            name="USD Treasury Portfolio",
            description="USD-denominated US Treasury instruments including nominal bonds, TIPS, and floating-rate notes across all maturities.",
            org_id=admin.org_id,
            created_by=admin.id,
        )
        db.add(usd_portfolio)
        db.flush()

        for inst_data in USD_INSTRUMENTS:
            instrument = DebtInstrument(
                portfolio_id=usd_portfolio.id,
                name=inst_data["name"],
                instrument_type=DebtInstrumentType(inst_data["type"]),
                currency=inst_data["currency"],
                principal_outstanding=inst_data["principal"],
                coupon_rate=inst_data["coupon"],
                maturity_date=inst_data["maturity"],
                issue_date=inst_data["issue"],
                spread_bps=0,
                data_quality="verified",
            )
            db.add(instrument)

        db.commit()

        # Verify
        portfolios = db.query(Portfolio).filter(Portfolio.org_id == admin.org_id).count()
        instruments = db.query(DebtInstrument).join(Portfolio).filter(Portfolio.org_id == admin.org_id).count()
        print(f"\n[DONE] Created {portfolios} portfolios with {instruments} instruments")
        print(f"  - Mexico Sovereign Debt Portfolio: {len(INSTRUMENTS)} instruments")
        print(f"  - USD Treasury Portfolio: {len(USD_INSTRUMENTS)} instruments")
        total_mxn = sum(i["principal"] for i in INSTRUMENTS)
        total_usd = sum(i["principal"] for i in USD_INSTRUMENTS)
        print(f"  - Total MXN: ${total_mxn/1e9:.1f}B | Total USD: ${total_usd/1e9:.1f}B")

    finally:
        db.close()


if __name__ == "__main__":
    seed()
