"""System routes: liveness + dataset status."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from ..config import get_api_settings
from ..pipelines import list_pipelines
from ..schemas.common import DatasetStatus, HealthResponse, StatusResponse
from ..services import gold

router = APIRouter(tags=["system"])

_STARTED = time.monotonic()


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    s = get_api_settings()
    return HealthResponse(
        status="ok", service=s.title, version=s.version, time=datetime.now(timezone.utc)
    )


@router.get("/status", response_model=StatusResponse, summary="Service + dataset readiness")
async def status() -> StatusResponse:
    s = get_api_settings()
    datasets = [
        DatasetStatus(
            pipeline=p.name,
            gold_domain=p.gold_domain,
            available=(part := gold.latest_partition(p.gold_domain)) is not None,
            latest_partition=part,
        )
        for p in list_pipelines()
    ]
    return StatusResponse(
        status="ok",
        version=s.version,
        uptime_seconds=round(time.monotonic() - _STARTED, 3),
        datasets=datasets,
    )
