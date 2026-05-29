"""NSE source adapter.

Phase 1 fetches:
  - EQUITY_L.csv         (full NSE-listed equity master)
  - Industry classification (with fallback to Nifty Total Market)

NSE blocks naive HTTP and requires cookie warmup from www.nseindia.com.
The curl_cffi Chrome impersonation in fetchers/http.py handles TLS-fingerprint.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from ..core.errors import FetchError
from ..core.logging import get_logger
from ..core.retry import with_retry
from ..core.settings import Settings
from ..fetchers.http import fetch_bytes
from ..storage.raw import write_bronze
from .base import BronzeResult, SourceAdapter

log = get_logger("nse")


@dataclass(frozen=True)
class NseFetchResult:
    equity_l: BronzeResult
    industry: BronzeResult | None      # None if both primary and fallback failed
    industry_source: str | None        # 'primary' | 'fallback' | None


class NseAdapter(SourceAdapter):
    name = "nse"

    def __init__(self, settings: Settings, config_path: Path | None = None) -> None:
        super().__init__(settings)
        cfg_file = config_path or (settings.project_root / "config" / "sources" / "nse.yaml")
        with cfg_file.open("r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.warmup_urls: list[str] = list(self.config.get("warmup_urls", []))

    # ── single endpoint fetch ───────────────────────────────────────────────
    def _fetch_endpoint(
        self,
        endpoint_key: str,
        partition: date,
        *,
        required: bool,
    ) -> BronzeResult | None:
        ep = self.config["endpoints"][endpoint_key]
        url = ep["url"]
        encoding = ep.get("encoding", "utf-8")
        suffix = ep.get("suffix", "csv")
        artifact = ep["artifact"]
        started_at = datetime.now(timezone.utc)

        log.info("nse.fetch.start", endpoint=endpoint_key, url=url)

        def _do() -> bytes:
            return fetch_bytes(url, self.settings.http, warmup_urls=self.warmup_urls)

        try:
            payload = with_retry(_do, cfg=self.settings.retry)
        except FetchError as e:
            log.warning("nse.fetch.fail", endpoint=endpoint_key, url=url, err=str(e))
            if required:
                raise
            return None

        rows_hint = payload.count(b"\n")
        path, run_id = write_bronze(
            self.settings,
            source=self.name,
            artifact=artifact,
            partition=partition,
            payload=payload,
            suffix=suffix,
            started_at=started_at,
            rows=rows_hint,
        )
        log.info(
            "nse.fetch.ok",
            endpoint=endpoint_key,
            url=url,
            bytes=len(payload),
            path=str(path),
            run_id=run_id,
        )
        return BronzeResult(
            source=self.name,
            artifact=artifact,
            partition=partition,
            path=path,
            run_id=run_id,
            rows_hint=rows_hint,
        )

    # ── public API ──────────────────────────────────────────────────────────
    def fetch(self, *, partition: date, **_: object) -> NseFetchResult:  # type: ignore[override]
        equity_l = self._fetch_endpoint("equity_l", partition, required=True)
        assert equity_l is not None  # required=True guarantees this

        industry = self._fetch_endpoint("industry_primary", partition, required=False)
        ind_source: str | None = "primary"
        if industry is None:
            industry = self._fetch_endpoint("industry_fallback", partition, required=False)
            ind_source = "fallback" if industry is not None else None

        return NseFetchResult(equity_l=equity_l, industry=industry, industry_source=ind_source)
