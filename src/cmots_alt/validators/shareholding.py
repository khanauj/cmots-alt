"""Shareholding validation: schema, 0-100 percentage bounds, component-consistency
checks, duplicate-quarter detection, missing-co_code report and a per-field null report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandera.polars as pa
import polars as pl

from ..core.errors import ValidationError
from ..core.logging import get_logger

log = get_logger("validate.shp")

_INSTRUMENT_TYPES = ["EQUITY", "ETF", "SME", "PREF", "WARRANT", "RIGHTS", "UNKNOWN"]
_PCT_COLS = [
    "PromoterPct", "PromoterGroupPct", "PublicPct", "DIIPct", "FIIPct",
    "GovtPct", "NonInstitutionPct", "InstitutionPct", "PledgedPct",
]
_PROMOTER_PUBLIC_TOL = 1.0
_COMPONENT_TOL = 2.0


SHAREHOLDING_GOLD = pa.DataFrameSchema(
    {
        "co_code": pa.Column(int, nullable=True),
        "BSECode": pa.Column(int, nullable=True),
        "NSESymbol": pa.Column(str, nullable=True),
        "isin": pa.Column(str, nullable=True),
        "QuarterEnd": pa.Column("date", nullable=True),
        "PromoterPct": pa.Column(float, nullable=True),
        "PromoterGroupPct": pa.Column(float, nullable=True),
        "PublicPct": pa.Column(float, nullable=True),
        "DIIPct": pa.Column(float, nullable=True),
        "FIIPct": pa.Column(float, nullable=True),
        "GovtPct": pa.Column(float, nullable=True),
        "NonInstitutionPct": pa.Column(float, nullable=True),
        "InstitutionPct": pa.Column(float, nullable=True),
        "PledgedPct": pa.Column(float, nullable=True),
        "NumberOfShareholders": pa.Column(int, nullable=True),
        "Exchange": pa.Column(str, nullable=False, checks=pa.Check.isin(["NSE", "BSE"])),
        "Source": pa.Column(str, nullable=False),
        "InstrumentType": pa.Column(str, nullable=False, checks=pa.Check.isin(_INSTRUMENT_TYPES)),
    },
    strict=True,
    coerce=False,
)


@dataclass
class ShpValidationReport:
    rows: int
    resolved: int
    coverage_pct: float
    xbrl_enriched: int
    duplicate_quarter: int
    missing_co_code: int
    pct_out_of_range: int
    promoter_public_inconsistent: int
    component_inconsistent: int
    quarters: dict[str, int]
    null_counts: dict[str, int]
    warnings: list[str] = field(default_factory=list)

    @property
    def is_fatal(self) -> bool:
        return self.duplicate_quarter > 0


def validate(df: pl.DataFrame) -> ShpValidationReport:
    SHAREHOLDING_GOLD.validate(df, lazy=True)

    rows = df.height
    resolved = df.filter(pl.col("co_code").is_not_null()).height
    coverage = 100 * resolved / rows if rows else 0.0
    xbrl_enriched = df.filter(pl.col("InstitutionPct").is_not_null()).height

    # Duplicate quarter on (co_code, QuarterEnd).
    keyed = df.filter(pl.col("co_code").is_not_null() & pl.col("QuarterEnd").is_not_null())
    distinct = keyed.select("co_code", "QuarterEnd").unique().height
    duplicate_quarter = keyed.height - distinct

    # Percentages outside [0, 100].
    out_of_range = df.filter(
        pl.any_horizontal(
            [(pl.col(c) < 0) | (pl.col(c) > 100) for c in _PCT_COLS]
        )
    ).height

    # Component consistency: promoter + public must not EXCEED 100 (a true
    # over-allocation error). A sum below 100 is legitimate — the remainder is
    # shares underlying DRs / employee-benefit trusts, not carried in this dataset.
    pp = df.filter(pl.col("PromoterPct").is_not_null() & pl.col("PublicPct").is_not_null())
    promoter_public_bad = pp.filter(
        (pl.col("PromoterPct") + pl.col("PublicPct")) - 100 > _PROMOTER_PUBLIC_TOL
    ).height

    # Component consistency: DII + FII + Govt + NonInstitution ≈ Public (where detailed).
    comp = df.filter(
        pl.col("PublicPct").is_not_null()
        & pl.col("DIIPct").is_not_null()
        & pl.col("NonInstitutionPct").is_not_null()
    )
    component_bad = comp.filter(
        (
            pl.col("DIIPct") + pl.col("FIIPct").fill_null(0)
            + pl.col("GovtPct").fill_null(0) + pl.col("NonInstitutionPct")
            - pl.col("PublicPct")
        ).abs() > _COMPONENT_TOL
    ).height

    quarters = {
        (r[0].isoformat() if r[0] else "null"): r[1]
        for r in df.group_by("QuarterEnd").len().sort("len", descending=True).iter_rows()
    }
    null_counts = {c: int(df.get_column(c).null_count()) for c in df.columns}

    report = ShpValidationReport(
        rows=rows, resolved=resolved, coverage_pct=round(coverage, 1),
        xbrl_enriched=xbrl_enriched, duplicate_quarter=duplicate_quarter,
        missing_co_code=rows - resolved, pct_out_of_range=out_of_range,
        promoter_public_inconsistent=promoter_public_bad,
        component_inconsistent=component_bad, quarters=quarters, null_counts=null_counts,
    )
    if report.missing_co_code:
        report.warnings.append(f"{report.missing_co_code} filings did not resolve to a co_code")
    if out_of_range:
        report.warnings.append(f"{out_of_range} rows have a percentage outside [0,100]")
    if promoter_public_bad:
        report.warnings.append(f"{promoter_public_bad} rows: promoter+public deviates from 100%")
    if component_bad:
        report.warnings.append(f"{component_bad} rows: public sub-components don't sum to public%")

    log.info(
        "validate.shp", rows=rows, resolved=resolved, coverage_pct=report.coverage_pct,
        xbrl_enriched=xbrl_enriched, duplicate_quarter=duplicate_quarter,
        pct_out_of_range=out_of_range, promoter_public_inconsistent=promoter_public_bad,
        component_inconsistent=component_bad, quarters=quarters,
    )

    if report.is_fatal:
        raise ValidationError(
            f"Shareholding validation failed: {duplicate_quarter} duplicate "
            "(co_code, QuarterEnd) rows"
        )
    return report
