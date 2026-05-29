"""Pipeline runner — background execution engine.

Launches each pipeline in a dedicated thread from a shared ThreadPoolExecutor.
The pipeline callable is imported lazily (importlib) to avoid pulling the
scraper/HTTP stack into the API worker process at startup.

Contract:
- `launch(spec, job_id)` is non-blocking; returns immediately.
- All exceptions inside the thread are caught; the job is marked FAILED.
- xlsxwriter PermissionError (file locked) is demoted to a WARNING: the gold
  parquet has already been written; xlsx is a convenience export only.
- Structured logs are emitted at RUNNING / SUCCESS / FAILED transitions.
- The partition produced is detected via `gold.latest_partition` after the run
  and attached to the job record regardless of terminal status.
"""

from __future__ import annotations

import importlib
import traceback
from concurrent.futures import ThreadPoolExecutor

from ...core.logging import get_logger
from ..pipelines import PipelineSpec
from ..services import gold
from .job_store import JobRecord, store

log = get_logger("api.runner")

# One shared executor; keeps threads bounded; daemon=True so they don't block
# process shutdown.
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="pipeline")

# xlsxwriter raises this when the output file is locked / open in Excel.
_XLSX_ERR = "xlsxwriter.exceptions.FileCreateError"


def _is_xlsx_lock(exc: Exception) -> bool:
    """True when the only failure is a locked xlsx output file."""
    t = type(exc)
    return f"{t.__module__}.{t.__qualname__}" == _XLSX_ERR or (
        isinstance(exc, PermissionError)
        and any(s in str(exc) for s in (".xlsx", ".xls"))
    )


def _run_pipeline(spec: PipelineSpec, job: JobRecord) -> None:
    """Executed inside the thread. Never raises — all exceptions are caught."""
    store.mark_running(job.job_id)
    log.info("runner.start", job_id=job.job_id, pipeline=spec.name)
    failed_exc: Exception | None = None
    try:
        module_path, func_name = spec.run_path.rsplit(":", 1)
        mod = importlib.import_module(module_path)
        run_fn = getattr(mod, func_name)
        run_fn()
    except Exception as exc:  # noqa: BLE001
        if _is_xlsx_lock(exc):
            # Gold parquet already written; xlsx is a convenience export only.
            log.warning(
                "runner.xlsx_locked",
                job_id=job.job_id,
                pipeline=spec.name,
                detail="xlsx export skipped (file locked); gold partition is intact",
            )
        else:
            failed_exc = exc
    finally:
        # Always check whether a gold partition now exists — even on failure the
        # pipeline may have written the parquet before the xlsx step raised.
        partition = gold.latest_partition(spec.gold_domain)

    if failed_exc is not None:
        err = traceback.format_exc()
        store.mark_failed(job.job_id, error=str(failed_exc))
        log.error(
            "runner.failed",
            job_id=job.job_id,
            pipeline=spec.name,
            error=str(failed_exc),
            traceback=err,
        )
    else:
        store.mark_success(job.job_id, partition=partition)
        log.info(
            "runner.success",
            job_id=job.job_id,
            pipeline=spec.name,
            partition=partition,
        )


def launch(spec: PipelineSpec, job: JobRecord) -> None:
    """Non-blocking: submits the pipeline to the thread pool and returns."""
    _executor.submit(_run_pipeline, spec, job)


# ── scheduler coordinator ─────────────────────────────────────────────────────
def _run_sequential(specs: list[PipelineSpec], run_id: str) -> None:
    """Sequential coordinator — runs inside a single thread from the executor.

    For each pipeline in order:
    - Skips if already RUNNING (single-flight guard).
    - Calls _run_pipeline synchronously (blocking within this thread).
    - Records job_id in sched_store; records failure if pipeline fails.
    - Always continues to the next pipeline regardless of failure.
    """
    from .scheduler_store import sched_store  # local import avoids circular

    sched_store.mark_run_running(run_id)
    log.info("scheduler.run.start", run_id=run_id, pipeline_count=len(specs))

    for spec in specs:
        if store.is_pipeline_running(spec.name):
            log.warning(
                "scheduler.skip.already_running",
                run_id=run_id,
                pipeline=spec.name,
            )
            continue

        job = store.create(pipeline=spec.name)
        sched_store.add_pipeline_job(run_id, spec.name, job.job_id)
        log.info(
            "scheduler.pipeline.start",
            run_id=run_id,
            pipeline=spec.name,
            job_id=job.job_id,
        )

        # Run synchronously inside this coordinator thread (sequential).
        _run_pipeline(spec, job)

        # Check outcome and mirror to run record.
        rec = store.get(job.job_id)
        if rec and rec.status.value == "FAILED":
            err = rec.error or "unknown error"
            sched_store.record_failure(run_id, spec.name, err)
            log.warning(
                "scheduler.pipeline.failed",
                run_id=run_id,
                pipeline=spec.name,
                error=err,
            )
        else:
            log.info(
                "scheduler.pipeline.success",
                run_id=run_id,
                pipeline=spec.name,
            )

    sched_store.mark_run_finished(run_id)
    final = sched_store.get(run_id)
    log.info(
        "scheduler.run.finished",
        run_id=run_id,
        status=final.status.value if final else "unknown",
        failures=list(final.failures.keys()) if final else [],
    )


def launch_sequential(specs: list[PipelineSpec], run_id: str) -> None:
    """Non-blocking: submits the sequential coordinator to the thread pool."""
    _executor.submit(_run_sequential, specs, run_id)
