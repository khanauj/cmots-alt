"""MF Holdings validation: structural schema, deduplication, weights, missing ISINs, unresolved co_codes, and top holdings sanity check."""

from __future__ import annotations

from dataclasses import dataclass, field
import polars as pl

from ..core.errors import ValidationError
from ..core.logging import get_logger

log = get_logger("validate.mf_holdings")


@dataclass
class ValidationReport:
    rows: int
    duplicates: int
    missing_isins: int
    unresolved_cocodes: int
    warnings: list[str] = field(default_factory=list)

    @property
    def is_fatal(self) -> bool:
        return self.duplicates > 0


def validate(gold: pl.DataFrame) -> ValidationReport:
    """Run structural + uniqueness + reconciliation + reporting checks on the gold holdings."""
    from .schemas import validate_mf_holdings_gold

    total = gold.height
    if total == 0:
        log.info("validate.mf_holdings.empty_data", rows=0)
        return ValidationReport(
            rows=0, duplicates=0, missing_isins=0, unresolved_cocodes=0
        )

    # 1. Structural pandera schema check
    validate_mf_holdings_gold(gold)

    # 2. Deduplication check on the 5-key compound identifier
    dup_keys = [
        "SchemeCode",
        "HoldingISIN",
        "HoldingName",
        "QuarterEnd",
        "InstrumentType",
    ]
    # We treat nulls in HoldingISIN as unique strings to prevent null comparison issues
    unique_count = (
        gold.with_columns(pl.col("HoldingISIN").fill_null("NULL_PLACEHOLDER"))
        .select(dup_keys)
        .unique()
        .height
    )
    duplicates = total - unique_count

    # 3. Weight reconciliation (sum of WeightPct per SchemeCode should be 95-105%)
    scheme_weights = gold.group_by("SchemeCode", "SchemeName").agg(
        pl.col("WeightPct").sum().alias("total_weight")
    )
    out_of_bounds = scheme_weights.filter(
        (pl.col("total_weight") < 95.0) | (pl.col("total_weight") > 105.0)
    )

    warnings = []
    if out_of_bounds.height > 0:
        msg = f"{out_of_bounds.height} schemes have total holdings weight outside 95-105% (WARN only)"
        warnings.append(msg)
        log.warning(
            "validate.mf_holdings.weight_bounds_warning",
            detail=msg,
            sample=out_of_bounds.head(5).to_dicts(),
        )

    # 4. Missing ISIN report (for EQUITY and DEBT specifically)
    missing_isin_df = gold.filter(
        (pl.col("HoldingISIN").is_null() | (pl.col("HoldingISIN") == ""))
        & pl.col("InstrumentType").is_in(["EQUITY", "DEBT"])
    )
    missing_isins_count = missing_isin_df.height
    if missing_isins_count > 0:
        msg = f"{missing_isins_count} EQUITY/DEBT holdings are missing ISINs"
        warnings.append(msg)
        log.warning(
            "validate.mf_holdings.missing_isins_report",
            count=missing_isins_count,
            sample=missing_isin_df.select(
                ["SchemeName", "HoldingName", "InstrumentType"]
            )
            .head(10)
            .to_dicts(),
        )

    # 5. Unresolved co_code report (for EQUITY only)
    unresolved_co_df = gold.filter(
        pl.col("co_code").is_null() & (pl.col("InstrumentType") == "EQUITY")
    )
    unresolved_cocodes_count = unresolved_co_df.height
    if unresolved_cocodes_count > 0:
        msg = f"{unresolved_cocodes_count} EQUITY holdings could not be resolved to co_code"
        warnings.append(msg)
        log.warning(
            "validate.mf_holdings.unresolved_cocodes_report",
            count=unresolved_cocodes_count,
            sample=unresolved_co_df.select(["SchemeName", "HoldingName", "HoldingISIN"])
            .head(10)
            .to_dicts(),
        )

    # 6. Top 10 holdings sanity check for major schemes
    # Detect major schemes containing "infrastructure", "bluechip", "liquid", "corporate bond"
    major_keywords = ["infrastructure", "bluechip", "liquid", "corporate bond"]
    major_schemes = (
        gold.filter(
            pl.col("SchemeName").str.to_lowercase().str.contains(
                "|".join(major_keywords)
            )
        )
        .select("SchemeCode")
        .unique()
        .to_series()
        .to_list()
    )

    for sc in major_schemes[:5]:  # limit to first 5 major schemes to avoid log bloat
        sc_holdings = gold.filter(pl.col("SchemeCode") == sc).sort(
            "WeightPct", descending=True
        )
        sc_name = sc_holdings.item(0, "SchemeName")

        log.info(
            "validate.mf_holdings.top_holdings_sanity",
            scheme_code=sc,
            scheme_name=sc_name,
            total_holdings=sc_holdings.height,
        )

        top_10 = sc_holdings.head(10)
        # Log top 10 holdings
        for r in top_10.to_dicts():
            log.info(
                "validate.mf_holdings.sanity_item",
                name=r["HoldingName"],
                isin=r["HoldingISIN"],
                weight=r["WeightPct"],
                type=r["InstrumentType"],
                co_code=r["co_code"],
            )

        if sc_holdings.height < 10:
            msg = f"Major scheme {sc_name} has only {sc_holdings.height} holdings (expected >= 10)"
            warnings.append(msg)
            log.warning("validate.mf_holdings.sanity_failed_count", detail=msg)

        top_10_weight_sum = top_10.select(pl.col("WeightPct").sum()).item()
        if not (10.0 <= top_10_weight_sum <= 100.0):
            msg = (
                f"Major scheme {sc_name} top 10 weight sum is {top_10_weight_sum:.2f}% "
                f"(expected between 10.0% and 100.0%)"
            )
            warnings.append(msg)
            log.warning("validate.mf_holdings.sanity_failed_weight", detail=msg)

    report = ValidationReport(
        rows=total,
        duplicates=duplicates,
        missing_isins=missing_isins_count,
        unresolved_cocodes=unresolved_cocodes_count,
        warnings=warnings,
    )

    log.info(
        "validate.mf_holdings.summary",
        rows=report.rows,
        duplicates=report.duplicates,
        missing_isins=report.missing_isins,
        unresolved_cocodes=report.unresolved_cocodes,
        warnings_count=len(report.warnings),
    )

    if report.is_fatal:
        raise ValidationError(
            f"MFHoldings validation failed: duplicates={report.duplicates}"
        )

    return report
