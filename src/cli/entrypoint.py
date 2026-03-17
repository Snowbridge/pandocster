"""pandocster command-line interface entry point."""

from __future__ import annotations

import importlib.metadata

import click

_VERSION = importlib.metadata.version("pandocster")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(_VERSION, "-v", "--version", prog_name="pandocster")
def main() -> None:
    """Pandocster — assembles a single document from a Markdown file tree.

    Takes a directory of Markdown files (optionally nested in subdirectories),
    preprocesses them (header offsets, image paths, reference-style links),
    and renders the result via pandoc into a standalone output file.

    Typical workflow:

    \b
      pandocster check                        # verify pandoc & Lua versions
      pandocster build ./docs --to pdf        # build a PDF
      pandocster build ./docs --to docx       # build a Word document
      pandocster config show                  # print effective configuration

    Configuration is loaded in order: pandocster.yaml in the current directory,
    then ~/.config/pandocster/config.yaml, then built-in defaults.
    Use 'pandocster config create' to generate a starter config file.
    """


# Import command modules to register the subcommands
try:  # pragma: no cover - thin wiring
    from . import check as _check_command  # noqa: F401
except ImportError:  # pragma: no cover - defensive
    _check_command = None

try:  # pragma: no cover - thin wiring
    from . import prepare as _prepare_command  # noqa: F401
except ImportError:  # pragma: no cover - defensive
    _prepare_command = None

try:  # pragma: no cover - thin wiring
    from . import build as _build_command  # noqa: F401
except ImportError:  # pragma: no cover - defensive
    _build_command = None

try:  # pragma: no cover - thin wiring
    from . import config_cmd as _config_command  # noqa: F401
except ImportError:  # pragma: no cover - defensive
    _config_command = None

try:  # pragma: no cover - thin wiring
    from . import init_cmd as _init_command  # noqa: F401
except ImportError:  # pragma: no cover - defensive
    _init_command = None


if __name__ == "__main__":
    main()
