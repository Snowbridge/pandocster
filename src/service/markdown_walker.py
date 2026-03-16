"""Shared markdown file walker for pandocster service commands."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator


def walk_markdown_files(root: Path) -> Iterator[tuple[Path, int]]:
    """Yield (path, current_level) for every .md file under root.

    current_level starts at 1 for files directly in root, and increases by one
    for each additional directory depth.
    """
    for root_dir, dirnames, filenames in os.walk(root):
        dirnames.sort()
        filenames.sort()

        current_dir = Path(root_dir)
        rel = current_dir.relative_to(root)
        current_level = len(rel.parts) + 1

        for filename in filenames:
            if filename.lower().endswith(".md"):
                yield current_dir / filename, current_level
