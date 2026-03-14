"""Configuration schema and default values for Pandocster."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
    """Pandocster application config: builtin filters and pandoc settings."""

    builtin_filters: list[str]
    pandoc: PandocConfig


def default_config() -> AppConfig:
    """Return the default configuration (matches docs/config.yml)."""
    return AppConfig(
        builtin_filters=[
            "header_offset",
            "link_anchors",
            "absorb_nonvisual_paragraphs",
            "newpage",
        ],
        pandoc=PandocConfig(
            bin="pandoc",
            filters=["$BUILTIN"],
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
