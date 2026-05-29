"""Merge NSE + BSE + industry + mcap into the CMOTS-shaped CompanyMaster gold.

Gold columns (exact CMOTS CompanyMaster order):
    co_code, BSECode, NSESymbol, CompanyName, CompanyShortName, CategoryName,
    isin, BSEGroup, mcaptype, SectorCode, SectorName, BSEListed, NSEListed
"""

from __future__ import annotations

import re

import polars as pl

from .short_name import ShortNameConfig, make_short_name

# Tokens kept upper-cased in CompanyName normalization.
_ALLCAPS_KEEP = {
    "TCS", "ITC", "ONGC", "GAIL", "NTPC", "BPCL", "HPCL", "IOCL", "SBI",
    "ICICI", "HDFC", "IDFC", "IDBI", "PNB", "BOB", "L&T", "M&M", "MRF",
    "NMDC", "SAIL", "NHPC", "REC", "PFC", "IRCTC", "IRFC", "RVNL", "BHEL",
    "MTNL", "BSNL", "DLF", "UPL", "GMR", "GVK", "JSW",
}

_GOLD_COLUMNS = [
    "co_code", "BSECode", "NSESymbol", "CompanyName", "CompanyShortName",
    "CategoryName", "isin", "BSEGroup", "mcaptype", "SectorCode", "SectorName",
    "SectorConfidence", "BSEListed", "NSEListed",
]


def normalize_company_name(raw: str | None) -> str | None:
    if not raw:
        return None
    tokens = re.split(r"(\s+)", raw.strip())
    out = []
    for t in tokens:
        if not t or t.isspace():
            out.append(t)
        elif t.upper() in _ALLCAPS_KEEP:
            out.append(t.upper())
        elif t.isupper() and len(t) <= 4:
            out.append(t)  # leave short acronyms alone
        else:
            out.append(t[:1].upper() + t[1:].lower() if t[:1].isalpha() else t)
    s = "".join(out)
    s = re.sub(r"\bLIMITED\b", "Ltd", s, flags=re.IGNORECASE)
    s = re.sub(r"\bPRIVATE\b", "Pvt", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip()


def merge(
    nse_equity: pl.DataFrame,
    bse_scrips: pl.DataFrame,
    nse_industry: pl.DataFrame | None,
    co_code_map: pl.DataFrame,
    short_name_cfg: ShortNameConfig,
) -> pl.DataFrame:
    # 1. Full outer join NSE ⨝ BSE on ISIN.
    merged = nse_equity.join(bse_scrips, on="isin", how="full", coalesce=True)

    # 2. Attach industry (dedupe on ISIN first).
    if nse_industry is not None:
        ind = (
            nse_industry.filter(pl.col("isin").is_not_null())
            .select("isin", "nse_industry")
            .unique(subset=["isin"], keep="first")
        )
        merged = merged.join(ind, on="isin", how="left")
    else:
        merged = merged.with_columns(pl.lit(None, dtype=pl.Utf8).alias("nse_industry"))

    # 3. Attach co_code.
    merged = merged.join(co_code_map, on="isin", how="left")

    # 4. CompanyName: prefer BSE legal name, else NSE; then normalize.
    raw_names = [
        bse if bse else nse
        for bse, nse in zip(
            merged.get_column("legal_name_bse").to_list()
            if "legal_name_bse" in merged.columns
            else [None] * merged.height,
            merged.get_column("legal_name_nse").to_list()
            if "legal_name_nse" in merged.columns
            else [None] * merged.height,
        )
    ]
    company_names = [normalize_company_name(n) for n in raw_names]

    # 5. CompanyShortName from the normalized name + override table.
    isins = merged.get_column("isin").to_list()
    short_names = [
        make_short_name(name, short_name_cfg, isin=isin) if name else None
        for name, isin in zip(company_names, isins)
    ]

    merged = merged.with_columns(
        pl.Series("CompanyName", company_names, dtype=pl.Utf8),
        pl.Series("CompanyShortName", short_names, dtype=pl.Utf8),
    )
    return merged


def to_gold(merged_with_sector_mcap: pl.DataFrame) -> pl.DataFrame:
    df = merged_with_sector_mcap
    has = set(df.columns)

    def col_or_null(name: str, dtype: pl.DataType) -> pl.Expr:
        return pl.col(name) if name in has else pl.lit(None, dtype=dtype).alias(name)

    # SectorConfidence: HIGH (nse_index|mc_exact) / MEDIUM (mc_fuzzy) /
    # LOW (NSE↔MC conflict) / UNKNOWN (unresolved). Conflict takes precedence.
    sector_confidence = (
        pl.when(col_or_null("sector_conflict", pl.Boolean).fill_null(False))
        .then(pl.lit("LOW"))
        .when(col_or_null("sector_code", pl.Int64).is_null())
        .then(pl.lit("UNKNOWN"))
        .when(col_or_null("sector_source", pl.Utf8).is_in(["nse_index", "mc_exact"]))
        .then(pl.lit("HIGH"))
        .when(col_or_null("sector_source", pl.Utf8) == "mc_fuzzy")
        .then(pl.lit("MEDIUM"))
        .otherwise(pl.lit("UNKNOWN"))
        .alias("SectorConfidence")
    )

    gold = df.with_columns(
        pl.lit("Company", dtype=pl.Utf8).alias("CategoryName"),
        sector_confidence,
        pl.when(col_or_null("bse_code", pl.Int64).is_not_null())
        .then(pl.lit("Yes")).otherwise(pl.lit("No")).alias("BSEListed"),
        pl.when(col_or_null("nse_symbol", pl.Utf8).is_not_null())
        .then(pl.lit("Yes")).otherwise(pl.lit("No")).alias("NSEListed"),
    ).select(
        pl.col("co_code"),
        col_or_null("bse_code", pl.Int64).alias("BSECode"),
        col_or_null("nse_symbol", pl.Utf8).alias("NSESymbol"),
        pl.col("CompanyName"),
        pl.col("CompanyShortName"),
        pl.col("CategoryName"),
        pl.col("isin"),
        col_or_null("bse_group", pl.Utf8).alias("BSEGroup"),
        col_or_null("mcap_class", pl.Utf8).alias("mcaptype"),
        col_or_null("sector_code", pl.Int64).alias("SectorCode"),
        col_or_null("sector_name", pl.Utf8).alias("SectorName"),
        pl.col("SectorConfidence"),
        pl.col("BSEListed"),
        pl.col("NSEListed"),
    )
    return gold.sort("co_code").select(_GOLD_COLUMNS)
