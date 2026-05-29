"""MF Scheme Master normalizer — scheme-name parsing utilities.

Extracts plan type, option type, ETF flag, and status from AMFI NAVAll
scheme names and metadata.  Silver input comes from the shared
``normalizers.mf_nav.parse_navall_file`` parser.

Phase 1: stub implementations returning UNKNOWN / defaults.
Full regex-based parsing will be added in Step 3.
"""

from __future__ import annotations

import polars as pl


# ---------------------------------------------------------------------------
# Allowed enum values (approved data contract)
# ---------------------------------------------------------------------------

PLAN_TYPES = {"DIRECT", "REGULAR", "RETAIL", "INSTITUTIONAL", "UNKNOWN"}
OPTION_TYPES = {"GROWTH", "DIVIDEND", "IDCW", "REINVESTMENT", "BONUS", "OTHER", "UNKNOWN"}
STATUS_VALUES = {"Active", "Inactive"}


# ---------------------------------------------------------------------------
# Extraction stubs — will be replaced with regex logic in Step 3
# ---------------------------------------------------------------------------

import re

# ---------------------------------------------------------------------------
# Allowed enum values (approved data contract)
# ---------------------------------------------------------------------------

PLAN_TYPES = {"DIRECT", "REGULAR", "RETAIL", "INSTITUTIONAL", "UNKNOWN"}
OPTION_TYPES = {"GROWTH", "DIVIDEND", "IDCW", "REINVESTMENT", "BONUS", "OTHER", "UNKNOWN"}
STATUS_VALUES = {"Active", "Inactive"}


# ---------------------------------------------------------------------------
# Extraction functions
# ---------------------------------------------------------------------------

def extract_plan_type(name: str) -> str:
    """Derive plan type from scheme name.

    Allowed: DIRECT | REGULAR | RETAIL | INSTITUTIONAL | UNKNOWN.
    Unknown is preferred over false classification.
    """
    if not name:
        return "UNKNOWN"
    name_lower = name.lower()
    
    # 1. DIRECT: "Direct Plan", "Dir", "Direct", "directplan"
    if "direct plan" in name_lower or "directplan" in name_lower or re.search(r"\b(direct|dir)\b", name_lower):
        return "DIRECT"
        
    # 2. Explicit Regular: "Regular Plan", "Reg", "Regular", "regularplan"
    if "regular plan" in name_lower or "regularplan" in name_lower or re.search(r"\b(regular|reg)\b", name_lower):
        return "REGULAR"
        
    # 3. Institutional: "Institutional", "Inst", "institution", "instn"
    if "institutional" in name_lower or "institution" in name_lower or "instn" in name_lower or re.search(r"\b(institutional|inst)\b", name_lower):
        return "INSTITUTIONAL"
        
    # 4. Retail: "Retail"
    if "retail" in name_lower or re.search(r"\bretail\b", name_lower):
        return "RETAIL"
        
    return "UNKNOWN"


def extract_option_type(name: str) -> str:
    """Derive option type from scheme name.

    Allowed: GROWTH | DIVIDEND | IDCW | REINVESTMENT | BONUS | OTHER | UNKNOWN.
    Dividend and IDCW are preserved as distinct values — no normalisation.
    """
    if not name:
        return "UNKNOWN"
    name_lower = name.lower()
    
    # 1. IDCW
    # keywords: IDCW, Income Distribution cum Capital Withdrawal, ICDW (typo)
    if "idcw" in name_lower or "income distribution cum capital withdrawal" in name_lower or "icdw" in name_lower:
        return "IDCW"
        
    # 2. Dividend
    # keywords: Dividend, Div, Div Payout, Payout, -D, -DP
    if (
        "dividend" in name_lower or
        "div payout" in name_lower or
        re.search(r"\b(div|payout)\b", name_lower) or
        re.search(r"\-\s*dp\b", name_lower) or
        re.search(r"\-\s*d\b", name_lower)
    ):
        return "DIVIDEND"
        
    # 3. Reinvestment
    # keywords: Reinvestment, Reinvest, Reinv
    if "reinvestment" in name_lower or "reinvest" in name_lower or "reinv" in name_lower or re.search(r"\breinv\b", name_lower):
        return "REINVESTMENT"
        
    # 4. Bonus
    # keyword: Bonus
    if "bonus" in name_lower or re.search(r"\bbonus\b", name_lower):
        return "BONUS"
        
    # 5. Growth
    # keywords: Growth, Growth Option, Gro, Gr, -G, Cumulative
    if (
        "growth" in name_lower or
        "cumulative" in name_lower or
        re.search(r"\b(growth|gro|gr)\b", name_lower) or
        re.search(r"\-\s*g\b", name_lower)
    ):
        return "GROWTH"
        
    return "UNKNOWN"


