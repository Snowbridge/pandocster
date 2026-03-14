from __future__ import annotations

from typing import Any

import subprocess

from service.commands.checks import (
    MIN_LUA_VERSION,
    MIN_PANDOC_VERSION,
    PandocCheckStatus,
    analyse_pandoc_output,
    run_pandoc_check,
)


def _completed(stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["pandoc", "-v"], returncode=0, stdout=stdout, stderr=stderr)


def test_analyse_pandoc_output_ok() -> None:
    output = "\n".join(
        [
            f"pandoc {MIN_PANDOC_VERSION}",
            "Compiled with pandoc-types 1.23, texmath 0.12",
            f"Scripting engine: Lua {MIN_LUA_VERSION}",
        ]
    )
    result = analyse_pandoc_output(output)
    assert result.status is PandocCheckStatus.OK
    assert result.pandoc_version == MIN_PANDOC_VERSION
    assert result.lua_version == MIN_LUA_VERSION


def test_analyse_pandoc_output_old_pandoc() -> None:
    output = "\n".join(
        [
            "pandoc 3.7.0",
            "Compiled with pandoc-types 1.23, texmath 0.12",
            f"Scripting engine: Lua {MIN_LUA_VERSION}",
        ]
    )
    result = analyse_pandoc_output(output)
    assert result.status is PandocCheckStatus.PANDOC_VERSION_TOO_OLD


def test_analyse_pandoc_output_missing_lua() -> None:
    output = "\n".join(
        [
            f"pandoc {MIN_PANDOC_VERSION}",
            "Compiled with pandoc-types 1.23, texmath 0.12",
        ]
    )
    result = analyse_pandoc_output(output)
    assert result.status is PandocCheckStatus.LUA_VERSION_TOO_OLD


def test_analyse_pandoc_output_old_lua() -> None:
    output = "\n".join(
        [
            f"pandoc {MIN_PANDOC_VERSION}",
            "Compiled with pandoc-types 1.23, texmath 0.12",
            "Scripting engine: Lua 5.3",
        ]
    )
    result = analyse_pandoc_output(output)
    assert result.status is PandocCheckStatus.LUA_VERSION_TOO_OLD


def test_run_pandoc_check_handles_not_found() -> None:
    def runner(_: Any) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("No such file or directory: 'pandoc'")

    result = run_pandoc_check(runner=runner)
    assert result.status is PandocCheckStatus.PANDOC_NOT_FOUND

