# Phase 6 — API Design

The REST API catalog that exposes the [data tree](phase1-data-tree.md). This is
generated **only after** the tree, fields, sources, refresh, and database are
fixed (Phases 1–5).

**Single source of truth:** the catalog rows live in
[`generate_catalog_workbook.py`](generate_catalog_workbook.py) as the `EQUITY`
and `MUTUAL_FUNDS` lists. That script renders both this contract *and* the
Phase-7 Excel workbook, so the two can never drift.

- Base URL: `https://api.cmots-alt.local/api/v1`
- Style: REST + JSON; aligned with the existing FastAPI routers
  (`/stocks`, `/stock/{symbol}/…`, `/mutual-funds`, `/mutual-fund/{scheme_code}/…`).
- Auth (roadmap): API key header `X-API-Key`; rate-limited per key.
- Every endpoint documents: **API Number · Report Name · API URL · Frequency ·
  Updation Time · Input · Input Description · Output · Data Type · Output Description.**

## Counts

| Sheet | APIs | Range |
|-------|------|-------|
| EQUITY | 57 | E001–E057 |
| MUTUAL FUNDS | 32 | M001–M032 |

## Equity API map (E001–E057)

| # | Report | URL (suffix) | Freq |
|---|--------|--------------|------|
| E001 | List Companies | `/stocks` | Daily |
| E002 | Company Master / Detail | `/stock/{symbol}` | Daily |
| E003 | Identifier Crosswalk | `/stock/{symbol}/identifiers` | Daily |
| E004 | Capital Structure | `/stock/{symbol}/capital-structure` | Weekly |
| E005 | EOD Price History | `/stock/{symbol}/prices` | Daily |
| E006 | Latest Quote | `/stock/{symbol}/quote` | Daily |
| E007 | Market EOD (Bhavcopy) | `/market/eod` | Daily |
| E008 | Intraday Bars | `/stock/{symbol}/intraday` | Real-time |
| E009 | Market Depth | `/stock/{symbol}/depth` | Real-time |
| E010 | Adjusted Price History | `/stock/{symbol}/prices/adjusted` | Daily |
| E011 | 52-Week & Price Stats | `/stock/{symbol}/price-stats` | Daily |
| E012 | Price Band / Circuit | `/stock/{symbol}/price-band` | Daily |
| E013 | Corporate Actions | `/stock/{symbol}/corporate-actions` | Daily |
| E014 | Dividends History | `/stock/{symbol}/dividends` | Daily |
| E015 | Splits & Bonus | `/stock/{symbol}/splits-bonus` | Daily |
| E016 | Profit & Loss | `/stock/{symbol}/financials/pnl` | Quarterly |
| E017 | Balance Sheet | `/stock/{symbol}/financials/balance-sheet` | Quarterly |
| E018 | Cash Flow | `/stock/{symbol}/financials/cashflow` | Quarterly |
| E019 | Quarterly Results | `/stock/{symbol}/results/quarterly` | Quarterly |
| E020 | Financial Ratios | `/stock/{symbol}/ratios` | Quarterly |
| E021 | Valuation Metrics | `/stock/{symbol}/valuation` | Daily |
| E022 | Shareholding Pattern | `/stock/{symbol}/shareholding` | Quarterly |
| E023 | Shareholding Holders (>1%) | `/stock/{symbol}/shareholding/holders` | Quarterly |
| E024 | MFs Holding This Stock | `/stock/{symbol}/mf-holders` | Monthly |
| E025 | Promoter Pledge | `/stock/{symbol}/pledge` | Quarterly |
| E026 | Board & Management | `/stock/{symbol}/management` | Quarterly |
| E027 | Announcements | `/stock/{symbol}/announcements` | Real-time |
| E028 | Events Calendar | `/stock/{symbol}/events` | Daily |
| E029 | Insider Trading (PIT) | `/stock/{symbol}/insider-trades` | Daily |
| E030 | Bulk Deals | `/stock/{symbol}/bulk-deals` | Daily |
| E031 | Block Deals | `/stock/{symbol}/block-deals` | Daily |
| E032 | Short Selling / SLB | `/stock/{symbol}/short-selling` | Daily |
| E033 | Surveillance Flags | `/stock/{symbol}/surveillance` | Daily |
| E034 | Credit Ratings | `/stock/{symbol}/credit-ratings` | Weekly |
| E035 | Technical Indicators | `/stock/{symbol}/technicals` | Daily |
| E036 | Pivot Levels | `/stock/{symbol}/pivots` | Daily |
| E037 | Risk / Beta | `/stock/{symbol}/risk` | Daily |
| E038 | Futures (F&O) | `/stock/{symbol}/derivatives/futures` | Daily |
| E039 | Option Chain | `/stock/{symbol}/derivatives/options` | Intraday |
| E040 | Peer Comparison | `/stock/{symbol}/peers` | Quarterly |
| E041 | Analyst Estimates | `/stock/{symbol}/estimates` | Weekly |
| E042 | News | `/stock/{symbol}/news` | Real-time |
| E043 | ESG Scores | `/stock/{symbol}/esg` | Annual |
| E044 | List Sectors | `/sectors` | Monthly |
| E045 | Sector Constituents | `/sector/{sector_code}/companies` | Daily |
| E046 | List Indices | `/indices` | Daily |
| E047 | Index Value History | `/index/{index_code}/values` | Daily |
| E048 | Index Constituents | `/index/{index_code}/constituents` | Daily |
| E049 | Market Breadth | `/market/breadth` | Daily |
| E050 | FII / DII Flows | `/market/fii-dii` | Daily |
| E051 | Bulk Deals (Market) | `/market/bulk-deals` | Daily |
| E052 | Block Deals (Market) | `/market/block-deals` | Daily |
| E053 | IPO Calendar | `/ipos` | Daily |
| E054 | IPO Detail / Subscription | `/ipo/{issue_id}` | Daily |
| E055 | Market Movers | `/market/movers` | Daily |
| E056 | Trading Calendar | `/calendar` | Annual |
| E057 | Corporate Actions (Market) | `/market/corporate-actions` | Daily |

