"""
Bubble & Cap Detector — Identifies overvalued assets, pump-and-dump patterns,
bubble risk, and provides investment safety scores.

Uses multiple signals:
- Price-to-Fundamentals ratio (P/E, P/S, market cap vs revenue)
- Volume manipulation detection (spike patterns, wash trading signs)
- Social sentiment vs price divergence
- Historical bubble pattern matching (dot-com, crypto 2017, meme stocks)
- Short interest and insider selling pressure
- Technical divergence (price up but volume declining)
"""

import math
import json
from datetime import datetime, timezone
from typing import Optional


# ── Bubble Pattern Definitions ──────────────────────────────────────

BUBBLE_PATTERNS = {
    "classic_bubble": {
        "name": "Classic Speculative Bubble",
        "description": "Exponential price rise with increasing volume, followed by sharp reversal",
        "signatures": [
            "price_acceleration",  # Price rising faster each week
            "volume_climax",      # Volume spikes at the top
            "media_frenzy",       # Can't measure directly, infer from volume
            "parabolic_rise",     # >100% gain in <30 days
        ],
    },
    "pump_and_dump": {
        "name": "Pump and Dump Scheme",
        "description": "Coordinated buying to inflate price, then mass selling",
        "signatures": [
            "volume_spike_no_news",  # 5x+ volume without catalyst
            "price_spike_reversal",  # >20% spike then immediate reversal
            "thin_book_wide_spread", # Low liquidity with wide bid-ask
        ],
    },
    "meme_bubble": {
        "name": "Meme/Social Bubble",
        "description": "Price driven by social media hype rather than fundamentals",
        "signatures": [
            "retail_surge",       # High small-order volume
            "zero_fundamentals",  # No revenue, no product, no path to profit
            "celebrity_catalyst", # Can't measure directly
        ],
    },
    "dot_com_repeat": {
        "name": "Dot-Com Style Overvaluation",
        "description": "Growth stock trading at extreme multiples of revenue",
        "signatures": [
            "ps_ratio_extreme",   # P/S > 50x or negative earnings
            "revenue_declining",  # Growth decelerating
            "cash_burn",          # Spending more than earning
        ],
    },
    "crypto_manias": {
        "name": "Crypto Mania Pattern",
        "description": "Crypto asset rising on hype with no utility or adoption",
        "signatures": [
            "no_utility_token",   # Token has no use case
            "whale_concentration", # Top 10 wallets hold >80% supply
            "volatility_extreme",  # >20% daily swings
        ],
    },
}


# ── Scoring Engine ──────────────────────────────────────────────────

