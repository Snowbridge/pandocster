from __future__ import annotations

from pathlib import Path
from typing import Callable

from service.commands.prepare import run_prepare


def test_prepare_copies_local_images_and_rewrites_links(
    tmp_path: Path, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"

    img_rel = Path("images") / "fig" / "diagram.png"
    write_file(src / "md" / "01-one" / "doc.md", "![Diagram](images/fig/diagram.png)\n")
    write_file(src / "md" / "01-one" / img_rel, "binary", binary=True)

    run_prepare(src, build)

    # Resources directory should contain the image with preserved structure.
    resources_img = build / "resources" / "md" / "01-one" / img_rel
    assert resources_img.exists()

    # Link in processed markdown should be rewritten to path relative to resources/.
    processed = (build / "md" / "01-one" / "doc.md").read_text(encoding="utf-8")
    # Image now lives in build/resources/md/01-one/images/fig/diagram.png,
    # so the path inside markdown is relative to build/resources.
    assert "![Diagram](md/01-one/images/fig/diagram.png)" in processed.splitlines()


def test_prepare_ignores_url_images(tmp_path: Path, write_file: Callable) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"

    write_file(
        src / "md" / "doc.md",
        "![Remote](https://example.com/image.png)\n",
    )

    run_prepare(src, build)

    processed = (build / "md" / "doc.md").read_text(encoding="utf-8")
    assert "![Remote](https://example.com/image.png)" in processed.splitlines()


def test_prepare_warns_and_keeps_image_outside_root(
    tmp_path: Path, capsys: object, write_file: Callable
) -> None:
    src = tmp_path / "src"
    build = tmp_path / "build"

    external_img = tmp_path / "image.png"
    write_file(external_img, "binary", binary=True)

    write_file(
        src / "md" / "doc.md",
        "![Ext](../image.png)\n",
    )

    run_prepare(src, build)

    # Link should remain unchanged.
    processed = (build / "md" / "doc.md").read_text(encoding="utf-8")
    assert "![Ext](../image.png)" in processed.splitlines()

