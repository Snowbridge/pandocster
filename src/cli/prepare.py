"""Prepare command for pandocster CLI."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import click

from service.commands.prepare import PrepareError, run_prepare
from .entrypoint import main


@main.command("prepare", hidden=True)
@click.argument("src", type=str, required=True)
@click.argument("build", type=str, required=False, default="./build")
def prepare_command(src: str, build: str) -> NoReturn:
    """Prepare a build directory from source markdown tree."""
    src_path = Path(src).expanduser().resolve()
    build_path = Path(build).expanduser().resolve()

    try:
        run_prepare(src_path, build_path)
    except PrepareError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1)
    except Exception as exc:  # pragma: no cover - defensive
        click.echo(f"Unexpected error during prepare: {exc}", err=True)
        raise SystemExit(1)

    click.echo(f"Prepared build directory at: {build_path}")
    raise SystemExit(0)

