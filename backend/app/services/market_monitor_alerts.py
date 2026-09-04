"""Market Monitor Alert Engine & Daily Insights Generator

Evaluates user alerts against new market data and generates
daily insights with actionable recommendations.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid


def evaluate_alert(alert: dict, market_data: dict) -> Optional[dict]:
    """Evaluate a single alert against current market data.

    Args:
        alert: User alert configuration
        market_data: Current market data for the alert's asset

    Returns:
        Triggered alert dict if condition met, else None
    """
    alert_type = alert.get("alert_type", "")
    threshold = alert.get("threshold", 0)
    condition = alert.get("condition", "")
    current_price = market_data.get("current_price", 0)
    day_change = market_data.get("day_change_pct", 0)
    rsi = market_data.get("rsi_14")
    volume_ratio = market_data.get("volume_ratio")

    triggered = False
    trigger_value = None
    reason = ""

    if alert_type == "price_above" and current_price > threshold:
        triggered = True
        trigger_value = current_price
        reason = f"Price ${current_price:.2f} crossed above ${threshold:.2f}"

    elif alert_type == "price_below" and current_price < threshold:
        triggered = True
        trigger_value = current_price
        reason = f"Price ${current_price:.2f} dropped below ${threshold:.2f}"

    elif alert_type == "price_change_pct" and abs(day_change) > threshold:
        triggered = True
        trigger_value = day_change
        reason = f"Price changed {day_change:+.1f}% (threshold: ±{threshold}%)"

    elif alert_type == "rsi_cross":
        if condition == "above" and rsi and rsi > threshold:
            triggered = True
            trigger_value = rsi
            reason = f"RSI crossed above {threshold} (current: {rsi:.0f})"
        elif condition == "below" and rsi and rsi < threshold:
            triggered = True
            trigger_value = rsi
            reason = f"RSI crossed below {threshold} (current: {rsi:.0f})"

    elif alert_type == "volume_spike" and volume_ratio and volume_ratio > threshold:
        triggered = True
        trigger_value = volume_ratio
        reason = f"Volume {volume_ratio:.1f}x average (threshold: {threshold}x)"

    elif alert_type == "macd_cross":
        macd = market_data.get("macd", {})
        if condition == "bullish" and macd and macd.get("bullish"):
            triggered = True
            reason = "MACD bullish crossover detected"
        elif condition == "bearish" and macd and macd.get("bearish"):
            triggered = True
            reason = "MACD bearish crossover detected"

    if triggered:
        # Check repeat setting
        repeat = alert.get("repeat", "once")
        last_triggered = alert.get("triggered_at")
        if repeat == "once" and last_triggered:
            return None  # Already triggered, don't re-trigger
        if repeat == "daily_summary" and last_triggered:
            if last_triggered and (datetime.now(timezone.utc) - last_triggered).total_seconds() < 86400:
                return None  # Already triggered today

        return {
            "alert_id": alert.get("id"),
            "user_id": alert.get("user_id"),
            "asset_symbol": market_data.get("symbol", ""),
            "triggered_at": datetime.now(timezone.utc),
            "trigger_value": trigger_value,
            "threshold_value": threshold,
            "reason": reason,
            "delivery_channels": alert.get("delivery_channels", ["in_app"]),
        }

    return None


def generate_daily_insights(
    market_assets: list[dict],
    portfolio: Optional[dict] = None,
    alerts_triggered: Optional[list[dict]] = None,
) -> list[dict]:
    """Generate daily insights from market data and portfolio state.

    Returns list of insight records sorted by priority.
    """
    insights = []
    now = datetime.now(timezone.utc)

    # 1. Market Pulse (always generated)
    total_assets = len(market_assets)
    gainers = [a for a in market_assets if a.get("day_change_pct", 0) > 2]
    losers = [a for a in market_assets if a.get("day_change_pct", 0) < -2]

    pulse_summary = f"{total_assets} assets tracked. "
    if gainers:
        pulse_summary += f"{len(gainers)} gainers (>+2%). "
    if losers:
        pulse_summary += f"{len(losers)} losers (>-2%). "

    insights.append({
        "id": str(uuid.uuid4()),
        "insight_type": "market_pulse",
        "title": "Daily Market Pulse",
        "summary": pulse_summary,
        "details": {
            "gainers_count": len(gainers),
            "losers_count": len(losers),
            "top_gainer": max(gainers, key=lambda x: x.get("day_change_pct", 0))["symbol"] if gainers else None,
            "top_loser": min(losers, key=lambda x: x.get("day_change_pct", 0))["symbol"] if losers else None,
        },
        "assets_involved": [],
        "priority": "medium",
        "action_type": None,
        "confidence_score": 0.9,
        "created_at": now.isoformat(),
    })

    # 2. Top Movers
    top_movers = sorted(market_assets, key=lambda x: abs(x.get("day_change_pct", 0)), reverse=True)[:5]
    for asset in top_movers:
        change = asset.get("day_change_pct", 0)
        if abs(change) > 3:
            action = "sell" if change > 8 else "hold" if change > 5 else "watch"
            insights.append({
                "id": str(uuid.uuid4()),
                "insight_type": "top_movers",
                "title": f"{asset['symbol']} {'+' if change > 0 else ''}{change:.1f}%",
                "summary": f"{asset.get('name', asset['symbol'])} moved {'up' if change > 0 else 'down'} {abs(change):.1f}%. "
                           f"{'Consider taking profits if overallocated.' if change > 8 else 'Monitor for continuation.'}",
                "details": {"price": asset.get("current_price"), "change_pct": change},
                "assets_involved": [asset.get("symbol", "")],
                "priority": "high" if abs(change) > 8 else "medium",
                "action_type": action,
                "confidence_score": 0.7,
                "created_at": now.isoformat(),
            })

    # 3. Emerging Opportunities (stocks with discovery score > 60)
    rising_stars = [a for a in market_assets if a.get("discovery_score", 0) > 60]
    for asset in rising_stars[:3]:
        score = asset.get("discovery_score", 0)
        classification = asset.get("classification", "watch")
        signals = asset.get("discovery_signals", {})
        signal_summary = ", ".join(signals.keys()) if signals else "multiple signals"

        insights.append({
            "id": str(uuid.uuid4()),
            "insight_type": "emerging_opportunity",
            "title": f"{'Rising Star' if classification == 'rising_star' else 'Watch'}: {asset['symbol']}",
            "summary": f"Discovery score: {score}/100. Signals: {signal_summary}. "
                       f"{'Strong opportunity — consider position.' if classification == 'rising_star' else 'Worth monitoring.'}",
            "details": {"score": score, "signals": signals, "classification": classification},
            "assets_involved": [asset.get("symbol", "")],
            "priority": "high" if classification == "rising_star" else "medium",
            "action_type": "buy" if classification == "rising_star" else "watch",
            "confidence_score": score / 100,
            "created_at": now.isoformat(),
        })

    # 4. Risk Warnings
    if portfolio:
        allocation = portfolio.get("allocation", {})
        total = portfolio.get("total_value", 0)
        if total > 0:
            for asset_class, pct in allocation.items():
                if asset_class == "crypto" and pct > 30:
                    insights.append({
                        "id": str(uuid.uuid4()),
                        "insight_type": "risk_warning",
                        "title": "Crypto Allocation High",
                        "summary": f"Crypto allocation at {pct:.0f}% of portfolio. "
                                   f"Historical max recommended: 25%. Consider rebalancing.",
                        "details": {"allocation": allocation, "asset_class": asset_class},
                        "assets_involved": [],
                        "priority": "high",
                        "action_type": "rebalance",
                        "confidence_score": 0.8,
                        "created_at": now.isoformat(),
                    })

    # 5. Alert-based insights
    if alerts_triggered:
        for alert in alerts_triggered[:5]:
            insights.append({
                "id": str(uuid.uuid4()),
                "insight_type": "earnings_alert" if "earnings" in alert.get("reason", "").lower() else "sentiment_shift",
                "title": f"Alert: {alert.get('asset_symbol', 'Unknown')}",
                "summary": alert.get("reason", "Alert triggered"),
                "details": {"alert_id": alert.get("alert_id")},
                "assets_involved": [alert.get("asset_symbol", "")],
                "priority": "critical",
                "action_type": None,
                "confidence_score": 1.0,
                "created_at": now.isoformat(),
            })

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    insights.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))

    return insights


def generate_market_pulse_summary(market_assets: list[dict], yields: dict = None) -> str:
    """Generate a one-paragraph market pulse summary."""
    stocks = [a for a in market_assets if a.get("asset_class") == "stock"]
    crypto = [a for a in market_assets if a.get("asset_class") == "crypto"]

    stock_change = sum(a.get("day_change_pct", 0) for a in stocks) / len(stocks) if stocks else 0
    crypto_change = sum(a.get("day_change_pct", 0) for a in crypto) / len(crypto) if crypto else 0

    parts = []
    if stock_change > 0.5:
        parts.append(f"Equities broadly positive (+{stock_change:.1f}% avg)")
    elif stock_change < -0.5:
        parts.append(f"Equities under pressure ({stock_change:.1f}% avg)")
    else:
        parts.append("Equities mixed")

    if crypto_change > 2:
        parts.append(f"crypto markets rallying (+{crypto_change:.1f}%)")
    elif crypto_change < -2:
        parts.append(f"crypto markets selling off ({crypto_change:.1f}%)")

    if yields:
        y10 = yields.get("10.0", yields.get("10Y"))
        if y10:
            parts.append(f"10Y yield at {y10:.2f}%")

    return ". ".join(parts) + "."
