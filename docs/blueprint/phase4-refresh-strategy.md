# Phase 4 — Refresh Strategy

For every module: refresh **frequency** and the **recommended update time (IST)**.
All times are India Standard Time. The cadence drives the scheduler
(`src/cmots_alt/api/routers/scheduler.py`).

Frequency vocabulary: `Real-time` · `Intraday` · `Daily` · `Weekly` · `Monthly` ·
`Quarterly` · `Annual` · `Event-driven` · `On-demand`.

> **Why these times:** NSE/BSE bhavcopy publishes ~18:00–19:00 IST after settlement;
> AMFI NAV publishes ~22:30–23:30 IST; corporate disclosures stream during market
> hours; MF portfolios disclose monthly (within 10 days of month-end) and quarterly.

---

# EQUITY

| # | Module | Frequency | Recommended update time (IST) | Notes |
|---|--------|-----------|-------------------------------|-------|
| 1 | Company / Security Master | Daily | 20:00 | Pick up new listings / symbol changes post-close |
| 2 | Listing & Capital Structure | Weekly + Event-driven | Sun 08:00 | Re-pull on capital-event announcement |
| 3 | Price Data — EOD | Daily (trading days) | 18:30 | After NSE/BSE bhavcopy; delivery file lags to ~19:00 |
| 4 | Price Data — Intraday/RT | Real-time / Intraday | continuous 09:15–15:30 | Bars persisted every minute; depth streamed |
| 5 | Adjusted Price History | Daily | 19:30 | Recompute after EOD + corporate-action refresh |
| 6 | Corporate Actions | Daily + Event-driven | 19:00 | Ex-dates trigger price-adjust recompute |
| 7 | Financial Statements | Quarterly + Event-driven | result-day 21:00 | Driven by results calendar; backfill annual at year-end |
| 8 | Ratios | Quarterly | result-day 22:00 | After statements land (derived) |
| 9 | Valuation Metrics | Daily | 19:45 | Mcap/PE move with price; recompute post-EOD |
| 10 | Shareholding Pattern | Quarterly | within 21 days of quarter-end, 20:00 | SEBI deadline is 21 days post quarter-end |
| 11 | Institutional & Major Holders | Quarterly | quarter-end + 25 days, 20:00 | After SHP + MF portfolios |
| 12 | Board / Management | Quarterly + Event-driven | Sun 09:00 | Re-pull on appointment/cessation filings |
| 13 | Announcements & Filings | Real-time / Intraday | every 15 min, 09:00–18:00 | Streamed during disclosure hours |
| 14 | Events & Calendar | Daily | 07:30 | Refresh forward calendar each morning |
| 15 | Insider Trading (PIT) | Daily | 19:30 | Disclosures filed within 2 trading days |
| 16 | Bulk Deals | Daily (trading days) | 19:00 | Published with EOD reports |
| 17 | Block Deals | Daily (trading days) | 19:00 | Published with EOD reports |
| 18 | Short Selling / SLB | Daily | 20:00 | NSE SLB/short report |
| 19 | Surveillance Flags (ASM/GSM/ban) | Daily | 18:00 | F&O ban list also pre-open 08:45 |
| 20 | Credit Ratings | Weekly + Event-driven | Sat 09:00 | Re-pull on rating-action announcement |
| 21 | Technical Indicators | Daily | 19:45 | Derived after EOD |
| 22 | Derivatives (F&O) | Daily + Intraday | EOD 18:30; OI intraday | Option chain snapshots intraday |
| 23 | Index Data | Daily | 18:30 | Index bhavcopy + constituents |
| 24 | Sector Classification | Monthly | 1st of month 08:00 | Taxonomy changes are infrequent |
| 25 | Peer Comparison | Quarterly | quarter-end + 25 days | Recompute after ratios/valuation |
| 26 | Analyst Estimates | Weekly + Event-driven | Sat 10:00 | Revisions cluster around results |
| 27 | News & Research | Real-time / Intraday | every 30 min | RSS/poll |
| 28 | Primary Market / IPO | Daily | 20:00 | Subscription daily during issue; GMP intraday |
| 29 | ESG | Annual + Event-driven | post-BRSR-filing | Annual disclosure cycle |
| 30 | Market Statistics | Daily | 18:30 | With EOD; FII/DII provisional ~17:30, final ~21:00 |

