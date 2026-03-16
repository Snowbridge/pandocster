"""Tests that verify key CLI commands and subcommands are available."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from cli.entrypoint import main


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_build_command_available(runner: CliRunner) -> None:
    result = runner.invoke(main, ["build", "--help"])
    assert result.exit_code == 0


def test_check_command_available(runner: CliRunner) -> None:
    result = runner.invoke(main, ["check", "--help"])
    assert result.exit_code == 0


def test_config_create_available(runner: CliRunner) -> None:
    result = runner.invoke(main, ["config", "create", "--help"])
    assert result.exit_code == 0


def test_config_show_available(runner: CliRunner) -> None:
    result = runner.invoke(main, ["config", "show", "--help"])
    assert result.exit_code == 0
