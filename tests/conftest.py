from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest


@pytest.fixture()
def write_file():
    """Return a helper that writes text (or binary) content to a file."""

    def _write(file: Path, content: str, binary: bool = False) -> None:
        file.parent.mkdir(parents=True, exist_ok=True)
        if binary:
            file.write_bytes(content.encode("utf-8"))
        else:
            file.write_text(content, encoding="utf-8")

    return _write
