# Phase 2 — Field Inventory

Every field, for every module in the [data tree](phase1-data-tree.md).
Field names use the project convention: **PascalCase** for output/gold columns,
**lowercase** for internal join keys (`co_code`, `isin`, `scheme_code`).
Type codes: `INT`, `BIGINT`, `STR`, `DATE`, `DATETIME`, `DEC(p,s)`, `BOOL`, `PCT` (decimal percent).

---

# EQUITY

## 1. Company / Security Master  [LIVE]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (PK) | Internal canonical company id (surrogate, ≥100001) |
| isin | STR(12) | ISIN — natural key |
| NSESymbol | STR | NSE trading symbol |
| BSECode | INT | BSE scrip code |
| BSETicker | STR | BSE scrip id (alpha) |
| CIN | STR(21) | MCA Corporate Identity Number |
| LegalName | STR | Full registered company name |
| ShortName | STR | Display/abbreviated name (CMOTS-style) |
| FormerNames | STR[] | Prior names (history) |
| Category | STR | EQUITY / MF / ETF / GOVT / preference / debt |
| InstrumentType | STR | Equity share / DVR / preference / warrant |
| SectorCode | INT | FK → sector_master |
| SectorName | STR | Sector display name |
| Industry | STR | Industry (NSE level-3) |
| BasicIndustry | STR | Basic industry (NSE level-4) |
| MacroSector | STR | Macro-economic sector (NSE level-1) |
| McapClass | STR | Large / Mid / Small / Micro cap |
| BSEGroup | STR | A / B / T / X / Z / etc. |
| FaceValue | DEC(10,2) | Par value per share |
| NSEListed | BOOL | Listed on NSE |
| BSEListed | BOOL | Listed on BSE |
| ListingDate | DATE | First listing date |
| RegisteredOffice | STR | Address |
| State | STR | State of registered office |
| Website | STR | Corporate website |
| Email | STR | Investor-relations email |
| Phone | STR | Contact |
| RTAName | STR | Registrar & transfer agent |
| AuditorName | STR | Statutory auditor |
| CompanySecretary | STR | CS name |
| IncorporationDate | DATE | Date of incorporation (MCA) |
| FirstSeenAt | DATETIME | First ingestion timestamp (lineage) |
| LastSeenAt | DATETIME | Latest ingestion timestamp (lineage) |

## 2. Listing & Capital Structure  [NEXT]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| AuthorisedCapital | DEC(18,2) | Authorised share capital (₹) |
| IssuedCapital | DEC(18,2) | Issued capital (₹) |
| PaidUpCapital | DEC(18,2) | Paid-up capital (₹) |
| SharesOutstanding | BIGINT | Total shares outstanding |
| FreeFloatShares | BIGINT | Free-float shares |
| FreeFloatFactor | DEC(5,4) | Free-float factor (0–1) |
| NSEListingDate | DATE | NSE listing |
| BSEListingDate | DATE | BSE listing |
| IPODate | DATE | IPO date |
| IPOPrice | DEC(10,2) | IPO issue price |
| SuspensionStatus | STR | Active / suspended / delisted |
| DelistingDate | DATE | If delisted |
| CapitalEventType | STR | FPO / QIP / rights / preferential |
| CapitalEventDate | DATE | Date of capital event |
| CapitalEventShares | BIGINT | Shares added |

## 3. Price Data — EOD  [LIVE]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| BSECode | INT | BSE scrip (when BSE row) |
| NSESymbol | STR | NSE symbol (when NSE row) |
| TradeDate | DATE | Trading date |
| Exchange | STR | NSE / BSE |
| Series | STR | EQ / BE / SM / etc. (NSE) |
| Open | DEC(14,2) | Open price |
| High | DEC(14,2) | High |
| Low | DEC(14,2) | Low |
| Close | DEC(14,2) | Close |
| PrevClose | DEC(14,2) | Previous close |
| LastPrice | DEC(14,2) | Last traded price |
| VWAP | DEC(14,2) | Volume-weighted avg price |
| TotalVolume | BIGINT | Traded quantity |
| TotalTurnover | DEC(18,2) | Traded value (₹) |
| NoOfTrades | BIGINT | Number of trades |
| DeliverableQty | BIGINT | Deliverable quantity |
| DeliverablePercent | DEC(6,2) | Delivery % |
| Week52High | DEC(14,2) | 52-week high |
| Week52Low | DEC(14,2) | 52-week low |
| UpperCircuit | DEC(14,2) | Upper price band |
| LowerCircuit | DEC(14,2) | Lower price band |
| PriceBandPct | DEC(6,2) | Circuit band % |

