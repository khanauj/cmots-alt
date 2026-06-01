# Phase 1 — Master Data Tree

The complete hierarchy of all data available in a CMOTS-style system, organised
into two Level-1 domains (**Equity**, **Mutual Funds**) plus shared
**Cross-Domain / Reference** data that both depend on.

Status tags: **[LIVE]** built today · **[NEXT]** next to build · **[ROADMAP]** catalogued.

---

## LEVEL 1 — Domains

```
Indian Market Data Platform
├── EQUITY
├── MUTUAL FUNDS
└── CROSS-DOMAIN / REFERENCE  (shared masters used by both)
```

---

## EQUITY (Level 2 modules → Level 3 sub-modules)

```
EQUITY
│
├── 1. Company / Security Master                                   [LIVE]
│   ├── 1.1 Identity (legal name, short name, ISIN)
│   ├── 1.2 Identifier crosswalk (ISIN ↔ NSE ↔ BSE ↔ co_code ↔ CIN)
│   ├── 1.3 Listing status & exchange membership
│   ├── 1.4 Classification (sector / industry / macro / mcap class)
│   ├── 1.5 Constitution (face value, group, ISIN type, instrument type)
│   ├── 1.6 Registered office / contact / website
│   ├── 1.7 Registrar & Transfer Agent (RTA)
│   └── 1.8 Auditor / company secretary
│
├── 2. Listing & Capital Structure                                 [NEXT]
│   ├── 2.1 Listing dates (NSE, BSE, IPO date)
│   ├── 2.2 Authorised / issued / paid-up capital
│   ├── 2.3 Shares outstanding (total, free-float)
│   ├── 2.4 Free-float factor
│   ├── 2.5 Capital history (allotments, FPOs, QIPs)
│   └── 2.6 Delisting / suspension history
│
├── 3. Price Data — End of Day (EOD)                               [LIVE]
│   ├── 3.1 OHLC + last/prev-close
│   ├── 3.2 Volume / turnover / trades
│   ├── 3.3 Delivery quantity & delivery %
│   ├── 3.4 VWAP
│   ├── 3.5 52-week high / low
│   ├── 3.6 Price band / circuit limits
│   └── 3.7 Per-exchange split (NSE / BSE) + consolidated
│
├── 4. Price Data — Intraday / Real-time                           [ROADMAP]
│   ├── 4.1 Tick / LTP feed
│   ├── 4.2 1-min / 5-min / 15-min / 60-min OHLC bars
│   ├── 4.3 Best bid/ask, market depth (5/20 level)
│   ├── 4.4 Open interest snapshots
│   └── 4.5 Pre-open session prices
│
├── 5. Adjusted Price History                                      [NEXT]
│   ├── 5.1 Split/bonus-adjusted close
│   ├── 5.2 Dividend-adjusted (total-return) close
│   └── 5.3 Adjustment factor series
│
├── 6. Corporate Actions                                           [LIVE]
│   ├── 6.1 Dividends (interim / final / special)
│   ├── 6.2 Bonus issues
│   ├── 6.3 Stock splits / sub-division
│   ├── 6.4 Rights issues
│   ├── 6.5 Buybacks
│   ├── 6.6 Face value changes / consolidation
│   ├── 6.7 Mergers / demergers / amalgamation / scheme of arrangement
│   ├── 6.8 Name / symbol change
│   ├── 6.9 Delisting / relisting
│   └── 6.10 Spin-offs / capital reduction
│
├── 7. Financial Statements                                        [NEXT]
│   ├── 7.1 Profit & Loss (standalone + consolidated)
│   ├── 7.2 Balance Sheet (standalone + consolidated)
│   ├── 7.3 Cash Flow (standalone + consolidated)
│   ├── 7.4 Quarterly results
│   ├── 7.5 Half-yearly / annual results
│   ├── 7.6 Segment reporting
│   ├── 7.7 Notes / accounting policies / contingent liabilities
│   └── 7.8 Banking/NBFC/Insurance-specific schedules
│
├── 8. Ratios & Derived Fundamentals                               [NEXT]
│   ├── 8.1 Profitability (margins, ROE, ROCE, ROA)
│   ├── 8.2 Liquidity (current, quick)
│   ├── 8.3 Leverage / solvency (D/E, interest coverage)
│   ├── 8.4 Efficiency / turnover (asset, inventory, receivable)
│   ├── 8.5 Per-share (EPS, BVPS, CFPS, DPS)
│   ├── 8.6 Growth (YoY / QoQ / CAGR for sales, profit, EPS)
│   ├── 8.7 DuPont decomposition
│   └── 8.8 Coverage & quality (Altman Z, Piotroski F, accruals)
│
├── 9. Valuation Metrics                                           [NEXT]
│   ├── 9.1 Market cap (full + free-float)
│   ├── 9.2 Enterprise value
│   ├── 9.3 P/E (TTM, forward), P/B, P/S, P/CF
│   ├── 9.4 EV/EBITDA, EV/Sales, EV/EBIT
│   ├── 9.5 Dividend yield, earnings yield
│   ├── 9.6 PEG ratio
│   └── 9.7 Historical valuation bands (median / percentile)
│
├── 10. Shareholding Pattern                                       [LIVE]
│   ├── 10.1 Promoter & promoter group %
│   ├── 10.2 FII / FPI %
│   ├── 10.3 DII %
│   ├── 10.4 Mutual fund holding %
│   ├── 10.5 Public / retail / HNI %
│   ├── 10.6 Government holding %
│   ├── 10.7 Pledge / encumbrance %
│   ├── 10.8 Number of shareholders
│   └── 10.9 Category-wise detail (XBRL)
│
├── 11. Institutional & Major Holders                              [ROADMAP]
│   ├── 11.1 Top mutual funds holding the stock
│   ├── 11.2 Top FIIs / FPIs holding
│   ├── 11.3 Insurance / pension holders
│   ├── 11.4 Holders > 1% (SHP detail)
│   └── 11.5 Holding change QoQ
│
├── 12. Board, Management & Governance                             [ROADMAP]
│   ├── 12.1 Board of directors (name, DIN, designation, tenure)
│   ├── 12.2 Key managerial personnel (KMP)
│   ├── 12.3 Committees (audit, NRC, CSR)
│   ├── 12.4 Remuneration
│   ├── 12.5 Auditor & auditor changes
│   └── 12.6 Related-party transactions
│
├── 13. Announcements & Corporate Filings                          [ROADMAP]
│   ├── 13.1 Exchange announcements (NSE/BSE)
│   ├── 13.2 Board meeting outcomes
│   ├── 13.3 Investor presentations / press releases
│   ├── 13.4 Regulation 30 disclosures
│   └── 13.5 Annual reports / XBRL filings
│
├── 14. Events & Calendar                                          [ROADMAP]
│   ├── 14.1 Board meetings
│   ├── 14.2 AGM / EGM
│   ├── 14.3 Results calendar
│   ├── 14.4 Ex-dates / record dates / book closure
│   └── 14.5 Conference calls / analyst meets
│
├── 15. Insider Trading (SEBI PIT)                                 [ROADMAP]
│   ├── 15.1 Promoter/insider acquisitions & disposals
│   ├── 15.2 Pledge creation / release by insiders
│   └── 15.3 SAST (substantial acquisition) disclosures
│
├── 16. Bulk Deals                                                 [ROADMAP]
├── 17. Block Deals                                                [ROADMAP]
├── 18. Short Selling / Securities Lending & Borrowing             [ROADMAP]
│
├── 19. Surveillance & Risk Flags                                  [ROADMAP]
│   ├── 19.1 ASM (Additional Surveillance Measure) long/short term
│   ├── 19.2 GSM (Graded Surveillance Measure)
│   ├── 19.3 Ban period (F&O)
│   ├── 19.4 Circuit / price-band stage
│   └── 19.5 Insolvency / suspension flags
│
├── 20. Credit Ratings                                             [ROADMAP]
│   ├── 20.1 Long-term / short-term issuer ratings
│   ├── 20.2 Instrument ratings
│   ├── 20.3 Rating action history (upgrade/downgrade/watch)
│   └── 20.4 Rating agency & rationale
│
├── 21. Technical Indicators                                       [ROADMAP]
│   ├── 21.1 Moving averages (SMA/EMA 5/10/20/50/100/200)
│   ├── 21.2 Momentum (RSI, MACD, stochastic, CCI, Williams %R)
│   ├── 21.3 Volatility (ATR, Bollinger Bands, std dev)
│   ├── 21.4 Volume (OBV, VWAP, A/D, MFI)
│   ├── 21.5 Trend (ADX, DMI, SAR, Supertrend)
│   ├── 21.6 Pivots (classic / Fibonacci / Camarilla)
│   └── 21.7 Beta / volatility / correlation
│
├── 22. Derivatives (F&O)                                          [ROADMAP]
│   ├── 22.1 Futures (price, OI, basis) — index & stock
│   ├── 22.2 Options chain (strike, CE/PE, IV, greeks, OI)
│   ├── 22.3 Open interest & OI change / PCR
│   ├── 22.4 Rollover & cost of carry
│   ├── 22.5 FII/DII derivative statistics
│   └── 22.6 Lot size / expiry / contract master
│
├── 23. Index Data                                                 [ROADMAP]
│   ├── 23.1 Index master (NIFTY 50, SENSEX, sectoral, thematic)
│   ├── 23.2 Index values (OHLC, EOD)
│   ├── 23.3 Constituents & weights
│   ├── 23.4 Index P/E, P/B, dividend yield
│   └── 23.5 Index rebalancing / inclusions-exclusions
│
├── 24. Sector / Industry Classification                          [LIVE]
│   ├── 24.1 Macro-economic sector
│   ├── 24.2 Sector
│   ├── 24.3 Industry
│   ├── 24.4 Basic industry (NSE 4-level taxonomy)
│   └── 24.5 BSE / custom sector map
│
├── 25. Peer Comparison                                           [ROADMAP]
│   ├── 25.1 Peer set definition
│   ├── 25.2 Side-by-side valuation
│   ├── 25.3 Side-by-side fundamentals & growth
│   └── 25.4 Relative ranking / percentile
│
├── 26. Analyst Estimates & Consensus                             [ROADMAP]
│   ├── 26.1 Consensus EPS / revenue / EBITDA (FY1, FY2)
│   ├── 26.2 Target price & recommendation (buy/hold/sell)
│   ├── 26.3 Number of analysts & revisions
│   └── 26.4 Surprise (actual vs estimate)
│
├── 27. News & Research                                           [ROADMAP]
│   ├── 27.1 News articles (tagged to co_code)
│   ├── 27.2 Broker research reports
│   └── 27.3 Sentiment scores
│
├── 28. Primary Market / IPO                                      [ROADMAP]
│   ├── 28.1 IPO/FPO calendar & details (price band, lot, dates)
│   ├── 28.2 Subscription (QIB/NII/Retail) & GMP
│   ├── 28.3 Listing-day performance
│   └── 28.4 SME IPOs / rights / OFS
│
├── 29. ESG & Sustainability                                      [ROADMAP]
│   ├── 29.1 ESG score (E / S / G pillars)
│   ├── 29.2 BRSR disclosures
│   └── 29.3 Controversies / carbon metrics
│
└── 30. Market Statistics (market-wide)                           [ROADMAP]
    ├── 30.1 Advances / declines
    ├── 30.2 52-wk high/low counts
    ├── 30.3 FII/DII cash-market flows
    ├── 30.4 Most active / top gainers-losers
    └── 30.5 Market breadth / turnover
```

