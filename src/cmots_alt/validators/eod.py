"""Equity EOD validation: structural schema, (co_code, TradeDate, Exchange)
uniqueness, missing-co_code report, and coverage.

Two coverage figures are reported:
  * overall  — resolved / all rows (includes ETFs/SME/debt that have no equity co_code)
  * equity   — resolved / rows classified InstrumentType == EQUITY (the headline
               resolver-coverage metric; the >95% target applies here)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandera.polars as pa
import polars as pl

from ..core.errors import ValidationError
from ..core.logging import get_logger

log = get_logger("validate.eod")

_INSTRUMENT_TYPES = ["EQUITY", "ETF", "SME", "PREF", "WARRANT", "RIGHTS", "UNKNOWN"]


EQUITY_EOD_GOLD = pa.DataFrameSchema(
    {
        "co_code": pa.Column(int, nullable=True),
        "BSECode": pa.Column(int, nullable=True),
        "NSESymbol": pa.Column(str, nullable=True),
        "isin": pa.Column(str, nullable=True),
        "TradeDate": pa.Column("date", nullable=False),
        "Open": pa.Column(float, nullable=True),
        "High": pa.Column(float, nullable=True),
        "Low": pa.Column(float, nullable=True),
        "Close": pa.Column(float, nullable=True),
        "PrevClose": pa.Column(float, nullable=True),
        "LastPrice": pa.Column(float, nullable=True),
        "VWAP": pa.Column(float, nullable=True),
        "TotalVolume": pa.Column(int, nullable=True),
        "TotalTurnover": pa.Column(float, nullable=True),
        "DeliverableQty": pa.Column(int, nullable=True),
        "DeliverablePercent": pa.Column(float, nullable=True),
        "NoOfTrades": pa.Column(int, nullable=True),
        "Series": pa.Column(str, nullable=True),
        "Exchange": pa.Column(str, nullable=False, checks=pa.Check.isin(["NSE", "BSE"])),
        "InstrumentType": pa.Column(str, nullable=False, checks=pa.Check.isin(_INSTRUMENT_TYPES)),
    },
    strict=True,
    coerce=False,
)


@dataclass
class EodValidationReport:
    rows: int
    resolved: int
    coverage_pct: float
    equity_rows: int
    equity_resolved: int
    equity_coverage_pct: float
    duplicate_key: int
    missing_co_code: int
    by_instrument: dict[str, int]
    by_type_resolved: dict[str, int]
    null_counts: dict[str, int]
    missing_sample: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_fatal(self) -> bool:
        return self.duplicate_key > 0


def validate(df: pl.DataFrame) -> EodValidationReport:
    EQUITY_EOD_GOLD.validate(df, lazy=True)

    rows = df.height
    resolved = df.filter(pl.col("co_code").is_not_null()).height
    coverage = 100 * resolved / rows if rows else 0.0

    equity = df.filter(pl.col("InstrumentType") == "EQUITY")
    eq_rows = equity.height
    eq_resolved = equity.filter(pl.col("co_code").is_not_null()).height
    eq_coverage = 100 * eq_resolved / eq_rows if eq_rows else 0.0

    # Uniqueness on (co_code, TradeDate, Exchange) — nulls excluded.
    keyed = df.filter(pl.col("co_code").is_not_null())
    distinct_keys = keyed.select("co_code", "TradeDate", "Exchange").unique().height
    duplicate_key = keyed.height - distinct_keys

    missing_sample = (
        df.filter(pl.col("co_code").is_null())
        .select(pl.coalesce("NSESymbol", pl.col("BSECode").cast(pl.Utf8), "isin"))
        .to_series().drop_nulls().head(15).to_list()
    )

    by_instrument = {r[0]: r[1] for r in df.group_by("InstrumentType").len().iter_rows()}
    by_type_resolved = {
        r[0]: r[1]
        for r in keyed.group_by("InstrumentType").len().iter_rows()
    }
    null_counts = {c: int(df.get_column(c).null_count()) for c in df.columns}

    report = EodValidationReport(
        rows=rows,
        resolved=resolved,
        coverage_pct=round(coverage, 1),
        equity_rows=eq_rows,
        equity_resolved=eq_resolved,
        equity_coverage_pct=round(eq_coverage, 1),
        duplicate_key=duplicate_key,
        missing_co_code=rows - resolved,
        by_instrument=by_instrument,
        by_type_resolved=by_type_resolved,
        null_counts=null_counts,
        missing_sample=missing_sample,
    )
    eq_unresolved = eq_rows - eq_resolved
    if eq_unresolved:
        report.warnings.append(f"{eq_unresolved} EQUITY rows did not resolve to a co_code")

    log.info(
        "validate.eod",
        rows=rows,
        resolved=resolved,
        coverage_pct=report.coverage_pct,
        equity_rows=eq_rows,
        equity_coverage_pct=report.equity_coverage_pct,
        duplicate_key=duplicate_key,
        by_instrument=by_instrument,
        missing_sample=missing_sample,
    )

    if report.is_fatal:
        raise ValidationError(
            f"Equity EOD validation failed: {duplicate_key} duplicate "
            "(co_code, TradeDate, Exchange) rows"
        )
    return report
