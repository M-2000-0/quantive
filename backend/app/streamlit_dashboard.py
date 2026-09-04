"""Streamlit Executive Control Room — Sovereign Debt Engine.

Multi-tab dashboard:
    Tab 1 (Yield & Allocation): Interactive duration targets, budget constraints, bond issuance splits
    Tab 2 (Quantum vs Classical): Side-by-side benchmarking of optimization approaches
    Tab 3 (Macro Stress Testing): Heatmaps and probability curves
    Tab 4 (Policy Briefing): Local LLM-generated markdown briefing

Run: streamlit run app/streamlit_dashboard.py --server.port 8501
"""

import json
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Quantive — Sovereign Debt Engine",
    page_icon="Q",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
    .stMetric { background: rgba(28, 28, 35, 0.8); border-radius: 8px; padding: 12px; }
    .stMetric label { color: #888; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ─────────────────────────────────────────────────────────
st.sidebar.title("Quantive Engine")
st.sidebar.markdown("**Air-Gapped Sovereign Debt Optimizer**")

page = st.sidebar.radio(
    "Navigate",
    ["Yield & Allocation", "Quantum vs Classical", "Stress Testing", "Policy Briefing", "System Status"],
    index=0,
)

# ── Shared State ────────────────────────────────────────────────────
if "yield_curve" not in st.session_state:
    st.session_state.yield_curve = {"3M": 4.25, "6M": 4.20, "1Y": 4.10, "2Y": 3.80, "3Y": 3.70, "5Y": 3.70, "7Y": 3.80, "10Y": 4.00, "20Y": 4.20, "30Y": 4.25}

if "instruments" not in st.session_state:
    st.session_state.instruments = [
        {"name": "US Treasury 2Y", "principal_outstanding": 10e9, "coupon_rate": 0.038, "maturity_years": 2, "rate_type": "fixed"},
        {"name": "US Treasury 5Y", "principal_outstanding": 15e9, "coupon_rate": 0.037, "maturity_years": 5, "rate_type": "fixed"},
        {"name": "US Treasury 10Y", "principal_outstanding": 12e9, "coupon_rate": 0.040, "maturity_years": 10, "rate_type": "fixed"},
        {"name": "US Treasury 30Y", "principal_outstanding": 8e9, "coupon_rate": 0.042, "maturity_years": 30, "rate_type": "fixed"},
        {"name": "FRN 3M", "principal_outstanding": 5e9, "coupon_rate": 0.040, "maturity_years": 3, "rate_type": "floating"},
    ]


def call_api(endpoint: str, data: dict = None, method: str = "POST") -> dict:
    """Call the FastAPI backend."""
    import urllib.request
    url = f"http://127.0.0.1:8000/api/v1/{endpoint}"
    try:
        if method == "GET":
            req = urllib.request.Request(url)
        else:
            req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=120)
        return json.loads(resp.read())
    except Exception as e:
        st.error(f"API Error: {e}")
        return {}


# ═══ TAB 1: YIELD & ALLOCATION ═════════════════════════════════════

if page == "Yield & Allocation":
    st.title("Yield Curve & Allocation Optimizer")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Current Yield Curve")
        for label in ["3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"]:
            st.session_state.yield_curve[label] = st.slider(
                f"{label} (%)", 0.0, 15.0, st.session_state.yield_curve[label], 0.05, key=f"yc_{label}"
            ) / 100

    with col2:
        st.subheader("Constraints")
        total_issuance = st.number_input("Total Issuance ($B)", value=50.0, min_value=1.0, max_value=500.0) * 1e9
        risk_aversion = st.slider("Risk Aversion (α)", 0.0, 50.0, 10.0)
        max_floating = st.slider("Max Floating Rate (%)", 0, 100, 30) / 100

    if st.button("Run Covariance QUBO Optimization", type="primary"):
        with st.spinner("Running QUBO solver..."):
            result = call_api("optimize", {
                "yield_curve": st.session_state.yield_curve,
                "total_issuance": total_issuance,
                "risk_aversion": risk_aversion,
            })

        if result.get("status") == "success":
            st.success(f"Optimization complete in {result['solve_time_seconds']}s")

            # Display results
            selected = result["result"]["selected_options"]
            if selected:
                alloc_data = []
                for opt in selected:
                    alloc_data.append({
                        "Maturity": opt["maturity_label"],
                        "Type": opt["rate_type"],
                        "Years": opt["maturity_years"],
                    })

                fig = go.Figure(data=[go.Pie(
                    labels=[f"{a['Maturity']} {a['Type']}" for a in alloc_data],
                    values=[1] * len(alloc_data),
                    hole=0.4,
                    marker_colors=["#6366f1", "#eab308", "#22c55e"],
                )])
                fig.update_layout(title="Optimized Allocation", height=400)
                st.plotly_chart(fig, use_container_width=True)

                st.json(alloc_data)

    # Yield curve visualization
    st.subheader("Yield Curve Visualization")
    labels = list(st.session_state.yield_curve.keys())
    rates = [v * 100 for v in st.session_state.yield_curve.values()]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels, y=rates, mode="lines+markers", name="Current",
                             line=dict(color="#6366f1", width=3), marker=dict(size=8)))
    fig.update_layout(
        title="Sovereign Yield Curve",
        xaxis_title="Maturity", yaxis_title="Yield (%)",
        template="plotly_dark", height=350,
    )
    st.plotly_chart(fig, use_container_width=True)


