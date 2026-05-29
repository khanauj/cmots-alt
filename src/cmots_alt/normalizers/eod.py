"""Parse NSE + BSE bhavcopies into a single canonical Equity-EOD silver schema.

Both parsers emit the same columns/dtypes so the transformer can vstack them:

    isin, bse_code, nse_symbol, series, trade_date,
    open, high, low, close, prev_close, last_price, vwap,
    total_volume, total_turnover, deliverable_qty, deliverable_percent,
    no_of_trades, exchange

Source-specific gaps:
  * NSE carries VWAP (AVG_PRICE), deliverable qty/% and no ISIN.
  * BSE carries ISIN + scrip code but no deliverables; its VWAP is derived
    as turnover / volume (the volume-weighted average traded price).
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from ..core.errors import ParseError
from ..core.logging import get_logger
from .company import _clean_columns, _col, _valid_isin

log = get_logger("normalize.eod")

# NSE series that represent tradable equity (drops govt-sec/bond series like GS, GB, TB).
NSE_EQUITY_SERIES = {"EQ", "BE", "BZ", "BL", "BT", "SM", "ST", "IL", "IQ"}

_SILVER_COLUMNS = [
    "isin", "bse_code", "nse_symbol", "instrument_name", "series", "trade_date",
    "open", "high", "low", "close", "prev_close", "last_price", "vwap",
    "total_volume", "total_turnover", "deliverable_qty", "deliverable_percent",
    "no_of_trades", "exchange",
]


def _fnum(col: str) -> pl.Expr:
    return pl.col(col).str.strip_chars().cast(pl.Float64, strict=False)


def _inum(col: str) -> pl.Expr:
    # Volumes/turnover sometimes carry decimals; round-trip via float to be safe.
    return pl.col(col).str.strip_chars().cast(pl.Float64, strict=False).cast(pl.Int64, strict=False)


def parse_nse_bhavcopy(path: Path) -> pl.DataFrame:
    df = _clean_columns(pl.read_csv(path, infer_schema_length=0))
    c_sym = _col(df, "SYMBOL")
    c_series = _col(df, "SERIES")
    c_date = _col(df, "DATE1")
    if not (c_sym and c_series and c_date):
        raise ParseError(f"NSE bhavcopy missing SYMBOL/SERIES/DATE1; got {df.columns}")

    out = df.select(
        pl.lit(None, dtype=pl.Utf8).alias("isin"),
        pl.lit(None, dtype=pl.Int64).alias("bse_code"),
        pl.col(c_sym).str.strip_chars().alias("nse_symbol"),
        pl.lit(None, dtype=pl.Utf8).alias("instrument_name"),  # NSE bhavcopy carries no name
        pl.col(c_series).str.strip_chars().alias("series"),
        pl.col(c_date).str.strip_chars().str.to_date("%d-%b-%Y", strict=False).alias("trade_date"),
        _fnum(_col(df, "OPEN_PRICE")).alias("open"),
        _fnum(_col(df, "HIGH_PRICE")).alias("high"),
        _fnum(_col(df, "LOW_PRICE")).alias("low"),
        _fnum(_col(df, "CLOSE_PRICE")).alias("close"),
        _fnum(_col(df, "PREV_CLOSE")).alias("prev_close"),
        _fnum(_col(df, "LAST_PRICE")).alias("last_price"),
        _fnum(_col(df, "AVG_PRICE")).alias("vwap"),
        _inum(_col(df, "TTL_TRD_QNTY")).alias("total_volume"),
        # TURNOVER_LACS is in lakhs of rupees → convert to rupees.
        (_fnum(_col(df, "TURNOVER_LACS")) * 100_000).alias("total_turnover"),
        _inum(_col(df, "DELIV_QTY")).alias("deliverable_qty"),
        _fnum(_col(df, "DELIV_PER")).alias("deliverable_percent"),
        _inum(_col(df, "NO_OF_TRADES")).alias("no_of_trades"),
        pl.lit("NSE", dtype=pl.Utf8).alias("exchange"),
    )
    out = out.filter(pl.col("series").is_in(list(NSE_EQUITY_SERIES)))
    return out.select(_SILVER_COLUMNS)


def parse_bse_bhavcopy(path: Path) -> pl.DataFrame:
    df = _clean_columns(pl.read_csv(path, infer_schema_length=0))
    c_type = _col(df, "FinInstrmTp")
    c_code = _col(df, "FinInstrmId", "SC_CODE")
    c_isin = _col(df, "ISIN", "ISIN_CODE")
    c_date = _col(df, "TradDt")
    if not (c_code and c_date):
        raise ParseError(f"BSE bhavcopy missing FinInstrmId/TradDt; got {df.columns}")

    if c_type:
        df = df.filter(pl.col(c_type).str.strip_chars() == "STK")

    turnover = _fnum(_col(df, "TtlTrfVal", "TURNOVER"))
    volume = _inum(_col(df, "TtlTradgVol", "NO_OF_SHRS"))
    out = df.select(
        _valid_isin(pl.col(c_isin)).alias("isin") if c_isin
        else pl.lit(None, dtype=pl.Utf8).alias("isin"),
        pl.col(c_code).str.strip_chars().cast(pl.Int64, strict=False).alias("bse_code"),
        (pl.col(_col(df, "TckrSymb")).str.strip_chars() if _col(df, "TckrSymb")
         else pl.lit(None, dtype=pl.Utf8)).alias("nse_symbol"),
        (pl.col(_col(df, "FinInstrmNm", "SC_NAME")).str.strip_chars() if _col(df, "FinInstrmNm", "SC_NAME")
         else pl.lit(None, dtype=pl.Utf8)).alias("instrument_name"),
        (pl.col(_col(df, "SctySrs")).str.strip_chars() if _col(df, "SctySrs")
         else pl.lit(None, dtype=pl.Utf8)).alias("series"),
        pl.col(c_date).str.strip_chars().str.to_date("%Y-%m-%d", strict=False).alias("trade_date"),
        _fnum(_col(df, "OpnPric")).alias("open"),
        _fnum(_col(df, "HghPric")).alias("high"),
        _fnum(_col(df, "LwPric")).alias("low"),
        _fnum(_col(df, "ClsPric")).alias("close"),
        _fnum(_col(df, "PrvsClsgPric")).alias("prev_close"),
        _fnum(_col(df, "LastPric")).alias("last_price"),
        # BSE has no published VWAP — derive volume-weighted avg traded price.
        pl.when(volume > 0).then((turnover / volume).round(2))
        .otherwise(None).cast(pl.Float64).alias("vwap"),
        volume.alias("total_volume"),
        turnover.alias("total_turnover"),
        pl.lit(None, dtype=pl.Int64).alias("deliverable_qty"),
        pl.lit(None, dtype=pl.Float64).alias("deliverable_percent"),
        _inum(_col(df, "TtlNbOfTxsExctd", "NO_TRADES")).alias("no_of_trades"),
        pl.lit("BSE", dtype=pl.Utf8).alias("exchange"),
    )
    # Equity-segment rows carry a numeric scrip code and a 12-char ISIN.
    out = out.filter(pl.col("bse_code").is_not_null())
    return out.select(_SILVER_COLUMNS)
