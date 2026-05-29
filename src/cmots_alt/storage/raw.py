"""Bronze writer: persists raw captured content + manifest row."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from ..core.settings import Settings
from ..fetchers.files import sha256_of_bytes
from . import paths as _paths
from .db import get_db


def write_bronze(
    settings: Settings,
    source: str,
    artifact: str,
    partition: date,
    payload: bytes,
    suffix: str,
    *,
    started_at: datetime | None = None,
    rows: int | None = None,
) -> tuple[Path, str]:
    """Write payload under storage/raw/<source>/<artifact>/dt=YYYY-MM-DD/.

    Inserts an ingest_manifest row. Returns (path, run_id).
    """
    started_at = started_at or datetime.now(timezone.utc)
    run_id = uuid.uuid4().hex
    out_dir = _paths.bronze_dir(settings, source, artifact, partition)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}.{suffix.lstrip('.')}"
    out_path.write_bytes(payload)

    sha = sha256_of_bytes(payload)
    ended_at = datetime.now(timezone.utc)

    with get_db(settings) as conn:
        conn.execute(
            """
            INSERT INTO ingest_manifest
                (run_id, source, artifact, partition, raw_path, sha256, rows,
                 started_at, ended_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                source,
                artifact,
                partition.isoformat(),
                str(out_path),
                sha,
                rows,
                started_at.isoformat(),
                ended_at.isoformat(),
                "ok",
            ),
        )
        conn.commit()
    return out_path, run_id
