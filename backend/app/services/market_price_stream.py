"""Market price WebSocket streaming.

Broadcasts live price updates for assets in the market monitor store to all
connected WebSocket clients. Runs as a background asyncio task started at app
startup; pushes updates at a fixed interval with rate-limit-friendly cadence.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("quantive.market_stream")

_bg_task: Optional[asyncio.Task] = None
STREAM_INTERVAL_SECONDS = 30  # Yahoo/ CoinGecko friendly cadence

_last_quotes: dict[str, dict] = {}


async def _collect_quotes() -> list[dict]:
    """Collect current quotes from the in-memory market stores (no blocking)."""
    # Ingestion is synchronous + network-bound, so run in a worker thread.
    loop = asyncio.get_running_loop()

    def _pull() -> list[dict]:
        quotes: list[dict] = []
        try:
            from app.api.market_monitor_api import _asset_store
            quotes.extend(list(_asset_store.values()))
        except Exception:
            pass
        try:
            from app.api.global_market_api import _global_asset_store
            quotes.extend(list(_global_asset_store.values()))
        except Exception:
            pass

        # Fallback: if stores are empty (fresh restart), refresh them once
        if not quotes:
            try:
                from app.services.market_monitor_ingest import ingest_all
                ingest_all(max_stocks=30, max_crypto=10)
                from app.api.market_monitor_api import _asset_store
                quotes.extend(list(_asset_store.values()))
            except Exception:
                pass
        return quotes

    return await loop.run_in_executor(None, _pull)


async def _stream_loop():
    """Periodically fetch fresh quotes and broadcast price updates."""
    global _last_quotes
    while True:
        try:
            quotes = await _collect_quotes()

            from app.websocket import get_ws_manager
            manager = get_ws_manager()
            sent = 0
            now_iso = datetime.now(timezone.utc).isoformat()

            updates = []
            for q in quotes:
                symbol = q.get("symbol") or ""
                if not symbol:
                    continue
                price = q.get("price") or q.get("current_price") or q.get("rate")
                if price is None:
                    continue
                prev = _last_quotes.get(symbol, {}).get("price")
                update = {
                    "symbol": symbol,
                    "name": q.get("name", symbol),
                    "asset_class": q.get("asset_class", "unknown"),
                    "price": price,
                    "prev_price": prev,
                    "change_pct": q.get("change_pct", 0),
                    "currency": q.get("currency", "USD"),
                    "source": q.get("source", "cache"),
                    "last_updated": q.get("last_updated", now_iso),
                }
                updates.append(update)

            if updates:
                payload = {
                    "type": "price_update",
                    "timestamp": now_iso,
                    "count": len(updates),
                    "updates": updates,
                }
                # Broadcast to everyone in the "market" room, plus all users
                try:
                    sent = await manager.broadcast_to_room("market", payload)
                except Exception:
                    sent = 0
                if sent == 0:
                    # Room empty (or no join); fall back to broadcast-all
                    try:
                        sent = await manager.broadcast_all({**payload, "type": "market_price_update"})
                    except Exception:
                        sent = 0
                _last_quotes = {u["symbol"]: u for u in updates}
                logger.debug("Broadcast %d price updates to %d clients", len(updates), sent)

        except Exception as e:
            logger.warning("Market stream tick failed: %s", e)

        await asyncio.sleep(STREAM_INTERVAL_SECONDS)


async def start_market_stream():
    """Start the background market price streaming task."""
    global _bg_task
    if _bg_task is None:
        try:
            loop = asyncio.get_running_loop()
            _bg_task = loop.create_task(_stream_loop())
            logger.info("Market price stream started (every %ds)", STREAM_INTERVAL_SECONDS)
        except RuntimeError:
            logger.warning("No running event loop; market stream not started")


async def stop_market_stream():
    """Stop the streaming task (graceful shutdown)."""
    global _bg_task
    if _bg_task is not None:
        _bg_task.cancel()
        _bg_task = None
        logger.info("Market price stream stopped")
