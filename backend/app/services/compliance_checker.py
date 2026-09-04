"""Regulatory Compliance Auto-Check — Validate portfolios against fiscal rules.

Checks against:
- Maximum Debt-to-GDP ratio (MTDS ceiling)
- Maximum annual debt service ratio
- Minimum average maturity
- Maximum single-currency concentration
- Maximum floating-rate exposure
- Maximum short-term debt ratio
- Callable instrument limits
"""

from typing import Optional


# Default fiscal rules (configurable per jurisdiction)
DEFAULT_FISCAL_RULES = {
    "max_debt_to_gdp_pct": 60.0,
    "max_annual_debt_service_pct": 20.0,
    "min_avg_maturity_years": 5.0,
    "max_single_currency_pct": 70.0,
    "max_floating_rate_pct": 30.0,
    "max_short_term_pct": 25.0,
    "max_callable_pct": 15.0,
    "min_reserve_coverage_months": 6.0,
}


def check_compliance(
    instruments: list[dict],
    fiscal_rules: Optional[dict] = None,
    macro_data: Optional[dict] = None,
) -> dict:
    """Run full compliance check against fiscal rules.

    Args:
        instruments: Portfolio instruments
        fiscal_rules: Override default rules (optional)
        macro_data: GDP, debt-to-GDP, reserves, etc. (optional)
    """
    if not instruments:
        return {"compliant": True, "checks": [], "message": "No instruments to check"}

    rules = {**DEFAULT_FISCAL_RULES, **(fiscal_rules or {})}
    total_principal = sum(float(i.get("principal_outstanding", i.get("principal", 0))) for i in instruments)
    if total_principal == 0:
        return {"compliant": True, "checks": [], "message": "Zero principal"}

    checks = []

    # ── 1. Floating Rate Exposure ──
    floating = sum(
        float(i.get("principal_outstanding", i.get("principal", 0)))
        for i in instruments
        if i.get("instrument_type", i.get("type", "")) in ("floating_rate_note", "floating")
    )
    floating_pct = (floating / total_principal) * 100
    checks.append({
        "rule": "Floating Rate Exposure",
        "limit": f"≤{rules['max_floating_rate_pct']}%",
        "actual": f"{floating_pct:.1f}%",
        "status": "pass" if floating_pct <= rules["max_floating_rate_pct"] else "fail",
        "severity": "high" if floating_pct > rules["max_floating_rate_pct"] * 1.5 else "medium",
        "recommendation": f"Convert {floating_pct - rules['max_floating_rate_pct']:.1f}% of floating to fixed" if floating_pct > rules["max_floating_rate_pct"] else None,
    })

    # ── 2. Currency Concentration ──
    currency_values = {}
    for i in instruments:
        cur = i.get("currency", "USD")
        currency_values[cur] = currency_values.get(cur, 0) + float(i.get("principal_outstanding", i.get("principal", 0)))

    max_currency_pct = max((v / total_principal * 100 for v in currency_values.values()), default=0)
    max_currency = max(currency_values, key=currency_values.get) if currency_values else "N/A"
    checks.append({
        "rule": "Currency Concentration",
        "limit": f"≤{rules['max_single_currency_pct']}% in any single currency",
        "actual": f"{max_currency_pct:.1f}% in {max_currency}",
        "status": "pass" if max_currency_pct <= rules["max_single_currency_pct"] else "fail",
        "severity": "high" if max_currency_pct > rules["max_single_currency_pct"] * 1.2 else "medium",
        "recommendation": f"Diversify: reduce {max_currency} from {max_currency_pct:.1f}% to {rules['max_single_currency_pct']}%" if max_currency_pct > rules["max_single_currency_pct"] else None,
    })

    # ── 3. Maturity Profile ──
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    short_term = 0
    callable_total = 0
    maturity_years = []

    for i in instruments:
        principal = float(i.get("principal_outstanding", i.get("principal", 0)))
        # Short-term: < 1 year
        try:
            mat_date = datetime.strptime(i.get("maturity_date", ""), "%Y-%m-%d")
            years = (mat_date - now).days / 365.25
            maturity_years.append(years)
            if years < 1:
                short_term += principal
        except (ValueError, TypeError):
            pass

        if i.get("is_callable"):
            callable_total += principal

    short_term_pct = (short_term / total_principal) * 100
    callable_pct = (callable_total / total_principal) * 100
    avg_maturity = sum(m * (float(i.get("principal_outstanding", i.get("principal", 0))) / total_principal)
                      for i, m in zip(instruments, maturity_years)) if maturity_years else 0

    checks.append({
        "rule": "Short-Term Debt Ratio",
        "limit": f"≤{rules['max_short_term_pct']}%",
        "actual": f"{short_term_pct:.1f}%",
        "status": "pass" if short_term_pct <= rules["max_short_term_pct"] else "fail",
        "severity": "high" if short_term_pct > rules["max_short_term_pct"] * 1.5 else "medium",
        "recommendation": f"Extend maturities: {short_term_pct - rules['max_short_term_pct']:.1f}% of debt matures within 12 months" if short_term_pct > rules["max_short_term_pct"] else None,
    })

    checks.append({
        "rule": "Average Maturity",
        "limit": f"≥{rules['min_avg_maturity_years']} years",
        "actual": f"{avg_maturity:.1f} years",
        "status": "pass" if avg_maturity >= rules["min_avg_maturity_years"] else "fail",
        "severity": "medium" if avg_maturity < rules["min_avg_maturity_years"] else "low",
        "recommendation": f"Extend maturity: current {avg_maturity:.1f}Y below minimum {rules['min_avg_maturity_years']}Y" if avg_maturity < rules["min_avg_maturity_years"] else None,
    })

    checks.append({
        "rule": "Callable Instruments",
        "limit": f"≤{rules['max_callable_pct']}%",
        "actual": f"{callable_pct:.1f}%",
        "status": "pass" if callable_pct <= rules["max_callable_pct"] else "fail",
        "severity": "medium" if callable_pct > rules["max_callable_pct"] else "low",
        "recommendation": f"Refinance callable instruments: {callable_pct:.1f}% exceeds {rules['max_callable_pct']}% limit" if callable_pct > rules["max_callable_pct"] else None,
    })

    # ── 4. Debt-to-GDP (if macro data provided) ──
    if macro_data and macro_data.get("debt_to_gdp"):
        dtg = macro_data["debt_to_gdp"]
        checks.append({
            "rule": "Debt-to-GDP Ratio",
            "limit": f"≤{rules['max_debt_to_gdp_pct']}%",
            "actual": f"{dtg:.1f}%",
            "status": "pass" if dtg <= rules["max_debt_to_gdp_pct"] else "fail",
            "severity": "critical" if dtg > rules["max_debt_to_gdp_pct"] * 1.2 else "high",
            "recommendation": f"Debt-to-GDP at {dtg:.1f}% exceeds MTDS ceiling of {rules['max_debt_to_gdp_pct']}%" if dtg > rules["max_debt_to_gdp_pct"] else None,
        })

    # ── 5. Annual Debt Service (if macro data provided) ──
    if macro_data and macro_data.get("annual_debt_service_pct"):
        ads = macro_data["annual_debt_service_pct"]
        checks.append({
            "rule": "Annual Debt Service Ratio",
            "limit": f"≤{rules['max_annual_debt_service_pct']}%",
            "actual": f"{ads:.1f}%",
            "status": "pass" if ads <= rules["max_annual_debt_service_pct"] else "fail",
            "severity": "high" if ads > rules["max_annual_debt_service_pct"] * 1.3 else "medium",
            "recommendation": f"Debt service at {ads:.1f}% exceeds limit of {rules['max_annual_debt_service_pct']}%" if ads > rules["max_annual_debt_service_pct"] else None,
        })

    # Summary
    fail_count = sum(1 for c in checks if c["status"] == "fail")
    critical_count = sum(1 for c in checks if c["status"] == "fail" and c["severity"] == "critical")
    high_count = sum(1 for c in checks if c["status"] == "fail" and c["severity"] == "high")

    return {
        "compliant": fail_count == 0,
        "total_checks": len(checks),
        "passed": sum(1 for c in checks if c["status"] == "pass"),
        "failed": fail_count,
        "critical_violations": critical_count,
        "high_violations": high_count,
        "checks": checks,
        "compliance_score": round((sum(1 for c in checks if c["status"] == "pass") / len(checks)) * 100, 1) if checks else 100,
        "rules_applied": rules,
    }
