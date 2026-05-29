"""Parse NSE/BSE raw artifacts into canonical silver frames.

Produces three frames keyed on ISIN:
  - nse_equity:   isin, nse_symbol, legal_name_nse, nse_series, listing_date, face_value
  - nse_industry: isin, nse_symbol, nse_industry
  - bse_scrips:   isin, bse_code, legal_name_bse, bse_group, bse_status

All parsers are defensive about column naming because NSE ships whitespace in
headers and BSE distributes the same data across a JSON API and a bhavcopy ZIP
with different field names.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import polars as pl

from ..core.errors import ParseError
from ..core.logging import get_logger

log = get_logger("normalize.company")


# ── helpers ─────────────────────────────────────────────────────────────────
def _clean_columns(df: pl.DataFrame) -> pl.DataFrame:
    return df.rename({c: c.strip() for c in df.columns})


def _col(df: pl.DataFrame, *candidates: str) -> str | None:
    """Return the first column whose normalized name matches a candidate."""
    norm = {c.strip().lower().replace(" ", "").replace("_", ""): c for c in df.columns}
    for cand in candidates:
        key = cand.lower().replace(" ", "").replace("_", "")
        if key in norm:
            return norm[key]
    return None


def _valid_isin(expr: pl.Expr) -> pl.Expr:
    # 12 chars, starts with two letters (IN for India) + alphanumerics.
    return expr.str.strip_chars().str.to_uppercase().str.replace_all(r"\s", "")


# ── NSE EQUITY_L.csv ──────────────────────────────────────────────────────────
def parse_nse_equity_l(path: Path) -> pl.DataFrame:
    df = _clean_columns(pl.read_csv(path, infer_schema_length=0))  # all-str first
    c_sym = _col(df, "SYMBOL")
    c_name = _col(df, "NAME OF COMPANY", "NAMEOFCOMPANY")
    c_series = _col(df, "SERIES")
    c_listing = _col(df, "DATE OF LISTING", "DATEOFLISTING")
    c_isin = _col(df, "ISIN NUMBER", "ISIN", "ISINNUMBER")
    c_fv = _col(df, "FACE VALUE", "FACEVALUE")

    if not (c_sym and c_isin):
        raise ParseError(f"NSE EQUITY_L missing SYMBOL/ISIN columns; got {df.columns}")

    out = df.select(
        _valid_isin(pl.col(c_isin)).alias("isin"),
        pl.col(c_sym).str.strip_chars().alias("nse_symbol"),
        pl.col(c_name).str.strip_chars().alias("legal_name_nse") if c_name
        else pl.lit(None, dtype=pl.Utf8).alias("legal_name_nse"),
        pl.col(c_series).str.strip_chars().alias("nse_series") if c_series
        else pl.lit(None, dtype=pl.Utf8).alias("nse_series"),
        pl.col(c_listing).str.strip_chars().alias("_listing_raw") if c_listing
        else pl.lit(None, dtype=pl.Utf8).alias("_listing_raw"),
        pl.col(c_fv).str.strip_chars().alias("_fv_raw") if c_fv
        else pl.lit(None, dtype=pl.Utf8).alias("_fv_raw"),
    )
    out = out.with_columns(
        pl.col("_listing_raw").str.to_date("%d-%b-%Y", strict=False).alias("listing_date"),
        pl.col("_fv_raw").cast(pl.Float64, strict=False).alias("face_value"),
    ).drop("_listing_raw", "_fv_raw")

    out = out.filter(pl.col("isin").str.len_chars() == 12)
    return out.unique(subset=["isin"], keep="first")


# ── NSE industry classification (primary or Nifty Total Market fallback) ──────
def parse_nse_industry(path: Path) -> pl.DataFrame:
    df = _clean_columns(pl.read_csv(path, infer_schema_length=0))
    c_isin = _col(df, "ISIN Code", "ISIN", "ISIN NUMBER", "ISINCode")
    c_sym = _col(df, "Symbol", "SYMBOL")
    # Prefer the most specific available industry-ish column.
    c_ind = _col(df, "Industry", "Basic Industry", "BasicIndustry", "Sector")

    if c_isin is None and c_sym is None:
        raise ParseError(f"NSE industry file has neither ISIN nor Symbol; got {df.columns}")

    select_exprs = []
    if c_isin:
        select_exprs.append(_valid_isin(pl.col(c_isin)).alias("isin"))
    else:
        select_exprs.append(pl.lit(None, dtype=pl.Utf8).alias("isin"))
    select_exprs.append(
        pl.col(c_sym).str.strip_chars().alias("nse_symbol") if c_sym
        else pl.lit(None, dtype=pl.Utf8).alias("nse_symbol")
    )
    select_exprs.append(
        pl.col(c_ind).str.strip_chars().alias("nse_industry") if c_ind
        else pl.lit(None, dtype=pl.Utf8).alias("nse_industry")
    )
    out = df.select(select_exprs)
    return out


# ── BSE scrips: JSON API or bhavcopy ZIP ──────────────────────────────────────
def _bse_from_json(payload: bytes) -> pl.DataFrame:
    data = json.loads(payload.decode("utf-8"))
    if isinstance(data, dict):
        # Some BSE endpoints wrap the list under a key like "Table".
        for v in data.values():
            if isinstance(v, list):
                data = v
                break
    if not isinstance(data, list) or not data:
        raise ParseError("BSE JSON did not contain a record list")

    def pick(rec: dict, *cands: str) -> str | None:
        norm = {k.lower().replace(" ", "").replace("_", ""): k for k in rec}
        for cand in cands:
            key = cand.lower().replace(" ", "").replace("_", "")
            if key in norm:
                val = rec[norm[key]]
                return str(val).strip() if val is not None else None
        return None

    records = []
    for rec in data:
        if not isinstance(rec, dict):
            continue
        records.append(
            {
                "bse_code_raw": pick(rec, "SCRIP_CD", "ScripCode", "SC_CODE", "Scrip_Cd"),
                "isin": (pick(rec, "ISIN_NUMBER", "ISIN", "ISIN_CODE", "ISINNo") or ""),
                "legal_name_bse": pick(rec, "Scrip_Name", "SC_NAME", "ScripName", "Issuer_Name"),
                "bse_group": pick(rec, "GROUP", "Group", "SC_GROUP"),
                "bse_status": pick(rec, "Status", "STATUS"),
                "mktcap_raw": pick(rec, "Mktcap", "MktCap", "MarketCap"),
            }
        )
    return pl.DataFrame(records)


def _bse_from_bhavcopy_csv(payload: bytes) -> pl.DataFrame:
    """New unified BSE bhavcopy (plain CSV).

    Columns: TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,
             SctySrs,...,FinInstrmNm,...
    For BSE equity: FinInstrmId is the scrip code, SctySrs the group.
    """
    df = _clean_columns(pl.read_csv(io.BytesIO(payload), infer_schema_length=0))
    c_code = _col(df, "FinInstrmId", "SC_CODE", "SC_CD")
    c_name = _col(df, "FinInstrmNm", "SC_NAME")
    c_group = _col(df, "SctySrs", "SC_GROUP")
    c_isin = _col(df, "ISIN", "ISIN_CODE", "ISIN_NUMBER")
    if not (c_code and c_isin):
        raise ParseError(f"BSE bhavcopy missing scrip code/ISIN; got {df.columns}")
    out = df.select(
        pl.col(c_code).str.strip_chars().alias("bse_code_raw"),
        _valid_isin(pl.col(c_isin)).alias("isin"),
        (pl.col(c_name).str.strip_chars() if c_name else pl.lit(None, dtype=pl.Utf8)).alias("legal_name_bse"),
        (pl.col(c_group).str.strip_chars() if c_group else pl.lit(None, dtype=pl.Utf8)).alias("bse_group"),
        pl.lit("Active", dtype=pl.Utf8).alias("bse_status"),
    )
    # Equity segment only: scrip codes are numeric; derivatives carry symbols.
    return out.filter(pl.col("bse_code_raw").str.contains(r"^\d+$"))


def parse_bse_scrips(path: Path, source_kind: str) -> pl.DataFrame:
    payload = path.read_bytes()
    if source_kind == "json_api":
        df = _bse_from_json(payload)
    elif source_kind == "bhavcopy_csv":
        df = _bse_from_bhavcopy_csv(payload)
    else:
        raise ParseError(f"unknown BSE source_kind: {source_kind}")

    if "mktcap_raw" not in df.columns:
        df = df.with_columns(pl.lit(None, dtype=pl.Utf8).alias("mktcap_raw"))

    df = df.with_columns(
        pl.col("bse_code_raw").cast(pl.Int64, strict=False).alias("bse_code"),
        pl.col("isin").str.strip_chars().str.to_uppercase(),
        pl.col("mktcap_raw").cast(pl.Float64, strict=False).alias("mktcap"),
    ).drop("bse_code_raw", "mktcap_raw")

    # Keep only equity-like rows that carry a 12-char ISIN.
    df = df.filter(
        (pl.col("isin").str.len_chars() == 12) & pl.col("bse_code").is_not_null()
    )
    return df.unique(subset=["isin"], keep="first")