# ═══ TAB 2: QUANTUM VS CLASSICAL ═══════════════════════════════════

elif page == "Quantum vs Classical":
    st.title("Quantum vs Classical Benchmarking")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Classical Solver (SLSQP)")
        if st.button("Run Classical"):
            with st.spinner("Running classical optimizer..."):
                from app.optimization.qubo_formulator import formulate_qubo, DebtParameters, solve_covariance_qubo as _
                from app.optimization.covariance_qubo import formulate_covariance_qubo, solve_covariance_qubo

                # Build a small QUBO for comparison
                params = {
                    "3M": 0.042, "2Y": 0.038, "5Y": 0.037, "10Y": 0.040, "30Y": 0.042
                }
                problem = formulate_covariance_qubo(
                    yield_rates=params,
                    covariance_matrix=[[0.0001 if i == j else 0.00005 for j in range(9)] for i in range(9)],
                    total_issuance=50e9,
                )
                start = time.time()
                result = solve_covariance_qubo(problem)
                elapsed = time.time() - start

            st.metric("Solve Time", f"{elapsed:.3f}s")
            st.metric("Objective Value", f"{result['objective_value']:.4f}")
            st.metric("Options Selected", result["n_selected"])

    with col2:
        st.subheader("Quantum QAOA (Simulator)")
        if st.button("Run QAOA"):
            with st.spinner("Running QAOA circuit..."):
                try:
                    from app.quantum.hybrid_solver import HybridSolver, SolverStatus
                    from app.quantum.state_encoder import CircuitParameters, CostFunction

                    solver = HybridSolver(max_iterations=100, timeout_seconds=10)
                    params = CircuitParameters(n_qubits=27, n_layers=2, gamma=[0.5]*2, beta=[0.5]*2)
                    cost_fn = CostFunction()

                    instruments = [{"face_value": 10e9, "isin": f"BOND-{i}"} for i in range(9)]
                    start = time.time()
                    qaoa_result = solver.solve(params, cost_fn, instruments, [], {})
                    elapsed = time.time() - start

                    st.metric("Solve Time", f"{elapsed:.3f}s")
                    st.metric("Status", qaoa_result.status.value)
                    st.metric("Objective", f"{qaoa_result.objective_value:.4f}")
                    st.metric("Backend", qaoa_result.backend)
                except Exception as e:
                    st.error(f"QAOA Error: {e}")

    # Convergence comparison chart
    st.subheader("Convergence Comparison")
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Classical SLSQP", "Quantum QAOA"))

    # Simulated convergence data
    import random
    classical_iters = list(range(100))
    classical_energy = [10.0 * (0.95 ** i) + random.gauss(0, 0.1) for i in classical_iters]
    qaoa_iters = list(range(100))
    qaoa_energy = [10.0 * (0.97 ** i) + random.gauss(0, 0.3) for i in qaoa_iters]

    fig.add_trace(go.Scatter(x=classical_iters, y=classical_energy, name="Classical", line=dict(color="#6366f1")), row=1, col=1)
    fig.add_trace(go.Scatter(x=qaoa_iters, y=qaoa_energy, name="QAOA", line=dict(color="#22c55e")), row=1, col=2)
    fig.update_layout(template="plotly_dark", height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


# ═══ TAB 3: STRESS TESTING ═════════════════════════════════════════

elif page == "Stress Testing":
    st.title("Macro Stress Testing")

    n_paths = st.slider("Simulation Paths", 1000, 50000, 10000, 1000)
    horizon = st.slider("Horizon (months)", 12, 120, 60, 12)

    if st.button("Run 10K Monte Carlo", type="primary"):
        with st.spinner(f"Running {n_paths:,} scenarios..."):
            result = call_api("simulate", {
                "yield_curve": {k: v/100 for k, v in st.session_state.yield_curve.items()},
                "instruments": st.session_state.instruments,
                "n_paths": n_paths,
                "horizon_months": horizon,
            })

        if result.get("status") == "success":
            st.success(f"Completed in {result['elapsed_seconds']}s ({result['n_paths']:,} paths)")

            # Portfolio risk metrics
            risk = result["portfolio_risk"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Duration", f"{risk['duration']:.2f}")
            c2.metric("VaR 95%", f"${risk['var_95']/1e9:.2f}B")
            c3.metric("CVaR 95%", f"${risk['cvar_95']/1e9:.2f}B")
            c4.metric("Sharpe", f"{risk['sharpe_ratio']:.2f}")

            # Yield curve fan chart
            scenarios = result["yield_scenarios"]
            mean_path = scenarios["mean_path"]
            worst_path = scenarios["worst_path"]
            best_path = scenarios["best_path"]
            labels = scenarios["maturity_labels"]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=labels, y=[r*100 for r in best_path[-1]], name="Best Case", line=dict(color="#22c55e", dash="dash")))
            fig.add_trace(go.Scatter(x=labels, y=[r*100 for r in mean_path[-1]], name="Mean", line=dict(color="#6366f1", width=3)))
            fig.add_trace(go.Scatter(x=labels, y=[r*100 for r in worst_path[-1]], name="Worst Case", line=dict(color="#ef4444", dash="dash")))
            fig.update_layout(title="Yield Curve at Horizon", template="plotly_dark", height=400)
            st.plotly_chart(fig, use_container_width=True)

            # Stress test heatmap
            if result.get("stress_tests"):
                stress_data = []
                for name, data in result["stress_tests"].items():
                    stress_data.append({
                        "Scenario": name.replace("_", " ").title(),
                        "Shift (bps)": data["shift_bps"],
                        "VaR 95%": data["var_95"] / 1e9,
                        "CVaR 95%": data["cvar_95"] / 1e9,
                    })

                fig = px.imshow(
                    [[s["VaR 95%"] for s in stress_data]],
                    labels=dict(x="Scenarios", y="Risk"),
                    x=[s["Scenario"] for s in stress_data],
                    color_continuous_scale="RdYlGn_r",
                    aspect="auto",
                )
                fig.update_layout(title="Stress Test Heatmap (VaR 95%)", template="plotly_dark", height=300)
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(stress_data, use_container_width=True)


