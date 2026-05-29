"""Shareholding-pattern source adapters.

NSE exposes a single bulk "master" of every company's latest filed quarter
(summary promoter/public %), each row linking to a per-company XBRL that holds
the full SEBI breakdown (institutions, FII/DII, government, non-institutions,
shareholder counts). We fetch the master once, then the XBRL for a bounded set.

BSE shareholding is only available per-scrip and has no discoverable public JSON
route, so the BSE adapter degrades to an empty result unless explicitly enabled.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from ..core.errors import FetchError
from ..core.logging import get_logger
from ..core.retry import with_retry
from ..core.settings import Settings
from ..fetchers.http import fetch_bytes
from ..storage.raw import write_bronze
from .base import BronzeResult

log = get_logger("shareholding")


def _load_cfg(settings: Settings, source: str) -> dict:
    with (settings.project_root / "config" / "sources" / f"{source}.yaml").open(
        "r", encoding="utf-8"
    ) as f:
        return yaml.safe_load(f)


@dataclass
class ShpResult:
    bronze: BronzeResult | None
    records: list[dict] = field(default_factory=list)
    xbrl: dict[str, str] = field(default_factory=dict)  # symbol -> xbrl text


class NseShareholdingAdapter:
    name = "nse"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cfg = _load_cfg(settings, "nse")
        self.ep = self.cfg["endpoints"]["shareholding_master"]
        self.warmup = list(self.ep.get("warmup_urls", []))

    def fetch_master(self, *, partition: date) -> ShpResult:
        url = self.ep["url"]
        started = datetime.now(timezone.utc)
        log.info("nse.shp.master_start", url=url)

        def _do() -> bytes:
            return fetch_bytes(url, self.settings.http, warmup_urls=self.warmup)

        payload = with_retry(_do, cfg=self.settings.retry)
        try:
            records = json.loads(payload)
        except json.JSONDecodeError as e:
            raise FetchError(f"NSE shareholding master: invalid JSON ({e})") from e
        records = records if isinstance(records, list) else []

        path, run_id = write_bronze(
            self.settings, source=self.name, artifact=self.ep["artifact"],
            partition=partition, payload=payload, suffix=self.ep["suffix"],
            started_at=started, rows=len(records),
        )
        log.info("nse.shp.master_ok", records=len(records), path=str(path))
        return ShpResult(
            bronze=BronzeResult(self.name, self.ep["artifact"], partition, path, run_id),
            records=records,
        )

    def fetch_xbrl(self, url: str) -> str | None:
        """Fetch one SHP XBRL document (archives are static — no cookie warmup)."""
        try:
            return with_retry(
                lambda: fetch_bytes(url, self.settings.http), cfg=self.settings.retry
            ).decode("utf-8", "replace")
        except FetchError as e:
            log.warning("nse.shp.xbrl_fail", url=url, err=str(e))
            return None


class BseShareholdingAdapter:
    name = "bse"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cfg = _load_cfg(settings, "bse")
        self.ep = self.cfg["endpoints"].get("shareholding", {})

    def fetch(self, *, partition: date) -> ShpResult:
        if not self.ep.get("enabled"):
            log.warning(
                "bse.shp.disabled",
                detail="BSE shareholding endpoint not configured; contributing 0 rows",
            )
            return ShpResult(bronze=None, records=[])
        # Reserved for a confirmed per-scrip endpoint; left unimplemented by design.
        log.warning("bse.shp.not_implemented")
        return ShpResult(bronze=None, records=[])
