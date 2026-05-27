import json

with open("scratch_sbi_schemes_list.json", "r", encoding="utf-8") as f:
    data = json.load(f)

first = data[0]
print("Schemes field type:", type(first.get("Schemes")))
print("Schemes field value:")
print(json.dumps(first.get("Schemes"), indent=2)[:2000])

print("\nScheme field type:", type(first.get("Scheme")))
print("Scheme field value:")
print(json.dumps(first.get("Scheme"), indent=2)[:2000])
