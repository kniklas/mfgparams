"""Unit tests for the TurningTool registry, mirroring
tests/unit/processes/machining/drilling/test_tools_registry.py.

Covers zero-config parity, override/append, partial-override via
``_STICKY_FIELDS`` (Copilot review finding: an override supplying only one
factor must keep the bundled value for the other, not raise
``RegistryConfigError``), display_name/translations, unit_system no-op, and
strict factor validation (missing/wrong-type/non-finite), matching milling's
`_tool_registry._to_tool` strictness.
"""

from __future__ import annotations

import math

import pytest

from mfgparams.processes.machining.turning.tools import (
    TOOL_REGISTRY,
    TurningTool,
    get_turning_tool,
    list_turning_tools,
)
from mfgparams.registry_config import RegistryConfigError

_EXPECTED_BUNDLED_TOOLS = {
    "HSS": (1.0, 1.0),
    "Cobalt": (1.2, 1.0),
    "Carbide": (2.4, 1.05),
}


# --- Zero-config regression parity ---


def test_list_turning_tools_zero_config_matches_bundled_names_and_values():
    names = list_turning_tools()
    assert names == list(_EXPECTED_BUNDLED_TOOLS.keys())
    for name, (speed_factor, feed_factor) in _EXPECTED_BUNDLED_TOOLS.items():
        tool = get_turning_tool(name)
        assert tool is not None
        assert math.isclose(tool.cutting_speed_factor, speed_factor, rel_tol=1e-9)
        assert math.isclose(tool.feed_factor, feed_factor, rel_tol=1e-9)


def test_get_turning_tool_zero_config_none_path_matches_no_config_path():
    assert get_turning_tool("Carbide", None) == get_turning_tool("Carbide")


def test_turning_tool_registry_names_unique_and_positive():
    names = list_turning_tools()
    assert len(names) == len(set(names))
    for tool in TOOL_REGISTRY.values():
        assert tool.cutting_speed_factor > 0
        assert tool.feed_factor > 0


# --- Override/append via user-supplied config file ---


def test_turning_tool_override_takes_effect(tmp_path):
    path = tmp_path / "override.toml"
    path.write_text(
        '[[turning_tools]]\nname = "Carbide"\ncutting_speed_factor = 3.0\nfeed_factor = 1.1\n'
    )
    overridden = get_turning_tool("Carbide", str(path))
    assert overridden is not None
    assert math.isclose(overridden.cutting_speed_factor, 3.0, rel_tol=1e-9)
    assert math.isclose(get_turning_tool("Carbide").cutting_speed_factor, 2.4, rel_tol=1e-9)


def test_turning_tool_append_new_name(tmp_path):
    path = tmp_path / "add.toml"
    path.write_text(
        '[[turning_tools]]\nname = "Ceramic"\ncutting_speed_factor = 4.0\nfeed_factor = 1.0\n'
    )
    names = list_turning_tools(config_path=str(path))
    assert "Ceramic" in names
    assert "HSS" in names
    assert "Ceramic" not in list_turning_tools()


def test_turning_tool_unaffected_built_ins_untouched(tmp_path):
    path = tmp_path / "override.toml"
    path.write_text(
        '[[turning_tools]]\nname = "Carbide"\ncutting_speed_factor = 3.0\nfeed_factor = 1.1\n'
    )
    hss = get_turning_tool("HSS", str(path))
    assert hss is not None
    assert math.isclose(hss.cutting_speed_factor, 1.0, rel_tol=1e-9)


# --- Partial override (sticky fields) — Copilot review finding ---


def test_partial_override_omitting_feed_factor_keeps_bundled_feed_factor(tmp_path):
    """An override supplying only `cutting_speed_factor` must not be
    rejected as missing `feed_factor` — the bundled entry's feed_factor
    carries over (contracts/turning-tools-config-schema.md: both factors
    are "optional when overriding")."""

    path = tmp_path / "override.toml"
    path.write_text('[[turning_tools]]\nname = "Carbide"\ncutting_speed_factor = 5.0\n')

    tool = get_turning_tool("Carbide", str(path))

    assert tool is not None
    assert math.isclose(tool.cutting_speed_factor, 5.0, rel_tol=1e-9)
    assert math.isclose(tool.feed_factor, 1.05, rel_tol=1e-9)  # bundled Carbide's own value


def test_partial_override_omitting_cutting_speed_factor_keeps_bundled_value(tmp_path):
    path = tmp_path / "override.toml"
    path.write_text('[[turning_tools]]\nname = "Carbide"\nfeed_factor = 2.0\n')

    tool = get_turning_tool("Carbide", str(path))

    assert tool is not None
    assert math.isclose(tool.cutting_speed_factor, 2.4, rel_tol=1e-9)  # bundled Carbide's own value
    assert math.isclose(tool.feed_factor, 2.0, rel_tol=1e-9)


