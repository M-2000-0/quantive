"""Report generation for decision packages.

Generates comprehensive reports in multiple formats (PDF, HTML, Markdown)
containing optimization results, strategy comparisons, and audit trails.

Includes matplotlib chart generation for visual analytics:
- Risk radar chart
- Maturity waterfall
- Strategy comparison bar charts
- Allocation pie chart
"""
from __future__ import annotations

import io
import base64
from datetime import datetime, timezone
from typing import Dict, List, Optional

from quantive.models.results import (
    BenchmarkResult,
    OptimizationResult,
    Strategy,
    StressTestResult,
)


# ── Chart Generation ────────────────────────────────────────────────────────

def _get_matplotlib():
    """Lazy import matplotlib to avoid hard dependency."""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        return plt, mpatches
    except ImportError:
        raise ImportError(
            "Chart generation requires matplotlib. "
            "Install with: pip install matplotlib"
        )


def generate_risk_radar(
    risk_metrics: dict,
    title: str = "Risk Profile",
    figsize: tuple = (8, 6),
) -> str:
    """Generate a radar chart of risk metrics.

    Args:
        risk_metrics: Dict with keys like interest_rate_risk, currency_risk, etc.
        title: Chart title
        figsize: Figure size

    Returns:
        Base64-encoded PNG image string
    """
    plt, _ = _get_matplotlib()

    # Normalize risk metrics to 0-1 scale
    categories = []
    values = []

    risk_mapping = {
        'interest_rate_risk': 'Interest Rate',
        'currency_risk': 'Currency',
        'refinancing_risk': 'Refinancing',
        'max_maturity_share': 'Maturity Concentration',
        'floating_share': 'Floating Rate',
        'foreign_currency_share': 'Foreign Currency',
    }

    for key, label in risk_mapping.items():
        if key in risk_metrics:
            categories.append(label)
            # Normalize to 0-1 (assuming max reasonable values)
            value = risk_metrics[key]
            if 'share' in key or 'concentration' in key:
                normalized = min(value, 1.0)
            else:
                normalized = min(abs(value) * 100, 1.0)
            values.append(normalized)

    if not categories:
        return ""

    # Close the polygon
    values.append(values[0])
    categories.append(categories[0])

    fig, ax = plt.subplots(figsize=figsize, subplot_kw=dict(polar=True))

    angles = [i / (len(categories) - 1) * 2 * 3.14159 for i in range(len(categories))]

    ax.plot(angles, values, 'o-', linewidth=2, color='#2563eb')
    ax.fill(angles, values, alpha=0.25, color='#2563eb')

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories[:-1], size=10)
    ax.set_ylim(0, 1)
    ax.set_title(title, size=14, fontweight='bold', pad=20)

    # Add risk level rings
    for level in [0.25, 0.5, 0.75, 1.0]:
        ax.plot([0, 2 * 3.14159], [level, level], '-', color='gray', alpha=0.3, linewidth=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode()


def generate_strategy_comparison(
    strategies: List[dict],
    metric: str = 'financing_cost',
    title: str = "Strategy Comparison",
    figsize: tuple = (10, 6),
) -> str:
    """Generate a bar chart comparing strategies.

    Args:
        strategies: List of strategy dicts with metrics
        metric: Which metric to compare
        title: Chart title
        figsize: Figure size

    Returns:
        Base64-encoded PNG image string
    """
    plt, _ = _get_matplotlib()

    names = [s.get('name', f'Strategy {i}') for i, s in enumerate(strategies)]
    values = [s.get('metrics', {}).get(metric, 0) for s in strategies]
    feasible = [s.get('feasible', True) for s in strategies]

    fig, ax = plt.subplots(figsize=figsize)

    colors = ['#22c55e' if f else '#ef4444' for f in feasible]
    bars = ax.bar(names, values, color=colors, edgecolor='white', linewidth=0.5)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.02,
            f'${val:,.0f}',
            ha='center', va='bottom', fontsize=9,
        )

    ax.set_xlabel('Strategy')
    ax.set_ylabel(metric.replace('_', ' ').title())
    ax.set_title(title, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Legend
    feasible_patch = plt.Rectangle((0, 0), 1, 1, fc='#22c55e')
    infeasible_patch = plt.Rectangle((0, 0), 1, 1, fc='#ef4444')
    ax.legend([feasible_patch, infeasible_patch], ['Feasible', 'Infeasible'])

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode()


def generate_allocation_pie(
    allocation: dict,
    title: str = "Portfolio Allocation",
    figsize: tuple = (8, 6),
) -> str:
    """Generate a pie chart of portfolio allocation.

    Args:
        allocation: Dict mapping instrument IDs to amounts
        title: Chart title
        figsize: Figure size

    Returns:
        Base64-encoded PNG image string
    """
    plt, _ = _get_matplotlib()

    # Filter out zero allocations and sort
    filtered = {k: v for k, v in allocation.items() if v > 0}
    if not filtered:
        return ""

    sorted_items = sorted(filtered.items(), key=lambda x: -x[1])

    # Group small allocations into 'Other' if more than 8 items
    if len(sorted_items) > 8:
        top_items = sorted_items[:7]
        other_amount = sum(v for _, v in sorted_items[7:])
        labels = [item[0][:20] for item in top_items] + ['Other']
        sizes = [item[1] for item in top_items] + [other_amount]
    else:
        labels = [item[0][:25] for item in sorted_items]
        sizes = [item[1] for item in sorted_items]

    total = sum(sizes)
    percentages = [(s / total * 100) for s in sizes]

    fig, ax = plt.subplots(figsize=figsize)

    colors = plt.cm.Set3(range(len(labels)))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct=lambda pct: f'{pct:.1f}%' if pct > 3 else '',
        colors=colors,
        startangle=90,
        pctdistance=0.85,
    )

    # Style
    for text in texts:
        text.set_fontsize(9)
    for autotext in autotexts:
        autotext.set_fontsize(8)
        autotext.set_fontweight('bold')

    ax.set_title(title, fontweight='bold', fontsize=12)

    # Add total in center
    centre_circle = plt.Circle((0, 0), 0.55, fc='white')
    ax.add_artist(centre_circle)
    ax.text(0, 0.05, f'${total:,.0f}', ha='center', va='center', fontsize=14, fontweight='bold')
    ax.text(0, -0.1, 'Total', ha='center', va='center', fontsize=10, color='gray')

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode()


