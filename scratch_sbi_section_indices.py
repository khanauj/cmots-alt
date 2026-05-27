import openpyxl

wb = openpyxl.load_workbook("scratch_sbi_infra_portfolio.xlsx", read_only=True)
ws = wb.active

target_rows = [7, 8, 9, 49, 51, 53, 63, 64, 78, 79, 83, 85, 87, 89, 91, 95, 96]
for r_idx in target_rows:
    row = [cell.value for cell in ws[r_idx + 1]]
    positions = [(idx, val) for idx, val in enumerate(row) if val is not None]
    print(f"Row {r_idx:03d}: {positions}")
