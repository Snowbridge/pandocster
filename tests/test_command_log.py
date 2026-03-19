"""Tests for service.command_log module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from service.command_log import (
    is_active,
    log,
    log_file,
    log_subprocess,
    make_logging_runner,
    start,
    stop,
)


class TestCommandLogSession:
    """Tests for log session lifecycle."""

    def test_start_creates_log_file_in_cwd(self, tmp_path: Path) -> None:
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            log_path = start(tmp_path)
        assert log_path.exists()
        assert log_path.suffix == ".log"
        assert log_path.parent == tmp_path
        stop()

    def test_log_writes_timestamped_line(self, tmp_path: Path) -> None:
        start(tmp_path)
        try:
            log("test message")
            content = next(tmp_path.glob("*.log")).read_text(encoding="utf-8")
            assert "test message" in content
            assert "\t" in content
        finally:
            stop()

    def test_log_file_writes_created_action(self, tmp_path: Path) -> None:
        start(tmp_path)
        try:
            log_file(Path("/some/file.md"), "created")
            content = next(tmp_path.glob("*.log")).read_text(encoding="utf-8")
            assert "FILE_CREATED" in content
            assert "file.md" in content
        finally:
            stop()

    def test_log_file_writes_modified_action(self, tmp_path: Path) -> None:
        start(tmp_path)
        try:
            log_file(Path("/some/file.md"), "modified")
            content = next(tmp_path.glob("*.log")).read_text(encoding="utf-8")
            assert "FILE_MODIFIED" in content
        finally:
            stop()

    def test_log_subprocess_writes_command_and_output(self, tmp_path: Path) -> None:
        start(tmp_path)
        try:
            log_subprocess(
                ["pandoc", "doc.md", "--to=pdf"],
                stdout="pandoc output",
                stderr="",
            )
            content = next(tmp_path.glob("*.log")).read_text(encoding="utf-8")
            assert "SUBPROCESS" in content
            assert "pandoc" in content
            assert "STDOUT" in content
            assert "pandoc output" in content
        finally:
            stop()

    def test_is_active_true_after_start(self, tmp_path: Path) -> None:
        assert not is_active()
        start(tmp_path)
        try:
            assert is_active()
        finally:
            stop()
        assert not is_active()

    def test_log_noop_when_inactive(self, tmp_path: Path) -> None:
        log("should not appear")
        log_files = list(tmp_path.glob("*.log"))
        assert len(log_files) == 0

    def test_log_file_noop_when_inactive(self, tmp_path: Path) -> None:
        log_file(Path("/x/y"), "created")
        log_files = list(tmp_path.glob("*.log"))
        assert len(log_files) == 0


class TestMakeLoggingRunner:
    """Tests for make_logging_runner."""

    def test_logging_runner_invokes_base_and_logs(self, tmp_path: Path) -> None:
        from service.subprocess_runner import _default_runner

        start(tmp_path)
        try:
            logging_runner = make_logging_runner(_default_runner)
            result = logging_runner(["python", "-c", "print('hello')"])
            assert result.returncode == 0
            content = next(tmp_path.glob("*.log")).read_text(encoding="utf-8")
            assert "SUBPROCESS" in content
            assert "python" in content
            assert "STDOUT" in content
            assert "hello" in content
        finally:
            stop()
