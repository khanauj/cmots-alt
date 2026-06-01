# Phase 5 — Database Design

Parent/child tables, primary keys, foreign keys, and the full relationship
hierarchy derived from the [data tree](phase1-data-tree.md). The design extends
the **existing** schema (`src/cmots_alt/storage/migrations/001_init.sql`):
`company`, `identifier_crosswalk`, `co_code_sequence`, `ingest_manifest`.

Conventions:
- **`company.co_code`** is the universal equity foreign key (CMOTS-style surrogate).
- **`mf_scheme.scheme_code`** (AMFI code) is the universal MF foreign key.
- All time-series child tables carry the parent key + a date/period column in their PK.
- Storage today is **SQLite** (gold also materialised as Parquet for the API layer).
  The same DDL ports to Postgres for scale-out.

---

## 1. Top-level relationship hierarchy

```
                         ┌─────────────────────┐
                         │  sector_master (R2) │
                         └──────────┬──────────┘
                                    │ 1
                                    │
                                    ▼ N
┌──────────────────────────────────────────────────────────────────┐
│                          company  (PARENT)                         │
│  PK isin · UNIQUE co_code · FK sector_code → sector_master         │
└───┬───────────────┬───────────────┬───────────────┬───────────────┘
    │1              │1              │1              │1
    ▼N             ▼N              ▼N              ▼N
identifier_     price_eod       corporate_      shareholding
crosswalk(R1)      │             actions             │
                   ▼N                                 ▼N
            technical_                          shareholding_
            indicators                          detail / holders
                   
company 1──N financials  1──N financial_line_item
company 1──N ratios       company 1──N valuation
company 1──N announcements company 1──N events
company 1──N insider_trades company 1──N bulk_block_deals
company 1──N credit_ratings company 1──N analyst_estimates
company 1──N board_member  company 1──N index_constituent ──N index_master
company N──N peer_group (self-join via peer_link)


                         ┌─────────────────────┐
                         │      amc_master      │
                         └──────────┬───────────┘
                                    │1
                                    ▼N
┌──────────────────────────────────────────────────────────────────┐
│                       mf_scheme  (PARENT)                          │
│  PK scheme_code · FK amc_code → amc_master · FK manager_id         │
└───┬───────────────┬───────────────┬───────────────┬───────────────┘
    │1              │1              │1              │1
    ▼N             ▼N              ▼N              ▼N
 mf_nav        mf_holding      mf_returns      mf_risk_metrics
                   │
                   │ FK co_code → company   (MF holding ↔ equity bridge)
                   ▼
                company

mf_scheme 1──N mf_asset_allocation   mf_scheme 1──N mf_sector_allocation
mf_scheme 1──N mf_aum                mf_scheme 1──N mf_expense
mf_scheme 1──N mf_idcw               mf_scheme N──1 fund_manager
mf_scheme 1──N mf_debt_analytics     mf_scheme 1──N mf_rating
```

---

## 2. Cross-domain / reference (parents-of-parents)

```sql
-- R2 sector_master (already partially present; expanded)
CREATE TABLE sector_master (
    sector_code        INTEGER PRIMARY KEY,
    sector_name        TEXT NOT NULL,
    macro_sector       TEXT,
    industry           TEXT,
    basic_industry     TEXT,
    parent_sector_code INTEGER REFERENCES sector_master(sector_code),
    source             TEXT,
    confidence_score   REAL
);

-- R1 identifier_crosswalk (EXISTING)
-- PK (isin, id_type, id_value); FK isin → company.isin

-- R3 trading_calendar
CREATE TABLE trading_calendar (
    calendar_date TEXT NOT NULL,
    exchange      TEXT NOT NULL,
    segment       TEXT NOT NULL,
    is_trading    INTEGER NOT NULL,
    holiday_name  TEXT,
    PRIMARY KEY (calendar_date, exchange, segment)
);

-- R5 index_master
CREATE TABLE index_master (
    index_code TEXT PRIMARY KEY,
    index_name TEXT NOT NULL,
    index_type TEXT,          -- broad / sector / thematic
    provider   TEXT,
    base_date  TEXT,
    base_value REAL
);

-- R8 rating_agency_master
CREATE TABLE rating_agency_master (
    agency_code TEXT PRIMARY KEY,
    agency_name TEXT NOT NULL,
    sebi_reg_no TEXT
);

-- R9 ingest_manifest (EXISTING) — lineage for every bronze write
-- R10 data_quality (EXISTING report output)
```

