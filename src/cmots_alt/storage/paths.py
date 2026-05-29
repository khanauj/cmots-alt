"""Central path conventions: bronze/silver/gold/output layout."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..core.settings import Settings


def bronze_dir(settings: Settings, source: str, artifact: str, partition: date) -> Path:
    return (
        settings.resolve(settings.paths.storage.raw)
        / source
        / artifact
        / f"dt={partition.isoformat()}"
    )


def silver_path(settings: Settings, domain: str, partition: date) -> Path:
    d = settings.resolve(settings.paths.storage.silver) / domain
    d.mkdir(parents=True, exist_ok=True)
    return d / f"dt={partition.isoformat()}.parquet"


def gold_path(settings: Settings, domain: str, partition: date) -> Path:
    d = settings.resolve(settings.paths.storage.gold) / domain
    d.mkdir(parents=True, exist_ok=True)
    return d / f"dt={partition.isoformat()}.parquet"


def output_path(settings: Settings, name: str, partition: date) -> Path:
    d = settings.resolve(settings.paths.storage.output)
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{name}_{partition.isoformat()}.xlsx"
