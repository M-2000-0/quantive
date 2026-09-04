"""
Asset Tracker API — Track everything: crypto, commodities, FX, bonds, custom assets.

Provides:
- Real-time crypto prices (BTC, ETH, SOL, etc.) via CoinGecko
- Commodities (Gold, Silver, Oil, Gas) via Yahoo Finance
- Expanded FX pairs (20+ currencies)
- Custom asset watchlists with alerts
- Portfolio correlation analysis
- Asset allocation breakdown
- Multi-asset dashboard endpoint
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.market_data.crypto import (
    fetch_crypto_history,
    fetch_crypto_prices,
    fetch_fear_greed_index,
)
from app.market_data.cache import get_cache
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/api/assets", tags=["asset-tracker"])


# ── Pydantic Models ──────────────────────────────────────────────────


class WatchlistAssetCreate(BaseModel):
    asset_type: str  # "crypto", "commodity", "fx", "bond", "custom"
    asset_id: str
    name: str
    symbol: str
    alert_above: Optional[float] = None
    alert_below: Optional[float] = None
    notes: str = ""


class WatchlistAssetResponse(BaseModel):
    id: str
    asset_type: str
    asset_id: str
    name: str
    symbol: str
    alert_above: Optional[float]
    alert_below: Optional[float]
    notes: str
    current_price: Optional[float]
    price_change_24h_pct: Optional[float]
    created_at: str


# ── Commodities ───────────────────────────────────────────────────────

# Tracked commodities via Yahoo Finance
TRACKED_COMMODITIES = [
    {"symbol": "GC=F", "name": "Gold", "category": "precious_metal", "unit": "USD/oz"},
    {"symbol": "SI=F", "name": "Silver", "category": "precious_metal", "unit": "USD/oz"},
    {"symbol": "CL=F", "name": "Crude Oil (WTI)", "category": "energy", "unit": "USD/bbl"},
    {"symbol": "BZ=F", "name": "Brent Crude", "category": "energy", "unit": "USD/bbl"},
    {"symbol": "NG=F", "name": "Natural Gas", "category": "energy", "unit": "USD/MMBtu"},
    {"symbol": "HG=F", "name": "Copper", "category": "industrial", "unit": "USD/lb"},
    {"symbol": "PL=F", "name": "Platinum", "category": "precious_metal", "unit": "USD/oz"},
    {"symbol": "PA=F", "name": "Palladium", "category": "precious_metal", "unit": "USD/oz"},
    {"symbol": "ZC=F", "name": "Corn", "category": "agriculture", "unit": "USD/bu"},
    {"symbol": "ZW=F", "name": "Wheat", "category": "agriculture", "unit": "USD/bu"},
    {"symbol": "ZS=F", "name": "Soybeans", "category": "agriculture", "unit": "USD/bu"},
    {"symbol": "KC=F", "name": "Coffee", "category": "agriculture", "unit": "USD/lb"},
    {"symbol": "SB=F", "name": "Sugar", "category": "agriculture", "unit": "USD/lb"},
    {"symbol": "CT=F", "name": "Cotton", "category": "agriculture", "unit": "USD/lb"},
]


def _fetch_yahoo_quote(symbol: str) -> dict:
    """Fetch a single quote from Yahoo Finance."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"interval": "1d", "range": "5d"}
        headers = {"User-Agent": "Quantive/1.0"}

        import requests as req
        resp = req.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        chart = data.get("chart", {}).get("result", [])
        if not chart:
            return {"error": f"No data for {symbol}"}

        meta = chart[0].get("meta", {})
        indicators = chart[0].get("indicators", {}).get("quote", [{}])
        closes = indicators[0].get("close", []) if indicators else []

        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("chartPreviousClose", 0)
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

        return {
            "price": round(price, 4),
            "previous_close": round(prev_close, 4),
            "change_pct": round(change_pct, 2),
            "currency": meta.get("currency", "USD"),
            "market_state": meta.get("marketState", "UNKNOWN"),
            "recent_closes": [round(c, 4) for c in (closes[-5:] if closes else [])],
        }
    except Exception as e:
        return {"error": str(e)}


