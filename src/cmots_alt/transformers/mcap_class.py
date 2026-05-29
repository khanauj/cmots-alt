"""Market-cap classification (Large/Mid/Small/Micro).

Source of truth: AMFI's half-yearly stock categorization list. AMFI publishes
it as an XLSX behind an HTML page; for Phase 1 we read it from a local file if
present (drop the downloaded sheet at config/amfi_mcap.csv or .xlsx). When the
file is absent, mcap_class is left null — the column still appears in output.

Expected columns in the reference file (case-insensitive):
  - ISIN
  - Classification  (values containing 'Large' / 'Mid' / 'Small')
or, if only ranks are present:
  - ISIN, Rank      (rank 1-100 Large, 101-250 Mid, 251-500 Small, >500 Micro)
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from ..core.logging import get_logger

log = get_logger("transform.mcap")


def _find_reference(project_root: Path) -> Path | None:
    for name in ("amfi_mcap.csv", "amfi_mcap.xlsx"):
        p = project_root / "config" / name
        if p.exists():
            return p
    return None


def _load_reference(path: Path) -> pl.DataFrame:
    if path.suffix.lower() == ".xlsx":
        df = pl.read_excel(path)
    else:
        df = pl.read_csv(path, infer_schema_length=0)
    df = df.rename({c: c.strip().lower() for c in df.columns})

    isin_col = next((c for c in df.columns if "isin" in c), None)
    if isin_col is None:
        raise ValueError(f"AMFI mcap reference has no ISIN column: {df.columns}")

    class_col = next((c for c in df.columns if "class" in c or "category" in c), None)
    rank_col = next((c for c in df.columns if "rank" in c), None)

    out = df.select(
        pl.col(isin_col).str.strip_chars().str.to_uppercase().alias("isin")
    )
    if class_col is not None:
        out = out.with_columns(
            pl.when(df[class_col].str.contains("(?i)large")).then(pl.lit("Large Cap"))
            .when(df[class_col].str.contains("(?i)mid")).then(pl.lit("Mid Cap"))
            .when(df[class_col].str.contains("(?i)small")).then(pl.lit("Small Cap"))
            .when(df[class_col].str.contains("(?i)micro")).then(pl.lit("Micro Cap"))
            .otherwise(None)
            .alias("mcap_class")
        )
    elif rank_col is not None:
        rank = df[rank_col].cast(pl.Int64, strict=False)
        out = out.with_columns(
            pl.when(rank <= 100).then(pl.lit("Large Cap"))
            .when(rank <= 250).then(pl.lit("Mid Cap"))
            .when(rank <= 500).then(pl.lit("Small Cap"))
            .when(rank.is_not_null()).then(pl.lit("Micro Cap"))
            .otherwise(None)
            .alias("mcap_class")
        )
    else:
        raise ValueError("AMFI mcap reference has neither Classification nor Rank column")
    return out.filter(pl.col("isin").str.len_chars() == 12).unique(subset=["isin"])


def _rank_by_market_cap(df: pl.DataFrame) -> pl.DataFrame:
    """AMFI-style cutoffs applied to point-in-time market cap.

    AMFI ranks by 6-month average full mcap (top 100 Large / 101-250 Mid /
    251+ Small). We approximate with the BSE-supplied market cap and add a
    Micro tier beyond rank 500. Documented divergence from AMFI: point-in-time
    vs 6-month average.
    """
    ranked = df.with_columns(
        pl.col("mktcap").rank(method="ordinal", descending=True).alias("_mcap_rank")
    )
    return ranked.with_columns(
        pl.when(pl.col("mktcap").is_null()).then(None)
        .when(pl.col("_mcap_rank") <= 100).then(pl.lit("Large Cap"))
        .when(pl.col("_mcap_rank") <= 250).then(pl.lit("Mid Cap"))
        .when(pl.col("_mcap_rank") <= 500).then(pl.lit("Small Cap"))
        .otherwise(pl.lit("Micro Cap"))
        .alias("mcap_class")
    ).drop("_mcap_rank")


def assign_mcap_class(df: pl.DataFrame, project_root: Path) -> pl.DataFrame:
    ref_path = _find_reference(project_root)
    if ref_path is not None:
        try:
            ref = _load_reference(ref_path)
            log.info("mcap.reference_loaded", path=str(ref_path), rows=ref.height)
            return df.join(ref, on="isin", how="left")
        except Exception as e:  # malformed file shouldn't kill the pipeline
            log.warning("mcap.reference_unreadable", path=str(ref_path), err=str(e))

    # No AMFI file → derive from market cap if we have it (BSE supplies Mktcap).
    if "mktcap" in df.columns and df.get_column("mktcap").drop_nulls().len() > 0:
        log.info("mcap.derived_from_market_cap", method="bse_mktcap_rank")
        return _rank_by_market_cap(df)

    log.warning("mcap.unavailable", hint="no AMFI file and no market cap column")
    return df.with_columns(pl.lit(None, dtype=pl.Utf8).alias("mcap_class"))
