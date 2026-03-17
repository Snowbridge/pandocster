"""Implementation of the `init` command logic for pandocster."""

from __future__ import annotations

from pathlib import Path

import yaml

from config import config_to_dict, load_config

_GENERATE_SH_CONTENT = """\
#!/usr/bin/env bash
pandocster build src/ --to docx -p
pandocster build src/ --to epub --prepared -p
pandocster build src/ --to html --prepared
"""

_SRC_SUBDIRS = ("src/md", "src/assets", "src/templates")


class InitError(RuntimeError):
    """User-facing errors for the `init` command."""


def _check_dir_empty(target_dir: Path, force: bool) -> None:
    """Raise InitError if target_dir is non-empty and force is False."""
    if target_dir.exists() and any(target_dir.iterdir()):
        if not force:
            raise InitError(
                f"Directory '{target_dir}' is not empty. "
                "Pass --force to initialize it anyway."
            )


def _create_config_file(target_dir: Path) -> None:
    """Write pandocster.yaml with default config into target_dir."""
    cfg = load_config(target_dir)
    data = config_to_dict(cfg)
    yaml_str = yaml.dump(
        data, allow_unicode=True, default_flow_style=False, sort_keys=False
    )
    config_path = target_dir / "pandocster.yaml"
    try:
        config_path.write_text(yaml_str, encoding="utf-8")
    except OSError as exc:
        raise InitError(f"Failed to write config file: {exc}") from exc


def _create_src_dirs(target_dir: Path) -> None:
    """Create src/md, src/assets, src/templates with .gitkeep inside each."""
    for subdir in _SRC_SUBDIRS:
        dir_path = target_dir / subdir
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            (dir_path / ".gitkeep").touch()
        except OSError as exc:
            raise InitError(f"Failed to create directory '{dir_path}': {exc}") from exc


def _create_generate_script(target_dir: Path) -> None:
    """Write generate.sh that runs pandocster build."""
    script_path = target_dir / "generate.sh"
    try:
        script_path.write_text(_GENERATE_SH_CONTENT, encoding="utf-8")
    except OSError as exc:
        raise InitError(f"Failed to write generate.sh: {exc}") from exc


def run_init(target_dir: Path, force: bool = False) -> None:
    """Scaffold a pandocster project directory.

    Creates pandocster.yaml, src/md, src/assets, src/templates, and generate.sh.
    Raises InitError if the directory is non-empty and force is False.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    _check_dir_empty(target_dir, force)
    _create_config_file(target_dir)
    _create_src_dirs(target_dir)
    _create_generate_script(target_dir)
