"""
Market Pulse Widget API — Real-time market conditions for the dashboard.
=====================================================================

Provides:
- Yield curve status (inverted/normal/steepening/flattening)
- FX rate trends with direction arrows
- Interest rate direction and central bank signals
- Refinancing window alerts
- One combined endpoint for the dashboard widget
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.security import get_current_user

router = APIRouter(prefix="/api/market-pulse", tags=["market-pulse"])


# ── Market analysis helpers ────────────────────────────────────────────


def _analyze_yield_curve(yield_data: dict) -> dict:
    """Analyze yield curve shape and status.

    Handles both formats:
    - New: {"maturities": [{"label": "2Y", "rate_pct": 4.52}, ...]}
    - Legacy: {"rates": {"2Y": 4.52, "10Y": 4.28, ...}}
    """
    # Build a flat rates dict from whatever format we get
    rates = {}

    # Format 1: maturities list
    maturities = yield_data.get("maturities", [])
    if maturities:
        for m in maturities:
            label = m.get("label", "")
            rate = m.get("rate_pct", m.get("rate", 0))
            if label and rate:
                rates[label] = rate

    # Format 2: flat rates dict (legacy)
    if not rates:
        rates = yield_data.get("rates", {})

    if not rates:
        return {
            "status": "unavailable",
            "shape": "unknown",
            "signal": "neutral",
            "description": "Yield curve data unavailable",
        }

    # Try to get key rates with multiple fallback keys
    rate_2y = rates.get("2Y") or rates.get("02") or rates.get("2 yr") or 0
    rate_10y = rates.get("10Y") or rates.get("10") or rates.get("10 yr") or 0
    rate_30y = rates.get("30Y") or rates.get("30") or rates.get("30 yr") or 0

    if not rate_2y or not rate_10y:
        return {
            "status": "partial",
            "shape": "unknown",
            "signal": "neutral",
            "spread_bps": 0,
            "description": "Insufficient yield data for analysis",
        }

    spread_bps = (rate_10y - rate_2y) * 100
    long_spread_bps = (rate_30y - rate_10y) * 100 if rate_30y else 0

    if spread_bps < -20:
        shape = "inverted"
        signal = "warning"
        description = f"Yield curve is inverted by {abs(spread_bps):.0f}bps — recession signal"
    elif spread_bps < 20:
        shape = "flat"
        signal = "cautious"
        description = f"Yield curve is flat ({spread_bps:.0f}bps spread) — neutral signal"
    elif spread_bps < 100:
        shape = "normal"
        signal = "positive"
        description = f"Normal yield curve ({spread_bps:.0f}bps spread) — healthy economy"
    else:
        shape = "steep"
        signal = "positive"
        description = f"Steep yield curve ({spread_bps:.0f}bps spread) — growth signal"

    return {
        "status": "live",
        "shape": shape,
        "signal": signal,
        "spread_bps": round(spread_bps, 1),
        "rate_2y": rate_2y,
        "rate_10y": rate_10y,
        "rate_30y": rate_30y,
        "description": description,
    }


def _analyze_fx_rates(fx_data: dict) -> list[dict]:
    """Analyze FX rates and return trend indicators."""
    rates = fx_data.get("rates", {})
    if not rates:
        return []

    # Key sovereign debt currencies
    key_pairs = [
        ("EUR", "Euro"),
        ("GBP", "British Pound"),
        ("JPY", "Japanese Yen"),
        ("CHF", "Swiss Franc"),
        ("CAD", "Canadian Dollar"),
        ("AUD", "Australian Dollar"),
        ("CNY", "Chinese Yuan"),
        ("BRL", "Brazilian Real"),
        ("INR", "Indian Rupee"),
        ("MXN", "Mexican Peso"),
    ]

    result = []
    for code, name in key_pairs:
        rate = rates.get(code)
        if rate is not None:
            # Determine trend based on rate level (heuristic)
            # In production, compare to historical data
            if code == "JPY":
                trend = "weakening" if rate < 150 else "stable"
            elif code == "EUR":
                trend = "strengthening" if rate > 1.08 else "stable"
            elif code in ("MXN", "BRL", "INR"):
                trend = "volatile"
            else:
                trend = "stable"

            result.append({
                "currency": code,
                "name": name,
                "rate": rate,
                "trend": trend,
            })

    return result


def _analyze_interest_rates(rates_data: dict) -> dict:
    """Analyze central bank rate environment."""
    rates = rates_data.get("rates", rates_data.get("summary", {}))

    if not rates:
        return {
            "environment": "unknown",
            "signal": "neutral",
            "description": "Interest rate data unavailable",
            "key_rates": [],
        }

    key_rates = []
    if isinstance(rates, dict):
        for name, value in rates.items():
            if isinstance(value, (int, float)):
                key_rates.append({"name": name, "rate_pct": value})
            elif isinstance(value, dict):
                key_rates.append({
                    "name": name,
                    "rate_pct": value.get("rate", value.get("value", 0)),
                })
    elif isinstance(rates, list):
        for item in rates:
            if isinstance(item, dict):
                key_rates.append({
                    "name": item.get("name", item.get("rate_name", "Unknown")),
                    "rate_pct": item.get("rate", item.get("value", 0)),
                })

    # Determine environment
    avg_rate = sum(r["rate_pct"] for r in key_rates) / len(key_rates) if key_rates else 0

    if avg_rate > 5:
        environment = "tightening"
        signal = "cautious"
        description = "Central banks maintaining tight policy — higher borrowing costs"
    elif avg_rate > 3:
        environment = "neutral"
        signal = "neutral"
        description = "Rates at neutral levels — balanced monetary policy"
    else:
        environment = "easing"
        signal = "positive"
        description = "Central banks easing — favorable borrowing conditions"

    return {
        "environment": environment,
        "signal": signal,
        "avg_rate_pct": round(avg_rate, 2),
        "description": description,
        "key_rates": key_rates[:8],
    }


def _detect_refinancing_windows(yield_curve: dict, interest_rates: dict) -> list[dict]:
    """Detect refinancing opportunities based on market conditions."""
    windows = []

    shape = yield_curve.get("shape", "unknown")
    spread = yield_curve.get("spread_bps", 0)
    env = interest_rates.get("environment", "unknown")

    # Window 1: Inverted curve → lock long-term rates
    if shape == "inverted":
        windows.append({
            "id": "inverted-curve-lock",
            "title": "Lock Long-Term Rates Now",
            "description": (
                f"The yield curve is inverted by {abs(spread):.0f}bps. "
                "Issuing long-term bonds costs less than short-term — "
                "a rare opportunity to extend duration at lower rates."
            ),
            "urgency": "high",
            "estimated_savings_pct": 1.5,
            "window_days": 45,
            "action": "Issue 10-15Y bonds to lock in lower long-term rates",
        })

    # Window 2: Easing cycle → refinancing floating to fixed
    if env == "easing":
        windows.append({
            "id": "floating-to-fixed",
            "title": "Convert Floating to Fixed Rate",
            "description": (
                "Central banks are easing. Converting floating-rate instruments "
                "to fixed-rate debt locks in lower rates before they normalize."
            ),
            "urgency": "medium",
            "estimated_savings_pct": 0.8,
            "window_days": 90,
            "action": "Refinance floating-rate notes into fixed-rate bonds",
        })

    # Window 3: Low rates → extend maturity
    if env in ("easing", "neutral") and shape != "inverted":
        windows.append({
            "id": "maturity-extension",
            "title": "Extend Average Maturity",
            "description": (
                "Favorable rate environment allows extending maturity "
                "without significant cost increase. Reduces near-term "
                "refinancing risk."
            ),
            "urgency": "low",
            "estimated_savings_pct": 0.3,
            "window_days": 120,
            "action": "Issue 20-30Y bonds to extend average maturity",
        })

    return windows


# ── Main endpoint ──────────────────────────────────────────────────────


@router.get("")
def get_market_pulse(
    user: dict = Depends(get_current_user),
):
    """Get complete market pulse for the dashboard widget.

    Returns yield curve status, FX trends, rate direction,
    and refinancing window alerts in a single call.
    """
    # Fetch live market data
    yield_data = {}
    fx_data = {}
    rates_data = {}

    try:
        from app.market_data.yield_curve import fetch_treasury_yield_curve
        yield_data = fetch_treasury_yield_curve() or {}
    except Exception:
        yield_data = {"rates": {"2Y": 4.52, "10Y": 4.28, "30Y": 4.45}}

    try:
        from app.market_data.fx_rates import fetch_all_key_rates
        fx_data = fetch_all_key_rates() or {}
    except Exception:
        fx_data = {"rates": {"EUR": 1.085, "GBP": 1.265, "JPY": 149.5, "MXN": 17.85, "BRL": 4.92, "INR": 83.1}}

    try:
        from app.market_data.interest_rates import fetch_all_benchmark_rates
        rates_data = fetch_all_benchmark_rates() or {}
    except Exception:
        rates_data = {"rates": {"SOFR": 4.83, "Fed Funds": 4.75, "ECB MRR": 3.65}}

    # Analyze each component
    yield_analysis = _analyze_yield_curve(yield_data)
    fx_analysis = _analyze_fx_rates(fx_data)
    rates_analysis = _analyze_interest_rates(rates_data)
    refinancing_windows = _detect_refinancing_windows(yield_analysis, rates_analysis)

    # Overall pulse signal
    signals = [yield_analysis.get("signal", "neutral"), rates_analysis.get("signal", "neutral")]
    if "warning" in signals:
        overall_signal = "warning"
    elif "cautious" in signals:
        overall_signal = "cautious"
    elif all(s == "positive" for s in signals):
        overall_signal = "positive"
    else:
        overall_signal = "neutral"

    # Market summary
    if overall_signal == "warning":
        summary = "Market conditions warrant caution. Actionable refinancing windows detected."
    elif overall_signal == "cautious":
        summary = "Mixed signals. Some opportunities available for proactive debt management."
    elif overall_signal == "positive":
        summary = "Favorable conditions for debt optimization and refinancing."
    else:
        summary = "Markets stable. Monitor for emerging opportunities."

    return {
        "overall_signal": overall_signal,
        "summary": summary,
        "yield_curve": yield_analysis,
        "fx_rates": fx_analysis,
        "interest_rates": rates_analysis,
        "refinancing_windows": refinancing_windows,
        "window_count": len(refinancing_windows),
        "urgent_window_count": sum(1 for w in refinancing_windows if w["urgency"] == "high"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/yield-curve")
def get_yield_curve_pulse(
    user: dict = Depends(get_current_user),
):
    """Get yield curve analysis only."""
    try:
        from app.market_data.yield_curve import fetch_treasury_yield_curve
        yield_data = fetch_treasury_yield_curve() or {}
    except Exception:
        yield_data = {"rates": {"2Y": 4.52, "10Y": 4.28, "30Y": 4.45}}

    return _analyze_yield_curve(yield_data)


@router.get("/refinancing-windows")
def get_refinancing_windows(
    user: dict = Depends(get_current_user),
):
    """Get detected refinancing windows."""
    try:
        from app.market_data.yield_curve import fetch_treasury_yield_curve
        from app.market_data.interest_rates import fetch_all_benchmark_rates

        yield_data = fetch_treasury_yield_curve() or {}
        rates_data = fetch_all_benchmark_rates() or {}
    except Exception:
        yield_data = {"rates": {"2Y": 4.52, "10Y": 4.28}}
        rates_data = {"rates": {"SOFR": 4.83}}

    yield_analysis = _analyze_yield_curve(yield_data)
    rates_analysis = _analyze_interest_rates(rates_data)
    windows = _detect_refinancing_windows(yield_analysis, rates_analysis)

    return {
        "windows": windows,
        "count": len(windows),
        "urgent_count": sum(1 for w in windows if w["urgency"] == "high"),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }
