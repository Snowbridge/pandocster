"""Pandoc and Lua engine version checks for pandocster."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable

from service.subprocess_runner import Runner, _default_runner

MIN_PANDOC_VERSION = "3.8.3"
MIN_LUA_VERSION = "5.4"
MIN_DOT_VERSION = "14.1.1"
MIN_MMDC_VERSION = "11.12.0"


class PandocCheckStatus(Enum):
    OK = auto()
    PANDOC_NOT_FOUND = auto()
    PANDOC_VERSION_TOO_OLD = auto()
    LUA_VERSION_TOO_OLD = auto()
    UNKNOWN_ERROR = auto()


@dataclass
class PandocCheckResult:
    status: PandocCheckStatus
    pandoc_version: str | None = None
    lua_version: str | None = None
    raw_output: str | None = None
    error_message: str | None = None


def _parse_version(raw: str) -> tuple[int, int, int]:
    parts: list[int] = []
    for token in raw.split("."):
        m = re.match(r"\d+", token)
        if not m:
            break
        parts.append(int(m.group()))
        if len(parts) == 3:
            break

    while len(parts) < 3:
        parts.append(0)

    return parts[0], parts[1], parts[2]


def _version_less_than(left: str, right: str) -> bool:
    return _parse_version(left) < _parse_version(right)


def _extract_pandoc_version(lines: Iterable[str]) -> str | None:
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("pandoc "):
            tokens = stripped.split()
            if len(tokens) >= 2:
                return tokens[1]
    return None


def _extract_lua_version(lines: Iterable[str]) -> str | None:
    needle = "scripting engine: lua "
    for line in lines:
        lowered = line.strip().lower()
        if needle in lowered:
            # Take the last whitespace-separated token as the version string.
            tokens = line.strip().split()
            if tokens:
                return tokens[-1]
    return None


def analyse_pandoc_output(output: str) -> PandocCheckResult:
    """Analyse the output of `pandoc -v` and determine compatibility."""
    lines = output.splitlines()
    pandoc_version = _extract_pandoc_version(lines)
    lua_version = _extract_lua_version(lines)

    if pandoc_version is None:
        return PandocCheckResult(
            status=PandocCheckStatus.PANDOC_VERSION_TOO_OLD,
            pandoc_version=None,
            lua_version=lua_version,
            raw_output=output,
            error_message="Could not determine pandoc version from output.",
        )

    if _version_less_than(pandoc_version, MIN_PANDOC_VERSION):
        return PandocCheckResult(
            status=PandocCheckStatus.PANDOC_VERSION_TOO_OLD,
            pandoc_version=pandoc_version,
            lua_version=lua_version,
            raw_output=output,
            error_message="pandoc version is below the minimum required.",
        )

    if lua_version is None:
        return PandocCheckResult(
            status=PandocCheckStatus.LUA_VERSION_TOO_OLD,
            pandoc_version=pandoc_version,
            lua_version=None,
            raw_output=output,
            error_message="Could not determine Lua scripting engine version.",
        )

    if _version_less_than(lua_version, MIN_LUA_VERSION):
        return PandocCheckResult(
            status=PandocCheckStatus.LUA_VERSION_TOO_OLD,
            pandoc_version=pandoc_version,
            lua_version=lua_version,
            raw_output=output,
            error_message="Lua scripting engine version is below the minimum required.",
        )

    return PandocCheckResult(
        status=PandocCheckStatus.OK,
        pandoc_version=pandoc_version,
        lua_version=lua_version,
        raw_output=output,
        error_message=None,
    )


def run_pandoc_check(
    runner: Runner | None = None,
) -> PandocCheckResult:
    """Run `pandoc -v` and evaluate whether it satisfies pandocster requirements."""
    actual_runner = runner or _default_runner
    try:
        completed = actual_runner(["pandoc", "-v"])
    except FileNotFoundError as exc:
        return PandocCheckResult(
            status=PandocCheckStatus.PANDOC_NOT_FOUND,
            pandoc_version=None,
            lua_version=None,
            raw_output=None,
            error_message=str(exc),
        )
    except Exception as exc:  # pragma: no cover - defensive
        return PandocCheckResult(
            status=PandocCheckStatus.UNKNOWN_ERROR,
            pandoc_version=None,
            lua_version=None,
            raw_output=None,
            error_message=str(exc),
        )

    combined_output = (completed.stdout or "") + (completed.stderr or "")
    result = analyse_pandoc_output(combined_output)
    result.raw_output = combined_output
    return result


# ---------------------------------------------------------------------------
# Generic tool check (dot / mmdc)
# ---------------------------------------------------------------------------


class ToolCheckStatus(Enum):
    OK = auto()
    NOT_FOUND = auto()
    VERSION_TOO_OLD = auto()


@dataclass
class ToolCheckResult:
    status: ToolCheckStatus
    version: str | None = None
    error_message: str | None = None


def _extract_dot_version(output: str) -> str | None:
    """Extract the version number from `dot --version` output.

    Expected format: "dot - graphviz version 14.1.1 (20251213.1925)"
    """
    for line in output.splitlines():
        m = re.search(r"graphviz version\s+(\S+)", line, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def _extract_mmdc_version(output: str) -> str | None:
    """Extract the version number from `mmdc --version` output.

    Expected format: "11.12.0"
    """
    for line in output.splitlines():
        stripped = line.strip()
        if stripped and re.match(r"\d+\.\d+", stripped):
            return stripped
    return None


def analyse_dot_output(output: str) -> ToolCheckResult:
    """Analyse the output of `dot --version` and determine compatibility."""
    version = _extract_dot_version(output)
    if version is None:
        return ToolCheckResult(
            status=ToolCheckStatus.VERSION_TOO_OLD,
            version=None,
            error_message="Could not determine dot (Graphviz) version from output.",
        )
    if _version_less_than(version, MIN_DOT_VERSION):
        return ToolCheckResult(
            status=ToolCheckStatus.VERSION_TOO_OLD,
            version=version,
            error_message=f"dot version {version} is below the minimum required {MIN_DOT_VERSION}.",
        )
    return ToolCheckResult(status=ToolCheckStatus.OK, version=version)


def run_dot_check(runner: Runner | None = None, bin: str = "dot") -> ToolCheckResult:
    """Run `<bin> --version` and evaluate whether it satisfies pandocster requirements."""
    actual_runner = runner or _default_runner
    try:
        completed = actual_runner([bin, "--version"])
    except FileNotFoundError:
        return ToolCheckResult(
            status=ToolCheckStatus.NOT_FOUND,
            error_message=f"{bin!r} executable not found in PATH.",
        )
    except Exception as exc:  # pragma: no cover - defensive
        return ToolCheckResult(
            status=ToolCheckStatus.NOT_FOUND,
            error_message=str(exc),
        )
    combined_output = (completed.stdout or "") + (completed.stderr or "")
    return analyse_dot_output(combined_output)


def analyse_mmdc_output(output: str) -> ToolCheckResult:
    """Analyse the output of `mmdc --version` and determine compatibility."""
    version = _extract_mmdc_version(output)
    if version is None:
        return ToolCheckResult(
            status=ToolCheckStatus.VERSION_TOO_OLD,
            version=None,
            error_message="Could not determine mmdc version from output.",
        )
    if _version_less_than(version, MIN_MMDC_VERSION):
        return ToolCheckResult(
            status=ToolCheckStatus.VERSION_TOO_OLD,
            version=version,
            error_message=f"mmdc version {version} is below the minimum required {MIN_MMDC_VERSION}.",
        )
    return ToolCheckResult(status=ToolCheckStatus.OK, version=version)


def run_mmdc_check(runner: Runner | None = None, bin: str = "mmdc") -> ToolCheckResult:
    """Run `<bin> --version` and evaluate whether it satisfies pandocster requirements."""
    actual_runner = runner or _default_runner
    try:
        completed = actual_runner([bin, "--version"])
    except FileNotFoundError:
        return ToolCheckResult(
            status=ToolCheckStatus.NOT_FOUND,
            error_message=f"{bin!r} executable not found in PATH.",
        )
    except Exception as exc:  # pragma: no cover - defensive
        return ToolCheckResult(
            status=ToolCheckStatus.NOT_FOUND,
            error_message=str(exc),
        )
    combined_output = (completed.stdout or "") + (completed.stderr or "")
    return analyse_mmdc_output(combined_output)

