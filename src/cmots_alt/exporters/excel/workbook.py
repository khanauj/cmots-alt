"""Excel writer. Uses xlsxwriter via Polars' write_excel for tight format control."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import xlsxwriter


def write_mf_nav_workbook(gold: pl.DataFrame, out_path: Path) -> Path:
    """Write a single-sheet xlsx for MF NAV.

    Date column rendered as DD-MM-YYYY (CMOTS-style); NAV as 4-decimal float;
    auto-fit column widths; frozen header row.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    gold.write_excel(
        workbook=out_path,
        worksheet="6_MFNAV",
        header_format={"bold": True, "bg_color": "#1F4E78", "font_color": "white"},
        column_formats={
            "NAV": "#,##0.0000",
            "NAVDate": "dd-mm-yyyy",
            "SchemeCode": "0",
        },
        autofit=True,
        freeze_panes=(1, 0),
        include_header=True,
    )
    return out_path


def write_company_master_workbook(gold: pl.DataFrame, out_path: Path) -> Path:
    """Write the CompanyMaster sheet (1_CompanyMaster)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gold.write_excel(
        workbook=out_path,
        worksheet="1_CompanyMaster",
        header_format={"bold": True, "bg_color": "#1F4E78", "font_color": "white"},
        column_formats={
            "co_code": "0",
            "BSECode": "0",
            "SectorCode": "0",
        },
        autofit=True,
        freeze_panes=(1, 0),
        include_header=True,
    )
    return out_path


_HDR = {"bold": True, "bg_color": "#1F4E78", "font_color": "white"}


def write_resolver_report_workbook(merged: pl.DataFrame, report, out_path: Path) -> Path:
    """Diagnostics workbook: coverage summary + resolution-reason / instrument-type
    breakdowns + the full resolved and unresolved row lists."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    summary = pl.DataFrame({
        "Metric": [
            "Total rows", "Resolved (co_code)", "Overall coverage %",
            "EQUITY rows", "EQUITY resolved", "EQUITY coverage %",
            "Duplicate (co_code,TradeDate,Exchange)", "Unresolved rows",
        ],
        "Value": [
            str(report.rows), str(report.resolved), f"{report.coverage_pct}%",
            str(report.equity_rows), str(report.equity_resolved), f"{report.equity_coverage_pct}%",
            str(report.duplicate_key), str(report.missing_co_code),
        ],
    })

    by_reason = (
        merged.group_by("resolution_reason").len()
        .rename({"len": "rows"}).sort("rows", descending=True)
    )
    by_instrument = (
        merged.group_by("instrument_type")
        .agg(
            pl.len().alias("rows"),
            pl.col("co_code").is_not_null().sum().alias("resolved"),
        )
        .with_columns(
            (100 * pl.col("resolved") / pl.col("rows")).round(1).alias("coverage_pct")
        )
        .sort("rows", descending=True)
    )

    cols = [
        "co_code", "isin", "nse_symbol", "bse_code", "instrument_name",
        "series", "exchange", "instrument_type", "resolution_reason", "resolution_confidence",
    ]
    resolved = merged.filter(pl.col("co_code").is_not_null()).select(cols)
    unresolved = merged.filter(pl.col("co_code").is_null()).select(cols)

    wb = xlsxwriter.Workbook(str(out_path))
    for frame, sheet, fmts in [
        (summary, "Summary", None),
        (by_reason, "ByReason", None),
        (by_instrument, "ByInstrument", {"coverage_pct": "0.0"}),
        (resolved, "Resolved", {"resolution_confidence": "0.000"}),
        (unresolved, "Unresolved", {"resolution_confidence": "0.000"}),
    ]:
        frame.write_excel(
            workbook=wb, worksheet=sheet, header_format=_HDR,
            column_formats=fmts or {}, autofit=True, freeze_panes=(1, 0),
            include_header=True,
        )
    wb.close()
    return out_path


