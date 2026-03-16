from __future__ import annotations

from pathlib import Path
from typing import Callable

from click.testing import CliRunner

from cli.entrypoint import main
from service.commands.prepare import (
    _build_file_anchor,
    find_root_level,
    iter_markdown_files,
    run_prepare,
)


def test_find_root_level_picks_first_dir_with_md(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    (src / "a" / "nested").mkdir(parents=True)
    (src / "b").mkdir()

    write_file(src / "a" / "nested" / "file.md", "# A")
    write_file(src / "b" / "file.md", "# B")

    root = find_root_level(src)

    # ROOT_LEVEL is the parent that groups markdown sections.
    # First directory with a markdown file is src/a/nested, so ROOT_LEVEL is src/a.
    assert root == src / "a"


def test_iter_markdown_files_levels(tmp_path: Path, write_file: Callable) -> None:
    root = tmp_path / "root"
    write_file(root / "_index.md", "# Root")
    write_file(root / "section" / "_index.md", "# Section")
    write_file(root / "section" / "chapter" / "intro.md", "# Intro")

    files = list(iter_markdown_files(root))
    paths_and_levels = {
        (f.path.relative_to(root).as_posix(), f.current_level) for f in files
    }

    assert ("_index.md", 1) in paths_and_levels
    assert ("section/_index.md", 2) in paths_and_levels
    assert ("section/chapter/intro.md", 3) in paths_and_levels


def test_build_file_anchor_resolves_md_target(tmp_path: Path) -> None:
    root = tmp_path / "root"
    source = root / "other" / "doc.md"
    target_file = root / "section" / "chapter" / "intro.md"
    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.touch()

    anchor = _build_file_anchor("../section/chapter/intro.md", source, root)

    assert anchor == "section_chapter_intro.md"


def test_run_prepare_injects_header_and_anchor(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    # ROOT_LEVEL = build; chapter/intro.md has current_level=2, so header-offset=3.
    write_file(src / "chapter" / "intro.md", "# Title\n\nContent\n")

    run_prepare(src, build)

    content = (build / "chapter" / "intro.md").read_text(encoding="utf-8").splitlines()

    assert content[0] == "<!-- @header-offset: 3 -->"
    # Anchor is placed on a separate line before the first heading.
    assert content[1] == '<!-- @anchor="chapter_intro.md" -->'
    assert content[2] == "# Title"
    assert "Content" in content[4]


def test_prepare_command_does_not_mutate_src(
    tmp_path: Path, monkeypatch: object, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"

    write_file(src / "book" / "_index.md", "# Root\n")
    write_file(src / "book" / "chapter1.md", "# Chapter 1\n")

    runner = CliRunner()
    result = runner.invoke(main, ["prepare", str(src), str(build)])

    assert result.exit_code == 0

    # src files must remain untouched
    assert (src / "book" / "_index.md").read_text(encoding="utf-8") == "# Root\n"
    assert (src / "book" / "chapter1.md").read_text(encoding="utf-8") == "# Chapter 1\n"

    # build files must exist and be processed
    processed_index = (build / "book" / "_index.md").read_text(encoding="utf-8")
    processed_chapter = (build / "book" / "chapter1.md").read_text(encoding="utf-8")

    # ROOT_LEVEL is build, so build/book has CURRENT_LEVEL = 2:
    # - _index.md → LEVEL = CURRENT_LEVEL = 2
    # - chapter1.md → LEVEL = CURRENT_LEVEL + 1 = 3
    assert "<!-- @header-offset: 2 -->" in processed_index.splitlines()[0]
    assert "<!-- @header-offset: 3 -->" in processed_chapter.splitlines()[0]


def test_find_root_level_for_md_tree(tmp_path: Path, write_file: Callable) -> None:
    build = tmp_path / "build"
    write_file(build / "md" / "01-the-problem" / "_index.md", "# Problem\n")
    write_file(build / "md" / "02-stakeholders" / "_index.md", "# Stakeholders\n")

    root = find_root_level(build)

    # ROOT_LEVEL should be the common md directory that groups sections
    assert root == build / "md"


def test_anchor_stays_second_line_when_no_heading(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"
    # File directly in src → ROOT_LEVEL = build, current_level = 1.
    write_file(src / "plain.md", "Just text\nWithout headings\n")

    run_prepare(src, build)

    lines = (build / "plain.md").read_text(encoding="utf-8").splitlines()

    assert lines[0].startswith("<!-- @header-offset: ")
    assert lines[1].startswith("<!-- @anchor=")
    assert "Just text" in lines[2]

