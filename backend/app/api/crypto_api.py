"""
Crypto Market Tracker API
=========================

Live cryptocurrency prices, market data, and portfolio tracking
using CoinGecko free API (no key required).

Provides:
- Live prices for top 50 cryptos
- Portfolio value calculation
- Price alerts
- Market overview stats
"""

import time
from typing import Optional

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/crypto", tags=["crypto"])

# ── Cache ──────────────────────────────────────────────────────────
_cache: dict = {}
CACHE_TTL = 120  # 2 minutes

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Top 50 coins by market cap
TOP_COINS = [
    "bitcoin", "ethereum", "tether", "binancecoin", "solana",
    "ripple", "usd-coin", "staked-ether", "dogecoin", "cardano",
    "tron", "avalanche-2", "chainlink", "polkadot", "wrapped-bitcoin",
    "shiba-inu", "matic-network", "litecoin", "uniswap", "dai",
    "bitcoin-cash", "stellar", "cosmos", "monero", "tron",
    "filecoin", "aptos", "near", "arbitrum", "optimism",
    "render-token", "the-graph", "aave", "maker", "immutable-x",
    "fantom", "algorand", "theta-token", "vechain", "hedera-hashgraph",
    "classic-readme", "eos", "axie-infinity", "the-sandbox", "decentraland",
    "pepe", "bonk", "floki", "sei-network", "celestia",
]

# Fiat currencies to show
VS_CURRENCIES = "usd"


class CryptoPrice(BaseModel):
    id: str
    symbol: str
    name: str
    current_price: float
    market_cap: float
    market_cap_rank: int
    price_change_24h: float
    price_change_percentage_24h: float
    price_change_percentage_7d: float
    total_volume: float
    high_24h: float
    low_24h: float
    circulating_supply: float
    total_supply: Optional[float] = None


class MarketOverview(BaseModel):
    total_market_cap: float
    total_volume_24h: float
    btc_dominance: float
    eth_dominance: float
    active_cryptos: int
    market_cap_change_24h: float
    market_cap_change_percentage_24h: float


async def _fetch_coingecko(endpoint: str, params: dict = None) -> dict:
    """Fetch from CoinGecko with caching."""
    cache_key = endpoint + str(params or {})
    if cache_key in _cache:
        data, ts = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return data

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{COINGECKO_BASE}{endpoint}", params=params or {})
            r.raise_for_status()
            data = r.json()
            _cache[cache_key] = (data, time.time())
            return data
    except Exception as e:
        print(f"[CRYPTO] CoinGecko error: {e}")
        return _cache.get(cache_key, ({}, 0))[0]


@router.get("/prices")
async def get_prices(
    vs_currency: str = Query("usd"),
    limit: int = Query(50, ge=1, le=250),
):
    """Get live prices for top cryptocurrencies."""
    data = await _fetch_coingecko("/coins/markets", {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": min(limit, 250),
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d",
    })
    if not data:
        return {"prices": [], "source": "unavailable"}

    prices = []
    for coin in data[:limit]:
        prices.append(CryptoPrice(
            id=coin.get("id", ""),
            symbol=coin.get("symbol", ""),
            name=coin.get("name", ""),
            current_price=coin.get("current_price", 0) or 0,
            market_cap=coin.get("market_cap", 0) or 0,
            market_cap_rank=coin.get("market_cap_rank", 0) or 0,
            price_change_24h=coin.get("price_change_24h", 0) or 0,
            price_change_percentage_24h=coin.get("price_change_percentage_24h", 0) or 0,
            price_change_percentage_7d=coin.get("price_change_percentage_7d_in_currency", 0) or 0,
            total_volume=coin.get("total_volume", 0) or 0,
            high_24h=coin.get("high_24h", 0) or 0,
            low_24h=coin.get("low_24h", 0) or 0,
            circulating_supply=coin.get("circulating_supply", 0) or 0,
            total_supply=coin.get("total_supply"),
        ).model_dump())

    return {"prices": prices, "source": "coingecko", "count": len(prices)}


@router.get("/overview")
async def market_overview():
    """Get crypto market overview stats."""
    data = await _fetch_coingecko("/global")
    if not data or "data" not in data:
        return {"error": "unavailable"}

    d = data["data"]
    return MarketOverview(
        total_market_cap=d.get("total_market_cap", {}).get("usd", 0),
        total_volume_24h=d.get("total_volume", {}).get("usd", 0),
        btc_dominance=d.get("market_cap_percentage", {}).get("btc", 0),
        eth_dominance=d.get("market_cap_percentage", {}).get("eth", 0),
        active_cryptos=d.get("active_cryptocurrencies", 0),
        market_cap_change_24h=d.get("market_cap_change_percentage_24h_usd", 0),
        market_cap_change_percentage_24h=d.get("market_cap_change_percentage_24h_usd", 0),
    ).model_dump()


@router.get("/coin/{coin_id}")
async def get_coin_detail(coin_id: str):
    """Get detailed info for a specific coin."""
    data = await _fetch_coingecko(f"/coins/{coin_id}", {
        "localization": "false",
        "tickers": "false",
        "community_data": "false",
        "developer_data": "false",
    })
    if not data:
        return {"error": "not found"}

    md = data.get("market_data", {})
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "symbol": data.get("symbol"),
        "description": (data.get("description", {}).get("en", "") or "")[:500],
        "current_price": md.get("current_price", {}).get("usd", 0),
        "market_cap": md.get("market_cap", {}).get("usd", 0),
        "market_cap_rank": md.get("market_cap_rank"),
        "total_volume": md.get("total_volume", {}).get("usd", 0),
        "high_24h": md.get("high_24h", {}).get("usd", 0),
        "low_24h": md.get("low_24h", {}).get("usd", 0),
        "price_change_24h": md.get("price_change_24h"),
        "price_change_percentage_24h": md.get("price_change_percentage_24h"),
        "price_change_percentage_7d": md.get("price_change_percentage_7d"),
        "price_change_percentage_30d": md.get("price_change_percentage_30d"),
        "price_change_percentage_1y": md.get("price_change_percentage_1y"),
        "ath": md.get("ath", {}).get("usd"),
        "ath_change_percentage": md.get("ath_change_percentage", {}).get("usd"),
        "atl": md.get("atl", {}).get("usd"),
        "circulating_supply": md.get("circulating_supply"),
        "total_supply": md.get("total_supply"),
        "max_supply": md.get("max_supply"),
    }


@router.get("/trending")
async def trending():
    """Get trending coins."""
    data = await _fetch_coingecko("/search/trending")
    if not data or "coins" not in data:
        return {"trending": []}

    trending = []
    for item in data["coins"][:10]:
        coin = item.get("item", {})
        trending.append({
            "id": coin.get("id"),
            "name": coin.get("name"),
            "symbol": coin.get("symbol"),
            "market_cap_rank": coin.get("market_cap_rank"),
            "price_btc": coin.get("price_btc"),
            "score": coin.get("score"),
        })
    return {"trending": trending, "source": "coingecko"}