---

## MUTUAL FUNDS (Level 2 modules → Level 3 sub-modules)

```
MUTUAL FUNDS
│
├── 1. AMC Master                                                  [NEXT]
│   ├── 1.1 AMC identity (name, code, sponsor, trustee)
│   ├── 1.2 Registration (SEBI reg no., incorporation)
│   ├── 1.3 Contact / RTA / custodian
│   └── 1.4 Total AUM & rank
│
├── 2. Scheme Master                                               [LIVE]
│   ├── 2.1 Scheme identity (AMFI code, ISIN-Growth, ISIN-IDCW, name)
│   ├── 2.2 AMC linkage
│   ├── 2.3 SEBI category & sub-category
│   ├── 2.4 Plan (Regular/Direct) & option (Growth/IDCW)
│   ├── 2.5 Launch / closure / reopening dates
│   ├── 2.6 Benchmark
│   ├── 2.7 Minimum investment / SIP details
│   ├── 2.8 Expense ratio (TER)
│   ├── 2.9 Exit load structure
│   └── 2.10 Fund manager linkage
│
├── 3. NAV Data                                                    [LIVE]
│   ├── 3.1 Daily NAV (per scheme/plan/option)
│   ├── 3.2 NAV history
│   ├── 3.3 Repurchase / sale price
│   └── 3.4 Adjusted (IDCW-reinvested) NAV
│
├── 4. Holdings / Portfolio                                        [LIVE]
│   ├── 4.1 Instrument-level holdings (name, ISIN, qty, value, weight)
│   ├── 4.2 Instrument type (equity/debt/cash/derivative/REIT)
│   ├── 4.3 Mapping to equity co_code
│   ├── 4.4 Rating (for debt holdings)
│   └── 4.5 Month-end vs quarter-end disclosure
│
├── 5. Asset Allocation                                            [NEXT]
│   ├── 5.1 Equity / debt / cash / others %
│   ├── 5.2 Large/mid/small-cap split
│   ├── 5.3 Derivative exposure
│   └── 5.4 Allocation history
│
├── 6. Sector Allocation                                           [NEXT]
│   ├── 6.1 Sector-wise weight
│   ├── 6.2 Top sectors
│   └── 6.3 Sector over/underweight vs benchmark
│
├── 7. Returns                                                     [NEXT]
│   ├── 7.1 Point-to-point (1D/1W/1M/3M/6M/1Y/3Y/5Y/10Y/SI)
│   ├── 7.2 Trailing returns (annualised > 1Y)
│   ├── 7.3 Calendar-year returns
│   ├── 7.4 Rolling returns
│   ├── 7.5 SIP returns / XIRR
│   └── 7.6 Benchmark & category returns (for comparison)
│
├── 8. Risk Metrics                                                [NEXT]
│   ├── 8.1 Standard deviation
│   ├── 8.2 Sharpe ratio
│   ├── 8.3 Sortino ratio
│   ├── 8.4 Beta
│   ├── 8.5 Alpha (Jensen's)
│   ├── 8.6 R-squared
│   ├── 8.7 Treynor ratio
│   ├── 8.8 Information ratio
│   ├── 8.9 Max drawdown
│   └── 8.10 Capture ratios (up/down)
│
├── 9. AUM / Fund Size                                             [NEXT]
│   ├── 9.1 Scheme AUM (month-end)
│   ├── 9.2 AUM history
│   ├── 9.3 AAUM (average)
│   └── 9.4 Folio count
│
├── 10. Fund Manager                                               [NEXT]
│   ├── 10.1 Manager profile (name, qualification, experience)
│   ├── 10.2 Schemes managed
│   ├── 10.3 Tenure on scheme
│   └── 10.4 Manager performance track record
│
├── 11. Expense & Load                                             [NEXT]
│   ├── 11.1 TER (regular / direct)
│   ├── 11.2 TER history
│   ├── 11.3 Exit load slabs
│   └── 11.4 Entry load (legacy / nil)
│
├── 12. Dividend / IDCW History                                    [ROADMAP]
│   ├── 12.1 IDCW declared (per unit, record date)
│   ├── 12.2 IDCW frequency
│   └── 12.3 Cumulative payouts
│
├── 13. Portfolio Analytics                                        [ROADMAP]
│   ├── 13.1 Portfolio turnover ratio
│   ├── 13.2 Number of holdings / concentration (top 10)
│   ├── 13.3 Holdings overlap (scheme vs scheme)
│   └── 13.4 Active share vs benchmark
│
├── 14. Debt-Specific Analytics                                    [ROADMAP]
│   ├── 14.1 Average maturity
│   ├── 14.2 Modified duration / Macaulay duration
│   ├── 14.3 Yield to maturity (YTM)
│   ├── 14.4 Credit-quality breakdown (AAA/AA/...)
│   └── 14.5 Instrument-type breakdown (G-Sec/Corp/CP/CD/TREPS)
│
├── 15. Scheme Categorisation (SEBI)                               [NEXT]
│   ├── 15.1 Category (Equity/Debt/Hybrid/Solution/Other)
│   ├── 15.2 Sub-category (Large Cap, Liquid, Aggressive Hybrid, ...)
│   └── 15.3 Riskometer level
│
├── 16. Ratings & Rankings                                         [ROADMAP]
│   ├── 16.1 CRISIL rank
│   ├── 16.2 Value Research stars
│   ├── 16.3 Morningstar rating
│   └── 16.4 Quartile ranking (within category)
│
├── 17. NFO (New Fund Offers)                                      [ROADMAP]
│   ├── 17.1 NFO open/close dates
│   ├── 17.2 NFO price & details
│   └── 17.3 NFO collection
│
├── 18. Transactions / Plans                                       [ROADMAP]
│   ├── 18.1 SIP / STP / SWP availability & limits
│   ├── 18.2 Minimum amounts
│   └── 18.3 Lock-in (ELSS / close-ended)
│
└── 19. Taxation                                                   [ROADMAP]
    ├── 19.1 Equity vs debt taxation flag
    ├── 19.2 Indexation / holding-period rules
    └── 19.3 Capital-gains classification
```

