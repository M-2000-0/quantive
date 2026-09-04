"""Signal conflict detection — identifies when technical indicators disagree."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("quantive.ai.signal_conflict")


@dataclass
class SignalConflict:
    """A detected conflict between technical signals."""
    indicator_a: str
    signal_a: str
    indicator_b: str
    signal_b: str
    severity: str  # mild, moderate, strong
    description: str
    recommendation: str


def detect_conflicts(
    rsi_signal: str | None = None,
    macd_signal: str | None = None,
    moving_avg_signal: str | None = None,
    bollinger_signal: str | None = None,
    volume_signal: str | None = None,
    composite_score: float = 0,
) -> dict:
    """Detect conflicts between multiple technical indicators.

    Returns:
    - has_conflict: bool
    - conflict_count: int
    - conflicts: list of SignalConflict details
    - agreement_score: 0-100 (100 = full agreement, 0 = full disagreement)
    - recommendation: overall guidance
    """
    signals = {}
    if rsi_signal:
        signals["RSI"] = rsi_signal.lower()
    if macd_signal:
        signals["MACD"] = macd_signal.lower()
    if moving_avg_signal:
        signals["Moving Average"] = moving_avg_signal.lower()
    if bollinger_signal:
        signals["Bollinger Bands"] = bollinger_signal.lower()
    if volume_signal:
        signals["Volume"] = volume_signal.lower()

    if len(signals) < 2:
        return {
            "has_conflict": False,
            "conflict_count": 0,
            "conflicts": [],
            "agreement_score": 100,
            "recommendation": "Insufficient signals for conflict analysis. Need at least 2 indicators.",
        }

    # Map signals to directional categories
    bullish_keywords = {"bullish", "buy", "oversold", "above", "strong", "positive", "expanding"}
    bearish_keywords = {"bearish", "sell", "overbought", "below", "weak", "negative", "contracting"}

    def classify(signal: str) -> str:
        signal_lower = signal.lower()
        if any(kw in signal_lower for kw in bullish_keywords):
            return "bullish"
        elif any(kw in signal_lower for kw in bearish_keywords):
            return "bearish"
        return "neutral"

    classified = {name: classify(sig) for name, sig in signals.items()}

    # Find conflicts
    conflicts: list[SignalConflict] = []
    indicator_names = list(classified.keys())

    for i in range(len(indicator_names)):
        for j in range(i + 1, len(indicator_names)):
            name_a = indicator_names[i]
            name_b = indicator_names[j]
            dir_a = classified[name_a]
            dir_b = classified[name_b]

            if dir_a == "neutral" or dir_b == "neutral":
                continue

            if dir_a != dir_b:
                severity = _conflict_severity(dir_a, dir_b)
                conflict = SignalConflict(
                    indicator_a=name_a,
                    signal_a=signals[name_a],
                    indicator_b=name_b,
                    signal_b=signals[name_b],
                    severity=severity,
                    description=f"{name_a} is {dir_a} while {name_b} is {dir_b} — contradictory signals.",
                    recommendation=_conflict_recommendation(name_a, dir_a, name_b, dir_b),
                )
                conflicts.append(conflict)

    # Calculate agreement score
    total_pairs = len(indicator_names) * (len(indicator_names) - 1) / 2
    conflict_pairs = len(conflicts)
    agreement_score = ((total_pairs - conflict_pairs) / total_pairs * 100) if total_pairs > 0 else 100

    # Cross-timeframe analysis
    timeframe_conflict = None
    if moving_avg_signal and rsi_signal:
        ma_dir = classified.get("Moving Average", "neutral")
        rsi_dir = classified.get("RSI", "neutral")
        if ma_dir != "neutral" and rsi_dir != "neutral" and ma_dir != rsi_dir:
            timeframe_conflict = {
                "type": "timeframe_mismatch",
                "description": f"Short-term RSI ({rsi_dir}) conflicts with longer-term Moving Average ({ma_dir}) — "
                               f"potential trend transition in progress.",
            }

    # Overall recommendation
    bullish_count = sum(1 for d in classified.values() if d == "bullish")
    bearish_count = sum(1 for d in classified.values() if d == "bearish")

    if not conflicts:
        if bullish_count > bearish_count:
            recommendation = "Signals are aligned bullish. Consensus supports long positioning."
        elif bearish_count > bullish_count:
            recommendation = "Signals are aligned bearish. Consensus supports caution or short positioning."
        else:
            recommendation = "Signals are neutral and aligned. No strong directional bias."
    elif len(conflicts) >= 2:
        recommendation = ("Multiple conflicting signals detected. Exercise caution — "
                         "consider waiting for signal convergence before taking action.")
    else:
        recommendation = ("Mild signal conflict detected. Consider the weight of each indicator "
                         "and your risk tolerance before acting.")

    return {
        "has_conflict": len(conflicts) > 0,
        "conflict_count": len(conflicts),
        "conflicts": [_conflict_to_dict(c) for c in conflicts],
        "agreement_score": round(agreement_score, 1),
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "neutral_count": sum(1 for d in classified.values() if d == "neutral"),
        "timeframe_conflict": timeframe_conflict,
        "recommendation": recommendation,
    }


def _conflict_severity(dir_a: str, dir_b: str) -> str:
    """Determine conflict severity based on indicator importance."""
    if dir_a != dir_b:
        return "moderate"
    return "mild"


def _conflict_recommendation(name_a: str, dir_a: str, name_b: str, dir_b: str) -> str:
    """Generate specific recommendation for a conflict pair."""
    return (f"{name_a} ({dir_a}) vs {name_b} ({dir_b}): "
            f"Consider waiting for convergence or weighing the more reliable indicator.")


def _conflict_to_dict(conflict: SignalConflict) -> dict:
    return {
        "indicator_a": conflict.indicator_a,
        "signal_a": conflict.signal_a,
        "indicator_b": conflict.indicator_b,
        "signal_b": conflict.signal_b,
        "severity": conflict.severity,
        "description": conflict.description,
        "recommendation": conflict.recommendation,
    }
