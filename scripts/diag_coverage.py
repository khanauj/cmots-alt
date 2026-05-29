import re, sys, yaml
from collections import Counter
import polars as pl
sys.stdout.reconfigure(encoding="utf-8")

root = "."
# Load current maps
tax = yaml.safe_load(open("config/sector_taxonomy.yaml", encoding="utf-8"))
mcm = yaml.safe_load(open("config/mc_sector_map.yaml", encoding="utf-8"))
nse_map = {re.sub(r"\s+"," ",k.strip().lower()) for k in tax["nse_industry_map"]}
mc_map = set(mcm["mc_sector_map"])

def ni(s): return re.sub(r"\s+"," ",s.strip().lower())
def nn(s):
    s=s.lower().replace("&","and")
    s=re.sub(r"\b(ltd|limited|pvt|private|the|co|company|corp|corporation)\b"," ",s)
    return re.sub(r"[^a-z0-9]","",s)

# A. Nifty industry distinct values + mapped?
nf = sorted(__import__("glob").glob("storage/raw/nse/industry_fallback/dt=*/*.csv"))[-1]
ndf = pl.read_csv(nf, infer_schema_length=0)
ndf = ndf.rename({c:c.strip() for c in ndf.columns})
icol = [c for c in ndf.columns if c.lower()=="industry"][0]
print("=== NSE Nifty 'Industry' values (mapped? Y/N) ===")
for ind, n in ndf.group_by(icol).len().sort("len",descending=True).iter_rows():
    print(f"  {'Y' if ni(ind) in nse_map else 'N'}  {n:4}  {ind!r}")

# B. Unmapped MC slugs for OUR matched universe
mc = pl.read_parquet("storage/cache/mc_directory.parquet")
gold = pl.read_parquet("storage/processed/gold/company_master/dt=2026-05-27.parquet")
our = {nn(n) for n in gold.filter(~pl.col("isin").str.starts_with("INF"))["CompanyName"].drop_nulls()}
# build mc name->slug
mc_by_key = {}
for slug,cs,code,name in mc.iter_rows():
    mc_by_key[cs]=slug; mc_by_key[nn(name)]=slug
# for our companies matched, get slug, count unmapped
unmapped = Counter()
for k in our:
    slug = mc_by_key.get(k)
    if slug and slug not in mc_map:
        unmapped[slug]+=1
print("\n=== Unmapped MC slugs hit by OUR universe (top 40) ===")
for slug,n in unmapped.most_common(40):
    print(f"  {n:4}  {slug}")
print("total our-universe companies on unmapped MC slugs:", sum(unmapped.values()))
