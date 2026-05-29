"""FastAPI application factory for the CMOTS-alt orchestration layer.

Auto-exposes Swagger UI (/docs), ReDoc (/redoc) and the OpenAPI schema
(/openapi.json). Modular routers; reuses the project's structlog logger and core
Settings. No business logic — routers serve the contract; gold reads come next.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from ..core.logging import get_logger
from .config import get_api_settings
from .routers import admin, mutual_funds, scheduler, stocks, system

log = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_api_settings()
    log.info("api.startup", title=s.title, version=s.version)
    yield
    log.info("api.shutdown")


def create_app() -> FastAPI:
    s = get_api_settings()
    app = FastAPI(
        title=s.title,
        description=s.description,
        version=s.version,
        docs_url=s.docs_url,
        redoc_url=s.redoc_url,
        openapi_url=s.openapi_url,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        log.info(
            "api.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - start) * 1000, 1),
        )
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        log.error("api.unhandled", path=request.url.path, error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "internal server error"})

    # Routers (modular, grouped by tag in Swagger).
    app.include_router(system.router)
    app.include_router(admin.router)
    app.include_router(stocks.router)
    app.include_router(mutual_funds.router)
    app.include_router(scheduler.router)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse(url=s.docs_url)

    return app


app = create_app()
