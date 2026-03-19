"""Prepare command for pandocster CLI."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import click

from config import load_config
from service.command_log import make_logging_runner
from service.commands.prepare import PrepareError, run_prepare

from .entrypoint import LOG_OPTION, ensure_log_session, main


@main.command("prepare", hidden=True)
@click.pass_context
@LOG_OPTION
@click.argument("src", type=str, required=True)
@click.argument("build", type=str, required=False, default="./build")
def prepare_command(ctx: click.Context, log: bool, src: str, build: str) -> NoReturn:
    """Prepare a build directory from source markdown tree."""
    src_path = Path(src).expanduser().resolve()
    build_path = Path(build).expanduser().resolve()
    cfg = load_config()
    log_enabled = log or ctx.obj.get("log")
    ctx.obj["log"] = log_enabled
    ensure_log_session(log_enabled)
    runner = make_logging_runner() if log_enabled else None

    try:
        run_prepare(src_path, build_path, cfg, runner=runner)
    except PrepareError as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1)
    except Exception as exc:  # pragma: no cover - defensive
        click.echo(f"Unexpected error during prepare: {exc}", err=True)
        raise SystemExit(1)

    click.echo(f"Prepared build directory at: {build_path}")
    raise SystemExit(0)

