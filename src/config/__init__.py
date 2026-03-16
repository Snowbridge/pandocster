"""Pandocster configuration: load from local/global YAML or defaults."""

from __future__ import annotations

from .load import ConfigError, config_to_dict, load_config
from .schema import (
    AppConfig,
    DiagramOption,
    DiagramToolConfig,
    DiagramsConfig,
    PandocConfig,
    PandocOption,
    default_config,
)

__all__ = [
    "AppConfig",
    "ConfigError",
    "DiagramOption",
    "DiagramToolConfig",
    "DiagramsConfig",
    "PandocConfig",
    "PandocOption",
    "config_to_dict",
    "default_config",
    "load_config",
]
