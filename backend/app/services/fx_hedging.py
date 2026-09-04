"""FX Hedging Engine — Analyze currency exposure and recommend hedging.

Identifies unhedged foreign currency debt, quantifies FX risk,
and recommends optimal hedging instruments (forwards, options, swaps).
"""

from typing import Optional


def analyze_fx_exposure(
    instruments: list[dict],
    fx_rates: Optional[dict] = None,
    target_hedge_ratio: float = 0.70,
) -> dict:
    """Analyze FX exposure and recommend hedging strategies.

    Args:
        instruments: Portfolio instruments with currency and principal
        fx_rates: Current FX rates {"usd_mxn": 20.45, "usd_jpy": 156.2, ...}
        target_hedge_ratio: Target percentage of foreign currency to hedge (0-1)
    """
    if not instruments:
        return {"error": "No instruments provided"}

    # Default FX rates if not provided
    if not fx_rates:
        fx_rates = {"usd_mxn": 20.45, "usd_jpy": 156.25, "eur_usd": 1.0, "gbp_usd": 0.74}

    total_principal = sum(float(i.get("principal_outstanding", i.get("principal", 0))) for i in instruments)
    if total_principal == 0:
        return {"error": "Zero principal"}

    # Determine base currency (most common)
    currency_totals = {}
    for i in instruments:
        cur = i.get("currency", "USD")
        currency_totals[cur] = currency_totals.get(cur, 0) + float(i.get("principal_outstanding", i.get("principal", 0)))

    base_currency = max(currency_totals, key=currency_totals.get) if currency_totals else "USD"

    # Analyze each foreign currency
    exposures = []
    for currency, amount in currency_totals.items():
        if currency == base_currency:
            continue

        pct = (amount / total_principal) * 100

        # Get FX rate
        rate_key = f"{base_currency.lower()}_{currency.lower()}"
        reverse_key = f"{currency.lower()}_{base_currency.lower()}"
        rate = fx_rates.get(rate_key) or (1 / fx_rates[reverse_key] if reverse_key in fx_rates and fx_rates[reverse_key] else None)

        if rate:
            local_value = amount
            base_value = amount / rate
        else:
            base_value = amount
            rate = 1.0

        # Estimate FX sensitivity (1% move in FX = how much P&L impact)
        fx_sensitivity = base_value * 0.01

        # Recommend hedge amount
        unhedged_amount = amount * (1 - target_hedge_ratio)
        hedge_amount = amount * target_hedge_ratio

        # Choose hedging instrument based on amount and tenor
        if amount > 1e9:
            instrument = "cross-currency swap"
            reason = "Large notional适合 long-term hedging via swaps"
        elif amount > 100e6:
            instrument = "forward contract"
            reason = "Medium notional适合 forward locks for 6-12 months"
        else:
            instrument = "FX option"
            reason = "Smaller notional allows cost-efficient option protection"

        # Estimate hedge cost (simplified)
        if currency in ("JPY",):
            hedge_cost_bps = 15  # JPY hedging is cheap
        elif currency in ("EUR", "GBP"):
            hedge_cost_bps = 25
        else:  # EM currencies
            hedge_cost_bps = 50

        hedge_cost = hedge_amount * hedge_cost_bps / 10000

        exposures.append({
            "currency": currency,
            "principal": amount,
            "local_value": round(amount, 0),
            "base_value": round(base_value, 0),
            "percentage": round(pct, 2),
            "fx_rate": rate,
            "fx_sensitivity_1pct": round(fx_sensitivity, 0),
            "hedging": {
                "recommended_instrument": instrument,
                "reason": reason,
                "hedge_amount": round(hedge_amount, 0),
                "hedge_ratio": target_hedge_ratio,
                "estimated_annual_cost": round(hedge_cost, 0),
                "cost_bps": hedge_cost_bps,
            },
        })

    # Sort by exposure size
    exposures.sort(key=lambda x: x["percentage"], reverse=True)

    # Overall FX risk score
    total_foreign = sum(e["percentage"] for e in exposures)
    max_single = max((e["percentage"] for e in exposures), default=0)
    fx_risk_score = min(100, total_foreign * 0.8 + max_single * 0.5)

    # Total hedge cost
    total_hedge_cost = sum(e["hedging"]["estimated_annual_cost"] for e in exposures)

    return {
        "base_currency": base_currency,
        "total_portfolio": total_principal,
        "foreign_currency_exposure_pct": round(total_foreign, 2),
        "fx_risk_score": round(fx_risk_score, 1),
        "fx_risk_level": "high" if fx_risk_score > 60 else "medium" if fx_risk_score > 30 else "low",
        "exposures": exposures,
        "hedging_summary": {
            "total_hedge_amount": round(sum(e["hedging"]["hedge_amount"] for e in exposures), 0),
            "total_annual_hedge_cost": round(total_hedge_cost, 0),
            "cost_as_pct_of_portfolio": round(total_hedge_cost / total_principal * 100, 3) if total_principal else 0,
            "currencies_to_hedge": len(exposures),
            "target_hedge_ratio": target_hedge_ratio,
        },
        "recommendations": [
            f"Hedge {e['currency']} exposure ({e['percentage']:.1f}% of portfolio) via {e['hedging']['recommended_instrument']}"
            for e in exposures if e["percentage"] > 5
        ] or ["No significant unhedged FX exposure detected"],
    }
