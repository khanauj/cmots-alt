"""Structured logging. JSON to file, friendly to console."""

from __future__ import annotations

import logging
import sys
from datetime import date
from pathlib import Path

import structlog

from .settings import Settings


def configure_logging(settings: Settings) -> structlog.BoundLogger:
    log_dir = settings.resolve(settings.paths.logs)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"cmots-alt.{date.today().isoformat()}.jsonl"

    handlers: list[logging.Handler] = []
    if settings.logging.console:
        handlers.append(logging.StreamHandler(sys.stderr))
    if settings.logging.file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, settings.logging.level.upper()),
        handlers=handlers,
        format="%(message)s",
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.logging.level.upper())
        ),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger("cmots_alt")


def get_logger(name: str = "cmots_alt") -> structlog.BoundLogger:
    return structlog.get_logger(name)


__all__ = ["configure_logging", "get_logger", "Path"]
