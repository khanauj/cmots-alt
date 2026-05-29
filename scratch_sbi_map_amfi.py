import json
import re
from pathlib import Path
import polars as pl
from cmots_alt.normalizers.mf_nav import parse_navall_file

# Load SBI schemes list
with open("scratch_sbi_schemes_list.json", "r", encoding="utf-8") as f:
    sbi_funds = json.load(f)

# Load AMFI schemes from raw file (we parse it using the existing parser)
raw_dir = Path("storage/raw/amfi/navall/dt=2026-05-27")
raw_files = list(raw_dir.glob("*.txt"))
amfi_df = parse_navall_file(raw_files[0])

# Filter AMFI to SBI schemes only
sbi_amfi = amfi_df.filter(pl.col("amc_name").str.contains("SBI"))
print("AMFI SBI schemes count:", sbi_amfi.height)

def normalize_name(name):
    if not name:
        return ""
    name = name.lower()
    # Remove plan/option details to get fund level name
    name = re.sub(r"\b(direct|regular|plan|growth|dividend|idcw|option|payout|reinvestment|reinvest|cumulative|weekly|monthly|quarterly|annual|daily|flexi|half yearly)\b", "", name)
    name = re.sub(r"[^a-z0-9]", "", name)
    return name

# Map SBI funds to AMFI scheme codes
mapped = 0
total_plans = 0
for fund in sbi_funds:
    fund_name = fund["FundName"]
    schemes = fund["Schemes"] or []
    for plan in schemes:
        total_plans += 1
        plan_name = plan["SchemeName"]
        nav = plan["NAV"]
        
        # Try matching by name and NAV
        # Let's normalize the plan name
        norm_plan = normalize_name(plan_name)
        
        # Match candidates in AMFI
        candidates = sbi_amfi.filter(
            (pl.col("scheme_name").str.to_lowercase().str.replace_all(r"[^a-z0-9]", "").str.contains(norm_plan)) |
            (pl.col("nav") == nav)
        )
        
        if candidates.height == 1:
            mapped += 1
        elif candidates.height > 1:
            # Narrow down by plan type (direct/regular) and option
            # Let's see if we can find exact NAV match
            exact_nav = candidates.filter(pl.col("nav") == nav)
            if exact_nav.height == 1:
                mapped += 1
            else:
                # print(f"Multiple matches for {plan_name}: {[r['scheme_name'] for r in candidates.to_dicts()]}")
                pass
        else:
            # print(f"No match for {plan_name}")
            pass

print(f"Mapped {mapped} plans out of {total_plans} total SBI plans.")