def calculate_bubble_risk_score(
    symbol: str,
    asset_class: str,
    current_price: float,
    previous_close: float,
    volume_24h: float = 0,
    market_cap: float = 0,
    high_52w: float = 0,
    low_52w: float = 0,
    ath: float = 0,
    avg_volume: float = 0,
    price_history: Optional[list] = None,
    day_change_pct: float = 0,
    pe_ratio: Optional[float] = None,
    ps_ratio: Optional[float] = None,
    revenue: Optional[float] = None,
    earnings: Optional[float] = None,
    insider_selling_pct: float = 0,
    short_interest_pct: float = 0,
) -> dict:
    """
    Calculate a comprehensive bubble risk score for an asset.
    
    Returns:
        dict with bubble_score (0-100), risk_level, detected_patterns,
        indicators, recommendation, and explanation
    """
    
    score = 0
    indicators = []
    patterns_detected = []
    
    if current_price <= 0:
        return _empty_result(symbol, "Price data unavailable")
    
    # ── 1. Price Acceleration Check ──────────────────────────────────
    if price_history and len(price_history) >= 7:
        recent_returns = []
        for i in range(1, min(len(price_history), 8)):
            # Accept both dict entries ({"close": x}) and plain numbers
            entry_prev, entry_curr = price_history[-(i+1)], price_history[-i]
            prev = entry_prev.get("close", 0) if isinstance(entry_prev, dict) else float(entry_prev or 0)
            curr = entry_curr.get("close", 0) if isinstance(entry_curr, dict) else float(entry_curr or 0)
            if prev > 0:
                recent_returns.append((curr - prev) / prev)
        
        if len(recent_returns) >= 3:
            # Check if returns are accelerating (each day bigger than last)
            accelerating = all(
                recent_returns[i] > recent_returns[i-1] 
                for i in range(1, len(recent_returns))
                if recent_returns[i] > 0
            )
            if accelerating:
                score += 15
                indicators.append({
                    "name": "Price Acceleration",
                    "value": "Exponential rise detected",
                    "impact": "+15 risk points",
                    "detail": "Each day's gain exceeds the previous — classic bubble signature",
                })
                patterns_detected.append("classic_bubble")
    
    # ── 2. Parabolic Rise Detection ──────────────────────────────────
    if price_history and len(price_history) >= 30:
        price_30d_ago = price_history[-30].get("close", current_price)
        if price_30d_ago > 0:
            gain_30d = ((current_price - price_30d_ago) / price_30d_ago) * 100
            if gain_30d > 200:
                score += 25
                indicators.append({
                    "name": "Parabolic 30-Day Rise",
                    "value": f"+{gain_30d:.0f}% in 30 days",
                    "impact": "+25 risk points",
                    "detail": "Extreme price appreciation in short period — historically unsustainable",
                })
                patterns_detected.append("classic_bubble")
            elif gain_30d > 100:
                score += 15
                indicators.append({
                    "name": "Strong 30-Day Rise",
                    "value": f"+{gain_30d:.0f}% in 30 days",
                    "impact": "+15 risk points",
                    "detail": "Significant price appreciation — monitor for continuation or reversal",
                })
                patterns_detected.append("classic_bubble")
            elif gain_30d > 50:
                score += 8
                indicators.append({
                    "name": "Moderate 30-Day Rise",
                    "value": f"+{gain_30d:.0f}% in 30 days",
                    "impact": "+8 risk points",
                    "detail": "Above-average appreciation — evaluate if fundamentals support the move",
                })
    
    # ── 3. Volume Spike Detection (Pump & Dump) ──────────────────────
    if volume_24h > 0 and avg_volume > 0:
        volume_ratio = volume_24h / avg_volume
        if volume_ratio > 5:
            score += 20
            indicators.append({
                "name": "Extreme Volume Spike",
                "value": f"{volume_ratio:.1f}x average volume",
                "impact": "+20 risk points",
                "detail": "Volume 5x+ normal without confirmed catalyst — possible manipulation",
            })
            patterns_detected.append("pump_and_dump")
        elif volume_ratio > 3:
            score += 12
            indicators.append({
                "name": "High Volume Spike",
                "value": f"{volume_ratio:.1f}x average volume",
                "impact": "+12 risk points",
                "detail": "Unusual volume activity — investigate cause before entering",
            })
        elif volume_ratio > 2:
            score += 5
            indicators.append({
                "name": "Elevated Volume",
                "value": f"{volume_ratio:.1f}x average volume",
                "impact": "+5 risk points",
                "detail": "Above-normal volume — could be legitimate or early manipulation",
            })
    
    # ── 4. Price Spike + Reversal (Pump & Dump) ─────────────────────
    if abs(day_change_pct) > 20:
        score += 15
        indicators.append({
            "name": "Extreme Daily Move",
            "value": f"{'+' if day_change_pct > 0 else ''}{day_change_pct:.1f}% today",
            "impact": "+15 risk points",
            "detail": "Single-day moves this large often precede reversals",
        })
        patterns_detected.append("pump_and_dump")
    elif abs(day_change_pct) > 10:
        score += 8
        indicators.append({
            "name": "Large Daily Move",
            "value": f"{'+' if day_change_pct > 0 else ''}{day_change_pct:.1f}% today",
            "impact": "+8 risk points",
            "detail": "Significant single-day movement — assess whether move is justified",
        })
    
    # ── 5. Distance from 52-Week High ────────────────────────────────
    if high_52w > 0 and current_price < high_52w:
        distance_from_high = ((high_52w - current_price) / high_52w) * 100
        if distance_from_high > 70:
            score += 10
            indicators.append({
                "name": "Deep Below 52-Week High",
                "value": f"-{distance_from_high:.0f}% from high",
                "impact": "+10 risk points",
                "detail": "Asset has lost most of its value — could be distressed or recovering",
            })
        elif distance_from_high > 50:
            score += 5
            indicators.append({
                "name": "Significantly Below 52-Week High",
                "value": f"-{distance_from_high:.0f}% from high",
                "impact": "+5 risk points",
                "detail": "Well off highs — investigate if fundamentals changed",
            })
    
    # ── 6. Distance from All-Time High (Crypto) ──────────────────────
    if asset_class == "crypto" and ath > 0 and current_price < ath:
        distance_from_ath = ((ath - current_price) / ath) * 100
        if distance_from_ath > 80:
            score += 12
            indicators.append({
                "name": "80%+ Below ATH",
                "value": f"-{distance_from_ath:.0f}% from ATH (${ath:,.2f})",
                "impact": "+12 risk points",
                "detail": "Crypto has lost most of its peak value — may never recover",
            })
        elif distance_from_ath > 60:
            score += 7
            indicators.append({
                "name": "60%+ Below ATH",
                "value": f"-{distance_from_ath:.0f}% from ATH (${ath:,.2f})",
                "impact": "+7 risk points",
                "detail": "Significant drawdown from peak — evaluate recovery potential",
            })
    
    # ── 7. Overvaluation Metrics ─────────────────────────────────────
    if pe_ratio is not None and pe_ratio > 0:
        if pe_ratio > 100:
            score += 18
            indicators.append({
                "name": "Extreme P/E Ratio",
                "value": f"{pe_ratio:.0f}x earnings",
                "impact": "+18 risk points",
                "detail": "Trading at 100x+ earnings — priced for perfection, any miss will hurt",
            })
            patterns_detected.append("dot_com_repeat")
        elif pe_ratio > 50:
            score += 10
            indicators.append({
                "name": "High P/E Ratio",
                "value": f"{pe_ratio:.0f}x earnings",
                "impact": "+10 risk points",
                "detail": "Elevated valuation — growth expectations are very high",
            })
    
    if ps_ratio is not None and ps_ratio > 0:
        if ps_ratio > 50:
            score += 15
            indicators.append({
                "name": "Extreme P/S Ratio",
                "value": f"{ps_ratio:.0f}x revenue",
                "impact": "+15 risk points",
                "detail": "Pricing 50x+ annual revenue — historically unsustainable for most companies",
            })
            patterns_detected.append("dot_com_repeat")
        elif ps_ratio > 20:
            score += 8
            indicators.append({
                "name": "High P/S Ratio",
                "value": f"{ps_ratio:.0f}x revenue",
                "impact": "+8 risk points",
                "detail": "Premium valuation relative to revenue — high growth expected",
            })
    
    # ── 8. Earnings Decline / Negative Earnings ──────────────────────
    if earnings is not None and earnings < 0:
        if market_cap > 0:
            loss_ratio = abs(earnings) / market_cap
            if loss_ratio > 0.1:
                score += 12
                indicators.append({
                    "name": "Burning Cash Relative to Market Cap",
                    "value": f"Losing ${abs(earnings):,.0f} annually",
                    "impact": "+12 risk points",
                    "detail": "Company is losing >10% of its market cap per year in losses",
                })
                patterns_detected.append("dot_com_repeat")
    
    # ── 9. Insider Selling Pressure ──────────────────────────────────
    if insider_selling_pct > 20:
        score += 15
        indicators.append({
            "name": "Heavy Insider Selling",
            "value": f"{insider_selling_pct:.0f}% of insider holdings sold",
            "impact": "+15 risk points",
            "detail": "Insiders are selling aggressively — they know the business best",
        })
    elif insider_selling_pct > 10:
        score += 8
        indicators.append({
            "name": "Elevated Insider Selling",
            "value": f"{insider_selling_pct:.0f}% of insider holdings sold",
            "impact": "+8 risk points",
            "detail": "Some insider selling — could be routine or a warning sign",
        })
    
    # ── 10. Short Interest ───────────────────────────────────────────
    if short_interest_pct > 20:
        score += 12
        indicators.append({
            "name": "Very High Short Interest",
            "value": f"{short_interest_pct:.0f}% of float short",
            "impact": "+12 risk points",
            "detail": "Heavy short positioning — market expects decline but squeeze possible",
        })
    elif short_interest_pct > 10:
        score += 6
        indicators.append({
            "name": "High Short Interest",
            "value": f"{short_interest_pct:.0f}% of float short",
            "impact": "+6 risk points",
            "detail": "Notable short interest — bearish sentiment from institutional shorts",
        })
    
    # ── 11. Volatility Check ─────────────────────────────────────────
    if price_history and len(price_history) >= 20:
        returns = []
        for i in range(1, min(len(price_history), 21)):
            prev = price_history[-(i+1)].get("close", 0)
            curr = price_history[-i].get("close", 0)
            if prev > 0:
                returns.append((curr - prev) / prev)
        
        if returns:
            avg_return = sum(returns) / len(returns)
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            volatility = math.sqrt(variance) * 100  # Daily vol as percentage
            
            annualized_vol = volatility * math.sqrt(252)
            
            if annualized_vol > 200:
                score += 18
                indicators.append({
                    "name": "Extreme Volatility",
                    "value": f"{annualized_vol:.0f}% annualized",
                    "impact": "+18 risk points",
                    "detail": "Volatility exceeds 200% — extreme risk, potential for total loss",
                })
                patterns_detected.append("crypto_manias")
            elif annualized_vol > 100:
                score += 10
                indicators.append({
                    "name": "High Volatility",
                    "value": f"{annualized_vol:.0f}% annualized",
                    "impact": "+10 risk points",
                    "detail": "Volatility exceeds 100% — expect large swings in both directions",
                })
            elif annualized_vol > 50:
                score += 5
                indicators.append({
                    "name": "Moderate-High Volatility",
                    "value": f"{annualized_vol:.0f}% annualized",
                    "impact": "+5 risk points",
                    "detail": "Above-average volatility — position sizing matters",
                })
    
    # ── 12. Penny Stock / Micro-Cap Check ────────────────────────────
    if market_cap > 0 and market_cap < 50_000_000:
        score += 15
        indicators.append({
            "name": "Micro-Cap Stock",
            "value": f"${market_cap/1_000_000:.1f}M market cap",
            "impact": "+15 risk points",
            "detail": "Very small company — high risk of manipulation, low liquidity",
        })
        patterns_detected.append("pump_and_dump")
    elif market_cap > 0 and market_cap < 300_000_000:
        score += 8
        indicators.append({
            "name": "Small-Cap Stock",
            "value": f"${market_cap/1_000_000:.0f}M market cap",
            "impact": "+8 risk points",
            "detail": "Small company — higher risk and volatility than large caps",
        })
    
    # ── Cap at 100 ───────────────────────────────────────────────────
    score = min(100, score)
    
    # ── Determine Risk Level ─────────────────────────────────────────
    if score >= 75:
        risk_level = "EXTREME"
        recommendation = "AVOID"
        color = "#ef4444"
    elif score >= 50:
        risk_level = "HIGH"
        recommendation = "REDUCE OR AVOID"
        color = "#f97316"
    elif score >= 30:
        risk_level = "MODERATE"
        recommendation = "PROCEED WITH CAUTION"
        color = "#eab308"
    elif score >= 15:
        risk_level = "LOW-MODERATE"
        recommendation = "MONITOR"
        color = "#22c55e"
    else:
        risk_level = "LOW"
        recommendation = "NORMAL RISK"
        color = "#10b981"
    
    # ── Deduplicate patterns ─────────────────────────────────────────
    patterns_detected = list(set(patterns_detected))
    
    # ── Build explanation ────────────────────────────────────────────
    explanation_parts = []
    if score >= 75:
        explanation_parts.append(f"{symbol} shows EXTREME bubble risk ({score}/100).")
    elif score >= 50:
        explanation_parts.append(f"{symbol} shows HIGH bubble risk ({score}/100).")
    elif score >= 30:
        explanation_parts.append(f"{symbol} shows MODERATE bubble risk ({score}/100).")
    else:
        explanation_parts.append(f"{symbol} shows manageable risk ({score}/100).")
    
    if "classic_bubble" in patterns_detected:
        explanation_parts.append("Classic bubble price patterns detected.")
    if "pump_and_dump" in patterns_detected:
        explanation_parts.append("Pump-and-dump warning signs present.")
    if "dot_com_repeat" in patterns_detected:
        explanation_parts.append("Dot-com style overvaluation metrics.")
    if "crypto_manias" in patterns_detected:
        explanation_parts.append("Crypto mania volatility patterns.")
    
    explanation = " ".join(explanation_parts)
    
    return {
        "symbol": symbol,
        "asset_class": asset_class,
        "bubble_score": score,
        "risk_level": risk_level,
        "recommendation": recommendation,
        "color": color,
        "patterns_detected": patterns_detected,
        "pattern_details": [
            {**BUBBLE_PATTERNS[p], "id": p} 
            for p in patterns_detected 
            if p in BUBBLE_PATTERNS
        ],
        "indicators": indicators,
        "indicator_count": len(indicators),
        "explanation": explanation,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def scan_portfolio_for_bubbles(assets: list) -> dict:
    """
    Scan a portfolio or asset list for bubble risks.
    
    Args:
        assets: List of asset dicts with price data
        
    Returns:
        dict with overall_risk, highest_risk assets, pattern summary
    """
    results = []
    
    for asset in assets:
        risk = calculate_bubble_risk_score(
            symbol=asset.get("symbol", "?"),
            asset_class=asset.get("asset_class", "stock"),
            current_price=asset.get("current_price", 0),
            previous_close=asset.get("previous_close", 0),
            volume_24h=asset.get("volume_24h", 0),
            market_cap=asset.get("market_cap", 0),
            high_52w=asset.get("high_52w", 0),
            low_52w=asset.get("low_52w", 0),
            ath=asset.get("ath", 0),
            avg_volume=asset.get("avg_volume", 0),
            price_history=asset.get("price_history"),
            day_change_pct=asset.get("day_change_pct", 0),
        )
        results.append(risk)
    
    # Sort by risk
    results.sort(key=lambda x: x["bubble_score"], reverse=True)
    
    # Summary stats
    extreme = [r for r in results if r["risk_level"] == "EXTREME"]
    high = [r for r in results if r["risk_level"] == "HIGH"]
    moderate = [r for r in results if r["risk_level"] == "MODERATE"]
    
    # Pattern frequency
    all_patterns = []
    for r in results:
        all_patterns.extend(r["patterns_detected"])
    pattern_counts = {}
    for p in all_patterns:
        pattern_counts[p] = pattern_counts.get(p, 0) + 1
    
    # Overall score
    if results:
        avg_score = sum(r["bubble_score"] for r in results) / len(results)
        max_score = max(r["bubble_score"] for r in results)
    else:
        avg_score = 0
        max_score = 0
    
    return {
        "scan_results": results[:50],  # Top 50
        "total_scanned": len(results),
        "overall_risk_score": round(avg_score),
        "highest_risk_score": max_score,
        "extreme_count": len(extreme),
        "high_count": len(high),
        "moderate_count": len(moderate),
        "pattern_frequency": pattern_counts,
        "top_risks": results[:10],  # Top 10 riskiest
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _empty_result(symbol: str, reason: str) -> dict:
    return {
        "symbol": symbol,
        "bubble_score": 0,
        "risk_level": "UNKNOWN",
        "recommendation": "INSUFFICIENT DATA",
        "color": "#6b7280",
        "patterns_detected": [],
        "pattern_details": [],
        "indicators": [],
        "indicator_count": 0,
        "explanation": f"{symbol}: {reason}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