---

## 3. Equity — parent & child tables

```sql
-- PARENT: company (EXISTING; columns extended in Phase 2)
-- PK isin · UNIQUE co_code · UNIQUE nse_symbol · UNIQUE bse_code
-- FK sector_code → sector_master(sector_code)

-- CHILD: capital_structure  (1:N over time / events)
CREATE TABLE capital_structure (
    co_code             INTEGER NOT NULL REFERENCES company(co_code),
    as_of_date          TEXT NOT NULL,
    authorised_capital  REAL, issued_capital REAL, paid_up_capital REAL,
    shares_outstanding  INTEGER, free_float_shares INTEGER, free_float_factor REAL,
    PRIMARY KEY (co_code, as_of_date)
);

-- CHILD: price_eod  (one row per co_code × exchange × date)
CREATE TABLE price_eod (
    co_code     INTEGER NOT NULL REFERENCES company(co_code),
    trade_date  TEXT NOT NULL,
    exchange    TEXT NOT NULL,           -- NSE / BSE
    series      TEXT,
    open REAL, high REAL, low REAL, close REAL, prev_close REAL,
    last_price REAL, vwap REAL,
    total_volume INTEGER, total_turnover REAL, no_of_trades INTEGER,
    deliverable_qty INTEGER, deliverable_percent REAL,
    week52_high REAL, week52_low REAL,
    upper_circuit REAL, lower_circuit REAL,
    PRIMARY KEY (co_code, trade_date, exchange)
);
CREATE INDEX ix_price_eod_date ON price_eod(trade_date);

-- CHILD: price_adjusted  (derived from price_eod + corporate_actions)
CREATE TABLE price_adjusted (
    co_code INTEGER NOT NULL REFERENCES company(co_code),
    trade_date TEXT NOT NULL,
    close_raw REAL, close_split_adj REAL, close_total_return REAL,
    adjustment_factor REAL, adjustment_reason TEXT,
    PRIMARY KEY (co_code, trade_date)
);

-- CHILD: corporate_actions
CREATE TABLE corporate_actions (
    action_id   TEXT PRIMARY KEY,        -- hash(co_code|type|ex_date)
    co_code     INTEGER NOT NULL REFERENCES company(co_code),
    action_type TEXT NOT NULL, action_subtype TEXT,
    announcement_date TEXT, ex_date TEXT, record_date TEXT,
    book_closure_start TEXT, book_closure_end TEXT, effective_date TEXT,
    dividend_per_share REAL, dividend_percent REAL,
    ratio_numerator REAL, ratio_denominator REAL,
    old_face_value REAL, new_face_value REAL,
    rights_price REAL, buyback_price REAL,
    purpose TEXT, source TEXT
);
CREATE INDEX ix_ca_co_ex ON corporate_actions(co_code, ex_date);

-- CHILD: financials  (statement header) → financial_line_item (grandchild)
CREATE TABLE financials (
    statement_id TEXT PRIMARY KEY,       -- hash(co_code|type|basis|period_end)
    co_code      INTEGER NOT NULL REFERENCES company(co_code),
    statement_type TEXT NOT NULL,        -- PL / BS / CF
    basis        TEXT NOT NULL,          -- Standalone / Consolidated
    period_type  TEXT NOT NULL,          -- Q / H / Annual
    period_end   TEXT NOT NULL,
    fiscal_year  TEXT, currency TEXT, unit_multiplier INTEGER,
    audit_status TEXT, filing_date TEXT,
    UNIQUE (co_code, statement_type, basis, period_end)
);
CREATE TABLE financial_line_item (
    statement_id TEXT NOT NULL REFERENCES financials(statement_id),
    line_code    TEXT NOT NULL,          -- canonical taxonomy code (e.g. REVENUE)
    line_label   TEXT, value REAL,
    PRIMARY KEY (statement_id, line_code)
);

-- CHILD: ratios  (1 row per co_code × period × basis)
CREATE TABLE ratios (
    co_code INTEGER NOT NULL REFERENCES company(co_code),
    period_end TEXT NOT NULL, basis TEXT NOT NULL,
    -- profitability / liquidity / leverage / efficiency / per-share / growth ...
    gross_margin REAL, operating_margin REAL, ebitda_margin REAL, net_margin REAL,
    roe REAL, roce REAL, roa REAL,
    current_ratio REAL, quick_ratio REAL, debt_to_equity REAL, interest_coverage REAL,
    asset_turnover REAL, inventory_turnover REAL, receivable_days REAL, payable_days REAL,
    eps REAL, book_value_per_share REAL, dividend_per_share REAL, dividend_payout REAL,
    sales_growth_yoy REAL, profit_growth_yoy REAL, eps_growth_yoy REAL,
    sales_cagr_3y REAL, profit_cagr_3y REAL,
    altman_z REAL, piotroski_f INTEGER,
    PRIMARY KEY (co_code, period_end, basis)
);

-- CHILD: valuation  (daily)
CREATE TABLE valuation (
    co_code INTEGER NOT NULL REFERENCES company(co_code),
    as_of_date TEXT NOT NULL,
    market_cap REAL, free_float_market_cap REAL, enterprise_value REAL,
    pe_ttm REAL, pe_forward REAL, pb REAL, ps REAL, pcf REAL,
    ev_ebitda REAL, ev_sales REAL, dividend_yield REAL, earnings_yield REAL, peg REAL,
    PRIMARY KEY (co_code, as_of_date)
);

-- CHILD: shareholding  (quarterly summary)
CREATE TABLE shareholding (
    co_code INTEGER NOT NULL REFERENCES company(co_code),
    quarter_end TEXT NOT NULL,
    promoter_pct REAL, promoter_group_pct REAL, promoter_pledge_pct REAL,
    fii_pct REAL, dii_pct REAL, mutual_fund_pct REAL, insurance_pct REAL,
    govt_pct REAL, institution_pct REAL, non_institution_pct REAL,
    public_pct REAL, retail_pct REAL, hni_pct REAL, pledged_pct REAL,
    number_of_shareholders INTEGER,
    PRIMARY KEY (co_code, quarter_end)
);
-- GRANDCHILD: shareholding_holder (holders > 1% / institutional detail)
CREATE TABLE shareholding_holder (
    co_code INTEGER NOT NULL REFERENCES company(co_code),
    quarter_end TEXT NOT NULL,
    holder_type TEXT NOT NULL, holder_name TEXT NOT NULL,
    holder_scheme_code INTEGER REFERENCES mf_scheme(scheme_code),
    shares_held INTEGER, holding_pct REAL, holding_value REAL, change_qoq_shares INTEGER,
    PRIMARY KEY (co_code, quarter_end, holder_type, holder_name)
);

-- CHILD: technical_indicators (daily, derived from price_eod)
CREATE TABLE technical_indicators (
    co_code INTEGER NOT NULL REFERENCES company(co_code),
    trade_date TEXT NOT NULL,
    sma_50 REAL, sma_200 REAL, ema_20 REAL, rsi_14 REAL,
    macd REAL, macd_signal REAL, atr_14 REAL,
    bollinger_upper REAL, bollinger_lower REAL, adx REAL,
    beta_1y REAL, volatility_30d REAL,
    PRIMARY KEY (co_code, trade_date)
);

-- CHILD tables (abbreviated DDL — same pattern: co_code FK + date in PK):
--   announcements(announcement_id PK, co_code FK, ...)
--   events(co_code, event_type, event_date PK-part, ...)
--   insider_trades(trade_id PK, co_code FK, ...)
--   bulk_block_deals(deal_id PK, co_code FK, deal_type, ...)
--   credit_ratings(co_code, agency_code FK, instrument_type, rating_date PK-part, ...)
--   analyst_estimates(co_code, fiscal_year, metric_type PK, ...)
--   board_member(co_code, din PK-part, ...)
--   derivatives_eod(symbol, expiry, strike, option_type, trade_date PK, co_code FK)
--   index_value(index_code FK, trade_date PK)
--   index_constituent(index_code FK, co_code FK, as_of_date PK)
--   peer_link(co_code, peer_co_code, peer_group_id PK)   -- self-referential N:N
--   surveillance_flags(co_code, as_of_date PK, asm_stage, gsm_stage, fno_ban)
--   ipo_issue(issue_id PK, co_code FK)
--   esg_score(co_code, as_of_date PK)
--   news(news_id PK, co_code FK)
```

