"""Build command for pandocster CLI."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import click

from config.load import load_config
from service.commands.build import BuildError, run_build
from service.commands.prepare import PrepareError

from .entrypoint import main

_TO_CHOICES = [
    "ansi",
    "asciidoc",
    "asciidoc_legacy",
    "asciidoctor",
    "bbcode",
    "bbcode_fluxbb",
    "bbcode_hubzilla",
    "bbcode_phpbb",
    "bbcode_steam",
    "bbcode_xenforo",
    "beamer",
    "biblatex",
    "bibtex",
    "chunkedhtml",
    "commonmark",
    "commonmark_x",
    "context",
    "csljson",
    "djot",
    "docbook",
    "docbook4",
    "docbook5",
    "docx",
    "dokuwiki",
    "dzslides",
    "epub",
    "epub2",
    "epub3",
    "fb2",
    "gfm",
    "haddock",
    "html",
    "html4",
    "html5",
    "icml",
    "ipynb",
    "jats",
    "jats_archiving",
    "jats_articleauthoring",
    "jats_publishing",
    "jira",
    "json",
    "latex",
    "man",
    "markdown",
    "markdown_github",
    "markdown_mmd",
    "markdown_phpextra",
    "markdown_strict",
    "markua",
    "mediawiki",
    "ms",
    "muse",
    "native",
    "odt",
    "opendocument",
    "opml",
    "org",
    "pdf",
    "plain",
    "pptx",
    "revealjs",
    "rst",
    "rtf",
    "s5",
    "slideous",
    "slidy",
    "tei",
    "texinfo",
    "textile",
    "typst",
    "vimdoc",
    "xml",
    "xwiki",
    "zimwiki",
]


@main.command("build")
@click.argument("src", type=str, required=True)
@click.argument("build", type=str, required=False, default="./build")
@click.option(
    "--to",
    "to_format",
    type=click.Choice(_TO_CHOICES),
    required=True,
    help="Output format passed to pandoc.",
)
@click.option(
    "--file-name",
    "file_name",
    type=str,
    required=False,
    help="Base name of the output file (without extension).",
)
@click.option(
    "--preserve-build",
    is_flag=True,
    default=False,
    help="Preserve build directory after pandoc run.",
)
def build_command(
    src: str,
    build: str,
    to_format: str,
    file_name: str | None,
    preserve_build: bool,
) -> NoReturn:
    """Prepare a build directory and render a document via pandoc."""
    src_path = Path(src).expanduser().resolve()
    build_path = Path(build).expanduser().resolve()
    config = load_config(Path.cwd())

    try:
        output_path = run_build(
            src=src_path,
            build=build_path,
            to_format=to_format,
            file_name=file_name,
            preserve_build=preserve_build,
            config=config,
        )
    except (PrepareError, BuildError) as exc:
        click.echo(str(exc), err=True)
        raise SystemExit(1)
    except Exception as exc:  # pragma: no cover - defensive
        click.echo(f"Unexpected error during build: {exc}", err=True)
        raise SystemExit(1)

    click.echo(f"Built document at: {output_path}")
    raise SystemExit(0)

