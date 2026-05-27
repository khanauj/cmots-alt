import openpyxl

wb = openpyxl.load_workbook("scratch_sbi_infra_portfolio.xlsx", read_only=True)
ws = wb.active

target_rows = [43, 69, 72, 80, 92, 97, 100]
for r_idx in target_rows:
    row = [cell.value for cell in ws[r_idx + 1]] # 1-based index
    # Find first non-None elements and their positions
    positions = [(idx, val) for idx, val in enumerate(row) if val is not None]
    print(f"Row {r_idx:03d} (len={len(row)}): {positions}")
