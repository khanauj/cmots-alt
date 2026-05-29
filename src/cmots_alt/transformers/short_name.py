"""CompanyShortName generation — reverse-engineered from CMOTS samples.

Observed evidence (from CMOTS rows):
  Mahindra & Mahindra Ltd                       -> "M & M"
  Deepak Fertilisers & Petrochemicals Corp Ltd  -> "Deepak Fertilis."
  Glaxosmithkline Pharmaceuticals Ltd           -> "Glaxosmi. Pharma"

Algorithm:
  1. override table (by ISIN, else by normalized legal-name match)
  2. strip suffix tokens (Ltd / Limited / Corp ...)
  3. "X & X" identical-tokens-around-& -> "X[0] & X[0]"
  4. whole-word dictionary abbreviation (Pharmaceuticals -> Pharma)
  5. if > cap and has "& <noun>" tail -> drop the tail
  6. truncate longest >9-char alpha token to first 8 chars + "."  (repeat)
  7. hard cap to max_length
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class ShortNameConfig:
    abbreviations: dict[str, str]
    suffix_tokens: set[str]
    max_length: int
    overrides_by_isin: dict[str, str]
    overrides_by_name: dict[str, str]


_AMP_TWIN = re.compile(r"^(\w+)\s*&\s*\1\s*$", re.IGNORECASE)
_AMP_TAIL = re.compile(r"\s+&\s+\w+(\s+\w+)?\s*$")


def _norm_name_key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def load_short_name_config(project_root: Path) -> ShortNameConfig:
    abbr_file = project_root / "config" / "short_name_abbreviations.yaml"
    with abbr_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    overrides_by_isin: dict[str, str] = {}
    overrides_by_name: dict[str, str] = {}
    ov_file = project_root / "config" / "short_name_overrides.csv"
    if ov_file.exists():
        with ov_file.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                short = (row.get("short_name") or "").strip()
                if not short:
                    continue
                isin = (row.get("isin") or "").strip().upper()
                name = (row.get("legal_name_match") or "").strip()
                if isin:
                    overrides_by_isin[isin] = short
                if name:
                    overrides_by_name[_norm_name_key(name)] = short

    return ShortNameConfig(
        abbreviations={k.lower(): v for k, v in data.get("abbreviations", {}).items()},
        suffix_tokens={t.lower().rstrip(".") for t in data.get("suffix_tokens", [])},
        max_length=int(data.get("max_length", 16)),
        overrides_by_isin=overrides_by_isin,
        overrides_by_name=overrides_by_name,
    )


def _strip_suffixes(name: str, suffix_tokens: set[str]) -> str:
    tokens = name.strip().split()
    while tokens and tokens[-1].lower().rstrip(".") in suffix_tokens:
        tokens.pop()
    return " ".join(tokens)


def _apply_dictionary(name: str, abbreviations: dict[str, str]) -> str:
    out = []
    for tok in name.split():
        key = tok.lower().rstrip(".,")
        out.append(abbreviations.get(key, tok))
    return " ".join(out)


def _truncate_long_token(name: str, cap: int) -> str:
    while len(name) > cap:
        toks = name.split()
        idx = None
        longest = 9
        for i, t in enumerate(toks):
            core = t.rstrip(".")
            if core.isalpha() and len(core) > longest:
                longest = len(core)
                idx = i
        if idx is None:
            break
        toks[idx] = toks[idx][:8] + "."
        name = " ".join(toks)
    return name


def make_short_name(
    legal_name: str,
    cfg: ShortNameConfig,
    *,
    isin: str | None = None,
) -> str:
    if isin and isin.upper() in cfg.overrides_by_isin:
        return cfg.overrides_by_isin[isin.upper()]
    name_key = _norm_name_key(legal_name)
    if name_key in cfg.overrides_by_name:
        return cfg.overrides_by_name[name_key]

    s = _strip_suffixes(legal_name, cfg.suffix_tokens)

    m = _AMP_TWIN.match(s)
    if m:
        c = m.group(1)[0].upper()
        return f"{c} & {c}"

    s = _apply_dictionary(s, cfg.abbreviations)
    if len(s) <= cfg.max_length:
        return s

    tail = _AMP_TAIL.search(s)
    if tail is not None:
        candidate = s[: tail.start()].strip()
        if candidate:
            s = candidate
            if len(s) <= cfg.max_length:
                return s

    s = _truncate_long_token(s, cfg.max_length)
    s = s[: cfg.max_length].rstrip()
    # Drop a trailing orphan fragment left by the hard cap (e.g. "Veto Switchge. A").
    toks = s.split()
    if len(toks) >= 2 and len(toks[-1].rstrip(".")) <= 2 and "&" not in toks[-1]:
        s = " ".join(toks[:-1])
    return s.rstrip()
