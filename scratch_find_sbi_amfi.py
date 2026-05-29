from pathlib import Path
import re

raw_dir = Path("storage/raw/amfi/navall/dt=2026-05-27")
raw_files = list(raw_dir.glob("*.txt"))

if not raw_files:
    print("No AMFI files found.")
else:
    amfi_file = raw_files[0]
    print("Reading", amfi_file)
    content = amfi_file.read_text(encoding="utf-8")
    
    # Let's search for "SBI Mutual Fund" and print adjacent lines
    lines = content.splitlines()
    found_amc = False
    count = 0
    for idx, line in enumerate(lines):
        if "SBI Mutual Fund" in line:
            print(f"Line {idx}: {line}")
            found_amc = True
            # print next 20 lines
            for j in range(idx, min(len(lines), idx + 30)):
                print(f"  {j}: {lines[j]}")
            count += 1
            if count >= 3:
                break
