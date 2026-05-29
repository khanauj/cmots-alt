"""CLI entry point. `cmots ingest mf-nav` is the Phase 1 MVP command."""

from __future__ import annotations

from datetime import date as _date

import typer

from .core.logging import configure_logging
from .core.settings import ensure_directories, load_settings
from .pipelines import company_master as company_master_pipeline
from .pipelines import corporate_actions as corporate_actions_pipeline
from .pipelines import eod as eod_pipeline
from .pipelines import mf_holdings as mf_holdings_pipeline
from .pipelines import mf_nav as mf_nav_pipeline
from .pipelines import mf_scheme_master as mf_scheme_master_pipeline
from .pipelines import shareholding as shareholding_pipeline

app = typer.Typer(add_completion=False, no_args_is_help=True, help="cmots-alt CLI")
ingest = typer.Typer(no_args_is_help=True, help="Ingest a single domain end-to-end.")
app.add_typer(ingest, name="ingest")


@ingest.command("mf-nav")
def ingest_mf_nav(
    as_of: str | None = typer.Option(
        None,
        "--date",
        help="Partition date (YYYY-MM-DD). Defaults to today.",
    ),
) -> None:
    """AMFI NAVAll → silver/gold parquet → mf_nav_<date>.xlsx."""
    settings = load_settings()
    ensure_directories(settings)
    log = configure_logging(settings)

    partition = _date.fromisoformat(as_of) if as_of else _date.today()
    log.info("cli.ingest.mf_nav.invoked", partition=partition.isoformat())

    out = mf_nav_pipeline.run(as_of=partition, settings=settings)
    typer.echo(f"Wrote {out}")


@ingest.command("company-master")
def ingest_company_master(
    as_of: str | None = typer.Option(
        None,
        "--date",
        help="Partition date (YYYY-MM-DD). Defaults to today.",
    ),
) -> None:
    """NSE EQUITY_L + Industry + BSE scrips → CompanyMaster gold → xlsx."""
    settings = load_settings()
    ensure_directories(settings)
    log = configure_logging(settings)

    partition = _date.fromisoformat(as_of) if as_of else _date.today()
    log.info("cli.ingest.company_master.invoked", partition=partition.isoformat())

    out = company_master_pipeline.run(as_of=partition, settings=settings)
    typer.echo(f"Wrote {out}")


@ingest.command("equity-eod")
def ingest_equity_eod(
    as_of: str | None = typer.Option(
        None,
        "--date",
        help="Partition date (YYYY-MM-DD). Defaults to today; walks back to last trading day.",
    ),
) -> None:
    """NSE + BSE bhavcopy → Equity EOD gold (resolved to co_code) → xlsx."""
    settings = load_settings()
    ensure_directories(settings)
    log = configure_logging(settings)

    partition = _date.fromisoformat(as_of) if as_of else _date.today()
    log.info("cli.ingest.equity_eod.invoked", partition=partition.isoformat())

    out = eod_pipeline.run(as_of=partition, settings=settings)
    typer.echo(f"Wrote {out}")


@ingest.command("corporate-actions")
def ingest_corporate_actions(
    as_of: str | None = typer.Option(
        None,
        "--date",
        help="Partition date (YYYY-MM-DD). Defaults to today; events fetched over a trailing window.",
    ),
) -> None:
    """NSE CA API + BSE Corp.Action announcements → Corporate Actions gold → xlsx."""
    settings = load_settings()
    ensure_directories(settings)
    log = configure_logging(settings)

    partition = _date.fromisoformat(as_of) if as_of else _date.today()
    log.info("cli.ingest.corporate_actions.invoked", partition=partition.isoformat())

    out = corporate_actions_pipeline.run(as_of=partition, settings=settings)
    typer.echo(f"Wrote {out}")


@ingest.command("shareholding")
def ingest_shareholding(
    as_of: str | None = typer.Option(
        None, "--date", help="Partition date (YYYY-MM-DD). Defaults to today."
    ),
) -> None:
    """NSE shareholding master + XBRL detail → Shareholding gold → xlsx."""
    settings = load_settings()
    ensure_directories(settings)
    log = configure_logging(settings)

    partition = _date.fromisoformat(as_of) if as_of else _date.today()
    log.info("cli.ingest.shareholding.invoked", partition=partition.isoformat())

    out = shareholding_pipeline.run(as_of=partition, settings=settings)
    typer.echo(f"Wrote {out}")


@ingest.command("mf-scheme-master")
def ingest_mf_scheme_master(
    as_of: str | None = typer.Option(
        None, "--date", help="Partition date (YYYY-MM-DD). Defaults to today."
    ),
) -> None:
    """AMFI NAVAll → MF Scheme Master gold → mf_scheme_master_<date>.xlsx."""
    settings = load_settings()
    ensure_directories(settings)
    log = configure_logging(settings)

    partition = _date.fromisoformat(as_of) if as_of else _date.today()
    log.info("cli.ingest.mf_scheme_master.invoked", partition=partition.isoformat())

    out = mf_scheme_master_pipeline.run(as_of=partition, settings=settings)
    typer.echo(f"Wrote {out}")


@ingest.command("mf-holdings")
def ingest_mf_holdings(
    as_of: str | None = typer.Option(
        None, "--date", help="Partition date (YYYY-MM-DD). Defaults to today."
    ),
) -> None:
    """AMC monthly portfolios → MF Holdings gold → mf_holdings_<date>.xlsx."""
    settings = load_settings()
    ensure_directories(settings)
    log = configure_logging(settings)

    partition = _date.fromisoformat(as_of) if as_of else _date.today()
    log.info("cli.ingest.mf_holdings.invoked", partition=partition.isoformat())

    out = mf_holdings_pipeline.run(as_of=partition, settings=settings)
    typer.echo(f"Wrote {out}")


if __name__ == "__main__":  # pragma: no cover
    app()
