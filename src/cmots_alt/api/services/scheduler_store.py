"""Scheduler run store — tracks full run-all executions.

A "run" is a coordinator job that executes all 7 pipelines sequentially.
Thread-safe. Capped at MAX_RUNS entries (oldest evicted first).
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class RunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"           # all pipelines succeeded
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"  # some failed, some succeeded
    FAILED = "FAILED"             # all pipelines failed (or coordinator crashed)


MAX_RUNS = 100


@dataclass
class RunRecord:
    run_id: str
    status: RunStatus = RunStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    # Ordered list of (pipeline_name, job_id) pairs
    pipeline_jobs: list[tuple[str, str]] = field(default_factory=list)
    # pipeline_name -> error string for failed pipelines
    failures: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "pipeline_jobs": [
                {"pipeline": p, "job_id": j} for p, j in self.pipeline_jobs
            ],
            "failures": self.failures,
        }


class SchedulerStore:
    """Capped ring-buffer of RunRecords. Thread-safe."""

    def __init__(self, max_runs: int = MAX_RUNS) -> None:
        self._lock = threading.Lock()
        self._runs: dict[str, RunRecord] = {}
        self._order: list[str] = []   # insertion-ordered run_ids
        self._max = max_runs

    # ── write ────────────────────────────────────────────────────────────────
    def create_run(self) -> RunRecord:
        run_id = str(uuid.uuid4())
        rec = RunRecord(run_id=run_id)
        with self._lock:
            self._runs[run_id] = rec
            self._order.append(run_id)
            # evict oldest if over cap
            while len(self._order) > self._max:
                old = self._order.pop(0)
                self._runs.pop(old, None)
        return rec

    def mark_run_running(self, run_id: str) -> None:
        with self._lock:
            rec = self._runs[run_id]
            rec.status = RunStatus.RUNNING
            rec.started_at = datetime.now(timezone.utc)

    def add_pipeline_job(self, run_id: str, pipeline: str, job_id: str) -> None:
        with self._lock:
            self._runs[run_id].pipeline_jobs.append((pipeline, job_id))

    def mark_run_finished(self, run_id: str) -> None:
        with self._lock:
            rec = self._runs[run_id]
            rec.finished_at = datetime.now(timezone.utc)
            n_total = len(rec.pipeline_jobs)
            n_failed = len(rec.failures)
            if n_failed == 0:
                rec.status = RunStatus.SUCCESS
            elif n_failed == n_total:
                rec.status = RunStatus.FAILED
            else:
                rec.status = RunStatus.PARTIAL_SUCCESS

    def record_failure(self, run_id: str, pipeline: str, error: str) -> None:
        with self._lock:
            self._runs[run_id].failures[pipeline] = error

    # ── read ─────────────────────────────────────────────────────────────────
    def get(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def latest(self) -> RunRecord | None:
        with self._lock:
            return self._runs[self._order[-1]] if self._order else None

    def active_run_ids(self) -> list[str]:
        with self._lock:
            return [
                r.run_id for r in self._runs.values()
                if r.status in (RunStatus.PENDING, RunStatus.RUNNING)
            ]

    def all_runs(self) -> list[RunRecord]:
        with self._lock:
            return [self._runs[rid] for rid in reversed(self._order)]


# Module-level singleton
sched_store = SchedulerStore()
