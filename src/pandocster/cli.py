"""Command-line interface for pandocster."""

from __future__ import annotations

from . import core


def main() -> int:
    """Entry point for the pandocster CLI."""
    return core.run()


if __name__ == "__main__":
    raise SystemExit(main())

