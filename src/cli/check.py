"""Check command for pandocster CLI."""

from __future__ import annotations

from typing import NoReturn

import click

from service.commands.checks import (
    MIN_LUA_VERSION,
    MIN_PANDOC_VERSION,
    PandocCheckStatus,
    run_pandoc_check,
)

from .entrypoint import main


INSTALL_HELP = (
    "Pandocster requires pandoc >= {pandoc_min} with a built-in Lua scripting "
    "engine >= {lua_min}.\n"
    "Your current installation does not meet these requirements.\n"
    "Please install or upgrade pandoc following the official instructions at "
    "https://pandoc.org/installing.html."
).format(pandoc_min=MIN_PANDOC_VERSION, lua_min=MIN_LUA_VERSION)


@main.command("check")
def check_command() -> NoReturn:
    """Verify that pandoc and its Lua engine satisfy pandocster requirements."""
    result = run_pandoc_check()

    if result.status is PandocCheckStatus.OK:
        click.echo(
            "Pandocster is ready to use.\n"
            f"Detected pandoc {result.pandoc_version} with Lua {result.lua_version}."
        )
        raise SystemExit(0)

    if result.status is PandocCheckStatus.PANDOC_NOT_FOUND:
        click.echo(
            "Could not find the `pandoc` executable in your PATH.\n" f"{INSTALL_HELP}"
        )
        raise SystemExit(1)

    if result.status is PandocCheckStatus.PANDOC_VERSION_TOO_OLD:
        detected = result.pandoc_version or "unknown"
        click.echo(
            "Your pandoc installation is too old "
            f"(detected version: {detected}).\n{INSTALL_HELP}"
        )
        raise SystemExit(1)

    if result.status is PandocCheckStatus.LUA_VERSION_TOO_OLD:
        detected = result.lua_version or "unknown"
        click.echo(
            "Your Lua scripting engine for pandoc is too old or missing "
            f"(detected version: {detected}).\n{INSTALL_HELP}"
        )
        raise SystemExit(1)

    click.echo(
        "An unexpected error occurred while checking your pandoc installation.\n"
        f"{INSTALL_HELP}"
    )
    raise SystemExit(1)

