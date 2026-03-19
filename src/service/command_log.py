"""Command logging for pandocster CLI when --log is enabled."""

from __future__ import annotations

import atexit
import subprocess
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from service.subprocess_runner import Runner, _default_runner

_log_session: ContextVar[LogSession | None] = ContextVar(
    "command_log_session", default=None
)


def _format_timestamp() -> str:
    """Return ISO timestamp safe for filenames (no colons)."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H-%M-%S") + "." + str(now.microsecond).zfill(6)


@dataclass
class LogSession:
    """Active log session with an open file handle."""

    path: Path
    file_handle: object

    def write_line(self, message: str) -> None:
        """Write a timestamped line to the log file."""
        ts = _format_timestamp()
        line = f"{ts}\t{message}\n"
        self.file_handle.write(line)
        self.file_handle.flush()


def start(cwd: Path) -> Path:
    """Create a log file in cwd and start a log session.

    Returns the path to the created log file.
    """
    timestamp = _format_timestamp()
    log_path = cwd / f"{timestamp}.log"
    fh = log_path.open("w", encoding="utf-8")
    session = LogSession(path=log_path, file_handle=fh)
    _log_session.set(session)
    atexit.register(stop)
    return log_path


def stop() -> None:
    """End the current log session and close the file."""
    session = _log_session.get()
    if session is not None:
        session.file_handle.close()
        _log_session.set(None)


def is_active() -> bool:
    """Return True if a log session is active."""
    return _log_session.get() is not None


def log(message: str) -> None:
    """Write a message to the log if a session is active."""
    session = _log_session.get()
    if session is not None:
        session.write_line(message)


def log_file(path: Path, action: str) -> None:
    """Log a file write event (action: 'created' or 'modified')."""
    if is_active():
        log(f"FILE_{action.upper()}: {path}")


def log_subprocess(
    args: Sequence[str],
    stdout: str | None,
    stderr: str | None,
) -> None:
    """Log a subprocess invocation with its command and output."""
    if not is_active():
        return
    cmd_str = " ".join(str(a) for a in args)
    log(f"SUBPROCESS: {cmd_str}")
    if stdout:
        for line in stdout.splitlines():
            log(f"STDOUT: {line}")
    if stderr:
        for line in stderr.splitlines():
            log(f"STDERR: {line}")


def make_logging_runner(base_runner: Runner | None = None) -> Runner:
    """Return a Runner that logs invocations and output."""
    runner = base_runner or _default_runner

    def _logging_runner(
        args: Sequence[str],
        *,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = runner(args, cwd=cwd)
        log_subprocess(
            args,
            result.stdout,
            result.stderr,
        )
        return result

    return _logging_runner
