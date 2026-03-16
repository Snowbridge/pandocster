"""Load configuration from local/global YAML or defaults."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import (
    AppConfig,
    DiagramOption,
    DiagramToolConfig,
    DiagramsConfig,
    PandocConfig,
    PandocOption,
    default_config,
)

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


def _parse_diagram_option(raw: Any) -> DiagramOption:
    if not isinstance(raw, dict):
        raise ConfigError(
            f"Expected diagram option as dict with 'name', got {type(raw)}"
        )
    name = raw.get("name")
    if name is None:
        raise ConfigError("Diagram option must have 'name'")
    value = raw.get("value")
    return DiagramOption(name=str(name), value=str(value) if value is not None else None)


def _parse_diagram_tool(raw: Any, tool_name: str) -> DiagramToolConfig:
    if not isinstance(raw, dict):
        raise ConfigError(f"Expected 'diagrams.{tool_name}' as dict, got {type(raw)}")
    enabled = raw.get("enabled")
    if enabled is None:
        raise ConfigError(f"'diagrams.{tool_name}.enabled' is required")
    if not isinstance(enabled, bool):
        raise ConfigError(f"'diagrams.{tool_name}.enabled' must be a boolean")
    bin_name = raw.get("bin")
    if bin_name is None:
        raise ConfigError(f"'diagrams.{tool_name}.bin' is required")
    options_raw = raw.get("options")
    if options_raw is not None:
        if not isinstance(options_raw, list):
            raise ConfigError(f"'diagrams.{tool_name}.options' must be a list")
        options = [_parse_diagram_option(o) for o in options_raw]
    else:
        options = []
    format_raw = raw.get("format")
    fmt = str(format_raw) if format_raw is not None else "png"
    return DiagramToolConfig(enabled=enabled, bin=str(bin_name), options=options, format=fmt)


def _parse_diagrams(raw: Any) -> DiagramsConfig | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ConfigError(f"Expected 'diagrams' as dict, got {type(raw)}")
    mmdc_raw = raw.get("mmdc")
    mmdc = _parse_diagram_tool(mmdc_raw, "mmdc") if mmdc_raw is not None else None
    graphviz_raw = raw.get("graphviz")
    graphviz = (
        _parse_diagram_tool(graphviz_raw, "graphviz")
        if graphviz_raw is not None
        else None
    )
    return DiagramsConfig(mmdc=mmdc, graphviz=graphviz)


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
        # Key missing: apply no filters (do not use defaults).
        filters = []
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
    pandoc_raw = raw.get("pandoc")
    pandoc = _parse_pandoc(pandoc_raw, defaults.pandoc)
    diagrams = _parse_diagrams(raw.get("diagrams"))
    return AppConfig(pandoc=pandoc, diagrams=diagrams)


def _load_yaml(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _diagram_tool_to_dict(tool: DiagramToolConfig) -> dict[str, Any]:
    options_data = [
        {"name": o.name, "value": o.value} if o.value is not None else {"name": o.name}
        for o in tool.options
    ]
    return {"enabled": tool.enabled, "bin": tool.bin, "format": tool.format, "options": options_data}


def config_to_dict(cfg: AppConfig) -> dict[str, Any]:
    """Convert AppConfig to a dict suitable for YAML dump (with pandocster key)."""
    options_data = [{"name": o.name, "value": o.value} for o in cfg.pandoc.options]
    pandoc_data: dict[str, Any] = {
        "bin": cfg.pandoc.bin,
        "filters": cfg.pandoc.filters,
        "metadata": cfg.pandoc.metadata,
        "options": options_data,
    }
    root: dict[str, Any] = {"pandoc": pandoc_data}
    if cfg.diagrams is not None:
        diagrams_data: dict[str, Any] = {}
        if cfg.diagrams.mmdc is not None:
            diagrams_data["mmdc"] = _diagram_tool_to_dict(cfg.diagrams.mmdc)
        if cfg.diagrams.graphviz is not None:
            diagrams_data["graphviz"] = _diagram_tool_to_dict(cfg.diagrams.graphviz)
        root["diagrams"] = diagrams_data
    return {ROOT_KEY: root}


def _load_and_parse(path: Path, defaults: AppConfig) -> AppConfig:
    """Load and parse a config YAML file, raising ConfigError on any problem."""
    try:
        data = _load_yaml(path)
    except (OSError, yaml.YAMLError) as e:
        raise ConfigError(f"Failed to read config from {path}: {e}") from e
    if not isinstance(data, dict) or ROOT_KEY not in data:
        raise ConfigError(f"Config file must have top-level key '{ROOT_KEY}'")
    return _parse_app_config(data[ROOT_KEY], defaults)


def load_config(cwd: Path | None = None) -> AppConfig:
    """Load config: local file > global file > defaults. Uses cwd for local path."""
    if cwd is None:
        cwd = Path.cwd()
    defaults = default_config()
    local_path = _local_config_path(cwd)
    if local_path.exists() and local_path.is_file():
        return _load_and_parse(local_path, defaults)
    if GLOBAL_CONFIG_PATH.exists() and GLOBAL_CONFIG_PATH.is_file():
        return _load_and_parse(GLOBAL_CONFIG_PATH, defaults)
    return defaults
