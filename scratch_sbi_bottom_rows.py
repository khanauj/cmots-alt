import openpyxl

wb = openpyxl.load_workbook("scratch_sbi_infra_portfolio.xlsx", read_only=True)
ws = wb.active

for idx, row in enumerate(ws.iter_rows(values_only=True)):
    if idx >= 15:
        # Check if the row has any non-None values
        clean_row = [val for val in row if val is not None]
        if clean_row:
            print(f"Row {idx:02d}: {clean_row}")
