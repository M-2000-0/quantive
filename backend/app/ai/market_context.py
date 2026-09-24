"""Live market data injection for AI chat answers.

Detects market/stock questions and attaches real-time quotes, indices,
yield-curve and FX data to the AI response so the assistant can answer
"What is the price of AAPL?" with actual numbers instead of textbook text.
"""

import re
from typing import Any, Dict, List, Optional

# ── Question classifiers ──────────────────────────────────────────────

MARKET_KEYWORDS = (
    "price", "quote", "stock", "share", "market", "index", "indices",
    "s&p", "nasdaq", "dow", "russell", "yield", "yields", "treasury",
    "bond market", "rate", "rates", "fed", "fx", "forex", "currency",
    "bitcoin", "btc", "ethereum", "eth", "crypto", "gold", "oil",
    "buy", "sell", "invest", "trading", "today", "now", "current",
    "performing", "doing", "how is the market", "how's the market",
)

TICKER_RE = re.compile(r"\b([A-Z]{1,5})\b")
KNOWN_SYMBOLS = {
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "NVDA", "NFLX",
    "AMD", "INTC", "JPM", "BAC", "GS", "V", "MA", "WMT", "KO", "PEP", "DIS",
    "SPY", "QQQ", "IWM", "DIA", "VTI", "VOO", "BTC-USD", "ETH-USD", "GLD", "USO",
}
CRYPTO_WORDS = {"bitcoin", "btc", "ethereum", "eth", "solana", "sol", "dogecoin", "doge", "xrp", "ripple"}
CRYPTO_MAP = {
    "bitcoin": "BTC-USD", "btc": "BTC-USD", "ethereum": "ETH-USD", "eth": "ETH-USD",
    "solana": "SOL-USD", "sol": "SOL-USD", "dogecoin": "DOGE-USD", "doge": "DOGE-USD",
    "xrp": "XRP-USD", "ripple": "XRP-USD",
}

def is_market_question(q: str) -> bool:
    ql = q.lower()
    if any(k in ql for k in MARKET_KEYWORDS):
        return True
    return bool(_extract_symbols(q))

def _extract_symbols(q: str) -> List[str]:
    """Extract requested symbols from the question text."""
    out: List[str] = []
    ql = q.lower()
    # Crypto names
    for w, sym in CRYPTO_MAP.items():
        if re.search(rf"\b{re.escape(w)}\b", ql) and sym not in out:
            out.append(sym)
    # Uppercase tickers the user typed (e.g. "AAPL", "TSLA")
    for m in TICKER_RE.findall(q):
        if m in KNOWN_SYMBOLS and m not in out:
            out.append(m)
    return out[:6]


# ── Data fetchers (all wrapped — never break the chat) ────────────────

def _fetch_quotes(symbols: List[str]) -> List[Dict[str, Any]]:
    if not symbols:
        return []
    try:
        from app.api.live_prices import get_batch_prices
        resp = get_batch_prices(symbols=",".join(symbols))
        return resp.get("prices", []) if isinstance(resp, dict) else []
    except Exception:
        return []

def _fetch_indices() -> Dict[str, Any]:
    try:
        from app.api.live_prices import get_market_snapshot
        resp = get_market_snapshot()
        return resp.get("indices", {}) if isinstance(resp, dict) else {}
    except Exception:
        return {}

def _fetch_rates() -> Dict[str, Any]:
    try:
        from app.market_data.interest_rates import fetch_all_benchmark_rates
        data = fetch_all_benchmark_rates() or {}
        return (data.get("rates") or {}) if isinstance(data, dict) else {}
    except Exception:
        return {}

def _fetch_yield_curve() -> Dict[str, Any]:
    try:
        from app.market_data.yield_curve import fetch_treasury_yield_curve
        data = fetch_treasury_yield_curve(use_cache=True) or {}
        if isinstance(data, dict):
            out = {}
            for m in data.get("maturities", []):
                out[m.get("label", "?")] = m.get("rate_pct")
            return out
        return {}
    except Exception:
        return {}

