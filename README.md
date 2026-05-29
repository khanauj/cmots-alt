# cmots-alt

CMOTS-alternative Indian financial market data pipeline.

## Phase 1

Local-only. No auth. No cloud. Python 3.12 + uv.

Sources: NSE, BSE, AMFI.

Outputs: a single Excel workbook with 7 sheets (Phase 1 scope).

## Run

```powershell
uv sync
uv run cmots ingest mf-nav
```

Output lands in `storage\output\mf_nav_<YYYY-MM-DD>.xlsx`.
