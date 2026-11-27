"""Tests for the `init` command (service layer and CLI)."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.entrypoint import main
from service.commands.init import (
    _AGENT_TEMPLATE_FILES,
    _SRC_SUBDIRS,
    InitError,
    run_init,
)

# ---------------------------------------------------------------------------
# Service layer — run_init()
# ---------------------------------------------------------------------------


class TestRunInitCreatesExpectedFiles:
    def test_creates_pandocster_yaml(self, tmp_path: Path) -> None:
        run_init(tmp_path)
        assert (tmp_path / "pandocster.yaml").is_file()

    def test_pandocster_yaml_is_valid_yaml(self, tmp_path: Path) -> None:
        import yaml

        run_init(tmp_path)
        content = (tmp_path / "pandocster.yaml").read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        assert isinstance(parsed, dict)

    def test_creates_generate_sh(self, tmp_path: Path) -> None:
        run_init(tmp_path)
        assert (tmp_path / "generate.sh").is_file()

    def test_generate_sh_has_shebang(self, tmp_path: Path) -> None:
        run_init(tmp_path)
        first_line = (
            (tmp_path / "generate.sh").read_text(encoding="utf-8").splitlines()[0]
        )
        assert first_line == "#!/usr/bin/env bash"

    def test_generate_sh_calls_pandocster_build(self, tmp_path: Path) -> None:
        run_init(tmp_path)
        content = (tmp_path / "generate.sh").read_text(encoding="utf-8")
        assert "pandocster build" in content

    @pytest.mark.parametrize("subdir", _SRC_SUBDIRS)
    def test_creates_src_subdirs(self, tmp_path: Path, subdir: str) -> None:
        run_init(tmp_path)
        assert (tmp_path / subdir).is_dir()

    @pytest.mark.parametrize("subdir", _SRC_SUBDIRS)
    def test_src_subdirs_contain_gitkeep(self, tmp_path: Path, subdir: str) -> None:
        run_init(tmp_path)
        assert (tmp_path / subdir / ".gitkeep").is_file()

    def test_creates_agent_instruction_files(self, tmp_path: Path) -> None:
        run_init(tmp_path)
        agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
        skill = (
            tmp_path / ".agents" / "skills" / "pandocster-markdown" / "SKILL.md"
        ).read_text(encoding="utf-8")

        assert "_index.md" in agents
        assert "[intro]: ./01-intro.md" in agents
        assert "{{" in agents
        assert "{{#:" in agents
        assert "```mermaid" in agents
        assert "<!-- @new-page -->" in agents
        assert "pandocster build" in agents
        assert skill.startswith("---\nname: pandocster-markdown\n")

    def test_force_rewrites_agent_instructions(self, tmp_path: Path) -> None:
        (tmp_path / "existing.txt").write_text("hello", encoding="utf-8")
        agents = tmp_path / "AGENTS.md"
        agents.write_text("local notes\n", encoding="utf-8")

        run_init(tmp_path, force=True)

        assert "local notes" not in agents.read_text(encoding="utf-8")
        assert "_index.md" in agents.read_text(encoding="utf-8")


class TestRunInitDirectoryHandling:
    def test_creates_target_dir_if_missing(self, tmp_path: Path) -> None:
        target = tmp_path / "new_project"
        assert not target.exists()
        run_init(target)
        assert target.is_dir()

    def test_creates_nested_target_dir(self, tmp_path: Path) -> None:
        target = tmp_path / "a" / "b" / "c"
        run_init(target)
        assert target.is_dir()

    def test_empty_dir_succeeds_without_force(self, tmp_path: Path) -> None:
        run_init(tmp_path)  # must not raise

    def test_non_empty_dir_raises_without_force(self, tmp_path: Path) -> None:
        (tmp_path / "existing.txt").write_text("hello", encoding="utf-8")
        with pytest.raises(InitError, match="not empty"):
            run_init(tmp_path, force=False)

    def test_non_empty_dir_succeeds_with_force(self, tmp_path: Path) -> None:
        (tmp_path / "existing.txt").write_text("hello", encoding="utf-8")
        run_init(tmp_path, force=True)  # must not raise

    def test_force_false_is_default(self, tmp_path: Path) -> None:
        (tmp_path / "existing.txt").write_text("hello", encoding="utf-8")
        with pytest.raises(InitError):
            run_init(tmp_path)

    def test_error_message_mentions_force(self, tmp_path: Path) -> None:
        (tmp_path / "file.md").write_text("x", encoding="utf-8")
        with pytest.raises(InitError, match="--force"):
            run_init(tmp_path, force=False)


class TestRunInitAgentsOnly:
    def test_writes_templates_into_non_empty_dir(self, tmp_path: Path) -> None:
        (tmp_path / "notes.md").write_text("keep\n", encoding="utf-8")

        run_init(tmp_path, agents=True)

        for _resource_name, relative_path in _AGENT_TEMPLATE_FILES:
            assert (tmp_path / relative_path).is_file()
        assert not (tmp_path / "pandocster.yaml").exists()
        assert not (tmp_path / "generate.sh").exists()
        assert (tmp_path / "notes.md").read_text(encoding="utf-8") == "keep\n"

    def test_does_not_change_existing_config(self, tmp_path: Path) -> None:
        config = tmp_path / "pandocster.yaml"
        config.write_text("pandocster: {}\n", encoding="utf-8")
        before = config.read_bytes()

        run_init(tmp_path, agents=True)

        assert config.read_bytes() == before

    def test_replaces_edited_agents_file(self, tmp_path: Path) -> None:
        agents = tmp_path / "AGENTS.md"
        agents.write_text("local notes\n", encoding="utf-8")

        run_init(tmp_path, agents=True)
        first = agents.read_text(encoding="utf-8")
        agents.write_text("local notes again\n", encoding="utf-8")
        run_init(tmp_path, agents=True)

        assert agents.read_text(encoding="utf-8") == first
        assert "local notes" not in first

    def test_agents_with_force_still_skips_scaffold(self, tmp_path: Path) -> None:
        (tmp_path / "existing.txt").write_text("hello", encoding="utf-8")

        run_init(tmp_path, force=True, agents=True)

        assert (tmp_path / "AGENTS.md").is_file()
        assert not (tmp_path / "generate.sh").exists()


# ---------------------------------------------------------------------------
# CLI layer — `pandocster init`
# ---------------------------------------------------------------------------


@pytest.fixture
def cli() -> CliRunner:
    return CliRunner()


class TestInitCliAvailability:
    def test_init_command_available(self, cli: CliRunner) -> None:
        result = cli.invoke(main, ["init", "--help"])
        assert result.exit_code == 0

    def test_init_help_mentions_dir_argument(self, cli: CliRunner) -> None:
        result = cli.invoke(main, ["init", "--help"])
        assert "DIR" in result.output

    def test_init_help_mentions_force_option(self, cli: CliRunner) -> None:
        result = cli.invoke(main, ["init", "--help"])
        assert "--force" in result.output

    def test_init_help_mentions_agents_option(self, cli: CliRunner) -> None:
        result = cli.invoke(main, ["init", "--help"])
        assert "--agents" in result.output


class TestInitCliExecution:
    def test_exits_zero_on_success(self, cli: CliRunner, tmp_path: Path) -> None:
        result = cli.invoke(main, ["init", str(tmp_path)])
        assert result.exit_code == 0

    def test_prints_initialized_path_on_success(
        self, cli: CliRunner, tmp_path: Path
    ) -> None:
        result = cli.invoke(main, ["init", str(tmp_path)])
        assert "Initialized" in result.output

    def test_exits_one_on_non_empty_dir_without_force(
        self, cli: CliRunner, tmp_path: Path
    ) -> None:
        (tmp_path / "file.txt").write_text("x", encoding="utf-8")
        result = cli.invoke(main, ["init", str(tmp_path)])
        assert result.exit_code == 1

    def test_error_output_on_non_empty_without_force(
        self, cli: CliRunner, tmp_path: Path
    ) -> None:
        (tmp_path / "file.txt").write_text("x", encoding="utf-8")
        result = cli.invoke(main, ["init", str(tmp_path)])
        assert "not empty" in result.output

    def test_force_flag_allows_non_empty_dir(
        self, cli: CliRunner, tmp_path: Path
    ) -> None:
        (tmp_path / "file.txt").write_text("x", encoding="utf-8")
        result = cli.invoke(main, ["init", str(tmp_path), "--force"])
        assert result.exit_code == 0

    def test_creates_files_via_cli(self, cli: CliRunner, tmp_path: Path) -> None:
        target = tmp_path / "project"
        cli.invoke(main, ["init", str(target)])
        assert (target / "pandocster.yaml").is_file()
        assert (target / "generate.sh").is_file()
        assert (target / "AGENTS.md").is_file()
        for subdir in _SRC_SUBDIRS:
            assert (target / subdir / ".gitkeep").is_file()

    def test_agents_flag_prints_wrote_instructions(
        self, cli: CliRunner, tmp_path: Path
    ) -> None:
        (tmp_path / "notes.md").write_text("keep\n", encoding="utf-8")

        result = cli.invoke(main, ["init", str(tmp_path), "--agents"])

        assert result.exit_code == 0
        assert "Wrote agent instructions" in result.output
        assert not (tmp_path / "pandocster.yaml").exists()

    def test_defaults_to_current_directory(
        self, cli: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = cli.invoke(main, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / "pandocster.yaml").is_file()