## 4. Price Data — Intraday / Real-time  [ROADMAP]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| Timestamp | DATETIME | Tick/bar timestamp |
| Interval | STR | tick/1m/5m/15m/60m |
| Open/High/Low/Close | DEC(14,2) | Bar OHLC |
| Volume | BIGINT | Bar volume |
| LTP | DEC(14,2) | Last traded price |
| LTQ | BIGINT | Last traded quantity |
| BidPrice / AskPrice | DEC(14,2) | Best bid / ask |
| BidQty / AskQty | BIGINT | Bid / ask quantity |
| TotalBuyQty / TotalSellQty | BIGINT | Order-book pressure |
| OpenInterest | BIGINT | OI (derivatives) |
| AvgTradePrice | DEC(14,2) | Day avg trade price |

## 5. Adjusted Price History  [NEXT]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| TradeDate | DATE | Date |
| CloseRaw | DEC(14,2) | Unadjusted close |
| CloseSplitAdj | DEC(14,4) | Split/bonus-adjusted close |
| CloseTotalReturn | DEC(14,4) | Dividend-adjusted (TR) close |
| AdjustmentFactor | DEC(14,8) | Cumulative adjustment factor |
| AdjustmentReason | STR | split / bonus / dividend / rights |

## 6. Corporate Actions  [LIVE]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| BSECode | INT | BSE scrip |
| ActionType | STR | DIVIDEND/BONUS/SPLIT/RIGHTS/BUYBACK/FV_CHANGE/MERGER/NAME_CHANGE/DELISTING |
| ActionSubType | STR | interim/final/special (dividends) |
| AnnouncementDate | DATE | Announcement |
| ExDate | DATE | Ex-date |
| RecordDate | DATE | Record date |
| BookClosureStart | DATE | Book closure start |
| BookClosureEnd | DATE | Book closure end |
| EffectiveDate | DATE | Effective/payment date |
| DividendPerShare | DEC(14,4) | ₹/share (dividends) |
| DividendPercent | DEC(8,2) | % of face value |
| RatioNumerator | DEC(12,4) | e.g. bonus 1:2 → 1 |
| RatioDenominator | DEC(12,4) | e.g. bonus 1:2 → 2 |
| OldFaceValue | DEC(10,2) | Pre-action FV |
| NewFaceValue | DEC(10,2) | Post-action FV |
| RightsPrice | DEC(14,2) | Rights issue price |
| BuybackPrice | DEC(14,2) | Buyback price |
| Purpose | STR | Free-text purpose / remarks |
| Source | STR | NSE / BSE |

## 7. Financial Statements  [NEXT]

Shared header fields (every statement row):

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| StatementType | STR | PL / BS / CF |
| Basis | STR | Standalone / Consolidated |
| PeriodType | STR | Q / H / 9M / Annual |
| PeriodEnd | DATE | Fiscal period end |
| FiscalYear | STR | e.g. FY2025 |
| Currency | STR | INR |
| UnitMultiplier | INT | 1 / 100000 (lakh) / 10000000 (crore) |
| AuditStatus | STR | Audited / Unaudited / Limited review |
| FilingDate | DATE | Result filing date |

**7.1 Profit & Loss line items**: Revenue/Net Sales, Other Operating Income, Total Income,
Other Income, Cost of Materials, Purchase of Stock-in-Trade, Change in Inventory,
Employee Benefit Expense, Finance Costs, Depreciation & Amortisation, Other Expenses,
Total Expenses, EBITDA, EBIT, PBT (Profit Before Tax), Exceptional Items,
Tax — Current, Tax — Deferred, PAT (Profit After Tax), Minority Interest,
Share of Associates, Net Profit, OCI (Other Comprehensive Income), Total Comprehensive Income,
Basic EPS, Diluted EPS, Dividend per Share.

