"""Corporate-action source adapters.

NSE: a single structured JSON list of corporate actions over a date window.
BSE: the "Corp. Action" announcement category, paginated, concatenated into one
     JSON array before persisting to bronze.

Both fetch a [as_of - lookback, as_of] window; nothing on a given day is an empty
list, not an error, so the pipeline still runs.
"""

from __future__ import annotations

import json
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
from .base import BronzeResult

log = get_logger("corpactions")

_BSE_PAGE_CAP = 80  # safety bound on pagination


def _load_cfg(settings: Settings, source: str) -> dict:
    with (settings.project_root / "config" / "sources" / f"{source}.yaml").open(
        "r", encoding="utf-8"
    ) as f:
        return yaml.safe_load(f)


@dataclass(frozen=True)
class CorpActionsResult:
    bronze: BronzeResult
    record_count: int
    from_date: date
    to_date: date


class NseCorpActionsAdapter:
    name = "nse"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cfg = _load_cfg(settings, "nse")
        self.ep = self.cfg["endpoints"]["corporate_actions"]

    def fetch(self, *, partition: date, lookback_days: int = 90) -> CorpActionsResult:
        frm = partition - timedelta(days=lookback_days)
        url = self.ep["url_template"].format(
            from_ddmmyyyy=frm.strftime("%d-%m-%Y"),
            to_ddmmyyyy=partition.strftime("%d-%m-%Y"),
        )
        warm = list(self.ep.get("warmup_urls", []))
        started = datetime.now(timezone.utc)
        log.info("nse.ca.start", url=url, from_date=frm.isoformat(), to_date=partition.isoformat())

        def _do() -> bytes:
            return fetch_bytes(url, self.settings.http, warmup_urls=warm)

        payload = with_retry(_do, cfg=self.settings.retry)
        try:
            records = json.loads(payload)
            count = len(records) if isinstance(records, list) else 0
        except json.JSONDecodeError as e:
            raise FetchError(f"NSE corporate actions: invalid JSON ({e})") from e

        path, run_id = write_bronze(
            self.settings, source=self.name, artifact=self.ep["artifact"],
            partition=partition, payload=payload, suffix=self.ep["suffix"],
            started_at=started, rows=count,
        )
        log.info("nse.ca.ok", records=count, path=str(path))
        return CorpActionsResult(
            bronze=BronzeResult(self.name, self.ep["artifact"], partition, path, run_id),
            record_count=count, from_date=frm, to_date=partition,
        )


class BseCorpActionsAdapter:
    name = "bse"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cfg = _load_cfg(settings, "bse")
        self.ep = self.cfg["endpoints"]["corp_action_announcements"]
        self.warmup = list(self.cfg.get("warmup_urls", []))

    def fetch(self, *, partition: date, lookback_days: int = 30) -> CorpActionsResult:
        frm = partition - timedelta(days=lookback_days)
        headers = self.ep.get("headers", {})
        started = datetime.now(timezone.utc)
        log.info("bse.ca.start", from_date=frm.isoformat(), to_date=partition.isoformat())

        records: list[dict] = []
        pageno = 1
        while pageno <= _BSE_PAGE_CAP:
            url = self.ep["url_template"].format(
                from_ymd=frm.strftime("%Y%m%d"),
                to_ymd=partition.strftime("%Y%m%d"),
                pageno=pageno,
            )

            def _do(u: str = url) -> bytes:
                return fetch_bytes(u, self.settings.http, headers=headers, warmup_urls=self.warmup)

            try:
                payload = with_retry(_do, cfg=self.settings.retry)
                page = json.loads(payload).get("Table", [])
            except (FetchError, json.JSONDecodeError) as e:
                log.warning("bse.ca.page_fail", pageno=pageno, err=str(e))
                break
            if not page:
                break
            records.extend(page)
            total_pages = int(page[0].get("TotalPageCnt") or 1)
            if pageno >= total_pages:
                break
            pageno += 1

        payload = json.dumps(records).encode("utf-8")
        path, run_id = write_bronze(
            self.settings, source=self.name, artifact=self.ep["artifact"],
            partition=partition, payload=payload, suffix=self.ep["suffix"],
            started_at=started, rows=len(records),
        )
        log.info("bse.ca.ok", records=len(records), pages=pageno, path=str(path))
        return CorpActionsResult(
            bronze=BronzeResult(self.name, self.ep["artifact"], partition, path, run_id),
            record_count=len(records), from_date=frm, to_date=partition,
        )
