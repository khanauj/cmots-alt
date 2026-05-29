"""AMC Portfolio source adapter — fetches raw SBI Mutual Fund monthly portfolios.

Downloads Excel portfolio spreadsheets for SBI Mutual Fund schemes.
"""

from __future__ import annotations

import datetime
import json
import random
import re
import time
import uuid
from datetime import date, datetime as dt, timezone
from pathlib import Path

from ..core.logging import get_logger
from ..core.settings import Settings
from ..fetchers.http import chrome_session
from .base import BronzeResult, SourceAdapter

log = get_logger("amc_portfolio")

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

MAJOR_FUNDS = [
    ("sbi-infrastructure-fund", "SBI Infrastructure Fund", 85),
    ("sbi-low-duration-fund", "SBI Low Duration Fund (Formerly known as SBI Magnum Low Duration Fund)", 88),
    ("sbi-short-term-debt-fund", "SBI Short Term Debt Fund", 89),
    ("sbi-gold-etf", "SBI Gold ETF", 131),
    ("sbi-corporate-bond-fund", "SBI Corporate Bond Fund", 518),
    ("sbi-liquid-fund", "SBI Liquid Fund", 19),
    ("sbi-bluechip-fund", "SBI Large Cap Fund (Formerly known as SBI Bluechip Fund)", 43),
    ("sbi-contra-fund", "SBI Contra Fund", 12),
    ("sbi-large-midcap-fund", "SBI Large & Midcap Fund", 2),
    ("sbi-arbitrage-opportunities-fund", "SBI Arbitrage Opportunities Fund", 54),
    ("sbi-equity-hybrid-fund", "SBI Equity Hybrid Fund", 5),
    ("sbi-nifty-50-etf", "SBI Nifty 50 ETF", 433),
    ("sbi-s-p-bse-sensex-etf", "SBI BSE SENSEX ETF", 294),
    ("sbi-small-cap-fund", "SBI Small Cap Fund", 329),
]


def generate_session_id() -> str:
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(random.choice(chars) for _ in range(30))


