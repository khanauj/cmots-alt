"""Crawl MC A-Z bulk tables; match comp_slug -> our normalized legal_name."""
import re
import string
import sys
import time

import polars as pl
from curl_cffi import requests as cr

sys.stdout.reconfigure(encoding="utf-8")
sess = cr.Session(impersonate="chrome120")
sess.headers.update({"Accept": "text/html"})

# Bulk alphabetical table rows: class="bl_12"
BULK = re.compile(
    r'href="https://www\.moneycontrol\.com/india/stockpricequote/'
    r'([a-z0-9-]+)/([a-z0-9-]+)/([A-Z0-9]+)"\s+class="bl_12">([^<]+)<'
)

rows = []
for letter in string.ascii_uppercase:
    url = f"https://www.moneycontrol.com/india/stockpricequote/{letter}"
    try:
        r = sess.get(url, timeout=30)
        for sector_slug, comp_slug, code, name in BULK.findall(r.text):
            rows.append((sector_slug, comp_slug, code, name.strip()))
    except Exception as e:
        print(f"letter {letter} ERR {e}")
    time.sleep(0.25)

mc = pl.DataFrame(rows, schema=["sector_slug", "comp_slug", "mc_code", "name"], orient="row").unique(
    subset=["comp_slug"], keep="first"
)
print(f"MC companies (unique comp_slug): {mc.height}")
print(f"distinct sector slugs: {mc.select(pl.col('sector_slug').n_unique()).item()}")
mc.write_parquet("storage/cache/mc_directory.parquet")


def norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\b(ltd|limited|pvt|private|the|co|company|corp|corporation|india|indias)\b", "", s)
    return re.sub(r"[^a-z0-9]", "", s)


gold = pl.read_parquet("storage/processed/gold/company_master/dt=2026-05-27.parquet")
our = {norm(n): n for n in gold.get_column("CompanyName").drop_nulls().to_list()}
mc_slugs = set(mc.get_column("comp_slug").to_list())
mc_names = {norm(n) for n in mc.get_column("name").to_list()}

by_slug = sum(1 for k in our if k in mc_slugs)
by_name = sum(1 for k in our if k in mc_names)
by_either = sum(1 for k in our if k in mc_slugs or k in mc_names)
print(f"\nour companies: {len(our)}")
print(f"match comp_slug:  {by_slug} ({100*by_slug/len(our):.1f}%)")
print(f"match norm-name:  {by_name} ({100*by_name/len(our):.1f}%)")
print(f"match either:     {by_either} ({100*by_either/len(our):.1f}%)")

print("\ntop MC sector slugs:")
print(mc.group_by("sector_slug").len().sort("len", descending=True).head(25))
