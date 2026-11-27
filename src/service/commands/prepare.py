"""Implementation of the `prepare` command logic for pandocster."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

import yaml

from config.schema import AppConfig, DiagramToolConfig, NumeratorConfig
from service.command_log import log_file as command_log_file
from service.markdown_walker import walk_markdown_files
from service.subprocess_runner import Runner, _default_runner


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


@dataclass
class _PreparedMarkdown:
    """One markdown file after variables and numerator generators are resolved."""

    path: Path
    header_offset: int
    lines: list[str]


def run_prepare(
    src: Path,
    build: Path,
    cfg: AppConfig | None = None,
    runner: Runner | None = None,
) -> None:
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
    variables = _cfg.variables or {}
    numerators = NumeratorEngine(_cfg.numerators or {})

    prepared: list[_PreparedMarkdown] = []
    for md_file in iter_markdown_files_for_build(root_level):
        path = md_file.path
        current_level = md_file.current_level

        try:
            original_content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise PrepareError(f"Failed to read markdown file {path}: {exc}") from exc

        level = _compute_header_level(path, current_level)
        lines_list = (
            original_content.splitlines(keepends=False) if original_content else []
        )
        prepared.append(
            _PreparedMarkdown(
                path=path,
                header_offset=level,
                lines=_generate_numerator_lines(
                    lines_list,
                    variables,
                    numerators,
                    path=path,
                    header_offset=level,
                ),
            )
        )

    new_content: list[str] = []
    for prepared_file in prepared:
        path = prepared_file.path
        relative = path.relative_to(root_level)
        file_anchor = "_".join(relative.parts)
        header_line = f"<!-- @header-offset: {prepared_file.header_offset} -->"
        anchor_line = f'<!-- @anchor="{file_anchor}" -->'
        new_content = [
            header_line,
            anchor_line,
        ]
        in_fence = False
        lines_iter = iter(prepared_file.lines)
        for line_number, line in enumerate(lines_iter, start=1):
            line, in_fence = _substitute_numerator_references(
                line,
                numerators,
                path=path,
                line_number=line_number,
                in_fence=in_fence,
            )
            reflink = _match_reflink(line, path, root_level)
            if reflink is not None:
                reflinks.append(reflink)
                continue

            if line == "```mermaid" and mermaid_is_enabled:
                if diagrams is None or diagrams.mmdc is None:
                    raise PrepareError("Mermaid is enabled but not configured.")
                new_content.append(
                    _generate_mermaid(
                        _collect_fenced_block(lines_iter),
                        resources_dir,
                        diagrams.mmdc,
                        runner,
                    )
                )
                continue

            if line in ("```graphviz", "```graphiz") and graphviz_is_enabled:
                if diagrams is None or diagrams.graphviz is None:
                    raise PrepareError("Graphviz is enabled but not configured.")
                new_content.append(
                    _generate_graphviz(
                        _collect_fenced_block(lines_iter),
                        resources_dir,
                        diagrams.graphviz,
                        runner,
                    )
                )
                continue

            if _IMAGE_PATTERN.search(line):
                line = _process_image_line(line, path, resources_dir)

            new_content.append(line)

        try:
            path.write_text("\n".join(new_content), encoding="utf-8")
            command_log_file(path, "modified")
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
                command_log_file(dest_file, "created")
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


def iter_markdown_files_for_build(root_level: Path) -> Iterator[MarkdownFile]:
    """Yield markdown files in the order pandoc later concatenates them.

    Within each directory ``_index.md`` comes first. ``999-reflinks.md`` is
    skipped: it is generated after this pass and must not contain numerators.
    """
    files = list(iter_markdown_files(root_level))

    def _sort_key(md_file: MarkdownFile) -> tuple[str, int, str]:
        relative = md_file.path.relative_to(root_level)
        parent = relative.parent.as_posix()
        is_index = 0 if relative.name == "_index.md" else 1
        return parent, is_index, relative.name

    files.sort(key=_sort_key)
    for md_file in files:
        if md_file.path.name == "999-reflinks.md":
            continue
        yield md_file


_REFLINK_PATTERN = re.compile(r"""^\s*\[([^\]]+)\]:\s+(.+)$""")
_IMAGE_PATTERN = re.compile(r"""!\[([^\]]*)\]\(([^)]+)\)""")
_FENCE_PATTERN = re.compile(r"""^ {0,3}(`{3,}|~{3,})""")
_TOKEN_BODY = (
    r"""(?:[A-Za-z0-9_]+"""
    r"""|#\#?(?::[ \t]*[A-Za-z0-9_]*){0,2}"""
    r"""|#\#?[ \t]*=:[ \t]*[A-Za-z0-9_]*:[ \t]*[A-Za-z0-9_]+)[ \t]*\}\}"""
)
_TOKEN_PATTERN = re.compile(
    r"""\\\{\{[ \t]*"""
    + _TOKEN_BODY
    + r"""|\{\{[ \t]*(?:(?P<hashes>#\#?)"""
    + r"""(?:[ \t]*(?P<reference>=):[ \t]*(?P<ref_name>[A-Za-z0-9_]*)"""
    + r""":[ \t]*(?P<ref_id>[A-Za-z0-9_]+)"""
    + r"""|(?::[ \t]*(?P<name>[A-Za-z0-9_]*))?"""
    + r"""(?::[ \t]*(?P<value_id>[A-Za-z0-9_]*))?)"""
    + r"""|(?P<variable>[A-Za-z0-9_]+))[ \t]*\}\}"""
)
_SETEXT_UNDERLINE = re.compile(r"""^ {0,3}(?:=+|-+)[ \t]*$""")
_ATX_LEVEL = re.compile(r"""^ {0,3}(#{1,6})(?:[ \t]+|$)""")
_BLANK_LINE = re.compile(r"""[ \t]*""")


class NumeratorEngine:
    """Cross-file numbering state for one prepare run."""

    def __init__(self, configs: dict[str, NumeratorConfig]) -> None:
        self._configs = configs
        self._kinds: dict[str, bool] = {}
        self._flat: dict[str, int] = {}
        self._body: dict[tuple[str, tuple[int, ...]], int] = {}
        self._values: dict[tuple[str, str], str] = {}
        self._value_origins: dict[tuple[str, str], str] = {}
        self._stacks: dict[str, list[_HierarchyFrame]] = {}
        self._offset = 1
        self._issued_in_heading: set[str] = set()

    def begin_file(self, header_offset: int) -> None:
        """Remember the offset Pandocster writes for the current file."""
        self._offset = header_offset

    def render(
        self,
        *,
        hierarchical: bool,
        name: str,
        value_id: str | None,
        heading_level: int | None,
        path: Path,
        line_number: int,
    ) -> str:
        """Return a newly allocated number. A repeated value id is an error."""
        self._reject_mixed_kind(name, hierarchical, path, line_number)
        if value_id:
            key = (name, value_id)
            origin = self._value_origins.get(key)
            if origin is not None:
                raise PrepareError(
                    f"Numerator '{name}' value '{value_id}' is already generated "
                    f"at {origin}; repeated generator in {path}:{line_number}"
                )
        if (
            hierarchical
            and heading_level is not None
            and name in self._issued_in_heading
        ):
            return ""
        rendered = (
            self._render_hierarchical(name, heading_level)
            if hierarchical
            else self._render_flat(name)
        )
        if value_id:
            key = (name, value_id)
            self._values[key] = rendered
            self._value_origins[key] = f"{path}:{line_number}"
        if hierarchical and heading_level is not None:
            self._issued_in_heading.add(name)
        return rendered

    def reference(
        self,
        *,
        name: str,
        value_id: str,
        path: Path,
        line_number: int,
    ) -> str:
        """Return a previously generated number without moving its counter."""
        rendered = self._values.get((name, value_id))
        if rendered is None:
            raise PrepareError(
                f"Numerator '{name}' has no generated value '{value_id}' "
                f"for reference in {path}:{line_number}"
            )
        return rendered

    def heading_level(self, lines: list[str], index: int) -> int | None:
        """Return the visual heading level of a line, matching header_offset.lua."""
        self._issued_in_heading.clear()
        markdown_level = _markdown_heading_level(lines, index)
        if markdown_level is None:
            return None
        # The file offset already includes the document base. Lua then subtracts
        # one, so an H1 in a root file (offset 2) stays at visual level 1.
        return markdown_level + self._offset - 2

    def _reject_mixed_kind(
        self,
        name: str,
        hierarchical: bool,
        path: Path,
        line_number: int,
    ) -> None:
        seen = self._kinds.get(name)
        if seen is None:
            self._kinds[name] = hierarchical
            return
        if seen != hierarchical:
            kind = "hierarchical" if hierarchical else "flat"
            raise PrepareError(
                f"Numerator '{name}' cannot be both flat and hierarchical "
                f"({kind} marker in {path}:{line_number})"
            )

    def _config(self, name: str) -> NumeratorConfig:
        return self._configs.get(name, NumeratorConfig())

    def _render_flat(self, name: str) -> str:
        config = self._config(name)
        number = self._flat.get(name, config.start)
        self._flat[name] = number + 1
        return f"{number}{config.suffix}"

    def _render_hierarchical(self, name: str, heading_level: int | None) -> str:
        config = self._config(name)
        frames = self._stacks.setdefault(name, [])
        if heading_level is None:
            return self._render_body(name, config, frames)
        del frames[sum(1 for frame in frames if frame.level < heading_level) :]
        components = _heading_components(
            self,
            name,
            frames,
            heading_level,
            config.start,
        )
        frames.append(_HierarchyFrame(heading_level, tuple(components)))
        return _join_number(components, config)

    def _render_body(
        self,
        name: str,
        config: NumeratorConfig,
        frames: list[_HierarchyFrame],
    ) -> str:
        if not frames:
            return self._render_flat(name)
        parent = frames[-1]
        key = (name, parent.components)
        number = self._body.get(key, 1)
        self._body[key] = number + 1
        return _join_number([*parent.components, number], config)


@dataclass(frozen=True)
class _HierarchyFrame:
    """One heading that opened a hierarchical numerator section."""

    level: int
    components: tuple[int, ...]


def _heading_components(
    engine: NumeratorEngine,
    name: str,
    frames: list[_HierarchyFrame],
    heading_level: int,
    start: int,
) -> list[int]:
    """Build a number whose depth matches the visual heading level."""
    if not frames:
        issued = engine._body.get((name, ()), start)
        components = [issued, *([1] * (heading_level - 1))]
        engine._body[(name, ())] = issued + 1
        return components
    parent = frames[-1]
    gap = heading_level - parent.level - 1
    prefix = (*parent.components, *([1] * max(gap, 0)))
    number = engine._body.get((name, prefix), 1)
    engine._body[(name, prefix)] = number + 1
    return [*prefix, number]


def _join_number(components: list[int], config: NumeratorConfig) -> str:
    return (
        config.delimiter.join(str(component) for component in components)
        + config.suffix
    )


def _markdown_heading_level(lines: list[str], index: int) -> int | None:
    """Recognize an ATX or setext heading line outside a nested container."""
    line = lines[index]
    if line[:1] in (">",) or _is_indented_container(line):
        return None
    atx = _ATX_LEVEL.match(line)
    if atx is not None:
        return len(atx.group(1))
    if not line.strip() or _SETEXT_UNDERLINE.fullmatch(line):
        return None
    underline = _next_content_line(lines, index + 1)
    if underline is not None and _SETEXT_UNDERLINE.fullmatch(lines[underline]):
        return 1 if lines[underline].lstrip().startswith("=") else 2
    return None


def _is_indented_container(line: str) -> bool:
    """A four-space indent is a nested block, not a document heading."""
    return line.startswith("    ") or line.startswith("\t")


def _next_content_line(lines: list[str], index: int) -> int | None:
    while index < len(lines):
        if not _BLANK_LINE.fullmatch(lines[index]):
            return index
        index += 1
    return None


def _render_variable_value(value: Any) -> str:
    """Render a YAML variable value as literal text."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    rendered = yaml.safe_dump(
        value,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )
    if not isinstance(rendered, str):
        raise PrepareError(f"Failed to render variable value: {value!r}")
    return rendered.removesuffix("\n...\n").removesuffix("\n")


def _generate_numerator_lines(
    lines: list[str],
    variables: dict[str, Any],
    numerators: NumeratorEngine,
    *,
    path: Path,
    header_offset: int,
) -> list[str]:
    """Resolve variables and numerator generators, leaving references in place."""
    numerators.begin_file(header_offset)
    generated: list[str] = []
    in_fence = False
    for line_number, line in enumerate(lines, start=1):
        line, in_fence = _substitute_variables(
            line,
            variables,
            numerators,
            path=path,
            line_number=line_number,
            in_fence=in_fence,
            lines=lines,
        )
        generated.append(line)
    return generated


def _substitute_numerator_references(
    line: str,
    numerators: NumeratorEngine,
    *,
    path: Path,
    line_number: int,
    in_fence: bool,
) -> tuple[str, bool]:
    """Replace numerator references after every generator has been allocated."""
    fence = _FENCE_PATTERN.match(line)
    if fence is not None:
        return line, not in_fence
    if in_fence:
        return line, in_fence
    return (
        _substitute_reference_spans(
            line,
            numerators,
            path=path,
            line_number=line_number,
        ),
        in_fence,
    )


def _substitute_reference_spans(
    line: str,
    numerators: NumeratorEngine,
    *,
    path: Path,
    line_number: int,
) -> str:
    """Resolve references in one line, skipping inline code spans."""
    return _walk_inline_code(
        line,
        lambda segment: _replace_references(
            segment,
            numerators,
            path=path,
            line_number=line_number,
        ),
    )


def _replace_references(
    text: str,
    numerators: NumeratorEngine,
    *,
    path: Path,
    line_number: int,
) -> str:
    """Replace {{#=:name:id}} tokens. A leading backslash keeps the token."""
    pieces: list[str] = []
    cursor = 0
    for match in _TOKEN_PATTERN.finditer(text):
        pieces.append(text[cursor : match.start()])
        if not match.group(0).startswith("\\") and match.group("reference"):
            pieces.append(
                numerators.reference(
                    name=match.group("ref_name") or "default",
                    value_id=match.group("ref_id") or "",
                    path=path,
                    line_number=line_number,
                )
            )
        else:
            pieces.append(match.group(0))
        cursor = match.end()
    pieces.append(text[cursor:])
    return "".join(pieces)


def _walk_inline_code(line: str, replace: Callable[[str], str]) -> str:
    """Apply a replacement to text outside inline code spans."""
    parts: list[str] = []
    cursor = 0
    in_code = False
    index = 0
    while index < len(line):
        if line[index] == "`" and (index == 0 or line[index - 1] != "\\"):
            segment = line[cursor:index]
            parts.append(replace(segment) if not in_code else segment)
            parts.append("`")
            cursor = index + 1
            in_code = not in_code
        index += 1
    tail = line[cursor:]
    parts.append(replace(tail) if not in_code else tail)
    return "".join(parts)


def _replace_placeholders(
    text: str,
    variables: dict[str, Any],
    numerators: NumeratorEngine,
    *,
    path: Path,
    line_number: int,
    heading_level: int | None,
) -> str:
    """Replace numerators and {{name}} outside code. A leading \\ keeps the token."""
    pieces: list[str] = []
    cursor = 0
    for match in _TOKEN_PATTERN.finditer(text):
        pieces.append(text[cursor : match.start()])
        pieces.append(
            _replace_one_token(
                match,
                variables,
                numerators,
                path=path,
                line_number=line_number,
                heading_level=heading_level,
            )
        )
        cursor = match.end()
    pieces.append(text[cursor:])
    return "".join(pieces)


def _replace_one_token(
    match: re.Match[str],
    variables: dict[str, Any],
    numerators: NumeratorEngine,
    *,
    path: Path,
    line_number: int,
    heading_level: int | None,
) -> str:
    """Render one placeholder or numerator token, including an escaped one."""
    token = match.group(0)
    if token.startswith("\\"):
        return token
    if match.group("hashes"):
        if match.group("reference"):
            return match.group(0)
        return numerators.render(
            hierarchical=match.group("hashes") == "##",
            name=match.group("name") or "default",
            value_id=match.group("value_id"),
            heading_level=heading_level,
            path=path,
            line_number=line_number,
        )
    name = match.group("variable")
    if name not in variables:
        raise PrepareError(f"Unknown variable '{name}' in {path}:{line_number}")
    return _render_variable_value(variables[name])


def _substitute_inline_spans(
    line: str,
    variables: dict[str, Any],
    numerators: NumeratorEngine,
    *,
    path: Path,
    line_number: int,
    heading_level: int | None,
) -> str:
    """Substitute placeholders in one line, skipping inline code spans."""
    return _walk_inline_code(
        line,
        lambda segment: _replace_placeholders(
            segment,
            variables,
            numerators,
            path=path,
            line_number=line_number,
            heading_level=heading_level,
        ),
    )


def _substitute_variables(
    line: str,
    variables: dict[str, Any],
    numerators: NumeratorEngine,
    *,
    path: Path,
    line_number: int,
    in_fence: bool,
    lines: list[str],
) -> tuple[str, bool]:
    """Substitute placeholders in one line and report the fence state after it."""
    fence = _FENCE_PATTERN.match(line)
    if fence is not None:
        return line, not in_fence
    if in_fence:
        return line, in_fence
    if _SETEXT_UNDERLINE.fullmatch(line):
        return line, in_fence
    heading_level = numerators.heading_level(lines, line_number - 1)
    return (
        _substitute_inline_spans(
            line,
            variables,
            numerators,
            path=path,
            line_number=line_number,
            heading_level=heading_level,
        ),
        in_fence,
    )


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
            existed = dest.exists()
            shutil.copy2(image_path, dest)
            command_log_file(dest, "modified" if existed else "created")
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
    runner: Runner | None = None,
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

    actual_runner = runner or _default_runner
    try:
        result = actual_runner(cmd)
        if result.returncode != 0:
            raise PrepareError(f"mmdc failed (exit {result.returncode}): {result.stderr}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return f"![]({output_stem}.{format})"


def _generate_graphviz(
    lines: list[str],
    resources_dir: Path,
    cfg: DiagramToolConfig,
    runner: Runner | None = None,
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

    actual_runner = runner or _default_runner
    try:
        result = actual_runner(cmd)
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
    existed = target.exists()

    try:
        target.write_text(content, encoding="utf-8")
        command_log_file(target, "modified" if existed else "created")
    except OSError as exc:
        raise PrepareError(f"Failed to write reflinks file {target}: {exc}") from exc
