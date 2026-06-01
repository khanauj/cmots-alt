# Phase 3 — Source Mapping

For every module (and the notable fields inside it): **Primary**, **Secondary**,
and **Fallback** source, the access URL/endpoint, and the data provider.

Source legend is in the [README](README.md#source-legend-used-throughout).
Endpoints marked `(html)` require scraping; `(api)` are JSON/CSV; `(file)` are
downloadable bhavcopy/master files; `(xbrl)` are structured filings.

> **Sourcing principle (matches the codebase):** prefer official exchange/regulator
> files (NSE/BSE/AMFI/SEBI) as primary; use aggregators (MC/Screener/Trendlyne/VR)
> as secondary for derived/computed fields; keep a web/file fallback so a single
> endpoint outage never zeroes a module.

---

# EQUITY

## 1. Company / Security Master  [LIVE]

| Field group | Primary | Secondary | Fallback |
|-------------|---------|-----------|----------|
| ISIN, symbol, name | NSE equity master `EQUITY_L.csv` (file) — nseindia.com/market-data/securities-available-for-trading | BSE `ListOfScrips` (api) — api.bseindia.com | NSDL/CDSL ISIN lookup |
| BSE code / group | BSE ListOfScrips (api) | MC company page (html) | Screener (html) |
| CIN, incorporation, RoC | MCA21 (html) — mca.gov.in | annual report (xbrl) | — |
| Sector / industry | NSE 4-level taxonomy (file) | MC sector map (config/mc_sector_map.yaml) | Screener sector |
| Face value, group | NSE/BSE master (file) | MC (html) | Screener |
| Registered office, website, RTA, auditor | NSE/BSE corp-info (html) | annual report | MCA |

## 2. Listing & Capital Structure  [NEXT]

| Field | Primary | Secondary | Fallback |
|-------|---------|-----------|----------|
| Authorised/issued/paid-up capital | MCA / annual report (xbrl) | Screener (html) | MC |
| Shares outstanding, free-float | NSE indices free-float file | BSE | Screener |
| Listing/IPO dates | NSE/BSE listing record (api) | Chittorgarh (html) | MC |
| Delisting/suspension | NSE/BSE circulars (html) | SEBI | — |

## 3. Price Data — EOD  [LIVE]

| Field | Primary | Secondary | Fallback |
|-------|---------|-----------|----------|
| OHLC, volume, turnover, trades | NSE Bhavcopy `sec_bhavdata_full` (file) — nseindia.com/all-reports | BSE Bhavcopy (file) — bseindia.com | Yahoo Finance (api) |
| Delivery qty / % | NSE security-wise delivery (file, in sec_bhavdata_full) | BSE delivery (file) | — |
| VWAP | NSE bhavcopy (file) | computed from intraday | — |
| 52wk high/low | NSE bhavcopy / quote (api) | BSE | Yahoo |
| Circuit / price band | NSE price-band file (file) | BSE | — |

## 4. Price Data — Intraday / Real-time  [ROADMAP]

| Field | Primary | Secondary | Fallback |
|-------|---------|-----------|----------|
| Tick / LTP / depth | Broker WebSocket (Kite/Upstox/Angel/Fyers) | NSE/BSE quote (api, delayed) | Yahoo (15-min delayed) |
| Intraday bars | Broker historical-candle API | computed from ticks | — |
| Pre-open prices | NSE pre-open (api) | BSE | — |

## 5. Adjusted Price History  [NEXT]
**Derived in-house** from Price EOD (3) + Corporate Actions (6). Cross-check fallback: Yahoo adjusted close (api), Screener price chart.

## 6. Corporate Actions  [LIVE]

| Field | Primary | Secondary | Fallback |
|-------|---------|-----------|----------|
| Dividends/bonus/split/rights | NSE Corporate Actions (api) — nseindia.com/api/corporates-corporateActions | BSE Corp Actions (api) — bseindia.com | MC corporate-actions (html) |
| Buyback | SEBI / exchange announcements (html) | BSE | MC |
| Mergers / name change / FV change | BSE announcements (api) | NSE circulars | MCA |

## 7. Financial Statements  [NEXT]

| Field | Primary | Secondary | Fallback |
|-------|---------|-----------|----------|
| Quarterly results | BSE/NSE XBRL financial results (xbrl) | Screener (html) — screener.in/company | MC financials (html) |
| Annual P&L / BS / CF | Annual report XBRL via BSE (xbrl) | Screener | MC / Tickertape |
| Banking/NBFC schedules | XBRL (banking taxonomy) | Screener | MC |
| Segment / notes | Annual report (xbrl/pdf) | — | — |

## 8. Ratios  [NEXT]
**Derived in-house** from Financial Statements (7) + Price (3). Cross-check: Screener (html), Trendlyne (html), Tickertape.

## 9. Valuation Metrics  [NEXT]
**Derived in-house**: MarketCap = price × shares; PE/PB/EV from (3)+(7)+(2). Cross-check: Screener, Trendlyne, MC.

## 10. Shareholding Pattern  [LIVE]

| Field | Primary | Secondary | Fallback |
|-------|---------|-----------|----------|
| Promoter/FII/DII/public % | NSE shareholding master + XBRL detail (xbrl/api) | BSE shareholding (no public endpoint → scrape) | MC / Trendlyne (html) |
| Pledge % | NSE/BSE pledge disclosure (xbrl) | Trendlyne | MC |
| No. of shareholders | XBRL SHP (xbrl) | — | — |

## 11. Institutional & Major Holders  [ROADMAP]
Primary: SHP XBRL "holders >1%" (xbrl) + MF portfolio reverse-map (in-house from MF Holdings). Secondary: Trendlyne (html), MC. Fallback: Value Research stock pages.

## 12. Board / Management / Governance  [ROADMAP]
Primary: MCA director master (html) + annual report (xbrl). Secondary: BSE/NSE corp-governance filings. Fallback: Tofler / Zauba (html).

## 13. Announcements & Filings  [ROADMAP]
Primary: BSE announcements (api) — api.bseindia.com/.../AnnGetData; NSE announcements (api). Secondary: MC. Fallback: company IR page.

## 14. Events & Calendar  [ROADMAP]
Primary: NSE/BSE board-meeting & event calendar (api). Secondary: MC. Fallback: Trendlyne.

## 15. Insider Trading (PIT)  [ROADMAP]
Primary: NSE/BSE insider-trading disclosures (api). Secondary: Trendlyne. Fallback: SEBI.

## 16/17. Bulk / Block Deals  [ROADMAP]
Primary: NSE bulk/block deal files (file) — nseindia.com/report-detail/display-bulk-and-block-deals; BSE (file). Secondary: MC. Fallback: Trendlyne.

## 18. Short Selling / SLB  [ROADMAP]
Primary: NSE SLB & short-selling reports (file). Secondary: — . Fallback: —.

## 19. Surveillance Flags  [ROADMAP]
Primary: NSE/BSE ASM & GSM lists (file/html) + F&O ban list (api). Secondary: MC. Fallback: Trendlyne.

## 20. Credit Ratings  [ROADMAP]
Primary: rating-agency sites — CRISIL/ICRA/CARE/India Ratings (html). Secondary: SEBI rating disclosure (html). Fallback: exchange announcements.

## 21. Technical Indicators  [ROADMAP]
**Derived in-house** from Price EOD (3). Cross-check: Trendlyne, Investing.com, Chartink.

## 22. Derivatives (F&O)  [ROADMAP]
Primary: NSE F&O bhavcopy + option chain (file/api) — nseindia.com/api/option-chain-indices. Secondary: broker API. Fallback: —.

## 23. Index Data  [ROADMAP]
Primary: NSE indices (file/api) — niftyindices.com; BSE indices. Secondary: MC. Fallback: Yahoo.

## 24. Sector Classification  [LIVE]
Primary: NSE 4-level industry classification (file). Secondary: MC sector map (config). Fallback: BSE / Screener.

## 25. Peer Comparison  [ROADMAP]
**Derived in-house** by grouping co_codes on sector + mcap. Cross-check: Screener peers, Trendlyne.

## 26. Analyst Estimates  [ROADMAP]
Primary: Trendlyne / MC consensus (html). Secondary: Tickertape. Fallback: Refinitiv/Bloomberg (licensed).

## 27. News & Research  [ROADMAP]
Primary: MC news + RSS (html/rss). Secondary: ET Markets, BSE/NSE announcements. Fallback: Google News RSS.

## 28. Primary Market / IPO  [ROADMAP]
Primary: NSE/BSE IPO pages + subscription (api). Secondary: Chittorgarh (html). Fallback: MC IPO.

## 29. ESG  [ROADMAP]
Primary: BRSR via BSE (xbrl). Secondary: Sustainalytics/MSCI (licensed). Fallback: company reports.

## 30. Market Statistics  [ROADMAP]
Primary: NSE/BSE market-summary (api) + FII/DII (NSE/MC). Secondary: MC. Fallback: —.

---

# MUTUAL FUNDS

## 1. AMC Master  [NEXT]
Primary: AMFI AMC list (file/html) — amfiindia.com. Secondary: SEBI MF intermediaries (html). Fallback: AMC websites.

## 2. Scheme Master  [LIVE]
Primary: AMFI scheme master (file) — amfiindia.com NAVAll / scheme-details. Secondary: AMC portals. Fallback: Value Research / MC.

## 3. NAV Data  [LIVE]
Primary: AMFI NAVAll.txt daily (file) — amfiindia.com/spages/NAVAll.txt; historical via AMFI NAV history (api). Secondary: AMC portal. Fallback: Value Research / MFAPI.in.

## 4. Holdings / Portfolio  [LIVE]
Primary: AMC monthly portfolio disclosure (file: xlsx/xml) — per-AMC investor portal; SEBI XBRL. Secondary: Value Research (html). Fallback: Morningstar.
*(co_code mapping uses the in-house Identifier Crosswalk R1.)*

## 5. Asset Allocation  [NEXT]
**Derived in-house** from Holdings (4). Cross-check: Value Research, MC.

## 6. Sector Allocation  [NEXT]
**Derived in-house** from Holdings (4) + Sector Master (R2). Cross-check: Value Research, MC.

## 7. Returns  [NEXT]
**Derived in-house** from NAV (3) + corporate-action/IDCW adjustment. Cross-check: Value Research, AMFI, MC.

## 8. Risk Metrics  [NEXT]
**Derived in-house** from NAV (3) + benchmark (R5) + risk-free (R6). Cross-check: Value Research, Morningstar.

## 9. AUM / Fund Size  [NEXT]
Primary: AMFI monthly AUM disclosure (file) — amfiindia.com. Secondary: AMC factsheet. Fallback: Value Research.

## 10. Fund Manager  [NEXT]
Primary: AMC factsheet / SID (pdf/html). Secondary: Value Research. Fallback: Morningstar.

## 11. Expense & Load  [NEXT]
Primary: AMC TER disclosure (file) — per-AMC + AMFI. Secondary: Value Research. Fallback: scheme SID.

## 12. Dividend / IDCW History  [ROADMAP]
Primary: AMFI / AMC IDCW disclosure (file). Secondary: Value Research. Fallback: MC.

## 13. Portfolio Analytics  [ROADMAP]
**Derived in-house** from Holdings (4). Cross-check: Value Research (turnover, overlap), Morningstar.

## 14. Debt Analytics  [ROADMAP]
Primary: AMC factsheet (YTM, duration) (pdf) + Holdings (4). Secondary: Value Research. Fallback: Morningstar.

## 15. Scheme Categorisation  [NEXT]
Primary: SEBI categorisation circular mapping (in-house) + AMFI. Secondary: Value Research. Fallback: AMC SID.

## 16. Ratings & Rankings  [ROADMAP]
Primary: CRISIL MF ranks (html), Value Research stars (html), Morningstar (html). Secondary: —. Fallback: —.

## 17. NFO  [ROADMAP]
Primary: AMFI NFO list + AMC (html). Secondary: Value Research. Fallback: MC.

## 18. Transactions / Plans  [ROADMAP]
Primary: AMC SID / portal (html). Secondary: Value Research. Fallback: —.

## 19. Taxation  [ROADMAP]
**Derived in-house** rule table from category (15) + Finance Act. Cross-check: Value Research.

---

# CROSS-DOMAIN / REFERENCE

| Module | Primary | Secondary | Fallback |
|--------|---------|-----------|----------|
| R1 Identifier Crosswalk [LIVE] | in-house resolver (NSE/BSE/AMFI masters) | config/identifier_aliases.csv | manual override |
| R2 Sector Master [LIVE] | NSE taxonomy (file) | config/sector_master.csv | MC map |
| R3 Trading Calendar [ROADMAP] | NSE/BSE holiday list (api) | RBI holiday list | — |
| R4 FX Rates [ROADMAP] | RBI reference rate (file) | — | Yahoo |
| R5 Benchmark Index Master [ROADMAP] | niftyindices.com (file) | BSE | — |
| R6 Macro Indicators [ROADMAP] | RBI DBIE (api) + MOSPI | — | TradingEconomics |
| R7 RTA Master [ROADMAP] | SEBI RTA list (html) | — | — |
| R8 Rating Agency Master [ROADMAP] | SEBI CRA list (html) | — | — |
| R9 Ingestion Manifest [LIVE] | in-house (SQLite) | — | — |
| R10 Data Quality [LIVE] | in-house resolver report | — | — |

---

## Source-reliability notes (carried from existing pipelines)

- **BSE shareholding has no clean public endpoint** → NSE master + XBRL is primary;
  BSE is scrape-only fallback (see `memory/shareholding-pipeline.md`).
- **MF Holdings parser is generic and AMC-agnostic** (no per-AMC branching) —
  proven on SBI + ICICI (see `memory/mf-holdings-parser.md`).
- **Sector coverage is frozen at 75.6%** for CompanyMaster V1 — do not over-optimise
  the sector source chain (see `memory/sector-coverage-ceiling.md`).
- **NSE endpoints require a cookie/referer warm-up**; all NSE access goes through the
  project's HTTP fetcher with retry (`src/cmots_alt/fetchers/http.py`).
