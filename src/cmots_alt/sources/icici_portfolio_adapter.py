"""ICICI Prudential portfolio adapter (thin).

ICICI publishes monthly portfolios as a ZIP of one-workbook-per-scheme files.
This adapter unpacks them into the SAME bronze layout the frozen MF-Holdings
parser already consumes (per-scheme .xlsx + manifest.json) — no parser changes.

The portfolio date ("Portfolio as on Apr 30,2026") sits in a header cell whose
label the frozen parser does not recognise, so the parser falls back to
manifest["partition"]. We therefore set the manifest partition to the actual
portfolio month-end read from a workbook, keeping QuarterEnd correct WITHOUT
touching parser logic.
"""

from __future__ import annotations

import json
import re
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import openpyxl

from ..core.logging import get_logger
from ..core.settings import Settings
from .base import BronzeResult, SourceAdapter

log = get_logger("icici_portfolio")


def _read_portfolio_date(xlsx_path: Path) -> date | None:
    wb = openpyxl.load_workbook(str(xlsx_path), data_only=True, read_only=True)
    ws = wb.active
    for row in ws.iter_rows(min_row=1, max_row=6, values_only=True):
        for cell in row:
            if cell and "portfolio as on" in str(cell).lower():
                m = re.search(r"([A-Za-z]{3,9}\s+\d{1,2}\s*,\s*\d{4})", str(cell))
                if m:
                    for fmt in ("%b %d,%Y", "%B %d,%Y", "%b %d, %Y", "%B %d, %Y"):
                        try:
                            return datetime.strptime(re.sub(r"\s*,\s*", ",", m.group(1)), fmt).date()
                        except ValueError:
                            continue
    return None


class IciciPortfolioAdapter(SourceAdapter):
    name = "icici_portfolio"

    def __init__(self, settings: Settings, zip_path: Path | None = None) -> None:
        super().__init__(settings)
        self.zip_path = zip_path

    def fetch(self, *, partition: date, **_: object) -> BronzeResult:
        started = datetime.now(timezone.utc)
        raw_dir = self.settings.resolve(
            Path(f"storage/raw/mf_holdings/{partition.isoformat()}/icici")
        )
        raw_dir.mkdir(parents=True, exist_ok=True)

        # Unpack the ZIP if provided; otherwise use files already present.
        if self.zip_path and self.zip_path.exists():
            with zipfile.ZipFile(self.zip_path) as z:
                for n in z.namelist():
                    fn = Path(n).name
                    if fn.lower().endswith((".xls", ".xlsx")):
                        (raw_dir / fn).write_bytes(z.read(n))

        files = sorted(p for p in raw_dir.iterdir() if p.suffix.lower() in (".xls", ".xlsx"))
        if not files:
            raise FileNotFoundError(f"ICICI: no workbooks in {raw_dir}")

        portfolio_date = _read_portfolio_date(files[0]) or partition
        manifest = {
            "partition": portfolio_date.isoformat(),  # parser uses this for QuarterEnd
            "run_partition": partition.isoformat(),
            "amc": "ICICI Prudential Mutual Fund",
            "source": "ICICI",
            "amfi_filter": "ICICI Prudential",
            "reporting_month": portfolio_date.strftime("%B"),
            "reporting_year": str(portfolio_date.year),
            "fetched_at": started.isoformat(),
            "files": [
                {
                    "fund_id": None,
                    "fund_name": f.stem,            # scheme name == file name
                    "file_name": f.name,
                    "source_url": str(self.zip_path) if self.zip_path else "local-zip",
                    "download_status": "success",
                }
                for f in files
            ],
        }
        (raw_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        log.info(
            "icici_portfolio.manifest_written",
            path=str(raw_dir), workbooks=len(files), portfolio_date=portfolio_date.isoformat(),
        )
        return BronzeResult(
            source=self.name, artifact="portfolios", partition=partition,
            path=raw_dir, run_id=started.strftime("%Y%m%d%H%M%S"), rows_hint=len(files),
        )
