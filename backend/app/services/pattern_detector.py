"""
Market Pattern Detection Engine
================================

Identifies actionable patterns in market data:
- Trend detection (momentum, mean-reversion)
- Correlation shifts between asset classes
- Anomaly detection (unusual moves, regime changes)
- Yield curve shape analysis
- Volatility regime classification
"""

import math
from typing import Optional


def classify_volatility_regime(vix: float, realized_vol: float) -> dict:
    """Classify current volatility regime."""
    if vix < 15:
        regime = "low_stable"
        description = "Low volatility with compressed ranges. Favor carry trades and yield harvesting."
    elif vix < 20:
        regime = "elevated_trending"
        description = "Moderate volatility with directional moves. Trend-following strategies favored."
    elif vix < 28:
        regime = "high_uncertain"
        description = "Elevated uncertainty with wide ranges. Defensive positioning recommended."
    else:
        regime = "crisis"
        description = "Extreme volatility. Risk-off environment. Prioritize capital preservation."

    vix_term_structure = "contango" if vix > realized_vol else "backwardation"
    mean_reversion_signal = "strong" if vix > 25 else "moderate" if vix > 18 else "weak"

    return {
        "regime": regime,
        "description": description,
        "vix_level": vix,
        "realized_vol": realized_vol,
        "vix_term_structure": vix_term_structure,
        "mean_reversion_signal": mean_reversion_signal,
        "recommendation": _vol_recommendation(regime),
    }


def _vol_recommendation(regime: str) -> str:
    recommendations = {
        "low_stable": "Consider selling volatility through covered calls or selling premium. Duration extension is attractive.",
        "elevated_trending": "Follow the trend with moderate position sizing. Use trailing stops. Consider VIX call spreads as hedges.",
        "high_uncertain": "Reduce position sizes. Increase hedging. Shift toward shorter duration. Consider tail-risk protection.",
        "crisis": "Maximize defensive allocation. Move to short-term instruments. Avoid leveraged positions. Prepare for opportunities.",
    }
    return recommendations.get(regime, "Monitor conditions.")


def detect_yield_curve_patterns(rates: dict) -> list[dict]:
    """Detect patterns in the yield curve."""
    patterns = []
    maturities = sorted(rates.keys(), key=lambda x: _maturity_to_months(x))

    if len(maturities) < 3:
        return patterns

    # Check for inversion
    short = rates.get(maturities[0], 0)
    long = rates.get(maturities[-1], 0)
    spread = long - short

    if spread < 0:
        patterns.append({
            "type": "inversion",
            "severity": "high" if spread < -0.5 else "moderate",
            "description": f"Yield curve inverted by {abs(spread)*100:.0f}bps. Historically precedes recession within 12-20 months.",
            "action": "Consider extending duration to lock in elevated long-term rates before potential rate cuts.",
        })
    elif spread < 0.25:
        patterns.append({
            "type": "flat_curve",
            "severity": "moderate",
            "description": f"Yield curve nearly flat (spread: {spread*100:.0f}bps). Limited term premium for duration extension.",
            "action": "Focus on intermediate maturities (3-7Y) for best risk-adjusted carry.",
        })
    elif spread > 1.5:
        patterns.append({
            "type": "steep_curve",
            "severity": "low",
            "description": f"Yield curve steep (spread: {spread*100:.0f}bps). Strong term premium available.",
            "action": "Long-term issuance attractive. Consider 10-30Y maturities to capture steepness.",
        })

    # Check for kink (middle maturities mispriced)
    if len(maturities) >= 5:
        mid_idx = len(maturities) // 2
        mid_rate = rates.get(maturities[mid_idx], 0)
        avg_neighbors = (
            rates.get(maturities[mid_idx - 1], 0) +
            rates.get(maturities[mid_idx + 1], 0)
        ) / 2
        kink = mid_rate - avg_neighbors
        if abs(kink) > 0.15:
            patterns.append({
                "type": "kink",
                "severity": "moderate",
                "description": f"Yield curve kink at {maturities[mid_idx]} maturity ({kink*100:.0f}bps deviation). Potential relative value opportunity.",
                "action": f"Consider {'buying' if kink < 0 else 'issuing'} at the {maturities[mid_idx]} point for relative value.",
            })

    # Check for bear steepening vs bull steepening
    if len(maturities) >= 4:
        two_year = rates.get("2Y", rates.get(maturities[1], 0))
        ten_year = rates.get("10Y", rates.get(maturities[-2], 0))
        if ten_year > two_year and spread > 0.5:
            patterns.append({
                "type": "bear_steepening",
                "severity": "moderate",
                "description": "Bear steepening detected — long-end rates rising faster than short-end. Fiscal concerns or inflation expectations driving long rates.",
                "action": "Consider inflation-linked issuance. Shorten average maturity to reduce duration risk.",
            })

    return patterns


