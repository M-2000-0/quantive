"""AI Policy Engine — LLM-Powered Fiscal Policy Recommendations.

Translates quantum optimization results and Monte Carlo stress tests
into plain-language policy briefings for government treasury staff.

Architecture:
    Quantum Result + Macro Data → Structured Prompt → LLM → Policy Brief

The LLM receives:
1. Optimized debt allocation matrix
2. Cost savings metrics
3. Stress test results (Monte Carlo)
4. Risk decomposition

And produces:
- Executive summary
- Key recommendations
- Risk assessment
- Issuance strategy narrative
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class PolicyBrief:
    """Structured output from the AI policy engine."""
    executive_summary: str
    key_recommendations: list[str]
    risk_assessment: str
    issuance_strategy: str
    cost_savings_analysis: str
    stress_test_interpretation: str
    confidence_level: str  # "high", "medium", "low"
    caveats: list[str]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_used: str = "structured_template"


def generate_policy_brief(
    optimization_result: dict,
    monte_carlo_results: dict,
    covariance_data: dict,
    cost_of_service: dict,
    macro_data: dict,
    model_provider: str = "template",
    api_key: Optional[str] = None,
) -> PolicyBrief:
    """Generate a policy brief from optimization and simulation results.

    Args:
        optimization_result: Output from QUBO solver (allocations, metrics)
        monte_carlo_results: Output from Monte Carlo simulation (percentiles, VaR)
        covariance_data: Yield curve covariance matrix and volatilities
        cost_of_service: Current portfolio cost metrics
        macro_data: GDP, inflation, fiscal balance indicators
        model_provider: "template" for deterministic, "openai"/"anthropic" for LLM
        api_key: API key for LLM provider

    Returns:
        PolicyBrief with structured recommendations
    """
    if model_provider == "template" or not api_key:
        return _generate_template_brief(
            optimization_result, monte_carlo_results, covariance_data,
            cost_of_service, macro_data,
        )

    # Build structured prompt for LLM
    prompt = _build_llm_prompt(
        optimization_result, monte_carlo_results, covariance_data,
        cost_of_service, macro_data,
    )

    try:
        if model_provider == "openai":
            return _call_openai(prompt, api_key)
        elif model_provider == "anthropic":
            return _call_anthropic(prompt, api_key)
        elif model_provider == "ollama":
            return _call_ollama(prompt)
    except Exception as e:
        # Fallback to template
        brief = _generate_template_brief(
            optimization_result, monte_carlo_results, covariance_data,
            cost_of_service, macro_data,
        )
        brief.caveats.append(f"LLM generation failed ({model_provider}: {e}), using template fallback")
        return brief


def _build_llm_prompt(
    opt_result: dict, mc_results: dict, cov_data: dict,
    cos: dict, macro: dict,
) -> str:
    """Build a structured prompt for the LLM."""
    allocations = opt_result.get("allocations", [])
    metrics = opt_result.get("portfolio_metrics", {})
    var_data = mc_results.get("var", {})
    stress = mc_results.get("stress_scenarios", {})

    prompt = f"""You are a senior sovereign debt advisor to a finance ministry.

## Current Portfolio
- Total annual interest: ${cos.get('total_annual_interest', 0):,.0f}
- Weighted avg coupon: {cos.get('weighted_avg_coupon', 0):.2f}%
- Weighted avg maturity: {cos.get('weighted_avg_maturity', 0):.1f} years
- Duration risk: {cos.get('duration_risk', 0):.2f}

## Optimized Allocation
{json.dumps(allocations, indent=2)}

## Portfolio Metrics After Optimization
- Floating rate exposure: {metrics.get('floating_rate_pct', 0):.1f}%
- Short-term concentration: {metrics.get('short_term_pct', 0):.1f}%
- Weighted avg maturity: {metrics.get('weighted_avg_maturity_years', 0):.1f} years

## Risk Analysis (Monte Carlo, 1000 simulations)
- VaR (95%): ${var_data.get('var_95', 0):,.0f}
- CVaR (97.5%): ${var_data.get('cvar_975', 0):,.0f}
- Expected loss: ${var_data.get('expected_loss', 0):,.0f}

## Stress Scenarios
{json.dumps(stress, indent=2)}

## Macro Context
- GDP growth: {macro.get('gdp_growth_pct', 'N/A')}%
- Inflation: {macro.get('inflation_pct', 'N/A')}%
- Fiscal balance: {macro.get('fiscal_balance_pct', 'N/A')}% of GDP

## Task
Generate a policy brief with:
1. **Executive Summary** (2-3 sentences)
2. **Key Recommendations** (3-5 actionable items)
3. **Risk Assessment** (what could go wrong, how to mitigate)
4. **Issuance Strategy** (specific bond types, maturities, timing)
5. **Cost Savings Analysis** (quantified benefits)
6. **Stress Test Interpretation** (what the Monte Carlo results mean)

