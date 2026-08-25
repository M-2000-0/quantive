"""Risk Probabilities and Investment Indicators Engine.

Provides:
- Probability distributions for portfolio returns
- Risk-adjusted return indicators
- Concrete investment examples ("Invest $X → Get $Y back with Z% probability")
- VaR and CVaR at multiple confidence levels
- Risk score (1-10 scale) with plain-English descriptions
- Scenarios: best case, expected, worst case, tail risk
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

import numpy as np

# ── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class RiskIndicator:
    """A single risk indicator with probability and return."""
    label: str
    description: str
    probability: float          # 0.0 to 1.0
    expected_return_pct: float  # percentage return
    expected_amount: float      # dollar amount for a given investment
    investment_amount: float    # input investment
    time_horizon_months: int    # time horizon
    confidence_level: str       # "high", "medium", "low"
    icon: str = "📊"            # emoji icon for display

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "description": self.description,
            "probability": round(self.probability, 4),
            "probability_pct": f"{self.probability * 100:.1f}%",
            "expected_return_pct": round(self.expected_return_pct, 2),
            "expected_return_pct_str": f"{self.expected_return_pct:+.2f}%",
            "expected_amount": round(self.expected_amount, 2),
            "investment_amount": round(self.investment_amount, 2),
            "profit_loss": round(self.expected_amount - self.investment_amount, 2),
            "profit_loss_str": f"${self.expected_amount - self.investment_amount:+,.0f}",
            "time_horizon_months": self.time_horizon_months,
            "confidence_level": self.confidence_level,
            "icon": self.icon,
        }


@dataclass
class RiskScore:
    """Overall portfolio risk score with breakdown."""
    overall_score: int          # 1-10 (1=safest, 10=riskiest)
    label: str                  # "Very Low", "Low", "Moderate", etc.
    color: str                  # hex color for UI
    description: str            # plain English description
    factors: dict[str, float]   # factor_name -> score (0-1)
    recommendations: list[str]  # actionable recommendations

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "label": self.label,
            "color": self.color,
            "description": self.description,
            "factors": {k: round(v, 3) for k, v in self.factors.items()},
            "recommendations": self.recommendations,
        }


@dataclass
class InvestmentScenario:
    """A concrete investment scenario for user display."""
    scenario_name: str          # "Best Case", "Expected", "Worst Case", "Tail Risk"
    investment: float           # USD amount invested
    return_amount: float        # USD amount returned
    return_pct: float           # percentage return
    probability: float          # probability of this outcome
    time_horizon_months: int
    annualized_return: float
    risk_level: str             # "low", "medium", "high"
    description: str            # human-readable description
    icon: str                   # emoji

    def to_dict(self) -> dict:
        profit = self.return_amount - self.investment
        return {
            "scenario_name": self.scenario_name,
            "investment": round(self.investment, 2),
            "return_amount": round(self.return_amount, 2),
            "return_pct": round(self.return_pct, 2),
            "return_pct_str": f"{self.return_pct:+.1f}%",
            "profit_loss": round(profit, 2),
            "profit_loss_str": f"${profit:+,.0f}",
            "probability": round(self.probability, 4),
            "probability_pct": f"{self.probability * 100:.1f}%",
            "time_horizon_months": self.time_horizon_months,
            "annualized_return": round(self.annualized_return, 2),
            "annualized_return_str": f"{self.annualized_return:+.2f}%",
            "risk_level": self.risk_level,
            "description": self.description,
            "icon": self.icon,
        }


# ── Risk Probability Calculator ─────────────────────────────────────────────

class RiskProbabilityEngine:
    """Calculates risk probabilities and investment indicators for portfolios.

    Uses Monte Carlo simulation and statistical analysis to generate
    probability distributions and concrete investment examples.
    """

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def calculate_risk_indicators(
        self,
        portfolio_value: float,
        instruments: list[dict],
        scenarios: Optional[list[dict]] = None,
        time_horizon_months: int = 12,
    ) -> list[RiskIndicator]:
        """Calculate risk indicators for a portfolio.

        Returns a list of indicators showing probability of different outcomes.
        """
        # Extract portfolio characteristics
        __total_principal = sum(i.get("principal_outstanding", 0) for i in instruments)
        avg_coupon = np.mean([i.get("coupon_rate", 0) for i in instruments]) if instruments else 0
        avg_spread = np.mean([i.get("spread_bps", 0) for i in instruments]) if instruments else 0
        avg_maturity_years = self._avg_maturity_years(instruments)
        currency_count = len(set(i.get("currency", "USD") for i in instruments))
        floating_count = sum(1 for i in instruments if i.get("instrument_type") == "floating_rate_note")
        floating_pct = floating_count / len(instruments) if instruments else 0

        # Base annual return and volatility estimates
        base_return = avg_coupon + (avg_spread / 10000)
        volatility = self._estimate_volatility(
            avg_coupon, avg_spread, avg_maturity_years, floating_pct, currency_count
        )

        # Time-adjusted parameters
        t = time_horizon_months / 12
        period_return = base_return * t
        period_vol = volatility * math.sqrt(t)

        investment = portfolio_value

        indicators = []

        # 1. High Confidence — likely outcome
        indicators.append(self._make_indicator(
            label="High Confidence Return",
            description="Outcome expected with high certainty based on current portfolio composition",
            base_return_pct=period_return * 0.85,
            volatility=period_vol * 0.3,
            investment=investment,
            time_horizon=time_horizon_months,
            confidence="high",
            icon="🟢",
        ))

        # 2. Expected Return — most likely
        indicators.append(self._make_indicator(
            label="Expected Return",
            description="Most likely outcome based on portfolio weighted average metrics",
            base_return_pct=period_return,
            volatility=period_vol * 0.5,
            investment=investment,
            time_horizon=time_horizon_months,
            confidence="medium",
            icon="📊",
        ))

        # 3. Moderate Upside
        indicators.append(self._make_indicator(
            label="Moderate Upside",
            description="Favorable market conditions with favorable rate environment",
            base_return_pct=period_return * 1.25,
            volatility=period_vol * 0.8,
            investment=investment,
            time_horizon=time_horizon_months,
            confidence="medium",
            icon="📈",
        ))

        # 4. Strong Upside
        indicators.append(self._make_indicator(
            label="Strong Upside",
            description="Best realistic scenario with strong market tailwinds",
            base_return_pct=period_return * 1.8,
            volatility=period_vol * 1.2,
            investment=investment,
            time_horizon=time_horizon_months,
            confidence="low",
            icon="🚀",
        ))

        # 5. Moderate Downside
        indicators.append(self._make_indicator(
            label="Moderate Downside",
            description="Adverse market conditions with rising rates or widening spreads",
            base_return_pct=period_return * -0.5,
            volatility=period_vol * 0.8,
            investment=investment,
            time_horizon=time_horizon_months,
            confidence="medium",
            icon="⚠️",
        ))

        # 6. Severe Downside
        indicators.append(self._make_indicator(
            label="Severe Downside",
            description="Significant market stress with credit events or liquidity crisis",
            base_return_pct=period_return * -2.0,
            volatility=period_vol * 1.5,
            investment=investment,
            time_horizon=time_horizon_months,
            confidence="low",
            icon="🔴",
        ))

        # 7. Tail Risk
        indicators.append(self._make_indicator(
            label="Tail Risk (Black Swan)",
            description="Extreme market event — rare but possible. Consider hedging.",
            base_return_pct=period_return * -4.0,
            volatility=period_vol * 2.5,
            investment=investment,
            time_horizon=time_horizon_months,
            confidence="low",
            icon="💀",
        ))

        return indicators

    def calculate_investment_scenarios(
        self,
        portfolio_value: float,
        instruments: list[dict],
        time_horizon_months: int = 12,
        investment_amounts: Optional[list[float]] = None,
    ) -> list[InvestmentScenario]:
        """Generate concrete investment scenarios for user display.

        Shows users exactly what they could expect: "Invest $1M → Get $1.05M back"
        """
        if investment_amounts is None:
            investment_amounts = [1_000_000, 5_000_000, 10_000_000, 50_000_000]

        # Get portfolio metrics
        _total_principal = sum(i.get("principal_outstanding", 0) for i in instruments)
        avg_coupon = np.mean([i.get("coupon_rate", 0) for i in instruments]) if instruments else 0.05
        avg_spread = np.mean([i.get("spread_bps", 0) for i in instruments]) if instruments else 0
        avg_maturity = self._avg_maturity_years(instruments)
        floating_pct = sum(1 for i in instruments if i.get("instrument_type") == "floating_rate_note") / len(instruments) if instruments else 0
        currency_count = len(set(i.get("currency", "USD") for i in instruments))

        base_annual_return = avg_coupon + (avg_spread / 10000)
        volatility = self._estimate_volatility(avg_coupon, avg_spread, avg_maturity, floating_pct, currency_count)

        t = time_horizon_months / 12
        annualized = base_annual_return

        scenarios = []
        for amount in investment_amounts:
            # Best Case (90th percentile)
            best_return = amount * (1 + (annualized + 2 * volatility) * t)
            best_pct = (annualized + 2 * volatility) * t * 100
            scenarios.append(InvestmentScenario(
                scenario_name="Best Case",
                investment=amount,
                return_amount=best_return,
                return_pct=best_pct,
                probability=0.10,
                time_horizon_months=time_horizon_months,
                annualized_return=annualized + 2 * volatility,
                risk_level="low",
                description=f"In favorable markets, ${amount:,.0f} grows to ${best_return:,.0f} ({best_pct:+.1f}%)",
                icon="🚀",
            ))

            # Expected Return (50th percentile)
            expected_return = amount * (1 + annualized * t)
            expected_pct = annualized * t * 100
            scenarios.append(InvestmentScenario(
                scenario_name="Expected Return",
                investment=amount,
                return_amount=expected_return,
                return_pct=expected_pct,
                probability=0.50,
                time_horizon_months=time_horizon_months,
                annualized_return=annualized,
                risk_level="medium",
                description=f"Based on current rates, ${amount:,.0f} returns ${expected_return:,.0f} ({expected_pct:+.1f}%)",
                icon="📊",
            ))

            # Moderate Downside (25th percentile)
            down_return = amount * (1 + (annualized - 1.5 * volatility) * t)
            down_pct = (annualized - 1.5 * volatility) * t * 100
            scenarios.append(InvestmentScenario(
                scenario_name="Moderate Downside",
                investment=amount,
                return_amount=down_return,
                return_pct=down_pct,
                probability=0.25,
                time_horizon_months=time_horizon_months,
                annualized_return=annualized - 1.5 * volatility,
                risk_level="medium",
                description=f"If rates rise, ${amount:,.0f} could return ${down_return:,.0f} ({down_pct:+.1f}%)",
                icon="⚠️",
            ))

            # Worst Case (5th percentile)
            worst_return = amount * (1 + (annualized - 3 * volatility) * t)
            worst_pct = (annualized - 3 * volatility) * t * 100
            scenarios.append(InvestmentScenario(
                scenario_name="Worst Case",
                investment=amount,
                return_amount=worst_return,
                return_pct=worst_pct,
                probability=0.05,
                time_horizon_months=time_horizon_months,
                annualized_return=annualized - 3 * volatility,
                risk_level="high",
                description=f"In stress conditions, ${amount:,.0f} could return only ${worst_return:,.0f} ({worst_pct:+.1f}%)",
                icon="🔴",
            ))

        return scenarios

    def calculate_risk_score(
        self,
        instruments: list[dict],
    ) -> RiskScore:
        """Calculate an overall risk score (1-10) for the portfolio."""
        if not instruments:
            return RiskScore(
                overall_score=5,
                label="Insufficient Data",
                color="#94a3b8",
                description="Not enough instruments to assess risk",
                factors={},
                recommendations=["Add instruments to your portfolio to get a risk assessment"],
            )

        total_principal = sum(i.get("principal_outstanding", 0) for i in instruments)
        avg_coupon = np.mean([i.get("coupon_rate", 0) for i in instruments])
        avg_spread = np.mean([i.get("spread_bps", 0) for i in instruments])
        avg_maturity = self._avg_maturity_years(instruments)
        floating_pct = sum(1 for i in instruments if i.get("instrument_type") == "floating_rate_note") / len(instruments)
        currency_count = len(set(i.get("currency", "USD") for i in instruments))

        # Concentration risk (Herfindahl index)
        principal_shares = [i.get("principal_outstanding", 0) / total_principal for i in instruments if total_principal > 0]
        hhi = sum(s ** 2 for s in principal_shares) if principal_shares else 0

        # Factor scores (0 = safest, 1 = riskiest)
        factors = {}

        # Maturity risk
        factors["maturity_risk"] = min(1.0, max(0, avg_maturity / 10))

        # Coupon risk (higher coupon = higher risk usually)
        factors["coupon_risk"] = min(1.0, max(0, avg_coupon / 0.15))

        # Spread risk
        factors["spread_risk"] = min(1.0, max(0, avg_spread / 500))

        # Floating rate risk
        factors["floating_rate_risk"] = floating_pct

        # Currency risk
        factors["currency_risk"] = min(1.0, max(0, (currency_count - 1) / 5))

        # Concentration risk
        factors["concentration_risk"] = min(1.0, hhi)

        # Number of instruments (diversification)
        factors["diversification_risk"] = max(0, 1.0 - min(1.0, len(instruments) / 20))

        # Weighted overall score
        weights = {
            "maturity_risk": 0.20,
            "coupon_risk": 0.10,
            "spread_risk": 0.15,
            "floating_rate_risk": 0.15,
            "currency_risk": 0.15,
            "concentration_risk": 0.15,
            "diversification_risk": 0.10,
        }

        weighted_score = sum(factors.get(k, 0) * w for k, w in weights.items())
        overall = max(1, min(10, round(weighted_score * 9 + 1)))

        # Label and color mapping
        score_map = {
            (1, 2): ("Very Low Risk", "#22c55e", "Your portfolio is very conservative with low exposure to market volatility."),
            (3, 4): ("Low Risk", "#84cc16", "Your portfolio has low risk. Stable returns expected with minimal downside."),
            (5, 6): ("Moderate Risk", "#eab308", "Your portfolio has moderate risk. Some volatility expected but generally stable."),
            (7, 8): ("High Risk", "#f97316", "Your portfolio carries elevated risk. Higher potential returns but significant volatility."),
            (9, 10): ("Very High Risk", "#ef4444", "Your portfolio has very high risk. Potential for large losses in stress scenarios."),
        }

        label, color, description = score_map.get(
            (overall if overall <= 2 else overall if overall <= 4 else overall if overall <= 6 else overall if overall <= 8 else 10),
            ("Moderate Risk", "#eab308", "Moderate risk profile.")
        )
        # Fix the lookup
        for (lo, hi), (lbl, clr, desc) in score_map.items():
            if lo <= overall <= hi:
                label, color, description = lbl, clr, desc
                break

        # Generate recommendations
        recommendations = self._generate_recommendations(factors, avg_maturity, floating_pct, currency_count, len(instruments))

        return RiskScore(
            overall_score=overall,
            label=label,
            color=color,
            description=description,
            factors=factors,
            recommendations=recommendations,
        )

    def calculate_var(
        self,
        portfolio_value: float,
        instruments: list[dict],
        confidence_levels: Optional[list[float]] = None,
        time_horizon_days: int = 252,
    ) -> dict:
        """Calculate Value-at-Risk at multiple confidence levels.

        Returns VaR as both dollar amounts and percentages.
        """
        if confidence_levels is None:
            confidence_levels = [0.95, 0.99]

        avg_coupon = np.mean([i.get("coupon_rate", 0) for i in instruments]) if instruments else 0.05
        avg_spread = np.mean([i.get("spread_bps", 0) for i in instruments]) if instruments else 0
        avg_maturity = self._avg_maturity_years(instruments)
        floating_pct = sum(1 for i in instruments if i.get("instrument_type") == "floating_rate_note") / len(instruments) if instruments else 0
        currency_count = len(set(i.get("currency", "USD") for i in instruments))

        volatility = self._estimate_volatility(avg_coupon, avg_spread, avg_maturity, floating_pct, currency_count)
        daily_vol = volatility / math.sqrt(252)

        results = {}
        for cl in confidence_levels:
            z_score = np.abs(np.percentile(self.rng.standard_normal(10000), (1 - cl) * 100))
            var_pct = z_score * daily_vol * math.sqrt(time_horizon_days) * 100
            var_dollar = portfolio_value * var_pct / 100
            cvar_pct = var_pct * 1.3  # CVaR is typically 1.2-1.5x VaR

            results[f"var_{int(cl * 100)}"] = {
                "confidence_level": f"{cl * 100:.0f}%",
                "var_pct": round(var_pct, 2),
                "var_dollar": round(var_dollar, 0),
                "cvar_pct": round(cvar_pct, 2),
                "cvar_dollar": round(portfolio_value * cvar_pct / 100, 0),
                "time_horizon_days": time_horizon_days,
                "description": f"There is a {(1-cl)*100:.0f}% chance of losing more than ${var_dollar:,.0f} ({var_pct:.2f}%) over {time_horizon_days} days",
            }

        return results

    # ── Internal Helpers ────────────────────────────────────────────────────

    def _avg_maturity_years(self, instruments: list[dict]) -> float:
        """Calculate average maturity in years."""
        if not instruments:
            return 5.0
        maturities = []
        today = date.today()
        for inst in instruments:
            try:
                mat = date.fromisoformat(inst.get("maturity_date", "2030-01-01"))
                years = (mat - today).days / 365.25
                maturities.append(max(0.1, years))
            except (ValueError, TypeError):
                maturities.append(5.0)
        return float(np.mean(maturities))

    def _estimate_volatility(
        self,
        coupon: float,
        spread_bps: float,
        maturity_years: float,
        floating_pct: float,
        currency_count: int,
    ) -> float:
        """Estimate portfolio volatility from characteristics.

        Higher maturity, floating rates, currency exposure, and spread = more volatile.
        """
        base_vol = 0.02  # 2% base volatility

        # Maturity effect (longer = more volatile)
        maturity_factor = 1 + (maturity_years - 3) * 0.05

        # Floating rate effect
        floating_factor = 1 + floating_pct * 0.3

        # Currency effect
        currency_factor = 1 + (currency_count - 1) * 0.15

        # Spread effect (wider spread = more volatile)
        spread_factor = 1 + (spread_bps / 1000) * 0.5

        return base_vol * maturity_factor * floating_factor * currency_factor * spread_factor

    def _make_indicator(
        self,
        label: str,
        description: str,
        base_return_pct: float,
        volatility: float,
        investment: float,
        time_horizon: int,
        confidence: str,
        icon: str,
    ) -> RiskIndicator:
        """Create a risk indicator with probability estimate."""
        # Convert to probability based on confidence level
        prob_map = {"high": 0.80, "medium": 0.50, "low": 0.20}
        probability = prob_map.get(confidence, 0.5)

        return_pct = base_return_pct * 100
        return_amount = investment * (1 + base_return_pct)

        return RiskIndicator(
            label=label,
            description=description,
            probability=probability,
            expected_return_pct=return_pct,
            expected_amount=return_amount,
            investment_amount=investment,
            time_horizon_months=time_horizon,
            confidence_level=confidence,
            icon=icon,
        )

    def _generate_recommendations(
        self,
        factors: dict,
        avg_maturity: float,
        floating_pct: float,
        currency_count: int,
        instrument_count: int,
    ) -> list[str]:
        """Generate actionable risk recommendations."""
        recs = []

        if factors.get("concentration_risk", 0) > 0.3:
            recs.append("Diversify across more instruments to reduce concentration risk")
        if avg_maturity > 7:
            recs.append("Consider shorter-dated instruments to reduce interest rate sensitivity")
        if avg_maturity < 2:
            recs.append("Consider adding longer-dated instruments for better yield")
        if floating_pct > 0.4:
            recs.append("High floating rate exposure — consider fixed rate instruments for stability")
        if currency_count > 3:
            recs.append("Multiple currency exposure — consider FX hedging strategies")
        if instrument_count < 5:
            recs.append("Portfolio is concentrated — add more instruments for diversification")
        if factors.get("spread_risk", 0) > 0.5:
            recs.append("High credit spread exposure — review credit quality of holdings")
        if not recs:
            recs.append("Portfolio risk profile looks well-balanced")

        return recs


# ── Convenience Functions ───────────────────────────────────────────────────

def get_risk_summary(
    portfolio_value: float,
    instruments: list[dict],
    time_horizon_months: int = 12,
) -> dict:
    """Get a complete risk summary for a portfolio.

    Returns all risk data in a single response, ready for frontend rendering.
    """
    engine = RiskProbabilityEngine()

    indicators = engine.calculate_risk_indicators(
        portfolio_value, instruments, time_horizon_months=time_horizon_months,
    )
    scenarios = engine.calculate_investment_scenarios(
        portfolio_value, instruments, time_horizon_months=time_horizon_months,
        investment_amounts=[1_000_000, 5_000_000, 10_000_000],
    )
    risk_score = engine.calculate_risk_score(instruments)
    var_data = engine.calculate_var(portfolio_value, instruments)

    return {
        "portfolio_value": portfolio_value,
        "time_horizon_months": time_horizon_months,
        "risk_score": risk_score.to_dict(),
        "indicators": [ind.to_dict() for ind in indicators],
        "investment_scenarios": [s.to_dict() for s in scenarios],
        "value_at_risk": var_data,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
