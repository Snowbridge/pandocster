"""Tests for cross-file numerator substitution during prepare."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from config.schema import AppConfig, NumeratorConfig, PandocConfig
from service.commands.prepare import PrepareError, run_prepare


def _cfg(numerators: dict[str, NumeratorConfig] | None = None) -> AppConfig:
    return AppConfig(
        pandoc=PandocConfig(bin="pandoc", filters=[], metadata={}, options=[]),
        numerators=numerators or {},
    )


def _body(path: Path) -> str:
    return "\n".join(path.read_text(encoding="utf-8").splitlines()[2:])


def test_flat_numerators_are_independent(tmp_path: Path, write_file: Callable) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(
        src / "chapter.md",
        "{{#:para}} Lorem ipsum dolor sit amet\n"
        "{{#:para}} Consectetur adipiscing elit\n"
        "{{#}} Sed do eiusmod tempor incididunt\n"
        "{{#:para}} Ut labore et dolore magna aliqua\n"
        "{{#}} Ut enim ad minim veniam\n",
    )

    run_prepare(src, build, _cfg())

    assert _body(build / "chapter.md") == (
        "1. Lorem ipsum dolor sit amet\n"
        "2. Consectetur adipiscing elit\n"
        "1. Sed do eiusmod tempor incididunt\n"
        "3. Ut labore et dolore magna aliqua\n"
        "2. Ut enim ad minim veniam"
    )


def test_named_value_is_reused_across_files(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "a.md", "{{#:para}} One\n{{#:para:foo_bar}} Two\n")
    write_file(src / "b.md", "See {{#=:para:foo_bar}} and {{#:para}}.\n")

    run_prepare(src, build, _cfg())

    assert _body(build / "a.md") == "1. One\n2. Two"
    assert _body(build / "b.md") == "See 2. and 3.."


def test_named_example_keeps_full_rendered_value(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(
        src / "chapter.md",
        "{{#:para}} Lorem ipsum dolor sit amet\n"
        "{{#:para:foo_bar}} Consectetur adipiscing elit\n"
        "{{#::buzz}} Sed do eiusmod tempor incididunt\n"
        "{{#:para}} Ut labore et dolore magna aliqua\n"
        "{{#}} Ut enim ad {{#=::buzz}} minim veniam {{#=:para:foo_bar}}\n",
    )

    run_prepare(src, build, _cfg())

    assert _body(build / "chapter.md") == (
        "1. Lorem ipsum dolor sit amet\n"
        "2. Consectetur adipiscing elit\n"
        "1. Sed do eiusmod tempor incididunt\n"
        "3. Ut labore et dolore magna aliqua\n"
        "2. Ut enim ad 1. minim veniam 2."
    )


def test_hierarchical_numbering_follows_visual_headings(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(
        src / "chapter.md",
        "# {{##:h}} Lorem ipsum dolor sit amet, consectetur\n"
        "## {{##:h}} adipiscing elit, sed do eiusmod tempor\n"
        "{{##:h}} incididunt ut labore et dolore\n"
        "{{##:h}} magna aliqua. Ut enim ad\n"
        "## {{##:h}} minim veniam, quis nostrud\n"
        "{{##:h}} exercitation ullamco laboris nisi\n"
        "{{##:h}} ut aliquip ex ea commodo consequat\n",
    )

    run_prepare(src, build, _cfg())

    assert _body(build / "chapter.md") == (
        "# 1. Lorem ipsum dolor sit amet, consectetur\n"
        "## 1.1. adipiscing elit, sed do eiusmod tempor\n"
        "1.1.1. incididunt ut labore et dolore\n"
        "1.1.2. magna aliqua. Ut enim ad\n"
        "## 1.2. minim veniam, quis nostrud\n"
        "1.2.1. exercitation ullamco laboris nisi\n"
        "1.2.2. ut aliquip ex ea commodo consequat"
    )


def test_missing_heading_level_is_filled_with_one(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(
        src / "chapter.md",
        "# {{##:h}} Root\n### {{##:h}} Skipped\n",
    )

    run_prepare(src, build, _cfg())

    assert "# 1. Root" in _body(build / "chapter.md")
    assert "### 1.1.1. Skipped" in _body(build / "chapter.md")


def test_body_and_heading_share_a_counter(tmp_path: Path, write_file: Callable) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(
        src / "chapter.md",
        "# {{##:h}} Root\n{{##:h}} Body\n## {{##:h}} Next\n",
    )

    run_prepare(src, build, _cfg())

    body = _body(build / "chapter.md")
    assert "1.1. Body" in body
    assert "## 1.2. Next" in body


def test_index_file_is_numbered_before_its_sibling(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "section" / "a.md", "# {{##:h}} Sibling\n")
    write_file(src / "section" / "_index.md", "# {{##:h}} Section\n")

    run_prepare(src, build, _cfg())

    assert _body(build / "section" / "_index.md") == "# 1. Section"
    assert _body(build / "section" / "a.md") == "# 1.1. Sibling"


def test_setext_heading_is_a_parent(tmp_path: Path, write_file: Callable) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(
        src / "chapter.md",
        "{{##:h}} Title\n===\n{{##:h}} Body\n",
    )

    run_prepare(src, build, _cfg())

    assert _body(build / "chapter.md") == "1. Title\n===\n1.1. Body"


def test_heading_inside_blockquote_is_text(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "chapter.md", "> # {{##:h}} Quoted\n{{##:h}} Body\n")

    run_prepare(src, build, _cfg())

    assert _body(build / "chapter.md") == "> # 1. Quoted\n2. Body"


def test_code_fences_and_escapes_are_left_literal(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(
        src / "chapter.md",
        "Use {{#}} but not `{{#}}`.\n"
        "\n"
        "```\n"
        "{{#}}\n"
        "```\n"
        "\n"
        r"Keep \{{#}} and use {{#}}."
        "\n",
    )

    run_prepare(src, build, _cfg())

    body = _body(build / "chapter.md")
    assert "Use 1. but not `{{#}}`." in body
    assert "\n{{#}}\n" in body
    assert r"Keep \{{#}} and use 2.." in body


def test_variable_value_is_not_scanned_for_numerators(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "chapter.md", "{{token}}\n")

    run_prepare(
        src,
        build,
        AppConfig(
            pandoc=PandocConfig(bin="pandoc", filters=[], metadata={}, options=[]),
            variables={"token": "{{#:para}}"},
        ),
    )

    assert _body(build / "chapter.md") == "{{#:para}}"


def test_config_formats_the_rendered_number(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "chapter.md", "# {{##:h}} Root\n## {{##:h}} Child\n")

    run_prepare(
        src,
        build,
        _cfg({"h": NumeratorConfig(suffix="", start=5, delimiter="-")}),
    )

    body = _body(build / "chapter.md")
    assert "# 5 Root" in body
    assert "## 5-1 Child" in body


def test_unknown_numerator_uses_defaults(tmp_path: Path, write_file: Callable) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "chapter.md", "{{#:fresh}} Item\n")

    run_prepare(src, build, _cfg())

    assert _body(build / "chapter.md") == "1. Item"


def test_mixed_kind_raises(tmp_path: Path, write_file: Callable) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "chapter.md", "{{#:h}} Flat\n{{##:h}} Hierarchical\n")

    with pytest.raises(PrepareError, match=r"h.*chapter\.md:2"):
        run_prepare(src, build, _cfg())


def test_reference_before_generator_uses_later_number(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "222.md", "See {{##=::_343}} first.\n{{##::_328}} Here.\n")
    write_file(src / "444.md", "{{##::_343}} Later.\nSee {{##=::_328}} back.\n")

    run_prepare(src, build, _cfg())

    assert _body(build / "222.md") == "See 2. first.\n1. Here."
    assert _body(build / "444.md") == "2. Later.\nSee 1. back."


def test_repeated_generator_raises(tmp_path: Path, write_file: Callable) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "chapter.md", "{{#:para:item}} One\n{{#:para:item}} Two\n")

    with pytest.raises(PrepareError, match=r"item.*chapter\.md:2"):
        run_prepare(src, build, _cfg())


def test_reference_without_generator_raises(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "chapter.md", "See {{#=:para:missing}}.\n")

    with pytest.raises(PrepareError, match=r"missing.*chapter\.md:1"):
        run_prepare(src, build, _cfg())


def test_reference_in_code_is_left_literal(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "chapter.md", "See `{{#=:para:item}}` and {{#:para:item}}.\n")

    run_prepare(src, build, _cfg())

    assert _body(build / "chapter.md") == "See `{{#=:para:item}}` and 1.."


def test_reference_does_not_open_heading(tmp_path: Path, write_file: Callable) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(
        src / "chapter.md",
        "# {{##:h:root}} Root\n## {{##=:h:root}} Repeated heading\n{{##:h}} Body\n",
    )

    run_prepare(src, build, _cfg())

    body = _body(build / "chapter.md")
    assert "# 1. Root" in body
    assert "## 1. Repeated heading" in body
    assert "1.1. Body" in body


def test_hyphen_in_value_id_is_not_a_numerator(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "chapter.md", "Before {{#:para:foo-bar}} after\n")

    run_prepare(src, build, _cfg())

    assert _body(build / "chapter.md") == "Before {{#:para:foo-bar}} after"


def test_reflinks_file_is_not_numbered(
    tmp_path: Path, write_file: Callable, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    write_file(src / "999-reflinks.md", "{{#}} Skip\n")
    write_file(src / "chapter.md", "{{#}} Keep\n[missing]: missing.md\n")
    monkeypatch.setattr(
        "service.commands.prepare._write_reflinks_file",
        lambda root_level, reflinks: None,
    )

    run_prepare(src, build, _cfg())

    assert "{{#}} Skip" in (build / "999-reflinks.md").read_text(encoding="utf-8")
    assert _body(build / "chapter.md") == "1. Keep"