def test_new_tool_still_requires_both_factors(tmp_path):
    """Sticky fields only carry over from a *matching bundled* entry
    (registry_config.merge_entries) — a brand-new tool name has nothing to
    inherit from, so both factors remain required for it."""

    path = tmp_path / "add.toml"
    path.write_text('[[turning_tools]]\nname = "Diamond"\ncutting_speed_factor = 6.0\n')

    with pytest.raises(RegistryConfigError) as exc_info:
        list_turning_tools(str(path))
    assert "feed_factor" in exc_info.value.kwargs["details"]


# --- display_name / translations ---


def test_turning_tool_display_name_returns_translation_when_present():
    tool = TurningTool("Test", 1.0, 1.0, translations={"fr": "Essai"})
    assert tool.display_name("fr") == "Essai"


def test_turning_tool_display_name_falls_back_to_english_when_locale_absent():
    tool = TurningTool("Test", 1.0, 1.0, translations={"fr": "Essai"})
    assert tool.display_name("de") == "Test"


def test_turning_tool_display_name_falls_back_to_english_when_no_translations():
    tool = TurningTool("Test", 1.0, 1.0)
    assert tool.display_name("fr") == "Test"


# --- unit_system accepted/stored but no-op for tools ---


def test_turning_tool_imperial_unit_system_accepted_but_no_conversion(tmp_path):
    path = tmp_path / "imperial.toml"
    path.write_text(
        '[[turning_tools]]\nname = "Imperial Tool"\ncutting_speed_factor = 2.0\n'
        'feed_factor = 1.0\nunit_system = "imperial"\n'
    )
    tool = get_turning_tool("Imperial Tool", str(path))
    assert tool is not None
    assert tool.unit_system == "imperial"
    assert math.isclose(tool.cutting_speed_factor, 2.0, rel_tol=1e-9)
    assert math.isclose(tool.feed_factor, 1.0, rel_tol=1e-9)


# --- Strict factor validation ---


def test_turning_tool_missing_field_raises_registry_config_error(tmp_path):
    path = tmp_path / "missing_field.toml"
    path.write_text('[[turning_tools]]\nname = "Incomplete"\ncutting_speed_factor = 2.0\n')
    with pytest.raises(RegistryConfigError) as exc_info:
        list_turning_tools(str(path))
    assert exc_info.value.kwargs["path"] == str(path)


def test_turning_tool_non_positive_factor_is_rejected(tmp_path):
    path = tmp_path / "override.toml"
    path.write_text(
        '[[turning_tools]]\nname = "HSS"\ncutting_speed_factor = -1.0\nfeed_factor = 1.0\n'
    )
    with pytest.raises(RegistryConfigError) as exc_info:
        get_turning_tool("HSS", str(path))
    assert exc_info.value.kwargs["path"] == str(path)


def test_turning_tool_non_numeric_string_field_is_rejected(tmp_path):
    path = tmp_path / "wrong_type.toml"
    path.write_text(
        '[[turning_tools]]\nname = "Bad Type"\ncutting_speed_factor = "fast"\nfeed_factor = 1.0\n'
    )
    with pytest.raises(RegistryConfigError) as exc_info:
        get_turning_tool("Bad Type", str(path))
    assert exc_info.value.message_key == "error.materials_config.invalid_entry"
    assert exc_info.value.kwargs["path"] == str(path)


def test_turning_tool_quoted_numeric_string_is_rejected(tmp_path):
    """`"1.8"` must not silently pass through `float()` as if it were the
    TOML number `1.8` — the schema requires a raw number (Copilot review
    finding)."""

    path = tmp_path / "quoted_number.toml"
    path.write_text(
        '[[turning_tools]]\nname = "Bad Type"\ncutting_speed_factor = "1.8"\nfeed_factor = 1.0\n'
    )
    with pytest.raises(RegistryConfigError) as exc_info:
        get_turning_tool("Bad Type", str(path))
    assert "cutting_speed_factor" in exc_info.value.kwargs["details"]


def test_turning_tool_boolean_field_is_rejected(tmp_path):
    """A TOML boolean is a bool subtype of int and would otherwise pass
    silently through `float()` (`true` -> `1.0`) (Copilot review finding)."""

    path = tmp_path / "boolean.toml"
    path.write_text(
        '[[turning_tools]]\nname = "Bad Type"\ncutting_speed_factor = true\nfeed_factor = 1.0\n'
    )
    with pytest.raises(RegistryConfigError) as exc_info:
        get_turning_tool("Bad Type", str(path))
    assert "cutting_speed_factor" in exc_info.value.kwargs["details"]


@pytest.mark.parametrize("literal", ["nan", "inf", "-inf"])
def test_turning_tool_non_finite_field_is_rejected(tmp_path, literal):
    """TOML supports `nan`/`inf`/`-inf` float literals directly; a
    hand-edited config could otherwise register one and silently poison
    every calculation using this tool (Copilot review finding)."""

    path = tmp_path / "non_finite.toml"
    path.write_text(
        f'[[turning_tools]]\nname = "Bad Type"\n'
        f"cutting_speed_factor = {literal}\nfeed_factor = 1.0\n"
    )
    with pytest.raises(RegistryConfigError) as exc_info:
        get_turning_tool("Bad Type", str(path))
    assert "cutting_speed_factor" in exc_info.value.kwargs["details"]
