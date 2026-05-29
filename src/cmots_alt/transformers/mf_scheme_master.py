"""Silver → gold projection for MF Scheme Master.

Gold columns (21 total):
    SchemeCode, ISIN, SchemeName, AMCName, FundHouse, Category, SubCategory,
    PlanType, OptionType, Benchmark, RiskLevel, FundType, OpenEnded, CloseEnded,
    ETF, LaunchDate, ClosureDate, ExpenseRatio, AUM, FundManager, Status

Phase 1 scaffold: maps direct fields from silver, stubs derived/enrichment
fields with UNKNOWN / null / defaults.
"""

from __future__ import annotations

from datetime import date

import polars as pl

from ..core.logging import get_logger

log = get_logger("transform.mf_scheme_master")

# ---------------------------------------------------------------------------
# Gold column order — the authoritative contract
# ---------------------------------------------------------------------------

GOLD_COLUMNS: list[str] = [
    "SchemeCode",
    "ISIN",
    "SchemeName",
    "AMCName",
    "FundHouse",
    "Category",
    "SubCategory",
    "PlanType",
    "OptionType",
    "Benchmark",
    "RiskLevel",
    "FundType",
    "OpenEnded",
    "CloseEnded",
    "ETF",
    "LaunchDate",
    "ClosureDate",
    "ExpenseRatio",
    "AUM",
    "FundManager",
    "Status",
]


def to_gold(silver: pl.DataFrame, as_of: date) -> pl.DataFrame:
    """Project silver MF NAV rows into the gold MF Scheme Master shape.

    Parameters
    ----------
    silver:
        Output of ``normalizers.mf_nav.parse_navall_file``.
    as_of:
        Pipeline partition date (used for status derivation in Step 3).
    """
    _ = as_of

    log.info("transform.mf_scheme_master.start", silver_rows=silver.height)

    # 1. Project fields with basic mappings and derivations.
    gold = silver.select(
        # --- Direct mappings from silver ---
        pl.col("scheme_code").alias("SchemeCode"),
        pl.col("isin_growth").alias("ISIN"),
        pl.col("scheme_name").alias("SchemeName"),
        pl.col("amc_name").alias("AMCName"),
        pl.col("amc_name").alias("FundHouse"),
        pl.col("scheme_category").alias("Category"),
        pl.col("scheme_subcategory").alias("SubCategory"),
        # --- Derived PlanType ---
        pl.when(
            pl.col("scheme_name").str.to_lowercase().str.contains(r"direct plan|directplan|\b(direct|dir)\b")
        ).then(pl.lit("DIRECT"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(r"regular plan|regularplan|\b(regular|reg)\b")
        ).then(pl.lit("REGULAR"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(r"institutional|institution|instn|\b(institutional|inst)\b")
        ).then(pl.lit("INSTITUTIONAL"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(r"\bretail\b")
        ).then(pl.lit("RETAIL"))
        .otherwise(pl.lit("UNKNOWN"))
        .alias("PlanType"),
        # --- Derived OptionType ---
        pl.when(
            pl.col("scheme_name").str.to_lowercase().str.contains(
                r"idcw|income distribution cum capital withdrawal|icdw"
            )
        ).then(pl.lit("IDCW"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(
                r"dividend|div payout|\b(div|payout)\b|\-\s*dp\b|\-\s*d\b"
            )
        ).then(pl.lit("DIVIDEND"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(
                r"reinvestment|reinvest|reinv|\breinv\b"
            )
        ).then(pl.lit("REINVESTMENT"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(
                r"\bbonus\b"
            )
        ).then(pl.lit("BONUS"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(
                r"growth|cumulative|\b(growth|gro|gr)\b|\-\s*g\b"
            )
        ).then(pl.lit("GROWTH"))
        .otherwise(pl.lit("UNKNOWN"))
        .alias("OptionType"),
        # --- Enrichment stubs (null in Phase 1) ---
        pl.lit(None).cast(pl.Utf8).alias("Benchmark"),
        pl.lit(None).cast(pl.Utf8).alias("RiskLevel"),
        # --- Fund type from section header ---
        pl.col("scheme_type").alias("FundType"),
        # --- Boolean derivations from scheme_type ---
        (pl.col("scheme_type") == "Open Ended").alias("OpenEnded"),
        (pl.col("scheme_type") == "Close Ended").alias("CloseEnded"),
        # --- ETF detection ---
        pl.col("scheme_name").str.to_lowercase().str.contains(
            r"etf|exchange traded"
        ).alias("ETF"),
        # --- Enrichment stubs (null in Phase 1) ---
        pl.lit(None).cast(pl.Date).alias("LaunchDate"),
        pl.lit(None).cast(pl.Date).alias("ClosureDate"),
        pl.lit(None).cast(pl.Float64).alias("ExpenseRatio"),
        pl.lit(None).cast(pl.Float64).alias("AUM"),
        pl.lit(None).cast(pl.Utf8).alias("FundManager"),
    )

    # 2. Derive Status based on name and ClosureDate
    gold = gold.with_columns(
        pl.when(
            pl.col("SchemeName").str.to_lowercase().str.contains(
                r"\b(closed?|closure|matur(ed|ity)|merg(ed|er)|defunct|discontinued)\b"
            ) | pl.col("ClosureDate").is_not_null()
        ).then(pl.lit("Inactive")).otherwise(pl.lit("Active")).alias("Status")
    )

    gold = gold.sort(["AMCName", "Category", "SchemeName"]).select(GOLD_COLUMNS)

    log.info("transform.mf_scheme_master.done", gold_rows=gold.height)
    return gold
