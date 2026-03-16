"""Tests for config loading and serialization, focused on diagram tool settings."""

from __future__ import annotations

from pathlib import Path

import pytest

from config.load import ConfigError, _diagram_tool_to_dict, _parse_diagram_tool, config_to_dict
from config.schema import AppConfig, DiagramsConfig, DiagramToolConfig, DiagramOption, PandocConfig


# ---------------------------------------------------------------------------
# _parse_diagram_tool
# ---------------------------------------------------------------------------


def _tool_raw(extra: dict | None = None) -> dict:
    base: dict = {"enabled": True, "bin": "mmdc"}
    if extra:
        base.update(extra)
    return base


def test_parse_diagram_tool_default_format() -> None:
    """When 'format' is absent in YAML, default 'png' is used."""
    result = _parse_diagram_tool(_tool_raw(), "mmdc")
    assert result.format == "png"


def test_parse_diagram_tool_explicit_format() -> None:
    result = _parse_diagram_tool(_tool_raw({"format": "svg"}), "mmdc")
    assert result.format == "svg"


def test_parse_diagram_tool_format_coerced_to_str() -> None:
    """Numeric or other scalar values are coerced to str."""
    result = _parse_diagram_tool(_tool_raw({"format": 123}), "mmdc")
    assert result.format == "123"


def test_parse_diagram_tool_options_and_format_together() -> None:
    raw = _tool_raw({"format": "svg", "options": [{"name": "width", "value": "800"}]})
    result = _parse_diagram_tool(raw, "mmdc")
    assert result.format == "svg"
    assert len(result.options) == 1
    assert result.options[0].name == "width"


# ---------------------------------------------------------------------------
# _diagram_tool_to_dict
# ---------------------------------------------------------------------------


def _tool(fmt: str = "svg", options: list[DiagramOption] | None = None) -> DiagramToolConfig:
    return DiagramToolConfig(enabled=True, bin="mmdc", options=options or [], format=fmt)


def test_diagram_tool_to_dict_includes_format() -> None:
    d = _diagram_tool_to_dict(_tool(fmt="svg"))
    assert d["format"] == "svg"


def test_diagram_tool_to_dict_format_png() -> None:
    d = _diagram_tool_to_dict(_tool(fmt="png"))
    assert d["format"] == "png"


def test_diagram_tool_to_dict_roundtrip_format() -> None:
    """Serialise then parse back preserves format."""
    original = _tool(fmt="svg")
    d = _diagram_tool_to_dict(original)
    restored = _parse_diagram_tool(d, "mmdc")
    assert restored.format == original.format


# ---------------------------------------------------------------------------
# config_to_dict (full serialisation path)
# ---------------------------------------------------------------------------


def _app_cfg(mmdc_fmt: str = "svg", gv_fmt: str = "png") -> AppConfig:
    return AppConfig(
        pandoc=PandocConfig(bin="pandoc", filters=[], metadata={}, options=[]),
        diagrams=DiagramsConfig(
            mmdc=DiagramToolConfig(enabled=True, bin="mmdc", options=[], format=mmdc_fmt),
            graphviz=DiagramToolConfig(enabled=True, bin="dot", options=[], format=gv_fmt),
        ),
    )


def test_config_to_dict_preserves_mmdc_format() -> None:
    d = config_to_dict(_app_cfg(mmdc_fmt="svg"))
    assert d["pandocster"]["diagrams"]["mmdc"]["format"] == "svg"


def test_config_to_dict_preserves_graphviz_format() -> None:
    d = config_to_dict(_app_cfg(gv_fmt="png"))
    assert d["pandocster"]["diagrams"]["graphviz"]["format"] == "png"


# ---------------------------------------------------------------------------
# load_config round-trip via a temp YAML file
# ---------------------------------------------------------------------------


def test_load_config_reads_format_from_yaml(tmp_path: Path, monkeypatch) -> None:
    """load_config picks up 'format' from a local pandocster.yaml."""
    yaml_content = """\
pandocster:
  pandoc:
    bin: pandoc
    filters: []
    metadata: {}
    options: []
  diagrams:
    mmdc:
      enabled: true
      bin: mmdc
      format: svg
    graphviz:
      enabled: true
      bin: dot
      format: png
"""
    (tmp_path / "pandocster.yaml").write_text(yaml_content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    from config.load import load_config

    cfg = load_config(cwd=tmp_path)
    assert cfg.diagrams is not None
    assert cfg.diagrams.mmdc is not None
    assert cfg.diagrams.mmdc.format == "svg"
    assert cfg.diagrams.graphviz is not None
    assert cfg.diagrams.graphviz.format == "png"


def test_load_config_default_format_when_key_absent(tmp_path: Path, monkeypatch) -> None:
    """When 'format' is absent from YAML, the default 'png' is used."""
    yaml_content = """\
pandocster:
  pandoc:
    bin: pandoc
    filters: []
    metadata: {}
    options: []
  diagrams:
    mmdc:
      enabled: true
      bin: mmdc
    graphviz:
      enabled: true
      bin: dot
"""
    (tmp_path / "pandocster.yaml").write_text(yaml_content, encoding="utf-8")

    from config.load import load_config

    cfg = load_config(cwd=tmp_path)
    assert cfg.diagrams is not None
    assert cfg.diagrams.mmdc is not None
    assert cfg.diagrams.mmdc.format == "png"
    assert cfg.diagrams.graphviz is not None
    assert cfg.diagrams.graphviz.format == "png"
