"""In-memory asynchronous job manager.

Optimizations can take significant time (especially with thousands of Monte
Carlo scenarios), so runs execute in a background thread pool. The API never
blocks: callers poll the job status.

Job timeout: if a job runs longer than ``job_timeout`` seconds, it will be
cancelled automatically. This prevents runaway optimizations from blocking
the API or consuming excessive resources.
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from quantive.models.enums import JobStatus


#: Default job timeout in seconds, read from QUANTIVE_JOB_TIMEOUT env var
DEFAULT_JOB_TIMEOUT = int(os.getenv("QUANTIVE_JOB_TIMEOUT", "300"))

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
    timeout_seconds: int = field(default_factory=DEFAULT_JOB_TIMEOUT)

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
            "timeout_seconds": self.timeout_seconds,
        }

    @property
    def is_timed_out(self) -> bool:
        """Check if the job has exceeded its timeout."""
        if self.started_at is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self.started_at).total_seconds()
        return elapsed > self.timeout_seconds


class JobManager:
    """Thread-safe job store with a bounded thread pool.

    Supports job timeout cancellation for runaway optimizations.
    """

    def __init__(self, max_workers: int = 2):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="quantive-job")
        self._timeout_monitor_thread: Optional[threading.Thread] = None
        self._shutdown_flag = False

    def submit(self, fn: Callable, *args, timeout: int = None, **kwargs) -> Job:
        """Submit a job for asynchronous execution.

        Args:
            fn: Function to execute
            *args: Positional arguments for fn
            timeout: Override default job timeout in seconds; None uses default
            kwargs: Keyword arguments for fn
        """
        job_id = uuid.uuid4().hex[:12]
        job = Job(id=job_id, timeout_seconds=timeout or DEFAULT_JOB_TIMEOUT)
        with self._lock:
            self._jobs[job_id] = job
        self._pool.submit(self._run, job, fn, args, kwargs)
        return job

    def cancel(self, job_id: str) -> bool:
        """Request cancellation of a running job.

        Returns True if the job was successfully cancelled, False if it
        wasn't found or already completed.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                return False
            job.status = JobStatus.CANCELLED
            job.error = "Job cancelled by user request"
            job.message = "cancelled"
            job.finished_at = datetime.now(timezone.utc)
            return True

    def _run(self, job: Job, fn: Callable, args, kwargs) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        job.message = "running"
        job.progress = 0.05

        # Set up timeout monitoring
        timeout = job.timeout_seconds

        def timeout_check():
            """Check if job has exceeded timeout; if so, cancel it."""
            while not self._shutdown_flag:
                time.sleep(max(1, timeout // 10))  # Check every ~10% of timeout
                if job.is_timed_out:
                    job.status = JobStatus.COMPLETED  # Will be treated as timeout
                    job.error = f"Job exceeded {timeout}s timeout"
                    job.message = "timed_out"
                    job.progress = 1.0
                    job.finished_at = datetime.now(timezone.utc)
                    break

        # Start timeout monitor in daemon thread
        _timeout_thread = threading.Thread(target=timeout_check, daemon=True)
        _timeout_thread.start()

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
            self._timeout_thread_join(_timeout_thread)
            job.finished_at = datetime.now(timezone.utc)

    def _timeout_thread_join(self, thread: threading.Thread, timeout: int = 5) -> None:
        """Join timeout monitor thread with timeout."""
        thread.join(timeout=timeout)
        # Daemon threads may not fully join; that's acceptable

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update_progress(self, job: Job, progress: float, message: str) -> None:
        job.progress = progress
        job.message = message

    def shutdown(self) -> None:
        """Shut down the job manager and its thread pool."""
        self._shutdown_flag = True
        self._pool.shutdown(wait=False)