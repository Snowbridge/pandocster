"""Check command for pandocster CLI."""

from __future__ import annotations

from typing import NoReturn

import click

from config import load_config
from service.command_log import make_logging_runner
from service.commands.checks import (
    MIN_DOT_VERSION,
    MIN_LUA_VERSION,
    MIN_MMDC_VERSION,
    MIN_PANDOC_VERSION,
    PandocCheckStatus,
    ToolCheckResult,
    ToolCheckStatus,
    run_dot_check,
    run_mmdc_check,
    run_pandoc_check,
)

from .entrypoint import LOG_OPTION, ensure_log_session, main

INSTALL_HELP = (
    "Pandocster requires pandoc >= {pandoc_min} with a built-in Lua scripting "
    "engine >= {lua_min}.\n"
    "Your current installation does not meet these requirements.\n"
    "Please install or upgrade pandoc following the official instructions at "
    "https://pandoc.org/installing.html."
).format(pandoc_min=MIN_PANDOC_VERSION, lua_min=MIN_LUA_VERSION)


def _dot_warning(result: ToolCheckResult, bin: str = "dot") -> str | None:
    """Return a warning message for a failed dot check, or None if OK."""
    match result.status:
        case ToolCheckStatus.NOT_FOUND:
            return (
                f"WARNING: `{bin}` not found in PATH. "
                f"Graphviz diagrams will not be rendered until you install "
                f"dot >= {MIN_DOT_VERSION}."
            )
        case ToolCheckStatus.VERSION_TOO_OLD:
            detected = result.version or "unknown"
            return (
                f"WARNING: `{bin}` version {detected} may render Graphviz diagrams "
                f"incorrectly. Please upgrade to dot >= {MIN_DOT_VERSION}."
            )
        case _:
            return None


def _mmdc_warning(result: ToolCheckResult, bin: str = "mmdc") -> str | None:
    """Return a warning message for a failed mmdc check, or None if OK."""
    match result.status:
        case ToolCheckStatus.NOT_FOUND:
            return (
                f"WARNING: `{bin}` not found in PATH. "
                "Mermaid diagrams will not be rendered until you install "
                "@mermaid-js/mermaid-cli."
            )
        case ToolCheckStatus.VERSION_TOO_OLD:
            detected = result.version or "unknown"
            return (
                f"WARNING: `{bin}` version {detected} may render Mermaid diagrams "
                f"incorrectly. Please upgrade to mmdc >= {MIN_MMDC_VERSION}."
            )
        case _:
            return None


@main.command("check")
@click.pass_context
@LOG_OPTION
def check_command(ctx: click.Context, log: bool) -> NoReturn:
    """Verify that pandoc and its Lua engine satisfy pandocster requirements."""
    cfg = load_config()
    dot_bin = cfg.diagrams.graphviz.bin if cfg.diagrams and cfg.diagrams.graphviz else "dot"
    mmdc_bin = cfg.diagrams.mmdc.bin if cfg.diagrams and cfg.diagrams.mmdc else "mmdc"
    log_enabled = log or ctx.obj.get("log")
    ctx.obj["log"] = log_enabled
    ensure_log_session(log_enabled)
    runner = make_logging_runner() if log_enabled else None

    pandoc_result = run_pandoc_check(runner=runner)
    dot_result = run_dot_check(runner=runner, bin=dot_bin)
    mmdc_result = run_mmdc_check(runner=runner, bin=mmdc_bin)

    match pandoc_result.status:
        case PandocCheckStatus.OK:
            click.echo(
                "Pandocster is ready to use.\n"
                f"Detected pandoc {pandoc_result.pandoc_version}"
                f" with Lua {pandoc_result.lua_version}."
            )

        case PandocCheckStatus.PANDOC_NOT_FOUND:
            click.echo(
                "Could not find the `pandoc` executable in your PATH.\n"
                f"{INSTALL_HELP}"
            )
            raise SystemExit(1)

        case PandocCheckStatus.PANDOC_VERSION_TOO_OLD:
            detected = pandoc_result.pandoc_version or "unknown"
            click.echo(
                "Your pandoc installation is too old "
                f"(detected version: {detected}).\n{INSTALL_HELP}"
            )
            raise SystemExit(1)

        case PandocCheckStatus.LUA_VERSION_TOO_OLD:
            detected = pandoc_result.lua_version or "unknown"
            click.echo(
                "Your Lua scripting engine for pandoc is too old or missing "
                f"(detected version: {detected}).\n{INSTALL_HELP}"
            )
            raise SystemExit(1)

        case PandocCheckStatus.UNKNOWN_ERROR:
            click.echo(
                "An unexpected error occurred while checking"
                f" your pandoc installation.\n{INSTALL_HELP}"
            )
            raise SystemExit(1)

    for warning in filter(None, [_dot_warning(dot_result, dot_bin), _mmdc_warning(mmdc_result, mmdc_bin)]):
        click.echo(warning)

    raise SystemExit(0)
