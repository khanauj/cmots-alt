"""Silver → gold projection and identifier resolution for MF Holdings.

Resolves equity holding ISIN to a stable co_code in CompanyMaster.
"""

from __future__ import annotations

from datetime import date
import polars as pl

from ..core.logging import get_logger
from ..core.settings import Settings
from ..transformers.resolver import load_identity_maps

log = get_logger("transform.mf_holdings")

GOLD_COLUMNS = [
    "SchemeCode",
    "SchemeName",
    "AMCName",
    "HoldingName",
    "HoldingISIN",
    "co_code",
    "WeightPct",
    "Quantity",
    "MarketValue",
    "Sector",
    "CreditRating",
    "InstrumentType",
    "QuarterEnd",
    "Source",
]


def to_gold(silver: pl.DataFrame, as_of: date, settings: Settings) -> pl.DataFrame:
    """Project silver holdings into gold shape and resolve co_code for equity holdings.

    Applies exact ISIN lookup to resolve co_code for EQUITY rows only.
    """
    log.info("transform.mf_holdings.start", silver_rows=silver.height)

    if silver.height == 0:
        return pl.DataFrame([], schema={
            "SchemeCode": pl.Int64,
            "SchemeName": pl.Utf8,
            "AMCName": pl.Utf8,
            "HoldingName": pl.Utf8,
            "HoldingISIN": pl.Utf8,
            "co_code": pl.Int64,
            "WeightPct": pl.Float64,
            "Quantity": pl.Float64,
            "MarketValue": pl.Float64,
            "Sector": pl.Utf8,
            "CreditRating": pl.Utf8,
            "InstrumentType": pl.Utf8,
            "QuarterEnd": pl.Date,
            "Source": pl.Utf8,
        })

    # Load resolver identities
    maps = load_identity_maps(settings)

    # Build ISIN lookup frame
    isin_co_map = {isin: ident.co_code for isin, ident in maps.by_isin.items()}
    isin_df = pl.DataFrame({
        "HoldingISIN": list(isin_co_map.keys()),
        "resolved_co_code": list(isin_co_map.values())
    }, schema={"HoldingISIN": pl.Utf8, "resolved_co_code": pl.Int64})

    # Project direct mappings
    gold = silver.select(
        pl.col("scheme_code").alias("SchemeCode"),
        pl.col("scheme_name").alias("SchemeName"),
        pl.col("amc_name").alias("AMCName"),
        pl.col("holding_name").alias("HoldingName"),
        pl.col("holding_isin").alias("HoldingISIN"),
        pl.col("weight_pct").alias("WeightPct"),
        pl.col("quantity").alias("Quantity"),
        pl.col("market_value").alias("MarketValue"),
        pl.col("sector").alias("Sector"),
        pl.col("credit_rating").alias("CreditRating"),
        pl.col("instrument_type").alias("InstrumentType"),
        pl.col("quarter_end").alias("QuarterEnd"),
        pl.col("source").alias("Source"),
    )

    # Join exact ISIN mapping
    gold = gold.join(isin_df, on="HoldingISIN", how="left")

    # Gate resolution to EQUITY only: other classes get null
    gold = gold.with_columns(
        pl.when(pl.col("InstrumentType") == "EQUITY")
        .then(pl.col("resolved_co_code"))
        .otherwise(pl.lit(None).cast(pl.Int64))
        .alias("co_code")
    )

    # Select columns in authoritative contract order
    gold = gold.select(GOLD_COLUMNS)

    resolved_count = gold.filter(pl.col("co_code").is_not_null()).height
    equity_count = gold.filter(pl.col("InstrumentType") == "EQUITY").height

    log.info(
        "transform.mf_holdings.done",
        gold_rows=gold.height,
        resolved_equities=resolved_count,
        total_equities=equity_count,
    )
    return gold