def generate_maturity_waterfall(
    instruments: List[dict],
    title: str = "Maturity Profile",
    figsize: tuple = (10, 6),
) -> str:
    """Generate a waterfall chart of maturities by year.

    Args:
        instruments: List of instrument dicts with maturity_date and principal_outstanding
        title: Chart title
        figsize: Figure size

    Returns:
        Base64-encoded PNG image string
    """
    plt, _ = _get_matplotlib()

    # Group by maturity year
    maturities = {}
    for inst in instruments:
        try:
            year = int(inst.get('maturity_date', '2030-01-01')[:4])
            amount = inst.get('principal_outstanding', 0)
            maturities[year] = maturities.get(year, 0) + amount
        except (ValueError, TypeError):
            continue

    if not maturities:
        return ""

    years = sorted(maturities.keys())
    amounts = [maturities[y] for y in years]

    fig, ax = plt.subplots(figsize=figsize)

    # Create waterfall bars
    colors = ['#3b82f6' for _ in years]
    bars = ax.bar([str(y) for y in years], amounts, color=colors, edgecolor='white', linewidth=0.5)

    # Add value labels
    for bar, val in zip(bars, amounts):
        if val > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(amounts) * 0.02,
                f'${val:,.0f}',
                ha='center', va='bottom', fontsize=8,
            )

    ax.set_xlabel('Maturity Year')
    ax.set_ylabel('Principal Outstanding')
    ax.set_title(title, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Add cumulative line
    cumulative = []
    running = 0
    for amt in amounts:
        running += amt
        cumulative.append(running)

    ax2 = ax.twinx()
    ax2.plot([str(y) for y in years], cumulative, 'o-', color='#ef4444', linewidth=2, markersize=6)
    ax2.set_ylabel('Cumulative', color='#ef4444')
    ax2.tick_params(axis='y', labelcolor='#ef4444')

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode()


def generate_benchmark_chart(
    benchmarks: List[dict],
    title: str = "Solver Benchmark",
    figsize: tuple = (10, 6),
) -> str:
    """Generate a performance comparison chart for solvers.

    Args:
        benchmarks: List of benchmark dicts with solver_name, execution_time_seconds, objective_value
        title: Chart title
        figsize: Figure size

    Returns:
        Base64-encoded PNG image string
    """
    plt, _ = _get_matplotlib()

    names = [b.get('solver_name', f'Solver {i}') for i, b in enumerate(benchmarks)]
    times = [b.get('execution_time_seconds', 0) for b in benchmarks]
    objectives = [b.get('objective_value', 0) for b in benchmarks]
    feasible = [b.get('feasible', True) for b in benchmarks]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=figsize)

    # Runtime comparison
    colors = ['#22c55e' if f else '#ef4444' for f in feasible]
    ax1.barh(names, times, color=colors, edgecolor='white')
    ax1.set_xlabel('Runtime (seconds)')
    ax1.set_title('Execution Time', fontweight='bold')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    # Objective comparison
    ax2.barh(names, objectives, color=colors, edgecolor='white')
    ax2.set_xlabel('Objective Value')
    ax2.set_title('Solution Quality', fontweight='bold')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    fig.suptitle(title, fontweight='bold', fontsize=12)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode()


