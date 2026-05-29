"""End-to-end Corporate Actions pipeline:
NSE CA API + BSE Corp.Action announcements → bronze → silver → gold → xlsx.

Events resolve to a stable co_code through the CompanyMaster crosswalk, so a
CompanyMaster run must have populated the company table first.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..core.logging import get_logger
from ..core.settings import Settings, ensure_directories, load_settings
from ..exporters.excel.workbook import write_corporate_actions_workbook
from ..normalizers.corporate_actions import parse_bse_corp_actions, parse_nse_corp_actions
from ..sources.corporate_actions import BseCorpActionsAdapter, NseCorpActionsAdapter
from ..storage import paths as _paths
from ..storage.db import run_migrations
from ..storage.processed import write_gold, write_silver
from ..transformers import corporate_actions as ca_tx
from ..transformers.identity_resolver import load_aliases
from ..transformers.resolver import load_identity_maps
from ..validators import corporate_actions as validator

log = get_logger("pipeline.ca")


def run(as_of: date | None = None, settings: Settings | None = None) -> Path:
    settings = settings or load_settings()
    ensure_directories(settings)
    run_migrations(settings)
    as_of = as_of or date.today()

    log.info("pipeline.ca.start", as_of=as_of.isoformat())

    # 1. INGEST (bronze) — windowed event lists per source.
    nse_ca = NseCorpActionsAdapter(settings).fetch(partition=as_of, lookback_days=90)
    bse_ca = BseCorpActionsAdapter(settings).fetch(partition=as_of, lookback_days=30)
    log.info(
        "pipeline.ca.bronze_ok",
        nse_records=nse_ca.record_count, bse_records=bse_ca.record_count,
        window=f"{nse_ca.from_date.isoformat()}..{as_of.isoformat()}",
    )

    # 2. NORMALIZE → silver (unified event schema per source).
    nse_silver = parse_nse_corp_actions(nse_ca.bronze.path)
    bse_silver = parse_bse_corp_actions(bse_ca.bronze.path)
    write_silver(settings, "ca_nse", as_of, nse_silver)
    write_silver(settings, "ca_bse", as_of, bse_silver)
    log.info("pipeline.ca.silver_ok", nse_rows=nse_silver.height, bse_rows=bse_silver.height)

    # 3. RESOLVE against CompanyMaster (frozen waterfall) + dedupe overlap.
    maps = load_identity_maps(settings)
    if maps.count == 0:
        log.warning("pipeline.ca.no_company_master",
                    detail="company table empty — run 'cmots ingest company-master' first")
    aliases = load_aliases(settings.project_root)
    merged = ca_tx.resolve_and_merge(nse_silver, bse_silver, maps, aliases)

    # 4. GOLD projection.
    gold = ca_tx.to_gold(merged)
    gold_path = write_gold(settings, "corporate_actions", as_of, gold)
    log.info("pipeline.ca.gold_ok", rows=gold.height, path=str(gold_path))

    # 5. VALIDATE (fatal on duplicate events; warns on missing co_code / ratio / dates).
    report = validator.validate(gold, as_of)
    for w in report.warnings:
        log.warning("pipeline.ca.warn", detail=w)
    log.info(
        "pipeline.ca.coverage",
        rows=report.rows, resolved=report.resolved, coverage_pct=report.coverage_pct,
        malformed_ratio=report.malformed_ratio, invalid_dates=report.invalid_dates,
    )

    # 6. EXPORT.
    out_xlsx = _paths.output_path(settings, "corporate_actions", as_of)
    write_corporate_actions_workbook(gold, out_xlsx)
    log.info("pipeline.ca.export_ok", path=str(out_xlsx), rows=gold.height)
    return out_xlsx
