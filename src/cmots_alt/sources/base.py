"""SourceAdapter base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..core.settings import Settings


@dataclass(frozen=True)
class BronzeResult:
    source: str
    artifact: str
    partition: date
    path: Path
    run_id: str
    rows_hint: int | None = None


class SourceAdapter(ABC):
    name: str

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def fetch(self, *, partition: date, **kwargs: object) -> BronzeResult: ...
