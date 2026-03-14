"""Basic smoke tests for the pandocster package."""

from __future__ import annotations

import importlib


def test_package_importable() -> None:
    module = importlib.import_module("pandocster")
    assert module is not None


def test_core_run_returns_int() -> None:
    from pandocster import core

    code = core.run()
    assert isinstance(code, int)
