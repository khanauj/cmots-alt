"""Hardened identity resolution for downstream feeds (Equity EOD and beyond).

Waterfall, highest-confidence first; the first hit wins and records its reason:

    isin_exact -> nse_symbol_exact -> bsecode_exact -> normalized_symbol
    -> alias -> historical -> fuzzy (strict) -> unresolved

Principles (per spec): never mint a co_code for an uncertain match; confidence
over coverage. Fuzzy only fires on a company name with a strict cutoff, so a
near-miss is left unresolved rather than mis-linked.

Each row is also tagged with an ``instrument_type`` so non-equity instruments
(ETF / SME / preference / warrant / rights / debt) are excluded from the equity
coverage denominator instead of counted as resolver failures.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from ..core.logging import get_logger
from .resolver import Identity, IdentityMaps, norm_symbol

log = get_logger("transform.identity")

_FUZZY_CUTOFF = 0.92          # strict — confidence over coverage
_ALIAS_MIN_CONFIDENCE = 0.90

# SME platform series: NSE Emerge (SM/ST) and BSE SME groups (M/MT/MS).
_SME_SERIES = {"SM", "ST", "M", "MT", "MS"}
_RIGHTS_SERIES = {"RR", "RE", "RT"}

_ETF_RE = re.compile(
    r"(BEES|ETF|IETF|LIQUID|GOLD|SILVER|NIFTY|SENSEX|GILT|GSEC|SDL|MOMENTUM|VALUE|"
    r"QUALITY|ALPHA|LOWVOL|HANGSENG|NASDAQ|BHARATBOND|MON100|PSUBNK|CPSE|MULTICAP|"
    r"MID150|SML250|SMALLCAP|HEALTH|CONSUM|TECH|INFRA|MNC|DIVOPP|EQUAL|N50|N100|"
    r"N200|NV20|NEXT50|NIF|BSE500|ESG|DEFENCE|ENERGY|METAL|REALTY|RAIL|PSE|FMCG|"
    r"AUTO|BANK|FINSER|GROWW|ADD|BETA|EVINDIA|CAPM)",
    re.I,
)
_DEBT_RE = re.compile(
    r"(\bNCD\b|\bBOND\b|DEBENTURE|\bGSEC\b|G-SEC|\bSDL\b|STRIPS|\bGOI\b|\bSGB\b|"
    r"\bTBILL\b|\bGS\b|SOVEREIGN|\bDR\b)",
    re.I,
)

RESOLUTION_REASONS = [
    "isin_exact", "nse_symbol_exact", "bsecode_exact", "normalized_symbol",
    "alias", "historical", "fuzzy", "unresolved",
]


@dataclass(frozen=True)
class Alias:
    new_symbol: str
    alias_type: str
    confidence: float


def load_aliases(project_root: Path) -> dict[str, Alias]:
    """norm_symbol(old) -> Alias. Only entries at confidence >= 0.90 are kept."""
    path = project_root / "config" / "identifier_aliases.csv"
    if not path.exists():
        return {}
    df = pl.read_csv(path, comment_prefix="#")
    out: dict[str, Alias] = {}
    for old, new, atype, conf in df.iter_rows():
        c = float(conf)
        if c < _ALIAS_MIN_CONFIDENCE or not old or not new:
            continue
        out[norm_symbol(old)] = Alias(new_symbol=str(new), alias_type=str(atype), confidence=c)
    log.info("identity.aliases_loaded", entries=len(out))
    return out


@dataclass
class Resolution:
    co_code: int | None
    isin: str | None
    bse_code: int | None
    nse_symbol: str | None
    reason: str
    confidence: float


def _accept(row: dict, ident: Identity, reason: str, confidence: float) -> Resolution:
    """Backfill missing identifiers from the matched master row; keep the row's own."""
    return Resolution(
        co_code=ident.co_code,
        isin=row.get("isin") or ident.isin,
        bse_code=row.get("bse_code") if row.get("bse_code") is not None else ident.bse_code,
        nse_symbol=row.get("nse_symbol") or ident.nse_symbol,
        reason=reason,
        confidence=confidence,
    )


