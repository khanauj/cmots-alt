"""Silver/gold parquet writers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from ..core.settings import Settings
from . import paths as _paths


def write_silver(settings: Settings, domain: str, partition: date, df: pl.DataFrame) -> Path:
    out = _paths.silver_path(settings, domain, partition)
    df.write_parquet(out, compression="zstd")
    return out


def write_gold(settings: Settings, domain: str, partition: date, df: pl.DataFrame) -> Path:
    out = _paths.gold_path(settings, domain, partition)
    df.write_parquet(out, compression="zstd")
    return out
