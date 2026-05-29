"""Scheduler routes: run-all orchestration + status.

POST /scheduler/run-all
  - Accepts immediately (202).
  - Returns run_id.
  - Launches sequential coordinator in background thread.
  - Guard: if a run is already active, returns 409.

GET /scheduler/status
  - Returns active runs, latest run details, currently running pipeline names.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..pipelines import PIPELINES
from ..schemas.common import (
    RunStatusResponse,
    SchedulerStatusResponse,
    TriggerResponse,
    PipelineJobSummary,
    MessageResponse,
)
from ..services.job_store import store as job_store
from ..services.runner import launch_sequential
from ..services.scheduler_store import sched_store

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

# Canonical execution order (dependency-safe)
_RUN_ORDER = [
    "company-master",
    "equity-eod",
    "corporate-actions",
    "shareholding",
    "mf-scheme-master",
    "mf-nav",
    "mf-holdings",
]


def _run_to_response(rec) -> RunStatusResponse:
    return RunStatusResponse(
        run_id=rec.run_id,
        status=rec.status.value,
        started_at=rec.started_at,
        finished_at=rec.finished_at,
        pipeline_jobs=[
            PipelineJobSummary(pipeline=p, job_id=j)
            for p, j in rec.pipeline_jobs
        ],
        failures=rec.failures,
    )


@router.post(
    "/run-all",
    response_model=TriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={409: {"model": MessageResponse, "description": "A run is already active"}},
    summary="Run every pipeline in dependency order (non-blocking)",
)
async def run_all() -> TriggerResponse:
    # Guard: reject if a run is already active
    active = sched_store.active_run_ids()
    if active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"run '{active[0]}' is already active; wait for it to finish",
        )

    # Resolve specs in declared order (skip any not in registry)
    specs = [PIPELINES[name] for name in _RUN_ORDER if name in PIPELINES]

    run = sched_store.create_run()
    launch_sequential(specs, run.run_id)

    return TriggerResponse(
        accepted=True,
        pipeline="*",
        job_id=run.run_id,
        detail=(
            f"run '{run.run_id}' queued ({len(specs)} pipelines); "
            f"poll GET /scheduler/status"
        ),
    )


@router.get(
    "/status",
    response_model=SchedulerStatusResponse,
    summary="Scheduler state: active runs, latest run, running pipelines",
)
async def scheduler_status() -> SchedulerStatusResponse:
    latest = sched_store.latest()
    return SchedulerStatusResponse(
        active_run_ids=sched_store.active_run_ids(),
        latest_run=_run_to_response(latest) if latest else None,
        running_pipelines=job_store.running_pipelines(),
    )