def detect_etf(name: str) -> bool:
    """Return True if the scheme is an ETF.

    Strict detection only: name must contain 'ETF' or 'Exchange Traded'
    (case-insensitive).
    """
    if not name:
        return False
    name_lower = name.lower()
    return "etf" in name_lower or "exchange traded" in name_lower


def derive_status(scheme_name: str, nav_date_str: str | None = None) -> str:
    """Derive scheme status.

    Default: Active.
    Only mark Inactive if explicit closure/merged/matured wording is detected
    in the scheme name, or a ClosureDate is present.
    """
    if not scheme_name:
        return "Active"
    name_lower = scheme_name.lower()
    
    if re.search(r"\b(closed?|closure|matur(ed|ity)|merg(ed|er)|defunct|discontinued)\b", name_lower):
        return "Inactive"
        
    return "Active"


# ---------------------------------------------------------------------------
# Batch application — Polars-native column derivation
# ---------------------------------------------------------------------------

def enrich_scheme_columns(silver: pl.DataFrame) -> pl.DataFrame:
    """Add derived columns to the silver DataFrame.

    Adds: plan_type, option_type, is_etf, status.
    """
    plan_type_expr = (
        pl.when(
            pl.col("scheme_name").str.to_lowercase().str.contains(r"direct plan|directplan|\b(direct|dir)\b")
        ).then(pl.lit("DIRECT"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(r"regular plan|regularplan|\b(regular|reg)\b")
        ).then(pl.lit("REGULAR"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(r"institutional|institution|instn|\b(institutional|inst)\b")
        ).then(pl.lit("INSTITUTIONAL"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(r"\bretail\b")
        ).then(pl.lit("RETAIL"))
        .otherwise(pl.lit("UNKNOWN"))
        .alias("plan_type")
    )

    option_type_expr = (
        pl.when(
            pl.col("scheme_name").str.to_lowercase().str.contains(
                r"idcw|income distribution cum capital withdrawal|icdw"
            )
        ).then(pl.lit("IDCW"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(
                r"dividend|div payout|\b(div|payout)\b|\-\s*dp\b|\-\s*d\b"
            )
        ).then(pl.lit("DIVIDEND"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(
                r"reinvestment|reinvest|reinv|\breinv\b"
            )
        ).then(pl.lit("REINVESTMENT"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(
                r"\bbonus\b"
            )
        ).then(pl.lit("BONUS"))
        .when(
            pl.col("scheme_name").str.to_lowercase().str.contains(
                r"growth|cumulative|\b(growth|gro|gr)\b|\-\s*g\b"
            )
        ).then(pl.lit("GROWTH"))
        .otherwise(pl.lit("UNKNOWN"))
        .alias("option_type")
    )

    is_etf_expr = (
        pl.col("scheme_name").str.to_lowercase().str.contains(
            r"etf|exchange traded"
        ).alias("is_etf")
    )

    status_expr = (
        pl.when(
            pl.col("scheme_name").str.to_lowercase().str.contains(
                r"\b(closed?|closure|matur(ed|ity)|merg(ed|er)|defunct|discontinued)\b"
            )
        ).then(pl.lit("Inactive")).otherwise(pl.lit("Active")).alias("status")
    )

    return silver.with_columns(
        plan_type_expr,
        option_type_expr,
        is_etf_expr,
        status_expr,
    )
