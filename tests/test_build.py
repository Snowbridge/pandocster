from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

from cli.entrypoint import main
from service.commands.build import BuildError, run_build


def _write(file: Path, content: str) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")


def _completed(args: Any, returncode: int = 0) -> Any:
    class _Result:
        def __init__(self, a: Any, code: int) -> None:
            self.args = a
            self.returncode = code
            self.stdout = ""
            self.stderr = ""

    return _Result(args, returncode)


def test_run_build_invokes_pandoc_with_expected_args(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "src"
    build = tmp_path / "build"

    _write(src / "md" / "01-one" / "_index.md", "# One\n")
    _write(src / "md" / "01-one" / "chapter1.md", "# Chapter 1\n")

    # Create a dummy resources directory that prepare would normally create.
    (build / "resources").mkdir(parents=True, exist_ok=True)

    captured_args: Any = None

    def runner(args: Any) -> Any:
        nonlocal captured_args
        captured_args = list(args)
        return _completed(args)

    output_path = run_build(
        src=src,
        build=build,
        to_format="docx",
        file_name="book",
        preserve_build=True,
        runner=runner,
    )

    # Output file is created in the current working directory (tmp_path).
    assert output_path == Path.cwd() / "book.docx"
    assert captured_args is not None

    # First argument should be the pandoc executable.
    assert captured_args[0] == "pandoc"

    # Output option must target the resolved output path.
    assert f"--output={output_path}" in captured_args

    # Format option must be passed through.
    assert "--to=docx" in captured_args

    # Lua filters must be present; order follows default config (builtin_filters).
    filter_args = [arg for arg in captured_args if arg.startswith("--lua-filter=")]
    filter_names = [Path(arg.split("=", 1)[1]).name for arg in filter_args]
    assert filter_names == [
        "absorb_nonvisual_paragraphs.lua",
        "header_offset.lua",
        "link_anchors.lua",
        "newpage.lua",
    ]


def test_run_build_raises_when_src_equals_build(tmp_path: Path) -> None:
    src = tmp_path / "tree"
    _write(src / "doc.md", "# Doc\n")

    try:
        run_build(
            src=src,
            build=src,
            to_format="docx",
            file_name="doc",
            preserve_build=True,
        )
    except BuildError as exc:
        assert "Source and build directories must not be the same" in str(exc)
    else:  # pragma: no cover - defensive
        assert False, "Expected BuildError to be raised"


def test_run_build_removes_build_when_not_preserved(tmp_path: Path) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"

    _write(src / "md" / "_index.md", "# One\n")
    (build / "resources").mkdir(parents=True, exist_ok=True)

    def runner(args: Any) -> Any:
        return _completed(args)

    run_build(
        src=src,
        build=build,
        to_format="docx",
        file_name="book",
        preserve_build=False,
        runner=runner,
    )

    assert not build.exists()


def test_cli_build_smoke(tmp_path: Path, monkeypatch: object) -> None:
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "src"
    build = tmp_path / "build"

    _write(src / "md" / "_index.md", "# One\n")

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "build",
            str(src),
            str(build),
            "--to",
            "docx",
            "--file-name",
            "book",
            "--preserve-build",
        ],
    )

    # We cannot guarantee pandoc is installed in the test environment,
    # but the command must produce some output (either success or error).
    assert result.output.strip() != ""

