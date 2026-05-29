"""Pipeline registry — the single source of truth the admin/scheduler routers use.

Maps the public pipeline name (as used in /admin/trigger/{pipeline}) to its gold
domain and the dotted path of its `run` callable. The callable is imported lazily
(only when actually triggered) so the API process starts without pulling in the
scraper/HTTP stack. Scaffold: triggering is not wired yet — see admin router TODO.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineSpec:
    name: str            # public name, used in the URL
    gold_domain: str     # storage/processed/gold/<gold_domain>
    run_path: str        # dotted path "module:function" of the pipeline entrypoint
    description: str


PIPELINES: dict[str, PipelineSpec] = {
    p.name: p
    for p in [
        PipelineSpec("company-master", "company_master",
                     "cmots_alt.pipelines.company_master:run",
                     "NSE/BSE company master with stable co_code, sector & mcap class."),
        PipelineSpec("equity-eod", "equity_eod",
                     "cmots_alt.pipelines.eod:run",
                     "NSE + BSE bhavcopy daily OHLC / VWAP / deliverables."),
        PipelineSpec("corporate-actions", "corporate_actions",
                     "cmots_alt.pipelines.corporate_actions:run",
                     "Dividends / bonus / split / rights / mergers / buyback / FV changes."),
        PipelineSpec("shareholding", "shareholding",
                     "cmots_alt.pipelines.shareholding:run",
                     "Quarterly promoter / public / DII / FII / pledged shareholding."),
        PipelineSpec("mf-scheme-master", "mf_scheme_master",
                     "cmots_alt.pipelines.mf_scheme_master:run",
                     "AMFI mutual-fund scheme master."),
        PipelineSpec("mf-nav", "mf_nav",
                     "cmots_alt.pipelines.mf_nav:run",
                     "AMFI daily mutual-fund NAVs."),
        PipelineSpec("mf-holdings", "mf_holdings",
                     "cmots_alt.pipelines.mf_holdings:run",
                     "Per-scheme mutual-fund portfolio holdings (generic AMC parser)."),
    ]
}


def list_pipelines() -> list[PipelineSpec]:
    return list(PIPELINES.values())


def get_pipeline(name: str) -> PipelineSpec | None:
    return PIPELINES.get(name)