**7.2 Balance Sheet line items**: Equity Share Capital, Other Equity / Reserves,
Total Shareholders' Funds, Minority Interest, Long-term Borrowings, Deferred Tax Liabilities,
Other Long-term Liabilities, Long-term Provisions, Short-term Borrowings, Trade Payables,
Other Current Liabilities, Short-term Provisions, Total Liabilities, Tangible Assets,
Intangible Assets, Capital WIP, Non-current Investments, Long-term Loans & Advances,
Inventories, Trade Receivables, Cash & Bank, Short-term Loans & Advances, Current Investments,
Other Current Assets, Total Assets, Contingent Liabilities, Book Value per Share.

**7.3 Cash Flow line items**: Cash from Operating Activities, Cash from Investing Activities,
Cash from Financing Activities, Net Cash Flow, Opening Cash, Closing Cash,
Depreciation (add-back), Working Capital Changes, Tax Paid, Interest Paid,
Dividend Paid, Capex, Free Cash Flow (derived).

**7.8 Banking/NBFC schedule** (when applicable): Interest Earned, Interest Expended,
Net Interest Income (NII), Provisions & Contingencies, Gross NPA, Net NPA, GNPA%, NNPA%,
CASA, Advances, Deposits, CAR/CRAR, Net Interest Margin (NIM), Cost-to-Income.

## 8. Ratios & Derived Fundamentals  [NEXT]

| Field | Type | Description |
|-------|------|-------------|
| co_code, PeriodEnd, Basis | — | Keys |
| GrossMargin | PCT | Gross profit / revenue |
| OperatingMargin | PCT | EBIT / revenue |
| EBITDAMargin | PCT | EBITDA / revenue |
| NetMargin | PCT | PAT / revenue |
| ROE | PCT | Return on equity |
| ROCE | PCT | Return on capital employed |
| ROA | PCT | Return on assets |
| CurrentRatio | DEC(8,2) | Current assets / current liabilities |
| QuickRatio | DEC(8,2) | (CA − inventory) / CL |
| DebtToEquity | DEC(8,2) | Total debt / equity |
| InterestCoverage | DEC(8,2) | EBIT / interest |
| AssetTurnover | DEC(8,2) | Revenue / total assets |
| InventoryTurnover | DEC(8,2) | COGS / inventory |
| ReceivableDays | DEC(8,1) | Debtor days |
| PayableDays | DEC(8,1) | Creditor days |
| CashConversionCycle | DEC(8,1) | Days |
| EPS | DEC(12,2) | Earnings per share |
| BookValuePerShare | DEC(12,2) | BVPS |
| CashFlowPerShare | DEC(12,2) | CFPS |
| DividendPerShare | DEC(12,2) | DPS |
| DividendPayout | PCT | DPS / EPS |
| SalesGrowthYoY | PCT | Revenue growth |
| ProfitGrowthYoY | PCT | PAT growth |
| EPSGrowthYoY | PCT | EPS growth |
| SalesCAGR3Y / 5Y | PCT | Multi-year CAGR |
| ProfitCAGR3Y / 5Y | PCT | Multi-year CAGR |
| DuPont_NetMargin / AssetTurnover / EquityMultiplier | DEC | DuPont components |
| AltmanZScore | DEC(8,2) | Bankruptcy score |
| PiotroskiFScore | INT | 0–9 quality score |

## 9. Valuation Metrics  [NEXT]

| Field | Type | Description |
|-------|------|-------------|
| co_code, AsOfDate | — | Keys |
| MarketCap | DEC(18,2) | Full market cap (₹) |
| FreeFloatMarketCap | DEC(18,2) | Free-float mcap |
| EnterpriseValue | DEC(18,2) | EV |
| PE_TTM | DEC(10,2) | Trailing P/E |
| PE_Forward | DEC(10,2) | Forward P/E |
| PB | DEC(10,2) | Price / book |
| PS | DEC(10,2) | Price / sales |
| PCF | DEC(10,2) | Price / cash flow |
| EV_EBITDA | DEC(10,2) | EV / EBITDA |
| EV_Sales | DEC(10,2) | EV / sales |
| EV_EBIT | DEC(10,2) | EV / EBIT |
| DividendYield | PCT | DPS / price |
| EarningsYield | PCT | EPS / price |
| PEG | DEC(10,2) | PE / growth |
| PE_MedianHist | DEC(10,2) | Historical median P/E |
| PE_Percentile | PCT | Current P/E percentile vs history |