def generate_all_charts(
    result: OptimizationResult,
    strategies: List[Strategy],
    benchmark: Optional[BenchmarkResult] = None,
    instruments: Optional[List[dict]] = None,
) -> Dict[str, str]:
    """Generate all charts for a report.

    Returns:
        Dict mapping chart name to base64-encoded PNG string
    """
    charts = {}

    # Risk radar
    try:
        risk_metrics = {
            'interest_rate_risk': result.strategy.risk_metrics.interest_rate_risk,
            'currency_risk': result.strategy.risk_metrics.currency_risk,
            'refinancing_risk': result.strategy.risk_metrics.refinancing_risk / 1e9,
            'max_maturity_share': result.strategy.risk_metrics.max_maturity_share,
            'floating_share': result.strategy.risk_metrics.floating_share,
            'foreign_currency_share': result.strategy.risk_metrics.foreign_currency_share,
        }
        charts['risk_radar'] = generate_risk_radar(risk_metrics)
    except Exception:
        pass

    # Strategy comparison
    try:
        strategy_dicts = [
            {
                'name': s.name,
                'metrics': {'financing_cost': s.financing_cost},
                'feasible': s.feasible,
            }
            for s in strategies
        ]
        charts['strategy_comparison'] = generate_strategy_comparison(strategy_dicts)
    except Exception:
        pass

    # Allocation pie
    try:
        charts['allocation_pie'] = generate_allocation_pie(result.strategy.allocation)
    except Exception:
        pass:

    # Maturity waterfall
    if instruments:
        try:
            charts['maturity_waterfall'] = generate_maturity_waterfall(instruments)
        except Exception:
            pass

    # Benchmark chart
    if benchmark and benchmark.rows:
        try:
            benchmark_dicts = [
                {
                    'solver_name': row.solver,
                    'execution_time_seconds': row.runtime,
                    'objective_value': row.objective_value,
                    'feasible': row.feasible,
                }
                for row in benchmark.ranked_rows()
            ]
            charts['benchmark'] = generate_benchmark_chart(benchmark_dicts)
        except Exception:
            pass

    return charts


