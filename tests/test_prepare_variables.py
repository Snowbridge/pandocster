"""Tests for {{variable}} substitution during prepare."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pytest

from config.schema import AppConfig, PandocConfig
from service.commands.prepare import PrepareError, run_prepare


def _cfg(variables: dict[str, Any]) -> AppConfig:
    return AppConfig(
        pandoc=PandocConfig(bin="pandoc", filters=[], metadata={}, options=[]),
        variables=variables,
    )


def _prepared_body(tmp_path: Path, source: str, variables: dict[str, Any]) -> str:
    src = tmp_path / "src"
    build = tmp_path / "build"
    (src).mkdir()
    (src / "chapter.md").write_text(source, encoding="utf-8")
    run_prepare(src, build, _cfg(variables))
    lines = (build / "chapter.md").read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[2:])


def test_substitutes_scalar_list_and_mapping(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    source = "# {{ product }}\n\nYear {{year}}, draft {{draft}}.\n\n{{ authors }}\n"
    write_file(src / "chapter.md", source)

    run_prepare(
        src,
        build,
        _cfg(
            {
                "product": "Pandocster",
                "year": 2026,
                "draft": True,
                "authors": ["Анна", "Борис"],
            }
        ),
    )

    assert (src / "chapter.md").read_text(encoding="utf-8") == source
    body = (build / "chapter.md").read_text(encoding="utf-8")
    assert "# Pandocster" in body
    assert "Year 2026, draft true." in body
    assert "- Анна" in body
    assert "- Борис" in body


def test_spaced_placeholder_matches_trimmed_name(tmp_path: Path) -> None:
    body = _prepared_body(tmp_path, "See {{ name }}.\n", {"name": "Pandocster"})
    assert body == "See Pandocster."


def test_unknown_variable_raises_with_file_and_line(tmp_path: Path) -> None:
    src = tmp_path / "src"
    (src).mkdir()
    (src / "chapter.md").write_text("ok\n{{ missing }}\n", encoding="utf-8")

    with pytest.raises(PrepareError, match=r"missing.*chapter\.md:2"):
        run_prepare(src, tmp_path / "build", _cfg({}))


def test_escaped_placeholder_stays_literal(tmp_path: Path) -> None:
    body = _prepared_body(
        tmp_path,
        r"Keep \{{name}} and use {{name}}." "\n",
        {"name": "Pandocster"},
    )
    assert body == r"Keep \{{name}} and use Pandocster."


def test_skips_inline_code_and_fenced_blocks(tmp_path: Path) -> None:
    source = (
        "Use {{name}} but not `{{name}}`.\n"
        "\n"
        "```\n"
        "{{name}}\n"
        "```\n"
        "\n"
        "```mermaid\n"
        "{{name}}\n"
        "```\n"
        "\n"
        "After {{name}}.\n"
    )
    body = _prepared_body(tmp_path, source, {"name": "Pandocster"})
    assert "Use Pandocster but not `{{name}}`." in body
    assert "\n{{name}}\n" in body
    assert "After Pandocster." in body


def test_empty_variables_leave_text_without_placeholders(tmp_path: Path) -> None:
    body = _prepared_body(tmp_path, "Plain text.\n", {})
    assert body == "Plain text."
