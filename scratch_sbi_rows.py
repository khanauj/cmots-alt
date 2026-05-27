import openpyxl

wb = openpyxl.load_workbook("scratch_sbi_infra_portfolio.xlsx", read_only=True)
ws = wb.active
print(f"Sheet title: {ws.title}")
for idx, row in enumerate(ws.iter_rows(values_only=True)):
    if idx < 15:
        # Strip trailing None values to make printout readable
        clean_row = []
        for val in row:
            if val is not None:
                clean_row.append(val)
            else:
                if len(clean_row) > 0 and clean_row[-1] is not None:
                    clean_row.append(None)
        # trim trailing Nones
        while clean_row and clean_row[-1] is None:
            clean_row.pop()
        print(f"Row {idx:02d}: {clean_row}")
