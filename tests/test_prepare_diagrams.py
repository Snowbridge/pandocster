"""Tests for diagram block processing in run_prepare."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Callable
from unittest.mock import patch

import pytest

from config.schema import AppConfig, DiagramsConfig, DiagramToolConfig, PandocConfig
from service.commands.prepare import PrepareError, run_prepare


def _cfg(
    mmdc_enabled: bool = True,
    gv_enabled: bool = True,
    fmt: str = "svg",
) -> AppConfig:
    return AppConfig(
        pandoc=PandocConfig(bin="pandoc", filters=[], metadata={}, options=[]),
        diagrams=DiagramsConfig(
            mmdc=DiagramToolConfig(enabled=mmdc_enabled, bin="mmdc", options=[], format=fmt),
            graphviz=DiagramToolConfig(enabled=gv_enabled, bin="dot", options=[], format=fmt),
        ),
    )


def _ok_run(cmd, **kwargs):
    """Fake subprocess.run that reports success without executing anything."""
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")


# ---------------------------------------------------------------------------
# Mermaid
# ---------------------------------------------------------------------------


def test_mermaid_block_replaced_with_svg_image(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "doc.md", "# Title\n\n```mermaid\nflowchart TD\n    A --> B\n```\n")

    with patch("service.commands.prepare.subprocess.run", side_effect=_ok_run):
        run_prepare(src, build, _cfg())

    content = (build / "doc.md").read_text(encoding="utf-8")
    assert "```mermaid" not in content
    assert re.search(r"!\[\]\(resources/[0-9a-f-]+\.svg\)", content)


def test_mermaid_block_passes_correct_cli_args(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "doc.md", "```mermaid\nflowchart TD\n    A --> B\n```\n")

    captured: list[list[str]] = []

    def _capture(cmd, **kwargs):
        captured.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("service.commands.prepare.subprocess.run", side_effect=_capture):
        run_prepare(src, build, _cfg())

    assert len(captured) == 1
    cmd = captured[0]
    assert cmd[0] == "mmdc"
    assert "-i" in cmd
    assert "-o" in cmd
    out_path = cmd[cmd.index("-o") + 1]
    assert out_path.endswith(".svg")
    assert "--backgroundColor" in cmd
    assert "transparent" in cmd[cmd.index("--backgroundColor") + 1]


def test_mermaid_block_kept_verbatim_when_disabled(
    tmp_path: Path, write_file: Callable
) -> None:
    """When mmdc is disabled the fenced block is left as-is in the output."""
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "doc.md", "```mermaid\nflowchart TD\n    A --> B\n```\n")

    run_prepare(src, build, _cfg(mmdc_enabled=False))

    content = (build / "doc.md").read_text(encoding="utf-8")
    assert "```mermaid" in content
    assert "flowchart TD" in content


def test_mermaid_cli_failure_raises_prepare_error(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "doc.md", "```mermaid\nflowchart TD\n    A --> B\n```\n")

    def _fail(cmd, **kwargs):
        return subprocess.CompletedProcess(
            args=cmd, returncode=1, stdout="", stderr="parse error"
        )

    with patch("service.commands.prepare.subprocess.run", side_effect=_fail):
        with pytest.raises(PrepareError, match="mmdc failed"):
            run_prepare(src, build, _cfg())


# ---------------------------------------------------------------------------
# Graphviz
# ---------------------------------------------------------------------------


def test_graphviz_block_replaced_with_svg_image(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "doc.md", "# Title\n\n```graphviz\ndigraph G { A -> B }\n```\n")

    with patch("service.commands.prepare.subprocess.run", side_effect=_ok_run):
        run_prepare(src, build, _cfg())

    content = (build / "doc.md").read_text(encoding="utf-8")
    assert "```graphviz" not in content
    assert re.search(r"!\[\]\(resources/[0-9a-f-]+\.svg\)", content)


def test_graphviz_block_passes_correct_cli_args(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "doc.md", "```graphviz\ndigraph G { A -> B }\n```\n")

    captured: list[list[str]] = []

    def _capture(cmd, **kwargs):
        captured.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("service.commands.prepare.subprocess.run", side_effect=_capture):
        run_prepare(src, build, _cfg())

    assert len(captured) == 1
    cmd = captured[0]
    assert cmd[0] == "dot"
    assert "-T" in cmd
    assert cmd[cmd.index("-T") + 1] == "svg"
    assert "-o" in cmd
    out_path = cmd[cmd.index("-o") + 1]
    assert out_path.endswith(".svg")


def test_graphviz_block_kept_verbatim_when_disabled(
    tmp_path: Path, write_file: Callable
) -> None:
    """When dot is disabled the fenced block is left as-is in the output."""
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "doc.md", "```graphviz\ndigraph G { A -> B }\n```\n")

    run_prepare(src, build, _cfg(gv_enabled=False))

    content = (build / "doc.md").read_text(encoding="utf-8")
    assert "```graphviz" in content
    assert "digraph G" in content


def test_graphviz_cli_failure_raises_prepare_error(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "doc.md", "```graphviz\ndigraph G { A -> B }\n```\n")

    def _fail(cmd, **kwargs):
        return subprocess.CompletedProcess(
            args=cmd, returncode=1, stdout="", stderr="syntax error"
        )

    with patch("service.commands.prepare.subprocess.run", side_effect=_fail):
        with pytest.raises(PrepareError, match="dot failed"):
            run_prepare(src, build, _cfg())


# ---------------------------------------------------------------------------
# graphiz alias
# ---------------------------------------------------------------------------


def test_graphiz_typo_fence_also_converted(
    tmp_path: Path, write_file: Callable
) -> None:
    """'```graphiz' (without 'v') is an accepted alias for '```graphviz'."""
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "doc.md", "```graphiz\ndigraph G { A -> B }\n```\n")

    with patch("service.commands.prepare.subprocess.run", side_effect=_ok_run):
        run_prepare(src, build, _cfg(fmt="svg"))

    content = (build / "doc.md").read_text(encoding="utf-8")
    assert "```graphiz" not in content
    assert re.search(r"!\[\]\(resources/[0-9a-f-]+\.svg\)", content)


# ---------------------------------------------------------------------------
# format parameter
# ---------------------------------------------------------------------------


def test_format_parameter_controls_mermaid_output_extension(
    tmp_path: Path, write_file: Callable
) -> None:
    """The format field in DiagramToolConfig determines the output file extension."""
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "doc.md", "```mermaid\nflowchart TD\n    A --> B\n```\n")

    with patch("service.commands.prepare.subprocess.run", side_effect=_ok_run):
        run_prepare(src, build, _cfg(fmt="png"))

    content = (build / "doc.md").read_text(encoding="utf-8")
    assert "```mermaid" not in content
    assert re.search(r"!\[\]\(resources/[0-9a-f-]+\.png\)", content)
    assert not re.search(r"!\[\]\(resources/[0-9a-f-]+\.svg\)", content)


def test_graphviz_format_passed_to_dot_T_flag(
    tmp_path: Path, write_file: Callable
) -> None:
    """-T flag and output path both reflect the configured format."""
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "doc.md", "```graphviz\ndigraph G { A -> B }\n```\n")

    captured: list[list[str]] = []

    def _capture(cmd, **kwargs):
        captured.append(list(cmd))
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("service.commands.prepare.subprocess.run", side_effect=_capture):
        run_prepare(src, build, _cfg(fmt="png"))

    cmd = captured[0]
    assert cmd[cmd.index("-T") + 1] == "png"
    assert cmd[cmd.index("-o") + 1].endswith(".png")