def detect_correlation_shifts(returns: dict[str, list[float]], window: int = 20) -> list[dict]:
    """Detect significant correlation changes between asset classes."""
    patterns = []
    assets = list(returns.keys())

    for i in range(len(assets)):
        for j in range(i + 1, len(assets)):
            a, b = assets[i], assets[j]
            r_a, r_b = returns[a], returns[b]

            if len(r_a) < window or len(r_b) < window:
                continue

            # Recent correlation
            recent = _pearson(r_a[-window:], r_b[-window:])
            # Longer-term correlation
            longer = _pearson(r_a[-window*3:], r_b[-window*3:]) if len(r_a) >= window*3 else recent

            shift = recent - longer
            if abs(shift) > 0.3:
                patterns.append({
                    "type": "correlation_shift",
                    "assets": [a, b],
                    "recent_correlation": round(recent, 3),
                    "baseline_correlation": round(longer, 3),
                    "shift": round(shift, 3),
                    "description": f"Correlation between {a} and {b} shifted from {longer:.2f} to {recent:.2f}. {'Diversification benefit changing.' if shift < 0 else 'Assets becoming more correlated.'}",
                    "action": "Review portfolio diversification. Consider rebalancing if correlation has moved significantly from portfolio assumptions.",
                })

    return patterns


def detect_anomalies(prices: list[float], threshold: float = 2.5) -> list[dict]:
    """Detect price anomalies (moves > threshold standard deviations)."""
    if len(prices) < 20:
        return []

    anomalies = []
    returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
    mean = sum(returns[-20:]) / 20
    std = math.sqrt(sum((r - mean) ** 2 for r in returns[-20:]) / 20)

    if std == 0:
        return []

    latest_return = returns[-1]
    z_score = (latest_return - mean) / std

    if abs(z_score) > threshold:
        direction = "up" if latest_return > 0 else "down"
        anomalies.append({
            "type": "price_anomaly",
            "severity": "critical" if abs(z_score) > 3.5 else "high",
            "z_score": round(z_score, 2),
            "return_pct": round(latest_return * 100, 2),
            "description": f"Unusual {direction} move of {abs(latest_return)*100:.2f}% ({abs(z_score):.1f} standard deviations from mean).",
            "action": "Investigate catalyst. Consider profit-taking if extended, or adding if fundamental thesis unchanged.",
        })

    return anomalies


def _pearson(x: list[float], y: list[float]) -> float:
    """Compute Pearson correlation coefficient."""
    n = min(len(x), len(y))
    if n < 2:
        return 0.0
    x, y = x[:n], y[:n]
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    den_x = math.sqrt(sum((x[i] - mx) ** 2 for i in range(n)))
    den_y = math.sqrt(sum((y[i] - my) ** 2 for i in range(n)))
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / (den_x * den_y)


def _maturity_to_months(label: str) -> int:
    """Convert maturity label to months for sorting."""
    mapping = {
        "1M": 1, "3M": 3, "6M": 6, "9M": 9,
        "1Y": 12, "2Y": 24, "3Y": 36, "5Y": 60,
        "7Y": 84, "10Y": 120, "20Y": 240, "30Y": 360,
    }
    return mapping.get(label, 12)


def generate_pattern_report(rates: dict, prices: list[float] = None,
                           returns: dict = None, vix: float = 15.0,
                           realized_vol: float = 12.0) -> dict:
    """Generate a comprehensive pattern detection report."""
    # Volatility regime
    vol = classify_volatility_regime(vix, realized_vol)

    # Yield curve patterns
    yc_patterns = detect_yield_curve_patterns(rates) if rates else []

    # Price anomalies
    anomalies = detect_anomalies(prices) if prices else []

    # Correlation shifts
    corr_shifts = detect_correlation_shifts(returns) if returns else []

    # Combine all patterns
    all_patterns = []
    for p in yc_patterns:
        all_patterns.append({**p, "source": "yield_curve"})
    for p in anomalies:
        all_patterns.append({**p, "source": "price_data"})
    for p in corr_shifts:
        all_patterns.append({**p, "source": "correlation"})

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "moderate": 2, "low": 3}
    all_patterns.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 3))

    return {
        "volatility_regime": vol,
        "patterns": all_patterns,
        "pattern_count": len(all_patterns),
        "high_severity_count": sum(1 for p in all_patterns if p.get("severity") in ("critical", "high")),
    }
