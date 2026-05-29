"""Equity EOD transform: resolve each bhavcopy row to a stable co_code via the
hardened CompanyMaster waterfall (see identity_resolver), union the two
exchanges, dedupe, and project to gold.

Dedup ("intelligently"): a company can surface multiple rows per exchange
(e.g. an NSE symbol traded in both EQ and BE series). We keep one row per
(co_code, exchange), preferring the most-liquid (highest volume) row. Rows that
fail to resolve keep a null co_code and are reported, never minted.

Both exchanges' rows are preserved (one per co_code per exchange); the output is
ordered NSE-first so the NSE quote is the primary line when a name is dual-listed.
"""

from __future__ import annotations

import polars as pl

from ..core.logging import get_logger
from .identity_resolver import Alias, resolve_frame
from .resolver import IdentityMaps

log = get_logger("transform.eod")

_GOLD_COLUMNS = [
    "co_code", "BSECode", "NSESymbol", "isin", "TradeDate",
    "Open", "High", "Low", "Close", "PrevClose", "LastPrice", "VWAP",
    "TotalVolume", "TotalTurnover", "DeliverableQty", "DeliverablePercent",
    "NoOfTrades", "Series", "Exchange", "InstrumentType",
]


def _dedupe(df: pl.DataFrame) -> pl.DataFrame:
    """One row per (co_code, exchange), keeping the most-liquid. Null co_code kept as-is."""
    resolved = df.filter(pl.col("co_code").is_not_null())
    unresolved = df.filter(pl.col("co_code").is_null())
    resolved = (
        resolved.sort("total_volume", descending=True, nulls_last=True)
        .unique(subset=["co_code", "exchange"], keep="first")
    )
    return pl.concat([resolved, unresolved], how="vertical")


def resolve_and_merge(
    nse_silver: pl.DataFrame,
    bse_silver: pl.DataFrame,
    maps: IdentityMaps,
    aliases: dict[str, Alias],
) -> pl.DataFrame:
    combined = pl.concat([nse_silver, bse_silver], how="vertical")
    combined = resolve_frame(combined, maps, aliases)
    combined = _dedupe(combined)
    # NSE-first ordering, then by co_code (unresolved rows sink to the bottom).
    combined = combined.with_columns(
        (pl.col("exchange") != "NSE").alias("_nse_first")
    ).sort(["co_code", "_nse_first"], nulls_last=True).drop("_nse_first")
    log.info(
        "eod.merged",
        total=combined.height,
        resolved=combined.filter(pl.col("co_code").is_not_null()).height,
        nse=combined.filter(pl.col("exchange") == "NSE").height,
        bse=combined.filter(pl.col("exchange") == "BSE").height,
    )
    return combined


def to_gold(df: pl.DataFrame) -> pl.DataFrame:
    return df.select(
        pl.col("co_code"),
        pl.col("bse_code").alias("BSECode"),
        pl.col("nse_symbol").alias("NSESymbol"),
        pl.col("isin"),
        pl.col("trade_date").alias("TradeDate"),
        pl.col("open").alias("Open"),
        pl.col("high").alias("High"),
        pl.col("low").alias("Low"),
        pl.col("close").alias("Close"),
        pl.col("prev_close").alias("PrevClose"),
        pl.col("last_price").alias("LastPrice"),
        pl.col("vwap").alias("VWAP"),
        pl.col("total_volume").alias("TotalVolume"),
        pl.col("total_turnover").alias("TotalTurnover"),
        pl.col("deliverable_qty").alias("DeliverableQty"),
        pl.col("deliverable_percent").alias("DeliverablePercent"),
        pl.col("no_of_trades").alias("NoOfTrades"),
        pl.col("series").alias("Series"),
        pl.col("exchange").alias("Exchange"),
        pl.col("instrument_type").alias("InstrumentType"),
    ).select(_GOLD_COLUMNS)
