"""Shareholding transform: resolve each filing to a stable co_code through the
frozen CompanyMaster waterfall (exact + safe symbol-fuzzy, never minted), tag
InstrumentType, deduplicate NSE/BSE overlap quarter-by-quarter, and project to gold.

The dataset is quarter-aware: the key is (co_code, QuarterEnd); historical quarters
for the same company are distinct rows. When both exchanges report the same
(co_code, QuarterEnd) the structured NSE filing wins; Source records the origin.
"""

from __future__ import annotations

import polars as pl

from ..core.logging import get_logger
from .identity_resolver import Alias, resolve_frame
from .resolver import IdentityMaps

log = get_logger("transform.shp")

_GOLD_COLUMNS = [
    "co_code", "BSECode", "NSESymbol", "isin", "QuarterEnd",
    "PromoterPct", "PromoterGroupPct", "PublicPct", "DIIPct", "FIIPct", "GovtPct",
    "NonInstitutionPct", "InstitutionPct", "PledgedPct", "NumberOfShareholders",
    "Exchange", "Source", "InstrumentType",
]


def _dedupe_overlap(df: pl.DataFrame) -> pl.DataFrame:
    """One row per (co_code, QuarterEnd), preferring NSE. Unresolved rows kept."""
    keyed = df.filter(pl.col("co_code").is_not_null() & pl.col("quarter_end").is_not_null())
    rest = df.filter(pl.col("co_code").is_null() | pl.col("quarter_end").is_null())
    keyed = (
        keyed.with_columns((pl.col("exchange") != "NSE").alias("_nse_first"))
        .sort("_nse_first")
        .unique(subset=["co_code", "quarter_end"], keep="first")
        .drop("_nse_first")
    )
    return pl.concat([keyed, rest], how="vertical")


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
    combined = combined.sort(["co_code", "quarter_end"], nulls_last=True)
    log.info(
        "shp.merged",
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
        pl.col("quarter_end").alias("QuarterEnd"),
        pl.col("promoter_pct").alias("PromoterPct"),
        pl.col("promoter_group_pct").alias("PromoterGroupPct"),
        pl.col("public_pct").alias("PublicPct"),
        pl.col("dii_pct").alias("DIIPct"),
        pl.col("fii_pct").alias("FIIPct"),
        pl.col("govt_pct").alias("GovtPct"),
        pl.col("non_institution_pct").alias("NonInstitutionPct"),
        pl.col("institution_pct").alias("InstitutionPct"),
        pl.col("pledged_pct").alias("PledgedPct"),
        pl.col("number_of_shareholders").alias("NumberOfShareholders"),
        pl.col("exchange").alias("Exchange"),
        pl.col("source").alias("Source"),
        pl.col("instrument_type").alias("InstrumentType"),
    ).select(_GOLD_COLUMNS)
