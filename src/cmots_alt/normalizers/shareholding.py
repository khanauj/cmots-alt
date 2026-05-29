"""Normalize NSE shareholding into the canonical silver schema.

Two layers:
  * the bulk master gives promoter% / public% / quarter for every company;
  * each company's XBRL gives the full SEBI breakdown (institutions, FII/DII,
    government, non-institutions, shareholder count) keyed by the category encoded
    in each fact's contextRef.

Unified columns:
    isin, nse_symbol, bse_code, instrument_name, quarter_end,
    promoter_pct, promoter_group_pct, public_pct, dii_pct, fii_pct, govt_pct,
    non_institution_pct, institution_pct, pledged_pct, number_of_shareholders,
    exchange, source
"""

from __future__ import annotations

import re
from datetime import date, datetime

import polars as pl

from ..core.logging import get_logger

log = get_logger("normalize.shp")

_SILVER_COLUMNS = [
    "isin", "nse_symbol", "bse_code", "instrument_name", "quarter_end",
    "promoter_pct", "promoter_group_pct", "public_pct", "dii_pct", "fii_pct",
    "govt_pct", "non_institution_pct", "institution_pct", "pledged_pct",
    "number_of_shareholders", "exchange", "source",
]

_SCHEMA = {
    "isin": pl.Utf8, "nse_symbol": pl.Utf8, "bse_code": pl.Int64,
    "instrument_name": pl.Utf8, "quarter_end": pl.Date,
    "promoter_pct": pl.Float64, "promoter_group_pct": pl.Float64, "public_pct": pl.Float64,
    "dii_pct": pl.Float64, "fii_pct": pl.Float64, "govt_pct": pl.Float64,
    "non_institution_pct": pl.Float64, "institution_pct": pl.Float64,
    "pledged_pct": pl.Float64, "number_of_shareholders": pl.Int64,
    "exchange": pl.Utf8, "source": pl.Utf8,
}

# XBRL contextRef category -> our field (percentage facts).
_XBRL_PCT_MAP = {
    "ShareholdingOfPromoterAndPromoterGroup": "promoter_pct",
    "PublicShareholding": "public_pct",
    "InstitutionsDomestic": "dii_pct",
    "InstitutionsForeign": "fii_pct",
    "Governments": "govt_pct",
    "NonInstitutions": "non_institution_pct",
}
_DETAIL_FIELDS = [
    "promoter_group_pct", "dii_pct", "fii_pct", "govt_pct",
    "non_institution_pct", "institution_pct", "pledged_pct", "number_of_shareholders",
]


def _pdate(s) -> date | None:
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _pf(s) -> float | None:
    try:
        return float(str(s).strip()) if s not in (None, "", "-", "NA") else None
    except (ValueError, TypeError):
        return None


def _ppct(s) -> float | None:
    """Parse a percentage, rejecting corrupt out-of-[0,100] filing values to null."""
    v = _pf(s)
    return v if (v is not None and 0.0 <= v <= 100.0) else None


def parse_shp_master(records: list[dict]) -> tuple[pl.DataFrame, dict[str, str]]:
    """Base silver (promoter/public/quarter) + {symbol: xbrl_url} for enrichment."""
    rows: list[dict] = []
    xbrl_urls: dict[str, str] = {}
    for r in records:
        sym = (r.get("symbol") or "").strip() or None
        if sym and r.get("xbrl"):
            xbrl_urls[sym] = r["xbrl"]
        rows.append({
            "isin": (r.get("isin") or "").strip().upper() or None,
            "nse_symbol": sym,
            "bse_code": None,
            "instrument_name": (r.get("name") or "").strip() or None,
            "quarter_end": _pdate(r.get("date")),
            "promoter_pct": _ppct(r.get("pr_and_prgrp")),
            "promoter_group_pct": None,
            "public_pct": _ppct(r.get("public_val")),
            "dii_pct": None, "fii_pct": None, "govt_pct": None,
            "non_institution_pct": None, "institution_pct": None, "pledged_pct": None,
            "number_of_shareholders": None,
            "exchange": "NSE", "source": "NSE_SHP_MASTER",
        })
    df = pl.DataFrame(rows, schema=_SCHEMA).select(_SILVER_COLUMNS) if rows else pl.DataFrame(schema=_SCHEMA)
    log.info("shp.master_parsed", rows=df.height, with_xbrl=len(xbrl_urls))
    return df, xbrl_urls


def parse_shp_xbrl(text: str) -> dict:
    """Extract the detailed breakdown from one SHP XBRL document."""
    pct = re.findall(
        r"<in-bse-shp:ShareholdingAsAPercentageOfTotalNumberOfShares[^>]*"
        r'contextRef="([^"]+)"[^>]*>([\d.]+)<',
        text,
    )
    cats: dict[str, float] = {}
    for ctx, val in pct:
        cats[re.sub(r"_Context.*", "", ctx)] = float(val)
    if not cats:
        return {}
    # Values are fractions (0.5 == 50%) when the 100%-total anchor is <= 1.5.
    scale = 100.0 if max(cats.values()) <= 1.5 else 1.0

    out: dict = {}
    for cat, field in _XBRL_PCT_MAP.items():
        if cat in cats:
            v = round(cats[cat] * scale, 4)
            if 0.0 <= v <= 100.0:  # ignore mis-scaled/corrupt facts
                out[field] = v
    dii, fii = out.get("dii_pct"), out.get("fii_pct")
    if dii is not None or fii is not None:
        out["institution_pct"] = round((dii or 0) + (fii or 0), 4)

    # Pledged (separate encumbrance table) — best effort.
    mp = re.search(
        r"<in-bse-shp:[\w]*[Pp]ledged[\w]*AsAPercentage[\w]*[^>]*>([\d.]+)<", text
    )
    if mp:
        out["pledged_pct"] = round(float(mp.group(1)) * scale, 4)

    # Total number of shareholders = the grand-total ShareholdingPattern context.
    msh = re.search(
        r"<in-bse-shp:NumberOfShareholders[^>]*"
        r'contextRef="ShareholdingPattern[^"]*"[^>]*>(\d+)<',
        text,
    )
    if msh:
        out["number_of_shareholders"] = int(msh.group(1))
    return out


def enrich_with_xbrl(df: pl.DataFrame, detail_by_symbol: dict[str, dict]) -> pl.DataFrame:
    """Overlay XBRL detail onto base rows, matched by NSE symbol."""
    if not detail_by_symbol:
        return df
    syms = df.get_column("nse_symbol").to_list()
    updates: dict[str, list] = {f: [] for f in _DETAIL_FIELDS}
    base = {f: df.get_column(f).to_list() for f in _DETAIL_FIELDS}
    for i, sym in enumerate(syms):
        detail = detail_by_symbol.get(sym) if sym else None
        for f in _DETAIL_FIELDS:
            updates[f].append(detail.get(f) if detail and f in detail else base[f][i])
    return df.with_columns(
        [pl.Series(f, updates[f], dtype=_SCHEMA[f]) for f in _DETAIL_FIELDS]
    )
