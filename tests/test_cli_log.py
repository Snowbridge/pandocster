"""Tests for --log CLI option."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.entrypoint import main
from service.command_log import stop as command_log_stop


@pytest.fixture(autouse=True)
def reset_command_log() -> None:
    """Reset log session before each test to avoid cross-test pollution."""
    command_log_stop()
    yield


@pytest.fixture
def cli() -> CliRunner:
    return CliRunner()


class TestLogOption:
    """Tests for global --log option."""

    def test_log_option_creates_log_file_on_init(
        self, cli: CliRunner, tmp_path: Path
    ) -> None:
        """Running init with --log creates a timestamped log file."""
        with cli.isolated_filesystem(tmp_path):
            result = cli.invoke(main, ["--log", "init", "proj"])
            log_files = list(Path.cwd().glob("*.log"))
        assert result.exit_code == 0
        assert len(log_files) == 1
        content = log_files[0].read_text(encoding="utf-8")
        assert "FILE_CREATED" in content
        assert "pandocster.yaml" in content

    def test_log_option_creates_log_file_on_config_create(
        self, cli: CliRunner, tmp_path: Path
    ) -> None:
        """Running config create with --log creates a log file."""
        with cli.isolated_filesystem(tmp_path):
            result = cli.invoke(main, ["--log", "config", "create"])
            log_files = list(Path.cwd().glob("*.log"))
        assert result.exit_code == 0
        assert len(log_files) == 1
        content = log_files[0].read_text(encoding="utf-8")
        assert "FILE_CREATED" in content or "FILE_MODIFIED" in content
        assert "pandocster.yaml" in content

    def test_log_option_creates_log_file_on_check(
        self, cli: CliRunner, tmp_path: Path
    ) -> None:
        """Running check with --log creates a log file with subprocess output."""
        with cli.isolated_filesystem(tmp_path):
            cli.invoke(main, ["--log", "check"])
            log_files = list(Path.cwd().glob("*.log"))
        # check may exit 0 or 1 depending on pandoc presence
        assert len(log_files) == 1
        content = log_files[0].read_text(encoding="utf-8")
        assert "SUBPROCESS" in content
        assert "pandoc" in content

    def test_log_option_available_for_all_commands(self, cli: CliRunner) -> None:
        """--log appears in help for main and for commands like build."""
        result = cli.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "--log" in result.output
        result = cli.invoke(main, ["build", "--help"])
        assert result.exit_code == 0
        assert "--log" in result.output

    def test_init_without_log_creates_no_log_file(
        self, cli: CliRunner, tmp_path: Path
    ) -> None:
        """Running init without --log does not create a log file."""
        with cli.isolated_filesystem(tmp_path):
            result = cli.invoke(main, ["init", "."])
            log_files = list(Path.cwd().glob("*.log"))
        assert result.exit_code == 0
        assert len(log_files) == 0
