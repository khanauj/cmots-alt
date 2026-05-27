import sqlite3

conn = sqlite3.connect("storage/cmots_alt.sqlite")
conn.row_factory = sqlite3.Row

# List tables
print("TABLES:")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(f" - {t['name']}")

# Show schema of company and mf_scheme if they exist
for tbl in ["company", "mf_scheme", "mf_holding"]:
    try:
        print(f"\nSCHEMA FOR {tbl}:")
        info = conn.execute(f"PRAGMA table_info({tbl})").fetchall()
        for col in info:
            print(f"  {col['name']}: {col['type']} (nullable={not col['notnull']})")
    except Exception as e:
        print(f"  Error: {e}")

# Check count of rows in company and mf_scheme
for tbl in ["company", "mf_scheme"]:
    try:
        cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"\nRow count in {tbl}: {cnt}")
    except Exception as e:
        pass