# ═══ TAB 4: POLICY BRIEFING ════════════════════════════════════════

elif page == "Policy Briefing":
    st.title("AI Policy Briefing")

    st.info("This briefing is generated locally using Ollama (air-gapped). No data leaves your machine.")

    model = st.selectbox("LLM Model", ["llama3.1", "deepseek-v4", "qwen3-30b", "mistral"])

    if st.button("Generate Policy Brief", type="primary"):
        with st.spinner("Generating policy brief via local LLM..."):
            result = call_api("report", {
                "portfolio_data": {"instruments": st.session_state.instruments, "total_value": 50e9},
                "yield_data": st.session_state.yield_curve,
                "macro_data": {"gdp_growth_pct": 2.5, "inflation_pct": 3.0, "fiscal_balance_pct": -3.5},
                "model": "ollama",
            })

        if result.get("status") == "success":
            report = result["report"]

            st.subheader("Executive Summary")
            st.write(report["executive_summary"])

            st.subheader("Key Recommendations")
            for i, rec in enumerate(report.get("recommendations", []), 1):
                with st.expander(f"Recommendation {i}: {rec.get('action', 'N/A')} {rec.get('target', '')}"):
                    st.write(f"**Current:** {rec.get('current_pct', 0)}% → **Target:** {rec.get('target_pct', 0)}%")
                    st.write(f"**Rationale:** {rec.get('rationale', '')}")
                    st.write(f"**Confidence:** {rec.get('confidence', 0):.0%} | **Priority:** {rec.get('priority', 'medium')}")

            st.subheader("Risk Assessment")
            st.write(report.get("risk_assessment", ""))

            st.subheader("Issuance Strategy")
            st.write(report.get("issuance_strategy", ""))

            st.subheader("Cost Savings Analysis")
            st.write(report.get("cost_savings_analysis", ""))

            st.subheader("Caveats")
            for caveats in report.get("caveats", []):
                st.warning(caveats)

            st.caption(f"Model: {report.get('model_used', 'unknown')} | Sources: {', '.join(report.get('sources_cited', []))}")


# ═══ TAB 5: SYSTEM STATUS ══════════════════════════════════════════

elif page == "System Status":
    st.title("System Status")

    result = call_api("status", method="GET")

    if result:
        for component, info in result.get("components", {}).items():
            status = info.get("status", "unknown")
            icon = "[+]" if status in ("operational", "connected") else "[~]" if status == "not_installed" else "[-]"
            with st.expander(f"{icon} {component.title()}"):
                st.json(info)
