"""
Crypto Market Data Fetcher — Free data from CoinGecko (no API key).

Provides:
- Real-time crypto prices (BTC, ETH, SOL, XRP, ADA, DOT, etc.)
- Market cap and 24h volume
- Price changes (1h, 24h, 7d, 30d)
- Historical prices for correlation analysis
- Fear & Greed index

CoinGecko free tier: 10-30 requests/minute (sufficient with caching).
"""
import logging
from datetime import datetime, timezone

import requests

from app.market_data.cache import get_cache

logger = logging.getLogger("quantive.market_data.crypto")

# CoinGecko free API (no key needed)
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Top cryptocurrencies relevant to sovereign finance & digital asset tracking
TRACKED_CRYPTOS = [
    {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"},
    {"id": "ethereum", "symbol": "ETH", "name": "Ethereum"},
    {"id": "tether", "symbol": "USDT", "name": "Tether"},
    {"id": "binancecoin", "symbol": "BNB", "name": "BNB"},
    {"id": "solana", "symbol": "SOL", "name": "Solana"},
    {"id": "ripple", "symbol": "XRP", "name": "XRP"},
    {"id": "usd-coin", "symbol": "USDC", "name": "USD Coin"},
    {"id": "cardano", "symbol": "ADA", "name": "Cardano"},
    {"id": "dogecoin", "symbol": "DOGE", "name": "Dogecoin"},
    {"id": "polkadot", "symbol": "DOT", "name": "Polkadot"},
    {"id": "avalanche-2", "symbol": "AVAX", "name": "Avalanche"},
    {"id": "chainlink", "symbol": "LINK", "name": "Chainlink"},
    {"id": "tron", "symbol": "TRX", "name": "TRON"},
    {"id": "matic-network", "symbol": "MATIC", "name": "Polygon"},
    {"id": "litecoin", "symbol": "LTC", "name": "Litecoin"},
]

# TTL for crypto data
TTL_CRYPTO_PRICES = 2 * 60       # 2 minutes — crypto is volatile
TTL_CRYPTO_MARKET = 5 * 60       # 5 minutes for market data
TTL_FEAR_GREED = 30 * 60         # 30 minutes for fear & greed


def fetch_crypto_prices(
    vs_currency: str = "usd",
    use_cache: bool = True,
) -> dict:
    """Fetch real-time prices for tracked cryptocurrencies.

    Uses CoinGecko /coins/markets endpoint (free, no key).

    Returns:
        {
            "prices": [
                {
                    "id": "bitcoin",
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "current_price": 67542.31,
                    "market_cap": 1328000000000,
                    "market_cap_rank": 1,
                    "total_volume": 28500000000,
                    "price_change_percentage_1h_in_currency": 0.12,
                    "price_change_percentage_24h": -1.23,
                    "price_change_percentage_7d_in_currency": 5.67,
                    "price_change_percentage_30d_in_currency": 12.45,
                    "ath": 73750.07,
                    "ath_change_percentage": -8.42,
                    "circulating_supply": 19700000,
                    "total_supply": 21000000,
                    "last_updated": "2026-09-01T10:00:00Z"
                },
                ...
            ],
            "total_market_cap_usd": 2450000000000,
            "total_volume_24h_usd": 89000000000,
            "btc_dominance_pct": 54.2,
            "fetched_at": "..."
        }
    """
    cache = get_cache()
    cache_key = f"crypto_prices_{vs_currency}"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        coin_ids = ",".join(c["id"] for c in TRACKED_CRYPTOS)
        url = f"{COINGECKO_BASE}/coins/markets"
        params = {
            "vs_currency": vs_currency,
            "ids": coin_ids,
            "order": "market_cap_desc",
            "per_page": 20,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "1h,24h,7d,30d",
        }
        headers = {"User-Agent": "Quantive/1.0"}

        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        # Enrich with tracked metadata
        tracked_map = {c["id"]: c for c in TRACKED_CRYPTOS}
        prices = []
        for coin in data:
            meta = tracked_map.get(coin["id"], {})
            prices.append({
                "id": coin["id"],
                "symbol": meta.get("symbol", coin.get("symbol", "").upper()),
                "name": meta.get("name", coin.get("name", "")),
                "current_price": coin.get("current_price", 0),
                "market_cap": coin.get("market_cap", 0),
                "market_cap_rank": coin.get("market_cap_rank", 0),
                "total_volume": coin.get("total_volume", 0),
                "price_change_percentage_1h_in_currency": coin.get("price_change_percentage_1h_in_currency", 0) or 0,
                "price_change_percentage_24h": coin.get("price_change_percentage_24h", 0) or 0,
                "price_change_percentage_7d_in_currency": coin.get("price_change_percentage_7d_in_currency", 0) or 0,
                "price_change_percentage_30d_in_currency": coin.get("price_change_percentage_30d_in_currency", 0) or 0,
                "ath": coin.get("ath", 0),
                "ath_change_percentage": coin.get("ath_change_percentage", 0) or 0,
                "circulating_supply": coin.get("circulating_supply", 0),
                "total_supply": coin.get("total_supply", 0),
                "last_updated": coin.get("last_updated", ""),
            })

        # Calculate aggregates
        total_market_cap = sum(p["market_cap"] for p in prices if p["market_cap"])
        total_volume = sum(p["total_volume"] for p in prices if p["total_volume"])
        btc_market_cap = next((p["market_cap"] for p in prices if p["symbol"] == "BTC"), 0)
        btc_dominance = (btc_market_cap / total_market_cap * 100) if total_market_cap > 0 else 0

        result = {
            "prices": prices,
            "total_market_cap_usd": total_market_cap,
            "total_volume_24h_usd": total_volume,
            "btc_dominance_pct": round(btc_dominance, 1),
            "tracked_count": len(prices),
            "vs_currency": vs_currency,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        cache.set(cache_key, result, TTL_CRYPTO_PRICES)
        return result

    except Exception as e:
        logger.warning(f"Crypto price fetch failed: {e}")
        return _fallback_crypto_prices()


def fetch_crypto_detail(
    coin_id: str,
    vs_currency: str = "usd",
    use_cache: bool = True,
) -> dict:
    """Fetch detailed data for a specific cryptocurrency.

    Includes description, links, market data, and historical prices.
    """
    cache = get_cache()
    cache_key = f"crypto_detail_{coin_id}_{vs_currency}"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        url = f"{COINGECKO_BASE}/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        }
        headers = {"User-Agent": "Quantive/1.0"}

        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        market = data.get("market_data", {})

        result = {
            "id": data.get("id"),
            "symbol": data.get("symbol", "").upper(),
            "name": data.get("name", ""),
            "description": (data.get("description", {}).get("en", "") or "")[:500],
            "categories": data.get("categories", []),
            "genesis_date": data.get("genesis_date"),
            "homepage": (data.get("links", {}).get("homepage", [None]) or [None])[0],
            "current_price": market.get("current_price", {}).get(vs_currency, 0),
            "market_cap": market.get("market_cap", {}).get(vs_currency, 0),
            "market_cap_rank": market.get("market_cap_rank"),
            "total_volume": market.get("total_volume", {}).get(vs_currency, 0),
            "high_24h": market.get("high_24h", {}).get(vs_currency, 0),
            "low_24h": market.get("low_24h", {}).get(vs_currency, 0),
            "price_change_24h": market.get("price_change_24h", 0),
            "price_change_percentage_24h": market.get("price_change_percentage_24h", 0),
            "price_change_percentage_7d": market.get("price_change_percentage_7d", 0),
            "price_change_percentage_30d": market.get("price_change_percentage_30d", 0),
            "price_change_percentage_1y": market.get("price_change_percentage_1y", 0),
            "ath": market.get("ath", {}).get(vs_currency, 0),
            "ath_date": market.get("ath_date", {}).get(vs_currency),
            "atl": market.get("atl", {}).get(vs_currency, 0),
            "atl_date": market.get("atl_date", {}).get(vs_currency),
            "circulating_supply": market.get("circulating_supply", 0),
            "total_supply": market.get("total_supply", 0),
            "max_supply": market.get("max_supply", 0),
            "fully_diluted_valuation": market.get("fully_diluted_valuation", {}).get(vs_currency, 0),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        cache.set(cache_key, result, TTL_CRYPTO_MARKET)
        return result

    except Exception as e:
        logger.warning(f"Crypto detail fetch failed for {coin_id}: {e}")
        return {"error": str(e)}


def fetch_crypto_history(
    coin_id: str,
    vs_currency: str = "usd",
    days: int = 30,
    use_cache: bool = True,
) -> dict:
    """Fetch historical price data for a cryptocurrency.

    Used for correlation analysis and charting.
    """
    cache = get_cache()
    cache_key = f"crypto_history_{coin_id}_{days}d"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": vs_currency,
            "days": str(days),
            "interval": "daily",
        }
        headers = {"User-Agent": "Quantive/1.0"}

        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        prices = [
            {
                "timestamp": p[0],
                "date": datetime.fromtimestamp(p[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                "price": p[1],
            }
            for p in data.get("prices", [])
        ]

        volumes = [
            {
                "timestamp": v[0],
                "date": datetime.fromtimestamp(v[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                "volume": v[1],
            }
            for v in data.get("total_volumes", [])
        ]

        result = {
            "coin_id": coin_id,
            "vs_currency": vs_currency,
            "days": days,
            "prices": prices,
            "volumes": volumes,
            "data_points": len(prices),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        cache.set(cache_key, result, 30 * 60)  # 30 min cache for history
        return result

    except Exception as e:
        logger.warning(f"Crypto history fetch failed for {coin_id}: {e}")
        return {"error": str(e)}


def fetch_fear_greed_index(use_cache: bool = True) -> dict:
    """Fetch the Crypto Fear & Greed Index.

    Source: alternative.me (free, no key)
    """
    cache = get_cache()
    cache_key = "crypto_fear_greed"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        url = "https://api.alternative.me/fng/"
        params = {"limit": "7", "format": "json"}
        headers = {"User-Agent": "Quantive/1.0"}

        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        entries = data.get("data", [])
        current = entries[0] if entries else {}

        history = []
        for entry in entries:
            history.append({
                "value": int(entry.get("value", 0)),
                "label": entry.get("value_classification", ""),
                "timestamp": entry.get("timestamp", ""),
                "date": datetime.fromtimestamp(
                    int(entry.get("timestamp", 0)), tz=timezone.utc
                ).strftime("%Y-%m-%d") if entry.get("timestamp") else "",
            })

        result = {
            "current_value": int(current.get("value", 0)),
            "current_label": current.get("value_classification", "Unknown"),
            "history": history,
            "interpretation": _interpret_fear_greed(int(current.get("value", 50))),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        cache.set(cache_key, result, TTL_FEAR_GREED)
        return result

    except Exception as e:
        logger.warning(f"Fear & Greed index fetch failed: {e}")
        return {
            "current_value": 50,
            "current_label": "Neutral",
            "history": [],
            "interpretation": "Data unavailable",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }


def _interpret_fear_greed(value: int) -> str:
    """Interpret the Fear & Greed Index value."""
    if value <= 20:
        return "Extreme Fear — potential buying opportunity; markets oversold"
    elif value <= 40:
        return "Fear — cautious sentiment; some undervaluation possible"
    elif value <= 60:
        return "Neutral — balanced market sentiment"
    elif value <= 80:
        return "Greed — bullish sentiment; consider taking profits"
    else:
        return "Extreme Greed — potential bubble risk; high caution warranted"


def _fallback_crypto_prices() -> dict:
    """Fallback prices when CoinGecko is unavailable."""
    return {
        "prices": [
            {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "current_price": 67500, "market_cap": 1328000000000, "market_cap_rank": 1, "total_volume": 28500000000, "price_change_percentage_24h": 0, "price_change_percentage_7d_in_currency": 0, "price_change_percentage_30d_in_currency": 0, "ath": 73750, "ath_change_percentage": -8.5, "circulating_supply": 19700000, "total_supply": 21000000},
            {"id": "ethereum", "symbol": "ETH", "name": "Ethereum", "current_price": 3450, "market_cap": 415000000000, "market_cap_rank": 2, "total_volume": 14200000000, "price_change_percentage_24h": 0, "price_change_percentage_7d_in_currency": 0, "price_change_percentage_30d_in_currency": 0, "ath": 4878, "ath_change_percentage": -29.3, "circulating_supply": 120200000, "total_supply": 120200000},
        ],
        "total_market_cap_usd": 1743000000000,
        "total_volume_24h_usd": 42700000000,
        "btc_dominance_pct": 54.5,
        "tracked_count": 2,
        "vs_currency": "usd",
        "is_fallback": True,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