---

## 4. Mutual Funds — parent & child tables

```sql
-- PARENT: amc_master
CREATE TABLE amc_master (
    amc_code INTEGER PRIMARY KEY,
    amc_name TEXT NOT NULL, sponsor_name TEXT, trustee_name TEXT,
    sebi_reg_no TEXT, incorporation_date TEXT,
    rta_name TEXT, custodian_name TEXT, website TEXT,
    total_aum REAL, aum_rank INTEGER
);

-- PARENT: fund_manager
CREATE TABLE fund_manager (
    manager_id INTEGER PRIMARY KEY,
    manager_name TEXT NOT NULL, qualification TEXT, experience_years INTEGER
);

-- PARENT: mf_scheme (EXISTING; extended)
CREATE TABLE mf_scheme (
    scheme_code INTEGER PRIMARY KEY,         -- AMFI code
    isin_growth TEXT, isin_idcw TEXT,
    scheme_name TEXT NOT NULL,
    amc_code INTEGER REFERENCES amc_master(amc_code),
    category TEXT, sub_category TEXT,
    plan TEXT, option TEXT,
    launch_date TEXT, closure_date TEXT, reopen_date TEXT,
    benchmark TEXT, riskometer_level TEXT,
    min_investment REAL, min_sip REAL,
    expense_ratio REAL, exit_load TEXT, lock_in_period INTEGER,
    manager_id INTEGER REFERENCES fund_manager(manager_id),
    aum REAL, is_active INTEGER
);

-- CHILD: mf_nav (daily)
CREATE TABLE mf_nav (
    scheme_code INTEGER NOT NULL REFERENCES mf_scheme(scheme_code),
    nav_date TEXT NOT NULL,
    nav REAL NOT NULL, repurchase_price REAL, sale_price REAL,
    nav_adjusted REAL, day_change REAL, day_change_pct REAL,
    PRIMARY KEY (scheme_code, nav_date)
);
CREATE INDEX ix_mf_nav_date ON mf_nav(nav_date);

-- CHILD: mf_holding  (BRIDGE to equity via co_code)
CREATE TABLE mf_holding (
    scheme_code INTEGER NOT NULL REFERENCES mf_scheme(scheme_code),
    quarter_end TEXT NOT NULL,
    instrument_name TEXT NOT NULL, isin TEXT,
    co_code INTEGER REFERENCES company(co_code),    -- nullable: equity bridge
    instrument_type TEXT, sector TEXT,
    quantity REAL, market_value REAL, weight_pct REAL,
    rating TEXT, ytm REAL, coupon REAL, maturity_date TEXT,
    PRIMARY KEY (scheme_code, quarter_end, instrument_name)
);
CREATE INDEX ix_mf_holding_cocode ON mf_holding(co_code);

-- CHILD: mf_returns (daily snapshot of trailing returns)
CREATE TABLE mf_returns (
    scheme_code INTEGER NOT NULL REFERENCES mf_scheme(scheme_code),
    as_of_date TEXT NOT NULL,
    ret_1d REAL, ret_1m REAL, ret_3m REAL, ret_6m REAL,
    ret_1y REAL, ret_3y REAL, ret_5y REAL, ret_si REAL,
    sip_xirr_1y REAL, sip_xirr_3y REAL, sip_xirr_5y REAL,
    PRIMARY KEY (scheme_code, as_of_date)
);

-- CHILD: mf_risk_metrics (weekly)
CREATE TABLE mf_risk_metrics (
    scheme_code INTEGER NOT NULL REFERENCES mf_scheme(scheme_code),
    as_of_date TEXT NOT NULL, period TEXT NOT NULL,   -- e.g. 3Y
    std_dev REAL, sharpe REAL, sortino REAL, beta REAL, alpha REAL,
    r_squared REAL, treynor REAL, information_ratio REAL, max_drawdown REAL,
    PRIMARY KEY (scheme_code, as_of_date, period)
);

-- CHILD tables (abbreviated — scheme_code FK + date in PK):
--   mf_asset_allocation(scheme_code, as_of_date PK, equity_pct, debt_pct, cash_pct, ...)
--   mf_sector_allocation(scheme_code, as_of_date, sector_name PK, weight_pct)
--   mf_aum(scheme_code, month_end PK, aum, aaum, folio_count)
--   mf_expense(scheme_code, as_of_date PK, ter_regular, ter_direct, exit_load_slab)
--   mf_idcw(scheme_code, record_date PK, idcw_per_unit, frequency)
--   mf_debt_analytics(scheme_code, as_of_date PK, avg_maturity, mod_duration, ytm, ...)
--   mf_rating(scheme_code, as_of_date, provider PK, rating_value, quartile_rank)
--   mf_categorisation(scheme_code PK, sebi_category, sebi_sub_category, riskometer)
```

