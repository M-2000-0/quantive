"""Automation scheduler — runs every enabled automation on its interval.

Started from app.main lifespan. Each automation keeps its own next-due
timestamp so intervals are independent (15-min lead scoring vs 6-h dunning).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("quantive.automation.scheduler")

_task: asyncio.Task | None = None


async def start_automation_scheduler() -> None:
    global _task
    if _task and not _task.done():
        return
    _task = asyncio.create_task(_loop())
    logger.info("Automation scheduler started")


async def stop_automation_scheduler() -> None:
    global _task
    if _task:
        _task.cancel()
        _task = None


async def _loop() -> None:
    from app.database import SessionLocal
    from app.services import automation_engine

    # Give the app a moment to finish booting (routes, tables)
    await asyncio.sleep(8)

    next_due: dict[str, datetime] = {}

    def _cycle() -> list[tuple[str, dict]]:
        """One sync scheduling pass; returns automations that ran."""
        ran: list[tuple[str, dict]] = []
        db = SessionLocal()
        try:
            automation_engine.ensure_automations(db)
            from app.models.automation import Automation
            autos = db.query(Automation).filter(Automation.enabled == True).all()  # noqa: E712
            now = datetime.now(timezone.utc)
            for auto in autos:
                due = next_due.get(auto.key)
                if due is None:
                    # First sight: stagger so they don't all fire at once
                    next_due[auto.key] = now + timedelta(seconds=_stagger(auto.key))
                    continue
                if now >= due:
                    ran.append((auto.key, {"interval": auto.interval_minutes}))
            return ran
        finally:
            db.close()

    def _execute(key: str, interval_minutes: int) -> None:
        """Run one automation in its own DB session (worker thread)."""
        from app.database import SessionLocal
        from app.services import automation_engine

        db = SessionLocal()
        try:
            result = automation_engine.run_automation(key, db, trigger="schedule")
            logger.info("Automation %s %s in %dms (%s)",
                        key, result["status"], result["duration_ms"],
                        result["summary"][:80])
        except Exception as e:
            logger.warning("Automation %s crashed: %s", key, e)
        finally:
            db.close()

    while True:
        try:
            # DB pass in a thread so the event loop is never blocked
            due_now = await asyncio.to_thread(_cycle)
            now = datetime.now(timezone.utc)
            for key, meta in due_now:
                # Execute in a thread: keeps the loop (and the server) responsive
                # even when an automation makes outbound HTTP calls.
                await asyncio.to_thread(_execute, key, meta["interval"])
                next_due[key] = datetime.now(timezone.utc) + timedelta(
                    minutes=max(meta["interval"], 1))
        except Exception as e:
            logger.warning("Automation scheduler cycle failed: %s", e)

        await asyncio.sleep(30)  # tick every 30s


_STAGGER_ORDER = ["health_check", "mrr_tracker", "lead_capture_score",
                  "support_triage", "onboarding", "dunning"]


def _stagger(key: str) -> int:
    """Spread first runs: health 0s, mrr 5s, leads 10s, ..."""
    base = _STAGGER_ORDER.index(key) * 7 if key in _STAGGER_ORDER else 20
    return base
