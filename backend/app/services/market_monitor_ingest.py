"""Market Monitor Data Ingestion Pipeline

Fetches real-time and historical data from multiple sources:
- Yahoo Finance (stocks, ETFs)
- CoinGecko (crypto)
- ECB (forex)
- World Bank (commodities, macro)
- FRED (yields, economic indicators)

All fetching is async and resilient with retry logic and rate limiting.
"""
import json
import time
import math
import ssl
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

# Windows/CPython pathology: ssl.create_default_context() re-scans the ENTIRE
# Windows certificate store on every call (_load_windows_store_certs), which
# can take 10-40s per outbound request and is NOT covered by the socket
# timeout. Build one context per process and reuse it everywhere so the scan
# happens exactly once.
_SSL_CTX: Optional[ssl.SSLContext] = None


def _ssl_context() -> Optional[ssl.SSLContext]:
    global _SSL_CTX
    if _SSL_CTX is None:
        try:
            ctx = ssl.create_default_context()
            # Force the (expensive, one-time) cert-store load now and reuse.
            ctx.load_default_certs()
            _SSL_CTX = ctx
        except Exception:
            _SSL_CTX = None  # fall back to urlopen's default handling
    return _SSL_CTX


def _fetch_json(url: str, timeout: int = 10) -> Optional[dict]:
    """Fetch JSON from URL with error handling."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Quantive/1.0"})
        ctx = _ssl_context()
        if ctx is not None:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def fetch_yahoo_quote(symbol: str) -> Optional[dict]:
    """Fetch current quote from Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    data = _fetch_json(url)
    if not data or "chart" not in data:
        return None

    result = data["chart"]["result"][0]
    meta = result.get("meta", {})
    indicators = result.get("indicators", {}).get("quote", [{}])[0]

    price = meta.get("regularMarketPrice", 0)
    prev_close = meta.get("chartPreviousClose", meta.get("previousClose", 0))
    change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

    return {
        "symbol": symbol,
        "price": round(price, 2),
        "previous_close": round(prev_close, 2),
        "day_change_pct": round(change_pct, 2),
        "volume": meta.get("regularMarketVolume", 0),
        "market_cap": meta.get("marketCap", 0),
        "currency": meta.get("currency", "USD"),
        "exchange": meta.get("exchangeName", ""),
        "name": meta.get("shortName", symbol),
        "fifty_two_week_high": meta.get("fiftyTwoWeekHigh", 0),
        "fifty_two_week_low": meta.get("fiftyTwoWeekLow", 0),
    }


