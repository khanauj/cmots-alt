"""Identifier resolution: ISIN spine → stable co_code, crosswalk maintenance.

For each ISIN seen across sources we ensure exactly one company row with a
co_code minted once and never changed. Returns an (isin, co_code) frame the
merge step joins back onto.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

import polars as pl

from ..core.logging import get_logger
from ..core.settings import Settings
from ..storage.db import get_db

log = get_logger("resolver")


def norm_symbol(s: str | None) -> str:
    """Uppercase, drop everything but A-Z0-9. 'M&M-RE' -> 'MMRE', 'L&TFH' -> 'LTFH'."""
    return re.sub(r"[^A-Z0-9]", "", s.upper()) if s else ""


def norm_name(s: str | None) -> str:
    if not s:
        return ""
    s = s.lower().replace("&", "and")
    s = re.sub(r"\b(ltd|limited|pvt|private|the|co|company|corp|corporation)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


@dataclass(frozen=True)
class Identity:
    co_code: int
    isin: str
    nse_symbol: str | None
    bse_code: int | None
    legal_name: str | None = None


@dataclass
class IdentityMaps:
    """CompanyMaster crosswalk for resolving downstream rows to a stable co_code."""

    by_isin: dict[str, Identity]
    by_nse_symbol: dict[str, Identity]
    by_bse_code: dict[int, Identity]
    by_norm_symbol: dict[str, Identity] = field(default_factory=dict)
    # First-4-char blocks of normalized NSE symbols → candidate norm_symbols, for
    # the strict-threshold fuzzy fallback. Symbol-based (not name-based) fuzzy
    # avoids linking ETFs/derivatives to same-named AMC/parent company rows.
    symbol_blocks: dict[str, list[str]] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.by_isin)


def load_identity_maps(settings: Settings) -> IdentityMaps:
    """Load ISIN / NSE-symbol / BSE-code / normalized-symbol / name → co_code lookups.

    The Equity EOD pipeline (and any future price/fundamental feed) resolves to
    a stable co_code through these maps rather than minting new identities.
    """
    by_isin: dict[str, Identity] = {}
    by_nse: dict[str, Identity] = {}
    by_bse: dict[int, Identity] = {}
    by_nsym: dict[str, Identity] = {}
    blocks: dict[str, list[str]] = defaultdict(list)
    with get_db(settings) as conn:
        for r in conn.execute(
            "SELECT isin, co_code, nse_symbol, bse_code, legal_name FROM company"
        ):
            ident = Identity(
                co_code=int(r["co_code"]),
                isin=r["isin"],
                nse_symbol=r["nse_symbol"],
                bse_code=int(r["bse_code"]) if r["bse_code"] is not None else None,
                legal_name=r["legal_name"],
            )
            by_isin[ident.isin] = ident
            if ident.nse_symbol:
                by_nse[ident.nse_symbol.upper()] = ident
                ns = norm_symbol(ident.nse_symbol)
                if len(ns) >= 4:
                    by_nsym.setdefault(ns, ident)
                    blocks[ns[:4]].append(ns)
            if ident.bse_code is not None:
                by_bse[ident.bse_code] = ident
    log.info("resolver.identity_maps_loaded", companies=len(by_isin), symbols=len(by_nsym))
    return IdentityMaps(
        by_isin=by_isin,
        by_nse_symbol=by_nse,
        by_bse_code=by_bse,
        by_norm_symbol=by_nsym,
        symbol_blocks=dict(blocks),
    )


def ensure_companies(
    settings: Settings,
    isins: list[str],
) -> pl.DataFrame:
    """Mint co_code for any new ISIN in a single transaction. Returns (isin, co_code).

    co_code is stable: an ISIN seen on a prior run keeps its original code.
    """
    now = datetime.now(timezone.utc).isoformat()

    with get_db(settings) as conn:
        existing = {
            r["isin"]: int(r["co_code"])
            for r in conn.execute("SELECT isin, co_code FROM company")
        }
        mapping = dict(existing)

        next_val = int(conn.execute("SELECT next_value FROM co_code_sequence").fetchone()["next_value"])
        to_insert: list[tuple[str, int, str, str]] = []
        for isin in isins:
            if isin in mapping:
                continue
            mapping[isin] = next_val
            to_insert.append((isin, next_val, now, now))
            next_val += 1

        if to_insert:
            conn.executemany(
                """
                INSERT OR IGNORE INTO company
                    (isin, co_code, legal_name, short_name, category,
                     nse_listed, bse_listed, first_seen_at, last_seen_at)
                VALUES (?, ?, '', '', 'Company', 0, 0, ?, ?)
                """,
                to_insert,
            )
            conn.execute("UPDATE co_code_sequence SET next_value = ?", (next_val,))
            conn.commit()

    minted = len(to_insert)
    log.info("resolver.ensured", total=len(isins), minted=minted, existing=len(isins) - minted)
    return pl.DataFrame(
        {"isin": isins, "co_code": [mapping[i] for i in isins]},
        schema={"isin": pl.Utf8, "co_code": pl.Int64},
    )


def upsert_company_master(settings: Settings, gold: pl.DataFrame) -> None:
    """Persist the enriched master back into SQLite (keeps co_code stable)."""
    now = datetime.now(timezone.utc).isoformat()
    rows = gold.to_dicts()
    with get_db(settings) as conn:
        for r in rows:
            conn.execute(
                """
                UPDATE company SET
                    nse_symbol = ?, bse_code = ?, legal_name = ?, short_name = ?,
                    category = ?, sector_code = ?, sector_name = ?,
                    sector_confidence = ?, mcap_class = ?,
                    bse_group = ?, nse_listed = ?, bse_listed = ?, last_seen_at = ?
                WHERE isin = ?
                """,
                (
                    r.get("NSESymbol"),
                    r.get("BSECode"),
                    r.get("CompanyName") or "",
                    r.get("CompanyShortName") or "",
                    r.get("CategoryName") or "Company",
                    r.get("SectorCode"),
                    r.get("SectorName"),
                    r.get("SectorConfidence"),
                    r.get("mcaptype"),
                    r.get("BSEGroup"),
                    1 if r.get("NSEListed") == "Yes" else 0,
                    1 if r.get("BSEListed") == "Yes" else 0,
                    now,
                    r.get("isin"),
                ),
            )
        conn.commit()
    log.info("resolver.upserted", rows=len(rows))