## 10. Shareholding Pattern  [LIVE]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| BSECode | INT | BSE scrip |
| QuarterEnd | DATE | Quarter-end date |
| PromoterPct | PCT | Promoter holding |
| PromoterGroupPct | PCT | Promoter group |
| PromoterPledgePct | PCT | Pledged % of promoter holding |
| FIIPct | PCT | FII / FPI |
| DIIPct | PCT | Domestic institutions |
| MutualFundPct | PCT | MF holding |
| InsurancePct | PCT | Insurance holding |
| BankFIPct | PCT | Banks / FIs |
| GovtPct | PCT | Govt holding |
| InstitutionPct | PCT | Total institutional |
| NonInstitutionPct | PCT | Total non-institutional |
| PublicPct | PCT | Public |
| RetailPct | PCT | Retail (≤₹2L) |
| HNIPct | PCT | Individuals >₹2L |
| CorporateBodiesPct | PCT | Bodies corporate |
| NRIPct | PCT | NRI |
| PledgedPct | PCT | Total encumbered |
| NumberOfShareholders | BIGINT | Total shareholders |

## 11. Institutional & Major Holders  [ROADMAP]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| QuarterEnd | DATE | Period |
| HolderType | STR | MF / FII / Insurance / Other |
| HolderName | STR | Institution / scheme name |
| HolderSchemeCode | INT | FK → MF scheme (if MF) |
| SharesHeld | BIGINT | Shares |
| HoldingPct | PCT | % of capital |
| HoldingValue | DEC(18,2) | ₹ value |
| ChangeQoQShares | BIGINT | Net change vs prev quarter |

## 12. Board, Management & Governance  [ROADMAP]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| PersonName | STR | Director / KMP name |
| DIN | STR | Director Identification Number |
| Designation | STR | Chairman / MD / CEO / CFO / ID |
| Category | STR | Executive / Non-exec / Independent |
| AppointmentDate | DATE | Date appointed |
| CessationDate | DATE | Date ceased (if any) |
| Remuneration | DEC(18,2) | Annual remuneration |
| Committees | STR[] | Audit / NRC / Stakeholders / CSR |

## 13. Announcements & Corporate Filings  [ROADMAP]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| AnnouncementId | STR | Exchange announcement id |
| Exchange | STR | NSE / BSE |
| AnnouncementDateTime | DATETIME | Timestamp |
| Category | STR | Board meeting / result / Reg-30 / press release |
| Subject | STR | Headline |
| Description | STR | Body / summary |
| AttachmentURL | STR | PDF/XBRL link |

## 14. Events & Calendar  [ROADMAP]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| EventType | STR | Board meeting / AGM / EGM / result / dividend |
| EventDate | DATE | Scheduled date |
| Purpose | STR | Purpose |
| ExDate / RecordDate / BookClosure | DATE | If corporate-action event |

## 15. Insider Trading (SEBI PIT)  [ROADMAP]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| AcquirerName | STR | Insider / promoter |
| Category | STR | Promoter / Director / KMP / Designated person |
| TransactionType | STR | Buy / Sell / Pledge / Pledge release |
| Shares | BIGINT | Quantity |
| Value | DEC(18,2) | Value |
| TransactionDate | DATE | Date |
| IntimationDate | DATE | Disclosure date |
| ModeOfAcquisition | STR | Market / off-market / ESOP |
| HoldingBefore / HoldingAfter | PCT | Pre/post holding |

## 16. Bulk Deals · 17. Block Deals  [ROADMAP]

| Field | Type | Description |
|-------|------|-------------|
| co_code | INT (FK) | Company |
| Exchange | STR | NSE / BSE |
| DealDate | DATE | Trade date |
| DealType | STR | BULK / BLOCK |
| ClientName | STR | Buyer/seller name |
| BuySell | STR | BUY / SELL |
| Quantity | BIGINT | Shares |
| Price | DEC(14,2) | Weighted avg trade price |
| Value | DEC(18,2) | Deal value |

## 18. Short Selling / SLB  [ROADMAP]
co_code, TradeDate, ShortQty, ShortValue, SLB_OutstandingQty, LendingFeePct.

## 19. Surveillance & Risk Flags  [ROADMAP]
co_code, AsOfDate, ASMStage, GSMStage, InFnOBan (BOOL), CircuitStage, SuspensionFlag, InsolvencyFlag.

## 20. Credit Ratings  [ROADMAP]
co_code, Agency, InstrumentType, RatingScale (LT/ST), Rating, Outlook, RatingAction, RatingDate, RationaleURL.

