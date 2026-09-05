"""Market Monitor Algorithm Engine

Identifies emerging stocks and cryptocurrencies, detects market trends,
and generates trading signals based on technical analysis.
"""
import math
from datetime import datetime, timezone, timedelta
from typing import Optional


# ── Technical Indicators ────────────────────────────────────────────

def calculate_rsi(prices: list[float], period: int = 14) -> Optional[float]:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def calculate_macd(prices: list[float]) -> Optional[dict]:
    """Calculate MACD (12, 26, 9)."""
    if len(prices) < 35:
        return None

    def ema(data, period):
        alpha = 2 / (period + 1)
        result = [data[0]]
        for i in range(1, len(data)):
            result.append(alpha * data[i] + (1 - alpha) * result[-1])
        return result

    ema12 = ema(prices, 12)
    ema26 = ema(prices, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    signal_line = ema(macd_line, 9)

    return {
        "macd": round(macd_line[-1], 4),
        "signal": round(signal_line[-1], 4),
        "histogram": round(macd_line[-1] - signal_line[-1], 4),
        "bullish": macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2],
        "bearish": macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2],
    }


def calculate_bollinger(prices: list[float], period: int = 20) -> Optional[dict]:
    """Calculate Bollinger Bands."""
    if len(prices) < period:
        return None

    window = prices[-period:]
    mean = sum(window) / period
    variance = sum((x - mean) ** 2 for x in window) / period
    std = math.sqrt(variance)

    return {
        "upper": round(mean + 2 * std, 2),
        "middle": round(mean, 2),
        "lower": round(mean - 2 * std, 2),
        "width": round(4 * std / mean * 100, 2),  # % width
        "pct_b": round((prices[-1] - (mean - 2 * std)) / (4 * std) * 100, 2) if std > 0 else 50,
    }


def calculate_sma(prices: list[float], period: int) -> Optional[float]:
    """Calculate Simple Moving Average."""
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 2)


def calculate_volatility(prices: list[float], period: int = 20) -> Optional[float]:
    """Calculate annualized volatility from daily returns."""
    if len(prices) < period + 1:
        return None

    returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(max(1, len(prices) - period), len(prices))]
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    daily_vol = math.sqrt(variance)
    annual_vol = daily_vol * math.sqrt(252)
    return round(annual_vol * 100, 2)


def calculate_volume_ratio(volumes: list[float], short_period: int = 5, long_period: int = 20) -> Optional[float]:
    """Calculate volume ratio (short-term avg / long-term avg)."""
    if len(volumes) < long_period:
        return None

    short_avg = sum(volumes[-short_period:]) / short_period
    long_avg = sum(volumes[-long_period:]) / long_period

    if long_avg == 0:
        return None

    return round(short_avg / long_avg, 2)


# ── Stock Discovery Scoring ────────────────────────────────────────

def score_stock_discovery(
    price_history: list[dict],
    current_quote: dict,
    sector_peers: Optional[list[dict]] = None,
) -> dict:
    """Score a stock for emerging opportunity potential.

    Returns a score 0-100 with individual signal breakdown.
    """
    if not price_history or len(price_history) < 50:
        return {"score": 0, "signals": {}, "reason": "Insufficient data"}

    prices = [p["close"] for p in price_history if p.get("close")]
    volumes = [p.get("volume", 0) for p in price_history]

    signals = {}
    total_score = 0

    # 1. Volume surge (0-20 points)
    vol_ratio = calculate_volume_ratio(volumes)
    if vol_ratio and vol_ratio > 2.0:
        score = min(20, int(vol_ratio * 5))
        signals["volume_surge"] = {"score": score, "detail": f"Volume {vol_ratio}x average"}
        total_score += score
    elif vol_ratio and vol_ratio > 1.5:
        signals["volume_surge"] = {"score": 5, "detail": f"Volume {vol_ratio}x average"}

    # 2. Price momentum (0-20 points)
    if len(prices) >= 20:
        sma20 = sum(prices[-20:]) / 20
        if prices[-1] > sma20:
            pct_above = (prices[-1] - sma20) / sma20 * 100
            score = min(20, int(pct_above * 2))
            signals["price_momentum"] = {"score": score, "detail": f"{pct_above:.1f}% above 20-day SMA"}
            total_score += score

    # 3. MACD bullish crossover (0-15 points)
    macd = calculate_macd(prices)
    if macd and macd.get("bullish"):
        score = 15
        signals["macd_crossover"] = {"score": score, "detail": "MACD bullish crossover"}
        total_score += score

    # 4. RSI recovery from oversold (0-15 points)
    rsi = calculate_rsi(prices)
    if rsi and 40 < rsi < 60:
        # RSI recovering from oversold
        if len(prices) > 14:
            prev_rsi = calculate_rsi(prices[:-1])
            if prev_rsi and prev_rsi < 35:
                score = 15
                signals["rsi_recovery"] = {"score": score, "detail": f"RSI recovering: {prev_rsi:.0f} -> {rsi:.0f}"}
                total_score += score

    # 5. Relative strength vs sector (0-15 points)
    if sector_peers and len(sector_peers) > 0:
        peer_avg_change = sum(p.get("day_change_pct", 0) for p in sector_peers) / len(sector_peers)
        stock_change = current_quote.get("day_change_pct", 0)
        if stock_change > peer_avg_change + 3:
            score = min(15, int((stock_change - peer_avg_change) * 2))
            signals["relative_strength"] = {"score": score, "detail": f"Outperforming sector by {stock_change - peer_avg_change:.1f}%"}
            total_score += score

    # 6. Near 52-week high (0-10 points)
    high_52w = current_quote.get("fifty_two_week_high", 0)
    if high_52w and prices[-1] > high_52w * 0.9:
        pct = (prices[-1] / high_52w) * 100
        score = min(10, int((pct - 90)))
        signals["near_high"] = {"score": score, "detail": f"{pct:.0f}% of 52-week high"}
        total_score += score

    # 7. Bollinger squeeze breakout (0-5 points)
    bollinger = calculate_bollinger(prices)
    if bollinger and prices[-1] > bollinger["upper"]:
        signals["bollinger_breakout"] = {"score": 5, "detail": "Price broke above upper Bollinger band"}
        total_score += 5

    return {
        "score": min(100, total_score),
        "signals": signals,
        "indicators": {
            "rsi_14": rsi,
            "macd": macd,
            "bollinger": bollinger,
            "sma_20": calculate_sma(prices, 20),
            "sma_50": calculate_sma(prices, 50),
            "volatility": calculate_volatility(prices),
            "volume_ratio": vol_ratio,
        },
        "classification": (
            "rising_star" if total_score >= 80 else
            "watch" if total_score >= 60 else
            "monitor" if total_score >= 40 else
            "quiet"
        ),
    }


