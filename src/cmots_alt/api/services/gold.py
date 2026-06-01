"""Gold-output access.

Reads ONLY the latest gold parquet partition per domain, via Polars lazy scans:
projection + predicates are pushed into the parquet read, and we filter before
`collect()` so the full file is never loaded. No SQLite. Functions are sync
(Polars is blocking) and called from the async routes through run_in_threadpool.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import polars as pl

from ...core.settings import Settings, load_settings

_DT_RE = re.compile(r"dt=(\d{4}-\d{2}-\d{2})\.parquet$")


# ── partition discovery ──────────────────────────────────────────────────────
def gold_domain_dir(domain: str, settings: Settings | None = None) -> Path:
    settings = settings or load_settings()
    return settings.resolve(settings.paths.storage.gold) / domain


def latest_partition(domain: str, settings: Settings | None = None) -> str | None:
    d = gold_domain_dir(domain, settings)
    if not d.exists():
        return None
    dates = [m.group(1) for p in d.glob("dt=*.parquet") if (m := _DT_RE.search(p.name))]
    return max(dates) if dates else None


def is_available(domain: str, settings: Settings | None = None) -> bool:
    return latest_partition(domain, settings) is not None


def _scan(domain: str, settings: Settings | None = None) -> pl.LazyFrame | None:
    """Lazy scan of the latest partition; None if the domain has no gold output."""
    part = latest_partition(domain, settings)
    if part is None:
        return None
    return pl.scan_parquet(gold_domain_dir(domain, settings) / f"dt={part}.parquet")


def _scan_all(domain: str, settings: Settings | None = None) -> pl.LazyFrame | None:
    """Lazy scan across ALL partitions of a domain (for time-series like EOD prices).

    Each partition holds one trading day; walk-back can make adjacent partitions
    repeat a day, so callers must dedupe on the natural key after scanning.
    """
    d = gold_domain_dir(domain, settings)
    if not d.exists():
        return None
    files = sorted(str(p) for p in d.glob("dt=*.parquet"))
    return pl.scan_parquet(files) if files else None


# ── column projections (gold PascalCase -> response snake_case) ───────────────
_STOCK = [
    pl.col("co_code"),
    pl.col("isin"),
    pl.col("NSESymbol").alias("nse_symbol"),
    pl.col("BSECode").alias("bse_code"),
    pl.col("CompanyName").alias("company_name"),
    pl.col("SectorName").alias("sector_name"),
    pl.col("mcaptype").alias("mcap_class"),
]
_STOCK_DETAIL = _STOCK + [
    pl.col("CompanyShortName").alias("company_short_name"),
    pl.col("SectorCode").alias("sector_code"),
    pl.col("SectorConfidence").alias("sector_confidence"),
    pl.col("BSEGroup").alias("bse_group"),
    (pl.col("NSEListed") == "Yes").alias("nse_listed"),
    (pl.col("BSEListed") == "Yes").alias("bse_listed"),
]
_PRICE = [
    pl.col("TradeDate").alias("trade_date"), pl.col("Exchange").alias("exchange"),
    pl.col("Open").alias("open"), pl.col("High").alias("high"),
    pl.col("Low").alias("low"), pl.col("Close").alias("close"),
    pl.col("PrevClose").alias("prev_close"), pl.col("VWAP").alias("vwap"),
    pl.col("TotalVolume").alias("total_volume"), pl.col("TotalTurnover").alias("total_turnover"),
    pl.col("DeliverableQty").alias("deliverable_qty"),
    pl.col("DeliverablePercent").alias("deliverable_percent"),
    pl.col("NoOfTrades").alias("no_of_trades"),
]
_SHP = [
    pl.col("QuarterEnd").alias("quarter_end"),
    pl.col("PromoterPct").alias("promoter_pct"), pl.col("PublicPct").alias("public_pct"),
    pl.col("DIIPct").alias("dii_pct"), pl.col("FIIPct").alias("fii_pct"),
    pl.col("GovtPct").alias("govt_pct"), pl.col("InstitutionPct").alias("institution_pct"),
    pl.col("NonInstitutionPct").alias("non_institution_pct"),
    pl.col("PledgedPct").alias("pledged_pct"),
    pl.col("NumberOfShareholders").alias("number_of_shareholders"),
]
_CA = [
    pl.col("ActionType").alias("action_type"),
    pl.col("AnnouncementDate").alias("announcement_date"),
    pl.col("ExDate").alias("ex_date"), pl.col("RecordDate").alias("record_date"),
    pl.col("Description").alias("description"),
    pl.col("RatioNumerator").alias("ratio_numerator"),
    pl.col("RatioDenominator").alias("ratio_denominator"),
    pl.col("OldFaceValue").alias("old_face_value"),
    pl.col("NewFaceValue").alias("new_face_value"),
    pl.col("Exchange").alias("exchange"), pl.col("Source").alias("source"),
]

_MF_LIST = [
    pl.col("SchemeCode").alias("scheme_code"),
    pl.col("SchemeName").alias("scheme_name"),
    pl.col("AMCName").alias("amc_name"),
    pl.col("Category").alias("category"),
]
_MF_DETAIL = _MF_LIST + [
    pl.col("ISIN").alias("isin"),
    pl.col("LaunchDate").alias("launch_date"),
    pl.col("ClosureDate").alias("closure_date"),
    pl.col("ExpenseRatio").alias("expense_ratio"),
    pl.col("AUM").alias("aum"),
    pl.col("FundManager").alias("fund_manager"),
    pl.col("Status").alias("status"),
]
_NAV = [
    pl.col("NAVDate").alias("nav_date"),
    pl.col("NAV").alias("nav"),
]
_HOLDING = [
    pl.col("HoldingName").alias("holding_name"),
    pl.col("HoldingISIN").alias("holding_isin"),
    pl.col("co_code"),
    pl.col("InstrumentType").alias("instrument_type"),
    pl.col("WeightPct").alias("weight_pct"),
    pl.col("Quantity").alias("quantity"),
    pl.col("MarketValue").alias("market_value"),
    pl.col("Sector").alias("sector"),
    pl.col("CreditRating").alias("credit_rating"),
    pl.col("QuarterEnd").alias("quarter_end"),
]


# ── queries ──────────────────────────────────────────────────────────────────
def list_stocks(search: str | None, sector: str | None, limit: int, offset: int,
                settings: Settings | None = None) -> list[dict]:
    lf = _scan("company_master", settings)
    if lf is None:
        return []
    lf = lf.select(_STOCK)
    if search:
        s = search.lower()
        lf = lf.filter(
            pl.col("company_name").str.to_lowercase().str.contains(s, literal=True).fill_null(False)
            | pl.col("nse_symbol").str.to_lowercase().str.contains(s, literal=True).fill_null(False)
        )
    if sector:
        lf = lf.filter(
            pl.col("sector_name").str.to_lowercase().str.contains(sector.lower(), literal=True)
            .fill_null(False)
        )
    return lf.sort("co_code").slice(offset, limit).collect().to_dicts()


def get_stock(symbol: str, settings: Settings | None = None) -> dict | None:
    lf = _scan("company_master", settings)
    if lf is None:
        return None
    rows = (
        lf.select(_STOCK_DETAIL)
        .filter(pl.col("nse_symbol").str.to_uppercase() == symbol.upper())
        .collect().to_dicts()
    )
    return rows[0] if rows else None


def resolve_co_code(symbol: str, settings: Settings | None = None) -> int | None:
    lf = _scan("company_master", settings)
    if lf is None:
        return None
    out = (
        lf.select(pl.col("co_code"), pl.col("NSESymbol"))
        .filter(pl.col("NSESymbol").str.to_uppercase() == symbol.upper())
        .select("co_code").collect()
    )
    return int(out["co_code"][0]) if out.height else None


def prices(co_code: int, exchange: str | None, from_date: date | None, to_date: date | None,
           limit: int, settings: Settings | None = None) -> list[dict]:
    lf = _scan_all("equity_eod", settings)
    if lf is None:
        return []
    lf = lf.filter(pl.col("co_code") == co_code)
    if exchange:
        lf = lf.filter(pl.col("Exchange") == exchange.upper())
    if from_date:
        lf = lf.filter(pl.col("TradeDate") >= from_date)
    if to_date:
        lf = lf.filter(pl.col("TradeDate") <= to_date)
    # Partitions can repeat a trading day (walk-back); collapse on the natural key.
    lf = lf.unique(subset=["co_code", "TradeDate", "Exchange"], keep="first")
    return lf.select(_PRICE).sort("trade_date", descending=True).limit(limit).collect().to_dicts()


def shareholding(co_code: int, settings: Settings | None = None) -> list[dict]:
    lf = _scan("shareholding", settings)
    if lf is None:
        return []
    return (
        lf.filter(pl.col("co_code") == co_code)
        .select(_SHP).sort("quarter_end", descending=True).collect().to_dicts()
    )


def corporate_actions(co_code: int, action_type: str | None,
                      settings: Settings | None = None) -> list[dict]:
    lf = _scan("corporate_actions", settings)
    if lf is None:
        return []
    lf = lf.filter(pl.col("co_code") == co_code)
    if action_type:
        lf = lf.filter(pl.col("ActionType") == action_type.upper())
    return (
        lf.select(_CA)
        .sort(["ex_date", "announcement_date"], descending=True, nulls_last=True)
        .collect().to_dicts()
    )


# ── mutual fund queries ───────────────────────────────────────────────────────
def list_mutual_funds(
    search: str | None, amc: str | None, category: str | None,
    limit: int, offset: int, settings: Settings | None = None,
) -> list[dict]:
    lf = _scan("mf_scheme_master", settings)
    if lf is None:
        return []
    lf = lf.select(_MF_LIST)
    if search:
        s = search.lower()
        lf = lf.filter(
            pl.col("scheme_name").str.to_lowercase().str.contains(s, literal=True).fill_null(False)
        )
    if amc:
        lf = lf.filter(
            pl.col("amc_name").str.to_lowercase().str.contains(amc.lower(), literal=True)
            .fill_null(False)
        )
    if category:
        lf = lf.filter(
            pl.col("category").str.to_lowercase().str.contains(category.lower(), literal=True)
            .fill_null(False)
        )
    return lf.sort("scheme_code").slice(offset, limit).collect().to_dicts()


def get_mutual_fund(scheme_code: int, settings: Settings | None = None) -> dict | None:
    lf = _scan("mf_scheme_master", settings)
    if lf is None:
        return None
    rows = (
        lf.filter(pl.col("SchemeCode") == scheme_code)
        .select(_MF_DETAIL)
        .collect().to_dicts()
    )
    return rows[0] if rows else None


def mf_nav(
    scheme_code: int, from_date: date | None, to_date: date | None,
    limit: int, settings: Settings | None = None,
) -> list[dict]:
    lf = _scan("mf_nav", settings)
    if lf is None:
        return []
    lf = lf.filter(pl.col("SchemeCode") == scheme_code)
    if from_date:
        lf = lf.filter(pl.col("NAVDate") >= from_date)
    if to_date:
        lf = lf.filter(pl.col("NAVDate") <= to_date)
    return lf.select(_NAV).sort("nav_date", descending=True).limit(limit).collect().to_dicts()


def mf_holdings(
    scheme_code: int, instrument_type: str | None,
    limit: int | None = None, settings: Settings | None = None,
) -> list[dict]:
    lf = _scan("mf_holdings", settings)
    if lf is None:
        return []
    lf = lf.filter(pl.col("SchemeCode") == scheme_code)
    if instrument_type:
        lf = lf.filter(pl.col("InstrumentType") == instrument_type.upper())
    lf = lf.select(_HOLDING).sort("weight_pct", descending=True, nulls_last=True)
    if limit is not None:
        lf = lf.limit(limit)
    return lf.collect().to_dicts()
