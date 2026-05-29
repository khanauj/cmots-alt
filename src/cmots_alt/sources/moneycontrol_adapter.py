"""Moneycontrol source adapter — A-Z stock directory crawl for sector data.

26 alphabetical pages, each listing companies as
/india/stockpricequote/<sector-slug>/<company-slug>/<mc-code>. Pages are
concatenated and written to one bronze artifact per run.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from ..core.errors import FetchError
from ..core.logging import get_logger
from ..core.retry import with_retry
from ..core.settings import Settings
from ..fetchers.http import fetch_text
from ..storage.raw import write_bronze
from .base import BronzeResult, SourceAdapter

log = get_logger("moneycontrol")

_SEP = "\n<!-- ===CMOTS_ALT_PAGE_BREAK letter={letter} === -->\n"


class MoneycontrolAdapter(SourceAdapter):
    name = "moneycontrol"

    def __init__(self, settings: Settings, config_path: Path | None = None) -> None:
        super().__init__(settings)
        cfg_file = config_path or (
            settings.project_root / "config" / "sources" / "moneycontrol.yaml"
        )
        with cfg_file.open("r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def fetch(self, *, partition: date, **_: object) -> BronzeResult:  # type: ignore[override]
        d = self.config["directory"]
        template = d["url_template"]
        letters = d["letters"]
        throttle = float(d.get("throttle_seconds", 0.25))
        started_at = datetime.now(timezone.utc)

        log.info("mc.fetch.start", pages=len(letters))
        chunks: list[str] = []
        ok_pages = 0
        for letter in letters:
            url = template.format(letter=letter)

            def _do() -> str:
                return fetch_text(url, self.settings.http)

            try:
                html = with_retry(_do, cfg=self.settings.retry)
                chunks.append(_SEP.format(letter=letter))
                chunks.append(html)
                ok_pages += 1
            except FetchError as e:
                log.warning("mc.fetch.page_fail", letter=letter, err=str(e))
            time.sleep(throttle)

        if ok_pages == 0:
            raise FetchError("Moneycontrol: all directory pages failed")

        payload = "".join(chunks).encode("utf-8")
        path, run_id = write_bronze(
            self.settings,
            source=self.name,
            artifact=d["artifact"],
            partition=partition,
            payload=payload,
            suffix=d.get("suffix", "html"),
            started_at=started_at,
            rows=ok_pages,
        )
        log.info("mc.fetch.ok", ok_pages=ok_pages, bytes=len(payload), path=str(path))
        return BronzeResult(
            source=self.name,
            artifact=d["artifact"],
            partition=partition,
            path=path,
            run_id=run_id,
            rows_hint=ok_pages,
        )
