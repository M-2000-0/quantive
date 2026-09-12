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
    """Generates personalized investment recommendations.

    Phases:
      1-2  user input + profile   -> explicit preferences + behavioral weights
      3    candidate universe      -> instruments + discovery items + market-derived candidates
      4    scoring                 -> fit + relevance + reason, separated (not a single opaque number)
      5    diversification         -> caps repetition by type / sector / asset class
      6    output shape            -> per-item 'why am I seeing this' + risk label + readiness flag
      7    feedback loop           -> record interactions, adjust behavioral weights
    """

    def __init__(self, db: Session, candidate_fetcher=None):
        self.db = db
        # candidate_fetcher is an optional injectable so tests and later live data
        # sources can be swapped without touching the scorer.
        self._candidate_fetcher = candidate_fetcher or self._default_candidate_fetcher

    # ── profile helpers (Phase 2) ────────────────────────────────────────────

    def get_profile(self, user_id: str) -> UserProfile:
        """Get or create user profile."""
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    def _get_exclusions(self, profile: UserProfile) -> set[str]:
        """Explicit symbols/instruments the user never wants to see."""
        raw = profile.exclusions or []
        return {str(x).strip().upper() for x in raw if str(x).strip()}

    # ── Phase 3: candidate universe ───────────────────────────────────────────

    def _default_candidate_fetcher(self, user_id: str, exclusions: set[str]) -> list[dict]:
        """Build the candidate universe from whatever is reachable right now.

        This is intentionally thin for the first usable version:
          - instruments already in the user's portfolios  (near you already)
          - discovery / market-monitor items that have a discovery_score
          - a small diversified baseline so the list is not just what they already hold

        Excluded symbols are dropped here so later phases never see them.
        """
        from app.models import Portfolio, DebtInstrument
        from app.models.market_monitor import MarketAsset
        from datetime import datetime, timezone

        profile = self.get_profile(user_id)
        now = datetime.now(timezone.utc)

        candidates: list[dict] = []
        seen: set[str] = set()

        def add(candidate: dict) -> None:
            key = str(candidate.get('symbol') or candidate.get('id') or '').upper()
            if not key or key in seen or key in exclusions:
                return
            seen.add(key)
            candidates.append(candidate)

        # 1. instruments the user already holds (so 'near you already' works)
        portfolios = (
            db_query_all(self.db, Portfolio).filter(Portfolio.org_id == _user_org(self.db, user_id)).all()
            if hasattr(Portfolio, 'org_id')
            else []
        )
        portfolio_ids = [p.id for p in portfolios]
        instruments = (
            db_query_all(self.db, DebtInstrument)
            .filter(DebtInstrument.portfolio_id.in_(portfolio_ids))
            .all()
            if portfolio_ids else []
        )

        for inst in instruments:
            try:
                maturity = datetime.strptime(inst.maturity_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                years_left = max(0.0, (maturity - now).days / 365.25)
            except (ValueError, AttributeError):
                years_left = 0.0

            add({
                'symbol': inst.isin or inst.ticker or inst.id,
                'name': inst.name or inst.ticker or 'Portfolio instrument',
                'asset_class': self._asset_class_from_instrument(inst),
                'sector': _sector_guess(inst.name or inst.ticker or ''),
                'years_left': years_left,
                'coupon': float(inst.coupon_rate or 0),
                'principal_outstanding': float(inst.principal_outstanding or 0),
                'currency': inst.currency or 'USD',
                'source': 'portfolio',
                'market_data_ready': False,
            })

        # 2. discovery / market-monitor items that already carry a discovery_score
        try:
            assets = (
                db_query_all(self.db, MarketAsset)
                .filter(MarketAsset.discovery_score > 0)
                .order_by(MarketAsset.discovery_score.desc())
                .limit(40)
                .all()
            )
        except Exception:
            assets = []

        for a in assets:
            add({
                'symbol': a.symbol,
                'name': a.name or a.symbol,
                'asset_class': a.asset_class or 'stock',
                'sector': getattr(a, 'sector', None) or _sector_guess(a.name or a.symbol or ''),
                'years_left': 0.0,
                'coupon': 0.0,
                'principal_outstanding': 0.0,
                'currency': 'USD',
                'source': 'discovery',
                'discovery_score': float(getattr(a, 'discovery_score', 0) or 0),
                'discovery_signals': getattr(a, 'discovery_signals', None),
                'market_data_ready': bool(getattr(a, 'price_usd', None) or getattr(a, 'market_cap_usd', None)),
            })

        # 3. small diversified baseline so new users still see breadth
        for item in DEFAULT_DIVERSITY_SEED:
            add(dict(item, source='baseline', market_data_ready=False))

        return candidates

    # ── Phase 3 helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _asset_class_from_instrument(inst) -> str:
        """Map a DebtInstrument row to a coarse asset class string."""
        name = (inst.name or '').lower()
        t = inst.instrument_type
        if hasattr(t, 'value'):
            t = t.value
        t = str(t or '').lower()
        if 'equity' in t or 'stock' in t or 'equity' in name:
            return 'equity'
        if 'bond' in t or 'debt' in t or 'note' in name or 'bond' in name:
            return 'fixed_income'
        if 'fx' in t or 'currency' in t or 'fx' in name:
            return 'currency'
        if 'crypto' in t or 'crypto' in name:
            return 'crypto'
        return 'other'

    # ── Phase 4: scoring ──────────────────────────────────────────────────────

    def generate_recommendations(
        self,
        user_id: str,
        portfolio_data: dict,
        market_data: dict,
        limit: int = 7,
    ) -> list[dict]:
        """Phase 3+4+5+6.

        Build the candidate universe, score each candidate on two separated
        axes (fit + relevance), diversify, and return the output shape with a
        per-item 'why am I seeing this' reason and readiness notes.
        """
        profile = self.get_profile(user_id)
        exclusions = self._get_exclusions(profile)

        candidates = self._candidate_fetcher(user_id, exclusions)

        # keep template-driven insights as a fallback when the universe is sparse
        template_candidates = [
            r for r in (
                self._evaluate_template(t, portfolio_data, market_data, profile)
                for t in RECOMMENDATION_TEMPLATES
            )
            if r
        ]
        if len(candidates) < limit:
            candidates.extend(
                self._generate_market_insights(market_data, profile, limit - len(candidates))
            )
        if not candidates:
            candidates = template_candidates

        # Phase 4: score each candidate on two separated axes
        scored = []
        for c in candidates:
            scored.append(self._score_candidate(c, profile, portfolio_data, market_data))

        # Phase 5: diversify
        diversified = self._diversify(scored, limit)

        # Phase 6: output shape
        out = []
        for c in diversified:
            out.append(self._to_output(c, profile))

        # engagement bookkeeping
        profile.total_recommendations_shown += len(out)
        profile.last_active_at = datetime.now(timezone.utc)
        self.db.commit()

        return out

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
            ccy_breakdown = p.get("currency_breakdown") or {"USD": 100}
            top_currency_pct = max(ccy_breakdown.values())
            if top_currency_pct < 60:
                return None
            top_ccy = max(ccy_breakdown, key=ccy_breakdown.get)
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

    # ── Phase 4: fit + relevance (separated, not one opaque number) ────────────

    def _score_candidate(
        self,
        candidate: dict,
        profile: UserProfile,
        portfolio_data: dict,
        market_data: dict,
    ) -> dict:
        """Return a copy with explicit `fit`, `relevance`, and `reason` fields.

        fit      - how well the item matches the user's risk/horizon/constraints
        relevance - how strongly it connects to interests, watched themes, activity
        reason   - one short plain-language sentence the UI can surface as 'why this'
        """
        cand = dict(candidate)
        risk = self._parse_risk_tolerance(profile.risk_tolerance or 'moderate')
        horizon = float(profile.investment_horizon_years or 10)
        exclusions = self._get_exclusions(profile)

        fit_components: list[tuple[str, float, float]] = []  # (label, value 0-1, weight)
        relevance_components: list[tuple[str, float, float]] = []

        # --- fit axis ---

        # risk alignment: penalize assets whose volatility tier is far from the
        # user's stated risk posture (or skip when we have no volatility signal)
        vol_tier = cand.get('volatility_tier')  # conservative | moderate | aggressive | unknown
        if vol_tier and vol_tier != 'unknown':
            vol_score = self._volatility_fit(vol_tier, risk)
            fit_components.append(('risk_poster_match', vol_score, 1.0))

        # horizon alignment: short-dated instruments are less relevant for long horizons
        # and vice-versa; we bias rather than block, because users do hold mixed horizons
        years = float(cand.get('years_left') or 0)
        if years > 0:
            horizon_score = self._horizon_fit(years, horizon)
            fit_components.append(('horizon_match', horizon_score, 0.8))

        # currency constraint: penalize items in currencies the user did not opt into
        ccy = cand.get('currency') or 'USD'
        currency_prefs = profile.currency_preferences or []
        if currency_prefs:
            currency_score = 1.0 if ccy in currency_prefs else 0.4
            fit_components.append(('currency_pref', currency_score, 0.6))

        # exclusions already handled upstream, but still note it here for explainability
        symbol = str(cand.get('symbol') or '').upper()
        if symbol in exclusions:
            fit_components.append(('excluded_by_user', 0.0, 1.0))

        # liquidity/readiness: if we do not have market data for this candidate yet,
        # lower fit a little rather than presenting it as comparable to live data
        if not cand.get('market_data_ready'):
            fit_components.append(('live_data_unavailable', 0.6, 0.5))

        # --- relevance axis ---

        # portfolio overlap: items already in the user's holdings are more relevant
        if cand.get('source') == 'portfolio':
            relevance_components.append(('in_your_portfolio', 0.9, 1.0))

        # discovery signal: prefer items the discovery pipeline already flagged
        ds = cand.get('discovery_score') or 0
        if ds > 0:
            relevance_components.append(('discovery_signal', min(1.0, ds / 100.0), 1.0))

        # sector / focus alignment: prefer sectors the user explicitly focused on
        focus = profile.focus_sectors or []
        sector = cand.get('sector')
        if focus and sector:
            rel = 0.9 if any(s.lower() in str(sector).lower() for s in focus) else 0.5
            relevance_components.append(('focus_sector_match', rel, 0.6))

        # behavioral weight on this candidate's type family
        weight_key = cand.get('weight_key') or 'market_weight'
        weight = getattr(profile, weight_key, 1.0)
        weight = max(0.3, min(2.0, float(weight)))
        relevance_components.append(('behavioral_weight', weight / 2.0, 0.5))

        # source variety bonus: do not starve the user of 'new to you' items
        if cand.get('source') == 'discovery' or cand.get('source') == 'baseline':
            relevance_components.append(('new_to_you', 0.6, 0.4))

        fit = _weighted_mean(fit_components) if fit_components else 0.5
        relevance = _weighted_mean(relevance_components) if relevance_components else 0.5

        # reason is built from the strongest component on each axis
        reason = _compose_reason(fit_components, relevance_components, cand)

        cand['fit'] = round(max(0.0, min(1.0, fit)), 3)
        cand['relevance'] = round(max(0.0, min(1.0, relevance)), 3)
        cand['reason'] = reason
        cand['risk_label'] = _risk_label_from_candidate(cand, market_data)
        cand['readiness'] = _readiness_from_candidate(cand)

        return cand

    @staticmethod
    def _parse_risk_tolerance(value: str) -> str:
        v = (value or 'moderate').lower()
        if 'conservativ' in v:
            return 'conservative'
        if 'aggressiv' in v:
            return 'aggressive'
        return 'moderate'

    @staticmethod
    def _volatility_fit(vol_tier: str, risk: str) -> float:
        order = ['conservative', 'moderate', 'aggressive']
        a = order.index(vol_tier) if vol_tier in order else 1
        b = order.index(risk) if risk in order else 1
        diff = abs(a - b)
        if diff == 0:
            return 0.95
        if diff == 1:
            return 0.7
        return 0.4

    @staticmethod
    def _horizon_fit(years_left: float, horizon: float) -> float:
        if horizon <= 0 or years_left <= 0:
            return 0.6
        ratio = years_left / max(1.0, horizon)
        if 0.5 <= ratio <= 2.0:
            return 0.9
        if ratio < 0.5:
            return 0.6
        return 0.7

    # ── Phase 5: diversification (type + sector + asset class) ─────────────────

    def _diversify(self, candidates: list[dict], limit: int) -> list[dict]:
        """Return the top candidates while capping repetition.

        Caps:
          - max 2 of the same recommendation type
          - max 2 of the same sector
          - max 3 of the same asset class
        This keeps the list scannable and not just one cluster repeated.
        """
        result: list[dict] = []
        type_counts: dict[str, int] = {}
        sector_counts: dict[str, int] = {}
        ac_counts: dict[str, int] = {}

        # sort by a blended rank so the user still sees the best fit/relevance first
        ranked = sorted(
            candidates,
            key=lambda c: (c.get('fit', 0) * 0.6 + c.get('relevance', 0) * 0.4),
            reverse=True,
        )

        for c in ranked:
            t = c.get('type') or 'other'
            sector = (c.get('sector') or '').strip() or 'unspecified'
            ac = (c.get('asset_class') or '').strip() or 'other'

            if type_counts.get(t, 0) >= 2:
                continue
            if sector_counts.get(sector, 0) >= 2:
                continue
            if ac_counts.get(ac, 0) >= 3:
                continue

            result.append(c)
            type_counts[t] = type_counts.get(t, 0) + 1
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
            ac_counts[ac] = ac_counts.get(ac, 0) + 1

            if len(result) >= limit:
                break

        return result

    # ── Phase 6: output shape ──────────────────────────────────────────────────

    def _to_output(self, candidate: dict, profile: UserProfile) -> dict:
        """Build the response item the UI actually renders.

        Key points:
          - fit and relevance are shown separately, not merged into one magic number
          - every item carries a one-line 'reason' the UI can expose as 'why am I seeing this'
          - risk_label and readiness are plain-language, not raw fields
        """
        symbol = candidate.get('symbol') or candidate.get('name') or 'Unknown'
        return {
            'symbol': symbol,
            'name': candidate.get('name') or symbol,
            'type': candidate.get('type') or 'market',
            'asset_class': candidate.get('asset_class') or 'other',
            'sector': candidate.get('sector') or 'unspecified',
            'source': candidate.get('source') or 'unknown',
            'fit': candidate.get('fit', 0.5),
            'relevance': candidate.get('relevance', 0.5),
            'reason': candidate.get('reason') or 'Included in your personalized list.',
            'risk_label': candidate.get('risk_label') or 'Not classified yet',
            'readiness': candidate.get('readiness') or 'pending_data',
            'why_this': self._explain_why_this(candidate, profile),
            'raw_reason_components': candidate.get('reason_components', []),
        }

    def _explain_why_this(self, candidate: dict, profile: UserProfile) -> str:
        """One short sentence for the UI 'why am I seeing this' chip."""
        parts: list[str] = []
        if candidate.get('source') == 'portfolio':
            parts.append('already in your portfolio')
        elif candidate.get('source') == 'discovery':
            parts.append('flagged by our discovery scans')
        elif candidate.get('source') == 'baseline':
            parts.append('added for portfolio breadth')

        risk = self._parse_risk_tolerance(profile.risk_tolerance or 'moderate')
        if candidate.get('fit', 0) >= 0.7:
            parts.append('matches your stated risk posture')
        elif candidate.get('fit', 0) < 0.5:
            parts.append('shown because it rounds out your coverage')

        ds = candidate.get('discovery_score') or 0
        if ds > 0:
            parts.append(f'has a discovery score of {int(ds)}/100')

        if not parts:
            parts.append('included in your personalized list')

        return ' / '.join(parts)

    # ── Phase 7: feedback loop (record + weight update) ────────────────────────

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


# ── small helpers used by the scorer (Phase 4-6) ────────────────────────────────


def _weighted_mean(components: list[tuple[str, float, float]]) -> float:
    """Weighted average of (label, value, weight)."""
    total_weight = sum(c[2] for c in components)
    if total_weight <= 0:
        return 0.5
    return sum(c[1] * c[2] for c in components) / total_weight


def _compose_reason(
    fit_components: list[tuple[str, float, float]],
    relevance_components: list[tuple[str, float, float]],
    candidate: dict,
) -> str:
    """Build one short plain-language reason from the strongest components."""
    parts: list[str] = []

    best_fit = max(fit_components, key=lambda c: c[1] * c[2], default=None)
    best_rel = max(relevance_components, key=lambda c: c[1] * c[2], default=None)

    label_map = {
        'risk_poster_match': 'matches your risk posture',
        'horizon_match': 'fits your time horizon',
        'currency_pref': 'uses a currency you focus on',
        'excluded_by_user': 'flagged by you',
        'live_data_unavailable': 'live market data not yet attached',
        'in_your_portfolio': 'already in your portfolio',
        'discovery_signal': 'flagged by discovery scans',
        'focus_sector_match': 'matches a sector you follow',
        'behavioral_weight': 'aligns with your recent interests',
        'new_to_you': 'added to broaden your coverage',
    }

    if best_fit and best_fit[1] >= 0.5:
        parts.append(label_map.get(best_fit[0], best_fit[0]))
    else:
        parts.append('shown for portfolio breadth')

    if best_rel and best_rel[1] >= 0.6:
        rel = label_map.get(best_rel[0], best_rel[0])
        if rel not in parts:
            parts.append(rel)

    symbol = candidate.get('symbol') or candidate.get('name') or ''
    if not parts:
        return f"Included in your personalized list."
    return f"{symbol or ''} {', '.join(parts)}".strip()


def _risk_label_from_candidate(candidate: dict, market_data: dict) -> str:
    """Plain-language risk label for the UI."""
    vol = candidate.get('volatility_tier') or ''
    source = candidate.get('source') or ''
    if source == 'baseline' or not candidate.get('market_data_ready'):
        return 'pending_data'
    if vol in ('conservative', 'low'):
        return 'lower-volatility'
    if vol in ('moderate', 'medium'):
        return 'moderate'
    if vol in ('aggressive', 'high'):
        return 'higher-volatility'
    return 'not_classified'


def _readiness_from_candidate(candidate: dict) -> str:
    """How ready the item is for comparison."""
    if candidate.get('market_data_ready'):
        return 'ready'
    return 'pending_data'


def _sector_guess(name: str) -> str:
    """Very rough sector guess from name text; only used when no sector field exists."""
    n = (name or '').lower()
    if not n:
        return 'unspecified'
    if ' treasury' in n or ' government' in n or ' sovereign' in n or ' gilt' in n or ' bnd ' in n:
        return 'sovereign'
    if ' corp' in n or ' corporate' in n or ' debenture' in n:
        return 'corporate'
    if ' crypto' in n or ' bitcoin' in n or ' ethereum' in n or ' eth' in n or ' btc' in n:
        return 'crypto'
    if 'fx' in n or ' currency' in n or ' forex' in n:
        return 'currency'
    if ' etf' in n or ' index' in n or ' spy' in n or ' qqq' in n or ' dia' in n:
        return 'etf/index'
    return 'unspecified'


DEFAULT_DIVERSITY_SEED: list[dict] = [
    {
        'symbol': 'DGS10',
        'name': '10-Year Treasury Yield Benchmark',
        'asset_class': 'fixed_income',
        'sector': 'sovereign',
        'source': 'baseline',
        'market_data_ready': False,
    },
    {
        'symbol': 'USD_FX',
        'name': 'USD FX Reference',
        'asset_class': 'currency',
        'sector': 'currency',
        'source': 'baseline',
        'market_data_ready': False,
    },
    {
        'symbol': 'SGOV',
        'name': 'Short Treasury ETF (example instrument)',
        'asset_class': 'fixed_income',
        'sector': 'sovereign',
        'source': 'baseline',
        'market_data_ready': False,
    },
    {
        'symbol': 'ACWI',
        'name': 'Global Equity Index (example instrument)',
        'asset_class': 'equity',
        'sector': 'etf/index',
        'source': 'baseline',
        'market_data_ready': False,
    },
]


def db_query_all(session, model):
    """Compatibility shim so the candidate fetcher can be test-double-friendly."""
    return session.query(model)


def _user_org(session, user_id: str) -> str:
    """Best-effort org id for the current user."""
    try:
        from app.models import User
        u = session.query(User).filter(User.id == user_id).first()
        if u and getattr(u, 'org_id', None):
            return u.org_id
    except Exception:
        pass
    return ''
