"""End-to-end pipeline: AMFI NAVAll.txt → bronze → silver → gold → xlsx.

Produces the MF Scheme Master sheet (5_MFSchemeMaster).
Reuses the same bronze source as the MF NAV pipeline.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..core.logging import get_logger
from ..core.settings import Settings, ensure_directories, load_settings
from ..exporters.excel.workbook import write_mf_scheme_master_workbook
from ..normalizers.mf_nav import parse_navall_file
from ..sources.amfi_adapter import AmfiAdapter
from ..storage import paths as _paths
from ..storage.db import run_migrations
from ..storage.processed import write_gold, write_silver
from ..transformers.mf_scheme_master import to_gold
from ..validators.mf_scheme_master import validate

log = get_logger("pipeline.mf_scheme_master")


def run(as_of: date | None = None, settings: Settings | None = None) -> Path:
    settings = settings or load_settings()
    ensure_directories(settings)
    run_migrations(settings)
    as_of = as_of or date.today()

    log.info("pipeline.mf_scheme_master.start", as_of=as_of.isoformat())

    # 1. INGEST (bronze) — reuses AmfiAdapter / NAVAll.txt
    adapter = AmfiAdapter(settings)
    bronze = adapter.fetch(partition=as_of)
    log.info(
        "pipeline.mf_scheme_master.bronze_ok",
        path=str(bronze.path),
        rows=bronze.rows_hint,
    )

    # 2. NORMALIZE → silver (reuses mf_nav normalizer)
    silver = parse_navall_file(bronze.path)
    silver_path = write_silver(settings, "mf_scheme_master", as_of, silver)
    log.info(
        "pipeline.mf_scheme_master.silver_ok",
        path=str(silver_path),
        rows=silver.height,
    )

    # 3. TRANSFORM → gold
    gold = to_gold(silver, as_of)
    gold_path = write_gold(settings, "mf_scheme_master", as_of, gold)
    log.info(
        "pipeline.mf_scheme_master.gold_ok",
        path=str(gold_path),
        rows=gold.height,
    )

    # 4. VALIDATE
    report = validate(gold)
    for w in report.warnings:
        log.warning("pipeline.mf_scheme_master.warn", detail=w)
    log.info("pipeline.mf_scheme_master.validated", rows=gold.height)

    # 5. EXPORT
    out_xlsx = _paths.output_path(settings, "mf_scheme_master", as_of)
    write_mf_scheme_master_workbook(gold, out_xlsx)
    log.info(
        "pipeline.mf_scheme_master.export_ok",
        path=str(out_xlsx),
        rows=gold.height,
    )
    return out_xlsx
