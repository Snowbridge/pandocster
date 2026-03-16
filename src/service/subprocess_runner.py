"""Shared subprocess runner for pandocster service commands."""

from __future__ import annotations

import subprocess
import sys
from typing import Callable, Sequence

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]

# On Windows, npm-installed CLIs (mmdc, etc.) are .cmd wrapper scripts that
# require the shell to be involved so that cmd.exe can resolve them.
_SHELL = sys.platform == "win32"


def _default_runner(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True, shell=_SHELL)
