"""Implementation of the `prepare` command logic for pandocster."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple


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


def run_prepare(src: Path, build: Path) -> None:
    """Orchestrate the prepare operation."""
    src_resolved = src.resolve()
    build_resolved = build.resolve()

    _validate_paths(src_resolved, build_resolved)
    prepare_build_directory(build_resolved)
    copy_src_to_build(src_resolved, build_resolved)

    resources_dir = _ensure_resources_dir(build_resolved)

    root_level = find_root_level(build_resolved)
    reflinks: List[ReflinkDefinition] = []

    for md_file in iter_markdown_files(root_level):
        reflinks.extend(
            process_markdown_file(
                md_file.path,
                md_file.current_level,
                root_level,
                resources_dir,
            ),
        )

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
        print(f"[pandocster] Warning: resources directory already exists: {resources_dir}")

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
    for root, dirnames, filenames in os.walk(root_level):
        dirnames.sort()
        filenames.sort()

        current_dir = Path(root)
        rel = current_dir.relative_to(root_level)
        # ROOT_LEVEL is considered to have CURRENT_LEVEL = 1,
        # its direct children = 2, and so on.
        current_level = len(rel.parts) + 1

        for filename in filenames:
            if not filename.lower().endswith(".md"):
                continue
            yield MarkdownFile(path=current_dir / filename, current_level=current_level)


def process_markdown_file(
    path: Path,
    current_level: int,
    root_level: Path,
    resources_dir: Path,
) -> List[ReflinkDefinition]:
    """Apply header offset, anchor metadata, and reflink extraction to a markdown file."""
    try:
        original_content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PrepareError(f"Failed to read markdown file {path}: {exc}") from exc

    if path.name == "_index.md":
        level = current_level
    else:
        level = current_level + 1

    relative = path.relative_to(root_level)
    file_anchor = _build_file_anchor(relative)

    header_line = f"<!-- @header-offset: {level} -->"
    anchor_line = f'<!-- @anchor="{file_anchor}" -->'

    lines = original_content.splitlines(keepends=False) if original_content else []
    # First, remove reference-style links to other markdown files and collect them.
    filtered_lines, reflinks = _extract_md_reflinks(lines, path, root_level)
    # Then rewrite image links and copy images into resources.
    filtered_lines = _rewrite_image_links(
        filtered_lines,
        path=path,
        root_level=root_level,
        resources_dir=resources_dir,
    )

    new_lines = [header_line]
    anchor_inserted = False

    for line in filtered_lines:
        stripped = line.lstrip()
        if not anchor_inserted and stripped.startswith("#"):
            # Place the anchor marker inline at the end of the first heading line.
            new_lines.append(f"{anchor_line}")
            new_lines.append(f"{line}")
            anchor_inserted = True
        else:
            new_lines.append(line)

    if not anchor_inserted:
        # No heading found: place anchor immediately after header-offset.
        new_lines.insert(1, anchor_line)

    # Ensure the file ends with exactly one trailing blank line:
    # 1) убрать все пустые строки в конце
    while new_lines and not new_lines[-1].strip():
        new_lines.pop()
    # 2) добавить одну пустую строку
    new_lines.append("")

    new_content = "\n".join(new_lines)

    try:
        path.write_text(new_content, encoding="utf-8")
    except OSError as exc:
        raise PrepareError(f"Failed to write markdown file {path}: {exc}") from exc

    return reflinks


def _build_file_anchor(relative: Path) -> str:
    parts: Tuple[str, ...] = relative.parts
    return "_".join(parts)


_REFLINK_PATTERN = re.compile(r"""^\s*\[([^\]]+)\]:\s+(.+)$""")
_IMAGE_PATTERN = re.compile(r"""!\[([^\]]*)\]\(([^)]+)\)""")


def _extract_md_reflinks(
    lines: Iterable[str],
    path: Path,
    root_level: Path,
) -> Tuple[List[str], List[ReflinkDefinition]]:
    """Extract reference-style links to markdown files.

    Returns the filtered list of lines (with such reference definitions removed)
    and a list of normalized reflink definitions.
    """
    kept: List[str] = []
    reflinks: List[ReflinkDefinition] = []

    lines_list = list(lines)
    index = 0

    while index < len(lines_list):
        line = lines_list[index]
        match = _REFLINK_PATTERN.match(line)
        if not match:
            kept.append(line)
            index += 1
            continue

        label, target = match.group(1), match.group(2).strip()
        anchor = _try_build_anchor_from_target(target, path, root_level)

        if anchor is None:
            # Not a markdown file under ROOT_LEVEL or unsupported target: keep as is.
            kept.append(line)
            index += 1
            continue

        reflinks.append(ReflinkDefinition(label=label, anchor=anchor))
        # The reference definition is removed from the file content along with
        # a single following empty line, if present, to avoid leaving visual gaps.
        index += 1
        if index < len(lines_list) and not lines_list[index].strip():
            index += 1

    return kept, reflinks


def _try_build_anchor_from_target(
    target: str,
    source_path: Path,
    root_level: Path,
) -> str | None:
    """Try to build an anchor for a reference target.

    Only relative paths to .md files under ROOT_LEVEL are converted. All other
    targets (http URLs, mailto, local anchors, non-md files, paths outside
    ROOT_LEVEL) yield None.
    """
    # Strip an optional title or extra data: take the first whitespace-separated token.
    token = target.split()[0].strip()

    # Remove optional surrounding <>, quotes.
    if token.startswith("<") and token.endswith(">"):
        token = token[1:-1]
    if (token.startswith('"') and token.endswith('"')) or (
        token.startswith("'") and token.endswith("'")
    ):
        token = token[1:-1]

    lowered = token.lower()

    # Skip non-relative schemes and local anchors.
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

    return _build_file_anchor(relative_to_root)


def _rewrite_image_links(
    lines: Iterable[str],
    path: Path,
    root_level: Path,
    resources_dir: Path,
) -> List[str]:
    """Rewrite local image links and copy images into the resources directory."""

    project_root = resources_dir.parent

    def _replace(match: re.Match[str]) -> str:
        label = match.group(1)
        target = match.group(2).strip()

        token = target.split()[0].strip()

        if token.startswith("<") and token.endswith(">"):
            token = token[1:-1]
        if (token.startswith('"') and token.endswith('"')) or (
            token.startswith("'") and token.endswith("'")
        ):
            token = token[1:-1]

        lowered = token.lower()

        # Skip non-local schemes and anchors.
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

        dest_image_path = resources_dir / relative_to_root
        try:
            dest_image_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_path, dest_image_path)
        except OSError as exc:
            raise PrepareError(
                f"Failed to copy image {image_path} to resources: {exc}",
            ) from exc

        new_target = relative_to_root.as_posix()
        return f"![{label}]({new_target})"

    rewritten: List[str] = []
    for line in lines:
        rewritten.append(_IMAGE_PATTERN.sub(_replace, line))
    return rewritten


def _write_reflinks_file(root_level: Path, reflinks: Iterable[ReflinkDefinition]) -> None:
    """Write collected reflinks into 999-reflinks.md under ROOT_LEVEL."""
    reflinks_list = list(reflinks)
    target = root_level / "999-reflinks.md"

    if not reflinks_list:
        # If there are no reflinks, ensure the file does not contain stale data.
        if target.exists():
            try:
                target.unlink()
            except OSError as exc:
                raise PrepareError(f"Failed to remove stale reflinks file: {exc}") from exc
        return

    # Remove exact duplicates.
    unique_reflinks = sorted(
        set(reflinks_list),
        key=lambda r: (r.label, r.anchor),
    )

    # Detect ambiguous definitions: same label with different anchors.
    by_label: dict[str, set[str]] = {}
    for reflink in unique_reflinks:
        by_label.setdefault(reflink.label, set()).add(reflink.anchor)

    ambiguous = {label: anchors for label, anchors in by_label.items() if len(anchors) > 1}

    if ambiguous:
        messages: List[str] = ["[pandocster] Warning: ambiguous reference-style links detected:"]
        for label, anchors in sorted(ambiguous.items()):
            anchors_list = ", ".join(sorted(f"#{anchor}" for anchor in anchors))
            messages.append(f"  label '{label}' -> {anchors_list}")
        print("\n".join(messages))

    lines: List[str] = ["<!-- Generated by pandocster prepare -->", ""]

    for reflink in unique_reflinks:
        lines.append(f"[{reflink.label}]: #{reflink.anchor}")

    content = "\n".join(lines) + "\n"

    try:
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise PrepareError(f"Failed to write reflinks file {target}: {exc}") from exc