## 21. Technical Indicators  [ROADMAP]

| Field | Type | Description |
|-------|------|-------------|
| co_code, TradeDate | — | Keys |
| SMA5/10/20/50/100/200 | DEC(14,2) | Simple moving averages |
| EMA5/10/20/50/100/200 | DEC(14,2) | Exponential MAs |
| RSI14 | DEC(6,2) | Relative strength index |
| MACD / MACDSignal / MACDHist | DEC(10,4) | MACD |
| Stochastic_K / _D | DEC(6,2) | Stochastic oscillator |
| CCI / WilliamsR / MFI | DEC(8,2) | Momentum / volume |
| ATR14 | DEC(10,4) | Average true range |
| BollingerUpper/Mid/Lower | DEC(14,2) | Bollinger bands |
| ADX / PlusDI / MinusDI | DEC(6,2) | Trend strength |
| SAR / Supertrend | DEC(14,2) | Trend-following |
| OBV | BIGINT | On-balance volume |
| Pivot / R1 / R2 / R3 / S1 / S2 / S3 | DEC(14,2) | Pivot levels |
| Beta1Y | DEC(6,3) | Beta vs index |
| Volatility30D | PCT | Annualised vol |

## 22. Derivatives (F&O)  [ROADMAP]
co_code/IndexCode, Symbol, InstrumentType (FUT/OPT), ExpiryDate, StrikePrice, OptionType (CE/PE),
Open/High/Low/Close/Settle, OpenInterest, ChangeInOI, NumberOfContracts, Volume, Value,
ImpliedVolatility, Delta/Gamma/Theta/Vega/Rho, LotSize, PCR.

## 23. Index Data  [ROADMAP]
IndexCode, IndexName, IndexType (broad/sector/thematic), TradeDate, Open/High/Low/Close,
PrevClose, PointsChange, PctChange, IndexPE, IndexPB, IndexDivYield, MarketCap;
constituents: IndexCode, co_code, Weight, FreeFloatMcap, JoinDate, ExitDate.

## 24. Sector / Industry Classification  [LIVE]
SectorCode (PK), SectorName, MacroSector, Industry, BasicIndustry, NSECode, BSECode,
ParentSectorCode, ConfidenceScore, Source.

## 25. Peer Comparison  [ROADMAP]
co_code, PeerCoCode, PeerGroupId, MarketCap, PE, PB, ROE, SalesGrowth, NetMargin, RankInPeerGroup.

## 26. Analyst Estimates  [ROADMAP]
co_code, FiscalYear, MetricType (EPS/Revenue/EBITDA), ConsensusMean, High, Low, NumAnalysts,
TargetPrice, Recommendation, BuyCount, HoldCount, SellCount, AsOfDate, ActualValue, SurprisePct.

## 27. News & Research  [ROADMAP]
co_code, NewsId, Source, PublishedAt, Headline, Summary, URL, SentimentScore, Category.

## 28. Primary Market / IPO  [ROADMAP]
IssueId, co_code, IssueType (IPO/FPO/OFS/Rights/SME), PriceBandLow/High, LotSize, IssueSize,
OpenDate, CloseDate, ListingDate, QIBx, NIIx, Retailx, TotalSubscriptionx, GMP, ListingPrice, ListingGainPct.

## 29. ESG  [ROADMAP]
co_code, AsOfDate, ESGScore, EnvScore, SocialScore, GovScore, ESGRating, ControversyLevel,
CarbonIntensity, Provider.

## 30. Market Statistics  [ROADMAP]
TradeDate, Exchange, Advances, Declines, Unchanged, New52WHigh, New52WLow, FIINetCash,
DIINetCash, TotalTurnover, AdvanceDeclineRatio.

---

# MUTUAL FUNDS

## 1. AMC Master  [NEXT]

| Field | Type | Description |
|-------|------|-------------|
| AMCCode | INT (PK) | Internal AMC id |
| AMCName | STR | Asset management company |
| SponsorName | STR | Sponsor |
| TrusteeName | STR | Trustee company |
| SEBIRegNo | STR | SEBI registration |
| IncorporationDate | DATE | Incorporation |
| RTAName | STR | CAMS / KFintech |
| CustodianName | STR | Custodian |
| Website | STR | AMC website |
| TotalAUM | DEC(18,2) | Total AUM (₹ cr) |
| AUMRank | INT | Rank among AMCs |

