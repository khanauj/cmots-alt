"""Parse the Moneycontrol directory bronze HTML → (sector_slug, comp_slug, name)."""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

from ..core.errors import ParseError

# Bulk alphabetical table rows carry class="bl_12".
_BULK = re.compile(
    r'href="https://www\.moneycontrol\.com/india/stockpricequote/'
    r'([a-z0-9-]+)/([a-z0-9-]+)/([A-Z0-9]+)"\s+class="bl_12">([^<]+)<'
)


def parse_mc_directory(path: Path) -> pl.DataFrame:
    html = path.read_text(encoding="utf-8")
    rows = [
        (sector_slug, comp_slug, code, name.strip())
        for sector_slug, comp_slug, code, name in _BULK.findall(html)
    ]
    if not rows:
        raise ParseError("Moneycontrol directory produced 0 rows — markup may have changed")
    df = pl.DataFrame(
        rows, schema=["sector_slug", "comp_slug", "mc_code", "name"], orient="row"
    )
    return df.unique(subset=["comp_slug"], keep="first")
