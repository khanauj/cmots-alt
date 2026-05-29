"""MF Scheme Master validation: structural schema + uniqueness checks.

Phase 1 scaffold: pandera schema check + duplicate SchemeCode detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import polars as pl

from ..core.errors import ValidationError
from ..core.logging import get_logger

log = get_logger("validate.mf_scheme_master")


# ---------------------------------------------------------------------------
# Data contract enums
# ---------------------------------------------------------------------------

PLAN_TYPES = frozenset({"DIRECT", "REGULAR", "RETAIL", "INSTITUTIONAL", "UNKNOWN"})
OPTION_TYPES = frozenset({"GROWTH", "DIVIDEND", "IDCW", "REINVESTMENT", "BONUS", "OTHER", "UNKNOWN"})
STATUS_VALUES = frozenset({"Active", "Inactive"})


# ---------------------------------------------------------------------------
# Validation report
# ---------------------------------------------------------------------------

@dataclass
class ValidationReport:
    rows: int
    duplicate_scheme_code: int
    missing_scheme_name: int
    unknown_plan_type: int
    unknown_option_type: int
    warnings: list[str] = field(default_factory=list)

    @property
    def is_fatal(self) -> bool:
        return self.duplicate_scheme_code > 0 or self.missing_scheme_name > 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate(gold: pl.DataFrame) -> ValidationReport:
    """Run structural + uniqueness validation on the gold MF Scheme Master.

    Raises ``ValidationError`` if fatal issues are found (duplicate SchemeCode,
    missing SchemeName).
    """
    from .schemas import validate_mf_scheme_master_gold

    # 1. Structural pandera schema check.
    validate_mf_scheme_master_gold(gold)

    # 2. Uniqueness + completeness checks.
    total = gold.height
    dup_code = total - gold.select(pl.col("SchemeCode").n_unique()).item()
    missing_name = gold.filter(
        pl.col("SchemeName").is_null() | (pl.col("SchemeName").str.len_chars() == 0)
    ).height

    unknown_plan = gold.filter(pl.col("PlanType") == "UNKNOWN").height
    unknown_option = gold.filter(pl.col("OptionType") == "UNKNOWN").height

    # Calculate before counts (Step 3 simple logic) for comparison logging
    before_plan_unknown = gold.filter(
        ~pl.col("SchemeName").str.to_lowercase().str.contains(r"direct plan|\b(direct|dir)\b") &
        ~pl.col("SchemeName").str.to_lowercase().str.contains(r"regular plan|\b(regular|reg)\b") &
        ~pl.col("SchemeName").str.to_lowercase().str.contains(r"institutional|\b(institutional|inst)\b") &
        ~pl.col("SchemeName").str.to_lowercase().str.contains(r"\bretail\b")
    ).height

    before_option_unknown = gold.filter(
        ~pl.col("SchemeName").str.to_lowercase().str.contains(r"idcw|income distribution cum capital withdrawal|icdw") &
        ~pl.col("SchemeName").str.to_lowercase().str.contains(r"dividend|\bdiv(idends?)?\b") &
        ~pl.col("SchemeName").str.to_lowercase().str.contains(r"reinvestment|reinvest|reinv|\breinv\b") &
        ~pl.col("SchemeName").str.to_lowercase().str.contains(r"\bbonus\b") &
        ~pl.col("SchemeName").str.to_lowercase().str.contains(r"growth|\b(growth|gro)\b")
    ).height

    # Log distributions of PlanType, OptionType, Status, and ETF count
    def get_dist(col_name: str) -> dict[str, int]:
        try:
            res = gold.group_by(col_name).len().sort("len", descending=True)
            return {str(r[col_name]): int(r["len"]) for r in res.iter_rows(named=True)}
        except Exception:
            res = gold.group_by(col_name).count().sort("count", descending=True)
            return {str(r[col_name]): int(r["count"]) for r in res.iter_rows(named=True)}

    plan_dist = get_dist("PlanType")
    option_dist = get_dist("OptionType")
    status_dist = get_dist("Status")
    etf_count = gold.filter(pl.col("ETF")).height

    log.info(
        "validate.mf_scheme_master.unknown_reduction",
        plan_type_unknown_before=before_plan_unknown,
        plan_type_unknown_after=unknown_plan,
        option_type_unknown_before=before_option_unknown,
        option_type_unknown_after=unknown_option,
    )

    log.info(
        "validate.mf_scheme_master.distributions",
        plan_type_distribution=plan_dist,
        option_type_distribution=option_dist,
        status_distribution=status_dist,
        etf_count=etf_count,
    )

    report = ValidationReport(
        rows=total,
        duplicate_scheme_code=dup_code,
        missing_scheme_name=missing_name,
        unknown_plan_type=unknown_plan,
        unknown_option_type=unknown_option,
    )

    if unknown_plan > 0:
        report.warnings.append(
            f"{unknown_plan} rows ({100*unknown_plan/total:.1f}%) have PlanType=UNKNOWN"
        )
    if unknown_option > 0:
        report.warnings.append(
            f"{unknown_option} rows ({100*unknown_option/total:.1f}%) have OptionType=UNKNOWN"
        )

    log.info(
        "validate.mf_scheme_master",
        rows=report.rows,
        dup_scheme_code=report.duplicate_scheme_code,
        missing_name=report.missing_scheme_name,
        unknown_plan=report.unknown_plan_type,
        unknown_option=report.unknown_option_type,
    )

    if report.is_fatal:
        raise ValidationError(
            "MFSchemeMaster validation failed: "
            f"dup_scheme_code={report.duplicate_scheme_code}, "
            f"missing_name={report.missing_scheme_name}"
        )
    return report