## 2. Scheme Master  [LIVE]

| Field | Type | Description |
|-------|------|-------------|
| SchemeCode | INT (PK) | AMFI scheme code |
| ISINGrowth | STR | ISIN — growth option |
| ISINIDCW | STR | ISIN — IDCW option |
| SchemeName | STR | Full scheme name |
| AMCCode | INT (FK) | AMC |
| AMCName | STR | AMC name |
| Category | STR | Equity/Debt/Hybrid/Solution/Other |
| SubCategory | STR | Large Cap / Liquid / ELSS / etc. |
| Plan | STR | Regular / Direct |
| Option | STR | Growth / IDCW / IDCW-Reinvest |
| LaunchDate | DATE | Scheme launch |
| ClosureDate | DATE | NFO closure |
| ReopenDate | DATE | Reopening for purchase |
| Benchmark | STR | Benchmark index |
| RiskometerLevel | STR | Low … Very High |
| MinInvestment | DEC(14,2) | Minimum lump sum |
| MinSIP | DEC(14,2) | Minimum SIP |
| ExpenseRatio | PCT | TER |
| ExitLoad | STR | Exit-load description |
| LockInPeriod | INT | Days (ELSS=1095) |
| FundManager | STR | Current manager(s) |
| AUM | DEC(18,2) | Latest scheme AUM (₹ cr) |
| IsActive | BOOL | Active / merged / wound-up |

## 3. NAV Data  [LIVE]

| Field | Type | Description |
|-------|------|-------------|
| SchemeCode | INT (FK) | Scheme |
| NAVDate | DATE | NAV date |
| NAV | DEC(14,4) | Net asset value |
| RepurchasePrice | DEC(14,4) | Repurchase price |
| SalePrice | DEC(14,4) | Sale price |
| NAVAdjusted | DEC(14,4) | IDCW-reinvested NAV |
| DayChange | DEC(14,4) | NAV change |
| DayChangePct | PCT | NAV % change |

## 4. Holdings / Portfolio  [LIVE]

| Field | Type | Description |
|-------|------|-------------|
| SchemeCode | INT (FK) | Scheme |
| QuarterEnd | DATE | Portfolio date (month/quarter-end) |
| InstrumentName | STR | Holding name |
| ISIN | STR | Instrument ISIN |
| co_code | INT (FK) | Mapped equity (if equity) |
| InstrumentType | STR | EQUITY/DEBT/CASH/TREPS/REIT/DERIVATIVE |
| Sector | STR | Sector of holding |
| Quantity | DEC(20,2) | Units / face value held |
| MarketValue | DEC(18,2) | ₹ value |
| WeightPct | PCT | % of net assets |
| Rating | STR | Credit rating (debt) |
| YTM | DEC(8,4) | Yield (debt) |
| Coupon | DEC(8,4) | Coupon (debt) |
| MaturityDate | DATE | Maturity (debt) |

## 5. Asset Allocation  [NEXT]
SchemeCode, AsOfDate, EquityPct, DebtPct, CashPct, OtherPct, DerivativePct,
LargeCapPct, MidCapPct, SmallCapPct.

## 6. Sector Allocation  [NEXT]
SchemeCode, AsOfDate, SectorName, WeightPct, BenchmarkWeightPct, ActiveWeightPct, Rank.

## 7. Returns  [NEXT]

| Field | Type | Description |
|-------|------|-------------|
| SchemeCode | INT (FK) | Scheme |
| AsOfDate | DATE | Return as-of date |
| Return1D/1W/1M/3M/6M | PCT | Point-to-point (absolute) |
| Return1Y/2Y/3Y/5Y/7Y/10Y | PCT | Annualised (CAGR) |
| ReturnSinceInception | PCT | SI CAGR |
| ReturnYTD | PCT | Year to date |
| CYReturn (per year) | PCT | Calendar-year returns |
| SIPReturn1Y/3Y/5Y (XIRR) | PCT | SIP XIRR |
| BenchmarkReturn (matched tenor) | PCT | Benchmark comparison |
| CategoryReturn (matched tenor) | PCT | Category average |

## 8. Risk Metrics  [NEXT]

