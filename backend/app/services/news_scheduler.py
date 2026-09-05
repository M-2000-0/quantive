"""Hourly news ingestion scheduler.

Background asyncio task that runs the news ingestion cycle every hour so
per-asset sentiment stays fresh without anyone clicking refresh.

Design:
- Default cadence: 60 minutes (NEWS_INGEST_INTERVAL_MINUTES env var to change;
  set to 0 to disable entirely).
- Also runs one cycle shortly after startup (2 min delay) so a fresh boot
  doesn't serve hour-old sentiment.
- Idempotent: run_ingestion_cycle dedupes by ingestion_hash, so a cycle that
  finds no new articles simply no-ops.
- Error-safe: a failing cycle logs and retries on the next tick; it never
  crashes the loop or the server.
- Skew protection: a single-flight lock prevents overlapping cycles if one
  run takes longer than the interval.
- Backoff: if a cycle errors, wait 5 minutes before retrying rather than
  hammering upstream feeds.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger("quantive.news_scheduler")

_bg_task = None

DEFAULT_INTERVAL_MINUTES = 60
STARTUP_DELAY_SECONDS = 120
ERROR_RETRY_SECONDS = 300


def _interval_seconds() -> int:
    try:
        minutes = int(os.environ.get("NEWS_INGEST_INTERVAL_MINUTES", DEFAULT_INTERVAL_MINUTES))
    except ValueError:
        minutes = DEFAULT_INTERVAL_MINUTES
    return max(0, minutes * 60)


async def _run_cycle() -> dict:
    """One ingestion cycle. Returns stats summary."""
    from app.database import SessionLocal
    from app.services.news_ingestion import run_ingestion_cycle, backfill_sentiment

    db = SessionLocal()
    try:
        results = run_ingestion_cycle(db)
        new_total = sum(r.get("new", 0) for r in results if isinstance(r, dict))
        errors = [r.get("source") for r in results if isinstance(r, dict) and r.get("error")]

        # Score any articles that landed without a sentiment score
        scored = backfill_sentiment(db, limit=500)

        return {
            "at": datetime.now(timezone.utc).isoformat(),
            "sources": len(results),
            "new_articles": new_total,
            "rescored": scored,
            "errors": errors,
        }
    finally:
        db.close()


async def _hourly_loop():
    interval = _interval_seconds()
    if interval == 0:
        logger.info("News scheduler disabled (NEWS_INGEST_INTERVAL_MINUTES=0)")
        return

    logger.info("Hourly news ingestion scheduled: first run in %ss, then every %ss",
                STARTUP_DELAY_SECONDS, interval)

    # Startup catch-up run
    await asyncio.sleep(STARTUP_DELAY_SECONDS)
    await _attempt_cycle()

    # Steady-state loop
    while True:
        await asyncio.sleep(interval)
        await _attempt_cycle()


async def _attempt_cycle():
    """Run one cycle with single-flight protection and error backoff."""
    if getattr(_hourly_loop, "_running", False):
        logger.warning("News ingestion cycle still running; skipping this tick")
        return

    _hourly_loop._running = True
    try:
        stats = await asyncio.wait_for(_run_cycle(), timeout=480)
        if stats.get("new_articles") or stats.get("rescored"):
            logger.info("News ingest: %s new articles, %s rescored from %s sources%s",
                        stats.get("new_articles", 0), stats.get("rescored", 0),
                        stats.get("sources", 0),
                        f" (errors: {stats.get('errors')})" if stats.get("errors") else "")
        else:
            logger.info("News ingest: no new articles (%s sources checked)", stats.get("sources", 0))
    except asyncio.TimeoutError:
        logger.error("News ingestion cycle timed out after 480s; will retry next tick")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error("News ingestion cycle failed: %s — retrying in %ss", e, ERROR_RETRY_SECONDS)
        await asyncio.sleep(ERROR_RETRY_SECONDS)
    finally:
        _hourly_loop._running = False


async def start_news_ingestion_scheduler():
    global _bg_task
    if _bg_task is not None:
        return
    try:
        loop = asyncio.get_running_loop()
        _bg_task = loop.create_task(_hourly_loop())
        logger.info("News ingestion scheduler started")
    except RuntimeError:
        logger.warning("No running event loop; news ingestion scheduler not started")


async def stop_news_ingestion_scheduler():
    global _bg_task
    if _bg_task is not None:
        _bg_task.cancel()
        _bg_task = None


async def run_cycle_now() -> dict:
    """Manual trigger for tests/admin — runs one cycle immediately."""
    return await _run_cycle()
