"""DeFi Llama TVL monitoring.

Fetches protocol-level TVL (Total Value Locked) data from the free DeFi Llama
API and exposes growth metrics used by the crypto discovery algorithm.

Data returned per protocol symbol:
  - tvl: current total value locked (USD)
  - tvl_change_1d / 7d / 1m: % change over each window
  - category: DeFi / DEX / Lending / CEX / etc.
  - chains: chains the protocol operates on
  - mcap_tvl_ratio: market cap / TVL (valuation vs. capital locked)

The protocol list is cached in memory for 1 hour — DeFi Llama updates TVL
roughly hourly and the free API should not be hammered.
"""
import logging
import time
from typing import Optional

logger = logging.getLogger("quantive.defi_tvl")

_CACHE: dict | None = None
_CACHE_AT: float = 0.0
_CACHE_TTL = 3600  # 1 hour

LLAMA_PROTOCOLS_URL = "https://api.llama.fi/protocols"


def _fetch_protocols() -> list[dict] | None:
    try:
        import json
        import urllib.request

        req = urllib.request.Request(LLAMA_PROTOCOLS_URL, headers={"User-Agent": "Quantive/1.0"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.warning("DeFi Llama fetch failed: %s", e)
        return None


def _get_protocol_data() -> dict[str, dict]:
    """Symbol -> TVL metrics. Cached 1h. Best symbol wins on duplicates."""
    global _CACHE, _CACHE_AT

    now = time.time()
    if _CACHE is not None and now - _CACHE_AT < _CACHE_TTL:
        return _CACHE

    protocols = _fetch_protocols()
    if not protocols:
        # Stale cache is better than nothing
        if _CACHE is not None:
            return _CACHE
        _CACHE = {}
        _CACHE_AT = now
        return _CACHE

    by_symbol: dict[str, dict] = {}
    for p in protocols:
        try:
            symbol = (p.get("symbol") or "").upper()
            tvl = p.get("tvl")
            if not symbol or not tvl or tvl <= 0:
                continue
            entry = {
                "tvl": float(tvl),
                "tvl_change_1d": _safe_float(p.get("change_1d")),
                "tvl_change_7d": _safe_float(p.get("change_7d")),
                "tvl_change_1m": _safe_float(p.get("change_1m")),
                "category": p.get("category"),
                "chains": (p.get("chains") or [])[:6],
                "mcap": _safe_float(p.get("mcap")),
                "protocol_name": p.get("name"),
            }
            mcap = entry["mcap"]
            if mcap and mcap > 0:
                entry["mcap_tvl_ratio"] = round(mcap / entry["tvl"], 3)

            # Keep the largest-TVL protocol per symbol (e.g. BNB chain vs token)
            existing = by_symbol.get(symbol)
            if not existing or entry["tvl"] > existing["tvl"]:
                by_symbol[symbol] = entry
        except Exception:
            continue

    _CACHE = by_symbol
    _CACHE_AT = time.time()
    logger.info("DeFi Llama: %d protocol symbols cached (TVL > 0)", len(by_symbol))
    return _CACHE


def _safe_float(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def get_tvl_for_symbol(symbol: str) -> dict | None:
    """TVL metrics for one symbol (e.g. 'UNI', 'AAVE', 'CRV')."""
    data = _get_protocol_data()
    return data.get((symbol or "").upper())


def get_tvl_growth_score(symbol: str) -> dict:
    """Score protocol growth for discovery: 0-20 points from TVL trends.

    Scoring:
      - 7-day growth (0-12): sustained capital inflow is the strongest signal
      - 1-day growth (0-4): fresh momentum
      - 1-month growth (0-4): structural trend

    Growth thresholds (7d): >+10% = 12, >+5% = 9, >+2% = 6, >0% = 3.
    """
    entry = get_tvl_for_symbol(symbol)
    if not entry:
        return {"score": 0, "has_data": False}

    score = 0
    signals = []

    c7 = entry.get("tvl_change_7d")
    if c7 is not None:
        if c7 > 10:
            s = 12
        elif c7 > 5:
            s = 9
        elif c7 > 2:
            s = 6
        elif c7 > 0:
            s = 3
        else:
            s = 0
        score += s
        if s:
            signals.append(f"TVL +{c7:.1f}% 7d (+{s})")

    c1 = entry.get("tvl_change_1d")
    if c1 is not None and c1 > 0:
        s = min(4, max(1, int(c1 / 2)))
        score += s
        signals.append(f"TVL +{c1:.1f}% 1d (+{s})")

    c30 = entry.get("tvl_change_1m")
    if c30 is not None and c30 > 5:
        s = min(4, int(c30 / 10) + 1)
        score += s
        signals.append(f"TVL +{c30:.1f}% 1m (+{s})")

    return {
        "score": min(20, score),
        "has_data": True,
        "signals": signals,
        "tvl": entry.get("tvl"),
        "tvl_change_7d": c7,
        "tvl_change_1d": c1,
        "tvl_change_1m": c30,
        "category": entry.get("category"),
        "chains": entry.get("chains", []),
        "mcap_tvl_ratio": entry.get("mcap_tvl_ratio"),
        "protocol_name": entry.get("protocol_name"),
    }


def enrich_crypto_assets(assets: dict[str, dict]) -> int:
    """Attach TVL metrics to crypto assets in the store. Returns enriched count."""
    data = _get_protocol_data()
    if not data:
        return 0

    n = 0
    for key, asset in assets.items():
        if not key.startswith("CRYPTO:"):
            continue
        sym = key.split(":", 1)[1]
        entry = data.get(sym)
        if entry:
            asset["tvl"] = entry["tvl"]
            asset["tvl_change_7d"] = entry.get("tvl_change_7d")
            asset["tvl_change_1d"] = entry.get("tvl_change_1d")
            asset["tvl_change_1m"] = entry.get("tvl_change_1m")
            asset["tvl_category"] = entry.get("category")
            asset["tvl_chains"] = entry.get("chains", [])
            asset["mcap_tvl_ratio"] = entry.get("mcap_tvl_ratio")
            n += 1
    return n


def get_top_tvl_movers(limit: int = 10, min_tvl: float = 50e6, category: str | None = None) -> list[dict]:
    """Protocols with fastest 7d TVL growth above a TVL floor."""
    data = _get_protocol_data()
    movers = []
    for sym, entry in data.items():
        if (entry.get("tvl") or 0) < min_tvl:
            continue
        if category and (entry.get("category") or "").lower() != category.lower():
            continue
        c7 = entry.get("tvl_change_7d")
        if c7 is None or c7 <= 0:
            continue
        movers.append({
            "symbol": sym,
            "protocol_name": entry.get("protocol_name"),
            "tvl": entry["tvl"],
            "tvl_change_7d": round(c7, 2),
            "tvl_change_1d": entry.get("tvl_change_1d"),
            "category": entry.get("category"),
            "chains": entry.get("chains", []),
        })
    movers.sort(key=lambda m: m["tvl_change_7d"], reverse=True)
    return movers[:limit]
