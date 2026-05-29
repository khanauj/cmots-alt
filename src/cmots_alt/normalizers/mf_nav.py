"""AMFI NAVAll.txt parser → canonical silver dataframe.

File structure (semicolon-delimited, interspersed with text):

  Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date

  Open Ended Schemes(Equity Scheme - ELSS)

  Aditya Birla Sun Life Mutual Fund

   Aditya Birla Sun Life AMC Limited
  102885;INF209K01199;INF209K01207;Aditya Birla SL Tax Relief 96 - Direct Plan-Growth;55.27;26-May-2026
  ...

Rules:
  - Header line starts with "Scheme Code;" — skip.
  - Section line matches r"^(Open Ended|Close Ended|Interval Fund) Schemes\\((.+)\\)$".
    Category form is "<Family> - <SubCategory>" (subcategory may be absent).
  - Data line: ≥ 5 semicolons → 6 fields.
  - Other non-empty, non-delimited lines are AMC names; we keep the *most recent*.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import polars as pl

from ..core.errors import ParseError

_SECTION_RE = re.compile(
    r"^\s*(Open Ended|Close Ended|Interval Fund) Schemes\((.+)\)\s*$"
)


@dataclass(frozen=True)
class ParsedNavRow:
    scheme_code: int
    isin_growth: str | None
    isin_div_reinvestment: str | None
    scheme_name: str
    nav: float | None
    nav_date: str | None  # ISO date string (silver)
    amc_name: str | None
    scheme_type: str | None
    scheme_category: str | None
    scheme_subcategory: str | None


def _coerce_float(token: str, null_tokens: set[str]) -> float | None:
    t = token.strip()
    if t in null_tokens:
        return None
    try:
        return float(t.replace(",", ""))
    except ValueError:
        return None


def _coerce_date(token: str, fmt: str) -> str | None:
    t = token.strip()
    if not t:
        return None
    try:
        return datetime.strptime(t, fmt).date().isoformat()
    except ValueError:
        return None


def parse_navall_text(
    text: str,
    *,
    date_format: str = "%d-%b-%Y",
    null_tokens: set[str] | None = None,
) -> list[ParsedNavRow]:
    null_tokens = null_tokens or {"", "N.A.", "-", "N/A"}
    out: list[ParsedNavRow] = []

    current_type: str | None = None
    current_cat: str | None = None
    current_sub: str | None = None
    current_amc: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Scheme Code;"):
            continue

        m = _SECTION_RE.match(line)
        if m:
            current_type = m.group(1)
            cat_full = m.group(2).strip()
            if " - " in cat_full:
                cat, sub = cat_full.split(" - ", 1)
                current_cat = cat.strip()
                current_sub = sub.strip()
            else:
                current_cat = cat_full
                current_sub = None
            continue

        if ";" not in line:
            current_amc = line
            continue

        parts = line.split(";")
        if len(parts) < 6:
            continue
        scheme_code_s, isin_g, isin_r, scheme_name, nav_s, date_s = (
            p.strip() for p in parts[:6]
        )
        try:
            scheme_code = int(scheme_code_s)
        except ValueError:
            continue

        out.append(
            ParsedNavRow(
                scheme_code=scheme_code,
                isin_growth=isin_g or None,
                isin_div_reinvestment=isin_r or None,
                scheme_name=scheme_name,
                nav=_coerce_float(nav_s, null_tokens),
                nav_date=_coerce_date(date_s, date_format),
                amc_name=current_amc,
                scheme_type=current_type,
                scheme_category=current_cat,
                scheme_subcategory=current_sub,
            )
        )

    if not out:
        raise ParseError("AMFI NAVAll.txt produced 0 rows — file format may have changed")
    return out


_CONSTRUCT_SCHEMA: dict[str, pl.DataType] = {
    # nav_date kept as Utf8 during construction; cast to Date below.
    "scheme_code": pl.Int64,
    "isin_growth": pl.Utf8,
    "isin_div_reinvestment": pl.Utf8,
    "scheme_name": pl.Utf8,
    "nav": pl.Float64,
    "nav_date": pl.Utf8,
    "amc_name": pl.Utf8,
    "scheme_type": pl.Utf8,
    "scheme_category": pl.Utf8,
    "scheme_subcategory": pl.Utf8,
}


def to_silver(rows: list[ParsedNavRow]) -> pl.DataFrame:
    df = pl.DataFrame(
        [r.__dict__ for r in rows],
        schema=_CONSTRUCT_SCHEMA,
    )
    return df.with_columns(pl.col("nav_date").str.to_date(strict=False))


def parse_navall_file(path: Path) -> pl.DataFrame:
    text = path.read_text(encoding="utf-8")
    rows = parse_navall_text(text)
    return to_silver(rows)
