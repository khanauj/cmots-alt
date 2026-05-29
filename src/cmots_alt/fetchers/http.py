"""HTTP client with Chrome TLS fingerprint impersonation.

NSE / BSE both require this — naive httpx/requests get 403'd. AMFI doesn't
need it but uses the same primitive for consistency.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Mapping

from curl_cffi import requests as cffi_requests  # type: ignore[import-untyped]

from ..core.errors import FetchError
from ..core.settings import HttpConfig


@contextmanager
def chrome_session(http_cfg: HttpConfig) -> Iterator[cffi_requests.Session]:
    """Yield a curl_cffi Session impersonating recent Chrome."""
    sess = cffi_requests.Session(impersonate="chrome120")
    sess.headers.update({"User-Agent": http_cfg.user_agent})
    try:
        yield sess
    finally:
        sess.close()


def _raise_for_status(resp, url: str) -> None:
    if not (200 <= resp.status_code < 300):
        raise FetchError(f"GET {url} returned HTTP {resp.status_code}")


def fetch_text(
    url: str,
    http_cfg: HttpConfig,
    *,
    encoding: str = "utf-8",
    warmup_urls: list[str] | None = None,
    headers: Mapping[str, str] | None = None,
) -> str:
    """One-shot GET → text, optionally warming cookies first (for NSE)."""
    with chrome_session(http_cfg) as sess:
        for w in warmup_urls or []:
            try:
                sess.get(w, timeout=http_cfg.default_timeout_seconds)
            except Exception:
                pass  # warmup is best-effort
        try:
            resp = sess.get(
                url,
                timeout=http_cfg.default_timeout_seconds,
                headers=dict(headers) if headers else None,
            )
        except Exception as e:
            raise FetchError(f"GET {url} failed: {e}") from e
        _raise_for_status(resp, url)
        resp.encoding = encoding
        return resp.text


def fetch_bytes(
    url: str,
    http_cfg: HttpConfig,
    *,
    warmup_urls: list[str] | None = None,
    headers: Mapping[str, str] | None = None,
) -> bytes:
    with chrome_session(http_cfg) as sess:
        for w in warmup_urls or []:
            try:
                sess.get(w, timeout=http_cfg.default_timeout_seconds)
            except Exception:
                pass
        try:
            resp = sess.get(
                url,
                timeout=http_cfg.default_timeout_seconds,
                headers=dict(headers) if headers else None,
            )
        except Exception as e:
            raise FetchError(f"GET {url} failed: {e}") from e
        _raise_for_status(resp, url)
        return resp.content