def generate_markdown_report(
    result: OptimizationResult,
    strategies: List[Strategy],
    benchmark: Optional[BenchmarkResult] = None,
    stress_results: Optional[Dict[str, StressTestResult]] = None,
    portfolio_name: str = "",
    problem_name: str = "",
) -> str:
    """Generate a comprehensive Markdown decision report."""
    lines = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Title
    lines.append(f"# Decision Package: {problem_name}")
    lines.append(f"**Generated:** {now}  ")
    lines.append(f"**Portfolio:** {portfolio_name}  ")
    lines.append(f"**Solver:** {result.solver} ({result.solver_type.value})  ")
    lines.append(f"**Runtime:** {result.runtime:.2f}s  ")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    strategy = result.strategy
    lines.append(f"- **Selected Strategy:** {strategy.name}")
    lines.append(f"- **Expected Financing Cost:** ${strategy.financing_cost:,.0f}")
    lines.append(f"- **Objective Value:** {strategy.objective_value:,.4f}")
    lines.append(f"- **Feasible:** {'Yes' if strategy.feasible else 'No'}")
    lines.append(f"- **Optimality:** {result.optimality_note}")
    lines.append("")

    # Risk Metrics
    lines.append("## Risk Metrics")
    lines.append("")
    rm = strategy.risk_metrics
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Expected Cost | ${rm.expected_cost:,.0f} |")
    lines.append(f"| Interest Rate Risk | {rm.interest_rate_risk:,.4f} |")
    lines.append(f"| Currency Risk | {rm.currency_risk:,.4f} |")
    lines.append(f"| Refinancing Risk | {rm.refinancing_risk:,.0f} |")
    lines.append(f"| Max Maturity Share | {rm.max_maturity_share:.1%} |")
    lines.append(f"| Floating Share | {rm.floating_share:.1%} |")
    lines.append(f"| Foreign Currency Share | {rm.foreign_currency_share:.1%} |")
    lines.append("")

    # Allocation
    lines.append("## Allocation")
    lines.append("")
    lines.append("| Instrument | Amount | Share |")
    lines.append("|-----------|--------|-------|")
    total = sum(strategy.allocation.values())
    for iid, amount in sorted(strategy.allocation.items(), key=lambda x: -x[1]):
        if amount > 0:
            share = amount / total if total > 0 else 0
            lines.append(f"| {iid} | ${amount:,.0f} | {share:.1%} |")
    lines.append(f"| **Total** | **${total:,.0f}** | **100%** |")
    lines.append("")

    # Constraint Status
    lines.append("## Constraint Satisfaction")
    lines.append("")
    lines.append("| Constraint | Status | Violation |")
    lines.append("|-----------|--------|-----------|")
    for cs in strategy.constraint_status:
        status = "✅ Satisfied" if cs.satisfied else "❌ Violated"
        lines.append(f"| {cs.name} | {status} | {cs.violation:.4f} |")
    lines.append("")

    # Strategies Comparison
    if len(strategies) > 1:
        lines.append("## Strategy Comparison")
        lines.append("")
        lines.append("| Strategy | Profile | Cost | Feasible | Solver |")
        lines.append("|----------|---------|------|----------|--------|")
        for s in strategies:
            lines.append(
                f"| {s.name} | {s.profile.value} | ${s.financing_cost:,.0f} "
                f"| {'Yes' if s.feasible else 'No'} | {s.solver} |"
            )
        lines.append("")

    # Benchmark
    if benchmark and benchmark.rows:
        lines.append("## Solver Benchmark")
        lines.append("")
        lines.append("| Rank | Solver | Type | Runtime | Objective | Feasible |")
        lines.append("|------|--------|------|---------|-----------|----------|")
        for row in benchmark.ranked_rows():
            lines.append(
                f"| {row.rank} | {row.solver} | {row.solver_type.value} "
                f"| {row.runtime:.2f}s | {row.objective_value:,.0f} "
                f"| {'Yes' if row.feasible else 'No'} |"
            )
        lines.append("")

    # Stress Test
    if stress_results:
        lines.append("## Stress Test Results")
        lines.append("")
        for sid, st in stress_results.items():
            lines.append(f"### Strategy: {sid}")
            lines.append(f"- **Scenarios:** {st.scenario_count}")
            lines.append(f"- **Avg Cost:** ${st.avg_financing_cost:,.0f}")
            lines.append(f"- **Worst Cost:** ${st.worst_financing_cost:,.0f}")
            lines.append(f"- **Constraint Satisfaction:** {st.constraint_satisfaction_rate:.1%}")
            lines.append(f"- **Refinancing Breaches:** {st.refinancing_breaches}")
            lines.append(f"- **Liquidity Breaches:** {st.liquidity_breaches}")
            lines.append(f"- **Currency Breaches:** {st.currency_breaches}")
            lines.append("")

    # Assumptions
    lines.append("## Assumptions & Limitations")
    lines.append("")
    lines.append("- All data is synthetic for demonstration purposes")
    lines.append("- Scenario parameters are calibrated to representative market conditions")
    lines.append("- Solver runtime and optimality depend on problem size and configuration")
    lines.append("- Results should be validated against actual market data before use")
    lines.append("")

    # Provenance
    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- **Model Version:** {result.metadata.get('model_version', '1.0.0')}")
    lines.append(f"- **Solver:** {result.solver} ({result.solver_type.value}, {result.execution_backend.value})")
    lines.append(f"- **Iterations:** {result.iterations or 'N/A'}")
    lines.append(f"- **Objective Evaluations:** {result.objective_evaluations or 'N/A'}")
    lines.append(f"- **Generated At:** {now}")
    lines.append("")

    return "\n".join(lines)


def generate_html_report(
    result: OptimizationResult,
    strategies: List[Strategy],
    benchmark: Optional[BenchmarkResult] = None,
    stress_results: Optional[Dict[str, StressTestResult]] = None,
    portfolio_name: str = "",
    problem_name: str = "",
) -> str:
    """Generate an HTML decision report with embedded styling."""
    md = generate_markdown_report(result, strategies, benchmark, stress_results, portfolio_name, problem_name)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Decision Package: {problem_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #1a1a2e; }}
        h1 {{ color: #1e40af; border-bottom: 2px solid #1e40af; padding-bottom: 0.5rem; }}
        h2 {{ color: #334155; margin-top: 2rem; }}
        h3 {{ color: #475569; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
        th, td {{ border: 1px solid #e2e8f0; padding: 0.75rem; text-align: left; }}
        th {{ background: #f8fafc; font-weight: 600; }}
        tr:nth-child(even) {{ background: #fafafa; }}
        strong {{ color: #1e40af; }}
        code {{ background: #f1f5f9; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.9em; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; }}
        .badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px;
                  font-size: 0.75rem; font-weight: 600; }}
        .badge-success {{ background: #dcfce7; color: #166534; }}
        .badge-danger {{ background: #fee2e2; color: #991b1b; }}
        @media print {{ body {{ padding: 1rem; }} }}
    </style>
</head>
<body>
<pre style="white-space: pre-wrap; font-family: inherit;">{_md_to_html(md)}</pre>
</body>
</html>"""
    return html


def _md_to_html(md: str) -> str:
    """Simple Markdown to HTML conversion for report embedding."""
    import re
    html = md
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    return html
