"""Inspect BSE JSON field set + Nifty fallback industry values."""
import json
from pathlib import Path
import polars as pl

# BSE JSON: dump keys of first record
bse = sorted(Path("storage/raw/bse/list_of_scrips").glob("dt=*/*.json"))[-1]
data = json.loads(bse.read_text(encoding="utf-8"))
print("BSE record count:", len(data))
print("BSE keys:", list(data[0].keys()))
print("BSE sample:", json.dumps(data[0], indent=0)[:500])
# distinct INDUSTRY values if present
ind_key = next((k for k in data[0] if "indust" in k.lower()), None)
print("\nBSE industry key:", ind_key)
if ind_key:
    vals = {}
    for r in data:
        v = (r.get(ind_key) or "").strip()
        vals[v] = vals.get(v, 0) + 1
    print("distinct BSE industries:", len(vals))
    for v, c in sorted(vals.items(), key=lambda x: -x[1])[:25]:
        print(f"  {c:5}  {v!r}")

# Nifty fallback columns + industry distinct
nf = sorted(Path("storage/raw/nse/industry_fallback").glob("dt=*/*.csv"))[-1]
df = pl.read_csv(nf, infer_schema_length=0)
print("\nNifty fallback columns:", df.columns)
if "Industry" in df.columns:
    print(df.get_column("Industry").value_counts(sort=True).head(15))