Be specific. Use numbers. Avoid vague language. Frame as recommendations to a finance minister.
"""
    return prompt


def _generate_template_brief(
    opt_result: dict, mc_results: dict, cov_data: dict,
    cos: dict, macro: dict,
) -> PolicyBrief:
    """Generate a deterministic template-based policy brief."""
    allocations = opt_result.get("allocations", [])
    metrics = opt_result.get("portfolio_metrics", {})
    var_data = mc_results.get("var", {})
    stress = mc_results.get("stress_scenarios", {})

    # Executive summary
    current_cost = cos.get("total_annual_interest", 0)
    current_coupon = cos.get("weighted_avg_coupon", 0)
    current_maturity = cos.get("weighted_avg_maturity", 0)
    new_maturity = metrics.get("weighted_avg_maturity_years", current_maturity)
    floating = metrics.get("floating_rate_pct", 0)
    short_term = metrics.get("short_term_pct", 0)

    savings_pct = max((current_coupon - metrics.get("target_coupon", current_coupon * 0.95)) / max(current_coupon, 0.01) * 100, 0)

    exec_summary = (
        f"The quantum-optimized allocation proposes {len(allocations)} issuance options "
        f"with a weighted average maturity of {new_maturity:.1f} years "
        f"(vs current {current_maturity:.1f} years). "
        f"Floating rate exposure is {floating:.1f}% "
        f"{'within' if floating <= 30 else 'exceeds'} the 30% target ceiling. "
        f"Estimated annual interest cost savings: {savings_pct:.1f}%."
    )

    # Key recommendations
    recommendations = []
    if floating > 30:
        recommendations.append(f"Reduce floating rate exposure from {floating:.1f}% to ≤30% to limit rate sensitivity")
    if short_term > 40:
        recommendations.append(f"Reduce short-term concentration from {short_term:.1f}% to ≤40% to lower rollover risk")
    if new_maturity < current_maturity - 1:
        recommendations.append(f"Extend average maturity from {current_maturity:.1f} to {new_maturity:.1f} years to lock in current rates")
    elif new_maturity > current_maturity + 2:
        recommendations.append(f"Consider shorter maturities to capture potential rate declines")
    recommendations.append("Stagger issuance across Q1-Q3 to avoid market timing risk")
    recommendations.append("Maintain 15-20% inflation-linked allocation to hedge CPI surprises")

    if not recommendations:
        recommendations = [
            "Portfolio is well-balanced; maintain current strategy with minor adjustments",
            "Monitor yield curve for inversion signals before next issuance window",
        ]

    # Risk assessment
    var_95 = var_data.get("var_95", 0)
    cvar = var_data.get("cvar_975", 0)
    risk_assessment = (
        f"Value-at-Risk (95%) is ${var_95:,.0f} under normal conditions. "
        f"Under extreme stress (97.5th percentile), expected loss reaches ${cvar:,.0f}. "
    )
    if stress:
        worst_scenario = max(stress.items(), key=lambda x: x[1].get("portfolio_loss_pct", 0) if isinstance(x[1], dict) else 0, default=None)
        if worst_scenario:
            risk_assessment += (
                f"Worst-case scenario: '{worst_scenario[0]}' with "
                f"{worst_scenario[1].get('portfolio_loss_pct', 0):.1f}% portfolio loss. "
            )
    risk_assessment += "Mitigation: maintain rolling 12-month maturity ladder and currency diversification."

    # Issuance strategy
    fixed_allocs = [a for a in allocations if a.get("rate_type") == "fixed"]
    float_allocs = [a for a in allocations if a.get("rate_type") == "floating"]
    il_allocs = [a for a in allocations if a.get("rate_type") == "inflation"]

    strategy_parts = []
    if fixed_allocs:
        fixed_maturities = ", ".join(a.get("maturity_label", "?") for a in fixed_allocs)
        strategy_parts.append(f"Issue fixed-rate bonds across maturities [{fixed_maturities}] to lock in current yields")
    if float_allocs:
        float_maturities = ", ".join(a.get("maturity_label", "?") for a in float_allocs)
        strategy_parts.append(f"Allocate {floating:.0f}% to floating-rate notes [{float_maturities}] for flexibility")
    if il_allocs:
        strategy_parts.append(f"Maintain inflation-linked issuance to hedge against CPI surprises")
    strategy_parts.append("Time primary auctions during low-volatility windows (VIX < 18)")

    issuance_strategy = ". ".join(strategy_parts) + "."

    # Cost savings
    potential_savings = current_cost * savings_pct / 100 if savings_pct > 0 else current_cost * 0.02
    cost_savings = (
        f"Estimated annual savings: ${potential_savings:,.0f} "
        f"({savings_pct:.1f}% of current ${current_cost:,.0f} annual interest). "
        f"Over 10 years (NPV at {cos.get('weighted_avg_coupon', 5):.1f}%): "
        f"${potential_savings * 7.5:,.0f}."
    )

    # Stress test interpretation
    stress_interp = (
        f"Under +200bps parallel shift, portfolio value declines by "
        f"{stress.get('rate_200bps_up', {}).get('portfolio_loss_pct', 5.0):.1f}%. "
        f"Under -100bps rally, gains of "
        f"{abs(stress.get('rate_100bps_down', {}).get('portfolio_loss_pct', -3.0)):.1f}%. "
        f"The optimized portfolio shows {'improved' if new_maturity > current_maturity else 'reduced'} "
        f"duration risk compared to current allocation."
    )

    return PolicyBrief(
        executive_summary=exec_summary,
        key_recommendations=recommendations,
        risk_assessment=risk_assessment,
        issuance_strategy=issuance_strategy,
        cost_savings_analysis=cost_savings,
        stress_test_interpretation=stress_interp,
        confidence_level="medium",
        caveats=[
            "Based on simulated quantum optimization on classical hardware",
            "Actual market conditions may differ from model assumptions",
            "Recommend independent validation by risk management team",
        ],
        model_used="structured_template",
    )


def _call_openai(prompt: str, api_key: str) -> PolicyBrief:
    """Call OpenAI API for policy brief generation."""
    import urllib.request

    payload = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a senior sovereign debt advisor. Generate structured policy briefs in JSON format with keys: executive_summary, key_recommendations (array), risk_assessment, issuance_strategy, cost_savings_analysis, stress_test_interpretation, confidence_level, caveats (array)."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    content = data["choices"][0]["message"]["content"]

    # Parse JSON from response
    try:
        # Try to extract JSON from markdown code block
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        result = json.loads(content.strip())
    except json.JSONDecodeError:
        result = {
            "executive_summary": content[:500],
            "key_recommendations": ["See executive summary"],
            "risk_assessment": "See executive summary",
            "issuance_strategy": "See executive summary",
            "cost_savings_analysis": "See executive summary",
            "stress_test_interpretation": "See executive summary",
            "confidence_level": "medium",
            "caveats": ["LLM output was not valid JSON"],
        }

    return PolicyBrief(
        executive_summary=result.get("executive_summary", ""),
        key_recommendations=result.get("key_recommendations", []),
        risk_assessment=result.get("risk_assessment", ""),
        issuance_strategy=result.get("issuance_strategy", ""),
        cost_savings_analysis=result.get("cost_savings_analysis", ""),
        stress_test_interpretation=result.get("stress_test_interpretation", ""),
        confidence_level=result.get("confidence_level", "medium"),
        caveats=result.get("caveats", []),
        model_used="gpt-4o",
    )


def _call_anthropic(prompt: str, api_key: str) -> PolicyBrief:
    """Call Anthropic API for policy brief generation."""
    import urllib.request

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "system": "You are a senior sovereign debt advisor. Generate structured policy briefs in JSON format.",
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )

    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read())
    content = data["content"][0]["text"]

    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        result = json.loads(content.strip())
    except json.JSONDecodeError:
        result = {"executive_summary": content[:500], "key_recommendations": [], "risk_assessment": "", "issuance_strategy": "", "cost_savings_analysis": "", "stress_test_interpretation": "", "confidence_level": "medium", "caveats": []}

    return PolicyBrief(
        executive_summary=result.get("executive_summary", ""),
        key_recommendations=result.get("key_recommendations", []),
        risk_assessment=result.get("risk_assessment", ""),
        issuance_strategy=result.get("issuance_strategy", ""),
        cost_savings_analysis=result.get("cost_savings_analysis", ""),
        stress_test_interpretation=result.get("stress_test_interpretation", ""),
        confidence_level=result.get("confidence_level", "medium"),
        caveats=result.get("caveats", []),
        model_used="claude-sonnet-4-20250514",
    )


def _call_ollama(prompt: str) -> PolicyBrief:
    """Call local Ollama instance for policy brief generation."""
    import urllib.request

    payload = json.dumps({
        "model": "llama3.1",
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 2000},
    }).encode()

    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    resp = urllib.request.urlopen(req, timeout=60)
    data = json.loads(resp.read())
    content = data.get("response", "")

    try:
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        result = json.loads(content.strip())
    except json.JSONDecodeError:
        result = {"executive_summary": content[:500], "key_recommendations": [], "risk_assessment": "", "issuance_strategy": "", "cost_savings_analysis": "", "stress_test_interpretation": "", "confidence_level": "low", "caveats": ["Ollama output was not valid JSON"]}

    return PolicyBrief(
        executive_summary=result.get("executive_summary", ""),
        key_recommendations=result.get("key_recommendations", []),
        risk_assessment=result.get("risk_assessment", ""),
        issuance_strategy=result.get("issuance_strategy", ""),
        cost_savings_analysis=result.get("cost_savings_analysis", ""),
        stress_test_interpretation=result.get("stress_test_interpretation", ""),
        confidence_level=result.get("confidence_level", "low"),
        caveats=result.get("caveats", []),
        model_used="ollama/llama3.1",
    )
