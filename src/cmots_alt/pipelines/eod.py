"""End-to-end Equity EOD pipeline: NSE + BSE bhavcopy → bronze → silver → gold → xlsx.

Resolves every row to a stable co_code through the CompanyMaster crosswalk, so a
CompanyMaster run must have populated the company table first.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..core.logging import get_logger
from ..core.settings import Settings, ensure_directories, load_settings
from ..exporters.excel.workbook import (
    write_equity_eod_workbook,
    write_resolver_report_workbook,
)
from ..normalizers.eod import parse_bse_bhavcopy, parse_nse_bhavcopy
from ..sources.bhavcopy import BseBhavcopyAdapter, NseBhavcopyAdapter
from ..storage import paths as _paths
from ..storage.db import run_migrations
from ..storage.processed import write_gold, write_silver
from ..transformers import eod as eod_tx
from ..transformers.identity_resolver import load_aliases
from ..transformers.resolver import load_identity_maps
from ..validators import eod as validator

log = get_logger("pipeline.eod")


def run(as_of: date | None = None, settings: Settings | None = None) -> Path:
    settings = settings or load_settings()
    ensure_directories(settings)
    run_migrations(settings)
    as_of = as_of or date.today()

    log.info("pipeline.eod.start", as_of=as_of.isoformat())

    # 1. INGEST (bronze) — each adapter walks back to the latest trading day.
    nse_bhav = NseBhavcopyAdapter(settings).fetch(partition=as_of)
    bse_bhav = BseBhavcopyAdapter(settings).fetch(partition=as_of)
    log.info(
        "pipeline.eod.bronze_ok",
        nse_trade_date=nse_bhav.trade_date.isoformat(),
        bse_trade_date=bse_bhav.trade_date.isoformat(),
        nse_path=str(nse_bhav.bronze.path),
        bse_path=str(bse_bhav.bronze.path),
    )

    # 2. NORMALIZE → silver (unified EOD schema per exchange).
    nse_silver = parse_nse_bhavcopy(nse_bhav.bronze.path)
    bse_silver = parse_bse_bhavcopy(bse_bhav.bronze.path)
    write_silver(settings, "eod_nse", as_of, nse_silver)
    write_silver(settings, "eod_bse", as_of, bse_silver)
    log.info("pipeline.eod.silver_ok", nse_rows=nse_silver.height, bse_rows=bse_silver.height)

    # 3. RESOLVE against CompanyMaster (hardened waterfall) + merge + dedupe.
    maps = load_identity_maps(settings)
    if maps.count == 0:
        log.warning("pipeline.eod.no_company_master",
                    detail="company table empty — run 'cmots ingest company-master' first")
    aliases = load_aliases(settings.project_root)
    merged = eod_tx.resolve_and_merge(nse_silver, bse_silver, maps, aliases)

    # 4. GOLD projection.
    gold = eod_tx.to_gold(merged)
    gold_path = write_gold(settings, "equity_eod", as_of, gold)
    log.info("pipeline.eod.gold_ok", rows=gold.height, path=str(gold_path))

    # 5. VALIDATE (fatal on duplicate co_code+TradeDate+Exchange).
    report = validator.validate(gold)
    for w in report.warnings:
        log.warning("pipeline.eod.warn", detail=w)
    log.info(
        "pipeline.eod.coverage",
        rows=report.rows,
        resolved=report.resolved,
        overall_coverage_pct=report.coverage_pct,
        equity_rows=report.equity_rows,
        equity_coverage_pct=report.equity_coverage_pct,
        missing_co_code=report.missing_co_code,
    )

    # 6. EXPORT EOD sheet + resolver diagnostics workbook.
    out_xlsx = _paths.output_path(settings, "equity_eod", as_of)
    write_equity_eod_workbook(gold, out_xlsx)
    report_xlsx = _paths.output_path(settings, "resolver_report", as_of)
    write_resolver_report_workbook(merged, report, report_xlsx)
    log.info(
        "pipeline.eod.export_ok",
        path=str(out_xlsx),
        resolver_report=str(report_xlsx),
        rows=gold.height,
    )
    return out_xlsx
