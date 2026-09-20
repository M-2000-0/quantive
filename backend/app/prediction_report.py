"""Prediction Report Generator — Comprehensive PDF reports with charts.

Combines all prediction engines into a single professional PDF report:
- Monte Carlo simulation (VaR, CVaR, distributions)
- Early warning indicators (12 sovereign risk signals)
- Risk scoring (1-10 with factor breakdown)
- Yield curve forecast
- AI-generated analysis summary
- All charts embedded as base64 PNGs
"""

import base64
import io
import json
import math
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Optional


# ── Chart Generation ──────────────────────────────────────────────────

def _get_matplotlib():
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        return None


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt = _get_matplotlib()
    if plt:
        plt.close(fig)
    return f"data:image/png;base64,{b64}"


def generate_yield_forecast_chart(yield_curve: dict, forecast: dict) -> str:
    """Generate yield curve + forecast chart."""
    plt = _get_matplotlib()
    if not plt:
        return ""
    fig, ax = plt.subplots(figsize=(8, 4))

    # Current yield curve
    maturities = yield_curve.get("maturities", [])
    if maturities:
        labels = [m.get("label", "") for m in maturities]
        rates = [m.get("rate_pct", m.get("rate", 0)) for m in maturities]
        ax.plot(labels, rates, 'o-', color='#2563eb', linewidth=2, label='Current')

    # Forecast bands
    if forecast.get("central"):
        fc = forecast["central"]
        ax.plot(range(len(fc)), fc, '--', color='#dc2626', linewidth=1.5, label='Central Forecast')
    if forecast.get("optimistic"):
        fo = forecast["optimistic"]
        fp = forecast.get("pessimistic", [])
        x = range(len(fo))
        ax.fill_between(x, fo, fp if fp else [r * 1.05 for r in fo], alpha=0.15, color='#10b981', label='Forecast Range')

    ax.set_title('Yield Curve Forecast', fontsize=14, fontweight='bold')
    ax.set_ylabel('Yield (%)', fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_monte_carlo_chart(simulations: dict) -> str:
    """Generate Monte Carlo distribution chart."""
    plt = _get_matplotlib()
    if not plt:
        return ""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    # Distribution histogram
    costs = simulations.get("costs", [])
    if costs:
        ax1.hist(costs, bins=40, color='#6366f1', alpha=0.7, edgecolor='white')
        var_95 = simulations.get("var_95", 0)
        var_99 = simulations.get("var_99", 0)
        if var_95:
            ax1.axvline(var_95, color='#f59e0b', linestyle='--', linewidth=2, label=f'VaR 95%: ${var_95:,.0f}')
        if var_99:
            ax1.axvline(var_99, color='#dc2626', linestyle='--', linewidth=2, label=f'VaR 99%: ${var_99:,.0f}')
        ax1.set_title('Cost Distribution', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Annual Cost ($)')
        ax1.set_ylabel('Frequency')
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)

    # Percentile chart
    percentiles = simulations.get("percentiles", {})
    if percentiles:
        p_labels = list(percentiles.keys())
        p_values = [percentiles[k] for k in p_labels]
        colors = ['#10b981', '#2563eb', '#f59e0b', '#dc2626']
        ax2.barh(p_labels, p_values, color=colors[:len(p_labels)])
        ax2.set_title('Cost Percentiles', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Annual Cost ($)')
        for i, v in enumerate(p_values):
            ax2.text(v + max(p_values) * 0.01, i, f'${v:,.0f}', va='center', fontsize=9)
        ax2.grid(True, alpha=0.3, axis='x')

    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_risk_radar_chart(risk_factors: dict) -> str:
    """Generate risk radar chart."""
    plt = _get_matplotlib()
    if not plt:
        return ""
    categories = list(risk_factors.keys())
    values = [min(risk_factors[k], 1.0) for k in categories]
    values.append(values[0])
    categories.append(categories[0])

    angles = [i / (len(categories) - 1) * 2 * math.pi for i in range(len(categories) - 1)]
    angles.append(angles[0])

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles, values, 'o-', linewidth=2, color='#2563eb')
    ax.fill(angles, values, alpha=0.25, color='#2563eb')
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories[:-1], size=9)
    ax.set_ylim(0, 1)
    ax.set_title('Risk Profile', fontsize=14, fontweight='bold', y=1.08)
    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_early_warning_chart(ew_results: dict) -> str:
    """Generate early warning indicators bar chart."""
    plt = _get_matplotlib()
    if not plt:
        return ""
    indicators = ew_results.get("indicators", [])
    if not indicators:
        return ""

    labels = [ind.get("name", "")[:20] for ind in indicators]
    scores = [ind.get("score", 0) for ind in indicators]
    colors = ['#10b981' if s < 0.3 else '#f59e0b' if s < 0.7 else '#dc2626' for s in scores]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(labels, scores, color=colors)
    ax.set_xlim(0, 1)
    ax.set_title('Early Warning Indicators', fontsize=14, fontweight='bold')
    ax.set_xlabel('Risk Score (0=Safe, 1=Critical)')
    ax.axvline(0.3, color='#10b981', linestyle='--', alpha=0.5, label='Safe Threshold')
    ax.axvline(0.7, color='#dc2626', linestyle='--', alpha=0.5, label='Critical Threshold')
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis='x')
    fig.tight_layout()
    return _fig_to_base64(fig)


