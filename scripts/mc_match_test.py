"""Improve MC->universe match: deterministic + token-blocked fuzzy. Measure coverage."""
import difflib
import re
import sys

import polars as pl

sys.stdout.reconfigure(encoding="utf-8")

mc = pl.read_parquet("storage/cache/mc_directory.parquet")
gold = pl.read_parquet("storage/processed/gold/company_master/dt=2026-05-27.parquet")


def norm(s: str) -> str:
    s = s.lower().replace("&", "and")
    s = re.sub(r"\b(ltd|limited|pvt|private|the|co|company|corp|corporation)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


# MC lookup: by comp_slug and by normalized name
mc_lookup: dict[str, str] = {}
mc_name_norm: dict[str, str] = {}
for sector_slug, comp_slug, code, name in mc.iter_rows():
    mc_lookup[comp_slug] = sector_slug
    mc_lookup[norm(name)] = sector_slug
    mc_name_norm[norm(name)] = sector_slug

# our companies, also keep nse symbol for slug fallback
our = []
for isin, nsym, cname in zip(
    gold.get_column("isin").to_list(),
    gold.get_column("NSESymbol").to_list(),
    gold.get_column("CompanyName").to_list(),
):
    our.append((isin, nsym, cname))

# Deterministic pass
unmatched = []
matched = 0
for isin, nsym, cname in our:
    if cname is None:
        unmatched.append((isin, nsym, cname))
        continue
    k = norm(cname)
    if k in mc_lookup or (nsym and nsym.lower() in mc_lookup):
        matched += 1
    else:
        unmatched.append((isin, nsym, cname))
print(f"deterministic matched: {matched}/{len(our)} ({100*matched/len(our):.1f}%)")
print(f"unmatched after deterministic: {len(unmatched)}")

# Token-blocked fuzzy: block on first 4 chars of normalized name
from collections import defaultdict

blocks = defaultdict(list)
for k in mc_name_norm:
    if len(k) >= 4:
        blocks[k[:4]].append(k)

fuzzy_matched = 0
still = []
for isin, nsym, cname in unmatched:
    if not cname:
        still.append((isin, nsym, cname))
        continue
    k = norm(cname)
    cands = blocks.get(k[:4], [])
    hit = difflib.get_close_matches(k, cands, n=1, cutoff=0.88)
    if hit:
        fuzzy_matched += 1
    else:
        still.append((isin, nsym, cname))

total = matched + fuzzy_matched
print(f"fuzzy added: {fuzzy_matched}")
print(f"TOTAL matched: {total}/{len(our)} ({100*total/len(our):.1f}%)")
print(f"still unmatched: {len(still)}")
print("\nsample still-unmatched:")
for isin, nsym, cname in still[:25]:
    print(f"  {isin}  {nsym}  {cname!r}")
