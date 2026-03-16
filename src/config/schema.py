"""Configuration schema and default values for Pandocster."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from typing import Any

from service.commands.checks import (
    ToolCheckStatus,
    run_dot_check,
    run_mmdc_check,
)
from service.subprocess_runner import Runner

_DEFAULT_FILTER_ORDER = (
    "header_offset",
    "link_anchors",
    "absorb_nonvisual_paragraphs",
    "newpage",
)

@dataclass
class PandocOption:
    """A single pandoc option or flag (e.g. toc-depth=3, standalone=true)."""

    name: str
    value: str | bool | int


@dataclass
class PandocConfig:
    """Pandoc-related settings: binary, filters, metadata, options."""

    bin: str
    filters: list[str]
    # Arbitrary YAML structure; we do not parse it, only write to a temp file
    # and pass its path to pandoc via --metadata-file.
    metadata: Any
    options: list[PandocOption]


@dataclass
class DiagramOption:
    """A single diagram tool option (e.g. width=1000). Value is optional."""

    name: str
    value: str | None = None


@dataclass
class DiagramToolConfig:
    """Settings for a single diagram tool (mmdc or graphviz)."""

    enabled: bool
    bin: str
    options: list[DiagramOption]
    format: str = "png"


@dataclass
class DiagramsConfig:
    """Diagram tool configurations."""

    mmdc: DiagramToolConfig | None
    graphviz: DiagramToolConfig | None


@dataclass
class AppConfig:
    """Pandocster application config: pandoc settings."""

    pandoc: PandocConfig
    diagrams: DiagramsConfig | None = None


def default_config(runner: Runner | None = None) -> AppConfig:
    """Return the default configuration with auto-detected diagram tool availability."""
    base = resources.files("pandoc-filters")
    default_filters = [str(base / f"{name}.lua") for name in _DEFAULT_FILTER_ORDER]

    dot_ok = run_dot_check(runner).status == ToolCheckStatus.OK
    mmdc_ok = run_mmdc_check(runner).status == ToolCheckStatus.OK

    return AppConfig(
        pandoc=PandocConfig(
            bin="pandoc",
            filters=default_filters,
            metadata={
                "lang": "ru",
                "toc-title": "Оглавление",
            },
            options=[
                PandocOption(name="toc", value=True),
                PandocOption(name="toc-depth", value=3),
                PandocOption(name="standalone", value=True),
                PandocOption(name="embed-resources", value=True),
            ],
        ),
        diagrams=DiagramsConfig(
            mmdc=DiagramToolConfig(enabled=mmdc_ok, bin="mmdc", options=[]),
            graphviz=DiagramToolConfig(enabled=dot_ok, bin="dot", options=[]),
        ),
    )
