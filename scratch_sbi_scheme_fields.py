import json

with open("scratch_sbi_schemes_list.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    
print("Total schemes:", len(data))
print("Fields in first scheme:", list(data[0].keys()))
for idx, item in enumerate(data[:10]):
    print(f"\nScheme #{idx}:")
    for k in ["FundId", "FundName", "FundCategoryName", "SchemeCode", "SchemeCodes", "AmfiCode", "amficode", "isin", "ISIN"]:
        if k in item:
            print(f"  {k}: {item[k]}")
        # search case insensitively
        for ik in item:
            if ik.lower() == k.lower() and ik not in ["FundId", "FundName", "FundCategoryName"]:
                print(f"  {ik} (case): {item[ik]}")