| Field | Type | Description |
|-------|------|-------------|
| SchemeCode, AsOfDate, Period | — | Keys (Period e.g. 3Y) |
| StdDev | PCT | Annualised standard deviation |
| Sharpe | DEC(8,3) | Sharpe ratio |
| Sortino | DEC(8,3) | Sortino ratio |
| Beta | DEC(8,3) | Beta vs benchmark |
| Alpha | DEC(8,3) | Jensen's alpha |
| RSquared | DEC(6,3) | R² |
| Treynor | DEC(8,3) | Treynor ratio |
| InformationRatio | DEC(8,3) | IR |
| MaxDrawdown | PCT | Max drawdown |
| UpCaptureRatio / DownCaptureRatio | DEC(8,2) | Capture ratios |

## 9. AUM / Fund Size  [NEXT]
SchemeCode, MonthEnd, AUM, AAUM, FolioCount.

## 10. Fund Manager  [NEXT]
ManagerId, ManagerName, Qualification, ExperienceYears, SchemeCode, ManagingSince,
SchemesManagedCount, AvgTenureReturn.

## 11. Expense & Load  [NEXT]
SchemeCode, AsOfDate, TERRegular, TERDirect, ExitLoadSlab (STR), EntryLoad.

## 12. Dividend / IDCW History  [ROADMAP]
SchemeCode, RecordDate, IDCWPerUnit, IDCWFrequency, CumNAVBefore.

## 13. Portfolio Analytics  [ROADMAP]
SchemeCode, AsOfDate, PortfolioTurnoverPct, NumberOfHoldings, Top10ConcentrationPct,
ActiveSharePct; overlap table: SchemeCodeA, SchemeCodeB, OverlapPct.

## 14. Debt-Specific Analytics  [ROADMAP]
SchemeCode, AsOfDate, AvgMaturityYears, ModifiedDuration, MacaulayDuration, YTM,
CreditAAAPct, CreditAAPct, CreditAPct, CreditBelowAPct, SovereignPct,
GSecPct, CorpBondPct, CPPct, CDPct, TREPSPct.

## 15. Scheme Categorisation  [NEXT]
SchemeCode, SEBICategory, SEBISubCategory, RiskometerLevel, IsELSS, IsIndexFund, IsETF.

## 16. Ratings & Rankings  [ROADMAP]
SchemeCode, AsOfDate, CRISILRank, ValueResearchStars, MorningstarRating, QuartileRank, Provider.

## 17. NFO  [ROADMAP]
SchemeCode, NFOOpenDate, NFOCloseDate, NFOPrice, NFOCollection, AllotmentDate.

## 18. Transactions / Plans  [ROADMAP]
SchemeCode, SIPMinAmount, SIPFrequencies, STPAvailable, SWPAvailable, MinAdditional, LockInDays.

## 19. Taxation  [ROADMAP]
SchemeCode, TaxBucket (Equity/Debt/Hybrid), LTCGHoldingMonths, STCGRate, LTCGRate, IndexationEligible.

---

# CROSS-DOMAIN / REFERENCE

## R1. Identifier Crosswalk  [LIVE]
isin, id_type (NSE/BSE/AMFI/CIN), id_value, source, confidence, seen_at.

## R2. Sector Master  [LIVE]
SectorCode (PK), SectorName, MacroSector, Industry, BasicIndustry, ParentSectorCode, Source, ConfidenceScore.

## R3. Trading Calendar  [ROADMAP]
CalendarDate, Exchange, IsTradingDay, HolidayName, Segment (cash/F&O/currency).

## R4. FX Rates  [ROADMAP]
RateDate, BaseCcy, QuoteCcy, Rate, Source (RBI).

## R5. Benchmark Index Master  [ROADMAP]
IndexCode, IndexName, Provider (NSE/BSE/CRISIL), BaseDate, BaseValue.

## R6. Macro Indicators  [ROADMAP]
IndicatorCode, IndicatorName, Date, Value, Unit, Frequency, Source (RBI/MOSPI).

## R7. RTA Master  [ROADMAP]
RTACode, RTAName, Type (equity/MF), Website, Contact.

## R8. Credit Rating Agency Master  [ROADMAP]
AgencyCode, AgencyName (CRISIL/ICRA/CARE/India Ratings), SEBIRegNo.

## R9. Ingestion Manifest  [LIVE]
run_id (PK), source, artifact, partition, raw_path, sha256, rows, started_at, ended_at, status.

## R10. Data Quality / Coverage  [LIVE]
run_id, module, total_rows, resolved_rows, coverage_pct, resolution_reason, generated_at.