# ── Crypto Discovery Scoring ───────────────────────────────────────

def score_crypto_discovery(
    price_history: list[dict],
    market_data: dict,
) -> dict:
    """Score a crypto asset for emerging potential."""
    if not price_history or len(price_history) < 14:
        return {"score": 0, "signals": {}, "reason": "Insufficient data"}

    prices = [p["close"] for p in price_history if p.get("close")]
    signals = {}
    total_score = 0

    # 1. Volume surge (0-20 points)
    vol_24h = market_data.get("volume_24h", 0)
    market_cap = market_data.get("market_cap", 0)
    if market_cap > 0:
        vol_to_mcap = vol_24h / market_cap
        if vol_to_mcap > 0.15:
            score = min(20, int(vol_to_mcap * 100))
            signals["volume_surge"] = {"score": score, "detail": f"Vol/MCap ratio: {vol_to_mcap:.2%}"}
            total_score += score

    # 2. Price momentum (0-20 points)
    if len(prices) >= 7:
        week_change = (prices[-1] - prices[-7]) / prices[-7] * 100 if prices[-7] else 0
        if week_change > 10:
            score = min(20, int(week_change))
            signals["price_momentum"] = {"score": score, "detail": f"+{week_change:.1f}% 7-day"}
            total_score += score

    # 3. RSI signals (0-15 points)
    rsi = calculate_rsi(prices)
    if rsi and rsi > 55:
        score = min(15, int((rsi - 55) * 0.5))
        signals["rsi_strength"] = {"score": score, "detail": f"RSI {rsi:.0f} (bullish momentum)"}
        total_score += score

    # 4. Distance from ATH (0-15 points) — closer to ATH = stronger
    ath = market_data.get("ath", 0)
    if ath and ath > 0:
        ath_pct = (prices[-1] / ath) * 100
        if ath_pct > 80:
            score = min(15, int(ath_pct - 80))
            signals["near_ath"] = {"score": score, "detail": f"{ath_pct:.0f}% of ATH"}
            total_score += score

    # 5. Volatility (0-10 points) — moderate volatility is good
    vol = calculate_volatility(prices)
    if vol and 30 < vol < 80:
        signals["healthy_volatility"] = {"score": 10, "detail": f"Volatility: {vol:.0f}% (healthy range)"}
        total_score += 10

    # 6. MACD (0-10 points)
    macd = calculate_macd(prices)
    if macd and macd.get("bullish"):
        signals["macd_bullish"] = {"score": 10, "detail": "MACD bullish crossover"}
        total_score += 10

    # 7. TVL growth via DeFi Llama (0-20 points, DeFi protocols only)
    # Real protocol-growth scoring: 7d/1d/1m TVL trends, not just TVL size.
    tvl_score = 0
    try:
        from app.services.defi_tvl import get_tvl_growth_score
        sym = market_data.get("symbol") or market_data.get("name") or ""
        growth = get_tvl_growth_score(sym)
        if growth.get("has_data"):
            tvl_score = growth["score"]
            if growth.get("signals"):
                signals["defi_tvl_growth"] = {
                    "score": tvl_score,
                    "detail": ", ".join(growth["signals"][:3]),
                    "tvl": growth.get("tvl"),
                    "tvl_change_7d": growth.get("tvl_change_7d"),
                    "category": growth.get("category"),
                    "chains": growth.get("chains", []),
                    "mcap_tvl_ratio": growth.get("mcap_tvl_ratio"),
                }
                total_score += tvl_score
        else:
            # Protocol not on DeFi Llama — fall back to static TVL-size signal
            tvl = market_data.get("tvl")
            if tvl and tvl > 1e8:  # >$100M TVL
                signals["defi_tvl"] = {"score": 5, "detail": f"TVL: ${tvl/1e6:.0f}M"}
                total_score += 5
    except Exception:
        tvl = market_data.get("tvl")
        if tvl and tvl > 1e8:
            signals["defi_tvl"] = {"score": 5, "detail": f"TVL: ${tvl/1e6:.0f}M"}
            total_score += 5

    return {
        "score": min(100, total_score),
        "signals": signals,
        "indicators": {
            "rsi_14": rsi,
            "macd": macd,
            "sma_20": calculate_sma(prices, 20),
            "volatility": vol,
        },
        "classification": (
            "emerging_token" if total_score >= 70 else
            "watch" if total_score >= 50 else
            "monitor" if total_score >= 30 else
            "quiet"
        ),
    }


