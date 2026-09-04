"""PDF Report Generator — Export portfolio data as printable reports.

Generates HTML-based reports that can be printed to PDF via browser.
Includes portfolio summary, risk metrics, AI recommendations, and compliance status.
"""
from datetime import datetime, timezone
from typing import Optional


def generate_portfolio_report(
    instruments: list[dict],
    portfolio_name: str = "Portfolio",
    include_charts: bool = True,
    include_ai: bool = True,
    include_compliance: bool = True,
) -> str:
    """Generate an HTML report that can be printed to PDF."""
    
    total_principal = sum(float(i.get("principal_outstanding", i.get("principal", 0))) for i in instruments)
    
    # Currency breakdown
    currencies = {}
    for inst in instruments:
        cur = inst.get("currency", "USD")
        currencies[cur] = currencies.get(cur, 0) + float(inst.get("principal_outstanding", inst.get("principal", 0)))
    
    # Type breakdown
    types = {}
    for inst in instruments:
        t = inst.get("instrument_type", "unknown")
        types[t] = types.get(t, 0) + float(inst.get("principal_outstanding", inst.get("principal", 0)))
    
    # Maturity distribution
    now = datetime.now(timezone.utc)
    maturities = {"< 1Y": 0, "1-5Y": 0, "5-10Y": 0, "10-30Y": 0, "> 30Y": 0}
    for inst in instruments:
        principal = float(inst.get("principal_outstanding", inst.get("principal", 0)))
        mat_date = inst.get("maturity_date")
        if mat_date:
            try:
                if isinstance(mat_date, str):
                    mat_dt = datetime.strptime(mat_date[:10], "%Y-%m-%d")
                else:
                    mat_dt = mat_date
                years = (mat_dt - now).days / 365.25
                if years < 1: maturities["< 1Y"] += principal
                elif years < 5: maturities["1-5Y"] += principal
                elif years < 10: maturities["5-10Y"] += principal
                elif years < 30: maturities["10-30Y"] += principal
                else: maturities["> 30Y"] += principal
            except (ValueError, TypeError):
                pass

    # Weighted coupon
    weighted_coupon = sum(
        float(inst.get("coupon_rate", 0)) * float(inst.get("principal_outstanding", inst.get("principal", 0)))
        for inst in instruments
    ) / total_principal if total_principal > 0 else 0

    now_str = now.strftime("%B %d, %Y at %H:%M UTC")

    # Build instrument table rows
    instrument_rows = ""
    for i, inst in enumerate(instruments[:50], 1):
        principal = float(inst.get("principal_outstanding", inst.get("principal", 0)))
        pct = (principal / total_principal * 100) if total_principal > 0 else 0
        instrument_rows += f"""
        <tr>
            <td>{i}</td>
            <td>{inst.get('name', 'N/A')}</td>
            <td>{inst.get('currency', 'USD')}</td>
            <td style="text-align:right">${principal:,.0f}</td>
            <td style="text-align:right">{pct:.1f}%</td>
            <td style="text-align:right">{inst.get('coupon_rate', 0)}%</td>
            <td>{inst.get('maturity_date', 'N/A')[:10] if inst.get('maturity_date') else 'N/A'}</td>
        </tr>"""

    # Currency breakdown rows
    currency_rows = ""
    for cur, val in sorted(currencies.items(), key=lambda x: x[1], reverse=True):
        pct = (val / total_principal * 100) if total_principal > 0 else 0
        currency_rows += f'<tr><td>{cur}</td><td style="text-align:right">${val:,.0f}</td><td style="text-align:right">{pct:.1f}%</td></tr>'

    # Maturity rows
    maturity_rows = ""
    for label, val in maturities.items():
        pct = (val / total_principal * 100) if total_principal > 0 else 0
        bar_width = max(2, pct * 2)
        maturity_rows += f"""
        <tr>
            <td>{label}</td>
            <td style="text-align:right">${val:,.0f}</td>
            <td style="text-align:right">{pct:.1f}%</td>
            <td><div style="width:{bar_width}px;height:12px;background:#2563eb;border-radius:3px;"></div></td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{portfolio_name} Report — Quantive</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1a1a2e; background: #fff; padding: 40px; font-size: 12px; line-height: 1.5; }}
    .header {{ display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 3px solid #1a1a2e; padding-bottom: 16px; margin-bottom: 24px; }}
    .header h1 {{ font-size: 24px; font-weight: 700; color: #1a1a2e; }}
    .header .meta {{ text-align: right; color: #666; font-size: 11px; }}
    .section {{ margin-bottom: 24px; page-break-inside: avoid; }}
    .section h2 {{ font-size: 14px; font-weight: 700; color: #1a1a2e; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
    .kpi {{ border: 1px solid #ddd; border-radius: 8px; padding: 12px; text-align: center; }}
    .kpi .value {{ font-size: 20px; font-weight: 700; color: #1a1a2e; }}
    .kpi .label {{ font-size: 10px; color: #666; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
    th {{ text-align: left; padding: 6px 8px; background: #f5f5f5; border-bottom: 2px solid #ddd; font-weight: 600; text-transform: uppercase; font-size: 10px; letter-spacing: 0.05em; color: #555; }}
    td {{ padding: 6px 8px; border-bottom: 1px solid #eee; }}
    tr:hover td {{ background: #f9f9f9; }}
    .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #ddd; font-size: 10px; color: #999; display: flex; justify-content: space-between; }}
    .disclaimer {{ background: #fef3c7; border: 1px solid #f59e0b; border-radius: 6px; padding: 12px; margin-top: 24px; font-size: 10px; color: #92400e; }}
    @media print {{ body {{ padding: 20px; }} .no-print {{ display: none; }} }}
</style>
</head>
<body>
<div class="no-print" style="text-align:right;margin-bottom:16px;">
    <button onclick="window.print()" style="background:#2563eb;color:#fff;border:none;border-radius:6px;padding:8px 16px;cursor:pointer;font-size:12px;">Print / Save as PDF</button>
</div>

<div class="header">
    <div>
        <h1>{portfolio_name}</h1>
        <div style="color:#666;font-size:12px;">Sovereign Debt Portfolio Report</div>
    </div>
    <div class="meta">
        Generated: {now_str}<br>
        Quantive v1.0.0
    </div>
</div>

<div class="kpi-grid">
    <div class="kpi"><div class="value">${total_principal:,.0f}</div><div class="label">Total Principal</div></div>
    <div class="kpi"><div class="value">{len(instruments)}</div><div class="label">Instruments</div></div>
    <div class="kpi"><div class="value">{weighted_coupon:.2f}%</div><div class="label">Weighted Coupon</div></div>
    <div class="kpi"><div class="value">{len(currencies)}</div><div class="label">Currencies</div></div>
</div>

<div class="section">
    <h2>Instruments</h2>
    <table>
        <thead><tr><th>#</th><th>Name</th><th>Currency</th><th style="text-align:right">Principal</th><th style="text-align:right">Weight</th><th style="text-align:right">Coupon</th><th>Maturity</th></tr></thead>
        <tbody>{instrument_rows}</tbody>
    </table>
</div>

<div class="section" style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
    <div>
        <h2>Currency Breakdown</h2>
        <table>
            <thead><tr><th>Currency</th><th style="text-align:right">Amount</th><th style="text-align:right">Weight</th></tr></thead>
            <tbody>{currency_rows}</tbody>
        </table>
    </div>
    <div>
        <h2>Maturity Profile</h2>
        <table>
            <thead><tr><th>Tenor</th><th style="text-align:right">Amount</th><th style="text-align:right">Weight</th><th></th></tr></thead>
            <tbody>{maturity_rows}</tbody>
        </table>
    </div>
</div>

<div class="disclaimer">
    <strong>AUTOMATED ANALYTICAL OUTPUT:</strong> FOR DECISION-SUPPORT PURPOSES ONLY. DOES NOT CONSTITUTE FINANCIAL, LEGAL, OR BINDING SOVEREIGN ISSUANCE ADVICE. 
    Data sources: US Treasury, ECB Statistical Data Warehouse, World Bank Open Data. 
    Model assumptions and methodology available upon request.
</div>

<div class="footer">
    <div>Quantive — Sovereign Debt Intelligence Platform</div>
    <div>Report generated automatically. Verify all figures before decision-making.</div>
</div>
</body>
</html>"""

    return html


