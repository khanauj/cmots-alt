# CMOTS-Replacement — Master Data Blueprint

This folder is the **complete architectural blueprint** for an Indian financial
market data platform that replaces CMOTS (and rhymes with the architecture of
Bloomberg / Refinitiv / Capital IQ / FactSet). It is built **tree-first**: every
dataset, field, source, refresh cadence, table, and API is catalogued *before*
any further implementation.

It is intentionally exhaustive. Nothing is summarised away.

## How to read this blueprint

The blueprint is delivered in 7 phases. Each phase builds on the previous one.

| Phase | File | What it answers |
|------|------|-----------------|
| 1 | [`phase1-data-tree.md`](phase1-data-tree.md) | What datasets exist? (the hierarchy) |
| 2 | [`phase2-field-inventory.md`](phase2-field-inventory.md) | What are *all* the fields in each dataset? |
| 3 | [`phase3-source-mapping.md`](phase3-source-mapping.md) | Where does each field come from? (primary / secondary / fallback) |
| 4 | [`phase4-refresh-strategy.md`](phase4-refresh-strategy.md) | How often is each module refreshed and when? |
| 5 | [`phase5-database-design.md`](phase5-database-design.md) | How is it stored? (parent/child tables, PK/FK, relationships) |
| 6 | [`phase6-api-design.md`](phase6-api-design.md) | What APIs expose it? (CMOTS-style report catalog) |
| 7 | `generate_catalog_workbook.py` → `CMOTS_Replacement_API_Catalog.xlsx` | The deliverable Excel workbook (3 sheets) |

## Alignment with the existing codebase

This blueprint is **not greenfield** — it extends what already exists in
`src/cmots_alt`:

- The canonical entity is the **`company`** row, keyed by **`isin`**, with an
  internal surrogate **`co_code`** (mirrors CMOTS's `co_code`).
- Gold/output columns use **PascalCase** (`TradeDate`, `BSECode`, `PromoterPct`),
  while internal join keys stay lowercase (`co_code`, `isin`).
- Live modules today: Company Master, Equity EOD, Corporate Actions,
  Shareholding, MF Scheme Master, MF NAV, MF Holdings.
- Everything else in this tree is **roadmap** — designed here so the schema and
  API surface are stable before code lands.

A field/module is tagged with its build status throughout:

- **[LIVE]** — implemented and producing gold output today
- **[NEXT]** — designed, partially sourced, next to build
- **[ROADMAP]** — catalogued for completeness, not yet sourced

## Regenerating the Excel workbook

```powershell
python docs/blueprint/generate_catalog_workbook.py
# → docs/blueprint/CMOTS_Replacement_API_Catalog.xlsx
```

## Source legend (used throughout)

| Code | Provider | Base |
|------|----------|------|
| NSE | NSE India | https://www.nseindia.com |
| BSE | BSE India | https://www.bseindia.com |
| AMFI | Assoc. of Mutual Funds in India | https://www.amfiindia.com |
| SEBI | Securities & Exchange Board of India | https://www.sebi.gov.in |
| MCA | Ministry of Corporate Affairs | https://www.mca.gov.in |
| RBI | Reserve Bank of India | https://www.rbi.org.in |
| MC | Moneycontrol | https://www.moneycontrol.com |
| SCR | Screener.in | https://www.screener.in |
| TL | Trendlyne | https://trendlyne.com |
| VR | Value Research | https://www.valueresearchonline.com |
| MS | Morningstar India | https://www.morningstar.in |
| YF | Yahoo Finance | https://finance.yahoo.com |
| TT | Tickertape | https://www.tickertape.in |
| AMC | AMC investor portals + SEBI XBRL | (per-AMC) |
| FILING | Corporate filings (XBRL / annual reports) | (per-company) |
