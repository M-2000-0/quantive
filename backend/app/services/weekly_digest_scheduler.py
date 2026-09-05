"""Weekly digest scheduler.

Background asyncio task that sends the weekly digest email every Monday at
08:00 UTC to all opted-in users. Idempotent per ISO week via the send marker,
so server restarts don't cause duplicate sends.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("quantive.weekly_scheduler")

_bg_task = None
SEND_WEEKDAY = 0  # Monday
SEND_HOUR_UTC = 8


def _next_send_time() -> datetime:
    """Next Monday 08:00 UTC."""
    now = datetime.now(timezone.utc)
    days_ahead = (SEND_WEEKDAY - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(
        hour=SEND_HOUR_UTC, minute=0, second=0, microsecond=0
    )
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def _week_key() -> str:
    year, week, _ = datetime.now(timezone.utc).isocalendar()
    return f"{year}-W{week:02d}"


async def _weekly_loop():
    sent_weeks: set[str] = set()
    while True:
        try:
            now = datetime.now(timezone.utc)
            nxt = _next_send_time()
            wait = max(60, (nxt - now).total_seconds())
            logger.info("Weekly digest scheduled for %s (sleeping %.0f min)", nxt.isoformat(), wait / 60)
            await asyncio.sleep(wait)

            week = _week_key()
            if week in sent_weeks:
                continue

            from app.services.weekly_digest_email import send_weekly_digest

            result = await send_weekly_digest()
            sent_weeks.add(week)
            logger.info("Weekly digest sent: %s", result)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Weekly digest loop error: %s", e)
            await asyncio.sleep(3600)  # retry in an hour


async def start_weekly_digest_scheduler():
    global _bg_task
    if _bg_task is None:
        try:
            loop = asyncio.get_running_loop()
            _bg_task = loop.create_task(_weekly_loop())
            logger.info("Weekly digest scheduler started")
        except RuntimeError:
            logger.warning("No running event loop; weekly digest scheduler not started")


async def stop_weekly_digest_scheduler():
    global _bg_task
    if _bg_task is not None:
        _bg_task.cancel()
        _bg_task = None
