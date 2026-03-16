"""Implementation of the `build` command logic for pandocster."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable

import yaml

from config.schema import AppConfig, PandocConfig, default_config
from service.markdown_walker import walk_markdown_files
from service.subprocess_runner import Runner, _default_runner

from .prepare import PrepareError, run_prepare


class BuildError(RuntimeError):
    """User-facing errors for the `build` command."""


def _iter_markdown_files(build: Path) -> list[Path]:
    """Collect all markdown files under the build directory, sorted by path.

    Within each directory, _index.md comes first; otherwise lexicographic order.
    """
    files = [path for path, _ in walk_markdown_files(build)]

    def _sort_key(path: Path) -> tuple[str, int, str]:
        rel = path.relative_to(build)
        parent = rel.parent.as_posix()
        is_index = 0 if rel.name == "_index.md" else 1
        return parent, is_index, rel.name

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
    metadata_file_path: Path | None = None,
) -> list[str]:
    args: list[str] = [pandoc_config.bin]
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
    if pandoc_config.filters:
        for filter_path in pandoc_config.filters:
            args.append(f"--lua-filter={filter_path}")
    return args


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

    if src == build:
        raise BuildError("Source and build directories must not be the same.")

    try:
        run_prepare(src, build, cfg)
    except PrepareError as exc:
        raise BuildError(str(exc)) from exc

    md_files = _iter_markdown_files(build)
    if not md_files:
        raise BuildError(
            f"No markdown (*.md) files found under build directory: {build}"
        )

    effective_file_name = file_name or Path.cwd().name
    if not effective_file_name:
        raise BuildError("Could not determine default output file name.")

    output_path = Path.cwd() / f"{effective_file_name}.{to_format}"
    resources_dir = build / "resources"

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
            shutil.rmtree(build)
        except OSError as exc:
            raise BuildError(f"Failed to remove build directory: {exc}") from exc

    return output_path

