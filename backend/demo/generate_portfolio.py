import json
import random
import math

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF"]
TYPES = ["treasury_bond", "t_bill", "sovereign_bond", "concessional_loan", "commercial_loan",
         "floating_rate_note", "inflation_linked", "eurobond", "domestic_bond"]

instruments = []
random.seed(42)
instrument_id = 0

for i in range(72):
    instrument_id += 1
    currency = CURRENCIES[i % len(CURRENCIES)]
    inst_type = TYPES[i % len(TYPES)]
    year = 2024 + (i % 5)
    month = (i % 12) + 1
    day = min(28, (i % 28) + 1)

    maturity_year = year + 2 + (i % 15)
    maturity_date = f"{maturity_year}-{month:02d}-{day:02d}"
    issue_date = f"{year}-{month:02d}-{day:02d}"

    base_rate = 0.02 + (i % 20) * 0.005
    coupon = round(base_rate + random.uniform(-0.005, 0.01), 4)
    principal = round(random.uniform(10_000_000, 5_000_000_000), 2)
    spread = round(random.uniform(0, 300), 1)

    instruments.append({
        "name": f"Synthetic Instrument {instrument_id:03d} ({currency}/{inst_type.replace('_', ' ').title()})",
        "instrument_type": inst_type,
        "currency": currency,
        "principal_outstanding": principal,
        "coupon_rate": coupon,
        "maturity_date": maturity_date,
        "issue_date": issue_date,
        "is_callable": random.random() < 0.2,
        "call_date": f"{maturity_year - 3}-{month:02d}-{day:02d}" if random.random() < 0.2 else None,
        "call_price": round(random.uniform(100, 105), 2) if random.random() < 0.2 else None,
        "spread_bps": spread,
    })

portfolio = {
    "name": "Synthetic Sovereign Debt Portfolio",
    "description": "A synthetic portfolio of 72 government debt instruments across multiple currencies, types, and maturities. ALL DATA IS SYNTHETIC AND FOR DEMONSTRATION PURPOSES ONLY.",
    "instruments": instruments,
}

print(f"Generated {len(instruments)} instruments")
print(f"Total principal: ${sum(i['principal_outstanding'] for i in instruments):,.2f}")
print(f"Currencies: {set(i['currency'] for i in instruments)}")
print(f"Types: {set(i['instrument_type'] for i in instruments)}")

with open("backend/demo/synthetic_portfolio.json", "w") as f:
    json.dump(portfolio, f, indent=2)

print("Written to backend/demo/synthetic_portfolio.json")
