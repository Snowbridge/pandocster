"""Implementation of the `build` command logic for pandocster."""

from __future__ import annotations

import os
import shutil
import subprocess
from importlib import resources
from pathlib import Path
from typing import Callable, Iterable, List, Sequence

from .prepare import PrepareError, run_prepare


class BuildError(RuntimeError):
    """User-facing errors for the `build` command."""


def _get_lua_filters() -> List[str]:
    """Return pandoc --lua-filter arguments pointing to packaged Lua filters.

    Paths are resolved relative to the installed `service` package so that the
    CLI behaves consistently regardless of the current working directory.
    """
    base = resources.files("pandoc-filters")
    filters = [
        base / "header_offset.lua",
        base / "link_anchors.lua",
        base / "absorb_nonvisual_paragraphs.lua",
        base / "newpage.lua",
    ]
    return [f"--lua-filter={str(path)}" for path in filters]


def _iter_markdown_files(build: Path) -> List[Path]:
    """Collect all markdown files under the build directory, sorted by path."""
    files: List[Path] = []
    for root, dirnames, filenames in os.walk(build):
        dirnames.sort()
        filenames.sort()
        root_path = Path(root)
        for filename in filenames:
            if not filename.lower().endswith(".md"):
                continue
            files.append(root_path / filename)

    # Sort by (relative directory, special index marker, filename) so that
    # `_index.md` comes first within each directory, while preserving
    # lexicographic ordering between directories and the remaining files.
    def _sort_key(path: Path) -> tuple[str, int, str]:
        rel = path.relative_to(build)
        parent = rel.parent.as_posix()
        name = rel.name
        is_index = 0 if name == "_index.md" else 1
        return parent, is_index, name

    files.sort(key=_sort_key)
    return files


def _build_pandoc_args(
    md_files: Iterable[Path],
    to_format: str,
    output_path: Path,
    resources_dir: Path,
) -> List[str]:
    args: List[str] = ["pandoc"]
    for path in md_files:
        args.append(str(path))
    args.extend(
        [
            "--toc",
            "--toc-depth=3",
            f"--output={output_path}",
            f"--to={to_format}",
            f"--resource-path={resources_dir}",
            "--standalone",
        ],
    )
    args.extend(_get_lua_filters())
    return args


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def _default_runner(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def run_build(
    src: Path,
    build: Path,
    to_format: str,
    file_name: str | None,
    preserve_build: bool,
    runner: Runner | None = None,
) -> Path:
    """Run prepare and then invoke pandoc to build the final document.

    Returns the path to the generated output file.
    """
    src_path = src.expanduser().resolve()
    build_path = build.expanduser().resolve()

    if src_path == build_path:
        raise BuildError("Source and build directories must not be the same.")

    try:
        run_prepare(src_path, build_path)
    except PrepareError as exc:
        raise BuildError(str(exc)) from exc

    md_files = _iter_markdown_files(build_path)
    if not md_files:
        raise BuildError(f"No markdown (*.md) files found under build directory: {build_path}")

    effective_file_name = file_name or Path.cwd().name
    if not effective_file_name:
        raise BuildError("Could not determine default output file name.")

    # The final document is created in the current working directory.
    output_path = Path.cwd() / f"{effective_file_name}.{to_format}"
    resources_dir = build_path / "resources"

    if not resources_dir.exists() or not resources_dir.is_dir():
        raise BuildError(f"Resources directory does not exist: {resources_dir}")

    actual_runner = runner or _default_runner

    try:
        completed = actual_runner(
            _build_pandoc_args(
                md_files=md_files,
                to_format=to_format,
                output_path=output_path,
                resources_dir=resources_dir,
            ),
        )
    except FileNotFoundError as exc:
        raise BuildError(f"Could not find the `pandoc` executable: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise BuildError(f"Unexpected error while running pandoc: {exc}") from exc

    if completed.returncode != 0:
        stderr = completed.stderr or ""
        stdout = completed.stdout or ""
        details = stderr.strip() or stdout.strip()
        message = "pandoc exited with a non-zero status code."
        if details:
            message = f"{message} Details: {details}"
        raise BuildError(message)

    if not preserve_build:
        try:
            shutil.rmtree(build_path)
        except OSError as exc:
            raise BuildError(f"Failed to remove build directory: {exc}") from exc

    return output_path