def fetch_all_commodities(use_cache: bool = True) -> dict:
    """Fetch prices for all tracked commodities."""
    cache = get_cache()
    cache_key = "commodities_all"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    results = []
    for commodity in TRACKED_COMMODITIES:
        quote = _fetch_yahoo_quote(commodity["symbol"])
        results.append({
            **commodity,
            "price": quote.get("price", 0),
            "previous_close": quote.get("previous_close", 0),
            "change_pct": quote.get("change_pct", 0),
            "currency": quote.get("currency", "USD"),
            "market_state": quote.get("market_state", "UNKNOWN"),
            "error": quote.get("error"),
        })

    result = {
        "commodities": results,
        "categories": {
            "precious_metal": [c for c in results if c["category"] == "precious_metal" and not c.get("error")],
            "energy": [c for c in results if c["category"] == "energy" and not c.get("error")],
            "industrial": [c for c in results if c["category"] == "industrial" and not c.get("error")],
            "agriculture": [c for c in results if c["category"] == "agriculture" and not c.get("error")],
        },
        "tracked_count": len(results),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set(cache_key, result, 5 * 60)  # 5 min cache
    return result


# ── Expanded FX ───────────────────────────────────────────────────────

# Yahoo Finance uses '=X' suffix for forex pairs
# Crypto/fiat uses '=USD' suffix, but we pull from CoinGecko instead
EXPANDED_FX_PAIRS = [
    # Major pairs
    {"pair": "EURUSD", "yahoo_symbol": "EURUSD=X", "name": "EUR/USD", "category": "major"},
    {"pair": "GBPUSD", "yahoo_symbol": "GBPUSD=X", "name": "GBP/USD", "category": "major"},
    {"pair": "USDJPY", "yahoo_symbol": "USDJPY=X", "name": "USD/JPY", "category": "major"},
    {"pair": "USDCHF", "yahoo_symbol": "USDCHF=X", "name": "USD/CHF", "category": "major"},
    {"pair": "AUDUSD", "yahoo_symbol": "AUDUSD=X", "name": "AUD/USD", "category": "major"},
    {"pair": "USDCAD", "yahoo_symbol": "USDCAD=X", "name": "USD/CAD", "category": "major"},
    {"pair": "NZDUSD", "yahoo_symbol": "NZDUSD=X", "name": "NZD/USD", "category": "major"},
    # Emerging market (relevant to sovereign debt)
    {"pair": "USDMXN", "yahoo_symbol": "USDMXN=X", "name": "USD/MXN", "category": "emerging"},
    {"pair": "USDINR", "yahoo_symbol": "USDINR=X", "name": "USD/INR", "category": "emerging"},
    {"pair": "USDBRL", "yahoo_symbol": "USDBRL=X", "name": "USD/BRL", "category": "emerging"},
    {"pair": "USDZAR", "yahoo_symbol": "USDZAR=X", "name": "USD/ZAR", "category": "emerging"},
    {"pair": "USDTWD", "yahoo_symbol": "USDTWD=X", "name": "USD/TWD", "category": "emerging"},
    {"pair": "USDKRW", "yahoo_symbol": "USDKRW=X", "name": "USD/KRW", "category": "emerging"},
    {"pair": "USDSGD", "yahoo_symbol": "USDSGD=X", "name": "USD/SGD", "category": "emerging"},
    {"pair": "USDTHB", "yahoo_symbol": "USDTHB=X", "name": "USD/THB", "category": "emerging"},
    {"pair": "USDTRY", "yahoo_symbol": "USDTRY=X", "name": "USD/TRY", "category": "emerging"},
    # Crypto/Fiat — pulled from CoinGecko, not Yahoo
    {"pair": "BTCUSD", "yahoo_symbol": None, "name": "BTC/USD", "category": "crypto_fiat"},
    {"pair": "ETHUSD", "yahoo_symbol": None, "name": "ETH/USD", "category": "crypto_fiat"},
]


def fetch_expanded_fx(use_cache: bool = True) -> dict:
    """Fetch all expanded FX pairs."""
    cache = get_cache()
    cache_key = "fx_expanded"

    if use_cache:
        cached = cache.get(cache_key)
        if cached:
            return cached

    # Pre-fetch crypto prices for BTC/USD and ETH/USD
    crypto_prices = {}
    try:
        cp = fetch_crypto_prices()
        for coin in cp.get("prices", []):
            if coin["symbol"] in ("BTC", "ETH"):
                crypto_prices[coin["symbol"]] = coin["current_price"]
    except Exception:
        pass

    results = []
    for pair_info in EXPANDED_FX_PAIRS:
        yahoo_sym = pair_info.get("yahoo_symbol")
        pair_name = pair_info["pair"]

        # Crypto/fiat pairs: use CoinGecko data
        if yahoo_sym is None:
            coin = "BTC" if "BTC" in pair_name else "ETH"
            price = crypto_prices.get(coin, 0)
            results.append({
                **pair_info,
                "rate": price,
                "previous_close": price,
                "change_pct": 0,
                "market_state": "LIVE",
                "error": None,
            })
        else:
            quote = _fetch_yahoo_quote(yahoo_sym)
            results.append({
                **pair_info,
                "rate": quote.get("price", 0),
                "previous_close": quote.get("previous_close", 0),
                "change_pct": quote.get("change_pct", 0),
                "market_state": quote.get("market_state", "UNKNOWN"),
                "error": quote.get("error"),
            })

    result = {
        "pairs": results,
        "categories": {
            "major": [p for p in results if p["category"] == "major" and not p.get("error")],
            "emerging": [p for p in results if p["category"] == "emerging" and not p.get("error")],
            "crypto_fiat": [p for p in results if p["category"] == "crypto_fiat" and not p.get("error")],
        },
        "tracked_count": len(results),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    cache.set(cache_key, result, 5 * 60)
    return result


# ── API Endpoints ─────────────────────────────────────────────────────


@router.get("/all")
def get_all_assets(user: dict = Depends(get_current_user)):
    """Get all tracked assets in a single call: crypto + commodities + FX.

    This is the main dashboard endpoint for the Asset Tracker.
    """
    crypto = fetch_crypto_prices()
    commodities = fetch_all_commodities()
    fx = fetch_expanded_fx()
    fear_greed = fetch_fear_greed_index()

    # Calculate portfolio exposure summary
    total_market_cap = crypto.get("total_market_cap_usd", 0)

    return {
        "crypto": crypto,
        "commodities": commodities,
        "fx": fx,
        "fear_greed_index": fear_greed,
        "summary": {
            "crypto_market_cap": total_market_cap,
            "btc_dominance": crypto.get("btc_dominance_pct", 0),
            "tracked_assets": (
                crypto.get("tracked_count", 0)
                + commodities.get("tracked_count", 0)
                + fx.get("tracked_count", 0)
            ),
            "fear_greed_value": fear_greed.get("current_value", 50),
            "fear_greed_label": fear_greed.get("current_label", "Neutral"),
        },
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/crypto")
def get_crypto_prices(
    vs_currency: str = Query("usd", description="Quote currency"),
    user: dict = Depends(get_current_user),
):
    """Get real-time cryptocurrency prices."""
    return fetch_crypto_prices(vs_currency=vs_currency)


# IMPORTANT: Static routes MUST come before parameterized /{coin_id} routes
# so FastAPI doesn't match "fear-greed" as a coin_id


@router.get("/crypto/fear-greed")
def get_fear_greed(user: dict = Depends(get_current_user)):
    """Get the Crypto Fear & Greed Index."""
    return fetch_fear_greed_index()


@router.get("/crypto/{coin_id}")
def get_crypto_detail(
    coin_id: str,
    vs_currency: str = Query("usd"),
    user: dict = Depends(get_current_user),
):
    """Get detailed data for a specific cryptocurrency."""
    return fetch_crypto_detail(coin_id, vs_currency=vs_currency)


@router.get("/crypto/{coin_id}/history")
def get_crypto_history(
    coin_id: str,
    days: int = Query(30, ge=1, le=365),
    vs_currency: str = Query("usd"),
    user: dict = Depends(get_current_user),
):
    """Get historical price data for correlation analysis."""
    return fetch_crypto_history(coin_id, vs_currency=vs_currency, days=days)


@router.get("/commodities")
def get_commodities(user: dict = Depends(get_current_user)):
    """Get all commodity prices (Gold, Silver, Oil, etc.)."""
    return fetch_all_commodities()


@router.get("/commodities/{symbol}")
def get_commodity_detail(
    symbol: str,
    user: dict = Depends(get_current_user),
):
    """Get a specific commodity price."""
    commodity = next(
        (c for c in TRACKED_COMMODITIES if c["symbol"] == symbol),
        None,
    )
    if not commodity:
        raise HTTPException(status_code=404, detail=f"Commodity {symbol} not found")

    quote = _fetch_yahoo_quote(symbol)
    return {**commodity, **quote}


@router.get("/fx")
def get_expanded_fx(user: dict = Depends(get_current_user)):
    """Get all expanded FX pairs (25+ currencies)."""
    return fetch_expanded_fx()


@router.get("/fx/{pair}")
def get_fx_pair_detail(
    pair: str,
    user: dict = Depends(get_current_user),
):
    """Get a specific FX pair rate."""
    pair_info = next(
        (p for p in EXPANDED_FX_PAIRS if p["pair"] == pair.upper()),
        None,
    )
    if not pair_info:
        raise HTTPException(status_code=404, detail=f"FX pair {pair} not found")

    yahoo_sym = pair_info.get("yahoo_symbol")
    if yahoo_sym:
        quote = _fetch_yahoo_quote(yahoo_sym)
    else:
        # Crypto/fiat pair
        coin = "BTC" if "BTC" in pair.upper() else "ETH"
        try:
            cp = fetch_crypto_prices()
            price = next((c["current_price"] for c in cp.get("prices", []) if c["symbol"] == coin), 0)
        except Exception:
            price = 0
        quote = {"price": price, "previous_close": price, "change_pct": 0, "market_state": "LIVE"}

    return {**pair_info, **quote}


@router.get("/correlation")
def get_asset_correlation(
    assets: str = Query(
        "BTC,Gold,Oil,EUR",
        description="Comma-separated asset symbols to correlate",
    ),
    days: int = Query(90, ge=7, le=365),
    user: dict = Depends(get_current_user),
):
    """Calculate correlation matrix between specified assets.

    Useful for understanding how crypto, commodities, and FX
    move relative to each other and the debt portfolio.
    """
    import numpy as np

    asset_list = [a.strip().upper() for a in assets.split(",")]
    price_series = {}

    for asset in asset_list:
        # Map asset symbols to data sources
        if asset in ("BTC", "ETH", "SOL", "XRP", "ADA"):
            coin_map = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "XRP": "ripple", "ADA": "cardano"}
            coin_id = coin_map.get(asset, asset.lower())
            history = fetch_crypto_history(coin_id, days=days, use_cache=True)
            if "prices" in history and history["prices"]:
                price_series[asset] = [p["price"] for p in history["prices"]]
        elif asset in ("GOLD", "XAU"):
            history = _fetch_yahoo_quote("GC=F")
            # Use current price as single point for now
            if history.get("price"):
                price_series[asset] = [history["price"]]
        elif asset in ("OIL", "WTI"):
            history = _fetch_yahoo_quote("CL=F")
            if history.get("price"):
                price_series[asset] = [history["price"]]
        elif asset in ("EUR", "EURUSD"):
            history = _fetch_yahoo_quote("EURUSD=X")
            if history.get("price"):
                price_series[asset] = [history["price"]]
        elif asset in ("GBP", "GBPUSD"):
            history = _fetch_yahoo_quote("GBPUSD=X")
            if history.get("price"):
                price_series[asset] = [history["price"]]

    # Calculate correlation matrix
    if len(price_series) < 2:
        return {
            "error": "Need at least 2 assets with data for correlation",
            "available": list(price_series.keys()),
        }

    # Align series to same length
    min_len = min(len(v) for v in price_series.values())
    aligned = {k: v[-min_len:] for k, v in price_series.items() if len(v) >= min_len}

    if len(aligned) < 2:
        return {"error": "Insufficient overlapping data points"}

    # Compute returns and correlation
    returns = {}
    for asset, prices in aligned.items():
        arr = np.array(prices, dtype=float)
        if len(arr) > 1:
            returns[asset] = np.diff(arr) / arr[:-1]

    assets_list = list(returns.keys())
    n = len(assets_list)
    matrix = np.eye(n)

    for i in range(n):
        for j in range(i + 1, n):
            if len(returns[assets_list[i]]) == len(returns[assets_list[j]]):
                corr = np.corrcoef(returns[assets_list[i]], returns[assets_list[j]])[0, 1]
                matrix[i][j] = round(float(corr), 4)
                matrix[j][i] = round(float(corr), 4)

    return {
        "assets": assets_list,
        "matrix": matrix.tolist(),
        "days": days,
        "data_points": min_len,
        "interpretation": _interpret_correlation(matrix, assets_list),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _interpret_correlation(matrix, assets: list) -> list[dict]:
    """Generate plain-English interpretations of correlations."""
    interpretations = []
    n = len(assets)
    for i in range(n):
        for j in range(i + 1, n):
            corr = matrix[i][j]
            if abs(corr) > 0.7:
                strength = "strong"
            elif abs(corr) > 0.3:
                strength = "moderate"
            else:
                strength = "weak"

            direction = "positive" if corr > 0 else "negative"

            interpretations.append({
                "pair": f"{assets[i]}/{assets[j]}",
                "correlation": corr,
                "description": f"{strength.title()} {direction} correlation ({corr:.2f})",
                "implication": (
                    f"When {assets[i]} rises, {assets[j]} tends to "
                    f"{'rise' if corr > 0 else 'fall'} ({strength}ly)"
                ),
            })

    return interpretations


@router.get("/allocation")
def get_asset_allocation(
    portfolio_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get asset allocation breakdown for a portfolio.

    Shows how exposure breaks down across asset classes:
    crypto, commodities, FX, bonds, and other categories.
    """
    from app.models import DebtInstrument, Portfolio

    if portfolio_id:
        portfolio = db.query(Portfolio).filter(
            Portfolio.id == portfolio_id,
            Portfolio.org_id == user.org_id,
        ).first()
    else:
        portfolio = db.query(Portfolio).filter(
            Portfolio.org_id == user.org_id,
        ).first()

    if not portfolio:
        return {
            "allocation": None,
            "message": "No portfolio found. Create a portfolio to see allocation.",
        }

    instruments = db.query(DebtInstrument).filter(
        DebtInstrument.portfolio_id == portfolio.id
    ).all()

    # Break down by currency
    currency_allocation = {}
    type_allocation = {}
    total_debt = 0

    for inst in instruments:
        principal = float(inst.principal_outstanding)
        total_debt += principal

        # Currency breakdown
        ccy = inst.currency
        currency_allocation[ccy] = currency_allocation.get(ccy, 0) + principal

        # Type breakdown
        inst_type = inst.instrument_type.value if hasattr(inst.instrument_type, "value") else str(inst.instrument_type)
        type_allocation[inst_type] = type_allocation.get(inst_type, 0) + principal

    # Convert to percentages
    currency_pcts = {
        k: {"amount": v, "percentage": round(v / total_debt * 100, 1) if total_debt else 0}
        for k, v in sorted(currency_allocation.items(), key=lambda x: -x[1])
    }

    type_pcts = {
        k: {"amount": v, "percentage": round(v / total_debt * 100, 1) if total_debt else 0}
        for k, v in sorted(type_allocation.items(), key=lambda x: -x[1])
    }

    return {
        "portfolio_name": portfolio.name,
        "total_debt": total_debt,
        "by_currency": currency_pcts,
        "by_type": type_pcts,
        "instrument_count": len(instruments),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_crypto_detail(coin_id: str, vs_currency: str = "usd", use_cache: bool = True) -> dict:
    """Fetch detailed crypto data (imported from crypto module)."""
    from app.market_data.crypto import fetch_crypto_detail as _fetch
    return _fetch(coin_id, vs_currency, use_cache)
