"""Retry policy wrapper around tenacity."""

from __future__ import annotations

from typing import Callable, TypeVar

from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .errors import FetchError
from .settings import RetryConfig

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    cfg: RetryConfig,
    exceptions: tuple[type[BaseException], ...] = (FetchError, ConnectionError, TimeoutError),
) -> T:
    """Execute fn() with the configured retry policy."""
    retrying = Retrying(
        stop=stop_after_attempt(cfg.attempts),
        wait=wait_exponential_jitter(
            initial=cfg.initial_wait_seconds,
            max=cfg.max_wait_seconds,
            exp_base=cfg.multiplier,
        ),
        retry=retry_if_exception_type(exceptions),
        reraise=True,
    )
    for attempt in retrying:
        with attempt:
            return fn()
    raise RuntimeError("unreachable")  # pragma: no cover