def generate_compliance_report(
    compliance_result: dict,
    portfolio_name: str = "Portfolio",
) -> str:
    """Generate a compliance report HTML."""
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    
    checks = compliance_result.get("checks", [])
    score = compliance_result.get("compliance_score", 0)
    passed = compliance_result.get("passed", 0)
    failed = compliance_result.get("failed", 0)
    total = compliance_result.get("total_checks", 0)
    
    check_rows = ""
    for c in checks:
        status_color = "#16a34a" if c["status"] == "pass" else "#dc2626"
        status_text = "PASS" if c["status"] == "pass" else "FAIL"
        check_rows += f"""
        <tr>
            <td><strong>{c['rule']}</strong></td>
            <td>{c['limit']}</td>
            <td>{c['actual']}</td>
            <td style="color:{status_color};font-weight:600;">{status_text}</td>
            <td>{c.get('recommendation', '—') or '—'}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Compliance Report — {portfolio_name}</title>
<style>
    * {{ margin:0;padding:0;box-sizing:border-box; }}
    body {{ font-family:-apple-system,sans-serif;color:#1a1a2e;background:#fff;padding:40px;font-size:12px;line-height:1.5; }}
    .header {{ border-bottom:3px solid #1a1a2e;padding-bottom:16px;margin-bottom:24px; }}
    .header h1 {{ font-size:24px;font-weight:700; }}
    .kpi {{ display:inline-block;border:1px solid #ddd;border-radius:8px;padding:16px 24px;text-align:center;margin-right:12px; }}
    .kpi .value {{ font-size:28px;font-weight:700; }}
    .kpi .label {{ font-size:10px;color:#666;text-transform:uppercase; }}
    table {{ width:100%;border-collapse:collapse;font-size:11px;margin-top:16px; }}
    th {{ text-align:left;padding:6px 8px;background:#f5f5f5;border-bottom:2px solid #ddd;font-weight:600;font-size:10px;text-transform:uppercase; }}
    td {{ padding:6px 8px;border-bottom:1px solid #eee; }}
    .disclaimer {{ background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:12px;margin-top:24px;font-size:10px;color:#92400e; }}
    .no-print {{ text-align:right;margin-bottom:16px; }}
    @media print {{ body {{ padding:20px; }} .no-print {{ display:none; }} }}
</style></head>
<body>
<div class="no-print"><button onclick="window.print()" style="background:#2563eb;color:#fff;border:none;border-radius:6px;padding:8px 16px;cursor:pointer;">Print / Save as PDF</button></div>
<div class="header">
    <h1>Regulatory Compliance Report</h1>
    <div style="color:#666;font-size:12px;">{portfolio_name} — {now_str}</div>
</div>
<div style="margin-bottom:24px;">
    <div class="kpi"><div class="value" style="color:{'#16a34a' if score >= 80 else '#dc2626'}">{score}%</div><div class="label">Compliance Score</div></div>
    <div class="kpi"><div class="value" style="color:#16a34a">{passed}</div><div class="label">Passed</div></div>
    <div class="kpi"><div class="value" style="color:#dc2626">{failed}</div><div class="label">Failed</div></div>
    <div class="kpi"><div class="value">{total}</div><div class="label">Total Checks</div></div>
</div>
<table>
    <thead><tr><th>Rule</th><th>Limit</th><th>Actual</th><th>Status</th><th>Recommendation</th></tr></thead>
    <tbody>{check_rows}</tbody>
</table>
<div class="disclaimer"><strong>AUTOMATED ANALYTICAL OUTPUT:</strong> FOR DECISION-SUPPORT PURPOSES ONLY. DOES NOT CONSTITUTE FINANCIAL, LEGAL, OR BINDING SOVEREIGN ISSUANCE ADVICE.</div>
</body></html>"""
    return html
