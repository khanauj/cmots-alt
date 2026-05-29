"""In-process job store for pipeline executions.

Thread-safe: every mutation goes through a Lock. Jobs live for the process
lifetime (no persistence). Capped at MAX_JOBS entries (oldest evicted first).
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


MAX_JOBS = 100


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass
class JobRecord:
    job_id: str
    pipeline: str
    status: JobStatus = JobStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    partition: str | None = None   # gold partition produced (if available)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "pipeline": self.pipeline,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "partition": self.partition,
        }


class JobStore:
    """Append-only, dict-backed job log. Thread-safe. Capped at MAX_JOBS."""

    def __init__(self, max_jobs: int = MAX_JOBS) -> None:
        self._lock = threading.Lock()
        self._jobs: dict[str, JobRecord] = {}
        self._order: list[str] = []   # insertion-ordered
        self._max = max_jobs

    # ── write ────────────────────────────────────────────────────────────────
    def create(self, pipeline: str) -> JobRecord:
        job_id = str(uuid.uuid4())
        rec = JobRecord(job_id=job_id, pipeline=pipeline)
        with self._lock:
            self._jobs[job_id] = rec
            self._order.append(job_id)
            while len(self._order) > self._max:
                old = self._order.pop(0)
                self._jobs.pop(old, None)
        return rec

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            rec = self._jobs[job_id]
            rec.status = JobStatus.RUNNING
            rec.started_at = datetime.now(timezone.utc)

    def mark_success(self, job_id: str, partition: str | None = None) -> None:
        with self._lock:
            rec = self._jobs[job_id]
            rec.status = JobStatus.SUCCESS
            rec.finished_at = datetime.now(timezone.utc)
            rec.partition = partition

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            rec = self._jobs[job_id]
            rec.status = JobStatus.FAILED
            rec.finished_at = datetime.now(timezone.utc)
            rec.error = error

    # ── read ─────────────────────────────────────────────────────────────────
    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list_all(self) -> list[JobRecord]:
        with self._lock:
            return list(reversed(list(self._jobs.values())))

    def running_pipelines(self) -> list[str]:
        with self._lock:
            return [
                r.pipeline for r in self._jobs.values()
                if r.status == JobStatus.RUNNING
            ]

    def is_pipeline_running(self, pipeline: str) -> bool:
        """Single-flight guard: True if a job for this pipeline is RUNNING."""
        with self._lock:
            return any(
                r.pipeline == pipeline and r.status == JobStatus.RUNNING
                for r in self._jobs.values()
            )


# Module-level singleton shared by all routers
store = JobStore()