def _fetch_fx() -> Dict[str, Any]:
    try:
        from app.market_data.fx_rates import fetch_all_key_rates
        data = fetch_all_key_rates() or {}
        return (data.get("rates") or {}) if isinstance(data, dict) else {}
    except Exception:
        return {}


# ── Context builder ───────────────────────────────────────────────────

def build_market_context(question: str) -> Optional[Dict[str, Any]]:
    """Return live market context relevant to the question, or None."""
    if not is_market_question(question):
        return None

    symbols = _extract_symbols(question)
    ql = question.lower()
    ctx: Dict[str, Any] = {"live_data": True}

    # Specific symbols the user asked about take priority
    if symbols:
        quotes = _fetch_quotes(symbols)
        if quotes:
            ctx["quotes"] = quotes

    # Index overview for general market questions
    if any(k in ql for k in ("market", "index", "indices", "s&p", "nasdaq", "doing", "performing", "today")):
        idx = _fetch_indices()
        if idx:
            ctx["indices"] = idx

    # Rates / yield curve
    if any(k in ql for k in ("yield", "treasury", "rate", "rates", "bond", "fed", "curve")):
        curve = _fetch_yield_curve()
        if curve:
            ctx["yield_curve"] = curve
        rates = _fetch_rates()
        if rates:
            # Trim to the headline ones for token economy
            ctx["benchmark_rates"] = {k: v for k, v in list(rates.items())[:6]}

    # FX
    if any(k in ql for k in ("fx", "forex", "currency", "eur", "gbp", "jpy", "dollar", "euro")):
        fx = _fetch_fx()
        if fx:
            ctx["fx_rates"] = {k: v for k, v in list(fx.items())[:8]}

    return ctx if len(ctx) > 1 else None


def format_market_context_text(ctx: Dict[str, Any]) -> str:
    """Render the context dict as readable lines appended to AI answers."""
    parts: List[str] = []

    quotes = ctx.get("quotes") or []
    for q in quotes:
        sym = q.get("symbol", "?")
        price = q.get("price")
        chg = q.get("change_pct") or 0
        arrow = "▲" if chg >= 0 else "▼"
        if price is not None:
            parts.append(f"• {sym}: ${price:,.2f} ({arrow} {abs(chg):.2f}%)")

    indices = ctx.get("indices") or {}
    for sym, info in indices.items():
        if isinstance(info, dict) and info.get("price") is not None:
            chg = info.get("change_pct") or 0
            arrow = "▲" if chg >= 0 else "▼"
            parts.append(f"• {info.get('name', sym)} ({sym}): {info['price']:,.2f} ({arrow} {abs(chg):.2f}%)")

    curve = ctx.get("yield_curve") or {}
    if curve:
        pts = ", ".join(f"{k} {v:.2f}%" for k, v in sorted(curve.items())[:8] if isinstance(v, (int, float)))
        if pts:
            parts.append(f"• Treasury yields: {pts}")

    rates = ctx.get("benchmark_rates") or {}
    if rates:
        rr = []
        for k, v in rates.items():
            val = v.get("rate_pct") if isinstance(v, dict) else v
            if isinstance(val, (int, float)):
                rr.append(f"{k} {val:.2f}%")
        if rr:
            parts.append("• Benchmark rates: " + ", ".join(rr))

    fx = ctx.get("fx_rates") or {}
    if fx:
        ff = []
        for k, v in fx.items():
            val = v.get("rate") if isinstance(v, dict) else v
            if isinstance(val, (int, float)):
                ff.append(f"{k} {val:,.2f}")
        if ff:
            parts.append("• FX: " + ", ".join(ff))

    if not parts:
        return ""
    stamp = "Live market data (fetched just now):\n" if ctx.get("live_data") else "Market data:\n"
    return stamp + "\n".join(parts)
