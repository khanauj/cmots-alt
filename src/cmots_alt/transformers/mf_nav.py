"""Silver MF NAV → gold (CMOTS-shaped) projection.

Gold columns (Phase 1):
    SchemeCode, SchemeName, AMC, SchemeType, Category, SubCategory,
    ISIN_Growth, ISIN_DivReinvestment, NAV, NAVDate
"""

from __future__ import annotations

import polars as pl


_GOLD_COLUMN_ORDER = [
    "SchemeCode",
    "SchemeName",
    "AMC",
    "SchemeType",
    "Category",
    "SubCategory",
    "ISIN_Growth",
    "ISIN_DivReinvestment",
    "NAV",
    "NAVDate",
]


def to_gold(silver: pl.DataFrame) -> pl.DataFrame:
    return (
        silver.select(
            pl.col("scheme_code").alias("SchemeCode"),
            pl.col("scheme_name").alias("SchemeName"),
            pl.col("amc_name").alias("AMC"),
            pl.col("scheme_type").alias("SchemeType"),
            pl.col("scheme_category").alias("Category"),
            pl.col("scheme_subcategory").alias("SubCategory"),
            pl.col("isin_growth").alias("ISIN_Growth"),
            pl.col("isin_div_reinvestment").alias("ISIN_DivReinvestment"),
            pl.col("nav").alias("NAV"),
            pl.col("nav_date").alias("NAVDate"),
        )
        .sort(["AMC", "Category", "SchemeName"])
        .select(_GOLD_COLUMN_ORDER)
    )
