"""Normalize NSE + BSE corporate-action events into one canonical silver schema.

NSE ships structured events (subject string carries the ratio / face-value change);
BSE ships board/record-date announcements (action keyword in NEWSSUB, dates mostly
in the attachment, so ex/record are usually null).

Unified columns:
    isin, nse_symbol, bse_code, instrument_name, series, face_value,
    action_type, announcement_date, ex_date, record_date, effective_date,
    description, old_face_value, new_face_value, ratio_num, ratio_den,
    exchange, source
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

import polars as pl

from ..core.logging import get_logger
from .company import _valid_isin  # noqa: F401  (kept for parity; not required here)

log = get_logger("normalize.ca")

ACTION_TYPES = [
    "DIVIDEND", "BONUS", "SPLIT", "RIGHTS", "MERGER",
    "DEMERGER", "BUYBACK", "FV_CHANGE", "OTHER",
]

_SILVER_COLUMNS = [
    "isin", "nse_symbol", "bse_code", "instrument_name", "series", "face_value",
    "action_type", "announcement_date", "ex_date", "record_date", "effective_date",
    "description", "old_face_value", "new_face_value", "ratio_num", "ratio_den",
    "exchange", "source",
]

_SCHEMA = {
    "isin": pl.Utf8, "nse_symbol": pl.Utf8, "bse_code": pl.Int64,
    "instrument_name": pl.Utf8, "series": pl.Utf8, "face_value": pl.Float64,
    "action_type": pl.Utf8, "announcement_date": pl.Date, "ex_date": pl.Date,
    "record_date": pl.Date, "effective_date": pl.Date, "description": pl.Utf8,
    "old_face_value": pl.Float64, "new_face_value": pl.Float64,
    "ratio_num": pl.Float64, "ratio_den": pl.Float64, "exchange": pl.Utf8,
    "source": pl.Utf8,
}


def classify_action(text: str | None) -> str:
    t = (text or "").lower()
    if "demerg" in t or "spin off" in t or "spin-off" in t:
        return "DEMERGER"
    if "amalgamat" in t or "merger" in t or "scheme of arrangement" in t:
        return "MERGER"
    if "bonus" in t:
        return "BONUS"
    if "buy back" in t or "buyback" in t or "buy-back" in t:
        return "BUYBACK"
    if "rights" in t:
        return "RIGHTS"
    if "split" in t or "sub-division" in t or "sub division" in t or "subdivision" in t:
        return "SPLIT"
    if "consolidat" in t or "face value change" in t or "change in face value" in t:
        return "FV_CHANGE"
    if "dividend" in t or "distribution" in t:
        return "DIVIDEND"
    return "OTHER"


def parse_ratio(text: str | None) -> tuple[float | None, float | None, float | None, float | None]:
    """Return (ratio_num, ratio_den, old_face_value, new_face_value).

    Handles: 'From Rs 10/- ... To Rs 5/-', '10->5', '10→5', 'Bonus 1:2', 'Rights 5:14'.
    For face-value transitions num/den mirror old/new; for X:Y ratios face values are null.
    """
    if not text:
        return (None, None, None, None)
    # Face-value transition: "From Rs/Re A ... To Rs/Re B"
    m = re.search(r"from\s+(?:rs|re)\.?\s*([\d.]+).*?to\s+(?:rs|re)\.?\s*([\d.]+)", text, re.I)
    if m:
        old, new = float(m.group(1)), float(m.group(2))
        return (old, new, old, new)
    # Arrow transition: "10->5", "10→5", "5=>10"
    m = re.search(r"([\d.]+)\s*(?:->|=>|→)\s*([\d.]+)", text)
    if m:
        old, new = float(m.group(1)), float(m.group(2))
        return (old, new, old, new)
    # Ratio "X:Y" (bonus / rights)
    m = re.search(r"(\d+)\s*:\s*(\d+)", text)
    if m:
        return (float(m.group(1)), float(m.group(2)), None, None)
    return (None, None, None, None)


def _pdate(s: str | None) -> date | None:
    if not s:
        return None
    s = str(s).strip()
    if s in ("-", "", "NA", "null"):
        return None
    if "T" in s:  # ISO datetime
        try:
            return datetime.fromisoformat(s.replace("Z", "")).date()
        except ValueError:
            s = s.split("T", 1)[0]
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d %b %Y", "%d-%b-%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _to_float(s) -> float | None:
    try:
        return float(str(s).strip()) if s not in (None, "", "-") else None
    except (ValueError, TypeError):
        return None


def _frame(rows: list[dict]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame(schema=_SCHEMA)
    return pl.DataFrame(rows, schema=_SCHEMA).select(_SILVER_COLUMNS)


def parse_nse_corp_actions(path: Path) -> pl.DataFrame:
    data = json.loads(path.read_bytes())
    rows: list[dict] = []
    for r in data if isinstance(data, list) else []:
        subject = r.get("subject")
        num, den, old_fv, new_fv = parse_ratio(subject)
        rows.append({
            "isin": (r.get("isin") or "").strip().upper() or None,
            "nse_symbol": (r.get("symbol") or "").strip() or None,
            "bse_code": None,
            "instrument_name": (r.get("comp") or "").strip() or None,
            "series": (r.get("series") or "").strip() or None,
            "face_value": _to_float(r.get("faceVal")),
            "action_type": classify_action(subject),
            "announcement_date": _pdate(r.get("caBroadcastDate")),
            "ex_date": _pdate(r.get("exDate")),
            "record_date": _pdate(r.get("recDate")),
            "effective_date": None,
            "description": subject,
            "old_face_value": old_fv,
            "new_face_value": new_fv,
            "ratio_num": num,
            "ratio_den": den,
            "exchange": "NSE",
            "source": "NSE_CA_API",
        })
    log.info("ca.nse_parsed", rows=len(rows))
    return _frame(rows)


def parse_bse_corp_actions(path: Path) -> pl.DataFrame:
    data = json.loads(path.read_bytes())
    rows: list[dict] = []
    for r in data if isinstance(data, list) else []:
        subject = r.get("NEWSSUB") or r.get("HEADLINE")
        num, den, old_fv, new_fv = parse_ratio(subject)
        code = r.get("SCRIP_CD")
        rows.append({
            "isin": None,
            "nse_symbol": None,
            "bse_code": int(code) if code not in (None, "") else None,
            "instrument_name": (r.get("SLONGNAME") or "").strip() or None,
            "series": None,
            "face_value": None,
            "action_type": classify_action(subject),
            "announcement_date": _pdate(r.get("DT_TM") or r.get("NEWS_DT")),
            "ex_date": None,
            "record_date": None,
            "effective_date": None,
            "description": (subject or "").strip() or None,
            "old_face_value": old_fv,
            "new_face_value": new_fv,
            "ratio_num": num,
            "ratio_den": den,
            "exchange": "BSE",
            "source": "BSE_ANN",
        })
    log.info("ca.bse_parsed", rows=len(rows))
    return _frame(rows)
