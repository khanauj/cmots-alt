"""Sector resolution: waterfall over NSE industry (by ISIN) and Moneycontrol
(by company-name slug), into our 50-bucket taxonomy.

Per company we record:
  sector_code, sector_name, sector_source, sector_confidence, sector_conflict

Sources & confidence:
  nse_index  -> high    (NSE official industry, joined cleanly by ISIN)
  mc_exact   -> high    (exact company-slug / normalized-name match on MC)
  mc_fuzzy   -> medium  (token-blocked fuzzy match on MC name)
  (none)     -> null

Conflict: NSE and MC both resolve but to different buckets (NSE wins the value).
"""

from __future__ import annotations

import difflib
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import yaml

from ..core.logging import get_logger

log = get_logger("transform.sector")

_FUZZY_CUTOFF = 0.86


@dataclass
class SectorTaxonomy:
    buckets: dict[int, str]
    nse_industry_map: dict[str, int]
    mc_sector_map: dict[str, int]
    non_company_slugs: set[str]


def _norm_industry(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _norm_name(s: str) -> str:
    s = s.lower().replace("&", "and")
    s = re.sub(r"\b(ltd|limited|pvt|private|the|co|company|corp|corporation)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def load_sector_taxonomy(project_root: Path) -> SectorTaxonomy:
    with (project_root / "config" / "sector_taxonomy.yaml").open("r", encoding="utf-8") as f:
        tax = yaml.safe_load(f)
    with (project_root / "config" / "mc_sector_map.yaml").open("r", encoding="utf-8") as f:
        mc = yaml.safe_load(f)
    return SectorTaxonomy(
        buckets={int(k): str(v) for k, v in tax["buckets"].items()},
        nse_industry_map={_norm_industry(k): int(v) for k, v in tax["nse_industry_map"].items()},
        mc_sector_map={str(k): int(v) for k, v in mc["mc_sector_map"].items()},
        non_company_slugs=set(mc.get("non_company_slugs", [])),
    )


def _build_mc_index(
    mc_dir: pl.DataFrame, tax: SectorTaxonomy
) -> tuple[dict[str, int], dict[str, int], dict[str, list[str]]]:
    """Returns (exact_lookup, name_to_code, fuzzy_blocks)."""
    exact: dict[str, int] = {}
    name_to_code: dict[str, int] = {}
    blocks: dict[str, list[str]] = defaultdict(list)
    for sector_slug, comp_slug, _code, name in mc_dir.iter_rows():
        bucket = tax.mc_sector_map.get(sector_slug)
        if bucket is None:
            continue
        exact[comp_slug] = bucket
        nk = _norm_name(name)
        if nk:
            exact[nk] = bucket
            name_to_code[nk] = bucket
            if len(nk) >= 4:
                blocks[nk[:4]].append(nk)
    return exact, name_to_code, blocks


def assign_sector(
    df: pl.DataFrame,
    tax: SectorTaxonomy,
    mc_dir: pl.DataFrame | None,
) -> pl.DataFrame:
    """Adds sector_code, sector_name, sector_source, sector_confidence, sector_conflict."""
    n = df.height
    has_industry = "nse_industry" in df.columns

    industries = df.get_column("nse_industry").to_list() if has_industry else [None] * n
    names = df.get_column("legal_name_for_match").to_list() if "legal_name_for_match" in df.columns else (
        df.get_column("CompanyName").to_list() if "CompanyName" in df.columns else [None] * n
    )
    nsyms = df.get_column("nse_symbol").to_list() if "nse_symbol" in df.columns else [None] * n

    mc_exact: dict[str, int] = {}
    mc_name_to_code: dict[str, int] = {}
    mc_blocks: dict[str, list[str]] = {}
    if mc_dir is not None:
        mc_exact, mc_name_to_code, mc_blocks = _build_mc_index(mc_dir, tax)

    codes: list[int | None] = []
    snames: list[str | None] = []
    sources: list[str | None] = []
    confs: list[str | None] = []
    conflicts: list[bool] = []

    for industry, name, nsym in zip(industries, names, nsyms):
        nse_code = tax.nse_industry_map.get(_norm_industry(industry)) if industry else None

        mc_code: int | None = None
        mc_src: str | None = None
        if mc_exact:
            key = _norm_name(name) if name else None
            if key and key in mc_exact:
                mc_code, mc_src = mc_exact[key], "mc_exact"
            elif nsym and nsym.lower() in mc_exact:
                mc_code, mc_src = mc_exact[nsym.lower()], "mc_exact"
            elif key and len(key) >= 4:
                cands = mc_blocks.get(key[:4], [])
                hit = difflib.get_close_matches(key, cands, n=1, cutoff=_FUZZY_CUTOFF)
                if hit:
                    mc_code, mc_src = mc_name_to_code[hit[0]], "mc_fuzzy"

        if nse_code is not None:
            final, source, conf = nse_code, "nse_index", "high"
        elif mc_code is not None:
            final = mc_code
            source = mc_src
            conf = "high" if mc_src == "mc_exact" else "medium"
        else:
            final, source, conf = None, None, None

        codes.append(final)
        snames.append(tax.buckets.get(final) if final is not None else None)
        sources.append(source)
        confs.append(conf)
        conflicts.append(nse_code is not None and mc_code is not None and nse_code != mc_code)

    out = df.with_columns(
        pl.Series("sector_code", codes, dtype=pl.Int64),
        pl.Series("sector_name", snames, dtype=pl.Utf8),
        pl.Series("sector_source", sources, dtype=pl.Utf8),
        pl.Series("sector_confidence", confs, dtype=pl.Utf8),
        pl.Series("sector_conflict", conflicts, dtype=pl.Boolean),
    )
    return out


def build_sector_master(
    df: pl.DataFrame,
    mc_dir: pl.DataFrame | None,
    tax: SectorTaxonomy,
    out_path: Path,
) -> pl.DataFrame:
    """Emit sector_master.csv: (raw_sector, source, mapped_sector, sector_code)."""
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()

    if "nse_industry" in df.columns:
        for ind in df.get_column("nse_industry").drop_nulls().unique().to_list():
            code = tax.nse_industry_map.get(_norm_industry(ind))
            key = ("nse", ind)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "raw_sector": ind,
                "source": "nse",
                "mapped_sector": tax.buckets.get(code) if code else None,
                "sector_code": code,
            })

    if mc_dir is not None:
        for slug in mc_dir.get_column("sector_slug").unique().to_list():
            code = tax.mc_sector_map.get(slug)
            key = ("mc", slug)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "raw_sector": slug,
                "source": "mc",
                "mapped_sector": tax.buckets.get(code) if code else None,
                "sector_code": code,
            })

    master = pl.DataFrame(rows).sort(["source", "sector_code", "raw_sector"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    master.write_csv(out_path)
    log.info("sector.master_written", path=str(out_path), rows=master.height)
    return master
