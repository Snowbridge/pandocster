"""Config command for pandocster CLI: show and create configuration."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import click
import yaml

from config import ConfigError, config_to_dict, load_config
from config.load import GLOBAL_CONFIG_PATH

from .entrypoint import main


@main.group("config")
def config_group() -> None:
    """View or create pandocster configuration.

    Config is loaded in priority order:

    \b
      1. pandocster.yaml in the current directory
      2. ~/.config/pandocster/config.yaml (global)
      3. Built-in defaults (shown below)

    Use 'pandocster config show' to inspect the effective config and
    'pandocster config create' to write it as a file you can then edit.

    \b
    DEFAULT PANDOC OPTIONS
      --toc=true              Include a table of contents.
      --toc-depth=3           Maximum heading level shown in the TOC.
      --standalone=true       Produce a standalone document (with header/footer).
      --embed-resources=true  Embed all external resources (images, CSS) inline.

    \b
    DEFAULT METADATA
      lang: ru                Document language (affects hyphenation, TOC heading).
      toc-title: Оглавление   Heading text used for the table of contents.

    \b
    DEFAULT LUA FILTERS (applied in order)
      header_offset           Adjusts heading levels based on directory depth.
      link_anchors            Rewrites cross-file anchor links for the merged doc.
      absorb_nonvisual_paragraphs  Removes invisible/non-visual paragraphs.
      newpage                 Inserts page breaks at section boundaries.

    \b
    DIAGRAM TOOLS (auto-detected at startup)
      mmdc (Mermaid CLI)      Converts ```mermaid fenced blocks to images.
                              Enabled automatically when 'mmdc' is on PATH.
      graphviz (dot)          Converts ```graphviz / ```graphiz fenced blocks.
                              Enabled automatically when 'dot' is on PATH.
    """


@config_group.command("show")
def config_show() -> NoReturn:
    """Print current app config (local/global file or defaults) as YAML."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from exc
    data = config_to_dict(cfg)
    out = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    click.echo(out)
    raise SystemExit(0)


@config_group.command("create")
@click.option(
    "-g",
    "--global",
    "use_global",
    is_flag=True,
    default=False,
    help="Write to ~/.config/pandocster/config.yaml instead of ./pandocster.yaml.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite an existing config file without prompting.",
)
def config_create(use_global: bool, force: bool) -> NoReturn:
    """Write config file in current directory (or globally with --global)."""
    try:
        cfg = load_config()
    except ConfigError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from exc
    path = GLOBAL_CONFIG_PATH if use_global else Path.cwd() / "pandocster.yaml"
    if path.exists():
        if not force:
            click.echo(
                f"{path} already exists. Pass --force to overwrite it.", err=True
            )
            raise SystemExit(1)
    if use_global:
        path.parent.mkdir(parents=True, exist_ok=True)
    data = config_to_dict(cfg)
    try:
        yaml_str = yaml.dump(
            data, allow_unicode=True, default_flow_style=False, sort_keys=False
        )
        path.write_text(yaml_str, encoding="utf-8")
    except OSError as exc:
        click.echo(f"Failed to write {path}: {exc}", err=True)
        raise SystemExit(1) from exc
    click.echo(f"Created {path}")
    raise SystemExit(0)
