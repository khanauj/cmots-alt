"""File-level fetch helpers (download to disk + hashing)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..core.settings import HttpConfig
from .http import fetch_bytes


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_to_file(url: str, dest: Path, http_cfg: HttpConfig) -> tuple[Path, str, int]:
    """Download URL to dest. Returns (path, sha256, bytes_written)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = fetch_bytes(url, http_cfg)
    dest.write_bytes(data)
    return dest, sha256_of_bytes(data), len(data)
