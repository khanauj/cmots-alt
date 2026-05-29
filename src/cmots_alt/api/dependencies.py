"""Shared FastAPI dependencies and scaffold helpers."""

from __future__ import annotations

from fastapi import HTTPException, status

from ..core.settings import Settings, load_settings


def get_settings() -> Settings:
    """Project settings (storage paths etc.). Cached by load_settings()."""
    return load_settings()


def scaffold_not_implemented(what: str) -> HTTPException:
    """Uniform 501 for endpoints whose data binding isn't wired yet.

    The success response_model is still declared on each route, so Swagger shows
    the full contract — only the gold-parquet read is pending (see services/gold.py).
    """
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"scaffold: {what} not yet wired to gold outputs",
    )
