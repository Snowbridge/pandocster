"""Load configuration from local/global YAML or defaults."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import AppConfig, PandocConfig, PandocOption, default_config

LOCAL_CONFIG_NAME = "pandocster.yaml"
GLOBAL_CONFIG_PATH = Path.home() / ".config" / "pandocster" / "config.yaml"

ROOT_KEY = "pandocster"


class ConfigError(Exception):
    """Raised when config file is invalid or missing required structure."""


def _local_config_path(cwd: Path) -> Path:
    return cwd / LOCAL_CONFIG_NAME


def _parse_option(raw: Any) -> PandocOption:
    if not isinstance(raw, dict):
        raise ConfigError(
            f"Expected option as dict with 'name' and 'value', got {type(raw)}"
        )
    name = raw.get("name")
    value = raw.get("value")
    if name is None:
        raise ConfigError("Option must have 'name'")
    if value is None:
        raise ConfigError("Option must have 'value'")
    return PandocOption(name=str(name), value=value)


def _parse_pandoc(raw: Any, defaults: PandocConfig) -> PandocConfig:
    if raw is None:
        return defaults
    if not isinstance(raw, dict):
        raise ConfigError(f"Expected 'pandoc' as dict, got {type(raw)}")
    bin_name = raw.get("bin")
    if bin_name is not None:
        bin_name = str(bin_name)
    else:
        bin_name = defaults.bin
    filters = raw.get("filters")
    if filters is not None:
        if not isinstance(filters, list) or not all(
            isinstance(x, str) for x in filters
        ):
            raise ConfigError("'pandoc.filters' must be a list of strings")
        filters = list(filters)
    else:
        filters = list(defaults.filters)
    metadata = raw.get("metadata")
    if metadata is not None:
        # Keep as-is: arbitrary YAML structure, we do not parse or validate it.
        pass
    else:
        metadata = dict(defaults.metadata)
    options_raw = raw.get("options")
    if options_raw is not None:
        if not isinstance(options_raw, list):
            raise ConfigError("'pandoc.options' must be a list")
        options = [_parse_option(o) for o in options_raw]
    else:
        options = list(defaults.options)
    return PandocConfig(
        bin=bin_name, filters=filters, metadata=metadata, options=options
    )


def _parse_app_config(raw: Any, defaults: AppConfig) -> AppConfig:
    if raw is None:
        return defaults
    if not isinstance(raw, dict):
        raise ConfigError(f"Expected '{ROOT_KEY}' value as dict, got {type(raw)}")
    builtin = raw.get("builtin-filters")
    if builtin is not None:
        if not isinstance(builtin, list) or not all(
            isinstance(x, str) for x in builtin
        ):
            raise ConfigError("'builtin-filters' must be a list of strings")
        builtin_filters = list(builtin)
    else:
        builtin_filters = list(defaults.builtin_filters)
    pandoc_raw = raw.get("pandoc")
    pandoc = _parse_pandoc(pandoc_raw, defaults.pandoc)
    return AppConfig(builtin_filters=builtin_filters, pandoc=pandoc)


def _load_yaml(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text)


def config_to_dict(cfg: AppConfig) -> dict[str, Any]:
    """Convert AppConfig to a dict suitable for YAML dump (with pandocster key)."""
    options_data = [{"name": o.name, "value": o.value} for o in cfg.pandoc.options]
    pandoc_data: dict[str, Any] = {
        "bin": cfg.pandoc.bin,
        "filters": cfg.pandoc.filters,
        "metadata": cfg.pandoc.metadata,
        "options": options_data,
    }
    return {
        ROOT_KEY: {
            "builtin-filters": cfg.builtin_filters,
            "pandoc": pandoc_data,
        }
    }


def load_config(cwd: Path | None = None) -> AppConfig:
    """Load config: local file > global file > defaults. Uses cwd for local path."""
    if cwd is None:
        cwd = Path.cwd()
    defaults = default_config()
    local_path = _local_config_path(cwd)
    if local_path.exists() and local_path.is_file():
        try:
            data = _load_yaml(local_path)
        except (OSError, yaml.YAMLError) as e:
            raise ConfigError(f"Failed to read config from {local_path}: {e}") from e
        if not isinstance(data, dict) or ROOT_KEY not in data:
            raise ConfigError(f"Config file must have top-level key '{ROOT_KEY}'")
        return _parse_app_config(data[ROOT_KEY], defaults)
    if GLOBAL_CONFIG_PATH.exists() and GLOBAL_CONFIG_PATH.is_file():
        try:
            data = _load_yaml(GLOBAL_CONFIG_PATH)
        except (OSError, yaml.YAMLError) as e:
            raise ConfigError(
                f"Failed to read config from {GLOBAL_CONFIG_PATH}: {e}"
            ) from e
        if not isinstance(data, dict) or ROOT_KEY not in data:
            raise ConfigError(f"Config file must have top-level key '{ROOT_KEY}'")
        return _parse_app_config(data[ROOT_KEY], defaults)
    return defaults
