"""Configuration schema and default values for Pandocster."""

from __future__ import annotations

from importlib import resources
from dataclasses import dataclass
from typing import Any

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
class AppConfig:
    """Pandocster application config: pandoc settings."""

    pandoc: PandocConfig


def default_config() -> AppConfig:
    """Return the default configuration."""
    base = resources.files("pandoc-filters")
    default_filters = [str(base / f"{name}.lua") for name in _DEFAULT_FILTER_ORDER]
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
    )
