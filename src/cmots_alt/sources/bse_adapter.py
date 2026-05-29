"""BSE source adapter.

Strategy:
  1. Try the JSON API ListofScripCode/w (gives the full active-equity master).
  2. If that fails, fall back to today's (or last business day's) equity
     bhavcopy ZIP, which has SC_CODE/SC_NAME/SC_GROUP/ISIN_CODE for the day.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from ..core.errors import FetchError
from ..core.logging import get_logger
from ..core.retry import with_retry
from ..core.settings import Settings
from ..fetchers.http import fetch_bytes
from ..storage.raw import write_bronze
from .base import BronzeResult, SourceAdapter

log = get_logger("bse")


@dataclass(frozen=True)
class BseFetchResult:
    scrips: BronzeResult
    source_kind: str   # 'json_api' | 'bhavcopy_zip'


class BseAdapter(SourceAdapter):
    name = "bse"

    def __init__(self, settings: Settings, config_path: Path | None = None) -> None:
        super().__init__(settings)
        cfg_file = config_path or (settings.project_root / "config" / "sources" / "bse.yaml")
        with cfg_file.open("r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.warmup_urls: list[str] = list(self.config.get("warmup_urls", []))

    def _try_json_api(self, partition: date) -> BronzeResult | None:
        ep = self.config["endpoints"]["list_of_scrips_api"]
        url = ep["url"]
        headers = ep.get("headers", {})
        started_at = datetime.now(timezone.utc)

        log.info("bse.fetch.api.start", url=url)

        def _do() -> bytes:
            return fetch_bytes(
                url, self.settings.http, headers=headers, warmup_urls=self.warmup_urls
            )

        try:
            payload = with_retry(_do, cfg=self.settings.retry)
        except FetchError as e:
            log.warning("bse.fetch.api.fail", url=url, err=str(e))
            return None

        if not payload or payload.lstrip()[:1] not in (b"[", b"{"):
            log.warning("bse.fetch.api.fail", url=url, err="non-JSON response")
            return None

        path, run_id = write_bronze(
            self.settings,
            source=self.name,
            artifact=ep["artifact"],
            partition=partition,
            payload=payload,
            suffix=ep["suffix"],
            started_at=started_at,
            rows=None,
        )
        log.info("bse.fetch.api.ok", path=str(path), bytes=len(payload))
        return BronzeResult(
            source=self.name,
            artifact=ep["artifact"],
            partition=partition,
            path=path,
            run_id=run_id,
        )

    def _try_bhavcopy(self, partition: date) -> BronzeResult | None:
        ep = self.config["endpoints"]["bhavcopy_fallback"]
        template = ep["url_template"]
        started_at = datetime.now(timezone.utc)

        # Try today, then walk back up to 5 business days (covers weekends + holidays).
        candidates: list[date] = []
        d = partition
        while len(candidates) < 6:
            candidates.append(d)
            d = d - timedelta(days=1)

        headers = ep.get("headers", {})
        for try_date in candidates:
            ymd = try_date.strftime("%Y%m%d")
            url = template.format(ymd=ymd)
            log.info("bse.fetch.bhav.start", url=url, try_date=try_date.isoformat())
            try:
                payload = fetch_bytes(
                    url, self.settings.http, headers=headers, warmup_urls=self.warmup_urls
                )
            except FetchError as e:
                log.warning("bse.fetch.bhav.try_fail", url=url, err=str(e))
                continue
            # New bhavcopy is a plain CSV beginning with the TradDt header.
            # A missing file returns the SPA homepage (starts with "<!DOCTYPE").
            if not payload[:80].lstrip().startswith(b"TradDt"):
                log.warning("bse.fetch.bhav.try_fail", url=url, err="not-bhavcopy-csv")
                continue
            path, run_id = write_bronze(
                self.settings,
                source=self.name,
                artifact=ep["artifact"],
                partition=partition,
                payload=payload,
                suffix=ep["suffix"],
                started_at=started_at,
                rows=None,
            )
            log.info(
                "bse.fetch.bhav.ok",
                url=url,
                try_date=try_date.isoformat(),
                bytes=len(payload),
                path=str(path),
            )
            return BronzeResult(
                source=self.name,
                artifact=ep["artifact"],
                partition=partition,
                path=path,
                run_id=run_id,
            )
        return None

    def fetch(self, *, partition: date, **_: object) -> BseFetchResult:  # type: ignore[override]
        result = self._try_json_api(partition)
        if result is not None:
            return BseFetchResult(scrips=result, source_kind="json_api")

        log.info("bse.fetch.fallback_to_bhavcopy")
        result = self._try_bhavcopy(partition)
        if result is None:
            raise FetchError("BSE: both JSON API and bhavcopy fallback failed")
        return BseFetchResult(scrips=result, source_kind="bhavcopy_csv")
