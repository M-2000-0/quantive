"""Job store abstraction for optimization job queue.

Provides a pluggable backend for job persistence and distribution:
- InMemoryJobStore: Default, single-process, non-persistent (current behavior)
- RedisJobStore: Multi-process, persistent, distributed job queue

The store handles:
- Job lifecycle tracking (queued -> running -> completed/failed)
- Job cancellation signaling
- Progress updates
- Job result storage
"""
import json
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger("quantive.job_store")


class JobStore(ABC):
    """Abstract base class for job stores."""

    @abstractmethod
    def enqueue_job(self, job_id: str, job_data: dict) -> None:
        """Add a job to the queue."""
        ...

    @abstractmethod
    def dequeue_job(self, timeout: float = 1.0) -> Optional[dict]:
        """Get the next job from the queue. Returns None on timeout."""
        ...

    @abstractmethod
    def get_job_status(self, job_id: str) -> Optional[dict]:
        """Get current job status and progress."""
        ...

    @abstractmethod
    def update_job_progress(self, job_id: str, status: str, progress: float, **kwargs) -> None:
        """Update job progress."""
        ...

    @abstractmethod
    def complete_job(self, job_id: str, result: Optional[dict] = None, error: Optional[str] = None) -> None:
        """Mark a job as completed or failed."""
        ...

    @abstractmethod
    def request_cancel(self, job_id: str) -> None:
        """Request cancellation of a running job."""
        ...

    @abstractmethod
    def is_cancelled(self, job_id: str) -> bool:
        """Check if a job has been cancelled."""
        ...

    @abstractmethod
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed jobs. Returns count removed."""
        ...


class InMemoryJobStore(JobStore):
    """In-memory job store (default).

    Good for single-process development. Jobs are lost on restart.
    """

    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._queue: list[dict] = []
        self._cancel_events: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def enqueue_job(self, job_id: str, job_data: dict) -> None:
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "status": "queued",
                "progress": 0.0,
                "data": job_data,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._queue.append({"id": job_id, "data": job_data})
            self._cancel_events[job_id] = threading.Event()
        logger.info(f"Job {job_id} enqueued")

    def dequeue_job(self, timeout: float = 1.0) -> Optional[dict]:
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                if self._queue:
                    job = self._queue.pop(0)
                    self._jobs[job["id"]]["status"] = "running"
                    self._jobs[job["id"]]["updated_at"] = datetime.now(timezone.utc).isoformat()
                    return job
            time.sleep(0.1)
        return None

    def get_job_status(self, job_id: str) -> Optional[dict]:
        with self._lock:
            return self._jobs.get(job_id)

    def update_job_progress(self, job_id: str, status: str, progress: float, **kwargs) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = status
                self._jobs[job_id]["progress"] = progress
                self._jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._jobs[job_id].update(kwargs)

    def complete_job(self, job_id: str, result: Optional[dict] = None, error: Optional[str] = None) -> None:
        with self._lock:
            if job_id in self._jobs:
                status = "failed" if error else "completed"
                self._jobs[job_id]["status"] = status
                self._jobs[job_id]["progress"] = 1.0 if not error else self._jobs[job_id].get("progress", 0)
                self._jobs[job_id]["result"] = result
                self._jobs[job_id]["error"] = error
                self._jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
                self._jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Job {job_id} {status}")

    def request_cancel(self, job_id: str) -> None:
        event = self._cancel_events.get(job_id)
        if event:
            event.set()
            logger.info(f"Job {job_id} cancellation requested")

    def is_cancelled(self, job_id: str) -> bool:
        event = self._cancel_events.get(job_id)
        return event.is_set() if event else False

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        removed = 0
        with self._lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if job.get("status") in ("completed", "failed", "cancelled"):
                    try:
                        updated = datetime.fromisoformat(job["updated_at"]).timestamp()
                        if updated < cutoff:
                            to_remove.append(job_id)
                    except (ValueError, KeyError):
                        pass

            for job_id in to_remove:
                del self._jobs[job_id]
                self._cancel_events.pop(job_id, None)
                removed += 1

        return removed


class RedisJobStore(JobStore):
    """Redis-backed job store for production use.

    Supports multi-process deployment and job persistence across restarts.
    Requires redis package: pip install redis
    """

    def __init__(self, redis_url: Optional[str] = None):
        try:
            import redis
        except ImportError:
            raise ImportError(
                "Redis backend requires the 'redis' package. "
                "Install with: pip install redis"
            )

        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._client = redis.from_url(self._redis_url, decode_responses=True)
        self._prefix = "quantive:jobs:"

        # Test connection
        try:
            self._client.ping()
            logger.info(f"Connected to Redis at {self._redis_url}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _key(self, job_id: str, suffix: str = "") -> str:
        return f"{self._prefix}{job_id}:{suffix}" if suffix else f"{self._prefix}{job_id}"

    def enqueue_job(self, job_id: str, job_data: dict) -> None:
        job = {
            "id": job_id,
            "status": "queued",
            "progress": 0.0,
            "data": json.dumps(job_data),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        pipe = self._client.pipeline()
        pipe.hset(self._key(job_id), mapping=job)
        pipe.lpush(f"{self._prefix}queue", job_id)
        pipe.execute()
        logger.info(f"Job {job_id} enqueued to Redis")

    def dequeue_job(self, timeout: float = 1.0) -> Optional[dict]:
        # Block pop from queue
        result = self._client.brpop(f"{self._prefix}queue", timeout=timeout)
        if result:
            _, job_id = result
            job_data = self._client.hgetall(self._key(job_id))
            if job_data:
                job_data["status"] = "running"
                job_data["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._client.hset(self._key(job_id), mapping={
                    "status": "running",
                    "updated_at": job_data["updated_at"],
                })
                return {"id": job_id, "data": json.loads(job_data.get("data", "{}"))}
        return None

    def get_job_status(self, job_id: str) -> Optional[dict]:
        data = self._client.hgetall(self._key(job_id))
        if data:
            data["progress"] = float(data.get("progress", 0))
            return data
        return None

    def update_job_progress(self, job_id: str, status: str, progress: float, **kwargs) -> None:
        mapping = {
            "status": status,
            "progress": str(progress),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        for k, v in kwargs.items():
            if isinstance(v, (dict, list)):
                mapping[k] = json.dumps(v)
            else:
                mapping[k] = str(v) if v is not None else ""
        self._client.hset(self._key(job_id), mapping=mapping)

    def complete_job(self, job_id: str, result: Optional[dict] = None, error: Optional[str] = None) -> None:
        status = "failed" if error else "completed"
        mapping = {
            "status": status,
            "progress": "1.0" if not error else "",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if result:
            mapping["result"] = json.dumps(result)
        if error:
            mapping["error"] = error[:2000]
        self._client.hset(self._key(job_id), mapping=mapping)
        logger.info(f"Job {job_id} {status} in Redis")

    def request_cancel(self, job_id: str) -> None:
        self._client.set(f"{self._prefix}cancel:{job_id}", "1", ex=3600)
        logger.info(f"Job {job_id} cancellation requested in Redis")

    def is_cancelled(self, job_id: str) -> bool:
        return self._client.exists(f"{self._prefix}cancel:{job_id}") == 1

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        removed = 0

        # Scan for job keys
        cursor = 0
        while True:
            cursor, keys = self._client.scan(cursor, match=f"{self._prefix}*", count=100)
            for key in keys:
                if ":queue" in key or ":cancel:" in key:
                    continue
                job_data = self._client.hgetall(key)
                if job_data.get("status") in ("completed", "failed", "cancelled"):
                    try:
                        updated = datetime.fromisoformat(job_data["updated_at"]).timestamp()
                        if updated < cutoff:
                            self._client.delete(key)
                            removed += 1
                    except (ValueError, KeyError):
                        pass
            if cursor == 0:
                break

        return removed


def get_job_store() -> JobStore:
    """Get the appropriate job store based on configuration.

    Uses Redis if REDIS_URL is set, otherwise falls back to in-memory.
    """
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            return RedisJobStore(redis_url)
        except Exception as e:
            logger.warning(f"Failed to initialize Redis job store, falling back to in-memory: {e}")

    return InMemoryJobStore()


# Singleton instance
_job_store: Optional[JobStore] = None
_store_lock = threading.Lock()


def get_singleton_job_store() -> JobStore:
    """Get or create the singleton job store instance."""
    global _job_store
    if _job_store is None:
        with _store_lock:
            if _job_store is None:
                _job_store = get_job_store()
    return _job_store
