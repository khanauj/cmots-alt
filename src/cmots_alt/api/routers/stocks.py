"""Stock / equity routes — served from the latest gold parquet (Polars lazy scan)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Path, Query, status
from fastapi.concurrency import run_in_threadpool

from ..schemas.common import MessageResponse
from ..schemas.stocks import (
    CorporateActionItem,
    PricePoint,
    ShareholdingPoint,
    Stock,
    StockDetail,
)
from ..services import gold

router = APIRouter(tags=["stocks"])

_SYMBOL = Path(..., description="NSE symbol (case-insensitive)", examples=["RELIANCE"])
_NOT_FOUND = {404: {"model": MessageResponse, "description": "Symbol not found"}}


async def _co_code_or_404(symbol: str) -> int:
    co = await run_in_threadpool(gold.resolve_co_code, symbol)
    if co is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"symbol '{symbol}' not found")
    return co


@router.get("/stocks", response_model=list[Stock], summary="List companies")
async def list_stocks(
    search: str | None = Query(None, description="Filter by name/symbol substring"),
    sector: str | None = Query(None, description="Filter by sector name substring"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[Stock]:
    return await run_in_threadpool(gold.list_stocks, search, sector, limit, offset)


@router.get("/stock/{symbol}", response_model=StockDetail, responses=_NOT_FOUND,
            summary="Company detail")
async def get_stock(symbol: str = _SYMBOL) -> StockDetail:
    row = await run_in_threadpool(gold.get_stock, symbol)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"symbol '{symbol}' not found")
    return row


@router.get("/stock/{symbol}/prices", response_model=list[PricePoint], responses=_NOT_FOUND,
            summary="EOD price history")
async def get_prices(
    symbol: str = _SYMBOL,
    exchange: str | None = Query(None, description="NSE or BSE; default both"),
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    limit: int = Query(250, ge=1, le=5000),
) -> list[PricePoint]:
    co = await _co_code_or_404(symbol)
    return await run_in_threadpool(gold.prices, co, exchange, from_date, to_date, limit)


@router.get("/stock/{symbol}/shareholding", response_model=list[ShareholdingPoint],
            responses=_NOT_FOUND, summary="Quarterly shareholding")
async def get_shareholding(symbol: str = _SYMBOL) -> list[ShareholdingPoint]:
    co = await _co_code_or_404(symbol)
    return await run_in_threadpool(gold.shareholding, co)


@router.get("/stock/{symbol}/corporate-actions", response_model=list[CorporateActionItem],
            responses=_NOT_FOUND, summary="Corporate actions")
async def get_corporate_actions(
    symbol: str = _SYMBOL,
    action_type: str | None = Query(None, description="DIVIDEND, BONUS, SPLIT, ..."),
) -> list[CorporateActionItem]:
    co = await _co_code_or_404(symbol)
    return await run_in_threadpool(gold.corporate_actions, co, action_type)
