"""Mutual-fund routes — served from the latest gold parquet (Polars lazy scan)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.concurrency import run_in_threadpool

from ..schemas.common import MessageResponse
from ..schemas.mutual_funds import HoldingItem, MutualFund, MutualFundDetail, NavPoint
from ..services import gold

router = APIRouter(tags=["mutual-funds"])

_CODE = Path(..., description="AMFI scheme code", examples=[120503])
_NOT_FOUND = {404: {"model": MessageResponse, "description": "Scheme code not found"}}


async def _scheme_or_404(scheme_code: int) -> dict:
    row = await run_in_threadpool(gold.get_mutual_fund, scheme_code)
    if row is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"scheme_code {scheme_code} not found"
        )
    return row


@router.get(
    "/mutual-funds",
    response_model=list[MutualFund],
    summary="List MF schemes",
)
async def list_mutual_funds(
    search: str | None = Query(None, description="Filter by scheme name substring"),
    amc: str | None = Query(None, description="Filter by AMC name substring"),
    category: str | None = Query(None, description="Filter by category substring (e.g. Equity, Debt)"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[MutualFund]:
    return await run_in_threadpool(
        gold.list_mutual_funds, search, amc, category, limit, offset
    )


@router.get(
    "/mutual-fund/{scheme_code}",
    response_model=MutualFundDetail,
    responses=_NOT_FOUND,
    summary="MF scheme detail",
)
async def get_mutual_fund(scheme_code: int = _CODE) -> MutualFundDetail:
    return await _scheme_or_404(scheme_code)


@router.get(
    "/mutual-fund/{scheme_code}/nav",
    response_model=list[NavPoint],
    responses=_NOT_FOUND,
    summary="NAV history",
)
async def get_nav(
    scheme_code: int = _CODE,
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    limit: int = Query(250, ge=1, le=5000),
) -> list[NavPoint]:
    # 404 if scheme unknown
    await _scheme_or_404(scheme_code)
    return await run_in_threadpool(gold.mf_nav, scheme_code, from_date, to_date, limit)


@router.get(
    "/mutual-fund/{scheme_code}/holdings",
    response_model=list[HoldingItem],
    responses=_NOT_FOUND,
    summary="Portfolio holdings (sorted by weight desc)",
)
async def get_holdings(
    scheme_code: int = _CODE,
    instrument_type: str | None = Query(None, description="EQUITY, DEBT, CASH, TREPS, ..."),
    limit: int | None = Query(None, ge=1, le=500, description="Cap number of rows returned"),
) -> list[HoldingItem]:
    await _scheme_or_404(scheme_code)
    return await run_in_threadpool(gold.mf_holdings, scheme_code, instrument_type, limit)
