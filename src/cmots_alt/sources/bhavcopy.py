"""NSE + BSE end-of-day bhavcopy adapters.

Both files are published only after market close, and not at all on weekends /
holidays, so each adapter walks back from the requested date up to a small
window to find the most recent available trading-day file. The returned
``trade_date`` is the actual date of the data found (which may precede the
requested ``partition``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from ..core.errors import FetchError
from ..core.logging import get_logger
from ..core.settings import Settings
from ..fetchers.http import fetch_bytes
from ..storage.raw import write_bronze
from .base import BronzeResult

log = get_logger("bhavcopy")

_WALK_BACK_DAYS = 7


@dataclass(frozen=True)
class BhavcopyResult:
    bronze: BronzeResult
    trade_date: date


def _load_source_cfg(settings: Settings, source: str) -> dict:
    cfg_file = settings.project_root / "config" / "sources" / f"{source}.yaml"
    with cfg_file.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class _BhavcopyAdapter:
    """Shared walk-back fetch loop; subclasses supply URL + validation."""

    source: str
    endpoint_key: str
    log_prefix: str

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.config = _load_source_cfg(settings, self.source)
        self.warmup_urls: list[str] = list(self.config.get("warmup_urls", []))
        self.endpoint = self.config["endpoints"][self.endpoint_key]

    def _url_for(self, d: date) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def _is_valid_payload(self, payload: bytes) -> bool:  # pragma: no cover - overridden
        raise NotImplementedError

    def fetch(self, *, partition: date) -> BhavcopyResult:
        headers = self.endpoint.get("headers", {})
        for i in range(_WALK_BACK_DAYS):
            try_date = partition - timedelta(days=i)
            url = self._url_for(try_date)
            log.info(f"{self.log_prefix}.start", url=url, try_date=try_date.isoformat())
            started_at = datetime.now(timezone.utc)
            try:
                payload = fetch_bytes(
                    url, self.settings.http, headers=headers, warmup_urls=self.warmup_urls
                )
            except FetchError as e:
                log.warning(f"{self.log_prefix}.try_fail", url=url, err=str(e))
                continue
            if not self._is_valid_payload(payload):
                log.warning(f"{self.log_prefix}.try_fail", url=url, err="unexpected-content")
                continue

            path, run_id = write_bronze(
                self.settings,
                source=self.source,
                artifact=self.endpoint["artifact"],
                partition=partition,
                payload=payload,
                suffix=self.endpoint["suffix"],
                started_at=started_at,
                rows=payload.count(b"\n"),
            )
            log.info(
                f"{self.log_prefix}.ok",
                url=url,
                trade_date=try_date.isoformat(),
                bytes=len(payload),
                path=str(path),
            )
            return BhavcopyResult(
                bronze=BronzeResult(
                    source=self.source,
                    artifact=self.endpoint["artifact"],
                    partition=partition,
                    path=path,
                    run_id=run_id,
                ),
                trade_date=try_date,
            )
        raise FetchError(
            f"{self.source} bhavcopy: no file in {_WALK_BACK_DAYS} days back from {partition}"
        )


class NseBhavcopyAdapter(_BhavcopyAdapter):
    source = "nse"
    endpoint_key = "bhavcopy_full"
    log_prefix = "nse.bhav"

    def _url_for(self, d: date) -> str:
        return self.endpoint["url_template"].format(ddmmyyyy=d.strftime("%d%m%Y"))

    def _is_valid_payload(self, payload: bytes) -> bool:
        # sec_bhavdata_full begins with the SYMBOL header; a 404 page does not.
        return payload[:40].lstrip().startswith(b"SYMBOL")


class BseBhavcopyAdapter(_BhavcopyAdapter):
    source = "bse"
    endpoint_key = "bhavcopy_eod"
    log_prefix = "bse.bhav"

    def _url_for(self, d: date) -> str:
        return self.endpoint["url_template"].format(ymd=d.strftime("%Y%m%d"))

    def _is_valid_payload(self, payload: bytes) -> bool:
        # Unified bhavcopy starts with TradDt; a missing file returns the SPA HTML.
        return payload[:80].lstrip().startswith(b"TradDt")
