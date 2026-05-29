"""Stock / equity response models. Field shapes mirror the gold parquet outputs."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class Stock(BaseModel):
    """Summary row from the CompanyMaster gold."""
    co_code: int = Field(examples=[101812])
    isin: str | None = Field(default=None, examples=["INE002A01018"])
    nse_symbol: str | None = Field(default=None, examples=["RELIANCE"])
    bse_code: int | None = Field(default=None, examples=[500325])
    company_name: str | None = Field(default=None, examples=["Reliance Industries Ltd"])
    sector_name: str | None = Field(default=None, examples=["Refineries & Marketing"])
    mcap_class: str | None = Field(default=None, examples=["Large Cap"])


class StockDetail(Stock):
    company_short_name: str | None = None
    sector_code: int | None = Field(default=None, examples=[1030])
    sector_confidence: str | None = Field(default=None, examples=["HIGH"])
    bse_group: str | None = None
    nse_listed: bool | None = None
    bse_listed: bool | None = None


class PricePoint(BaseModel):
    trade_date: date
    exchange: str = Field(examples=["NSE"])
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    prev_close: float | None = None
    vwap: float | None = None
    total_volume: int | None = None
    total_turnover: float | None = None
    deliverable_qty: int | None = None
    deliverable_percent: float | None = None
    no_of_trades: int | None = None


class ShareholdingPoint(BaseModel):
    quarter_end: date
    promoter_pct: float | None = None
    public_pct: float | None = None
    dii_pct: float | None = None
    fii_pct: float | None = None
    govt_pct: float | None = None
    institution_pct: float | None = None
    non_institution_pct: float | None = None
    pledged_pct: float | None = None
    number_of_shareholders: int | None = None


class CorporateActionItem(BaseModel):
    action_type: str = Field(examples=["DIVIDEND", "BONUS", "SPLIT", "RIGHTS"])
    announcement_date: date | None = None
    ex_date: date | None = None
    record_date: date | None = None
    description: str | None = None
    ratio_numerator: float | None = None
    ratio_denominator: float | None = None
    old_face_value: float | None = None
    new_face_value: float | None = None
    exchange: str | None = Field(default=None, examples=["NSE"])
    source: str | None = None