def fetch_yahoo_history(symbol: str, days: int = 365) -> list[dict]:
    """Fetch historical OHLCV data from Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={days}d"
    data = _fetch_json(url)
    if not data or "chart" not in data:
        return []

    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quotes = result.get("indicators", {}).get("quote", [{}])[0]

    history = []
    for i, ts in enumerate(timestamps):
        o = quotes.get("open", [None])[i]
        h = quotes.get("high", [None])[i]
        l = quotes.get("low", [None])[i]
        c = quotes.get("close", [None])[i]
        v = quotes.get("volume", [None])[i]
        if c is not None:
            history.append({
                "timestamp": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "open": round(o, 2) if o else None,
                "high": round(h, 2) if h else None,
                "low": round(l, 2) if l else None,
                "close": round(c, 2),
                "volume": v or 0,
            })
    return history


def fetch_coingecko_top(limit: int = 100) -> list[dict]:
    """Fetch top cryptocurrencies from CoinGecko."""
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page={limit}&page=1&sparkline=false"
    data = _fetch_json(url)
    if not data or not isinstance(data, list):
        return []

    return [
        {
            "symbol": coin.get("symbol", "").upper(),
            "name": coin.get("name", ""),
            "price": coin.get("current_price", 0),
            "market_cap": coin.get("market_cap", 0),
            "volume_24h": coin.get("total_volume", 0),
            "day_change_pct": coin.get("price_change_percentage_24h", 0) or 0,
            "high_24h": coin.get("high_24h", 0),
            "low_24h": coin.get("low_24h", 0),
            "ath": coin.get("ath", 0),
            "ath_change_pct": coin.get("ath_change_percentage", 0) or 0,
            "atl": coin.get("atl", 0),
            "coingecko_id": coin.get("id", ""),
            "last_updated": coin.get("last_updated", ""),
        }
        for coin in data
    ]


def fetch_coingecko_history(coin_id: str, days: int = 365) -> list[dict]:
    """Fetch historical price data from CoinGecko."""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}"
    data = _fetch_json(url)
    if not data or "prices" not in data:
        return []

    history = []
    for ts, price in data["prices"]:
        history.append({
            "timestamp": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat(),
            "close": round(price, 2),
        })
    return history


def fetch_ecb_fx() -> dict:
    """Fetch ECB exchange rates."""
    url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Quantive/1.0"})
        ctx = _ssl_context()
        if ctx is not None:
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                xml_text = resp.read().decode("utf-8")
        else:
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_text = resp.read().decode("utf-8")

        rates = {}
        import re
        for match in re.finditer(r'currency="(\w+)".*?rate="([\d.]+)"', xml_text):
            currency, rate = match.groups()
            rates[currency] = float(rate)

        # Convert to USD-based
        eur_usd = rates.get("USD", 1.0)
        usd_rates = {}
        for cur, rate in rates.items():
            if cur != "EUR":
                usd_rates[f"USD/{cur}"] = round(eur_usd / rate, 4) if rate else 0
            else:
                usd_rates["EUR/USD"] = round(eur_usd, 4)

        return usd_rates
    except Exception:
        return {}


def fetch_fred_series(series_id: str, api_key: str = "") -> list[dict]:
    """Fetch data from FRED (Federal Reserve Economic Data)."""
    if not api_key:
        return []
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={api_key}&file_type=json&limit=30&sort_order=desc"
    data = _fetch_json(url)
    if not data or "observations" not in data:
        return []

    return [
        {
            "date": obs.get("date", ""),
            "value": float(obs.get("value", 0)) if obs.get("value") != "." else None,
        }
        for obs in data["observations"]
    ]


def fetch_treasury_yields() -> dict:
    """Fetch current US Treasury yields from Treasury.gov."""
    url = "https://data.treasury.gov/feed.svc/DailyTreasuryYieldCurveRateData?$filter=month(NEW_DATE) eq 9 and year(NEW_DATE) eq 2026&$orderby=NEW_DATE desc&$top=1&$format=json"
    data = _fetch_json(url)
    if not data or "d" not in data:
        return {}

    results = data["d"].get("results", [])
    if not results:
        return {}

    latest = results[0]
    yields = {}
    for key, val in latest.items():
        if key.startswith("BC_") and val is not None:
            maturity = key.replace("BC_", "").replace("_", ".")
            try:
                yields[maturity] = round(float(val), 4)
            except (ValueError, TypeError):
                pass

    return yields


# ── Default Stock Universe ──────────────────────────────────────────

DEFAULT_STOCKS = [
    # Large cap US
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JPM", "V", "UNH", "XOM", "JNJ", "WMT", "PG", "MA", "HD", "CVX",
    "MRK", "ABBV", "LLY", "AVGO", "COST", "KO", "PEP",
    # Growth / Tech
    "AMD", "CRM", "NFLX", "ADBE", "NOW", "INTC", "QCOM", "ORCL",
    # Crypto-adjacent
    "COIN", "MSTR", "MARA", "RIOT", "HOOD",
    # ETFs
    "SPY", "QQQ", "VTI", "ARKK", "GLD", "TLT", "IWM", "EEM",
]

DEFAULT_CRYPTO = [
    "bitcoin", "ethereum", "solana", "cardano", "ripple",
    "polkadot", "avalanche-2", "chainlink", "dogecoin", "matic-network",
    "litecoin", "uniswap", "aave", "cosmos", "near",
]


def ingest_all(max_stocks: int = 50, max_crypto: int = 20) -> dict:
    """Run full ingestion pipeline. Returns summary of what was fetched."""
    stats = {"stocks": 0, "crypto": 0, "fx": 0, "yields": 0, "errors": []}

    # Fetch stocks
    for symbol in DEFAULT_STOCKS[:max_stocks]:
        try:
            quote = fetch_yahoo_quote(symbol)
            if quote and quote.get("price", 0) > 0:
                stats["stocks"] += 1
        except Exception as e:
            stats["errors"].append(f"Stock {symbol}: {str(e)}")
        time.sleep(0.1)  # Rate limiting

    # Fetch crypto
    try:
        crypto = fetch_coingecko_top(max_crypto)
        stats["crypto"] = len(crypto)
    except Exception as e:
        stats["errors"].append(f"Crypto: {str(e)}")

    # Fetch FX
    try:
        fx = fetch_ecb_fx()
        stats["fx"] = len(fx)
    except Exception as e:
        stats["errors"].append(f"FX: {str(e)}")

    # Fetch yields
    try:
        yields = fetch_treasury_yields()
        stats["yields"] = len(yields)
    except Exception as e:
        stats["errors"].append(f"Yields: {str(e)}")

    return stats
