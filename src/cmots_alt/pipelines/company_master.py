"""End-to-end CompanyMaster pipeline: NSE + BSE → bronze → silver → gold → xlsx."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..core.logging import get_logger
from ..core.settings import Settings, ensure_directories, load_settings
from ..exporters.excel.workbook import write_company_master_workbook
from ..normalizers.company import (
    parse_bse_scrips,
    parse_nse_equity_l,
    parse_nse_industry,
)
from ..normalizers.mc_sector import parse_mc_directory
from ..sources.bse_adapter import BseAdapter
from ..sources.moneycontrol_adapter import MoneycontrolAdapter
from ..sources.nse_adapter import NseAdapter
from ..storage import paths as _paths
from ..storage.db import run_migrations
from ..storage.processed import write_gold, write_silver
from ..transformers import company_master as cm
from ..transformers.mcap_class import assign_mcap_class
from ..transformers.resolver import ensure_companies, upsert_company_master
from ..transformers.sector import assign_sector, build_sector_master, load_sector_taxonomy
from ..transformers.short_name import load_short_name_config
from ..validators import company_master as validator

import polars as pl


def _report_sector_coverage(merged: pl.DataFrame) -> None:
    """Coverage % (excluding INF mutual-fund/ETF ISINs), confidence + conflict breakdown."""
    company = merged.filter(~pl.col("isin").str.starts_with("INF"))
    total = company.height
    mapped = company.filter(pl.col("sector_code").is_not_null()).height
    pct = 100 * mapped / total if total else 0.0
    by_source = (
        company.filter(pl.col("sector_source").is_not_null())
        .group_by("sector_source").len().sort("len", descending=True)
    )
    conflicts = merged.filter(pl.col("sector_conflict")).height
    log.info(
        "pipeline.company_master.sector_coverage",
        company_universe=total,
        mapped=mapped,
        coverage_pct=round(pct, 1),
        conflicts=conflicts,
        by_source={r[0]: r[1] for r in by_source.iter_rows()},
    )

log = get_logger("pipeline.company_master")


def run(as_of: date | None = None, settings: Settings | None = None) -> Path:
    settings = settings or load_settings()
    ensure_directories(settings)
    run_migrations(settings)
    as_of = as_of or date.today()
    root = settings.project_root

    log.info("pipeline.company_master.start", as_of=as_of.isoformat())

    # 1. INGEST (bronze)
    nse = NseAdapter(settings).fetch(partition=as_of)
    bse = BseAdapter(settings).fetch(partition=as_of)
    log.info(
        "pipeline.company_master.bronze_ok",
        nse_equity=str(nse.equity_l.path),
        nse_industry=str(nse.industry.path) if nse.industry else None,
        nse_industry_source=nse.industry_source,
        bse_kind=bse.source_kind,
        bse_path=str(bse.scrips.path),
    )

    # 2. NORMALIZE → silver
    nse_equity = parse_nse_equity_l(nse.equity_l.path)
    nse_industry = parse_nse_industry(nse.industry.path) if nse.industry else None
    bse_scrips = parse_bse_scrips(bse.scrips.path, bse.source_kind)
    write_silver(settings, "company_nse", as_of, nse_equity)
    write_silver(settings, "company_bse", as_of, bse_scrips)
    if nse_industry is not None:
        write_silver(settings, "company_nse_industry", as_of, nse_industry)
    log.info(
        "pipeline.company_master.silver_ok",
        nse_rows=nse_equity.height,
        bse_rows=bse_scrips.height,
        industry_rows=nse_industry.height if nse_industry is not None else 0,
    )

    # 3. RESOLVE — mint co_code per unique ISIN across both sources.
    all_isins = (
        nse_equity.select("isin")
        .vstack(bse_scrips.select("isin"))
        .unique()
        .get_column("isin")
        .to_list()
    )
    co_code_map = ensure_companies(settings, all_isins)

    # 4. MERGE + derive name/short-name.
    sn_cfg = load_short_name_config(root)
    merged = cm.merge(nse_equity, bse_scrips, nse_industry, co_code_map, sn_cfg)

    # 5a. Moneycontrol sector source (bulk A-Z directory, ~26 page fetches).
    mc_bronze = MoneycontrolAdapter(settings).fetch(partition=as_of)
    mc_dir = parse_mc_directory(mc_bronze.path)
    write_silver(settings, "mc_directory", as_of, mc_dir)
    log.info("pipeline.company_master.mc_ok", mc_companies=mc_dir.height)

    # 5b. SECTOR waterfall (NSE-index by ISIN > MC exact > MC fuzzy) + MCAP.
    tax = load_sector_taxonomy(root)
    merged = assign_sector(merged, tax, mc_dir)
    merged = assign_mcap_class(merged, root)

    # sector_master.csv (raw_sector, source, mapped_sector, sector_code) + coverage report
    build_sector_master(merged, mc_dir, tax, root / "config" / "sector_master.csv")
    _report_sector_coverage(merged)

    # 6. GOLD projection.
    gold = cm.to_gold(merged)
    gold_path = write_gold(settings, "company_master", as_of, gold)
    log.info("pipeline.company_master.gold_ok", rows=gold.height, path=str(gold_path))

    # 7. VALIDATE (fatal on dup ISIN/co_code/BSECode/NSESymbol/missing ISIN).
    report = validator.validate(gold)
    for w in report.warnings:
        log.warning("pipeline.company_master.warn", detail=w)

    # 8. PERSIST enriched master back to SQLite (keeps co_code stable next run).
    upsert_company_master(settings, gold)

    # 9. EXPORT.
    out_xlsx = _paths.output_path(settings, "company_master", as_of)
    write_company_master_workbook(gold, out_xlsx)
    log.info("pipeline.company_master.export_ok", path=str(out_xlsx), rows=gold.height)
    return out_xlsx
