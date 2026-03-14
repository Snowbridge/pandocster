"""Implementation of the `build` command logic for pandocster."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Iterable, List, Sequence

import yaml

from config.schema import AppConfig, PandocConfig, default_config

from .prepare import PrepareError, run_prepare


class BuildError(RuntimeError):
    """User-facing errors for the `build` command."""


BUILTIN_PLACEHOLDER = "$BUILTIN"


def _resolve_builtin_filters(names: List[str]) -> List[str]:
    """Resolve builtin filter names to --lua-filter arguments.

    Paths are resolved via the installed `pandoc-filters` package so that the
    CLI behaves consistently regardless of the current working directory.
    """
    if not names:
        return []
    base = resources.files("pandoc-filters")
    return [f"--lua-filter={str(base / f'{name}.lua')}" for name in names]


def _get_lua_filters(
    pandoc_filters: List[str],
    builtin_filter_names: List[str],
) -> List[str]:
    """Return pandoc --lua-filter arguments from config.

    - If pandoc_filters is non-empty: use it. Each item is either a user path
      (passed as-is as --lua-filter=...) or BUILTIN_PLACEHOLDER, which is
      replaced by all resolved builtin filters from builtin_filter_names.
    - If pandoc_filters is empty: use builtin_filter_names resolved to paths
      under the packaged pandoc-filters. Empty builtin_filter_names yields no
      filters.
    """
    resolved_builtin = _resolve_builtin_filters(builtin_filter_names)

    if pandoc_filters:
        result: List[str] = []
        for item in pandoc_filters:
            if item == BUILTIN_PLACEHOLDER:
                result.extend(resolved_builtin)
            else:
                result.append(f"--lua-filter={item}")
        return result

    return resolved_builtin


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


def _should_write_metadata_file(metadata: Any) -> bool:
    """True if we have non-empty metadata to write (arbitrary YAML structure)."""
    if metadata is None:
        return False
    if isinstance(metadata, dict) and len(metadata) == 0:
        return False
    return True


def _option_value_to_str(value: str | bool | int) -> str:
    """Format a PandocOption value for pandoc CLI (e.g. True -> 'true')."""
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _build_pandoc_args(
    md_files: Iterable[Path],
    to_format: str,
    output_path: Path,
    resources_dir: Path,
    pandoc_config: PandocConfig,
    builtin_filters: List[str],
    metadata_file_path: Path | None = None,
) -> List[str]:
    args: List[str] = [pandoc_config.bin]
    for path in md_files:
        args.append(str(path))
    for opt in pandoc_config.options:
        args.append(f"--{opt.name}={_option_value_to_str(opt.value)}")
    args.extend(
        [
            f"--output={output_path}",
            f"--to={to_format}",
            f"--resource-path={resources_dir}",
        ],
    )
    if metadata_file_path is not None:
        args.append(f"--metadata-file={metadata_file_path}")
    args.extend(
        _get_lua_filters(pandoc_config.filters, builtin_filters),
    )
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
    config: AppConfig | None = None,
) -> Path:
    """Run prepare and then invoke pandoc to build the final document.

    Returns the path to the generated output file.
    """
    cfg = config if config is not None else default_config()
    pandoc_cfg = cfg.pandoc

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
        raise BuildError(
            f"No markdown (*.md) files found under build directory: {build_path}"
        )

    effective_file_name = file_name or Path.cwd().name
    if not effective_file_name:
        raise BuildError("Could not determine default output file name.")

    # The final document is created in the current working directory.
    output_path = Path.cwd() / f"{effective_file_name}.{to_format}"
    resources_dir = build_path / "resources"

    if not resources_dir.exists() or not resources_dir.is_dir():
        raise BuildError(f"Resources directory does not exist: {resources_dir}")

    metadata_file_path: Path | None = None
    if _should_write_metadata_file(pandoc_cfg.metadata):
        fd, path_str = tempfile.mkstemp(suffix=".yaml", dir=tempfile.gettempdir())
        metadata_file_path = Path(path_str)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                yaml.dump(
                    pandoc_cfg.metadata,
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
        except OSError as exc:
            metadata_file_path.unlink(missing_ok=True)
            raise BuildError(f"Failed to write metadata temp file: {exc}") from exc

    actual_runner = runner or _default_runner

    try:
        pandoc_command = _build_pandoc_args(
                md_files=md_files,
                to_format=to_format,
                output_path=output_path,
                resources_dir=resources_dir,
                pandoc_config=pandoc_cfg,
                builtin_filters=cfg.builtin_filters,
                metadata_file_path=metadata_file_path,
            )
        completed = actual_runner(
            pandoc_command,
        )
    except FileNotFoundError as exc:
        raise BuildError(f"Could not find the `pandoc` executable: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise BuildError(f"Unexpected error while running pandoc: {exc}") from exc
    finally:
        if metadata_file_path is not None and metadata_file_path.exists():
            metadata_file_path.unlink(missing_ok=True)

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