---

## CROSS-DOMAIN / REFERENCE (shared by both domains)

```
CROSS-DOMAIN / REFERENCE
│
├── R1. Identifier Crosswalk            [LIVE]  ISIN ↔ NSE ↔ BSE ↔ co_code ↔ AMFI ↔ CIN
├── R2. Sector Taxonomy / Master        [LIVE]  macro / sector / industry / basic-industry
├── R3. Calendar / Trading Holidays     [ROADMAP] NSE/BSE/RBI holiday master
├── R4. Currency / FX Rates             [ROADMAP] INR reference & cross rates
├── R5. Benchmark Index Master          [ROADMAP] indices used as MF/peer benchmarks
├── R6. Macro & Economic Indicators     [ROADMAP] repo rate, CPI/WPI, IIP, GDP, G-Sec yields
├── R7. Registrar / RTA Master          [ROADMAP] KFintech, CAMS, Link Intime
├── R8. Credit Rating Agency Master     [ROADMAP] CRISIL, ICRA, CARE, India Ratings
├── R9. Ingestion Manifest / Lineage    [LIVE]  run_id, source, sha256, rows, status (audit)
└── R10. Data Quality / Coverage Report [LIVE]  resolver coverage, resolution_reason
```

---

## Tree summary

| Domain | Level-2 modules | of which LIVE | NEXT | ROADMAP |
|--------|----------------|---------------|------|---------|
| Equity | 30 | 4 | 5 | 21 |
| Mutual Funds | 19 | 3 | 7 | 9 |
| Cross-domain | 10 | 4 | 0 | 6 |

Phase 2 enumerates **every field** inside each of these modules.
