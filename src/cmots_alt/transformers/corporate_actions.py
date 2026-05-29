"""Corporate-actions transform: resolve each event to a stable co_code through the
frozen CompanyMaster waterfall (exact identifiers + safe symbol-fuzzy; never minted),
tag InstrumentType, deduplicate NSE/BSE overlap, and project to gold.

Unlike Equity EOD (exchange-wise rows preserved), corporate actions are a single
logical event: when the same (co_code, ActionType, ExDate) appears on both
exchanges we keep one row, preferring the structured NSE record. BSE announcements
that carry no ex-date are retained as-is (the announcement is itself the artifact)
with Source = BSE_ANN for traceability.
"""

from __future__ import annotations

import polars as pl

from ..core.logging import get_logger
from .identity_resolver import Alias, resolve_frame
from .resolver import IdentityMaps

log = get_logger("transform.ca")

_GOLD_COLUMNS = [
    "co_code", "BSECode", "NSESymbol", "isin", "ActionType",
    "AnnouncementDate", "ExDate", "RecordDate", "EffectiveDate", "Description",
    "OldFaceValue", "NewFaceValue", "RatioNumerator", "RatioDenominator",
    "Exchange", "Source", "InstrumentType",
]


def _dedupe_overlap(df: pl.DataFrame) -> pl.DataFrame:
    """Collapse the same action seen on both exchanges, always preferring the
    structured NSE record.

    Two passes:
      1. Exact dated-event dedup on (co_code, ActionType, ExDate) for fully-keyed rows.
      2. Cross-source overlap: a BSE announcement whose (co_code, ActionType) already
         appears as an NSE event is dropped (NSE carries ex/record dates + ratio).
    BSE rows with no NSE counterpart, and unresolved rows, are retained with their
    own Source for traceability."""
    # Pass 1 — exact keyed dedup, NSE first.
    keyed = df.filter(pl.col("co_code").is_not_null() & pl.col("ex_date").is_not_null())
    rest = df.filter(pl.col("co_code").is_null() | pl.col("ex_date").is_null())
    keyed = (
        keyed.with_columns((pl.col("exchange") != "NSE").alias("_nse_first"))
        .sort("_nse_first")
        .unique(subset=["co_code", "action_type", "ex_date"], keep="first")
        .drop("_nse_first")
    )
    out = pl.concat([keyed, rest], how="vertical")

    # Pass 2 — drop BSE announcements that overlap an NSE event for the same company.
    nse_keys = (
        out.filter((pl.col("exchange") == "NSE") & pl.col("co_code").is_not_null())
        .select("co_code", "action_type").unique()
    )
    bse_kept = out.filter(pl.col("exchange") == "BSE").join(
        nse_keys, on=["co_code", "action_type"], how="anti"
    )
    return pl.concat([out.filter(pl.col("exchange") == "NSE"), bse_kept], how="vertical")


def resolve_and_merge(
    nse_silver: pl.DataFrame,
    bse_silver: pl.DataFrame,
    maps: IdentityMaps,
    aliases: dict[str, Alias],
) -> pl.DataFrame:
    combined = pl.concat([nse_silver, bse_silver], how="vertical")
    combined = resolve_frame(combined, maps, aliases)
    before = combined.height
    combined = _dedupe_overlap(combined)
    combined = combined.sort(
        ["co_code", "ex_date", "announcement_date"], nulls_last=True
    )
    log.info(
        "ca.merged",
        rows=combined.height,
        deduped=before - combined.height,
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
        pl.col("action_type").alias("ActionType"),
        pl.col("announcement_date").alias("AnnouncementDate"),
        pl.col("ex_date").alias("ExDate"),
        pl.col("record_date").alias("RecordDate"),
        pl.col("effective_date").alias("EffectiveDate"),
        pl.col("description").alias("Description"),
        pl.col("old_face_value").alias("OldFaceValue"),
        pl.col("new_face_value").alias("NewFaceValue"),
        pl.col("ratio_num").alias("RatioNumerator"),
        pl.col("ratio_den").alias("RatioDenominator"),
        pl.col("exchange").alias("Exchange"),
        pl.col("source").alias("Source"),
        pl.col("instrument_type").alias("InstrumentType"),
    ).select(_GOLD_COLUMNS)
