from pathlib import Path

raw_dir = Path("storage/raw/amfi/navall/dt=2026-05-27")
raw_files = list(raw_dir.glob("*.txt"))

if raw_files:
    amfi_file = raw_files[0]
    content = amfi_file.read_text(encoding="utf-8")
    for idx, line in enumerate(content.splitlines()):
        if "SBI Infrastructure Fund" in line:
            print(f"Line {idx}: {line}")