# ── Trend Detection ────────────────────────────────────────────────

def detect_volatility_regime(vix_level: float = None, spy_prices: list[float] = None) -> dict:
    """Classify current market volatility regime."""
    if vix_level is None and spy_prices:
        vol = calculate_volatility(spy_prices)
        vix_level = vol if vol else 15

    if vix_level is None:
        return {"regime": "unknown", "vix": None}

    if vix_level < 12:
        regime = "calm"
        description = "Low volatility — complacency risk"
    elif vix_level < 18:
        regime = "normal"
        description = "Normal volatility — healthy market conditions"
    elif vix_level < 25:
        regime = "elevated"
        description = "Elevated volatility — caution advised"
    elif vix_level < 35:
        regime = "stressed"
        description = "High volatility — defensive positioning recommended"
    else:
        regime = "panic"
        description = "Extreme volatility — crisis-level conditions"

    return {
        "regime": regime,
        "vix": round(vix_level, 2),
        "description": description,
        "color": {
            "calm": "#34d399",
            "normal": "#60a5fa",
            "elevated": "#fbbf24",
            "stressed": "#f87171",
            "panic": "#ef4444",
        }.get(regime, "#9ca3af"),
    }


def detect_sector_rotation(sector_data: list[dict]) -> dict:
    """Detect sector rotation by comparing short vs long-term performance."""
    if not sector_data or len(sector_data) < 3:
        return {"rotation": "none", "leaders": [], "laggards": []}

    # Sort by 5-day performance
    short_sorted = sorted(sector_data, key=lambda x: x.get("5d_change", 0), reverse=True)
    long_sorted = sorted(sector_data, key=lambda x: x.get("20d_change", 0), reverse=True)

    leaders = []
    laggards = []

    for i, sector in enumerate(short_sorted[:3]):
        long_rank = next((j for j, s in enumerate(long_sorted) if s["name"] == sector["name"]), 99)
        if i < long_rank:
            leaders.append({
                "name": sector["name"],
                "5d_change": sector.get("5d_change", 0),
                "20d_change": sector.get("20d_change", 0),
                "momentum": "accelerating",
            })

    for i, sector in enumerate(short_sorted[-3:]):
        long_rank = next((j for j, s in enumerate(long_sorted) if s["name"] == sector["name"]), 0)
        if i > long_rank:
            laggards.append({
                "name": sector["name"],
                "5d_change": sector.get("5d_change", 0),
                "20d_change": sector.get("20d_change", 0),
                "momentum": "decelerating",
            })

    return {
        "rotation": "detected" if leaders or laggards else "none",
        "leaders": leaders,
        "laggards": laggards,
    }


def calculate_correlation(prices_a: list[float], prices_b: list[float]) -> Optional[float]:
    """Calculate Pearson correlation coefficient between two price series."""
    n = min(len(prices_a), len(prices_b))
    if n < 20:
        return None

    # Use returns instead of prices
    returns_a = [(prices_a[i] - prices_a[i - 1]) / prices_a[i - 1] for i in range(1, n)]
    returns_b = [(prices_b[i] - prices_b[i - 1]) / prices_b[i - 1] for i in range(1, n)]

    mean_a = sum(returns_a) / len(returns_a)
    mean_b = sum(returns_b) / len(returns_b)

    cov = sum((a - mean_a) * (b - mean_b) for a, b in zip(returns_a, returns_b)) / len(returns_a)
    std_a = math.sqrt(sum((a - mean_a) ** 2 for a in returns_a) / len(returns_a))
    std_b = math.sqrt(sum((b - mean_b) ** 2 for b in returns_b) / len(returns_b))

    if std_a == 0 or std_b == 0:
        return None

    return round(cov / (std_a * std_b), 4)
