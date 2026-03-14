"""Pandocster configuration: load from local/global YAML or defaults."""

from __future__ import annotations

from pathlib import Path

from .load import ConfigError, config_to_dict, load_config
from .schema import AppConfig, PandocConfig, PandocOption, default_config

__all__ = [
    "AppConfig",
    "ConfigError",
    "PandocConfig",
    "PandocOption",
    "app_config",
    "config_to_dict",
    "default_config",
    "get_app_config",
    "load_config",
]

app_config: AppConfig | None = None


def get_app_config(cwd: Path | None = None) -> AppConfig:
    """Return the application config, loading it lazily on first call (from cwd)."""
    global app_config
    if app_config is None:
        app_config = load_config(cwd=cwd)
    return app_config
