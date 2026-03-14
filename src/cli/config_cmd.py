"""Config command for pandocster CLI: show and create configuration."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import click
import yaml

from config import ConfigError, config_to_dict, get_app_config

from .entrypoint import main


@main.group("config")
def config_group() -> None:
    """View or create pandocster configuration."""


@config_group.command("show")
def config_show() -> NoReturn:
    """Print current app config (local/global file or defaults) as YAML."""
    try:
        cfg = get_app_config()
    except ConfigError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from exc
    data = config_to_dict(cfg)
    out = yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
    click.echo(out)
    raise SystemExit(0)


@config_group.command("create")
def config_create() -> NoReturn:
    """Write pandocster.yaml in current directory. Overwrites if present."""
    try:
        cfg = get_app_config()
    except ConfigError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1) from exc
    path = Path.cwd() / "pandocster.yaml"
    if path.exists():
        path.unlink()
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
