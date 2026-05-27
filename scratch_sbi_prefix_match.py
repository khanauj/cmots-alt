import json
import re
from pathlib import Path
import polars as pl
from cmots_alt.normalizers.mf_nav import parse_navall_file

with open("scratch_sbi_schemes_list.json", "r", encoding="utf-8") as f:
    sbi_funds = json.load(f)

raw_dir = Path("storage/raw/amfi/navall/dt=2026-05-27")
raw_files = list(raw_dir.glob("*.txt"))
amfi_df = parse_navall_file(raw_files[0])
sbi_amfi = amfi_df.filter(pl.col("amc_name").str.contains("SBI"))

def clean_for_match(name):
    if not name:
        return ""
    name = name.lower()
    name = name.replace("and", "").replace("&", "")
    name = re.sub(r"\(.*?\)", "", name)
    name = re.sub(r"formerly known as", "", name)
    name = re.sub(r"[^a-z0-9]", "", name)
    return name

mapped_funds = 0
for fund in sbi_funds:
    fund_name = fund["FundName"]
    norm_fund = clean_for_match(fund_name)
    
    # Try prefix matching against AMFI scheme names
    matches = []
    for row in sbi_amfi.to_dicts():
        norm_amfi = clean_for_match(row["scheme_name"])
        if norm_amfi.startswith(norm_fund) or norm_fund in norm_amfi or norm_amfi in norm_fund:
            matches.append(row["scheme_code"])
            
    if matches:
        mapped_funds += 1
    else:
        print(f"Unmapped Fund: {fund_name}")
        
print(f"Mapped {mapped_funds} funds out of {len(sbi_funds)}")
