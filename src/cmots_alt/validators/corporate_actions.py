"""Corporate-actions validation: schema, duplicate-event detection, missing-co_code
report, malformed-ratio detection, invalid-date detection and a per-field null report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandera.polars as pa
import polars as pl

from ..core.errors import ValidationError
from ..core.logging import get_logger
from ..normalizers.corporate_actions import ACTION_TYPES

log = get_logger("validate.ca")

_INSTRUMENT_TYPES = ["EQUITY", "ETF", "SME", "PREF", "WARRANT", "RIGHTS", "UNKNOWN"]
# Action types that must carry a ratio (and, for the face-value ones, old/new FV).
_RATIO_REQUIRED = {"BONUS", "SPLIT", "RIGHTS", "FV_CHANGE"}


CORPORATE_ACTIONS_GOLD = pa.DataFrameSchema(
    {
        "co_code": pa.Column(int, nullable=True),
        "BSECode": pa.Column(int, nullable=True),
        "NSESymbol": pa.Column(str, nullable=True),
        "isin": pa.Column(str, nullable=True),
        "ActionType": pa.Column(str, nullable=False, checks=pa.Check.isin(ACTION_TYPES)),
        "AnnouncementDate": pa.Column("date", nullable=True),
        "ExDate": pa.Column("date", nullable=True),
        "RecordDate": pa.Column("date", nullable=True),
        "EffectiveDate": pa.Column("date", nullable=True),
        "Description": pa.Column(str, nullable=True),
        "OldFaceValue": pa.Column(float, nullable=True),
        "NewFaceValue": pa.Column(float, nullable=True),
        "RatioNumerator": pa.Column(float, nullable=True),
        "RatioDenominator": pa.Column(float, nullable=True),
        "Exchange": pa.Column(str, nullable=False, checks=pa.Check.isin(["NSE", "BSE"])),
        "Source": pa.Column(str, nullable=False),
        "InstrumentType": pa.Column(str, nullable=False, checks=pa.Check.isin(_INSTRUMENT_TYPES)),
    },
    strict=True,
    coerce=False,
)


@dataclass
class CaValidationReport:
    rows: int
    resolved: int
    coverage_pct: float
    duplicate_events: int
    missing_co_code: int
    malformed_ratio: int
    invalid_dates: int
    by_action: dict[str, int]
    null_counts: dict[str, int]
    missing_sample: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_fatal(self) -> bool:
        return self.duplicate_events > 0


def validate(df: pl.DataFrame, as_of: date) -> CaValidationReport:
    CORPORATE_ACTIONS_GOLD.validate(df, lazy=True)

    rows = df.height
    resolved = df.filter(pl.col("co_code").is_not_null()).height
    coverage = 100 * resolved / rows if rows else 0.0

    # Duplicate events on (co_code, ActionType, ExDate) — only fully-keyed rows count.
    keyed = df.filter(pl.col("co_code").is_not_null() & pl.col("ExDate").is_not_null())
    distinct = keyed.select("co_code", "ActionType", "ExDate").unique().height
    duplicate_events = keyed.height - distinct

    # Malformed ratio: a *scheduled* ratio-bearing action (ExDate set) missing a usable
    # ratio. BSE board-intimation announcements (no ex-date yet) legitimately carry no
    # ratio, so they are not flagged.
    malformed = df.filter(
        pl.col("ActionType").is_in(list(_RATIO_REQUIRED))
        & pl.col("ExDate").is_not_null()
        & (
            pl.col("RatioNumerator").is_null()
            | pl.col("RatioDenominator").is_null()
            | (pl.col("RatioDenominator") == 0)
        )
    ).height

    # Invalid dates: out-of-range, or record date earlier than ex date.
    lo, hi = 1990, as_of.year + 2
    date_cols = ["AnnouncementDate", "ExDate", "RecordDate", "EffectiveDate"]
    out_of_range = pl.any_horizontal(
        [pl.col(c).dt.year().is_between(lo, hi).not_() & pl.col(c).is_not_null()
         for c in date_cols]
    )
    rec_before_ex = (
        pl.col("RecordDate").is_not_null()
        & pl.col("ExDate").is_not_null()
        & (pl.col("RecordDate") < pl.col("ExDate"))
    )
    invalid_dates = df.filter(out_of_range | rec_before_ex).height

    missing_sample = (
        df.filter(pl.col("co_code").is_null())
        .select(pl.coalesce("NSESymbol", pl.col("BSECode").cast(pl.Utf8), "isin"))
        .to_series().drop_nulls().head(15).to_list()
    )
    by_action = {r[0]: r[1] for r in df.group_by("ActionType").len().sort("len", descending=True).iter_rows()}
    null_counts = {c: int(df.get_column(c).null_count()) for c in df.columns}

    report = CaValidationReport(
        rows=rows, resolved=resolved, coverage_pct=round(coverage, 1),
        duplicate_events=duplicate_events, missing_co_code=rows - resolved,
        malformed_ratio=malformed, invalid_dates=invalid_dates,
        by_action=by_action, null_counts=null_counts, missing_sample=missing_sample,
    )
    if report.missing_co_code:
        report.warnings.append(f"{report.missing_co_code} events did not resolve to a co_code")
    if malformed:
        report.warnings.append(f"{malformed} ratio-bearing actions have a malformed/empty ratio")
    if invalid_dates:
        report.warnings.append(f"{invalid_dates} rows have implausible/inconsistent dates")

    log.info(
        "validate.ca", rows=rows, resolved=resolved, coverage_pct=report.coverage_pct,
        duplicate_events=duplicate_events, malformed_ratio=malformed,
        invalid_dates=invalid_dates, by_action=by_action, missing_sample=missing_sample,
    )

    if report.is_fatal:
        raise ValidationError(
            f"Corporate actions validation failed: {duplicate_events} duplicate "
            "(co_code, ActionType, ExDate) events"
        )
    return report
