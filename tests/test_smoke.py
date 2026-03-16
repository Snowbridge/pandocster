"""Basic smoke tests for the pandocster package."""

from __future__ import annotations

import importlib


def test_package_importable() -> None:
    module = importlib.import_module("pandocster")
    assert module is not None


def test_cli_entry_point_importable() -> None:
    module = importlib.import_module("cli.entrypoint")
    assert hasattr(module, "main")
