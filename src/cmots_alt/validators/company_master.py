"""CompanyMaster validation: structural schema + uniqueness + missing-ISIN report."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandera.polars as pa
import polars as pl

from ..core.errors import ValidationError
from ..core.logging import get_logger

log = get_logger("validate.company_master")


COMPANY_MASTER_GOLD = pa.DataFrameSchema(
    {
        "co_code": pa.Column(int, nullable=False),
        "BSECode": pa.Column(int, nullable=True),
        "NSESymbol": pa.Column(str, nullable=True),
        "CompanyName": pa.Column(str, nullable=True),
        "CompanyShortName": pa.Column(str, nullable=True),
        "CategoryName": pa.Column(str, nullable=False),
        "isin": pa.Column(str, nullable=False),
        "BSEGroup": pa.Column(str, nullable=True),
        "mcaptype": pa.Column(str, nullable=True),
        "SectorCode": pa.Column(int, nullable=True),
        "SectorName": pa.Column(str, nullable=True),
        "SectorConfidence": pa.Column(
            str, nullable=False,
            checks=pa.Check.isin(["HIGH", "MEDIUM", "LOW", "UNKNOWN"]),
        ),
        "BSEListed": pa.Column(str, nullable=False),
        "NSEListed": pa.Column(str, nullable=False),
    },
    strict=True,
    coerce=False,
)


@dataclass
class ValidationReport:
    rows: int
    duplicate_isin: int
    duplicate_co_code: int
    duplicate_bse_code: int
    duplicate_nse_symbol: int
    missing_isin: int
    unmapped_sector: int
    invalid_isin_format: int
    warnings: list[str] = field(default_factory=list)

    @property
    def is_fatal(self) -> bool:
        return (
            self.duplicate_isin > 0
            or self.duplicate_co_code > 0
            or self.duplicate_bse_code > 0
            or self.duplicate_nse_symbol > 0
            or self.missing_isin > 0
        )


def _dup_count(df: pl.DataFrame, col: str) -> int:
    sub = df.filter(pl.col(col).is_not_null())
    return sub.height - sub.select(pl.col(col).n_unique()).item()


def validate(df: pl.DataFrame) -> ValidationReport:
    # 1. Structural schema (fail-loud on shape/type drift).
    COMPANY_MASTER_GOLD.validate(df, lazy=True)

    # 2. Uniqueness + completeness checks.
    missing_isin = df.filter(
        pl.col("isin").is_null() | (pl.col("isin").str.len_chars() != 12)
    ).height
    invalid_fmt = df.filter(
        pl.col("isin").is_not_null()
        & ~pl.col("isin").str.contains(r"^IN[A-Z0-9]{10}$")
    ).height
    unmapped_sector = df.filter(pl.col("SectorCode").is_null()).height

    report = ValidationReport(
        rows=df.height,
        duplicate_isin=_dup_count(df, "isin"),
        duplicate_co_code=_dup_count(df, "co_code"),
        duplicate_bse_code=_dup_count(df, "BSECode"),
        duplicate_nse_symbol=_dup_count(df, "NSESymbol"),
        missing_isin=missing_isin,
        unmapped_sector=unmapped_sector,
        invalid_isin_format=invalid_fmt,
    )

    if report.unmapped_sector:
        report.warnings.append(
            f"{report.unmapped_sector} rows have no sector mapping (null SectorCode)"
        )
    if report.invalid_isin_format:
        report.warnings.append(
            f"{report.invalid_isin_format} rows have non-standard ISIN format"
        )

    log.info(
        "validate.company_master",
        rows=report.rows,
        dup_isin=report.duplicate_isin,
        dup_co_code=report.duplicate_co_code,
        dup_bse=report.duplicate_bse_code,
        dup_nse=report.duplicate_nse_symbol,
        missing_isin=report.missing_isin,
        unmapped_sector=report.unmapped_sector,
    )

    if report.is_fatal:
        raise ValidationError(
            "CompanyMaster validation failed: "
            f"dup_isin={report.duplicate_isin}, dup_co_code={report.duplicate_co_code}, "
            f"dup_bse={report.duplicate_bse_code}, dup_nse={report.duplicate_nse_symbol}, "
            f"missing_isin={report.missing_isin}"
        )
    return report
