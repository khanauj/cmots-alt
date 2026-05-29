"""AMFI source adapter — fetches NAVAll.txt (daily, all schemes + NAVs)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from ..core.logging import get_logger
from ..core.retry import with_retry
from ..core.settings import Settings
from ..fetchers.http import fetch_text
from ..storage.raw import write_bronze
from .base import BronzeResult, SourceAdapter

log = get_logger("amfi")


class AmfiAdapter(SourceAdapter):
    name = "amfi"

    def __init__(self, settings: Settings, config_path: Path | None = None) -> None:
        super().__init__(settings)
        cfg_file = config_path or (settings.project_root / "config" / "sources" / "amfi.yaml")
        with cfg_file.open("r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def fetch(self, *, partition: date, **_: object) -> BronzeResult:
        ep = self.config["endpoints"]["navall"]
        url = ep["url"]
        encoding = ep.get("encoding", "utf-8")
        suffix = ep.get("suffix", "txt")
        artifact = ep.get("artifact", "navall")

        started_at = datetime.now(timezone.utc)
        log.info("amfi.fetch.start", url=url, partition=partition.isoformat())

        text: str = with_retry(
            lambda: fetch_text(url, self.settings.http, encoding=encoding),
            cfg=self.settings.retry,
        )

        # Count semicolon-delimited data lines as a quick rows hint.
        rows_hint = sum(1 for line in text.splitlines() if line.count(";") >= 5)

        path, run_id = write_bronze(
            self.settings,
            source=self.name,
            artifact=artifact,
            partition=partition,
            payload=text.encode(encoding),
            suffix=suffix,
            started_at=started_at,
            rows=rows_hint,
        )
        log.info(
            "amfi.fetch.ok",
            url=url,
            bytes=len(text.encode(encoding)),
            rows_hint=rows_hint,
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
