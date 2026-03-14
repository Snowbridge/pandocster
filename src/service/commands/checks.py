"""Pandoc and Lua engine version checks for pandocster."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
import subprocess
from typing import Callable, Iterable, Optional, Sequence, Tuple


MIN_PANDOC_VERSION = "3.8.3"
MIN_LUA_VERSION = "5.4"


class PandocCheckStatus(Enum):
    OK = auto()
    PANDOC_NOT_FOUND = auto()
    PANDOC_VERSION_TOO_OLD = auto()
    LUA_VERSION_TOO_OLD = auto()
    UNKNOWN_ERROR = auto()


@dataclass
class PandocCheckResult:
    status: PandocCheckStatus
    pandoc_version: Optional[str] = None
    lua_version: Optional[str] = None
    raw_output: str | None = None
    error_message: str | None = None


def _parse_version(raw: str) -> Tuple[int, int, int]:
    parts: list[int] = []
    for token in raw.split("."):
        number = ""
        for ch in token:
            if ch.isdigit():
                number += ch
            else:
                break
        if not number:
            break
        parts.append(int(number))
        if len(parts) == 3:
            break

    while len(parts) < 3:
        parts.append(0)

    return parts[0], parts[1], parts[2]


def _version_less_than(left: str, right: str) -> bool:
    return _parse_version(left) < _parse_version(right)


def _extract_pandoc_version(lines: Iterable[str]) -> Optional[str]:
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("pandoc "):
            tokens = stripped.split()
            if len(tokens) >= 2:
                return tokens[1]
    return None


def _extract_lua_version(lines: Iterable[str]) -> Optional[str]:
    needle = "scripting engine: lua "
    for line in lines:
        lowered = line.strip().lower()
        if needle in lowered:
            # Take the last whitespace-separated token as the version string.
            tokens = line.strip().split()
            if tokens:
                return tokens[-1]
    return None


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def _default_runner(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
    )


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