---

# MUTUAL FUNDS

| # | Module | Frequency | Recommended update time (IST) | Notes |
|---|--------|-----------|-------------------------------|-------|
| 1 | AMC Master | Monthly | 1st of month 09:00 | New AMCs are rare |
| 2 | Scheme Master | Daily | 22:00 | Catch NFOs / scheme changes before NAV pull |
| 3 | NAV Data | Daily | 23:00 | After AMFI NAVAll publish (~22:30) |
| 4 | Holdings / Portfolio | Monthly | 12th of month 21:00 | AMCs disclose within 10 days of month-end |
| 5 | Asset Allocation | Monthly | 12th of month 22:00 | Derived after holdings |
| 6 | Sector Allocation | Monthly | 12th of month 22:00 | Derived after holdings |
| 7 | Returns | Daily | 23:30 | Recompute trailing returns after NAV |
| 8 | Risk Metrics | Weekly | Sat 08:00 | Rolling 1Y/3Y windows; weekly is sufficient |
| 9 | AUM / Fund Size | Monthly | 8th of month 10:00 | AMFI monthly AUM disclosure |
| 10 | Fund Manager | Monthly + Event-driven | 1st of month 09:30 | Re-pull on manager-change filings |
| 11 | Expense & Load | Monthly | 5th of month 10:00 | TER disclosed monthly |
| 12 | Dividend / IDCW History | Event-driven | record-day 22:00 | On IDCW declaration |
| 13 | Portfolio Analytics | Monthly | 13th of month 09:00 | After holdings; overlap recompute |
| 14 | Debt Analytics | Monthly | 13th of month 09:00 | YTM/duration from holdings + factsheet |
| 15 | Scheme Categorisation | Monthly | 1st of month 09:00 | Stable; refresh with scheme master |
| 16 | Ratings & Rankings | Monthly | 5th of month 11:00 | CRISIL/VR refresh monthly/quarterly |
| 17 | NFO | Daily | 20:30 | Active only during open NFOs |
| 18 | Transactions / Plans | Quarterly | quarter-start 09:00 | SID-driven, infrequent |
| 19 | Taxation | Annual + Event-driven | post-Budget | On Finance Act changes |

---

# CROSS-DOMAIN / REFERENCE

| Module | Frequency | Recommended update time (IST) |
|--------|-----------|-------------------------------|
| R1 Identifier Crosswalk | Daily | 20:15 (after Company Master) |
| R2 Sector Master | Monthly | 1st 08:00 |
| R3 Trading Calendar | Annual + Event-driven | Dec 15 (next-year list) |
| R4 FX Rates | Daily | 18:00 (RBI reference) |
| R5 Benchmark Index Master | Quarterly | quarter-start |
| R6 Macro Indicators | Per-release (Monthly/Quarterly) | on official release |
| R7 RTA Master | Annual | Jan 01 |
| R8 Rating Agency Master | Annual | Jan 01 |
| R9 Ingestion Manifest | Real-time | every pipeline run |
| R10 Data Quality | Per-run | after each gold build |

---

## Daily schedule digest (typical trading day, IST)

```
08:45  F&O ban list, surveillance pre-open
09:15  Intraday tick/bar capture starts
15:30  Intraday capture ends
17:30  FII/DII provisional
18:00  Surveillance (ASM/GSM), FX (RBI)
18:30  Price EOD, Index, Derivatives EOD, Market stats
19:00  Corporate actions, Bulk/Block deals
19:30  Adjusted prices, Insider trading
19:45  Valuation, Technical indicators
20:00  Company master, Short selling, SHP (on quarter days)
20:15  Identifier crosswalk
21:00  Financial results (on result days), FII/DII final
22:00  Scheme master, Ratios (on result days)
23:00  MF NAV
23:30  MF returns
```

Weekly/monthly/quarterly jobs are slotted on weekends/month-starts to avoid
contending with the daily window.
