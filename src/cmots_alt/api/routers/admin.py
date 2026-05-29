"""Admin routes: pipeline management, trigger execution, job tracking."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..pipelines import get_pipeline, list_pipelines
from ..schemas.common import JobResponse, MessageResponse, PipelineInfo, TriggerResponse
from ..services import gold
from ..services.job_store import store
from ..services.runner import launch

router = APIRouter(prefix="/admin", tags=["admin"])

_NOT_FOUND = {404: {"model": MessageResponse}}


# ── pipelines listing ─────────────────────────────────────────────────────────
@router.get("/pipelines", response_model=list[PipelineInfo], summary="List ingestion pipelines")
async def pipelines() -> list[PipelineInfo]:
    out: list[PipelineInfo] = []
    for p in list_pipelines():
        part = gold.latest_partition(p.gold_domain)
        out.append(PipelineInfo(
            name=p.name, gold_domain=p.gold_domain, description=p.description,
            available=part is not None, latest_partition=part,
        ))
    return out


# ── trigger ───────────────────────────────────────────────────────────────────
@router.post(
    "/trigger/{pipeline}",
    response_model=TriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_NOT_FOUND,
    summary="Trigger a pipeline run (non-blocking)",
)
async def trigger(pipeline: str) -> TriggerResponse:
    spec = get_pipeline(pipeline)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"unknown pipeline '{pipeline}'; see GET /admin/pipelines",
        )

    # Create job record, then submit to thread pool — returns immediately.
    job = store.create(pipeline=spec.name)
    launch(spec, job)

    return TriggerResponse(
        accepted=True,
        pipeline=spec.name,
        job_id=job.job_id,
        detail=f"pipeline '{spec.name}' queued; poll GET /admin/job/{job.job_id}",
    )


# ── job inspection ────────────────────────────────────────────────────────────
@router.get(
    "/jobs",
    response_model=list[JobResponse],
    summary="List all jobs (newest first)",
)
async def list_jobs() -> list[JobResponse]:
    return [JobResponse(**r.to_dict()) for r in store.list_all()]


@router.get(
    "/job/{job_id}",
    response_model=JobResponse,
    responses=_NOT_FOUND,
    summary="Get job status by ID",
)
async def get_job(job_id: str) -> JobResponse:
    rec = store.get(job_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"job '{job_id}' not found",
        )
    return JobResponse(**rec.to_dict())