def generate_strategy_comparison_chart(strategies: list) -> str:
    """Generate strategy comparison bar chart."""
    plt = _get_matplotlib()
    if not plt:
        return ""
    if not strategies:
        return ""

    names = [s.get("name", "")[:20] for s in strategies]
    costs = [s.get("total_annual_cost", 0) for s in strategies]
    risks = [s.get("risk_score", 0) * 100 for s in strategies]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    colors = ['#6366f1', '#10b981', '#f59e0b', '#dc2626']
    ax1.bar(names, costs, color=colors[:len(names)])
    ax1.set_title('Annual Cost by Strategy', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Annual Cost ($)')
    for i, v in enumerate(costs):
        ax1.text(i, v + max(costs) * 0.01, f'${v:,.0f}', ha='center', fontsize=9)
    ax1.grid(True, alpha=0.3, axis='y')

    ax2.bar(names, risks, color=colors[:len(names)])
    ax2.set_title('Risk Score by Strategy', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Risk Score')
    ax2.set_ylim(0, 10)
    for i, v in enumerate(risks):
        ax2.text(i, v + 0.1, f'{v:.1f}', ha='center', fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')

    fig.tight_layout()
    return _fig_to_base64(fig)


# ── HTML Report Builder ──────────────────────────────────────────────

PREDICTION_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #1e293b; line-height: 1.5; padding: 40px; background: #fff; }}
    .header {{ background: linear-gradient(135deg, #1e40af, #7c3aed); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; }}
    .header h1 {{ font-size: 24px; margin: 0 0 8px; }}
    .header .subtitle {{ opacity: 0.85; font-size: 14px; }}
    .section {{ margin-bottom: 24px; page-break-inside: avoid; }}
    .section h2 {{ font-size: 18px; color: #1e40af; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 16px; }}
    .section h3 {{ font-size: 14px; color: #374151; margin: 12px 0 8px; }}
    .metrics {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }}
    .metric-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; min-width: 140px; flex: 1; }}
    .metric-card .label {{ font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }}
    .metric-card .value {{ font-size: 20px; font-weight: 700; color: #0f172a; }}
    .metric-card .sub {{ font-size: 11px; color: #94a3b8; margin-top: 2px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }}
    th {{ background: #1e40af; color: white; padding: 8px 10px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
    td {{ padding: 8px 10px; border-bottom: 1px solid #e2e8f0; }}
    tr:nth-child(even) {{ background: #f8fafc; }}
    .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 11px; color: #94a3b8; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
    .badge-green {{ background: #dcfce7; color: #166534; }}
    .badge-yellow {{ background: #fef9c3; color: #854d0e; }}
    .badge-red {{ background: #fee2e2; color: #991b1b; }}
    .badge-blue {{ background: #dbeafe; color: #1e40af; }}
    .chart {{ text-align: center; margin: 16px 0; }}
    .chart img {{ max-width: 100%; border: 1px solid #e2e8f0; border-radius: 8px; }}
    .ai-summary {{ background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 16px; margin: 16px 0; }}
    .ai-summary h3 {{ color: #0369a1; margin: 0 0 8px; font-size: 13px; }}
    .ai-summary p {{ font-size: 13px; color: #1e40af; line-height: 1.6; }}
</style>
</head>
<body>
{content}
<div class="footer">
    <p>Generated by Quantive — Government Financial Optimization Infrastructure</p>
    <p>{generated_at} | Report ID: {report_id} | Confidential</p>
</div>
</body>
</html>"""


def build_prediction_report(
    prediction_data: dict,
    charts: Optional[dict] = None,
) -> str:
    """Build the full HTML prediction report."""
    if charts is None:
        charts = {}
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report_id = f"RPT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    content = ""

    # ── Executive Summary
    content += f"""
    <div class="header">
        <h1>Sovereign Debt Prediction Report</h1>
        <div class="subtitle">Comprehensive Analysis — {generated_at}</div>
    </div>
    <div class="section">
        <h2>Executive Summary</h2>
        <div class="metrics">
            <div class="metric-card">
                <div class="label">Overall Risk Score</div>
                <div class="value" style="color: {prediction_data.get('risk_color', '#6b7280')}">{prediction_data.get('risk_score', 'N/A')}/10</div>
                <div class="sub">{prediction_data.get('risk_label', 'Unknown')}</div>
            </div>
            <div class="metric-card">
                <div class="label">Market Signal</div>
                <div class="value">{prediction_data.get('market_signal', 'Neutral')}</div>
                <div class="sub">{prediction_data.get('signal_description', '')}</div>
            </div>
            <div class="metric-card">
                <div class="label">Optimal Strategy</div>
                <div class="value">{prediction_data.get('best_strategy', 'N/A')}</div>
                <div class="sub">Projected savings: {prediction_data.get('projected_savings', '$0')}</div>
            </div>
            <div class="metric-card">
                <div class="label">VaR (95%)</div>
                <div class="value">{prediction_data.get('var_95', 'N/A')}</div>
                <div class="sub">Value at Risk</div>
            </div>
        </div>
    </div>"""

    # ── AI Analysis Summary
    ai_summary = prediction_data.get("ai_summary", "")
    if ai_summary:
        content += f"""
    <div class="ai-summary">
        <h3>AI-Generated Analysis</h3>
        <p>{ai_summary}</p>
    </div>"""

    # ── Yield Curve Forecast
    if charts.get("yield_forecast"):
        content += f"""
    <div class="section">
        <h2>Yield Curve Forecast</h2>
        <p style="font-size: 13px; color: #64748b; margin-bottom: 12px;">Projected yield curve evolution based on current market conditions and historical patterns.</p>
        <div class="chart"><img src="{charts['yield_forecast']}" alt="Yield Curve Forecast"></div>
    </div>"""

    # ── Monte Carlo Simulation
    mc = prediction_data.get("monte_carlo", {})
    if mc:
        content += f"""
    <div class="section">
        <h2>Monte Carlo Simulation</h2>
        <p style="font-size: 13px; color: #64748b; margin-bottom: 12px;">{mc.get('num_simulations', 1000)} simulated scenarios over {mc.get('horizon_years', 5)} years.</p>
        <div class="metrics">
            <div class="metric-card">
                <div class="label">Expected Cost</div>
                <div class="value">${mc.get('expected_cost', 0):,.0f}</div>
            </div>
            <div class="metric-card">
                <div class="label">Best Case (5th)</div>
                <div class="value" style="color: #10b981">${mc.get('best_case', 0):,.0f}</div>
            </div>
            <div class="metric-card">
                <div class="label">Worst Case (95th)</div>
                <div class="value" style="color: #dc2626">${mc.get('worst_case', 0):,.0f}</div>
            </div>
            <div class="metric-card">
                <div class="label">CVaR (99%)</div>
                <div class="value">${mc.get('cvar_99', 0):,.0f}</div>
            </div>
        </div>"""

        # Monte Carlo chart
        if charts.get("monte_carlo"):
            content += f"""
        <div class="chart"><img src="{charts['monte_carlo']}" alt="Monte Carlo Distribution"></div>"""

        # Percentile table
        percentiles = mc.get("percentiles", {})
        if percentiles:
            content += """
        <table>
            <tr><th>Percentile</th><th>Annual Cost</th><th>Interpretation</th></tr>"""
            for p, val in sorted(percentiles.items(), key=lambda x: float(x[0].replace('%', '').replace('th', '').replace('st', '').replace('nd', '').replace('rd', ''))):
                interp = "Best case" if "5" in p else "Expected" if "50" in p else "Stress" if "95" in p else "Moderate"
                content += f"""
            <tr><td>{p}</td><td>${val:,.0f}</td><td>{interp}</td></tr>"""
            content += "</table>"
        content += "</div>"

    # ── Early Warning Indicators
    ew = prediction_data.get("early_warning", {})
    if ew:
        content += f"""
    <div class="section">
        <h2>Early Warning Indicators</h2>
        <p style="font-size: 13px; color: #64748b; margin-bottom: 12px;">12 key sovereign risk indicators with automated threshold monitoring.</p>
        <div class="metrics">
            <div class="metric-card">
                <div class="label">Overall EW Score</div>
                <div class="value" style="color: {ew.get('color', '#6b7280')}">{ew.get('overall_score', 'N/A')}</div>
                <div class="sub">{ew.get('status', 'Unknown')}</div>
            </div>
            <div class="metric-card">
                <div class="label">Alerts Active</div>
                <div class="value">{ew.get('alerts_count', 0)}</div>
            </div>
            <div class="metric-card">
                <div class="label">Lead Time</div>
                <div class="value">{ew.get('lead_time', 'N/A')}</div>
            </div>
        </div>"""

        if charts.get("early_warning"):
            content += f"""
        <div class="chart"><img src="{charts['early_warning']}" alt="Early Warning Indicators"></div>"""

        indicators = ew.get("indicators", [])
        if indicators:
            content += """
        <table>
            <tr><th>Indicator</th><th>Score</th><th>Status</th><th>Description</th></tr>"""
            for ind in indicators:
                score = ind.get("score", 0)
                status = "CRITICAL" if score > 0.7 else "WARNING" if score > 0.3 else "SAFE"
                badge = "badge-red" if score > 0.7 else "badge-yellow" if score > 0.3 else "badge-green"
                content += f"""
            <tr>
                <td>{ind.get('name', '')}</td>
                <td>{score:.2f}</td>
                <td><span class="badge {badge}">{status}</span></td>
                <td>{ind.get('description', '')}</td>
            </tr>"""
            content += "</table>"
        content += "</div>"

    # ── Risk Score Breakdown
    risk = prediction_data.get("risk_score", {})
    if isinstance(risk, dict):
        content += """
    <div class="section">
        <h2>Risk Score Breakdown</h2>"""

        if charts.get("risk_radar"):
            content += f"""
        <div class="chart"><img src="{charts['risk_radar']}" alt="Risk Radar"></div>"""

        factors = risk.get("factors", {})
        if factors:
            content += """
        <table>
            <tr><th>Factor</th><th>Score</th><th>Weight</th><th>Contribution</th></tr>"""
            for name, score in factors.items():
                content += f"""
            <tr>
                <td>{name.replace('_', ' ').title()}</td>
                <td>{score:.3f}</td>
                <td>—</td>
                <td>{score * 0.14:.3f}</td>
            </tr>"""
            content += "</table>"

        recs = risk.get("recommendations", [])
        if recs:
            content += "<h3>Recommendations</h3><ul>"
            for r in recs:
                content += f"<li>{r}</li>"
            content += "</ul>"
        content += "</div>"

    # ── Strategy Comparison
    strategies = prediction_data.get("strategies", [])
    if strategies:
        content += """
    <div class="section">
        <h2>Strategy Comparison</h2>
        <table>
            <tr><th>Strategy</th><th>Annual Cost</th><th>Risk Score</th><th>Duration</th><th>FX Exposure</th><th>Recommendation</th></tr>"""
        for s in strategies:
            badge = "badge-green" if s.get("recommended") else "badge-blue"
            content += f"""
        <tr>
            <td>{s.get('name', '')}</td>
            <td>${s.get('total_annual_cost', 0):,.0f}</td>
            <td>{s.get('risk_score', 0):.1f}/10</td>
            <td>{s.get('avg_duration', 0):.1f}Y</td>
            <td>{s.get('fx_exposure', 0):.1%}</td>
            <td><span class="badge {badge}">{'RECOMMENDED' if s.get('recommended') else 'ALTERNATIVE'}</span></td>
        </tr>"""
        content += "</table>"

        if charts.get("strategy_comparison"):
            content += f"""
        <div class="chart"><img src="{charts['strategy_comparison']}" alt="Strategy Comparison"></div>"""
        content += "</div>"

    # ── Investment Scenarios
    scenarios = prediction_data.get("investment_scenarios", [])
    if scenarios:
        content += """
    <div class="section">
        <h2>Investment Scenarios</h2>
        <table>
            <tr><th>Scenario</th><th>Investment</th><th>Expected Return</th><th>Return %</th><th>Probability</th><th>Risk Level</th></tr>"""
        for sc in scenarios:
            badge = "badge-green" if sc.get("risk_level") == "low" else "badge-yellow" if sc.get("risk_level") == "medium" else "badge-red"
            content += f"""
        <tr>
            <td>{sc.get('scenario_name', '')}</td>
            <td>${sc.get('investment', 0):,.0f}</td>
            <td>${sc.get('return_amount', 0):,.0f}</td>
            <td>{sc.get('return_pct', 0):+.1f}%</td>
            <td>{sc.get('probability', 0):.1%}</td>
            <td><span class="badge {badge}">{sc.get('risk_level', '').upper()}</span></td>
        </tr>"""
        content += "</table></div>"

    # ── Methodology
    content += """
    <div class="section">
        <h2>Methodology</h2>
        <p style="font-size: 12px; color: #64748b; line-height: 1.6;">
        This report uses Monte Carlo simulation with Hull-White mean-reverting rate dynamics (1,000+ paths),
        12-indicator early warning detection with bias-adjusted thresholds,
        multi-factor risk scoring, and optimization via mixed-integer linear programming (MILP).
        All projections are based on current market data and historical patterns. Past performance does not guarantee future results.
        </p>
    </div>"""

    return PREDICTION_HTML_TEMPLATE.format(
        content=content,
        generated_at=generated_at,
        report_id=report_id,
    )


# ── PDF Rendering ────────────────────────────────────────────────────

def render_html_to_pdf(html: str, output_path: Optional[str] = None) -> str:
    """Convert HTML to PDF using wkhtmltopdf. Returns output path."""
    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), f"quantive_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")

    try:
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
            f.write(html)
            html_path = f.name

        result = subprocess.run(
            ["wkhtmltopdf", "--enable-local-file-access", "--page-size", "A4",
             "--margin-top", "15mm", "--margin-bottom", "15mm",
             "--margin-left", "15mm", "--margin-right", "15mm",
             html_path, output_path],
            capture_output=True, text=True, timeout=30,
        )

        os.unlink(html_path)

        if result.returncode != 0:
            raise RuntimeError(f"wkhtmltopdf failed: {result.stderr}")

        return output_path
    except FileNotFoundError:
        # wkhtmltopdf not installed — return HTML path instead
        html_path = output_path.replace('.pdf', '.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return html_path


def generate_prediction_pdf(prediction_data: dict, charts: Optional[dict] = None) -> str:
    """Generate complete prediction PDF report. Returns file path."""
    html = build_prediction_report(prediction_data, charts)
    return render_html_to_pdf(html)
