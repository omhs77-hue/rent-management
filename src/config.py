"""Configuration helpers for the crawler project."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "settings.yml"


@dataclass
class Settings:
    """In-memory representation of settings.yml."""

    paths: Dict[str, Any]
    http: Dict[str, Any]
    http_client: Dict[str, Any] = field(default_factory=dict)
    domains: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    concurrency: Dict[str, Any] = field(default_factory=dict)

    def data_root(self) -> Path:
        return Path(self.paths.get("data_root", "./data")).expanduser().resolve()


_SETTINGS_CACHE: Optional[Settings] = None


def get_settings(refresh: bool = False) -> Settings:
    """Load project settings from YAML.

    Args:
        refresh: Force reload from disk if True.
    """

    global _SETTINGS_CACHE
    if _SETTINGS_CACHE is not None and not refresh:
        return _SETTINGS_CACHE

    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Settings file not found: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    _SETTINGS_CACHE = Settings(**raw)
    return _SETTINGS_CACHE


def resolve_data_path(*parts: str) -> Path:
    """Resolve a path inside the configured data root."""

    settings = get_settings()
    path = settings.data_root().joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_data_directories(settings: Settings) -> None:
    """Ensure the expected directory tree exists under the data root."""

    root = settings.data_root()
    required = [
        root / "raw" / "blogs",
        root / "raw" / "youtube",
        root / "processed" / "chunks",
        root / "logs",
    ]
    for path in required:
        path.mkdir(parents=True, exist_ok=True)