def resolve_one(row: dict, maps: IdentityMaps, aliases: dict[str, Alias]) -> Resolution:
    isin = row.get("isin")
    sym = row.get("nse_symbol")
    bse = row.get("bse_code")
    name = row.get("instrument_name")

    # 1. ISIN exact
    if isin and isin in maps.by_isin:
        return _accept(row, maps.by_isin[isin], "isin_exact", 1.0)
    # 2. NSE symbol exact
    if sym and sym.upper() in maps.by_nse_symbol:
        return _accept(row, maps.by_nse_symbol[sym.upper()], "nse_symbol_exact", 1.0)
    # 3. BSE code exact
    if bse is not None and bse in maps.by_bse_code:
        return _accept(row, maps.by_bse_code[bse], "bsecode_exact", 1.0)
    # 4. Normalized symbol (drops &, -, suffixes)
    nsy = norm_symbol(sym)
    if nsy and nsy in maps.by_norm_symbol:
        return _accept(row, maps.by_norm_symbol[nsy], "normalized_symbol", 0.97)
    # 5./6. Alias + historical symbol map
    if nsy and nsy in aliases:
        al = aliases[nsy]
        tgt = maps.by_nse_symbol.get(al.new_symbol.upper()) or maps.by_norm_symbol.get(
            norm_symbol(al.new_symbol)
        )
        if tgt is not None:
            reason = "historical" if al.alias_type == "historical" else "alias"
            return _accept(row, tgt, reason, al.confidence)
    # 7. Fuzzy on normalized symbol (strict cutoff), gated to equity candidates so
    #    ETFs / pref / warrants / SME are never linked to a same-named company.
    if intrinsic_type(row) is None and len(nsy) >= 4:
        cands = maps.symbol_blocks.get(nsy[:4], [])
        hit = difflib.get_close_matches(nsy, cands, n=1, cutoff=_FUZZY_CUTOFF)
        if hit:
            ratio = difflib.SequenceMatcher(None, nsy, hit[0]).ratio()
            return _accept(row, maps.by_norm_symbol[hit[0]], "fuzzy", round(ratio, 3))
    # 8. Unresolved — never minted.
    return Resolution(co_code=None, isin=isin, bse_code=bse, nse_symbol=sym,
                      reason="unresolved", confidence=0.0)


def intrinsic_type(row: dict) -> str | None:
    """Definitive non-equity instrument type from intrinsic signals (ISIN / series /
    name / symbol), independent of resolution. Returns None when the row could be a
    genuine equity (so the resolver may attempt a fuzzy match and classify by outcome).
    Debt/bond instruments map to UNKNOWN (no co_code in the equity master, no enum)."""
    sym = (row.get("nse_symbol") or "").upper()
    name = (row.get("instrument_name") or "").upper()
    series = (row.get("series") or "").upper()
    isin = row.get("isin") or ""

    if series in _SME_SERIES:
        return "SME"
    if "RIGHTS" in name or sym.endswith("-RE") or series in _RIGHTS_SERIES:
        return "RIGHTS"
    if "WARRANT" in name or sym.endswith("-WR") or sym.endswith("-W"):
        return "WARRANT"
    if ("PREF" in name or "PREFERENCE" in name
            or sym.endswith("RPS") or sym.endswith("PP") or sym.endswith("-PS")):
        return "PREF"
    if isin.startswith("INF") or "ETF" in name or "MUTUAL FUND" in name or "BEES" in name:
        return "ETF"
    if _DEBT_RE.search(name):
        return "UNKNOWN"  # debt/bond
    return None


def classify_instrument(row: dict, resolved: bool) -> str:
    t = intrinsic_type(row)
    if t is not None:
        return t
    if resolved:
        return "EQUITY"  # matched the equity CompanyMaster by an exact identifier
    # Unresolved + no hard signal: a weak symbol heuristic catches ETFs/index funds
    # whose only tell is the ticker (NSE bhavcopy gives no name or ISIN).
    if _ETF_RE.search((row.get("nse_symbol") or "").upper()):
        return "ETF"
    return "UNKNOWN"


def resolve_frame(
    df: pl.DataFrame, maps: IdentityMaps, aliases: dict[str, Alias]
) -> pl.DataFrame:
    """Resolve every silver EOD row; add co_code, backfilled identifiers,
    resolution_reason/confidence and instrument_type."""
    co, isin, bse, sym, reason, conf, itype = [], [], [], [], [], [], []
    for row in df.iter_rows(named=True):
        res = resolve_one(row, maps, aliases)
        co.append(res.co_code)
        isin.append(res.isin)
        bse.append(res.bse_code)
        sym.append(res.nse_symbol)
        reason.append(res.reason)
        conf.append(res.confidence)
        itype.append(classify_instrument(row, res.co_code is not None))
    out = df.with_columns(
        pl.Series("co_code", co, dtype=pl.Int64),
        pl.Series("isin", isin, dtype=pl.Utf8),
        pl.Series("bse_code", bse, dtype=pl.Int64),
        pl.Series("nse_symbol", sym, dtype=pl.Utf8),
        pl.Series("resolution_reason", reason, dtype=pl.Utf8),
        pl.Series("resolution_confidence", conf, dtype=pl.Float64),
        pl.Series("instrument_type", itype, dtype=pl.Utf8),
    )
    log.info(
        "identity.resolved",
        rows=out.height,
        by_reason={r[0]: r[1] for r in out.group_by("resolution_reason").len().iter_rows()},
        by_type={r[0]: r[1] for r in out.group_by("instrument_type").len().iter_rows()},
    )
    return out