---

## 5. Key relationship summary

| Parent | Child | Relationship | FK |
|--------|-------|--------------|-----|
| sector_master | company | 1:N | company.sector_code |
| company | price_eod / corporate_actions / financials / ratios / valuation / shareholding / technical_indicators / … | 1:N | child.co_code |
| company | identifier_crosswalk | 1:N | crosswalk.isin |
| financials | financial_line_item | 1:N | line_item.statement_id |
| company | peer_link | N:N (self) | peer_link.(co_code, peer_co_code) |
| index_master | index_constituent | 1:N | constituent.index_code |
| company | index_constituent | 1:N | constituent.co_code |
| amc_master | mf_scheme | 1:N | mf_scheme.amc_code |
| fund_manager | mf_scheme | 1:N | mf_scheme.manager_id |
| mf_scheme | mf_nav / mf_holding / mf_returns / mf_risk_metrics / … | 1:N | child.scheme_code |
| **mf_holding** | **company** | **N:1 (BRIDGE)** | **mf_holding.co_code** |
| mf_scheme | shareholding_holder | 1:N | holder.holder_scheme_code |

The **mf_holding ↔ company bridge** is the spine of the platform: it lets a query
walk "which mutual funds hold stock X" (shareholding side) and "what does fund Y
own" (portfolio side) over the same `co_code` keyspace — the core CMOTS join.

---

## 6. Migration plan (additive, ordered)

```
001_init.sql                 (EXISTING) company, identifier_crosswalk, ingest_manifest
002_sector_confidence.sql    (EXISTING) sector confidence columns
003_price_corp_share.sql     price_eod, corporate_actions, shareholding (+holder)
004_financials_ratios.sql    financials, financial_line_item, ratios, valuation
005_mf_core.sql              amc_master, fund_manager, mf_scheme, mf_nav, mf_holding
006_mf_analytics.sql         mf_returns, mf_risk_metrics, allocation, aum, expense
007_market_microstructure.sql technicals, derivatives, bulk_block, insider, surveillance
008_reference.sql            trading_calendar, index_master/value/constituent, ratings
```

Each migration is additive and idempotent (`CREATE TABLE IF NOT EXISTS`), matching
the existing migration style.
