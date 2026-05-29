"""Measure combined sector coverage: NSE index union (ISIN) + MC (name) - exclude INF."""
import difflib
import re
import sys
from collections import defaultdict

import polars as pl
from curl_cffi import requests as cr

sys.stdout.reconfigure(encoding="utf-8")

# ── NSE index union (clean ISIN -> industry) ──────────────────────────────────
nse = cr.Session(impersonate="chrome120")
try:
    nse.get("https://www.nseindia.com/", timeout=20)
except Exception:
    pass
INDEX_FILES = [
    "ind_niftytotalmarket_list.csv",
    "ind_nifty500list.csv",
    "ind_niftymicrocap250_list.csv",
    "ind_niftysmallcap250list.csv",
    "ind_niftymidcap150list.csv",
]
nse_isin_industry: dict[str, str] = {}
for f in INDEX_FILES:
    url = f"https://nsearchives.nseindia.com/content/indices/{f}"
    try:
        r = nse.get(url, timeout=30)
        if r.status_code != 200:
            print(f"  {f}: HTTP {r.status_code}")
            continue
        df = pl.read_csv(r.content, infer_schema_length=0)
        df = df.rename({c: c.strip() for c in df.columns})
        ic = next((c for c in df.columns if "ISIN" in c.upper()), None)
        ind = next((c for c in df.columns if c.strip().lower() == "industry"), None)
        if ic and ind:
            for isin, industry in zip(df[ic].to_list(), df[ind].to_list()):
                if isin and isin not in nse_isin_industry:
                    nse_isin_industry[isin.strip()] = (industry or "").strip()
        print(f"  {f}: {df.height} rows")
    except Exception as e:
        print(f"  {f}: ERR {e}")
print(f"NSE index union: {len(nse_isin_industry)} ISINs with industry")

# ── MC name lookup ────────────────────────────────────────────────────────────
mc = pl.read_parquet("storage/cache/mc_directory.parquet")


def norm(s: str) -> str:
    s = s.lower().replace("&", "and")
    s = re.sub(r"\b(ltd|limited|pvt|private|the|co|company|corp|corporation)\b", " ", s)
    return re.sub(r"[^a-z0-9]", "", s)


mc_keys = set(mc.get_column("comp_slug").to_list())
mc_name_keys = defaultdict(list)
for comp_slug, name in zip(mc.get_column("comp_slug").to_list(), mc.get_column("name").to_list()):
    mc_keys.add(norm(name))
    nk = norm(name)
    if len(nk) >= 4:
        mc_name_keys[nk[:4]].append(nk)

# ── Universe (exclude INF = mutual fund / ETF ISINs) ──────────────────────────
gold = pl.read_parquet("storage/processed/gold/company_master/dt=2026-05-27.parquet")
all_rows = list(zip(gold["isin"].to_list(), gold["NSESymbol"].to_list(), gold["CompanyName"].to_list()))
inf = [r for r in all_rows if r[0].startswith("INF")]
universe = [r for r in all_rows if not r[0].startswith("INF")]
print(f"\ntotal rows: {len(all_rows)}  INF(MF/ETF excluded): {len(inf)}  company universe: {len(universe)}")

nse_hit = mc_hit = fuzzy_hit = unmatched = 0
for isin, nsym, cname in universe:
    if isin in nse_isin_industry and nse_isin_industry[isin]:
        nse_hit += 1
        continue
    if cname and (norm(cname) in mc_keys or (nsym and nsym.lower() in mc_keys)):
        mc_hit += 1
        continue
    if cname:
        k = norm(cname)
        cands = mc_name_keys.get(k[:4], [])
        if difflib.get_close_matches(k, cands, n=1, cutoff=0.85):
            fuzzy_hit += 1
            continue
    unmatched += 1

covered = nse_hit + mc_hit + fuzzy_hit
print(f"\nNSE-index ISIN hits: {nse_hit}")
print(f"MC name/slug hits:   {mc_hit}")
print(f"fuzzy hits:          {fuzzy_hit}")
print(f"unmatched:           {unmatched}")
print(f"\nCOVERAGE: {covered}/{len(universe)} = {100*covered/len(universe):.1f}% of company universe")
print(f"COVERAGE (incl INF in denom): {covered}/{len(all_rows)} = {100*covered/len(all_rows):.1f}%")
