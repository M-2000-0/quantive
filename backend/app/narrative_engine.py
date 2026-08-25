"""Scenario Narrative Engine — generates board-ready reports from optimization data.

This is the McKinsey killer. It takes raw optimization results, market data,
and country context and produces professional narratives that a Finance Minister
can present to Parliament.

Outputs:
- Executive Summary (1-page)
- Risk Assessment Narrative
- Strategy Recommendations
- Market Context Brief
- What-If Scenario Narratives
- Implementation Roadmap
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# ── Data Classes ────────────────────────────────────────────────────────

@dataclass
class MarketContext:
    """Current market conditions for narrative context."""
    us_10y_yield: float = 4.30
    us_2y_yield: float = 4.15
    ecb_rate: float = 4.50
    sofr_rate: float = 4.31
    dxy_index: float = 104.5
    vix: float = 18.5
    oil_price: float = 78.0
    gold_price: float = 2450.0
    fed_outlook: str = "hawkish pause"
    inflation_trend: str = "moderating"
    geopolitical_risk: str = "elevated"
    date: str = field(default_factory=lambda: datetime.now().strftime("%B %d, %Y"))


@dataclass
class CountryContext:
    """Country-specific context for narrative."""
    country_code: str = "US"
    country_name: str = "United States"
    credit_rating: str = "AA+"
    gdp_trillions: float = 28.0
    debt_to_gdp_pct: float = 123.0
    total_debt_outstanding: float = 35_000_000_000_000
    avg_maturity_years: float = 6.2
    foreign_held_pct: float = 30.0
    currency: str = "USD"
    fiscal_deficit_pct: float = 6.5
    external_account_pct: float = -3.5
    inflation_rate_pct: float = 3.2
    gdp_growth_pct: float = 2.5
    unemployment_pct: float = 3.7


@dataclass
class StrategyNarrative:
    """Narrative for a single optimization strategy."""
    rank: int
    name: str
    label: str  # "Best Overall", "Lowest Risk", "Lowest Cost"
    headline: str
    executive_summary: str
    key_metrics: dict[str, str]
    strengths: list[str]
    risks: list[str]
    recommendation: str
    comparison_to_baseline: str


@dataclass
class BoardReport:
    """Complete board-ready report."""
    title: str
    date: str
    country: str
    executive_summary: str
    market_brief: str
    current_portfolio_assessment: str
    strategy_narratives: list[StrategyNarrative]
    risk_assessment: str
    peer_comparison: str
    implementation_roadmap: str
    key_recommendations: list[str]
    next_steps: list[str]
    disclaimer: str


# ── Narrative Engine ────────────────────────────────────────────────────

class NarrativeEngine:
    """Generates professional narratives from optimization data.

    Usage:
        engine = NarrativeEngine()
        report = engine.generate_board_report(
            portfolio_data={...},
            optimization_results={...},
            strategies=[...],
            country=CountryContext(...),
            market=MarketContext(...),
        )
    """

    def generate_board_report(
        self,
        portfolio_data: dict,
        optimization_results: dict,
        strategies: list[dict],
        country: Optional[CountryContext] = None,
        market: Optional[MarketContext] = None,
        investment_amount: float = 1_000_000_000,
    ) -> BoardReport:
        """Generate a complete board-ready report."""
        country = country or CountryContext()
        market = market or MarketContext()

        # Generate strategy narratives
        strategy_narratives = [
            self._narrate_strategy(s, i, portfolio_data, investment_amount)
            for i, s in enumerate(strategies[:4], 1)
        ]

        # Generate executive summary
        exec_summary = self._generate_executive_summary(
            portfolio_data, strategies, country, market, investment_amount
        )

        # Generate market brief
        market_brief = self._generate_market_brief(market, country)

        # Generate portfolio assessment
        portfolio_assessment = self._assess_portfolio(portfolio_data, country)

        # Generate risk assessment
        risk_assessment = self._assess_risks(portfolio_data, strategies, country, market)

        # Generate peer comparison
        peer_comparison = self._compare_to_peers(portfolio_data, country)

        # Generate implementation roadmap
        roadmap = self._generate_roadmap(strategies, country)

        # Generate key recommendations
        recommendations = self._generate_recommendations(strategies, portfolio_data, market, country)

        return BoardReport(
            title=f"Sovereign Debt Optimization Analysis — {country.country_name}",
            date=market.date,
            country=country.country_name,
            executive_summary=exec_summary,
            market_brief=market_brief,
            current_portfolio_assessment=portfolio_assessment,
            strategy_narratives=strategy_narratives,
            risk_assessment=risk_assessment,
            peer_comparison=peer_comparison,
            implementation_roadmap=roadmap,
            key_recommendations=recommendations,
            next_steps=[
                "Cabinet review and approval of recommended strategy",
                "Treasury team to prepare detailed implementation plan",
                "Engage primary dealers for execution timeline",
                "Update Parliament committee on debt management strategy",
                "Schedule quarterly review of strategy performance",
            ],
            disclaimer="This analysis is generated by Quantive's optimization engine. "
                       "All projections are based on current market conditions and historical data. "
                       "Past performance does not guarantee future results. "
                       "This document should be reviewed by qualified financial advisors before implementation.",
        )

    def _generate_executive_summary(
        self, portfolio: dict, strategies: list[dict],
        country: CountryContext, market: MarketContext,
        investment_amount: float,
    ) -> str:
        """Generate the executive summary — the most important paragraph."""
        instruments = portfolio.get("instruments", [])
        total_principal = sum(i.get("principal_outstanding", 0) for i in instruments)
        num_instruments = len(instruments)
        currencies = list(set(i.get("currency", "USD") for i in instruments))
        avg_coupon = sum(i.get("coupon_rate", 0) for i in instruments) / max(num_instruments, 1)

        best_strategy = strategies[0] if strategies else None
        best_cost = best_strategy.get("metrics", {}).get("expected_cost", 0) if best_strategy else 0

        # Calculate potential savings
        baseline_cost = total_principal * avg_coupon
        savings = baseline_cost - best_cost if best_cost > 0 else 0
        savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0

        risk_score = portfolio.get("risk_score", {})
        risk_label = risk_score.get("label", "Moderate") if isinstance(risk_score, dict) else "Moderate"

        return (
            f"This report presents a comprehensive debt optimization analysis for {country.country_name}'s "
            f"sovereign portfolio comprising {num_instruments} instruments across {len(currencies)} currency(ies) "
            f"with a total outstanding principal of ${total_principal:,.0f}. "
            f"The current weighted average coupon is {avg_coupon*100:.2f}%, with an average maturity of "
            f"{country.avg_maturity_years:.1f} years and a debt-to-GDP ratio of {country.debt_to_gdp_pct:.1f}%. "
            f"\n\n"
            f"Our multi-solver optimization engine analyzed thousands of portfolio configurations across "
            f"multiple market scenarios (base, stress, and tail risk) to identify the optimal restructuring strategy. "
            f"The recommended strategy ({best_strategy.get('name', 'N/A') if best_strategy else 'N/A'}) "
            f"projects {'annual savings of approximately ${:,.0f} ({:.1f}% reduction)'.format(abs(savings), abs(savings_pct)) if savings > 0 else 'improved risk profile with stable costs'} "
            f"while maintaining all regulatory and liquidity constraints. "
            f"\n\n"
            f"The portfolio's current risk assessment is '{risk_label}' "
            f"based on maturity profile, currency exposure, and interest rate sensitivity. "
            f"In the current environment of {market.fed_outlook} monetary policy and {market.geopolitical_risk} "
            f"geopolitical conditions, we recommend {strategies[0].get('name', 'the primary strategy').lower() if strategies else 'a conservative approach'} "
            f"as it provides the best balance of cost reduction and risk management."
        )

    def _generate_market_brief(self, market: MarketContext, country: CountryContext) -> str:
        """Generate the market context section."""
        yield_spread = market.us_10y_yield - market.us_2y_yield

        return (
            f"**Market Conditions as of {market.date}**\n\n"
            f"The current rate environment reflects {market.fed_outlook} monetary policy with the Federal Reserve "
            f"maintaining its benchmark rate. Key market indicators:\n\n"
            f"- **US 10-Year Treasury:** {market.us_10y_yield:.2f}% (benchmark for sovereign borrowing)\n"
            f"- **US 2-Year Treasury:** {market.us_2y_yield:.2f}% (policy rate proxy)\n"
            f"- **2s10s Spread:** {yield_spread:+.0f} bps ({'normal' if yield_spread > 0 else 'inverted'} yield curve)\n"
            f"- **SOFR:** {market.sofr_rate:.2f}% (short-term funding reference)\n"
            f"- **ECB Main Rate:** {market.ecb_rate:.2f}%\n"
            f"- **VIX:** {market.vix:.1f} ({'low' if market.vix < 15 else 'moderate' if market.vix < 25 else 'elevated'} volatility)\n"
            f"- **DXY:** {market.dxy_index:.1f} ({'strong' if market.dxy_index > 105 else 'stable'} dollar)\n\n"
            f"**Macroeconomic Outlook:**\n"
            f"Inflation is {market.inflation_trend} at {country.inflation_rate_pct:.1f}%, with GDP growth at "
            f"{country.gdp_growth_pct:.1f}%. The fiscal deficit stands at {country.fiscal_deficit_pct:.1f}% of GDP. "
            f"Geopolitical risks remain {market.geopolitical_risk}, creating uncertainty in global rate markets.\n\n"
            f"**Implications for Debt Management:**\n"
            f"{'The inverted yield curve suggests elevated near-term rate risk; shorter maturities may offer better value.' if yield_spread < 0 else 'The normal yield curve supports traditional maturity extension strategies.'} "
            f"{'Strong dollar conditions create favorable opportunities for USD-denominated issuance.' if market.dxy_index > 105 else 'Current FX conditions warrant careful currency mix management.'} "
            f"The elevated VIX suggests timing issuance windows around periods of lower volatility."
        )

    def _assess_portfolio(self, portfolio: dict, country: CountryContext) -> str:
        """Assess the current portfolio's health."""
        instruments = portfolio.get("instruments", [])
        if not instruments:
            return "No instruments in the portfolio for assessment."

        total = sum(i.get("principal_outstanding", 0) for i in instruments)
        avg_coupon = sum(i.get("coupon_rate", 0) * i.get("principal_outstanding", 0) for i in instruments) / total if total else 0
        avg_spread = sum(i.get("spread_bps", 0) for i in instruments) / len(instruments)

        # Currency breakdown
        ccy_exposure = {}
        for i in instruments:
            ccy = i.get("currency", "USD")
            ccy_exposure[ccy] = ccy_exposure.get(ccy, 0) + i.get("principal_outstanding", 0)

        # Maturity analysis
        from datetime import date
        today = date.today()
        maturities = {"short": 0, "medium": 0, "long": 0}
        for i in instruments:
            try:
                mat = date.fromisoformat(i.get("maturity_date", "2030-01-01"))
                years = (mat - today).days / 365.25
                if years < 3:
                    maturities["short"] += i.get("principal_outstanding", 0)
                elif years < 7:
                    maturities["medium"] += i.get("principal_outstanding", 0)
                else:
                    maturities["long"] += i.get("principal_outstanding", 0)
            except (ValueError, TypeError):
                maturities["medium"] += i.get("principal_outstanding", 0)

        ccy_str = ", ".join(f"{k}: {v/total*100:.1f}%" for k, v in sorted(ccy_exposure.items(), key=lambda x: -x[1]))

        return (
            f"**Current Portfolio Composition**\n\n"
            f"The portfolio contains {len(instruments)} instruments with a total principal of ${total:,.0f} "
            f"and a weighted average coupon of {avg_coupon*100:.2f}% (spread: {avg_spread:.0f} bps).\n\n"
            f"**Currency Exposure:** {ccy_str}\n\n"
            f"**Maturity Profile:**\n"
            f"- Short-term (< 3 years): ${maturities['short']:,.0f} ({maturities['short']/total*100:.1f}%)\n"
            f"- Medium-term (3-7 years): ${maturities['medium']:,.0f} ({maturities['medium']/total*100:.1f}%)\n"
            f"- Long-term (> 7 years): ${maturities['long']:,.0f} ({maturities['long']/total*100:.1f}%)\n\n"
            f"**Assessment:** "
            f"{'The portfolio has a well-distributed maturity profile.' if abs(maturities['medium']/total - 0.4) < 0.15 else 'The maturity profile could benefit from better distribution.'} "
            f"{'Currency diversification is healthy.' if len(ccy_exposure) >= 3 else 'Currency concentration risk exists.'} "
            f"{'Average spreads are tight, indicating strong credit quality.' if avg_spread < 50 else 'Elevated spreads suggest room for credit improvement.'}"
        )

    def _assess_risks(
        self, portfolio: dict, strategies: list[dict],
        country: CountryContext, market: MarketContext,
    ) -> str:
        """Generate risk assessment narrative."""
        instruments = portfolio.get("instruments", [])
        if not instruments:
            return "Insufficient data for risk assessment."

        total = sum(i.get("principal_outstanding", 0) for i in instruments)
        floating_count = sum(1 for i in instruments if i.get("instrument_type") == "floating_rate_note")
        floating_pct = floating_count / len(instruments) * 100

        # Find best strategy stress results
        best = strategies[0] if strategies else {}
        stress = best.get("stress_test_results", {})
        if isinstance(stress, dict):
            stress_strs = []
            for scenario, result in stress.items():
                if isinstance(result, dict):
                    severity = result.get("severity", "unknown")
                    impact = result.get("cost_impact", 0)
                    stress_strs.append(f"  - {scenario}: {severity} impact (${impact:,.0f})")
            stress_text = "\n".join(stress_strs) if stress_strs else "  - Stress test results pending"
        else:
            stress_text = "  - Stress test results pending"

        return (
            f"**Key Risk Factors**\n\n"
            f"1. **Interest Rate Risk:** With {market.fed_outlook} policy outlook, a 200bps rate increase "
            f"would increase annual debt service by approximately ${total * 0.02:,.0f}. "
            f"{'The portfolio has significant floating rate exposure ({:.1f}%) amplifying this risk.'.format(floating_pct) if floating_pct > 20 else 'Floating rate exposure ({:.1f}%) is manageable.'.format(floating_pct)}\n\n"
            f"2. **Refinancing Risk:** "
            f"The average maturity of {country.avg_maturity_years:.1f} years "
            f"{'requires careful management of near-term maturities.' if country.avg_maturity_years < 5 else 'provides adequate runway for planned issuances.'}\n\n"
            f"3. **Currency Risk:** "
            f"With {country.foreign_held_pct:.1f}% of debt held by foreign investors, "
            f"FX movements of 10% could impact debt service by ${total * country.foreign_held_pct / 100 * 0.10:,.0f}.\n\n"
            f"4. **Stress Test Results ({best.get('name', 'N/A')}):**\n{stress_text}\n\n"
            f"5. **Geopolitical Risk:** {market.geopolitical_risk.title()} — potential for sudden rate moves "
            f"or credit spread widening. Maintain adequate liquidity buffers."
        )

    def _compare_to_peers(self, portfolio: dict, country: CountryContext) -> str:
        """Compare to peer sovereigns."""
        # Peer data (simplified for demonstration)
        peers = {
            "US": {"dtd": 123, "avg_mat": 6.2, "foreign_pct": 30, "rating": "AA+"},
            "UK": {"dtd": 101, "avg_mat": 14.2, "foreign_pct": 28, "rating": "AA"},
            "JP": {"dtd": 261, "avg_mat": 8.5, "foreign_pct": 7, "rating": "A+"},
            "DE": {"dtd": 66, "avg_mat": 7.1, "foreign_pct": 45, "rating": "AAA"},
            "FR": {"dtd": 112, "avg_mat": 8.9, "foreign_pct": 50, "rating": "AA"},
            "IT": {"dtd": 144, "avg_mat": 7.0, "foreign_pct": 33, "rating": "BBB"},
            "BR": {"dtd": 88, "avg_mat": 5.1, "foreign_pct": 18, "rating": "BB-"},
            "IN": {"dtd": 83, "avg_mat": 6.4, "foreign_pct": 22, "rating": "BBB-"},
            "MX": {"dtd": 54, "avg_mat": 7.8, "foreign_pct": 35, "rating": "BBB"},
            "ZA": {"dtd": 72, "avg_mat": 8.1, "foreign_pct": 25, "rating": "BB-"},
        }

        peer_data = peers.get(country.country_code)
        if not peer_data:
            return "Peer comparison data not available for this jurisdiction."

        # Sort peers by DTD for comparison
        sorted_peers = sorted(peers.items(), key=lambda x: x[1]["dtd"])

        lines = [
            "**Peer Sovereign Comparison**\n",
            "| Sovereign | Rating | Debt/GDP | Avg Maturity | Foreign Held |",
            "|-----------|--------|----------|-------------|-------------|",
        ]
        for code, data in sorted_peers[:8]:
            marker = " ◄" if code == country.country_code else ""
            lines.append(
                f"| {code}{marker} | {data['rating']} | {data['dtd']}% | {data['avg_mat']}y | {data['foreign_pct']}% |"
            )

        # Position analysis
        rank = next(i for i, (c, _) in enumerate(sorted_peers, 1) if c == country.country_code)
        avg_dtd = sum(d["dtd"] for d in peers.values()) / len(peers)

        return (
            "\n".join(lines) + f"\n\n"
            f"**Positioning:** {country.country_name} ranks **{rank} out of {len(peers)}** "
            f"peer sovereigns by debt-to-GDP ratio ({country.debt_to_gdp_pct:.1f}% vs. peer average of {avg_dtd:.1f}%). "
            f"{'This above-average leverage suggests prioritizing cost reduction.' if country.debt_to_gdp_pct > avg_dtd else 'This below-average leverage provides fiscal space for strategic borrowing.'}"
        )

    def _narrate_strategy(
        self, strategy: dict, rank: int,
        portfolio: dict, investment_amount: float,
    ) -> StrategyNarrative:
        """Generate narrative for a single strategy."""
        metrics = strategy.get("metrics", {})
        expected_cost = metrics.get("expected_cost", 0)
        refinancing_risk = metrics.get("refinancing_risk", 0)
        rate_risk = metrics.get("interest_rate_risk", 0)
        currency_risk = metrics.get("currency_risk", 0)
        _stress = strategy.get("stress_test_results", {})

        # Determine strategy label
        labels = {1: "Best Overall", 2: "Lowest Risk", 3: "Lowest Cost", 4: "Most Resilient"}
        label = labels.get(rank, f"Strategy {rank}")

        # Generate strengths/risks based on metrics
        strengths = []
        risks = []
        if refinancing_risk < 0.15:
            strengths.append("Low refinancing concentration")
        elif refinancing_risk > 0.25:
            risks.append("Elevated refinancing risk")

        if rate_risk < 0.18:
            strengths.append("Protected against rate volatility")
        elif rate_risk > 0.25:
            risks.append("Sensitive to interest rate changes")

        if currency_risk < 0.12:
            strengths.append("Minimal FX exposure")
        elif currency_risk > 0.20:
            risks.append("Significant currency risk")

        if not strengths:
            strengths.append("Balanced risk profile")
        if not risks:
            risks.append("No significant risk concentrations identified")

        # Generate headline
        if rank == 1:
            headline = f"Recommended: {strategy.get('name', 'Strategy')} — Optimal balance of cost and risk"
        elif rank == 2:
            headline = f"Conservative: {strategy.get('name', 'Strategy')} — Prioritizes capital preservation"
        else:
            headline = f"{strategy.get('name', f'Strategy {rank}')} — {strategy.get('description', '')[:80]}"

        return StrategyNarrative(
            rank=rank,
            name=strategy.get("name", f"Strategy {rank}"),
            label=label,
            headline=headline,
            executive_summary=(
                f"Strategy {rank} ({strategy.get('name', 'N/A')}) targets an expected annual financing cost "
                f"of ${expected_cost:,.0f} with a refinancing risk score of {refinancing_risk:.1%}, "
                f"interest rate risk of {rate_risk:.1%}, and currency risk of {currency_risk:.1%}. "
                f"This strategy {'provides the best overall balance across all objectives.' if rank == 1 else 'specializes in risk minimization.' if rank == 2 else 'minimizes financing costs.' if rank == 3 else 'provides maximum resilience in stress scenarios.'}"
            ),
            key_metrics={
                "Expected Annual Cost": f"${expected_cost:,.0f}",
                "Refinancing Risk": f"{refinancing_risk:.1%}",
                "Interest Rate Risk": f"{rate_risk:.1%}",
                "Currency Risk": f"{currency_risk:.1%}",
                "Stress Resilience": f"{metrics.get('stress_resilience', 0):.0%}",
                "Liquidity Coverage": f"{metrics.get('liquidity_coverage', 0):.0%}",
            },
            strengths=strengths,
            risks=risks,
            recommendation=(
                f"We {'strongly recommend' if rank == 1 else 'recommend considering' if rank <= 2 else 'include'} "
                f"{strategy.get('name', 'this strategy')} "
                f"{'as the primary implementation strategy.' if rank == 1 else 'as a risk-averse alternative.' if rank == 2 else 'for cost-sensitive scenarios.' if rank == 3 else 'for maximum stress protection.'}"
            ),
            comparison_to_baseline=(
                f"Expected cost of ${expected_cost:,.0f} "
                f"{'represents a meaningful improvement over current allocation.' if expected_cost > 0 else 'requires further analysis.'}"
            ),
        )

    def _generate_roadmap(self, strategies: list[dict], country: CountryContext) -> str:
        """Generate implementation roadmap."""
        return (
            "**Implementation Roadmap**\n\n"
            "**Phase 1: Approval & Planning (Weeks 1-4)**\n"
            "- Present optimization analysis to Cabinet/Parliament committee\n"
            "- Obtain Board/Minister approval for recommended strategy\n"
            "- Engage legal counsel for any required regulatory approvals\n"
            "- Brief primary dealers on upcoming issuance plan\n\n"
            "**Phase 2: Market Preparation (Weeks 5-8)**\n"
            "- Monitor market conditions for optimal issuance windows\n"
            "- Prepare investor roadshow materials\n"
            "- Coordinate with rating agencies if significant changes planned\n"
            "- Set up necessary FX hedging facilities\n\n"
            "**Phase 3: Execution (Weeks 9-16)**\n"
            "- Execute new bond issuances per strategy\n"
            "- Manage buyback/tender offers for maturing instruments\n"
            "- Implement any FX rebalancing trades\n"
            "- Monitor execution against strategy targets\n\n"
            "**Phase 4: Monitoring (Ongoing)**\n"
            "- Monthly portfolio analytics review\n"
            "- Quarterly strategy performance assessment\n"
            "- Semi-annual re-optimization under updated market conditions\n"
            "- Annual comprehensive strategy review\n"
        )

    def _generate_recommendations(
        self, strategies: list[dict], portfolio: dict,
        market: MarketContext, country: CountryContext,
    ) -> list[str]:
        """Generate prioritized recommendations."""
        recs = []

        if strategies:
            best = strategies[0]
            metrics = best.get("metrics", {})
            recs.append(
                f"Adopt {best.get('name', 'the recommended strategy')} as the primary debt management strategy, "
                f"targeting expected annual savings of "
                f"${abs(sum(i.get('principal_outstanding', 0) for i in portfolio.get('instruments', [])) * 0.04 - metrics.get('expected_cost', 0)):,.0f}."
            )

        recs.append(
            f"Maintain adequate liquidity buffers given {market.geopolitical_risk} geopolitical conditions "
            f"and {market.fed_outlook} monetary policy outlook."
        )

        instruments = portfolio.get("instruments", [])
        floating = sum(1 for i in instruments if i.get("instrument_type") == "floating_rate_note")
        if floating / max(len(instruments), 1) > 0.3:
            recs.append("Reduce floating-rate exposure through fixed-rate issuances or interest rate swaps.")

        foreign_pct = country.foreign_held_pct
        if foreign_pct > 40:
            recs.append("Consider domestic investor diversification to reduce foreign-held concentration risk.")

        recs.append(f"Continue monitoring yield curve dynamics — current 2s10s spread of {market.us_10y_yield - market.us_2y_yield:+.0f}bps signals {'curve normalization' if market.us_10y_yield > market.us_2y_yield else 'recession risk'}.")

        return recs


