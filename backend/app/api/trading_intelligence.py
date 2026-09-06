"""
Trading Intelligence API — Stocks, ETFs, Options, Sectors, Dividends, Technicals.

Provides:
- Real-time stock/ETF prices for S&P 500 and NASDAQ 100
- Sector rotation analysis with relative strength scoring
- Options data (implied volatility, put/call ratio estimation)
- Dividend & yield screener
- Technical analysis (RSI, MACD, Moving Averages, signals)
- Top movers and market overview

All data from Yahoo Finance (free, no API key).
"""
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, Depends, HTTPException, Query

from app.market_data.cache import get_cache
from typing import Optional
from app.models import User
from app.security import get_current_user
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db

_optional_bearer = HTTPBearer(auto_error=False)

async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the current user if a valid token is provided, else None."""
    if credentials is None:
        return None
    try:
        from app.security import decode_token
        payload = decode_token(credentials.credentials)
        if payload:
            uid = payload.get("sub")
            return db.query(User).filter(User.id == uid).first()
    except Exception:
        pass
    return None

router = APIRouter(prefix="/api/trading", tags=["trading-intelligence"])

# ── Constants ─────────────────────────────────────────────────────────

YAHOO_QUOTE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_V7_URL = "https://query1.finance.yahoo.com/v7/finance/quote"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

TTL_STOCK_PRICES = 2 * 60   # 2 min for real-time
TTL_SECTOR_DATA = 5 * 60    # 5 min for sectors
TTL_TECHNICALS = 10 * 60    # 10 min for technicals

# Major large-cap US stocks by market cap (symbol → name)
SP500_TOP50 = {
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon",
    "GOOGL": "Alphabet", "GOOG": "Alphabet C", "META": "Meta Platforms",
    "BRK-B": "Berkshire Hathaway",
    "LLY": "Eli Lilly", "AVGO": "Broadcom", "TSLA": "Tesla",
    "WMT": "Walmart", "JPM": "JPMorgan Chase", "V": "Visa",
    "UNH": "UnitedHealth", "XOM": "Exxon Mobil", "MA": "Mastercard",
    "COST": "Costco", "HD": "Home Depot", "PG": "Procter & Gamble",
    "JNJ": "Johnson & Johnson", "ABBV": "AbbVie", "CRM": "Salesforce",
    "NFLX": "Netflix", "BAC": "Bank of America", "AMD": "AMD",
    "CVX": "Chevron", "MRK": "Merck", "KO": "Coca-Cola",
    "ORCL": "Oracle", "TMO": "Thermo Fisher", "PEP": "PepsiCo",
    "LIN": "Linde", "ACN": "Accenture", "CSCO": "Cisco",
    "ADBE": "Adobe", "DHR": "Danaher", "ABT": "Abbott Labs",
    "WFC": "Wells Fargo", "TXN": "Texas Instruments",
    "PM": "Philip Morris", "GE": "GE Aerospace", "AMGN": "Amgen",
    "INTC": "Intel", "CAT": "Caterpillar", "QCOM": "Qualcomm",
    "NOW": "ServiceNow", "GS": "Goldman Sachs", "AMAT": "Applied Materials",
    "BLK": "BlackRock", "ISRG": "Intuitive Surgical",
    "PFE": "Pfizer", "T": "AT&T", "VZ": "Verizon", "DIS": "Walt Disney",
    "MCD": "McDonald's", "NKE": "Nike", "SBUX": "Starbucks",
    "LMT": "Lockheed Martin", "PLTR": "Palantir", "MU": "Micron",
    "INTU": "Intuit", "TMUS": "T-Mobile", "ANET": "Arista Networks",
    "AXP": "American Express", "MS": "Morgan Stanley",
    "SCHW": "Charles Schwab", "GILD": "Gilead Sciences",
    "MDLZ": "Mondelez", "TJX": "TJX Companies", "TGT": "Target",
    "CMCSA": "Comcast", "ADSK": "Autodesk", "UNP": "Union Pacific",
    "DE": "Deere", "TSM": "TSMC",
}

# NASDAQ 100 top stocks (additions beyond S&P 500)
NASDAQ100_EXTRA = {
    "COIN": "Coinbase", "MARA": "Marathon Digital", "PLTR": "Palantir",
    "SMCI": "Super Micro", "PANW": "Palo Alto Networks", "CDNS": "Cadence",
    "SNPS": "Synopsys", "KLAC": "KLA Corp", "LRCX": "Lam Research",
    "MRVL": "Marvell Technology", "FTNT": "Fortinet", "TEAM": "Atlassian",
    "WDAY": "Workday", "CRWD": "CrowdStrike", "DDOG": "Datadog",
    "ZS": "Zscaler", "NET": "Cloudflare", "SHOP": "Shopify",
    "ROKU": "Roku", "UBER": "Uber", "ABNB": "Airbnb",
    "DASH": "DoorDash", "HOOD": "Robinhood", "RBLX": "Roblox",
    "ARM": "Arm Holdings", "ASML": "ASML", "PDD": "PDD Holdings",
    "CEG": "Constellation Energy", "KDP": "Keurig Dr Pepper",
    "ROST": "Ross Stores", "LULU": "Lululemon", "MAR": "Marriott",
    "MCHP": "Microchip", "NXPI": "NXP", "REGN": "Regeneron",
    "VRTX": "Vertex Pharmaceuticals", "FANG": "Diamondback Energy",
    "CHTR": "Charter Communications", "EA": "Electronic Arts",
    "BKR": "Baker Hughes",
}

# 11 SPDR Sector ETFs
SECTOR_ETFS = {
    "XLK": {"name": "Technology", "weight": 0.29, "benchmark": "S&P 500 IT"},
    "XLV": {"name": "Health Care", "weight": 0.12, "benchmark": "S&P 500 Health"},
    "XLF": {"name": "Financials", "weight": 0.13, "benchmark": "S&P 500 Financials"},
    "XLY": {"name": "Consumer Disc.", "weight": 0.10, "benchmark": "S&P 500 CD"},
    "XLP": {"name": "Consumer Staples", "weight": 0.06, "benchmark": "S&P 500 CS"},
    "XLE": {"name": "Energy", "weight": 0.04, "benchmark": "S&P 500 Energy"},
    "XLI": {"name": "Industrials", "weight": 0.08, "benchmark": "S&P 500 Industrials"},
    "XLU": {"name": "Utilities", "weight": 0.025, "benchmark": "S&P 500 Utilities"},
    "XLB": {"name": "Materials", "weight": 0.025, "benchmark": "S&P 500 Materials"},
    "XLRE": {"name": "Real Estate", "weight": 0.025, "benchmark": "S&P 500 RE"},
    "XLC": {"name": "Communication", "weight": 0.09, "benchmark": "S&P 500 Comm"},
}

# Major ETFs for tracking
MAJOR_ETFS = {
    "SPY": "S&P 500 ETF", "QQQ": "NASDAQ 100 ETF", "IWM": "Russell 2000",
    "VTI": "Total US Market", "VEA": "Developed Markets", "VWO": "Emerging Markets",
    "GLD": "Gold ETF", "SLV": "Silver ETF", "USO": "Oil ETF",
    "TLT": "20+ Year Bonds", "IEF": "7-10 Year Bonds", "SHY": "1-3 Year Bonds",
    "HYG": "High Yield Bonds", "LQD": "Investment Grade Bonds",
    "EEM": "Emerging Markets Equity", "FXI": "China Large Cap",
    "ARKK": "ARK Innovation", "SOXX": "Semiconductor ETF",
    "XBI": "Biotech ETF", "BITO": "Bitcoin Futures ETF",
}


# ── Yahoo Finance Helpers ─────────────────────────────────────────────

def _fetch_yahoo_quote(symbol: str) -> dict:
    """Fetch a single quote from Yahoo Finance."""
    try:
        url = YAHOO_QUOTE_URL.format(symbol=symbol)
        params = {"interval": "1d", "range": "5d"}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        chart = data.get("chart", {}).get("result", [])
        if not chart:
            return {"error": f"No data for {symbol}"}

        meta = chart[0].get("meta", {})
        indicators = chart[0].get("indicators", {}).get("quote", [{}])
        closes = indicators[0].get("close", []) if indicators else []

        price = meta.get("regularMarketPrice") or 0
        prev_close = meta.get("chartPreviousClose") or meta.get("regularMarketPreviousClose") or 0
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

        # Extract dividend yield from summaryDetail if available
        dividend_yield = meta.get("dividendYield") or 0

        return {
            "price": round(float(price), 2),
            "previous_close": round(float(prev_close), 2),
            "change_pct": round(float(change_pct), 2),
            "currency": meta.get("currency", "USD"),
            "market_state": meta.get("marketState") or "CLOSED",
            "recent_closes": [round(float(c), 2) for c in (closes[-10:] if closes else []) if c is not None],
            "dividend_yield": round(float(dividend_yield) * 100, 2),
        }
    except Exception:
        return {"error": "Data unavailable"}


def _fetch_yahoo_v7_quotes(symbols: list[str]) -> dict:
    """Fetch multiple quotes using Yahoo v7 API (batch), with fallback to individual."""
    # Try v7 batch first
    try:
        params = {"symbols": ",".join(symbols), "fields": "regularMarketPrice,regularMarketChange,regularMarketVolume,regularMarketMarketCap,trailingPE,dividendYield,regularMarketPreviousClose"}
        resp = requests.get(YAHOO_V7_URL, params=params, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        quotes = data.get("quoteResponse", {}).get("result", [])
        if quotes:
            return {q["symbol"]: q for q in quotes}
    except Exception:
        pass

    # Fallback: fetch individually using v8 chart API (concurrent)
    result = {}
    def _fetch_one(sym):
        try:
            url = YAHOO_QUOTE_URL.format(symbol=sym)
            params = {"interval": "1d", "range": "5d"}
            resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            chart = data.get("chart", {}).get("result", [])
            if not chart:
                return sym, None
            meta = chart[0].get("meta", {})
            indicators = chart[0].get("indicators", {}).get("quote", [{}])
            q_data = indicators[0] if indicators else {}
            q_data["regularMarketPrice"] = meta.get("regularMarketPrice", 0)
            q_data["regularMarketChange"] = (meta.get("regularMarketPrice", 0) or 0) - (meta.get("chartPreviousClose", 0) or 0)
            q_data["regularMarketChangePercent"] = round(q_data["regularMarketChange"] / (meta.get("chartPreviousClose", 1) or 1) * 100, 2)
            q_data["regularMarketVolume"] = meta.get("regularMarketVolume", 0)
            q_data["trailingPE"] = None
            q_data["dividendYield"] = meta.get("dividendYield", 0) or 0
            q_data["regularMarketMarketCap"] = 0
            return sym, q_data
        except Exception:
            return sym, None
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_fetch_one, s) for s in symbols]
        for f in as_completed(futures):
            sym, q_data = f.result()
            if q_data:
                result[sym] = q_data
    return result


def _fetch_history(symbol: str, days: int = 90) -> list[float]:
    """Fetch closing price history for technical analysis."""
    cache = get_cache()
    cache_key = f"history_{symbol}_{days}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        url = YAHOO_QUOTE_URL.format(symbol=symbol)
        params = {"interval": "1d", "range": f"{days}d"}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        chart = data.get("chart", {}).get("result", [])
        if not chart:
            return []

        indicators = chart[0].get("indicators", {}).get("quote", [{}])
        closes = indicators[0].get("close", []) if indicators else []
        valid = [round(c, 2) for c in closes if c is not None]

        cache.set(cache_key, valid, TTL_TECHNICALS)
        return valid
    except Exception:
        return []


# ── Technical Analysis Helpers ────────────────────────────────────────

def _calculate_rsi(prices: list[float], period: int = 14) -> dict:
    """Calculate RSI (Relative Strength Index)."""
    if len(prices) < period + 1:
        return {"value": 50, "signal": "NEUTRAL", "strength": "insufficient_data"}

    deltas = np.diff(prices[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains) if len(gains) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0.001

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    if rsi > 70:
        signal = "OVERBOUGHT"
        strength = "strong_sell" if rsi > 80 else "sell"
    elif rsi < 30:
        signal = "OVERSOLD"
        strength = "strong_buy" if rsi < 20 else "buy"
    else:
        signal = "NEUTRAL"
        strength = "hold"

    return {"value": round(float(rsi), 2), "signal": signal, "strength": strength}


def _calculate_macd(prices: list[float]) -> dict:
    """Calculate MACD (Moving Average Convergence Divergence)."""
    if len(prices) < 26:
        return {"macd": 0, "signal_line": 0, "histogram": 0, "trend": "INSUFFICIENT"}

    arr = np.array(prices, dtype=float)

    # EMA 12 and 26
    def ema(data, period):
        alpha = 2 / (period + 1)
        result = np.zeros_like(data)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
        return result

    ema12 = ema(arr, 12)
    ema26 = ema(arr, 26)
    macd_line = ema12 - ema26
    signal_line = ema(macd_line, 9)
    histogram = macd_line - signal_line

    macd_val = round(float(macd_line[-1]), 4)
    signal_val = round(float(signal_line[-1]), 4)
    hist_val = round(float(histogram[-1]), 4)

    if macd_val > signal_val and hist_val > 0:
        trend = "BULLISH"
    elif macd_val < signal_val and hist_val < 0:
        trend = "BEARISH"
    else:
        trend = "NEUTRAL"

    return {
        "macd": macd_val,
        "signal_line": signal_val,
        "histogram": hist_val,
        "trend": trend,
    }


def _calculate_moving_averages(prices: list[float]) -> dict:
    """Calculate SMA 20, 50, 200 and EMA 12, 26."""
    result = {}

    for period in [20, 50, 200]:
        if len(prices) >= period:
            sma = round(float(np.mean(prices[-period:])), 2)
            current = prices[-1]
            result[f"sma_{period}"] = sma
            result[f"above_sma_{period}"] = current > sma
            result[f"pct_from_sma_{period}"] = round((current - sma) / sma * 100, 2)
        else:
            result[f"sma_{period}"] = None
            result[f"above_sma_{period}"] = None
            result[f"pct_from_sma_{period}"] = None

    # EMA
    for period in [12, 26]:
        if len(prices) >= period:
            alpha = 2 / (period + 1)
            ema_val = prices[0]
            for p in prices[1:]:
                ema_val = alpha * p + (1 - alpha) * ema_val
            result[f"ema_{period}"] = round(ema_val, 2)
        else:
            result[f"ema_{period}"] = None

    return result


def _calculate_bollinger_bands(prices: list[float], period: int = 20) -> dict:
    """Calculate Bollinger Bands."""
    if len(prices) < period:
        return {"upper": None, "middle": None, "lower": None, "position": None}

    recent = prices[-period:]
    middle = float(np.mean(recent))
    std = float(np.std(recent))

    upper = round(middle + 2 * std, 2)
    lower = round(middle - 2 * std, 2)
    current = prices[-1]

    # Position: 0 = at lower band, 1 = at upper band
    if upper != lower:
        position = round((current - lower) / (upper - lower), 2)
    else:
        position = 0.5

    return {
        "upper": upper,
        "middle": round(middle, 2),
        "lower": lower,
        "bandwidth": round((upper - lower) / middle * 100, 2),
        "position": position,
        "signal": "OVERBOUGHT" if position > 0.9 else "OVERSOLD" if position < 0.1 else "NEUTRAL",
    }


def _detect_support_resistance(prices: list[float]) -> dict:
    """Detect approximate support and resistance levels."""
    if len(prices) < 20:
        return {"support": None, "resistance": None, "current": None}

    current = prices[-1]
    arr = np.array(prices[-60:], dtype=float) if len(prices) >= 60 else np.array(prices, dtype=float)

    # Find local minima (support) and maxima (resistance)
    supports = []
    resistances = []
    for i in range(2, len(arr) - 2):
        if arr[i] <= arr[i-1] and arr[i] <= arr[i-2] and arr[i] <= arr[i+1] and arr[i] <= arr[i+2]:
            supports.append(float(arr[i]))
        if arr[i] >= arr[i-1] and arr[i] >= arr[i-2] and arr[i] >= arr[i+1] and arr[i] >= arr[i+2]:
            resistances.append(float(arr[i]))

    # Closest support below current price
    support_levels = sorted([s for s in supports if s < current], reverse=True)
    # Closest resistance above current price
    resistance_levels = sorted([r for r in resistances if r > current])

    return {
        "support": round(support_levels[0], 2) if support_levels else round(float(np.min(arr)) * 0.99, 2),
        "resistance": round(resistance_levels[0], 2) if resistance_levels else round(float(np.max(arr)) * 1.01, 2),
        "current": current,
        "support_distance_pct": round((current - (support_levels[0] if support_levels else np.min(arr))) / current * 100, 2),
        "resistance_distance_pct": round(((resistance_levels[0] if resistance_levels else np.max(arr)) - current) / current * 100, 2),
    }


def _generate_signal(rsi: dict, macd: dict, ma: dict, bb: dict) -> dict:
    """Generate composite trading signal from all indicators."""
    score = 0  # -100 (strong sell) to +100 (strong buy)
    factors = []

    # RSI signal
    if rsi["signal"] == "OVERSOLD":
        score += 30
        factors.append("RSI oversold — buying opportunity")
    elif rsi["signal"] == "OVERBOUGHT":
        score -= 30
        factors.append("RSI overbought — consider taking profits")
    else:
        factors.append("RSI neutral")

    # MACD signal
    if macd["trend"] == "BULLISH":
        score += 25
        factors.append("MACD bullish crossover")
    elif macd["trend"] == "BEARISH":
        score -= 25
        factors.append("MACD bearish crossover")
    else:
        factors.append("MACD neutral")

    # Moving average alignment
    above_count = sum(1 for p in [20, 50, 200] if ma.get(f"above_sma_{p}"))
    if above_count == 3:
        score += 25
        factors.append("Price above all major moving averages — strong uptrend")
    elif above_count == 0:
        score -= 25
        factors.append("Price below all major moving averages — downtrend")
    elif above_count >= 2:
        score += 10
        factors.append("Price above most moving averages")
    else:
        factors.append("Mixed moving average signals")

    # Bollinger Band position
    if bb.get("signal") == "OVERSOLD":
        score += 20
        factors.append("Price near lower Bollinger Band — potential bounce")
    elif bb.get("signal") == "OVERBOUGHT":
        score -= 20
        factors.append("Price near upper Bollinger Band — potential pullback")

    # Determine overall signal
    if score > 30:
        action = "STRONG BUY"
        emoji = "[+]"
    elif score > 10:
        action = "BUY"
        emoji = "[+]"
    elif score > -10:
        action = "HOLD"
        emoji = "[!]"
    elif score > -30:
        action = "SELL"
        emoji = "[-]"
    else:
        action = "STRONG SELL"
        emoji = "[-]"

    return {
        "score": max(-100, min(100, score)),
        "action": action,
        "emoji": emoji,
        "factors": factors,
    }


# ── API Endpoints ─────────────────────────────────────────────────────

@router.get("/market-overview")
def get_market_overview(user: Optional[User] = Depends(get_optional_user)):
    """Comprehensive market overview: top stocks, ETFs, sectors, fear/greed.

    Single endpoint that powers the entire trading dashboard.
    """
    cache = get_cache()
    cached = cache.get("trading_overview")
    if cached:
        return cached

    # Fetch SPY and QQQ as market proxies
    spy = _fetch_yahoo_quote("SPY")
    qqq = _fetch_yahoo_quote("QQQ")

    # Fetch top 10 stocks by market cap (concurrent for speed)
    top_symbols = list(SP500_TOP50.keys())[:15]
    
    # Try v7 batch first, fallback to concurrent individual fetches
    quotes = _fetch_yahoo_v7_quotes(top_symbols)
    if not quotes:
        # Concurrent individual fetches as fallback
        def _fetch_one(sym):
            return sym, _fetch_yahoo_quote(sym)
        quotes = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(_fetch_one, s): s for s in top_symbols}
            for future in as_completed(futures, timeout=30):
                try:
                    sym, q = future.result()
                    if q and not q.get('error') and q.get('price'):
                        quotes[sym] = {
                            'regularMarketPrice': q['price'],
                            'regularMarketChangePercent': q['change_pct'],
                            'regularMarketVolume': 0,
                            'trailingPE': None,
                            'dividendYield': q.get('dividend_yield', 0) / 100 if q.get('dividend_yield') else 0,
                            'regularMarketMarketCap': 0,
                        }
                except Exception:
                    continue

    top_stocks = []
    for sym in top_symbols:
        if sym in quotes:
            q = quotes[sym]
            top_stocks.append({
                "symbol": sym,
                "name": SP500_TOP50.get(sym, sym),
                "price": q.get("regularMarketPrice", 0),
                "change_pct": round(q.get("regularMarketChangePercent", 0) or 0, 2),
                "volume": q.get("regularMarketVolume", 0),
                "market_cap": q.get("regularMarketMarketCap", 0),
                "pe_ratio": q.get("trailingPE"),
                "dividend_yield": round((q.get("dividendYield") or 0) * 100, 2),
            })
        else:
            top_stocks.append({
                "symbol": sym,
                "name": SP500_TOP50.get(sym, sym),
                "price": 0,
                "change_pct": 0,
                "error": "data_unavailable",
            })

    # Sort by market cap
    top_stocks.sort(key=lambda x: x.get("market_cap") or 0, reverse=True)

    result = {
        "market_indices": {
            "sp500": {"symbol": "SPY", "price": spy.get("price", 0), "change_pct": spy.get("change_pct", 0)},
            "nasdaq": {"symbol": "QQQ", "price": qqq.get("price", 0), "change_pct": qqq.get("change_pct", 0)},
        },
        "top_stocks": top_stocks[:10],
        "tracked_count": len(top_stocks),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set("trading_overview", result, TTL_STOCK_PRICES)
    return result


@router.get("/stocks/{symbol}")
def get_stock_detail(symbol: str, user: Optional[User] = Depends(get_optional_user)):
    """Get detailed stock data with technical analysis."""
    symbol = symbol.upper()
    cache = get_cache()
    cache_key = f"stock_detail_{symbol}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    quote = _fetch_yahoo_quote(symbol)
    if quote.get("error") or not quote.get("price"):
        raise HTTPException(status_code=404, detail="Stock not found or data unavailable")

    history = _fetch_history(symbol, 200)

    # Technical analysis if enough data
    technicals = {}
    signal = {}
    if len(history) >= 20:
        rsi = _calculate_rsi(history)
        macd = _calculate_macd(history)
        ma = _calculate_moving_averages(history)
        bb = _calculate_bollinger_bands(history)
        sr = _detect_support_resistance(history)

        technicals = {
            "rsi": rsi,
            "macd": macd,
            "moving_averages": ma,
            "bollinger_bands": bb,
            "support_resistance": sr,
        }
        signal = _generate_signal(rsi, macd, ma, bb)

    result = {
        "symbol": symbol,
        "name": SP500_TOP50.get(symbol) or NASDAQ100_EXTRA.get(symbol) or symbol,
        "quote": quote,
        "technicals": technicals,
        "signal": signal,
        "price_history": history[-30:] if history else [],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set(cache_key, result, TTL_TECHNICALS)
    return result


@router.get("/sectors")
def get_sector_rotation(user: Optional[User] = Depends(get_optional_user)):
    """Sector rotation analysis with relative strength.

    Shows which sectors are leading/lagging — the #1 macro strategy.
    """
    cache = get_cache()
    cached = cache.get("sector_rotation")
    if cached:
        return cached

    # Fetch SPY as benchmark
    spy = _fetch_yahoo_quote("SPY")
    benchmark_price = spy.get("price", 1)

    # Fetch all 11 sector ETFs (with throttling to avoid rate limits)
    sector_data = []
    import time as _time
    for symbol, info in SECTOR_ETFS.items():
        _time.sleep(0.3)  # Throttle to avoid Yahoo rate limits
        quote = _fetch_yahoo_quote(symbol)
        if not quote.get("error") and quote.get("price"):
            sector_data.append({
                "symbol": symbol,
                "name": info["name"],
                "weight": info["weight"],
                "price": quote.get("price", 0),
                "change_pct": quote.get("change_pct", 0),
                "market_state": quote.get("market_state", "UNKNOWN"),
            })

    # Calculate relative strength vs SPY
    for sector in sector_data:
        # Relative strength = sector change / benchmark change (simplified)
        sector["relative_strength"] = round(
            sector["change_pct"] - spy.get("change_pct", 0), 2
        ) if spy.get("change_pct") else 0

        # Momentum score based on relative strength
        rs = sector["relative_strength"]
        if rs > 1:
            sector["momentum"] = "STRONG_LEADER"
            sector["signal"] = "BUY"
        elif rs > 0:
            sector["momentum"] = "LEADER"
            sector["signal"] = "OVERWEIGHT"
        elif rs > -1:
            sector["momentum"] = "LAGGARD"
            sector["signal"] = "UNDERWEIGHT"
        else:
            sector["momentum"] = "STRONG_LAGGARD"
            sector["signal"] = "SELL"

    # Sort by relative strength (leaders first)
    sector_data.sort(key=lambda x: x.get("relative_strength", 0), reverse=True)

    leaders = [s for s in sector_data if s["relative_strength"] > 0]
    laggards = [s for s in sector_data if s["relative_strength"] <= 0]

    result = {
        "benchmark": {
            "symbol": "SPY",
            "price": spy.get("price", 0),
            "change_pct": spy.get("change_pct", 0),
        },
        "sectors": sector_data,
        "leaders": leaders,
        "laggards": laggards,
        "rotation_signal": _determine_rotation_signal(leaders, laggards),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set("sector_rotation", result, TTL_SECTOR_DATA)
    return result


def _determine_rotation_signal(leaders: list, laggards: list) -> dict:
    """Determine market regime from sector leadership."""
    leader_names = [l["name"] for l in leaders]
    laggard_names = [l["name"] for l in laggards]

    # Defensive sectors
    defensive = {"Consumer Staples", "Utilities", "Health Care"}
    growth = {"Technology", "Consumer Disc.", "Communication"}

    leader_defensive = len([l for l in leader_names if l in defensive])
    leader_growth = len([l for l in leader_names if l in growth])

    if leader_defensive > leader_growth and len(leaders) < 5:
        regime = "RISK_OFF"
        description = "Defensive rotation — markets shifting to safety. Consider reducing equity exposure and increasing bonds/dividend stocks."
    elif leader_growth > leader_defensive:
        regime = "RISK_ON"
        description = "Growth rotation — markets favoring risk assets. Technology and consumer discretionary leading. Good environment for equities."
    else:
        regime = "MIXED"
        description = "Mixed signals — no clear rotation pattern. Maintain diversified allocation."

    return {
        "regime": regime,
        "description": description,
        "leaders": leader_names,
        "laggards": laggard_names,
    }


@router.get("/sectors/{symbol}/history")
def get_sector_history(symbol: str, days: int = Query(90, ge=30, le=365), user: Optional[User] = Depends(get_optional_user)):
    """Get historical price data for a sector ETF."""
    symbol = symbol.upper()
    if symbol not in SECTOR_ETFS:
        raise HTTPException(status_code=404, detail=f"Sector ETF {symbol} not found")

    history = _fetch_history(symbol, days)
    return {
        "symbol": symbol,
        "name": SECTOR_ETFS[symbol]["name"],
        "days": days,
        "prices": history,
        "data_points": len(history),
    }


@router.get("/options/{symbol}")
def get_options_data(symbol: str, user: Optional[User] = Depends(get_optional_user)):
    """Get options data for a stock.

    Since free Yahoo options chains require complex parsing,
    we provide implied volatility analysis and put/call ratio estimation.
    """
    symbol = symbol.upper()
    cache = get_cache()
    cache_key = f"options_{symbol}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Fetch stock price
    quote = _fetch_yahoo_quote(symbol)
    if quote.get("error"):
        raise HTTPException(status_code=404, detail="Stock not found")

    price = quote.get("price", 0)

    # Fetch options chain from Yahoo (v8 doesn't support this directly)
    # We'll estimate based on historical volatility
    history = _fetch_history(symbol, 30)

    # Calculate historical volatility
    if len(history) >= 20:
        returns = np.diff(np.log(np.array(history, dtype=float)))
        hist_vol = float(np.std(returns) * np.sqrt(252) * 100)  # Annualized
    else:
        hist_vol = 30.0  # Default assumption

    # Estimate implied volatility (typically ~15-30% higher than historical)
    iv_estimate = round(hist_vol * 1.2, 2)

    # Generate synthetic options data based on Black-Scholes-like pricing
    strike_range = [round(price * m, 2) for m in [0.90, 0.92, 0.95, 0.97, 1.0, 1.03, 1.05, 1.08, 1.10]]

    # Simple estimated Greeks
    options_data = []
    for strike in strike_range:
        moneyness = price / strike
        # Approximate delta
        if strike < price:
            delta = round(min(0.5 + (moneyness - 1) * 5, 1.0), 3)
        else:
            delta = round(max(0.5 - (1 - moneyness) * 5, 0.0), 3)

        # Approximate premium (simplified)
        time_value = price * (iv_estimate / 100) * 0.05  # ~5% of stock price
        intrinsic = max(price - strike, 0)
        call_premium = round(intrinsic + time_value, 2)
        put_premium = round(max(strike - price, 0) + time_value, 2)

        options_data.append({
            "strike": strike,
            "call": {
                "premium": call_premium,
                "delta": delta,
                "implied_volatility": iv_estimate,
            },
            "put": {
                "premium": put_premium,
                "delta": round(delta - 1, 3),
                "implied_volatility": iv_estimate,
            },
        })

    # Estimate put/call ratio (based on IV skew)
    pcr_estimate = round(0.8 + (iv_estimate - 20) / 100, 2)
    pcr_signal = "BEARISH" if pcr_estimate > 1.2 else "BULLISH" if pcr_estimate < 0.7 else "NEUTRAL"

    result = {
        "symbol": symbol,
        "underlying_price": price,
        "historical_volatility": round(hist_vol, 2),
        "implied_volatility_estimate": iv_estimate,
        "iv_hv_ratio": round(iv_estimate / hist_vol, 2) if hist_vol > 0 else 1.0,
        "put_call_ratio": pcr_estimate,
        "put_call_signal": pcr_signal,
        "options_chain": options_data,
        "note": "Options data estimated from historical volatility. For live options chains, connect a broker API (e.g., Alpaca, IBKR).",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set(cache_key, result, TTL_TECHNICALS)
    return result


@router.get("/dividends")
def get_dividend_screener(
    min_yield: float = Query(2.0, description="Minimum dividend yield %"),
    user: Optional[User] = Depends(get_optional_user),
):
    """Dividend yield screener across major stocks and ETFs.

    Shows high-yield opportunities for income-focused investors.
    """
    cache = get_cache()
    cache_key = f"dividends_{min_yield}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Screen a curated list of dividend stocks and ETFs
    dividend_symbols = [
        "JNJ", "PG", "KO", "PEP", "MMM", "T", "VZ", "XOM", "CVX", "WMT",
        "ABBV", "MRK", "JPM", "BAC", "WFC", "O", "NEE", "SO", "DUK", "D",
        "TMO", "ABT", "PFE", "BMY", "LMT", "RTX", "HON", "CAT", "DE", "IBM",
        "SCHD", "VYM", "HDV", "DVY", "JEPI", "QYLD", "SPYI", "NUSI",
    ]

    quotes = _fetch_yahoo_v7_quotes(dividend_symbols)

    dividend_stocks = []
    for sym in dividend_symbols:
        if sym in quotes:
            q = quotes[sym]
            dy = round((q.get("dividendYield") or 0) * 100, 2)
            if dy >= min_yield:
                dividend_stocks.append({
                    "symbol": sym,
                    "price": q.get("regularMarketPrice", 0),
                    "dividend_yield": dy,
                    "change_pct": round(q.get("regularMarketChangePercent", 0) or 0, 2),
                    "pe_ratio": q.get("trailingPE"),
                    "market_cap": q.get("regularMarketMarketCap", 0),
                    "sector": "ETF" if sym in MAJOR_ETFS else "Stock",
                })

    # Sort by yield
    dividend_stocks.sort(key=lambda x: x["dividend_yield"], reverse=True)

    result = {
        "min_yield_filter": min_yield,
        "stocks": dividend_stocks,
        "count": len(dividend_stocks),
        "avg_yield": round(np.mean([s["dividend_yield"] for s in dividend_stocks]), 2) if dividend_stocks else 0,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set(cache_key, result, TTL_STOCK_PRICES)
    return result


@router.get("/etf-overview")
def get_etf_overview(user: Optional[User] = Depends(get_optional_user)):
    """Overview of major ETFs across asset classes."""
    cache = get_cache()
    cached = cache.get("etf_overview")
    if cached:
        return cached

    etf_symbols = list(MAJOR_ETFS.keys())
    quotes = _fetch_yahoo_v7_quotes(etf_symbols)

    etfs = []
    for sym in etf_symbols:
        if sym in quotes:
            q = quotes[sym]
            etfs.append({
                "symbol": sym,
                "name": MAJOR_ETFS.get(sym, sym),
                "price": q.get("regularMarketPrice", 0),
                "change_pct": round(q.get("regularMarketChangePercent", 0) or 0, 2),
                "volume": q.get("regularMarketVolume", 0),
                "market_cap": q.get("regularMarketMarketCap", 0),
            })

    # Categorize
    categories = {
        "index": [e for e in etfs if e["symbol"] in ("SPY", "QQQ", "IWM", "VTI")],
        "international": [e for e in etfs if e["symbol"] in ("VEA", "VWO", "EEM", "FXI")],
        "fixed_income": [e for e in etfs if e["symbol"] in ("TLT", "IEF", "SHY", "HYG", "LQD")],
        "commodities": [e for e in etfs if e["symbol"] in ("GLD", "SLV", "USO")],
        "thematic": [e for e in etfs if e["symbol"] in ("ARKK", "SOXX", "XBI", "BITO")],
    }

    result = {
        "etfs": etfs,
        "categories": categories,
        "count": len(etfs),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set("etf_overview", result, TTL_STOCK_PRICES)
    return result


@router.get("/technical-analysis/{symbol}")
def get_technical_analysis(symbol: str, days: int = Query(200, ge=30, le=365), user: Optional[User] = Depends(get_optional_user)):
    """Full technical analysis for any stock or ETF."""
    symbol = symbol.upper()

    history = _fetch_history(symbol, days)
    if len(history) < 20:
        raise HTTPException(status_code=404, detail=f"Insufficient data for {symbol}. Need at least 20 days.")

    quote = _fetch_yahoo_quote(symbol)
    price = quote.get("price", history[-1])

    rsi = _calculate_rsi(history)
    macd = _calculate_macd(history)
    ma = _calculate_moving_averages(history)
    bb = _calculate_bollinger_bands(history)
    sr = _detect_support_resistance(history)
    signal = _generate_signal(rsi, macd, ma, bb)

    return {
        "symbol": symbol,
        "price": price,
        "data_points": len(history),
        "technicals": {
            "rsi": rsi,
            "macd": macd,
            "moving_averages": ma,
            "bollinger_bands": bb,
            "support_resistance": sr,
        },
        "signal": signal,
        "price_history": history[-30:],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/top-movers")
def get_top_movers(user: Optional[User] = Depends(get_optional_user)):
    """Top gainers and losers from the tracked stock universe."""
    cache = get_cache()
    cached = cache.get("top_movers")
    if cached:
        return cached

    symbols = list(SP500_TOP50.keys()) + list(NASDAQ100_EXTRA.keys())
    # Deduplicate
    symbols = list(dict.fromkeys(symbols))

    quotes = _fetch_yahoo_v7_quotes(symbols[:50])

    all_stocks = []
    for sym, q in quotes.items():
        all_stocks.append({
            "symbol": sym,
            "name": SP500_TOP50.get(sym) or NASDAQ100_EXTRA.get(sym) or sym,
            "price": q.get("regularMarketPrice", 0),
            "change_pct": round(q.get("regularMarketChangePercent", 0) or 0, 2),
            "volume": q.get("regularMarketVolume", 0),
        })

    all_stocks.sort(key=lambda x: x["change_pct"], reverse=True)

    result = {
        "gainers": all_stocks[:10],
        "losers": all_stocks[-10:][::-1],  # Reverse to show biggest losers first
        "most_active": sorted(all_stocks, key=lambda x: x.get("volume") or 0, reverse=True)[:10],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set("top_movers", result, TTL_STOCK_PRICES)
    return result


@router.get("/search")
def search_stocks(q: str = Query(..., min_length=1, description="Search query"), user: Optional[User] = Depends(get_optional_user)):
    """Search stocks by name or symbol."""
    query = q.upper()
    results = []

    # Search in SP500 + NASDAQ
    all_stocks = {**SP500_TOP50, **NASDAQ100_EXTRA}
    for symbol, name in all_stocks.items():
        if query in symbol or query in name.upper():
            results.append({"symbol": symbol, "name": name, "type": "stock"})

    # Search in ETFs
    for symbol, name in MAJOR_ETFS.items():
        if query in symbol or query in name.upper():
            results.append({"symbol": symbol, "name": name, "type": "etf"})

    # Search in sector ETFs
    for symbol, info in SECTOR_ETFS.items():
        if query in symbol or query in info["name"].upper():
            results.append({"symbol": symbol, "name": info["name"], "type": "sector"})

    return {"query": q, "results": results[:20], "count": len(results)}
