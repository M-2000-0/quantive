"""Liquidity Risk Model — Beyond the Illusion of Easy Trading.

Sovereign bond markets assume you can always buy/sell at "market price."
In reality, bid-ask spreads explode during stress, market depth vanishes,
and large orders move the price against you. This model captures that reality.

Features:
- Bid-ask spread modeling (normal + stress scenarios)
- Market depth estimation (order book simulation)
- Liquidity-adjusted VaR (LVaR)
- Market impact cost for large trades
- Liquidity score per instrument type and currency
- Stress liquidity (crisis scenario liquidity)
- Liquidity-adjusted return metrics
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class LiquidityProfile:
    """Liquidity profile for a single instrument."""
    instrument_id: str
    instrument_name: str
    currency: str
    instrument_type: str          # treasury_bond, eurobond, FRN, etc.

    # Current liquidity metrics
    bid_ask_spread_bps: float     # Current bid-ask in basis points
    average_daily_volume_usd: float
    market_depth_usd: float       # Depth at best bid/offer
    days_to_liquidate_10pct: float  # Days to sell 10% without material impact
    days_to_liquidate_25pct: float  # Days to sell 25% without material impact
    days_to_liquidate_50pct: float  # Days to sell 50%

    # Stress metrics
    bid_ask_spread_stress_bps: float  # Bid-ask during stress
    avg_volume_stress_usd: float      # Volume during stress
    market_impact_1pct_bps: float     # Price impact of trading 1% of daily volume
    market_impact_5pct_bps: float     # Price impact of trading 5% of daily volume

    # Composite scores
    liquidity_score: float        # 1-10 (10 = most liquid)
    liquidity_tier: str           # "tier1", "tier2", "tier3", "illiquid"

    def to_dict(self) -> dict:
        return {
            "instrument_id": self.instrument_id,
            "instrument_name": self.instrument_name,
            "currency": self.currency,
            "instrument_type": self.instrument_type,
            "current": {
                "bid_ask_spread_bps": round(self.bid_ask_spread_bps, 1),
                "average_daily_volume_usd": round(self.average_daily_volume_usd, 0),
                "market_depth_usd": round(self.market_depth_usd, 0),
                "days_to_liquidate_10pct": round(self.days_to_liquidate_10pct, 1),
                "days_to_liquidate_25pct": round(self.days_to_liquidate_25pct, 1),
                "days_to_liquidate_50pct": round(self.days_to_liquidate_50pct, 1),
            },
            "stress": {
                "bid_ask_spread_stress_bps": round(self.bid_ask_spread_stress_bps, 1),
                "avg_volume_stress_usd": round(self.avg_volume_stress_usd, 0),
            },
            "market_impact": {
                "1pct_daily_volume_bps": round(self.market_impact_1pct_bps, 1),
                "5pct_daily_volume_bps": round(self.market_impact_5pct_bps, 1),
            },
            "score": {
                "liquidity_score": round(self.liquidity_score, 1),
                "liquidity_tier": self.liquidity_tier,
            },
        }


@dataclass
class PortfolioLiquidityResult:
    """Portfolio-level liquidity analysis."""
    total_principal_usd: float
    weighted_spread_bps: float
    weighted_liquidity_score: float
    total_adv_usd: float          # Total average daily volume
    days_to_liquidate_full: float
    liquidity_value_at_risk_bps: float  # LVaR
    market_impact_cost_usd: float
    concentration_risk: float     # HHI of liquidity sources
    instrument_profiles: list[LiquidityProfile]
    recommendations: list[str]

    def to_dict(self) -> dict:
        return {
            "total_principal_usd": round(self.total_principal_usd, 0),
            "weighted_spread_bps": round(self.weighted_spread_bps, 1),
            "weighted_liquidity_score": round(self.weighted_liquidity_score, 1),
            "total_adv_usd": round(self.total_adv_usd, 0),
            "days_to_liquidate_full": round(self.days_to_liquidate_full, 1),
            "liquidity_var_bps": round(self.liquidity_value_at_risk_bps, 1),
            "market_impact_cost_usd": round(self.market_impact_cost_usd, 0),
            "concentration_risk_hhi": round(self.concentration_risk, 0),
            "instruments": [p.to_dict() for p in self.instrument_profiles],
            "recommendations": self.recommendations,
        }


# ══════════════════════════════════════════════════════════════════════
# LIQUIDITY PARAMETERS BY INSTRUMENT TYPE
# ══════════════════════════════════════════════════════════════════════

# Base liquidity parameters for different sovereign instrument types
LIQUIDITY_PARAMS: dict[str, dict] = {
    "treasury_bond": {
        "normal_spread_bps_range": (1, 8),
        "stress_spread_bps_range": (15, 80),
        "adv_to_principal_pct": (0.3, 2.0),     # Daily volume as % of outstanding
        "stress_volume_multiplier": 0.2,        # Volume drops to 20% in stress
        "market_impact_coefficient": 0.1,       # Impact per 1% of ADV
        "tier": "tier1" if True else "tier2",
    },
    "eurobond": {
        "normal_spread_bps_range": (5, 25),
        "stress_spread_bps_range": (40, 200),
        "adv_to_principal_pct": (0.1, 0.8),
        "stress_volume_multiplier": 0.15,
        "market_impact_coefficient": 0.15,
        "tier": "tier2",
    },
    "frn": {
        "normal_spread_bps_range": (3, 15),
        "stress_spread_bps_range": (20, 100),
        "adv_to_principal_pct": (0.2, 1.2),
        "stress_volume_multiplier": 0.25,
        "market_impact_coefficient": 0.12,
        "tier": "tier1",
    },
    "floating_rate_note": {
        "normal_spread_bps_range": (3, 15),
        "stress_spread_bps_range": (20, 100),
        "adv_to_principal_pct": (0.2, 1.2),
        "stress_volume_multiplier": 0.25,
        "market_impact_coefficient": 0.12,
        "tier": "tier1",
    },
    "treasury_bill": {
        "normal_spread_bps_range": (0.5, 3),
        "stress_spread_bps_range": (5, 30),
        "adv_to_principal_pct": (0.5, 3.0),
        "stress_volume_multiplier": 0.3,
        "market_impact_coefficient": 0.05,
        "tier": "tier1",
    },
    "inflation_linked": {
        "normal_spread_bps_range": (5, 20),
        "stress_spread_bps_range": (30, 150),
        "adv_to_principal_pct": (0.1, 0.5),
        "stress_volume_multiplier": 0.1,
        "market_impact_coefficient": 0.2,
        "tier": "tier2",
    },
    "samurai_bond": {
        "normal_spread_bps_range": (10, 40),
        "stress_spread_bps_range": (50, 250),
        "adv_to_principal_pct": (0.05, 0.3),
        "stress_volume_multiplier": 0.08,
        "market_impact_coefficient": 0.25,
        "tier": "tier3",
    },
    "dim_sum_bond": {
        "normal_spread_bps_range": (15, 60),
        "stress_spread_bps_range": (80, 400),
        "adv_to_principal_pct": (0.03, 0.2),
        "stress_volume_multiplier": 0.05,
        "market_impact_coefficient": 0.3,
        "tier": "tier3",
    },
    "sukuk": {
        "normal_spread_bps_range": (10, 50),
        "stress_spread_bps_range": (60, 300),
        "adv_to_principal_pct": (0.05, 0.3),
        "stress_volume_multiplier": 0.1,
        "market_impact_coefficient": 0.25,
        "tier": "tier3",
    },
}

# Liquidity premiums by currency (wider spreads for less liquid currencies)
CURRENCY_LIQUIDITY_PREMIUM: dict[str, float] = {
    "USD": 0.0,
    "EUR": 0.2,
    "GBP": 0.3,
    "JPY": 0.3,
    "CHF": 0.5,
    "CAD": 0.5,
    "AUD": 0.7,
    "SEK": 0.8,
    "NOK": 0.8,
    "SGD": 1.0,
    "HKD": 1.0,
    "CNY": 2.0,
    "INR": 2.5,
    "BRL": 3.0,
    "MXN": 2.5,
    "ZAR": 3.5,
    "TRY": 4.0,
    "SAR": 1.5,
    "PLN": 1.5,
    "CZK": 1.5,
    "HUF": 2.0,
    "RUB": 5.0,  # Effectively illiquid under sanctions
}


class LiquidityRiskModel:
    """Models liquidity risk for sovereign bond portfolios.

    Goes beyond simple bid-ask by modeling:
    1. Time to liquidate (how long to exit positions)
    2. Market impact (price movement from your own trading)
    3. Stress liquidity (what happens in a crisis)
    4. Liquidity-adjusted VaR (VaR + liquidity risk)
    5. Concentration risk (over-reliance on liquid instruments)
    """

    def analyze_instrument(self, instrument: dict) -> LiquidityProfile:
        """Analyze liquidity for a single instrument."""
        inst_type = instrument.get("instrument_type", "treasury_bond").lower()
        currency = instrument.get("currency", "USD")
        principal = instrument.get("principal_outstanding", 0)

        # Get base parameters
        params = LIQUIDITY_PARAMS.get(inst_type, LIQUIDITY_PARAMS["treasury_bond"])
        ccy_premium = CURRENCY_LIQUIDITY_PREMIUM.get(currency, 2.0)

        # Normal bid-ask spread
        spread_lo, spread_hi = params["normal_spread_bps_range"]
        normal_spread = (spread_lo + spread_hi) / 2 * (1 + ccy_premium * 0.1)

        # Stress bid-ask spread (3-5x wider)
        stress_lo, stress_hi = params["stress_spread_bps_range"]
        stress_spread = (stress_lo + stress_hi) / 2 * (1 + ccy_premium * 0.15)

        # Average daily volume (as % of outstanding)
        adv_lo, adv_hi = params["adv_to_principal_pct"]
        adv_pct = (adv_lo + adv_hi) / 2
        adv_usd = principal * adv_pct / 100

        # Stress volume
        stress_adv = adv_usd * params["stress_volume_multiplier"]

        # Market depth (typically 2-5x daily volume)
        market_depth = adv_usd * 3

        # Market impact (square-root model: impact = k * sqrt(trade_size / ADV))
        k = params["market_impact_coefficient"]
        impact_1pct = k * math.sqrt(0.01) * 10000  # Convert to bps
        impact_5pct = k * math.sqrt(0.05) * 10000

        # Days to liquidate (linear model with market impact constraint)
        def days_to_liquidate(target_pct: float) -> float:
            """Estimate days to liquidate target_pct of position."""
            target_usd = principal * target_pct
            # Can trade at most 15% of ADV per day without excessive impact
            max_daily = adv_usd * 0.15
            if max_daily <= 0:
                return 999.0
            base_days = target_usd / max_daily
            # Add 1 day per 10% of position due to market impact
            impact_days = target_pct * 10
            return base_days + impact_days

        days_10 = days_to_liquidate(0.10)
        days_25 = days_to_liquidate(0.25)
        days_50 = days_to_liquidate(0.50)

        # Liquidity score (1-10)
        score = 10.0
        # Penalize wide spreads
        if normal_spread > 50:
            score -= 3
        elif normal_spread > 20:
            score -= 2
        elif normal_spread > 10:
            score -= 1
        # Penalize low volume
        if adv_pct < 0.1:
            score -= 3
        elif adv_pct < 0.3:
            score -= 2
        elif adv_pct < 0.5:
            score -= 1
        # Penalize long liquidation times
        if days_25 > 20:
            score -= 2
        elif days_25 > 10:
            score -= 1
        # Currency penalty
        score -= min(2, ccy_premium * 0.3)

        score = max(1, min(10, score))

        # Tier classification
        if score >= 7:
            tier = "tier1"
        elif score >= 4:
            tier = "tier2"
        elif score >= 2:
            tier = "tier3"
        else:
            tier = "illiquid"

        return LiquidityProfile(
            instrument_id=instrument.get("id", instrument.get("isin", "unknown")),
            instrument_name=instrument.get("issuer_name", "Unknown"),
            currency=currency,
            instrument_type=inst_type,
            bid_ask_spread_bps=round(normal_spread, 1),
            average_daily_volume_usd=round(adv_usd, 0),
            market_depth_usd=round(market_depth, 0),
            days_to_liquidate_10pct=round(days_10, 1),
            days_to_liquidate_25pct=round(days_25, 1),
            days_to_liquidate_50pct=round(days_50, 1),
            bid_ask_spread_stress_bps=round(stress_spread, 1),
            avg_volume_stress_usd=round(stress_adv, 0),
            market_impact_1pct_bps=round(impact_1pct, 1),
            market_impact_5pct_bps=round(impact_5pct, 1),
            liquidity_score=round(score, 1),
            liquidity_tier=tier,
        )

    def analyze_portfolio(self, instruments: list[dict]) -> PortfolioLiquidityResult:
        """Analyze liquidity for an entire portfolio."""
        if not instruments:
            return PortfolioLiquidityResult(
                total_principal_usd=0, weighted_spread_bps=0,
                weighted_liquidity_score=0, total_adv_usd=0,
                days_to_liquidate_full=0, liquidity_value_at_risk_bps=0,
                market_impact_cost_usd=0, concentration_risk=0,
                instrument_profiles=[], recommendations=["No instruments to analyze"],
            )

        profiles = [self.analyze_instrument(inst) for inst in instruments]
        total_principal = sum(inst.get("principal_outstanding", 0) for inst in instruments)

        if total_principal == 0:
            total_principal = sum(1 for _ in instruments)  # Equal weight fallback

        # Weighted averages
        weighted_spread = sum(
            p.bid_ask_spread_bps * inst.get("principal_outstanding", 0)
            for p, inst in zip(profiles, instruments)
        ) / total_principal if total_principal > 0 else 0

        weighted_score = sum(
            p.liquidity_score * inst.get("principal_outstanding", 0)
            for p, inst in zip(profiles, instruments)
        ) / total_principal if total_principal > 0 else 0

        total_adv = sum(p.average_daily_volume_usd for p in profiles)

        # Full portfolio liquidation time
        # Assume parallel liquidation across instruments
        days_to_full = max(p.days_to_liquidate_50pct for p in profiles) if profiles else 0

        # Liquidity-adjusted VaR (LVaR)
        # LVaR = VaR + liquidity spread / 2 * position size
        lvar_bps = weighted_spread / 2 + max(p.bid_ask_spread_stress_bps for p in profiles) / 10
        if profiles:
            lvar_bps = max(lvar_bps, max(p.bid_ask_spread_stress_bps for p in profiles) * 0.3)

        # Market impact cost (if portfolio needed to be liquidated quickly)
        market_impact_cost = sum(
            inst.get("principal_outstanding", 0) * p.market_impact_5pct_bps / 10000
            for p, inst in zip(profiles, instruments)
        )

        # Concentration risk (Herfindahl-Hirschman Index of ADV)
        adv_shares = [p.average_daily_volume_usd / total_adv if total_adv > 0 else 0 for p in profiles]
        hhi = sum(s ** 2 for s in adv_shares) * 10000

        # Recommendations
        recs = []
        illiquid_count = sum(1 for p in profiles if p.liquidity_tier in ("tier3", "illiquid"))
        if illiquid_count > 0:
            recs.append(
                f"{illiquid_count} instrument(s) are illiquid (tier3/illiquid). "
                f"Consider reducing exposure or accepting longer liquidation horizons."
            )
        if weighted_spread > 30:
            recs.append(
                f"Weighted bid-ask spread of {weighted_spread:.1f}bps is elevated. "
                f"Portfolio may face significant trading costs."
            )
        if hhi > 2500:
            recs.append(
                "Liquidity is concentrated in few instruments. Diversify across "
                "more liquid instruments to reduce concentration risk."
            )
        if lvar_bps > 50:
            recs.append(
                f"Liquidity-adjusted VaR of {lvar_bps:.1f}bps indicates significant "
                f"liquidity risk. Consider maintaining larger liquidity buffers."
            )
        if days_to_full > 30:
            recs.append(
                f"Full portfolio liquidation estimated at {days_to_full:.0f} days. "
                f"This may not meet liquidity requirements in a stress scenario."
            )
        if not recs:
            recs.append("Portfolio liquidity profile is adequate. No action required.")

        return PortfolioLiquidityResult(
            total_principal_usd=round(total_principal, 0),
            weighted_spread_bps=round(weighted_spread, 1),
            weighted_liquidity_score=round(weighted_score, 1),
            total_adv_usd=round(total_adv, 0),
            days_to_liquidate_full=round(days_to_full, 1),
            liquidity_value_at_risk_bps=round(lvar_bps, 1),
            market_impact_cost_usd=round(market_impact_cost, 0),
            concentration_risk=round(hhi, 0),
            instrument_profiles=profiles,
            recommendations=recs,
        )

    def stress_test_liquidity(self, instruments: list[dict], scenario: str = "global") -> dict:
        """Run a liquidity stress test under different crisis scenarios.

        Scenarios:
        - "global": Global risk-off (2008, 2020 style)
        - "em_crises": Emerging market sell-off
        - "rate_shock": Sharp rate increase
        - "geopolitical": War/sanctions event
        """
        stress_multipliers = {
            "global": {"spread_mult": 5.0, "volume_mult": 0.15, "depth_mult": 0.2},
            "em_crises": {"spread_mult": 8.0, "volume_mult": 0.1, "depth_mult": 0.1},
            "rate_shock": {"spread_mult": 3.0, "volume_mult": 0.3, "depth_mult": 0.4},
            "geopolitical": {"spread_mult": 10.0, "volume_mult": 0.05, "depth_mult": 0.05},
        }

        mults = stress_multipliers.get(scenario, stress_multipliers["global"])

        # Create stressed instruments
        stressed_instruments = []
        for inst in instruments:
            stressed = dict(inst)
            # Apply stress to spread
            base_profile = self.analyze_instrument(inst)
            stressed_spread = base_profile.bid_ask_spread_bps * mults["spread_mult"]
            stressed["stressed_spread_bps"] = round(stressed_spread, 1)
            stressed["stressed_adv_usd"] = round(
                base_profile.average_daily_volume_usd * mults["volume_mult"], 0
            )
            stressed_instruments.append(stressed)

        # Run analysis on stressed parameters
        result = self.analyze_portfolio(stressed_instruments)

        return {
            "scenario": scenario,
            "stress_parameters": mults,
            "stressed_result": result.to_dict(),
            "impact_summary": {
                "spread_increase_pct": round((mults["spread_mult"] - 1) * 100, 0),
                "volume_decrease_pct": round((1 - mults["volume_mult"]) * 100, 0),
                "estimated_trading_cost_usd": round(result.market_impact_cost_usd * mults["spread_mult"], 0),
                "days_to_liquidate_under_stress": round(result.days_to_liquidate_full / mults["volume_mult"], 1),
            },
        }


# ── Convenience Functions ──────────────────────────────────────────────

def analyze_portfolio_liquidity(instruments: list[dict]) -> dict:
    """Analyze portfolio liquidity and return result as dict."""
    model = LiquidityRiskModel()
    result = model.analyze_portfolio(instruments)
    return result.to_dict()


def stress_test_liquidity(instruments: list[dict], scenario: str = "global") -> dict:
    """Run liquidity stress test and return result as dict."""
    model = LiquidityRiskModel()
    return model.stress_test_liquidity(instruments, scenario)
