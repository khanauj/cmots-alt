"""End-to-end Shareholding pipeline:
NSE shareholding master (+ per-company XBRL detail) → bronze → silver → gold → xlsx.

The bulk master supplies promoter/public % for every company; the XBRL detail
(institutions, FII/DII, government, non-institutions, shareholder count) is fetched
for a bounded set of resolved companies (xbrl_limit) to keep the run end-to-end.
BSE shareholding has no public JSON endpoint and currently contributes 0 rows; the
merge/dedup is wired to accept it once configured.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..core.logging import get_logger
from ..core.settings import Settings, ensure_directories, load_settings
from ..exporters.excel.workbook import write_shareholding_workbook
from ..normalizers.shareholding import enrich_with_xbrl, parse_shp_master, parse_shp_xbrl
from ..sources.shareholding import BseShareholdingAdapter, NseShareholdingAdapter
from ..storage import paths as _paths
from ..storage.db import run_migrations
from ..storage.processed import write_gold, write_silver
from ..transformers import shareholding as shp_tx
from ..transformers.identity_resolver import load_aliases
from ..transformers.resolver import load_identity_maps

log = get_logger("pipeline.shp")


def run(as_of: date | None = None, settings: Settings | None = None, xbrl_limit: int = 120) -> Path:
    settings = settings or load_settings()
    ensure_directories(settings)
    run_migrations(settings)
    as_of = as_of or date.today()

    log.info("pipeline.shp.start", as_of=as_of.isoformat(), xbrl_limit=xbrl_limit)

    maps = load_identity_maps(settings)
    if maps.count == 0:
        log.warning("pipeline.shp.no_company_master",
                    detail="company table empty — run 'cmots ingest company-master' first")
    aliases = load_aliases(settings.project_root)

    # 1. INGEST master (bronze) + parse base silver.
    nse = NseShareholdingAdapter(settings)
    master = nse.fetch_master(partition=as_of)
    nse_silver, xbrl_urls = parse_shp_master(master.records)

    # 2. ENRICH a bounded set of resolved companies from their XBRL, prioritising
    #    larger companies (by mcap_class) so marquee names get the full breakdown.
    mcap_rank = _mcap_rank_by_symbol(settings)
    candidates = [
        s for s in nse_silver.get_column("nse_symbol").to_list()
        if s and s.upper() in maps.by_nse_symbol and s in xbrl_urls
    ]
    candidates.sort(key=lambda s: (mcap_rank.get(s.upper(), 99), s))
    priority = candidates[:xbrl_limit]
    detail_by_symbol: dict[str, dict] = {}
    for sym in priority:
        text = nse.fetch_xbrl(xbrl_urls[sym])
        if text:
            detail = parse_shp_xbrl(text)
            if detail:
                detail_by_symbol[sym] = detail
    nse_silver = enrich_with_xbrl(nse_silver, detail_by_symbol)
    log.info("pipeline.shp.enriched", attempted=len(priority), enriched=len(detail_by_symbol))

    # BSE (best-effort; currently empty) → same silver schema.
    BseShareholdingAdapter(settings).fetch(partition=as_of)
    bse_silver = nse_silver.head(0)

    write_silver(settings, "shp_nse", as_of, nse_silver)
    write_silver(settings, "shp_bse", as_of, bse_silver)
    log.info("pipeline.shp.silver_ok", nse_rows=nse_silver.height, bse_rows=bse_silver.height)

    # 3. RESOLVE + dedupe quarter-wise.
    merged = shp_tx.resolve_and_merge(nse_silver, bse_silver, maps, aliases)

    # 4. GOLD.
    gold = shp_tx.to_gold(merged)
    gold_path = write_gold(settings, "shareholding", as_of, gold)
    log.info("pipeline.shp.gold_ok", rows=gold.height, path=str(gold_path))

    # 5. VALIDATE.
    report = validate_and_log(gold)

    # 6. EXPORT.
    out_xlsx = _paths.output_path(settings, "shareholding", as_of)
    write_shareholding_workbook(gold, out_xlsx)
    log.info("pipeline.shp.export_ok", path=str(out_xlsx), rows=gold.height,
             coverage_pct=report.coverage_pct, xbrl_enriched=report.xbrl_enriched)
    return out_xlsx


def validate_and_log(gold):
    from ..validators import shareholding as validator
    report = validator.validate(gold)
    for w in report.warnings:
        log.warning("pipeline.shp.warn", detail=w)
    return report


def _mcap_rank_by_symbol(settings: Settings) -> dict[str, int]:
    """NSE symbol (upper) -> mcap priority (Largecap=0, Midcap=1, Smallcap=2)."""
    from ..storage.db import get_db
    rank = {"Large Cap": 0, "Mid Cap": 1, "Small Cap": 2, "Micro Cap": 3}
    out: dict[str, int] = {}
    with get_db(settings) as conn:
        for r in conn.execute(
            "SELECT nse_symbol, mcap_class FROM company WHERE nse_symbol IS NOT NULL"
        ):
            out[r["nse_symbol"].upper()] = rank.get(r["mcap_class"], 50)
    return out
