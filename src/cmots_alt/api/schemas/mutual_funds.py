"""Mutual-fund response models. Field shapes mirror the gold parquet outputs."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class MutualFund(BaseModel):
    """Summary row from the MF Scheme Master gold."""
    scheme_code: int = Field(examples=[120503])
    scheme_name: str | None = Field(default=None, examples=["SBI Large Cap Fund - Direct Plan - Growth"])
    amc_name: str | None = Field(default=None, examples=["SBI Mutual Fund"])
    category: str | None = Field(default=None, examples=["Equity"])


class MutualFundDetail(MutualFund):
    isin: str | None = None
    launch_date: date | None = None
    closure_date: date | None = None
    expense_ratio: float | None = None
    aum: float | None = None
    fund_manager: str | None = None
    status: str | None = Field(default=None, examples=["Active"])


class NavPoint(BaseModel):
    nav_date: date
    nav: float | None = Field(default=None, examples=[98.7654])


class HoldingItem(BaseModel):
    holding_name: str = Field(examples=["HDFC Bank Ltd."])
    holding_isin: str | None = Field(default=None, examples=["INE040A01034"])
    co_code: int | None = Field(default=None, examples=[100208])
    instrument_type: str = Field(examples=["EQUITY", "DEBT", "CASH"])
    weight_pct: float | None = Field(default=None, examples=[7.63])
    quantity: float | None = None
    market_value: float | None = None
    sector: str | None = None
    credit_rating: str | None = None
    quarter_end: date | None = None