class AmcPortfolioAdapter(SourceAdapter):
    name = "amc_portfolio"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)

    def fetch(self, *, partition: date, **_: object) -> BronzeResult:
        """Fetch SBI Mutual Fund monthly portfolios."""
        started_at = dt.now(timezone.utc)
        log.info("amc_portfolio.fetch.start", partition=partition.isoformat())

        # Determine reporting month and year
        first_day_curr = partition.replace(day=1)
        prev_month_end = first_day_curr - datetime.timedelta(days=1)
        reporting_year = str(prev_month_end.year)
        reporting_month = MONTH_NAMES[prev_month_end.month - 1]

        # Raw output folder: storage/raw/mf_holdings/<date>/sbi
        raw_dir = self.settings.resolve(
            Path(f"storage/raw/mf_holdings/{partition.isoformat()}/sbi")
        )
        raw_dir.mkdir(parents=True, exist_ok=True)

        manifest_data = {
            "partition": partition.isoformat(),
            "amc": "SBI Mutual Fund",
            "source": "SBI",
            "amfi_filter": "SBI",
            "reporting_year": reporting_year,
            "reporting_month": reporting_month,
            "fetched_at": started_at.isoformat(),
            "files": [],
        }

        downloaded_count = 0
        with chrome_session(self.settings.http) as sess:
            # Step 1: Token/API Discovery Flow (Primary)
            funds_to_download = []
            try:
                log.info("amc_portfolio.api_discovery.start")
                # Generate token
                req_uuid = str(uuid.uuid4())
                session_id = generate_session_id()
                token_url = "https://www.sbimf.com/api/GenerateToken/Post/"
                r_token = sess.post(
                    token_url,
                    json={"Requestid": req_uuid, "SessionId": session_id},
                    timeout=30,
                )
                data_match = re.search(r"<Data[^>]*>(.*?)</Data>", r_token.text, re.DOTALL)
                if not data_match:
                    raise ValueError("No token data found in response XML")

                token_json = json.loads(data_match.group(1))
                token = token_json["CreateTokenResult"]["Data"]

                # Get schemes list
                schemes_url = (
                    "https://www.sbimf.com/api/SchemeListingAPI/GetSchemeDataByFundId/"
                )
                schemes_payload = {
                    "Requestid": str(uuid.uuid4()),
                    "SessionId": generate_session_id(),
                    "Data": json.dumps({"FundId": None, "SchemeCodes": []}),
                }
                headers = {
                    "Token": token,
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json, text/plain, */*",
                }
                r_schemes = sess.post(
                    schemes_url, json=schemes_payload, headers=headers, timeout=30
                )
                if r_schemes.text.strip().startswith("[") or r_schemes.text.strip().startswith("{"):
                    schemes_list = r_schemes.json()
                else:
                    s_data_match = re.search(
                        r"<Data[^>]*>(.*?)</Data>", r_schemes.text, re.DOTALL
                    )
                    if not s_data_match:
                        raise ValueError("No scheme data found in response XML")
                    schemes_list = json.loads(s_data_match.group(1))

                # Identify unique funds
                seen_fids = set()
                for item in schemes_list:
                    fid = item.get("FundId")
                    fname = item.get("FundName")
                    if fid and fid not in seen_fids:
                        seen_fids.add(fid)
                        funds_to_download.append((fid, fname))

                log.info(
                    "amc_portfolio.api_discovery.ok",
                    discovered_funds=len(funds_to_download),
                )
            except Exception as e:
                log.warning("amc_portfolio.api_discovery.failed", error=str(e))
                # Fallback: construct using MAJOR_FUNDS list
                funds_to_download = [
                    (fid, fname) for _, fname, fid in MAJOR_FUNDS
                ]
                log.info(
                    "amc_portfolio.api_discovery.fallback",
                    target_funds=len(funds_to_download),
                )

            # Step 2: Download Portfolio Sheets
            sheets_url = "https://www.sbimf.com/ajaxcall/CMS/GetSchemePortfolioSheets"
            for fid, fname in funds_to_download:
                # We only download the major funds to avoid hitting the website with 120+ requests in a single run
                # (Proving architecture > scale).
                is_major = any(fid == item[2] for item in MAJOR_FUNDS)
                if not is_major:
                    continue

                # Clean fund name to make a safe slug
                slug = re.sub(r"\(.*?\)", "", fname.lower())
                slug = re.sub(r"formerly known as", "", slug)
                slug = re.sub(r"[^a-z0-9\s]", "", slug)
                slug = "-".join(slug.split())

                download_url = None
                # Try getting URL from API
                try:
                    payload = {
                        "FundId": fid,
                        "PSYear": reporting_year,
                        "PSMonth": reporting_month,
                        "PSFrequency": "Monthly",
                    }
                    r_sheet = sess.post(sheets_url, json=payload, timeout=15)
                    xlsx_links = re.findall(
                        r'href="([^"]+\.xlsx[^"]*)"', r_sheet.text, re.I
                    )
                    if xlsx_links:
                        download_url = xlsx_links[0]
                        # Clean up entity encoding
                        download_url = download_url.replace("&amp;", "&")
                        log.info(
                            "amc_portfolio.resolved_download_url",
                            fid=fid,
                            url=download_url,
                        )
                except Exception as e:
                    log.warning(
                        "amc_portfolio.api_resolved_url.failed",
                        fid=fid,
                        error=str(e),
                    )

                # Fallback: Construct deterministic URL
                if not download_url:
                    fallback_slug = slug
                    # Special overrides for fallback slugs if needed
                    if fid == 88:
                        fallback_slug = "sbi-low-duration-fund"
                    elif fid == 19:
                        fallback_slug = "sbi-liquid-fund"

                    download_url = (
                        f"https://www.sbimf.com/docs/default-source/scheme-portfolios/"
                        f"{fallback_slug}-monthly-portfolio---"
                        f"{reporting_month.lower()}-{reporting_year}.xlsx"
                    )
                    log.info(
                        "amc_portfolio.fallback_url_constructed",
                        fid=fid,
                        url=download_url,
                    )

                # Attempt download
                try:
                    r_dl = sess.get(download_url, timeout=30)
                    if r_dl.status_code == 200 and len(r_dl.content) > 5000:
                        file_path = raw_dir / f"{slug}.xlsx"
                        file_path.write_bytes(r_dl.content)
                        log.info(
                            "amc_portfolio.download.ok",
                            fid=fid,
                            path=str(file_path),
                        )
                        manifest_data["files"].append(
                            {
                                "fund_id": fid,
                                "fund_name": fname,
                                "file_name": f"{slug}.xlsx",
                                "source_url": download_url,
                                "download_status": "success",
                            }
                        )
                        downloaded_count += 1
                    else:
                        log.warning(
                            "amc_portfolio.download.invalid_response",
                            fid=fid,
                            status=r_dl.status_code,
                            length=len(r_dl.content),
                        )
                except Exception as e:
                    log.warning(
                        "amc_portfolio.download.failed", fid=fid, error=str(e)
                    )

        # Write manifest.json
        manifest_path = raw_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
        log.info(
            "amc_portfolio.manifest_written",
            path=str(manifest_path),
            downloaded=downloaded_count,
        )

        return BronzeResult(
            source=self.name,
            artifact="portfolios",
            partition=partition,
            path=raw_dir,
            run_id=started_at.strftime("%Y%m%d%H%M%S"),
            rows_hint=downloaded_count,
        )
