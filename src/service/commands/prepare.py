"""Implementation of the `prepare` command logic for pandocster."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

from config.schema import AppConfig, DiagramToolConfig

from service.markdown_walker import walk_markdown_files
from service.subprocess_runner import _SHELL


class PrepareError(RuntimeError):
    """User-facing errors for the `prepare` command."""


@dataclass(frozen=True)
class MarkdownFile:
    """Descriptor of a markdown file to be processed."""

    path: Path
    current_level: int


@dataclass(frozen=True)
class ReflinkDefinition:
    """Normalized reference-style link to another markdown file."""

    label: str
    anchor: str

def run_prepare(src: Path, build: Path, cfg: AppConfig | None = None) -> None:
    """Orchestrate the prepare operation."""
    from config import default_config

    _cfg = cfg if cfg is not None else default_config()
    diagrams = _cfg.diagrams

    mermaid_is_enabled = diagrams is not None and diagrams.mmdc is not None and diagrams.mmdc.enabled
    graphviz_is_enabled = diagrams is not None and diagrams.graphviz is not None and diagrams.graphviz.enabled

    src_resolved = src.resolve()
    build_resolved = build.resolve()

    _validate_paths(src_resolved, build_resolved)
    prepare_build_directory(build_resolved)
    copy_src_to_build(src_resolved, build_resolved)

    resources_dir = _ensure_resources_dir(build_resolved)

    root_level = find_root_level(build_resolved)
    reflinks: list[ReflinkDefinition] = []

    for md_file in iter_markdown_files(root_level):
        path = md_file.path
        current_level = md_file.current_level

        try:
            original_content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise PrepareError(f"Failed to read markdown file {path}: {exc}") from exc

        level = _compute_header_level(path, current_level)
        relative = path.relative_to(root_level)
        file_anchor = "_".join(relative.parts)

        header_line = f"<!-- @header-offset: {level} -->"
        anchor_line = f'<!-- @anchor="{file_anchor}" -->'

        lines_list = (
            original_content.splitlines(keepends=False) if original_content else []
        )
        new_content: list[str] = [
            header_line,
            anchor_line,
        ]

        lines_iter = iter(lines_list)
        for line in lines_iter:
            reflink = _match_reflink(line, path, root_level)
            if reflink is not None:
                reflinks.append(reflink)
                continue

            if line == "```mermaid" and mermaid_is_enabled:
                new_content.append(
                    _generate_mermaid(
                        _collect_fenced_block(lines_iter), resources_dir, diagrams.mmdc
                    )
                )
                continue

            if line in ("```graphviz", "```graphiz") and graphviz_is_enabled:
                new_content.append(
                    _generate_graphviz(
                        _collect_fenced_block(lines_iter), resources_dir, diagrams.graphviz
                    )
                )
                continue

            if _IMAGE_PATTERN.search(line):
                line = _process_image_line(line, path, resources_dir)

            new_content.append(line)

        try:
            path.write_text("\n".join(new_content), encoding="utf-8")
        except OSError as exc:
            raise PrepareError(f"Failed to write markdown file {path}: {exc}") from exc

    _write_reflinks_file(root_level, reflinks)



def _validate_paths(src: Path, build: Path) -> None:
    if not src.exists():
        raise PrepareError(f"Source directory does not exist: {src}")
    if not src.is_dir():
        raise PrepareError(f"Source path is not a directory: {src}")

    if src == build:
        raise PrepareError("Source and build directories must not be the same.")

    # Ensure src and build trees do not overlap in any way.
    if _is_subpath(build, src) or _is_subpath(src, build):
        raise PrepareError("Source and build directories must not overlap.")


def _is_subpath(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def prepare_build_directory(build: Path) -> None:
    """Create or clean the build directory without touching its parents."""
    try:
        if not build.exists():
            build.mkdir(parents=True, exist_ok=True)
            return

        if not build.is_dir():
            raise PrepareError(f"Build path exists and is not a directory: {build}")

        for entry in build.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
    except OSError as exc:
        raise PrepareError(f"Failed to prepare build directory: {exc}") from exc


def _ensure_resources_dir(build: Path) -> Path:
    """Create or validate the resources directory under build."""
    resources_dir = build / "resources"

    if resources_dir.exists() and not resources_dir.is_dir():
        raise PrepareError(
            f"Resources path exists and is not a directory: {resources_dir}",
        )

    if not resources_dir.exists():
        try:
            resources_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PrepareError(
                f"Failed to create resources directory: {exc}",
            ) from exc
    else:
        print(
            "[pandocster] Warning: resources directory already exists: "
            f"{resources_dir}"
        )

    return resources_dir


def copy_src_to_build(src: Path, build: Path) -> None:
    """Copy the full contents of src into build, preserving structure."""
    try:
        for root, dirnames, filenames in os.walk(src):
            root_path = Path(root)
            rel_root = root_path.relative_to(src)
            dest_root = build / rel_root
            dest_root.mkdir(parents=True, exist_ok=True)

            dirnames.sort()
            filenames.sort()

            for dirname in dirnames:
                (dest_root / dirname).mkdir(exist_ok=True)

            for filename in filenames:
                src_file = root_path / filename
                dest_file = dest_root / filename
                shutil.copy2(src_file, dest_file)
    except OSError as exc:
        raise PrepareError(f"Failed to copy files from src to build: {exc}") from exc


def find_root_level(build: Path) -> Path:
    """Find the logical ROOT_LEVEL for markdown processing.

    ROOT_LEVEL is defined as the parent directory that groups all markdown
    sections. Technically, it is:
    - the build directory itself, if it already contains at least one *.md, or
    - the parent of the first directory that contains a *.md file.
    """
    for root, dirnames, filenames in os.walk(build):
        dirnames.sort()
        filenames.sort()

        if _has_markdown_file(filenames):
            md_dir = Path(root)
            if md_dir == build:
                return build
            return md_dir.parent

    raise PrepareError(
        f"No markdown (*.md) files found under build directory: {build}",
    )


def _has_markdown_file(filenames: Iterable[str]) -> bool:
    return any(name.lower().endswith(".md") for name in filenames)


def iter_markdown_files(root_level: Path) -> Iterator[MarkdownFile]:
    """Yield all markdown files from root_level downwards with their CURRENT_LEVEL."""
    for path, current_level in walk_markdown_files(root_level):
        yield MarkdownFile(path=path, current_level=current_level)


_REFLINK_PATTERN = re.compile(r"""^\s*\[([^\]]+)\]:\s+(.+)$""")
_IMAGE_PATTERN = re.compile(r"""!\[([^\]]*)\]\(([^)]+)\)""")


def _normalize_link_token(target: str) -> str:
    """Extract and normalize the first token of a Markdown link target."""
    token = target.split()[0].strip()
    if token.startswith("<") and token.endswith(">"):
        token = token[1:-1]
    if (token.startswith('"') and token.endswith('"')) or (
        token.startswith("'") and token.endswith("'")
    ):
        token = token[1:-1]
    return token

def _compute_header_level(path: Path, current_level: int) -> int:
    """Compute the header offset level for a markdown file."""
    if path.name == "_index.md":
        return current_level
    return current_level + 1



def _process_image_line(line: str, path: Path, resources_dir: Path) -> str:
    """Rewrite local image links in one line and copy images to resources."""
    project_root = resources_dir.parent

    def _replace(match: re.Match[str]) -> str:
        label = match.group(1)
        token = _normalize_link_token(match.group(2).strip())
        lowered = token.lower()

        if lowered.startswith(
            ("http://", "https://", "ftp://", "mailto:", "data:", "#"),
        ):
            return match.group(0)

        image_path = (path.parent / token).resolve()

        if not image_path.exists():
            print(
                "[pandocster] Warning: image file not found, skipped: "
                f"{image_path}",
            )
            return match.group(0)

        try:
            relative_to_root = image_path.relative_to(project_root)
        except ValueError:
            print(
                "[pandocster] Warning: image outside build directory skipped: "
                f"{image_path}",
            )
            return match.group(0)

        dest = resources_dir / relative_to_root
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_path, dest)
        except OSError as exc:
            raise PrepareError(
                f"Failed to copy image {image_path} to resources: {exc}",
            ) from exc

        return f"![{label}]({relative_to_root.as_posix()})"

    return _IMAGE_PATTERN.sub(_replace, line)


def _collect_fenced_block(lines_iter: Iterator[str]) -> list[str]:
    """Consume lines from an iterator up to the closing '```' fence and return them."""
    block: list[str] = []
    for inner in lines_iter:
        if inner == "```":
            break
        block.append(inner)
    return block


def _generate_mermaid(
    lines: list[str],
    resources_dir: Path,
    cfg: DiagramToolConfig,
) -> str:
    """Convert a Mermaid diagram block to SVG via the mmdc CLI and return a Markdown image line."""
    if not cfg.enabled:
        raise PrepareError(
            "mmdc is not enabled or not found; cannot render mermaid diagram."
        )
    format = cfg.format
    output_stem = str(uuid.uuid4())
    output_path = resources_dir / f"{output_stem}.{format}"
    content = "\n".join(lines)

    with tempfile.NamedTemporaryFile(
        suffix=".mermaid", mode="w", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    cmd: list[str] = [
        cfg.bin,
        "-i", str(tmp_path),
        "-o", str(output_path),
        "--backgroundColor", "transparent",
    ]
    for opt in cfg.options:
        if opt.value is not None:
            cmd += [f"--{opt.name}", str(opt.value)]
        else:
            cmd.append(f"--{opt.name}")

    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True, shell=_SHELL)
        if result.returncode != 0:
            raise PrepareError(f"mmdc failed (exit {result.returncode}): {result.stderr}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return f"![]({output_stem}.{format})"


def _generate_graphviz(
    lines: list[str],
    resources_dir: Path,
    cfg: DiagramToolConfig,
) -> str:
    """Convert a Graphviz diagram block to SVG via the dot CLI and return a Markdown image line."""
    if not cfg.enabled:
        raise PrepareError(
            "dot is not enabled or not found; cannot render graphviz diagram."
        )
    format = cfg.format
    output_stem = str(uuid.uuid4())
    output_path = resources_dir / f"{output_stem}.{format}"
    content = "\n".join(lines)

    with tempfile.NamedTemporaryFile(
        suffix=".dot", mode="w", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    cmd: list[str] = [cfg.bin, "-T", f"{format}", "-o", str(output_path), str(tmp_path)]

    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True, shell=_SHELL)
        if result.returncode != 0:
            raise PrepareError(f"dot failed (exit {result.returncode}): {result.stderr}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return f"![]({output_stem}.{format})"


def _match_reflink(
    line: str,
    path: Path,
    root_level: Path,
) -> ReflinkDefinition | None:
    """Parse a line as a markdown reflink definition pointing to a .md file.

    Returns a ReflinkDefinition if the line is a reflink to a markdown file under
    ROOT_LEVEL, or None if the line should be kept as-is.
    """
    match = _REFLINK_PATTERN.match(line)
    if not match:
        return None
    label = match.group(1)
    target = match.group(2).strip()
    anchor = _build_file_anchor(target, path, root_level)
    if anchor is None:
        return None
    return ReflinkDefinition(label=label, anchor=anchor)


def _build_file_anchor(
    target: str,
    source_path: Path,
    root_level: Path,
) -> str | None:
    """Try to build an anchor for a reference target.

    Only relative paths to .md files under ROOT_LEVEL are converted. All other
    targets (http URLs, mailto, local anchors, non-md files, paths outside
    ROOT_LEVEL) yield None.
    """
    token = _normalize_link_token(target)
    lowered = token.lower()

    if lowered.startswith(("http://", "https://", "mailto:", "#")):
        return None

    if not lowered.endswith(".md"):
        return None

    target_path = (source_path.parent / token).resolve()

    try:
        relative_to_root = target_path.relative_to(root_level)
    except ValueError:
        # Target is outside of ROOT_LEVEL – leave it untouched.
        return None

    return "_".join(relative_to_root.parts)


def _write_reflinks_file(
    root_level: Path, reflinks: Iterable[ReflinkDefinition]
) -> None:
    """Write collected reflinks into 999-reflinks.md under ROOT_LEVEL."""
    reflinks_list = list(reflinks)
    target = root_level / "999-reflinks.md"

    if not reflinks_list:
        if target.exists():
            try:
                target.unlink()
            except OSError as exc:
                raise PrepareError(
                    f"Failed to remove stale reflinks file: {exc}"
                ) from exc
        return

    unique_reflinks = sorted(
        set(reflinks_list),
        key=lambda r: (r.label, r.anchor),
    )

    by_label: dict[str, set[str]] = {}
    for reflink in unique_reflinks:
        by_label.setdefault(reflink.label, set()).add(reflink.anchor)

    ambiguous = {
        label: anchors for label, anchors in by_label.items() if len(anchors) > 1
    }

    if ambiguous:
        messages: list[str] = [
            "[pandocster] Warning: ambiguous reference-style links detected:"
        ]
        for label, anchors in sorted(ambiguous.items()):
            anchors_list = ", ".join(sorted(f"#{anchor}" for anchor in anchors))
            messages.append(f"  label '{label}' -> {anchors_list}")
        print("\n".join(messages))

    lines_out: list[str] = ["<!-- Generated by pandocster prepare -->", ""]
    for reflink in unique_reflinks:
        lines_out.append(f"[{reflink.label}]: #{reflink.anchor}")

    content = "\n".join(lines_out) + "\n"

    try:
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise PrepareError(f"Failed to write reflinks file {target}: {exc}") from exc
