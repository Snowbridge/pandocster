"""Init command for pandocster CLI."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import click

from service.commands.init import InitError, run_init

from .entrypoint import LOG_OPTION, ensure_log_session, main


@main.command("init")
@click.pass_context
@LOG_OPTION
@click.argument("dir", type=str, required=False, default=".")
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Initialize even if the directory is not empty.",
)
def init_command(ctx: click.Context, log: bool, dir: str, force: bool) -> NoReturn:
    """Prepare a directory for document development.

    Creates pandocster.yaml, src/md, src/assets, src/templates directories,
    and a generate.sh build script.

    DIR defaults to the current directory.
    """
    target_dir = Path(dir).expanduser().resolve()
    log_enabled = log or ctx.obj.get("log")
    ctx.obj["log"] = log_enabled
    ensure_log_session(log_enabled)

    try:
        run_init(target_dir=target_dir, force=force)
    except InitError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1)
    except Exception as exc:  # pragma: no cover - defensive
        click.echo(f"Unexpected error during init: {exc}", err=True)
        raise SystemExit(1)

    click.echo(f"Initialized project directory: {target_dir}")
    raise SystemExit(0)
