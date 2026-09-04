"""
Personalized Recommendation Engine
===================================

Generates investment recommendations tailored to each user's:
- Risk tolerance and investment horizon
- Portfolio composition and constraints
- Behavioral history and engagement patterns
- Current market conditions

Produces ranked, personalized recommendations with confidence scores
and relevance explanations.
"""

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile, RecommendationInteraction


# ── Recommendation Templates ───────────────────────────────────────
# Each template defines: type, condition_check, title, text, base_relevance

RECOMMENDATION_TEMPLATES = [
    {
        "type": "refinancing",
        "condition": "maturity_wall",
        "title": "Refinancing Window Opportunity",
        "text": "Your portfolio has {pct:.0f}% of debt maturing within 12 months. Current yield curves suggest refinancing {amount} now could save {savings} annually vs waiting for the maturity wall.",
        "base_relevance": 0.8,
        "weight_key": "refinancing_weight",
    },
    {
        "type": "refinancing",
        "condition": "inverted_curve",
        "title": "Inverted Curve Arbitrage",
        "text": "The yield curve is inverted by {spread:.0f}bps. Locking in long-term fixed rates now costs less than rolling short-term debt. Consider issuing {term}Y bonds at current {rate:.2f}%.",
        "base_relevance": 0.75,
        "weight_key": "refinancing_weight",
    },
    {
        "type": "risk",
        "condition": "duration_mismatch",
        "title": "Duration Risk Alert",
        "text": "Your portfolio duration ({duration:.1f}Y) is {direction} your target ({target:.1f}Y). {direction_cap} duration exposure increases sensitivity to rate moves by {multiplier:.1f}x.",
        "base_relevance": 0.85,
        "weight_key": "risk_insight_weight",
    },
    {
        "type": "risk",
        "condition": "concentration_risk",
        "title": "Concentration Risk Warning",
        "text": "{pct:.0f}% of your portfolio is in {currency} {instrument}. Diversification would reduce your portfolio's maximum drawdown by an estimated {reduction:.0f}%.",
        "base_relevance": 0.7,
        "weight_key": "risk_insight_weight",
    },
    {
        "type": "cost",
        "condition": "high_coupon",
        "title": "Coupon Reduction Opportunity",
        "text": "Your weighted average coupon ({coupon:.2f}%) is above current market rates ({market:.2f}%). Phased refinancing could reduce annual interest costs by ~{savings}.",
        "base_relevance": 0.8,
        "weight_key": "cost_insight_weight",
    },
    {
        "type": "currency",
        "condition": "fx_exposure",
        "title": "Currency Exposure Advisory",
        "text": "Foreign currency debt is {pct:.0f}% of total, {direction} your {limit:.0f}% policy ceiling. Consider {action} to reduce FX vulnerability.",
        "base_relevance": 0.75,
        "weight_key": "currency_weight",
    },
    {
        "type": "compliance",
        "condition": "fiscal_rule",
        "title": "Fiscal Rule Compliance",
        "text": "Your debt-to-GDP ratio ({gdp:.1f}%) is approaching the {rule} ceiling of {ceiling:.0f}%. Current trajectory suggests breaching within {months} months without corrective action.",
        "base_relevance": 0.9,
        "weight_key": "compliance_weight",
    },
    {
        "type": "market",
        "condition": "rate_direction",
        "title": "Rate Direction Signal",
        "text": "The 10Y-2Y spread has {direction} by {change:.0f}bps over 30 days, suggesting {interpretation}. {action_recommendation}.",
        "base_relevance": 0.65,
        "weight_key": "market_weight",
    },
    {
        "type": "cost",
        "condition": "floating_exposure",
        "title": "Floating Rate Exposure Review",
        "text": "{pct:.0f}% of your debt is floating-rate, exposing you to {variance:.0f}bps of rate variance. Converting {amount} to fixed at {rate:.2f}% would lock in savings of ~{savings}/year.",
        "base_relevance": 0.75,
        "weight_key": "cost_insight_weight",
    },
    {
        "type": "risk",
        "condition": "maturity_ladder",
        "title": "Maturity Ladder Optimization",
        "text": "Your maturity profile has a {gap:.0f}-year gap between {near} and {far}. Filling this with a {term}Y issuance would improve refinancing predictability and reduce rollover risk.",
        "base_relevance": 0.7,
        "weight_key": "risk_insight_weight",
    },
]