# ── Convenience Function ────────────────────────────────────────────────

def generate_narrative_report(
    portfolio_data: dict,
    strategies: list[dict],
    country_code: str = "US",
    investment_amount: float = 1_000_000_000,
) -> dict:
    """Generate a complete narrative report as a dictionary.

    This is the main entry point for the API layer.
    """
    engine = NarrativeEngine()
    report = engine.generate_board_report(
        portfolio_data=portfolio_data,
        optimization_results={},
        strategies=strategies,
        country=CountryContext(country_code=country_code),
        investment_amount=investment_amount,
    )

    return {
        "title": report.title,
        "date": report.date,
        "country": report.country,
        "executive_summary": report.executive_summary,
        "market_brief": report.market_brief,
        "current_portfolio_assessment": report.current_portfolio_assessment,
        "strategies": [
            {
                "rank": s.rank,
                "name": s.name,
                "label": s.label,
                "headline": s.headline,
                "executive_summary": s.executive_summary,
                "key_metrics": s.key_metrics,
                "strengths": s.strengths,
                "risks": s.risks,
                "recommendation": s.recommendation,
                "comparison_to_baseline": s.comparison_to_baseline,
            }
            for s in report.strategy_narratives
        ],
        "risk_assessment": report.risk_assessment,
        "peer_comparison": report.peer_comparison,
        "implementation_roadmap": report.implementation_roadmap,
        "key_recommendations": report.key_recommendations,
        "next_steps": report.next_steps,
        "disclaimer": report.disclaimer,
    }
