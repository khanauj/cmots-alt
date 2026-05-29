"""End-to-end pipeline: AMC portfolios → bronze → silver → gold → xlsx.

Produces the MF Holdings sheet (6_MFHoldings).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..core.logging import get_logger
from ..core.settings import Settings, ensure_directories, load_settings
from ..exporters.excel.workbook import write_mf_holdings_workbook
from ..normalizers.mf_holdings import parse_portfolio_file
from ..sources.amc_portfolio_adapter import AmcPortfolioAdapter
from ..storage import paths as _paths
from ..storage.processed import write_gold, write_silver
from ..transformers.mf_holdings import to_gold
from ..validators.mf_holdings import validate

log = get_logger("pipeline.mf_holdings")


def run(as_of: date | None = None, settings: Settings | None = None) -> Path:
    settings = settings or load_settings()
    ensure_directories(settings)
    as_of = as_of or date.today()

    log.info("pipeline.mf_holdings.start", as_of=as_of.isoformat())

    # 1. INGEST (bronze)
    adapter = AmcPortfolioAdapter(settings)
    bronze = adapter.fetch(partition=as_of)
    log.info(
        "pipeline.mf_holdings.bronze_ok",
        path=str(bronze.path),
        rows=bronze.rows_hint,
    )

    # 2. NORMALIZE → silver
    silver = parse_portfolio_file(bronze.path)
    silver_path = write_silver(settings, "mf_holdings", as_of, silver)
    log.info(
        "pipeline.mf_holdings.silver_ok",
        path=str(silver_path),
        rows=silver.height,
    )

    # 3. TRANSFORM → gold
    gold = to_gold(silver, as_of, settings)
    gold_path = write_gold(settings, "mf_holdings", as_of, gold)
    log.info(
        "pipeline.mf_holdings.gold_ok",
        path=str(gold_path),
        rows=gold.height,
    )

    # 4. VALIDATE
    report = validate(gold)
    for w in report.warnings:
        log.warning("pipeline.mf_holdings.warn", detail=w)
    log.info("pipeline.mf_holdings.validated", rows=gold.height)

    # 5. EXPORT
    out_xlsx = _paths.output_path(settings, "mf_holdings", as_of)
    write_mf_holdings_workbook(gold, out_xlsx)
    log.info(
        "pipeline.mf_holdings.export_ok",
        path=str(out_xlsx),
        rows=gold.height,
    )
    return out_xlsx
