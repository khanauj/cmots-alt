"""API configuration.

API-specific settings (host/port/CORS/title) layered on top of the existing
core Settings (which owns storage paths). Override via CMOTS_API_* env vars.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CMOTS_API_",
        extra="ignore",
        populate_by_name=True,
    )

    title: str = "CMOTS-alt API"
    description: str = (
        "Orchestration layer over the CMOTS-alternative data pipelines. "
        "Serves gold parquet outputs (stocks, prices, corporate actions, "
        "shareholding, mutual funds) and triggers ingestion pipelines.\n\n"
        "### 📊 Master Data Viewer\n"
        "Browse the full **[Stock Master & Mutual Fund Master &rarr;](/ui)** "
        "in a searchable, paginated web grid — "
        "[Stock Master](/ui?view=stocks) · [Mutual Funds Master](/ui?view=mf)."
    )
    version: str = "0.1.0"

    # Render (and most PaaS) inject PORT; also overridable via CMOTS_API_PORT.
    # HOST defaults to 0.0.0.0 so the container is reachable externally.
    host: str = Field(default="0.0.0.0", alias="CMOTS_API_HOST")
    port: int = Field(default=8000, alias="PORT")
    reload: bool = False

    # Comma-separated origins; "*" allows all (dev default).
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"


@lru_cache(maxsize=1)
def get_api_settings() -> ApiSettings:
    return ApiSettings()