def write_shareholding_workbook(gold: pl.DataFrame, out_path: Path) -> Path:
    """Write the Shareholding sheet (4_Shareholding)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pct = "#,##0.00"
    gold.write_excel(
        workbook=out_path,
        worksheet="4_Shareholding",
        header_format=_HDR,
        column_formats={
            "co_code": "0", "BSECode": "0", "QuarterEnd": "dd-mm-yyyy",
            "PromoterPct": pct, "PromoterGroupPct": pct, "PublicPct": pct,
            "DIIPct": pct, "FIIPct": pct, "GovtPct": pct,
            "NonInstitutionPct": pct, "InstitutionPct": pct, "PledgedPct": pct,
            "NumberOfShareholders": "#,##0",
        },
        autofit=True,
        freeze_panes=(1, 0),
        include_header=True,
    )
    return out_path


def write_corporate_actions_workbook(gold: pl.DataFrame, out_path: Path) -> Path:
    """Write the Corporate Actions sheet (3_CorporateActions)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gold.write_excel(
        workbook=out_path,
        worksheet="3_CorporateActions",
        header_format=_HDR,
        column_formats={
            "co_code": "0",
            "BSECode": "0",
            "AnnouncementDate": "dd-mm-yyyy",
            "ExDate": "dd-mm-yyyy",
            "RecordDate": "dd-mm-yyyy",
            "EffectiveDate": "dd-mm-yyyy",
            "OldFaceValue": "#,##0.00",
            "NewFaceValue": "#,##0.00",
            "RatioNumerator": "#,##0.####",
            "RatioDenominator": "#,##0.####",
        },
        autofit=True,
        freeze_panes=(1, 0),
        include_header=True,
    )
    return out_path


def write_equity_eod_workbook(gold: pl.DataFrame, out_path: Path) -> Path:
    """Write the Equity EOD sheet (2_EquityEOD)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    price = "#,##0.00"
    gold.write_excel(
        workbook=out_path,
        worksheet="2_EquityEOD",
        header_format={"bold": True, "bg_color": "#1F4E78", "font_color": "white"},
        column_formats={
            "co_code": "0",
            "BSECode": "0",
            "TradeDate": "dd-mm-yyyy",
            "Open": price, "High": price, "Low": price, "Close": price,
            "PrevClose": price, "LastPrice": price, "VWAP": price,
            "TotalVolume": "#,##0",
            "TotalTurnover": "#,##0.00",
            "DeliverableQty": "#,##0",
            "DeliverablePercent": "#,##0.00",
            "NoOfTrades": "#,##0",
        },
        autofit=True,
        freeze_panes=(1, 0),
        include_header=True,
    )
    return out_path


def write_mf_scheme_master_workbook(gold: pl.DataFrame, out_path: Path) -> Path:
    """Write the MF Scheme Master sheet (5_MFSchemeMaster)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gold.write_excel(
        workbook=out_path,
        worksheet="5_MFSchemeMaster",
        header_format=_HDR,
        column_formats={
            "SchemeCode": "0",
            "LaunchDate": "dd-mm-yyyy",
            "ClosureDate": "dd-mm-yyyy",
            "ExpenseRatio": "0.00%",
            "AUM": "#,##0.00",
        },
        autofit=True,
        freeze_panes=(1, 0),
        include_header=True,
    )
    return out_path


def write_mf_holdings_workbook(gold: pl.DataFrame, out_path: Path) -> Path:
    """Write the MF Holdings sheet (6_MFHoldings)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gold.write_excel(
        workbook=out_path,
        worksheet="6_MFHoldings",
        header_format=_HDR,
        column_formats={
            "SchemeCode": "0",
            "co_code": "0",
            "WeightPct": "0.00",
            "Quantity": "#,##0.00",
            "MarketValue": "#,##0.00",
            "QuarterEnd": "dd-mm-yyyy",
        },
        autofit=True,
        freeze_panes=(1, 0),
        include_header=True,
    )
    return out_path
