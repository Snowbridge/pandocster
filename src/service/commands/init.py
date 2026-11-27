"""Implementation of the `init` command logic for pandocster."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import yaml

from config import config_to_dict, load_config
from service.command_log import log_file as command_log_file

_GENERATE_SH_CONTENT = """\
#!/usr/bin/env bash
pandocster build src/ --to docx -p
pandocster build src/ --to epub --prepared -p
pandocster build src/ --to html --prepared
"""

_SRC_SUBDIRS = ("src/md", "src/assets", "src/templates")

_AGENT_TEMPLATE_FILES = (
    ("init_templates/AGENTS.md", "AGENTS.md"),
    (
        "init_templates/skills/pandocster-markdown/SKILL.md",
        ".agents/skills/pandocster-markdown/SKILL.md",
    ),
)


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
        command_log_file(config_path, "created")
    except OSError as exc:
        raise InitError(f"Failed to write config file: {exc}") from exc


def _create_src_dirs(target_dir: Path) -> None:
    """Create src/md, src/assets, src/templates with .gitkeep inside each."""
    for subdir in _SRC_SUBDIRS:
        dir_path = target_dir / subdir
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            gitkeep = dir_path / ".gitkeep"
            gitkeep.touch()
            command_log_file(gitkeep, "created")
        except OSError as exc:
            raise InitError(f"Failed to create directory '{dir_path}': {exc}") from exc


def _create_generate_script(target_dir: Path) -> None:
    """Write generate.sh that runs pandocster build."""
    script_path = target_dir / "generate.sh"
    try:
        script_path.write_text(_GENERATE_SH_CONTENT, encoding="utf-8")
        command_log_file(script_path, "created")
    except OSError as exc:
        raise InitError(f"Failed to write generate.sh: {exc}") from exc


def _write_agent_instructions(target_dir: Path) -> None:
    """Write AGENTS.md and the pandocster-markdown skill, replacing both."""
    templates = resources.files("pandocster")
    for resource_name, relative_path in _AGENT_TEMPLATE_FILES:
        destination = target_dir / relative_path
        try:
            content = (templates / resource_name).read_text(encoding="utf-8")
            destination.parent.mkdir(parents=True, exist_ok=True)
            existed = destination.exists()
            destination.write_text(content, encoding="utf-8")
            command_log_file(destination, "modified" if existed else "created")
        except OSError as exc:
            raise InitError(
                f"Failed to write agent instructions '{destination}': {exc}"
            ) from exc


def run_init(target_dir: Path, force: bool = False, agents: bool = False) -> None:
    """Scaffold a pandocster project directory.

    Creates pandocster.yaml, src/md, src/assets, src/templates, generate.sh,
    AGENTS.md, and the pandocster-markdown skill. Raises InitError if the
    directory is non-empty and force is False.

    With agents=True, only the agent instruction files are written or replaced.
    An existing project is left otherwise untouched, and force is not required.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    if agents:
        _write_agent_instructions(target_dir)
        return
    _check_dir_empty(target_dir, force)
    _create_config_file(target_dir)
    _create_src_dirs(target_dir)
    _create_generate_script(target_dir)
    _write_agent_instructions(target_dir)
