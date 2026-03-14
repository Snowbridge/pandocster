from __future__ import annotations

from click.testing import CliRunner

from cli.entrypoint import main


def test_cli_check_produces_output_without_pandoc(monkeypatch: object) -> None:
    runner = CliRunner()

    result = runner.invoke(main, ["check"])

    # We cannot guarantee pandoc is installed in the test environment,
    # but the command must produce helpful output describing the state.
    assert (
        "Pandocster requires pandoc" in result.output
        or "Pandocster is ready to use." in result.output
    )

