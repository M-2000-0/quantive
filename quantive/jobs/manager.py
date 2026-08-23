"""In-memory asynchronous job manager.

Optimizations can take significant time (especially with thousands of Monte
Carlo scenarios), so runs execute in a background thread pool. The API never
blocks: callers poll the job status.
"""
from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from quantive.models.enums import JobStatus


@dataclass
class Job:
    id: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Any = None
    progress: float = 0.0
    message: str = "queued"

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "progress": self.progress,
            "message": self.message,
            "has_result": self.result is not None,
        }


class JobManager:
    """Thread-safe job store with a bounded thread pool."""

    def __init__(self, max_workers: int = 2):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="quantive-job")

    def submit(self, fn: Callable, *args, **kwargs) -> Job:
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id)
        with self._lock:
            self._jobs[job_id] = job
        self._pool.submit(self._run, job, fn, args, kwargs)
        return job

    def _run(self, job: Job, fn: Callable, args, kwargs) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        job.message = "running"
        job.progress = 0.05
        try:
            job.result = fn(*args, **kwargs)
            job.status = JobStatus.COMPLETED
            job.progress = 1.0
            job.message = "completed"
        except Exception as exc:  # noqa: BLE001 - surfaced to the client
            job.status = JobStatus.FAILED
            job.error = f"{type(exc).__name__}: {exc}"
            job.message = "failed"
        finally:
            job.finished_at = datetime.now(timezone.utc)

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update_progress(self, job: Job, progress: float, message: str) -> None:
        job.progress = progress
        job.message = message

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False)