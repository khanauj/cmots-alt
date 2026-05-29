"""Settings loader. Reads config/settings.yaml into a typed model."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class StoragePaths(BaseModel):
    raw: Path
    silver: Path
    gold: Path
    output: Path
    cache: Path


class PathsConfig(BaseModel):
    root: Path
    storage: StoragePaths
    db: Path
    logs: Path


class ProjectConfig(BaseModel):
    name: str
    timezone: str = "Asia/Kolkata"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    console: bool = True
    file: bool = True


class RetryConfig(BaseModel):
    attempts: int = 5
    initial_wait_seconds: float = 1.0
    max_wait_seconds: float = 30.0
    multiplier: float = 2.0


class HttpConfig(BaseModel):
    default_timeout_seconds: int = 30
    user_agent: str = "cmots-alt/0.1"


class Settings(BaseModel):
    project: ProjectConfig
    paths: PathsConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    http: HttpConfig = Field(default_factory=HttpConfig)

    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT

    def resolve(self, p: Path) -> Path:
        """Resolve a possibly-relative path against the project root."""
        return p if p.is_absolute() else (self.project_root / p).resolve()


_PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]


@lru_cache(maxsize=1)
def load_settings(config_path: Path | None = None) -> Settings:
    cfg_path = config_path or (_PROJECT_ROOT / "config" / "settings.yaml")
    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Settings.model_validate(data)


def ensure_directories(settings: Settings) -> None:
    """Create all configured storage/log directories if missing."""
    for p in (
        settings.paths.storage.raw,
        settings.paths.storage.silver,
        settings.paths.storage.gold,
        settings.paths.storage.output,
        settings.paths.storage.cache,
        settings.paths.logs,
        settings.paths.db.parent,
    ):
        settings.resolve(p).mkdir(parents=True, exist_ok=True)
