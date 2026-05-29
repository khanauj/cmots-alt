"""Pandera schemas for gold tables. Cheap, fail-loud structural checks."""

from __future__ import annotations

import pandera.polars as pa
import polars as pl


MF_NAV_GOLD = pa.DataFrameSchema(
    {
        "SchemeCode": pa.Column(int, nullable=False),
        "SchemeName": pa.Column(str, nullable=False),
        "AMC": pa.Column(str, nullable=True),
        "SchemeType": pa.Column(str, nullable=True),
        "Category": pa.Column(str, nullable=True),
        "SubCategory": pa.Column(str, nullable=True),
        "ISIN_Growth": pa.Column(str, nullable=True),
        "ISIN_DivReinvestment": pa.Column(str, nullable=True),
        "NAV": pa.Column(float, nullable=True),
        "NAVDate": pa.Column(pl.Date, nullable=True),
    },
    strict=True,
    coerce=False,
)


def validate_mf_nav_gold(df: pl.DataFrame) -> pl.DataFrame:
    return MF_NAV_GOLD.validate(df, lazy=True)


# ---------------------------------------------------------------------------
# MF Scheme Master
# ---------------------------------------------------------------------------

MF_SCHEME_MASTER_GOLD = pa.DataFrameSchema(
    {
        "SchemeCode": pa.Column(int, nullable=False),
        "ISIN": pa.Column(str, nullable=True),
        "SchemeName": pa.Column(str, nullable=False),
        "AMCName": pa.Column(str, nullable=True),
        "FundHouse": pa.Column(str, nullable=True),
        "Category": pa.Column(str, nullable=True),
        "SubCategory": pa.Column(str, nullable=True),
        "PlanType": pa.Column(
            str, nullable=False,
            checks=pa.Check.isin(["DIRECT", "REGULAR", "RETAIL", "INSTITUTIONAL", "UNKNOWN"]),
        ),
        "OptionType": pa.Column(
            str, nullable=False,
            checks=pa.Check.isin(["GROWTH", "DIVIDEND", "IDCW", "REINVESTMENT", "BONUS", "OTHER", "UNKNOWN"]),
        ),
        "Benchmark": pa.Column(str, nullable=True),
        "RiskLevel": pa.Column(str, nullable=True),
        "FundType": pa.Column(str, nullable=True),
        "OpenEnded": pa.Column(bool, nullable=False),
        "CloseEnded": pa.Column(bool, nullable=False),
        "ETF": pa.Column(bool, nullable=False),
        "LaunchDate": pa.Column(pl.Date, nullable=True),
        "ClosureDate": pa.Column(pl.Date, nullable=True),
        "ExpenseRatio": pa.Column(float, nullable=True),
        "AUM": pa.Column(float, nullable=True),
        "FundManager": pa.Column(str, nullable=True),
        "Status": pa.Column(
            str, nullable=False,
            checks=pa.Check.isin(["Active", "Inactive"]),
        ),
    },
    strict=True,
    coerce=False,
)


def validate_mf_scheme_master_gold(df: pl.DataFrame) -> pl.DataFrame:
    return MF_SCHEME_MASTER_GOLD.validate(df, lazy=True)


# ---------------------------------------------------------------------------
# MF Holdings
# ---------------------------------------------------------------------------

MF_HOLDINGS_GOLD = pa.DataFrameSchema(
    {
        "SchemeCode": pa.Column(int, nullable=False),
        "SchemeName": pa.Column(str, nullable=False),
        "AMCName": pa.Column(str, nullable=False),
        "HoldingName": pa.Column(str, nullable=False),
        "HoldingISIN": pa.Column(str, nullable=True),
        "co_code": pa.Column(int, nullable=True),
        "WeightPct": pa.Column(float, nullable=False),
        "Quantity": pa.Column(float, nullable=True),
        "MarketValue": pa.Column(float, nullable=True),
        "Sector": pa.Column(str, nullable=True),
        "CreditRating": pa.Column(str, nullable=True),
        "InstrumentType": pa.Column(
            str, nullable=False,
            checks=pa.Check.isin([
                "EQUITY", "DEBT", "CASH", "TREPS", "REIT", "INVIT", "ETF",
                "MUTUAL_FUND", "DERIVATIVE", "GOLD", "SILVER", "OTHER", "UNKNOWN"
            ]),
        ),
        "QuarterEnd": pa.Column(pl.Date, nullable=False),
        "Source": pa.Column(str, nullable=False),
    },
    strict=True,
    coerce=False,
)


def validate_mf_holdings_gold(df: pl.DataFrame) -> pl.DataFrame:
    return MF_HOLDINGS_GOLD.validate(df, lazy=True)
