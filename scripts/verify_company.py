import polars as pl

g = pl.read_parquet("storage/processed/gold/company_master/dt=2026-05-27.parquet")

print("rows:", g.height)
print("\nmcaptype distribution:")
print(g.group_by("mcaptype").len().sort("len", descending=True))

print("\nLarge Caps sample:")
print(
    g.filter(pl.col("mcaptype") == "Large Cap")
    .select("CompanyName", "CompanyShortName", "BSEGroup")
    .head(8)
)

print("\norphan-trim check:")
sub = g.filter(pl.col("CompanyName").str.contains("(?i)veto|switchgear"))
for r in sub.select("CompanyName", "CompanyShortName").iter_rows():
    print(f"  {r[0]!r:48} -> {r[1]!r}")

print("\nfield completeness (non-null %):")
for c in g.columns:
    nn = 100 * g.get_column(c).drop_nulls().len() / g.height
    print(f"  {c:18} {nn:5.1f}%")
