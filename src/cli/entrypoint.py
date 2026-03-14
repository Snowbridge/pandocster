"""pandocster command-line interface entry point."""

from __future__ import annotations

import click


@click.group()
def main() -> None:
    """Pandocster — helper around pandoc workflows."""


# Import command modules to register the subcommands
try:  # pragma: no cover - thin wiring
    from . import check as _check_command  # noqa: F401
except Exception:  # pragma: no cover - defensive
    _check_command = None

try:  # pragma: no cover - thin wiring
    from . import prepare as _prepare_command  # noqa: F401
except Exception:  # pragma: no cover - defensive
    _prepare_command = None

try:  # pragma: no cover - thin wiring
    from . import build as _build_command  # noqa: F401
except Exception:  # pragma: no cover - defensive
    _build_command = None


if __name__ == "__main__":
    main()
