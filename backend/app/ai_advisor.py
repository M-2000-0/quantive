"""AI Debt Advisor Co-pilot.

A conversational AI that answers sovereign debt management questions
using Quantive's data engines. No external API keys required — uses
rule-based intelligence with quantitative backing.

Capabilities:
- Market timing advice ("Should we issue a 10Y bond now?")
- Country comparison ("How does our debt compare to Brazil?")
- Risk analysis ("What's our exposure to rate hikes?")
- Strategy recommendations ("What's the best tenor mix?")
- What-if scenarios ("What if we swap 30% USD to EUR?")
- Yield curve analysis ("Is the curve inverted? What does it mean?")
- Peer benchmarking ("Are we above or below median for our rating?")
"""

from __future__ import annotations

from typing import Optional

from app.country_data import compare_countries, get_country, get_peer_group
from app.market_data.cache import MarketDataCache
from app.narrative_engine import MarketContext


class DebtAdvisorAI:
    """Rule-based sovereign debt advisor with quantitative backing.

    This is a sophisticated pattern-matching system that understands
    debt management questions and provides data-backed answers.
    """

    def __init__(self):
        self.market_cache = MarketDataCache()

    def answer(self, question: str, country_code: str = "US", context: Optional[dict] = None) -> dict:
        """Answer a sovereign debt question.

        Returns:
            {
                "answer": "markdown-formatted answer",
                "data": {...},  // supporting data
                "confidence": 0.0-1.0,
                "sources": ["country_data", "market_data", "risk_engine"],
                "suggestions": ["related question 1", "related question 2"]
            }
        """
        q = question.lower().strip()

        # Route to the right handler
        if any(w in q for w in ["should we issue", "issuance", "borrow", "new bond", "timing"]):
            return self._issue_timing(q, country_code)
        elif any(w in q for w in ["compare", "comparison", "peer", "versus", "vs", "how do we stack"]):
            return self._country_comparison(q, country_code)
        elif any(w in q for w in ["risk", "exposure", "vulnerable", "hedge", "danger"]):
            return self._risk_analysis(q, country_code, context)
        elif any(w in q for w in ["tenor", "maturity", "duration", "how long"]):
            return self._tenor_advice(q, country_code)
        elif any(w in q for w in ["yield curve", "curve", "inverted", "spread", "2s10s"]):
            return self._yield_curve_analysis(q, country_code)
        elif any(w in q for w in ["currency", "fx", "exchange", "dollar", "eur", "gbp"]):
            return self._currency_advice(q, country_code)
        elif any(w in q for w in ["cost", "cheapest", "rate", "coupon", "interest"]):
            return self._cost_analysis(q, country_code, context)
        elif any(w in q for w in ["what if", "scenario", "simulate", "impact"]):
            return self._whatif_scenario(q, country_code, context)
        elif any(w in q for w in ["rating", "credit", "upgrade", "downgrade"]):
            return self._rating_analysis(q, country_code)
        elif any(w in q for w in ["inflation", "cpi", "prices"]):
            return self._inflation_analysis(q, country_code)
        elif any(w in q for w in ["fiscal", "deficit", "surplus", "budget"]):
            return self._fiscal_analysis(q, country_code)
        elif any(w in q for w in ["hello", "hi", "help", "what can you"]):
            return self._greeting()
        else:
            return self._general_advice(q, country_code)

    def _issue_timing(self, q: str, country_code: str) -> dict:
        """Advise on bond issuance timing."""
        country = get_country(country_code)
        if not country:
            return {"answer": "Country data not available.", "confidence": 0.0}

        # Get market context
        market = self._get_market_context()

        # Analyze conditions
        factors = []
        score = 50  # neutral

        # Yield curve analysis
        spread = market.us_10y_yield - market.us_2y_yield
        if spread < 0:
            factors.append(("negative", f"The yield curve is inverted ({spread:+.0f}bps), suggesting near-term uncertainty. Consider shorter tenors."))
            score -= 10
        else:
            factors.append(("positive", f"The yield curve is normal ({spread:+.0f}bps), supporting traditional maturity extension."))

        # VIX analysis
        if market.vix > 25:
            factors.append(("negative", f"VIX at {market.vix:.1f} indicates elevated volatility. Consider waiting for calmer markets."))
            score -= 15
        elif market.vix < 15:
            factors.append(("positive", f"VIX at {market.vix:.1f} is low — favorable issuance window."))
            score += 15
        else:
            factors.append(("neutral", f"VIX at {market.vix:.1f} is moderate — proceed with standard hedging."))

        # Country-specific
        if country.debt_to_gdp > 100:
            factors.append(("warning", f"Debt-to-GDP at {country.debt_to_gdp:.0f}% is elevated. Market may demand higher spreads."))
            score -= 5

        if country.avg_maturity_years < 5:
            factors.append(("warning", f"Average maturity is only {country.avg_maturity_years:.1f} years — consider extending to reduce refinancing risk."))
        elif country.avg_maturity_years > 8:
            factors.append(("positive", f"Average maturity of {country.avg_maturity_years:.1f} years provides good refinancing stability."))

        # Recommendation
        if score >= 65:
            recommendation = "**Strongly favorable** conditions for issuance. We recommend proceeding with a planned issuance."
        elif score >= 45:
            recommendation = "**Moderately favorable** conditions. Proceed with standard market timing and hedging."
        else:
            recommendation = "**Challenging** conditions. Consider delaying non-urgent issuances or using shorter tenors."

        factors_text = "\n".join(f"- {'✅' if t == 'positive' else '⚠️' if t == 'warning' else '❌' if t == 'negative' else '📊'} {msg}" for t, msg in factors)

        return {
            "answer": (
                f"## Bond Issuance Timing Analysis — {country.name}\n\n"
                f"**Overall Assessment:** {recommendation}\n\n"
                f"**Market Factors:**\n{factors_text}\n\n"
                f"**Current Rates:**\n"
                f"- US 10Y: {market.us_10y_yield:.2f}%\n"
                f"- US 2Y: {market.us_2y_yield:.2f}%\n"
                f"- SOFR: {market.sofr_rate:.2f}%\n"
                f"- 2s10s Spread: {spread:+.0f} bps\n\n"
                f"**Timing Score:** {score}/100\n\n"
                f"{'💡 **Tip:** Consider issuing in the next 2-4 weeks while conditions are favorable.' if score >= 60 else '💡 **Tip:** Monitor VIX and yield curve for a better window.' if score >= 40 else '💡 **Tip:** Consider bridging with short-term T-bills until conditions improve.'}"
            ),
            "data": {"score": score, "factors": [(t, m) for t, m in factors], "market": {"vix": market.vix, "us_10y": market.us_10y_yield, "spread": spread}},
            "confidence": 0.85 if score >= 60 or score <= 40 else 0.70,
            "sources": ["market_data", "country_data"],
            "suggestions": [
                f"What's the optimal tenor for a {country.name} issuance?",
                f"How does {country.name}'s borrowing cost compare to peers?",
                "What's the risk of issuing in current market conditions?",
            ],
        }

    def _country_comparison(self, q: str, country_code: str) -> dict:
        """Compare a country with peers."""
        country = get_country(country_code)
        if not country:
            return {"answer": "Country data not available.", "confidence": 0.0}

        peers = get_peer_group(country_code)
        all_codes = [country_code] + [p.code for p in peers[:5]]
        comparison = compare_countries(all_codes)

        peer_table = "| Country | Rating | Debt/GDP | Growth | Inflation |\n|---------|--------|----------|--------|----------|\n"
        for p in comparison["countries"]:
            marker = " ◄" if p["code"] == country_code else ""
            r = p["ratings"]
            e = p["economy"]
            peer_table += f"| {p['name']}{marker} | {r['sp']} | {p['debt_metrics']['debt_to_gdp']:.0f}% | {e['gdp_growth_pct']:.1f}% | {e['inflation_pct']:.1f}% |\n"

        avg = comparison["averages"]
        best = comparison["best_in_class"]

        return {
            "answer": (
                f"## {country.name} — Peer Comparison\n\n"
                f"{peer_table}\n"
                f"**Peer Averages:** Debt/GDP {avg['debt_to_gdp']:.0f}%, Growth {avg['gdp_growth_pct']:.1f}%, Inflation {avg['inflation_pct']:.1f}%\n\n"
                f"**Best in Class:**\n"
                f"- Lowest Debt: {best['lowest_debt']}\n"
                f"- Strongest Growth: {best['strongest_growth']}\n"
                f"- Lowest Inflation: {best['lowest_inflation']}\n\n"
                f"**{country.name} Position:** "
                f"{'Above average on debt-to-GDP — fiscal consolidation recommended.' if country.debt_to_gdp > avg['debt_to_gdp'] else 'Below average on debt-to-GDP — fiscal space available.'}"
            ),
            "data": comparison,
            "confidence": 0.95,
            "sources": ["country_data"],
            "suggestions": [
                f"What should {country.name} do to improve its credit rating?",
                f"How does {country.name}'s debt maturity compare to peers?",
                f"What's the outlook for {country.name}'s fiscal position?",
            ],
        }

    def _risk_analysis(self, q: str, country_code: str, context: Optional[dict] = None) -> dict:
        """Analyze portfolio risks."""
        country = get_country(country_code)
        if not country:
            return {"answer": "Country data not available.", "confidence": 0.0}

        market = self._get_market_context()

        risks = []
        if country.interest_to_revenue > 10:
            risks.append(("high", "Interest payments consume >10% of revenue — limited fiscal space"))
        if country.fiscal_balance_pct < -5:
            risks.append(("high", f"Fiscal deficit of {abs(country.fiscal_balance_pct):.1f}% of GDP is unsustainable"))
        if country.debt_to_gdp > 100:
            risks.append(("medium", f"Debt-to-GDP at {country.debt_to_gdp:.0f}% limits borrowing capacity"))
        if country.foreign_held_pct > 40:
            risks.append(("medium", f"High foreign investor exposure ({country.foreign_held_pct:.0f}%) creates flight risk"))
        if country.current_account_pct < -3:
            risks.append(("medium", f"Current account deficit of {abs(country.current_account_pct):.1f}% pressures FX"))
        if market.vix > 20:
            risks.append(("low", f"Elevated market volatility (VIX {market.vix:.1f}) may widen spreads"))

        risk_text = "\n".join(f"- {'🔴' if s == 'high' else '🟡' if s == 'medium' else '🟢'} {msg}" for s, msg in risks) if risks else "- No significant risks identified"

        return {
            "answer": (
                f"## Risk Analysis — {country.name}\n\n"
                f"**Key Risks:**\n{risk_text}\n\n"
                f"**Credit Ratings:** S&P {country.rating_sp} / Moody's {country.rating_moody} / Fitch {country.rating_fitch} ({country.rating_outlook})\n\n"
                f"**Debt Metrics:**\n"
                f"- Debt/GDP: {country.debt_to_gdp:.0f}%\n"
                f"- Interest/Revenue: {country.interest_to_revenue:.1f}%\n"
                f"- Debt Service/Revenue: {country.debt_service_to_revenue:.1f}%\n\n"
                f"**Recommendation:** {'Immediate fiscal consolidation needed.' if any(s == 'high' for s, _ in risks) else 'Monitor key indicators and maintain buffers.' if risks else 'Risk profile is well-managed.'}"
            ),
            "data": {"risks": risks, "country": country.to_dict()},
            "confidence": 0.80,
            "sources": ["country_data", "market_data"],
            "suggestions": [
                f"What's the optimal debt strategy for {country.name}?",
                f"How does {country.name}'s risk profile compare to peers?",
                f"What stress scenarios should {country.name} prepare for?",
            ],
        }

    def _tenor_advice(self, q: str, country_code: str) -> dict:
        """Advise on optimal tenor/maturity mix."""
        country = get_country(country_code)
        if not country:
            return {"answer": "Country data not available.", "confidence": 0.0}

        market = self._get_market_context()
        spread = market.us_10y_yield - market.us_2y_yield

        if country.avg_maturity_years < 4:
            recommendation = "Extend maturity aggressively. Current short average creates high refinancing risk."
        elif country.avg_maturity_years < 6:
            recommendation = "Maintain current maturity profile. Consider modest extension."
        elif country.avg_maturity_years < 10:
            recommendation = "Good maturity profile. Focus on cost optimization across tenors."
        else:
            recommendation = "Long maturity profile provides stability. Ensure coupon cost is competitive."

        return {
            "answer": (
                f"## Tenor/Maturity Advice — {country.name}\n\n"
                f"**Current:** Average maturity of {country.avg_maturity_years:.1f} years\n\n"
                f"**Recommendation:** {recommendation}\n\n"
                f"**Yield Curve Context:**\n"
                f"- 2s10s spread: {spread:+.0f} bps ({'normal' if spread > 0 else 'inverted'})\n"
                f"- Short end ({market.us_2y_yield:.2f}%) {'expensive' if market.us_2y_yield > 4.5 else 'reasonable'}\n"
                f"- Long end ({market.us_10y_yield:.2f}%) {'attractive for locking in' if market.us_10y_yield < 4.5 else 'elevated — consider shorter tenors'}\n\n"
                f"**Suggested Mix:**\n"
                f"- Short (1-3Y): 20-30% for liquidity\n"
                f"- Medium (5-7Y): 40-50% for balance\n"
                f"- Long (10Y+): 20-30% for stability"
            ),
            "data": {"avg_maturity": country.avg_maturity_years, "spread": spread},
            "confidence": 0.75,
            "sources": ["country_data", "market_data"],
            "suggestions": [
                "Should we issue a long bond now?",
                "How does our maturity compare to AAA-rated sovereigns?",
                "What's the cost impact of extending maturity by 2 years?",
            ],
        }

    def _yield_curve_analysis(self, q: str, country_code: str) -> dict:
        """Analyze yield curve conditions."""
        market = self._get_market_context()
        spread = market.us_10y_yield - market.us_2y_yield

        if spread < 0:
            curve_status = "inverted"
            meaning = "An inverted yield curve historically signals recession risk within 12-18 months. Consider shorter-dated issuances and building liquidity buffers."
        elif spread < 50:
            curve_status = "flat"
            meaning = "A flat yield curve suggests uncertainty about the economic outlook. Balanced tenor strategy recommended."
        else:
            curve_status = "normal/upward sloping"
            meaning = "A normal yield curve supports traditional debt management strategies. Long-dated issuances offer term premium."

        return {
            "answer": (
                f"## Yield Curve Analysis\n\n"
                f"**Status:** The US yield curve is **{curve_status}** (2s10s spread: {spread:+.0f} bps)\n\n"
                f"**What This Means:** {meaning}\n\n"
                f"**Key Rates:**\n"
                f"- 2Y: {market.us_2y_yield:.2f}%\n"
                f"- 10Y: {market.us_10y_yield:.2f}%\n"
                f"- 30Y: {market.us_10y_yield + 0.4:.2f}% (estimated)\n"
                f"- SOFR: {market.sofr_rate:.2f}%\n\n"
                f"**Debt Management Implications:**\n"
                f"- {'Favor long-dated issuances to lock in rates' if spread > 50 else 'Consider shorter maturities until curve normalizes' if spread > 0 else 'Minimize duration exposure; focus on floating/short-term'}"
            ),
            "data": {"spread": spread, "status": curve_status, "rates": {"2y": market.us_2y_yield, "10y": market.us_10y_yield}},
            "confidence": 0.90,
            "sources": ["market_data"],
            "suggestions": [
                "What's the forecast for the yield curve over the next 6 months?",
                "Should we extend duration given current curve conditions?",
                "How does the curve affect our refinancing risk?",
            ],
        }

    def _currency_advice(self, q: str, country_code: str) -> dict:
        """Advise on currency mix."""
        country = get_country(country_code)
        if not country:
            return {"answer": "Country data not available.", "confidence": 0.0}
        market = self._get_market_context()

        return {
            "answer": (
                f"## Currency Mix Advice — {country.name}\n\n"
                f"**Current:** {country.currency} as primary denomination\n"
                f"**Foreign Held:** {country.foreign_held_pct:.0f}% of total debt\n"
                f"**External Debt:** ${country.external_debt_usd_trillions:.1f}T ({country.external_debt_to_gdp:.0f}% of GDP)\n\n"
                f"**Recommendation:**\n"
                f"- {'Consider reducing foreign currency exposure if not backed by matching revenue' if country.foreign_held_pct > 40 else 'Foreign currency exposure is manageable'}\n"
                f"- {'Dollar strength supports USD issuance' if market.us_10y_yield > 4 else 'Consider diversifying across currencies'}\n"
                f"- Maintain FX hedging for 30-50% of foreign exposure"
            ),
            "data": {"foreign_held": country.foreign_held_pct, "external_debt": country.external_debt_to_gdp},
            "confidence": 0.70,
            "sources": ["country_data", "market_data"],
            "suggestions": [
                "What's the optimal currency split for our portfolio?",
                "How does FX risk affect our overall debt cost?",
                "Should we issue in local or foreign currency?",
            ],
        }

    def _cost_analysis(self, q: str, country_code: str, context: Optional[dict] = None) -> dict:
        """Analyze borrowing costs."""
        country = get_country(country_code)
        if not country:
            return {"answer": "Country data not available.", "confidence": 0.0}
        market = self._get_market_context()

        return {
            "answer": (
                f"## Cost Analysis — {country.name}\n\n"
                f"**Current Borrowing Costs:**\n"
                f"- Weighted Average Coupon: {country.avg_coupon_pct:.2f}%\n"
                f"- Interest/Revenue: {country.interest_to_revenue:.1f}%\n"
                f"- Debt Service/Revenue: {country.debt_service_to_revenue:.1f}%\n\n"
                f"**Benchmark Rates:**\n"
                f"- US 10Y: {market.us_10y_yield:.2f}%\n"
                f"- SOFR: {market.sofr_rate:.2f}%\n\n"
                f"**Cost Optimization Opportunities:**\n"
                f"{'- High coupon burden — consider refinancing at current rates' if country.avg_coupon_pct > 5 else '- Coupon costs are reasonable'}\n"
                f"{'- Short average maturity creates frequent refinancing costs' if country.avg_maturity_years < 5 else '- Long maturity reduces rollover costs'}"
            ),
            "data": {"avg_coupon": country.avg_coupon_pct, "interest_to_revenue": country.interest_to_revenue},
            "confidence": 0.80,
            "sources": ["country_data", "market_data"],
            "suggestions": [
                "How much could we save by refinancing?",
                "What's the cheapest tenor to issue at right now?",
                "Compare our borrowing cost to peer sovereigns",
            ],
        }

    def _whatif_scenario(self, q: str, country_code: str, context: Optional[dict] = None) -> dict:
        """Run what-if scenarios."""
        country = get_country(country_code)
        if not country:
            return {"answer": "Country data not available.", "confidence": 0.0}
        market = self._get_market_context()

        return {
            "answer": (
                f"## What-If Scenario — {country.name}\n\n"
                f"To run a detailed what-if analysis, use the **What-If Playground** with specific adjustments.\n\n"
                f"**Quick Scenarios to Consider:**\n"
                f"1. Issue 10Y bond at current 10Y rate ({market.us_10y_yield:.2f}%)\n"
                f"2. Extend average maturity by 2 years\n"
                f"3. Reduce foreign currency exposure by 10%\n"
                f"4. Refinance short-term debt with 5Y bonds\n\n"
                f"**For detailed analysis, visit the What-If Playground** and add specific adjustments."
            ),
            "data": {},
            "confidence": 0.60,
            "sources": ["country_data", "market_data"],
            "suggestions": [
                "What's the impact of issuing $5B in new 10Y bonds?",
                "How would a 200bps rate hike affect our debt service?",
                "Compare issuing in USD vs EUR",
            ],
        }

    def _rating_analysis(self, q: str, country_code: str) -> dict:
        """Analyze credit rating implications."""
        country = get_country(country_code)
        if not country:
            return {"answer": "Country data not available.", "confidence": 0.0}

        ig_order = ["BBB-", "BBB", "BBB+", "A-", "A", "A+", "AA-", "AA", "AA+", "AAA"]
        current_idx = ig_order.index(country.rating_sp) if country.rating_sp in ig_order else -1

        return {
            "answer": (
                f"## Credit Rating Analysis — {country.name}\n\n"
                f"**Current Ratings:**\n"
                f"- S&P: {country.rating_sp} ({country.rating_outlook})\n"
                f"- Moody's: {country.rating_moody}\n"
                f"- Fitch: {country.rating_fitch}\n\n"
                f"**Rating Position:** {current_idx + 1}/{len(ig_order)} in investment-grade scale\n\n"
                f"**Factors for Potential Upgrade:**\n"
                f"{'- Reduce fiscal deficit below 3% of GDP' if country.fiscal_balance_pct < -3 else '- Maintain fiscal discipline'}\n"
                f"{'- Reduce debt-to-GDP below 80%' if country.debt_to_gdp > 80 else '- Debt level is sustainable'}\n"
                f"{'- Strengthen growth outlook' if country.gdp_growth_pct < 2 else '- Growth outlook is positive'}\n\n"
                f"**Rating Outlook:** {country.rating_outlook.title()}"
            ),
            "data": {"rating": country.rating_sp, "outlook": country.rating_outlook},
            "confidence": 0.70,
            "sources": ["country_data"],
            "suggestions": [
                "What would it take to reach AA+?",
                "How does our rating compare to regional peers?",
                "What's the spread impact of a one-notch downgrade?",
            ],
        }

    def _inflation_analysis(self, q: str, country_code: str) -> dict:
        """Analyze inflation impact on debt."""
        country = get_country(country_code)
        if not country:
            return {"answer": "Country data not available.", "confidence": 0.0}

        market = self._get_market_context()

        return {
            "answer": (
                f"## Inflation Analysis — {country.name}\n\n"
                f"**Current Inflation:** {country.inflation_pct:.1f}%\n"
                f"**Trend:** {market.inflation_trend.title()}\n\n"
                f"**Impact on Debt:**\n"
                f"- {'Inflation erodes real debt burden — beneficial for nominal debt holders' if country.inflation_pct > 3 else 'Low inflation supports debt sustainability'}\n"
                f"- {'Consider inflation-linked bonds for hedging' if country.inflation_pct > 4 else 'Fixed-rate bonds are appropriate'}\n\n"
                f"**Real Interest Rate:** {market.us_10y_yield:.2f}% - {country.inflation_pct:.1f}% = {market.us_10y_yield - country.inflation_pct:.1f}%"
            ),
            "data": {"inflation": country.inflation_pct, "real_rate": market.us_10y_yield - country.inflation_pct},
            "confidence": 0.80,
            "sources": ["country_data", "market_data"],
            "suggestions": [
                "Should we issue inflation-linked bonds?",
                "How does inflation affect our debt sustainability?",
                "What's the breakeven inflation rate?",
            ],
        }

    def _fiscal_analysis(self, q: str, country_code: str) -> dict:
        """Analyze fiscal position."""
        country = get_country(country_code)
        if not country:
            return {"answer": "Country data not available.", "confidence": 0.0}

        return {
            "answer": (
                f"## Fiscal Analysis — {country.name}\n\n"
                f"**Fiscal Position:**\n"
                f"- Balance: {country.fiscal_balance_pct:+.1f}% of GDP\n"
                f"- Primary Balance: {country.primary_balance_pct:+.1f}% of GDP\n"
                f"- Revenue: {country.revenue_to_gdp:.1f}% of GDP\n"
                f"- Expenditure: {country.expenditure_to_gdp:.1f}% of GDP\n\n"
                f"**Assessment:** {'Fiscal position is strained — consolidation needed.' if country.fiscal_balance_pct < -4 else 'Fiscal position is manageable.' if country.fiscal_balance_pct < -2 else 'Fiscal position is strong.'}\n\n"
                f"**Recommendation:** {'Prioritize deficit reduction through spending restraint or revenue enhancement.' if country.fiscal_balance_pct < -3 else 'Maintain fiscal discipline while supporting growth.'}"
            ),
            "data": {"fiscal_balance": country.fiscal_balance_pct, "primary_balance": country.primary_balance_pct},
            "confidence": 0.85,
            "sources": ["country_data"],
            "suggestions": [
                "What's the optimal fiscal consolidation path?",
                "How does our fiscal position compare to peers?",
                "What's the debt sustainability outlook?",
            ],
        }

    def _greeting(self) -> dict:
        """Handle greetings."""
        return {
            "answer": (
                "## 👋 Welcome to Quantive AI Advisor\n\n"
                "I'm your sovereign debt management advisor. I can help with:\n\n"
                "**Market Timing:**\n"
                "- \"Should we issue a bond now?\"\n"
                "- \"Is the yield curve favorable for borrowing?\"\n\n"
                "**Risk Analysis:**\n"
                "- \"What are our main debt risks?\"\n"
                "- \"How exposed are we to rate hikes?\"\n\n"
                "**Peer Comparison:**\n"
                "- \"How does our debt compare to Brazil?\"\n"
                "- \"Are we above median for our rating?\"\n\n"
                "**Strategy:**\n"
                "- \"What's the optimal tenor mix?\"\n"
                "- \"Should we issue in USD or EUR?\"\n\n"
                "**Ask me anything about sovereign debt management!**"
            ),
            "data": {},
            "confidence": 1.0,
            "sources": [],
            "suggestions": [
                "Should we issue a 10Y bond now?",
                "How does our debt compare to G7 peers?",
                "What's our biggest risk right now?",
            ],
        }

    def _general_advice(self, q: str, country_code: str) -> dict:
        """Handle general questions."""
        country = get_country(country_code)
        name = country.name if country else "this sovereign"

        return {
            "answer": (
                f"I can help with sovereign debt management questions about {name}. "
                f"Try asking about:\n\n"
                f"- **Issuance timing** — \"Should we issue now?\"\n"
                f"- **Risk analysis** — \"What are our risks?\"\n"
                f"- **Peer comparison** — \"Compare us to G7\"\n"
                f"- **Tenor advice** — \"What maturity should we target?\"\n"
                f"- **Currency mix** — \"USD vs EUR issuance?\"\n"
                f"- **Credit rating** — \"What affects our rating?\"\n"
                f"- **Fiscal position** — \"How's our fiscal health?\"\n"
            ),
            "data": {},
            "confidence": 0.50,
            "sources": [],
            "suggestions": [
                "Should we issue a bond now?",
                "What's our biggest risk?",
                "Compare us to peer sovereigns",
            ],
        }

    def _get_market_context(self) -> MarketContext:
        """Get current market context."""
        try:
            data = self.market_cache.get("yield_curve")
            if data:
                return MarketContext(
                    us_10y_yield=data.get("maturities", [{}])[6].get("rate_pct", 4.3) if len(data.get("maturities", [])) > 6 else 4.3,
                    us_2y_yield=data.get("maturities", [{}])[2].get("rate_pct", 4.15) if len(data.get("maturities", [])) > 2 else 4.15,
                )
        except Exception:
            pass
        return MarketContext()
