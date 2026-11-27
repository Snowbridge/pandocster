"""Tests for config loading and serialization, focused on diagram tool settings."""

from __future__ import annotations

from pathlib import Path

import pytest

from config.load import (
    ConfigError,
    _diagram_tool_to_dict,
    _parse_diagram_tool,
    config_to_dict,
)
from config.schema import (
    AppConfig,
    DiagramOption,
    DiagramsConfig,
    DiagramToolConfig,
    PandocConfig,
)

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


def _tool(
    fmt: str = "svg", options: list[DiagramOption] | None = None
) -> DiagramToolConfig:
    return DiagramToolConfig(
        enabled=True, bin="mmdc", options=options or [], format=fmt
    )


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
            mmdc=DiagramToolConfig(
                enabled=True, bin="mmdc", options=[], format=mmdc_fmt
            ),
            graphviz=DiagramToolConfig(
                enabled=True, bin="dot", options=[], format=gv_fmt
            ),
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


def test_load_config_default_format_when_key_absent(
    tmp_path: Path, monkeypatch
) -> None:
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


def test_load_config_reads_variables(tmp_path: Path) -> None:
    """variables keeps scalars and nested YAML values as parsed."""
    yaml_content = """\
pandocster:
  variables:
    product: Pandocster
    year: 2026
    draft: true
    authors:
      - Анна
      - Борис
    meta:
      lang: ru
"""
    (tmp_path / "pandocster.yaml").write_text(yaml_content, encoding="utf-8")

    from config.load import load_config

    cfg = load_config(cwd=tmp_path)
    assert cfg.variables == {
        "product": "Pandocster",
        "year": 2026,
        "draft": True,
        "authors": ["Анна", "Борис"],
        "meta": {"lang": "ru"},
    }


def test_load_config_variables_absent_is_empty(tmp_path: Path) -> None:
    (tmp_path / "pandocster.yaml").write_text("pandocster: {}\n", encoding="utf-8")

    from config.load import load_config

    cfg = load_config(cwd=tmp_path)
    assert cfg.variables == {}


def test_load_config_rejects_variables_list(tmp_path: Path) -> None:
    (tmp_path / "pandocster.yaml").write_text(
        "pandocster:\n  variables:\n    - product\n",
        encoding="utf-8",
    )

    from config.load import load_config

    with pytest.raises(ConfigError, match="variables"):
        load_config(cwd=tmp_path)


def test_load_config_rejects_variable_name_with_hyphen(tmp_path: Path) -> None:
    (tmp_path / "pandocster.yaml").write_text(
        "pandocster:\n  variables:\n    product-name: Pandocster\n",
        encoding="utf-8",
    )

    from config.load import load_config

    with pytest.raises(ConfigError, match="product-name"):
        load_config(cwd=tmp_path)


def test_config_to_dict_roundtrip_preserves_nested_variable() -> None:
    cfg = AppConfig(
        pandoc=PandocConfig(bin="pandoc", filters=[], metadata={}, options=[]),
        variables={"meta": {"lang": "ru"}, "year": 2026},
    )
    dumped = config_to_dict(cfg)
    assert dumped["pandocster"]["variables"]["meta"] == {"lang": "ru"}
    assert dumped["pandocster"]["variables"]["year"] == 2026


def test_config_to_dict_omits_empty_variables() -> None:
    cfg = AppConfig(
        pandoc=PandocConfig(bin="pandoc", filters=[], metadata={}, options=[]),
        variables={},
    )
    assert "variables" not in config_to_dict(cfg)["pandocster"]


def test_load_config_reads_numerators(tmp_path: Path) -> None:
    yaml_content = """\
pandocster:
  numerators:
    h:
      suffix: ". "
      start: 5
      delimiter: "-"
      extra: ignored
    plain: null
"""
    (tmp_path / "pandocster.yaml").write_text(yaml_content, encoding="utf-8")

    from config.load import load_config
    from config.schema import NumeratorConfig

    cfg = load_config(cwd=tmp_path)
    assert cfg.numerators == {
        "h": NumeratorConfig(suffix=". ", start=5, delimiter="-"),
        "plain": NumeratorConfig(),
    }


def test_load_config_numerator_defaults_and_null_suffix(tmp_path: Path) -> None:
    (tmp_path / "pandocster.yaml").write_text(
        "pandocster:\n  numerators:\n    h:\n      suffix: null\n",
        encoding="utf-8",
    )

    from config.load import load_config
    from config.schema import NumeratorConfig

    cfg = load_config(cwd=tmp_path)
    assert cfg.numerators == {"h": NumeratorConfig(suffix="")}


@pytest.mark.parametrize(
    ("yaml_text", "message"),
    [
        ("pandocster:\n  numerators:\n    - h\n", "numerators"),
        ("pandocster:\n  numerators:\n    bad-name: {}\n", "bad-name"),
        ("pandocster:\n  numerators:\n    h: []\n", "numerators.h"),
        ("pandocster:\n  numerators:\n    h:\n      suffix: 1\n", "suffix"),
        ("pandocster:\n  numerators:\n    h:\n      start: one\n", "start"),
        ("pandocster:\n  numerators:\n    h:\n      delimiter: 1\n", "delimiter"),
    ],
)
def test_load_config_rejects_invalid_numerators(
    tmp_path: Path, yaml_text: str, message: str
) -> None:
    (tmp_path / "pandocster.yaml").write_text(yaml_text, encoding="utf-8")

    from config.load import load_config

    with pytest.raises(ConfigError, match=message):
        load_config(cwd=tmp_path)


def test_config_to_dict_roundtrip_numerators() -> None:
    from config.schema import NumeratorConfig

    cfg = AppConfig(
        pandoc=PandocConfig(bin="pandoc", filters=[], metadata={}, options=[]),
        numerators={"h": NumeratorConfig(suffix="", start=5, delimiter="-")},
    )
    dumped = config_to_dict(cfg)
    assert dumped["pandocster"]["numerators"]["h"] == {
        "suffix": None,
        "start": 5,
        "delimiter": "-",
    }


def test_config_to_dict_omits_empty_numerators() -> None:
    cfg = AppConfig(
        pandoc=PandocConfig(bin="pandoc", filters=[], metadata={}, options=[]),
        numerators={},
    )
    assert "numerators" not in config_to_dict(cfg)["pandocster"]
