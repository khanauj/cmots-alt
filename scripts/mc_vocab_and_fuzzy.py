"""Dump MC sector-slug vocabulary (by company count) + test token-Jaccard fuzzy gain."""
import re
import sys
from collections import defaultdict

import polars as pl

sys.stdout.reconfigure(encoding="utf-8")
mc = pl.read_parquet("storage/cache/mc_directory.parquet")

# Clean sector vocabulary: count companies per sector_slug
vc = mc.group_by("sector_slug").len().sort("len", descending=True)
total = mc.height
cum = 0
print("=== MC sector slugs covering 95% of companies ===")
keep = []
for slug, n in vc.iter_rows():
    cum += n
    keep.append((slug, n))
    if cum / total >= 0.95:
        break
print(f"{len(keep)} slugs cover 95% of {total} companies")
for slug, n in keep:
    print(f"{n:5}  {slug}")

# write full vocab to a file for mapping authoring
vc.write_csv("storage/cache/mc_sector_vocab.csv")
print(f"\nfull vocab ({vc.height} slugs) -> storage/cache/mc_sector_vocab.csv")
