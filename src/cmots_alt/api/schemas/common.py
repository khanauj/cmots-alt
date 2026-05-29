"""Shared response models (system / admin / scheduler)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field("ok", examples=["ok"])
    service: str = Field(examples=["CMOTS-alt API"])
    version: str = Field(examples=["0.1.0"])
    time: datetime


class DatasetStatus(BaseModel):
    pipeline: str = Field(examples=["company-master"])
    gold_domain: str = Field(examples=["company_master"])
    available: bool = Field(description="Whether a gold parquet partition exists on disk")
    latest_partition: str | None = Field(default=None, examples=["2026-05-27"])


class StatusResponse(BaseModel):
    status: str = Field("ok")
    version: str
    uptime_seconds: float
    datasets: list[DatasetStatus]


class PipelineInfo(BaseModel):
    name: str = Field(examples=["equity-eod"])
    gold_domain: str = Field(examples=["equity_eod"])
    description: str
    available: bool = Field(description="Whether gold output exists")
    latest_partition: str | None = None


class TriggerResponse(BaseModel):
    accepted: bool = Field(True)
    pipeline: str
    job_id: str = Field(examples=["job-20260527-equity-eod"])
    detail: str = Field(examples=["scaffold: trigger not yet wired to pipeline runner"])


class JobResponse(BaseModel):
    job_id: str = Field(examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    pipeline: str = Field(examples=["company-master"])
    status: str = Field(examples=["PENDING", "RUNNING", "SUCCESS", "FAILED"])
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    partition: str | None = Field(default=None, examples=["2026-05-27"])


class PipelineJobSummary(BaseModel):
    """One pipeline stage within a run-all execution."""
    pipeline: str = Field(examples=["company-master"])
    job_id: str = Field(examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])


class RunStatusResponse(BaseModel):
    """Status of a single run-all execution."""
    run_id: str = Field(examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    status: str = Field(examples=["PENDING", "RUNNING", "SUCCESS", "PARTIAL_SUCCESS", "FAILED"])
    started_at: datetime | None = None
    finished_at: datetime | None = None
    pipeline_jobs: list[PipelineJobSummary] = Field(default_factory=list)
    failures: dict[str, str] = Field(
        default_factory=dict,
        description="pipeline_name -> error string for any failed stage",
    )


class SchedulerStatusResponse(BaseModel):
    """Current state of the scheduler."""
    active_run_ids: list[str] = Field(
        default_factory=list,
        description="run_ids currently PENDING or RUNNING",
    )
    latest_run: RunStatusResponse | None = None
    running_pipelines: list[str] = Field(
        default_factory=list,
        description="Individual pipeline names currently RUNNING",
    )


class MessageResponse(BaseModel):
    detail: str