## Mutual Fund API map (M001–M032)

| # | Report | URL (suffix) | Freq |
|---|--------|--------------|------|
| M001 | List Schemes | `/mutual-funds` | Daily |
| M002 | Scheme Master / Detail | `/mutual-fund/{scheme_code}` | Daily |
| M003 | NAV History | `/mutual-fund/{scheme_code}/nav` | Daily |
| M004 | Latest NAV | `/mutual-fund/{scheme_code}/nav/latest` | Daily |
| M005 | NAV (Market) by Date | `/mf/nav` | Daily |
| M006 | Portfolio Holdings | `/mutual-fund/{scheme_code}/holdings` | Monthly |
| M007 | Asset Allocation | `/mutual-fund/{scheme_code}/asset-allocation` | Monthly |
| M008 | Sector Allocation | `/mutual-fund/{scheme_code}/sector-allocation` | Monthly |
| M009 | Returns | `/mutual-fund/{scheme_code}/returns` | Daily |
| M010 | Rolling Returns | `/mutual-fund/{scheme_code}/returns/rolling` | Weekly |
| M011 | SIP Returns (XIRR) | `/mutual-fund/{scheme_code}/returns/sip` | Daily |
| M012 | Risk Metrics | `/mutual-fund/{scheme_code}/risk` | Weekly |
| M013 | AUM History | `/mutual-fund/{scheme_code}/aum` | Monthly |
| M014 | Expense & Load | `/mutual-fund/{scheme_code}/expense` | Monthly |
| M015 | IDCW History | `/mutual-fund/{scheme_code}/idcw` | Event-driven |
| M016 | Fund Manager | `/mutual-fund/{scheme_code}/manager` | Monthly |
| M017 | Portfolio Analytics | `/mutual-fund/{scheme_code}/portfolio-analytics` | Monthly |
| M018 | Holdings Overlap | `/mutual-fund/overlap` | Monthly |
| M019 | Debt Analytics | `/mutual-fund/{scheme_code}/debt-analytics` | Monthly |
| M020 | Categorisation | `/mutual-fund/{scheme_code}/category` | Monthly |
| M021 | Ratings & Rankings | `/mutual-fund/{scheme_code}/ratings` | Monthly |
| M022 | List AMCs | `/amcs` | Monthly |
| M023 | AMC Detail | `/amc/{amc_code}` | Monthly |
| M024 | AMC Schemes | `/amc/{amc_code}/schemes` | Daily |
| M025 | List Fund Managers | `/fund-managers` | Monthly |
| M026 | Fund Manager Detail | `/fund-manager/{manager_id}` | Monthly |
| M027 | NFO List | `/nfos` | Daily |
| M028 | List Categories | `/mf/categories` | Monthly |
| M029 | Category Leaderboard | `/mf/category/{category}/schemes` | Daily |
| M030 | Taxation | `/mutual-fund/{scheme_code}/taxation` | Annual |
| M031 | Compare Schemes | `/mf/compare` | Daily |
| M032 | Stock Exposure (Reverse) | `/mf/stock-exposure/{symbol}` | Monthly |

## Full field-level detail

The complete per-API specification — every Input, Input Description, Output
field list, Data Type, and Output Description — is in the generated workbook
(Phase 7), sheets **EQUITY** and **MUTUAL FUNDS**. Regenerate with:

```powershell
python docs/blueprint/generate_catalog_workbook.py
```

## Conventions

- **Path vs query inputs:** `{symbol}`/`{scheme_code}`/`{code}` are path params;
  `from`, `to`, `limit`, `offset`, `exchange`, `date` are query params (matching
  the live routers).
- **Pagination:** list endpoints take `limit` (default 50, max 1000) + `offset`.
- **Date format:** ISO `YYYY-MM-DD` in/out; the Excel exporters render `DD-MM-YYYY`.
- **Errors:** `404` unknown symbol/scheme (`MessageResponse`), `422` validation,
  `500` internal (matching `api/main.py`).
- **Status semantics:** LIVE endpoints serve gold Parquet today; NEXT/ROADMAP
  endpoints return `501 Not Implemented` until their pipeline lands (current
  scaffold behaviour).
