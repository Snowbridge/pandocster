from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from cli.entrypoint import main
from service.commands.prepare import MarkdownFile, _build_file_anchor, find_root_level, iter_markdown_files, process_markdown_file


def _write(file: Path, content: str) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")


def test_find_root_level_picks_first_dir_with_md(tmp_path: Path) -> None:
    src = tmp_path / "src"
    (src / "a" / "nested").mkdir(parents=True)
    (src / "b").mkdir()

    _write(src / "a" / "nested" / "file.md", "# A")
    _write(src / "b" / "file.md", "# B")

    root = find_root_level(src)

    # ROOT_LEVEL is the parent that groups markdown sections.
    # First directory with a markdown file is src/a/nested, so ROOT_LEVEL is src/a.
    assert root == src / "a"


def test_iter_markdown_files_levels(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _write(root / "_index.md", "# Root")
    _write(root / "section" / "_index.md", "# Section")
    _write(root / "section" / "chapter" / "intro.md", "# Intro")

    files = list(iter_markdown_files(root))
    paths_and_levels = {(f.path.relative_to(root).as_posix(), f.current_level) for f in files}

    assert ("_index.md", 1) in paths_and_levels
    assert ("section/_index.md", 2) in paths_and_levels
    assert ("section/chapter/intro.md", 3) in paths_and_levels


def test_build_file_anchor_uses_relative_path(tmp_path: Path) -> None:
    root = tmp_path / "root"
    file_path = root / "section" / "chapter" / "intro.md"

    anchor = _build_file_anchor(file_path.relative_to(root))

    assert anchor == "section_chapter_intro.md"


def test_process_markdown_file_injects_header_and_anchor(tmp_path: Path) -> None:
    root = tmp_path / "root"
    resources = root / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    file_path = root / "section" / "chapter" / "intro.md"
    _write(file_path, "# Title\n\nContent\n")

    process_markdown_file(file_path, current_level=2, root_level=root, resources_dir=resources)

    content = file_path.read_text(encoding="utf-8").splitlines()

    assert content[0] == "<!-- @header-offset: 3 -->"
    # Anchor is placed on a separate line before the first heading.
    assert content[1] == '<!-- @anchor="section_chapter_intro.md" -->'
    assert content[2] == "# Title"
    assert "Content" in content[4]


def test_prepare_command_does_not_mutate_src(tmp_path: Path, monkeypatch: object) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"

    _write(src / "book" / "_index.md", "# Root\n")
    _write(src / "book" / "chapter1.md", "# Chapter 1\n")

    runner = CliRunner()
    result = runner.invoke(main, ["prepare", str(src), str(build)])

    assert result.exit_code == 0

    # src files must remain untouched
    assert (src / "book" / "_index.md").read_text(encoding="utf-8") == "# Root\n"
    assert (src / "book" / "chapter1.md").read_text(encoding="utf-8") == "# Chapter 1\n"

    # build files must exist and be processed
    root_level = find_root_level(build)
    processed_index = (build / "book" / "_index.md").read_text(encoding="utf-8")
    processed_chapter = (build / "book" / "chapter1.md").read_text(encoding="utf-8")

    # ROOT_LEVEL is build, so build/book has CURRENT_LEVEL = 2:
    # - _index.md → LEVEL = CURRENT_LEVEL = 2
    # - chapter1.md → LEVEL = CURRENT_LEVEL + 1 = 3
    assert "<!-- @header-offset: 2 -->" in processed_index.splitlines()[0]
    assert "<!-- @header-offset: 3 -->" in processed_chapter.splitlines()[0]


def test_find_root_level_for_md_tree(tmp_path: Path) -> None:
    build = tmp_path / "build"
    _write(build / "md" / "01-the-problem" / "_index.md", "# Problem\n")
    _write(build / "md" / "02-stakeholders" / "_index.md", "# Stakeholders\n")

    root = find_root_level(build)

    # ROOT_LEVEL should be the common md directory that groups sections
    assert root == build / "md"


def test_anchor_after_first_heading_with_leading_text(tmp_path: Path) -> None:
    root = tmp_path / "root"
    resources = root / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    file_path = root / "doc.md"
    _write(
        file_path,
        "// comment\n"
        "\n"
        "# Heading 1\n"
        "Intro text\n",
    )

    process_markdown_file(file_path, current_level=1, root_level=root, resources_dir=resources)

    lines = file_path.read_text(encoding="utf-8").splitlines()

    assert lines[0].startswith("<!-- @header-offset: ")
    # First heading should remain, anchor goes on its own line before it.
    assert lines[3].startswith("<!-- @anchor=")
    assert lines[4].startswith("# Heading 1")


def test_anchor_stays_second_line_when_no_heading(tmp_path: Path) -> None:
    root = tmp_path / "root"
    resources = root / "resources"
    resources.mkdir(parents=True, exist_ok=True)
    file_path = root / "plain.md"
    _write(file_path, "Just text\nWithout headings\n")

    process_markdown_file(file_path, current_level=1, root_level=root, resources_dir=resources)

    lines = file_path.read_text(encoding="utf-8").splitlines()

    assert lines[0].startswith("<!-- @header-offset: ")
    assert lines[1].startswith("<!-- @anchor=")
    assert "Just text" in lines[2]

