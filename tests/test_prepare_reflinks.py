from __future__ import annotations

from pathlib import Path

from service.commands.prepare import find_root_level, run_prepare


def _write(file: Path, content: str) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")


def test_run_prepare_collects_md_reflinks_into_999_file(tmp_path: Path) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"

    # Layout similar to real project: md tree grouped under md/.
    _write(src / "md" / "01-one" / "_index.md", "# One\n")
    _write(src / "md" / "01-one" / "two.md", "# Two\n")

    _write(
        src / "md" / "02-section" / "ref.md",
        "See [Two][two]\n\n"
        "[two]: ../01-one/two.md\n"
        "[web]: https://example.com\n",
    )

    run_prepare(src, build)

    # During prepare, ROOT_LEVEL is computed before reflinks are written.
    # With this layout, that logical root is build / "md", so the reflinks
    # file is expected there.
    reflinks_path = build / "md" / "999-reflinks.md"
    assert reflinks_path.exists()

    reflinks_content = reflinks_path.read_text(encoding="utf-8").splitlines()

    # Relative link to two.md must be converted to a global anchor based on ROOT_LEVEL.
    # ROOT_LEVEL is build / "md", so the anchor is derived from the path
    # "01-one/two.md" -> "01-one_two.md".
    assert "[two]: #01-one_two.md" in reflinks_content

    # Non-md reference links should not be moved into 999-reflinks.md.
    assert not any(line.startswith("[web]:") for line in reflinks_content)

    # In the processed markdown file, the md reflink definition must be removed,
    # but other reference definitions must remain.
    processed_ref = (build / "md" / "02-section" / "ref.md").read_text(
        encoding="utf-8"
    ).splitlines()

    assert "See [Two][two]" in processed_ref
    assert not any(line.startswith("[two]:") for line in processed_ref)
    assert any(line.startswith("[web]:") for line in processed_ref)