class RecommendationEngine:
    """Generates personalized investment recommendations."""

    def __init__(self, db: Session):
        self.db = db

    def get_profile(self, user_id: str) -> UserProfile:
        """Get or create user profile."""
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    def generate_recommendations(
        self,
        user_id: str,
        portfolio_data: dict,
        market_data: dict,
        limit: int = 7,
    ) -> list[dict]:
        """
        Generate personalized recommendations based on portfolio, market,
        and user behavioral profile.

        Returns ranked list of recommendations with scores and explanations.
        """
        profile = self.get_profile(user_id)
        candidates = []

        # Generate candidates from templates
        for template in RECOMMENDATION_TEMPLATES:
            result = self._evaluate_template(template, portfolio_data, market_data, profile)
            if result:
                candidates.append(result)

        # If too few candidates from portfolio analysis, add generic market insights
        if len(candidates) < limit:
            candidates.extend(self._generate_market_insights(market_data, profile, limit - len(candidates)))

        # Score and rank
        for candidate in candidates:
            candidate["score"] = self._compute_score(candidate, profile)

        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # Apply diversity — don't show all same type
        final = self._diversify(candidates, limit)

        # Update profile engagement counters
        profile.total_recommendations_shown += len(final)
        profile.last_active_at = datetime.now(timezone.utc)
        self.db.commit()

        return final

    def _evaluate_template(self, template: dict, portfolio: dict, market: dict, profile: UserProfile) -> Optional[dict]:
        """Evaluate a recommendation template against current conditions."""
        condition = template["condition"]
        p = portfolio
        m = market

        params = {}

        if condition == "maturity_wall":
            short_term = p.get("short_term_pct", 0)
            if short_term < 20:
                return None
            params = {
                "pct": short_term,
                "amount": f"${p.get('short_term_principal', 0)/1e9:.1f}B",
                "savings": f"${p.get('short_term_principal', 0) * 0.0075 / 1e9:.2f}B",
            }

        elif condition == "inverted_curve":
            spread = m.get("curve_spread_bps", 0)
            if spread > 0:
                return None
            params = {
                "spread": abs(spread),
                "term": 10,
                "rate": m.get("rate_10y", 4.3),
            }

        elif condition == "duration_mismatch":
            duration = p.get("avg_maturity", 0)
            target = profile.investment_horizon_years or 10
            diff = duration - target
            if abs(diff) < 1:
                return None
            params = {
                "duration": duration,
                "target": target,
                "direction": "above" if diff > 0 else "below",
                "direction_cap": "Excessive" if diff > 0 else "Insufficient",
                "multiplier": abs(diff) * 0.5,
            }

        elif condition == "concentration_risk":
            top_currency_pct = max(p.get("currency_breakdown", {"USD": 100}).values())
            if top_currency_pct < 60:
                return None
            top_ccy = max(p.get("currency_breakdown", {}), key=p.get("currency_breakdown", {}).get)
            params = {
                "pct": top_currency_pct,
                "currency": top_ccy,
                "instrument": "holdings",
                "reduction": min(25, (top_currency_pct - 50) * 0.5),
            }

        elif condition == "high_coupon":
            coupon = p.get("weighted_coupon", 0)
            market_rate = m.get("rate_10y", 4.3)
            if coupon <= market_rate:
                return None
            params = {
                "coupon": coupon,
                "market": market_rate,
                "savings": f"${p.get('total_debt', 0) * (coupon - market_rate) / 100 / 1e9:.2f}B",
            }

        elif condition == "fx_exposure":
            fx_pct = p.get("fx_exposure_pct", 0)
            limit = 35
            if fx_pct <= limit:
                return None
            params = {
                "pct": fx_pct,
                "direction": "above",
                "limit": limit,
                "action": "FX hedging or increased domestic currency issuance",
            }

        elif condition == "fiscal_rule":
            gdp = p.get("debt_to_gdp", 0)
            ceiling = 60
            if gdp < ceiling - 10:
                return None
            months = max(1, int((ceiling - gdp) / 0.5)) if gdp < ceiling else 0
            params = {
                "gdp": gdp,
                "rule": "MTDS",
                "ceiling": ceiling,
                "months": months,
            }

        elif condition == "rate_direction":
            spread_change = m.get("spread_30d_change_bps", 0)
            if abs(spread_change) < 15:
                return None
            params = {
                "direction": "widened" if spread_change > 0 else "narrowed",
                "change": abs(spread_change),
                "interpretation": "potential rate volatility" if spread_change > 0 else "rate stabilization",
                "action_recommendation": "Consider extending duration to lock in current rates" if spread_change > 0 else "Floating-rate exposure may become cheaper",
            }

        elif condition == "floating_exposure":
            floating_pct = p.get("floating_pct", 0)
            if floating_pct < 15:
                return None
            params = {
                "pct": floating_pct,
                "variance": int(floating_pct * 1.5),
                "amount": f"${p.get('floating_principal', 0)/1e9:.1f}B",
                "rate": m.get("rate_10y", 4.3),
                "savings": f"${p.get('floating_principal', 0) * 0.005 / 1e9:.2f}B",
            }

        elif condition == "maturity_ladder":
            distribution = p.get("maturity_distribution", {})
            years = sorted(distribution.keys()) if distribution else []
            if len(years) < 3:
                return None
            # Check for gaps
            max_gap = 0
            gap_start = ""
            gap_end = ""
            for i in range(len(years) - 1):
                gap = int(years[i + 1]) - int(years[i])
                if gap > max_gap:
                    max_gap = gap
                    gap_start = years[i]
                    gap_end = years[i + 1]
            if max_gap < 2:
                return None
            params = {
                "gap": max_gap,
                "near": gap_start,
                "far": gap_end,
                "term": max_gap,
            }

        if not params:
            return None

        return {
            "type": template["type"],
            "title": template["title"],
            "text": template["text"].format(**params),
            "base_relevance": template["base_relevance"],
            "weight_key": template["weight_key"],
            "params": params,
        }

    def _generate_market_insights(self, market: dict, profile: UserProfile, count: int) -> list[dict]:
        """Generate general market insights when portfolio-specific ones are insufficient."""
        insights = []
        rate = market.get("rate_10y", 4.3)
        spread = market.get("curve_spread_bps", -25)

        if rate > 4.5:
            insights.append({
                "type": "market",
                "title": "Elevated Rate Environment",
                "text": f"The 10Y Treasury yield is at {rate:.2f}%, above the 5-year average of 4.1%. Fixed-rate issuance at current levels may be attractive relative to recent history.",
                "base_relevance": 0.6,
                "weight_key": "market_weight",
                "params": {"rate": rate},
            })

        if spread < -20:
            insights.append({
                "type": "market",
                "title": "Yield Curve Inversion Signal",
                "text": f"The 10Y-2Y spread is {spread:.0f}bps, indicating inverted yield curve. Historically, inversions precede rate cuts within 12-18 months. Lock in long-term rates now.",
                "base_relevance": 0.65,
                "weight_key": "market_weight",
                "params": {"spread": spread},
            })

        insights.append({
            "type": "market",
            "title": "Daily Market Summary",
            "text": f"US 10Y: {rate:.2f}% | 2Y: {market.get('rate_2y', rate - 0.25):.2f}% | Spread: {spread:.0f}bps | SOFR: {market.get('sofr', 3.66):.2f}%",
            "base_relevance": 0.4,
            "weight_key": "market_weight",
            "params": {},
        })

        return insights[:count]

    def _compute_score(self, rec: dict, profile: UserProfile) -> float:
        """Compute personalized score based on relevance and user weights."""
        base = rec["base_relevance"]
        weight = getattr(profile, rec.get("weight_key", ""), 1.0)

        # Apply weight (weights range 0.5-2.0 based on behavioral history)
        score = base * weight

        # Add small noise for diversity
        score += random.uniform(-0.05, 0.05)

        return round(min(max(score, 0), 1.0), 3)

    def _diversify(self, candidates: list[dict], limit: int) -> list[dict]:
        """Ensure diversity — max 3 of same type in top results."""
        result = []
        type_counts = {}
        for rec in candidates:
            t = rec["type"]
            if type_counts.get(t, 0) >= 3:
                continue
            result.append(rec)
            type_counts[t] = type_counts.get(t, 0) + 1
            if len(result) >= limit:
                break
        return result

    def record_interaction(self, user_id: str, recommendation_type: str,
                          title: str, text: str, action: str,
                          time_spent: float = 0, market_ctx: dict = None,
                          portfolio_ctx: dict = None):
        """Record a user interaction with a recommendation."""
        profile = self.get_profile(user_id)

        interaction = RecommendationInteraction(
            user_id=user_id,
            profile_id=profile.id,
            recommendation_type=recommendation_type,
            recommendation_title=title,
            recommendation_text=text,
            action=action,
            time_spent_seconds=time_spent,
            market_context=market_ctx,
            portfolio_snapshot=portfolio_ctx,
        )
        self.db.add(interaction)

        # Update behavioral weights based on action
        weight_attr = None
        for t in RECOMMENDATION_TEMPLATES:
            if t["type"] == recommendation_type:
                weight_attr = t["weight_key"]
                break

        if weight_attr and hasattr(profile, weight_attr):
            current = getattr(profile, weight_attr)
            if action == "acted":
                setattr(profile, weight_attr, min(2.0, current + 0.15))
                profile.total_recommendations_acted += 1
            elif action == "clicked":
                setattr(profile, weight_attr, min(2.0, current + 0.05))
                profile.total_recommendations_clicked += 1
            elif action == "dismissed":
                setattr(profile, weight_attr, max(0.3, current - 0.1))
                profile.total_recommendations_dismissed += 1

        # Recompute engagement score
        total = profile.total_recommendations_shown or 1
        profile.avg_engagement_score = (
            (profile.total_recommendations_clicked * 1 + profile.total_recommendations_acted * 3 -
             profile.total_recommendations_dismissed * 1) / total
        )

        self.db.commit()
