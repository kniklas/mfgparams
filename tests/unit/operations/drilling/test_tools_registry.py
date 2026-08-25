"""Unit tests for the drilling-tool registry (T016), mirroring test_registry.py.

Covers User Story 1 (zero-config parity), User Story 2 (override/append),
User Story 3 (display_name), and User Story 4 (unit_system no-op for tools).
"""

from __future__ import annotations

import math

import pytest

from mfgparams.operations.drilling.tools import TOOL_REGISTRY, DrillingTool, get_tool, list_tools
from mfgparams.registry_config import RegistryConfigError

_EXPECTED_BUNDLED_TOOLS = {
    "HSS": (1.0, 1.0),
    "Cobalt": (1.15, 1.0),
    "Carbide": (2.5, 1.1),
}


# --- User Story 1: zero-config regression parity (T016) ---


def test_list_tools_zero_config_matches_pre_feature_names_and_values():
    names = list_tools()
    assert names == list(_EXPECTED_BUNDLED_TOOLS.keys())
    for name, (speed_factor, feed_factor) in _EXPECTED_BUNDLED_TOOLS.items():
        tool = get_tool(name)
        assert tool is not None
        assert math.isclose(tool.cutting_speed_factor, speed_factor, rel_tol=1e-9)
        assert math.isclose(tool.feed_factor, feed_factor, rel_tol=1e-9)


def test_get_tool_zero_config_none_path_matches_no_config_path():
    assert get_tool("Carbide", None) == get_tool("Carbide")


def test_tool_registry_names_unique_and_positive():
    names = list_tools()
    assert len(names) == len(set(names))
    for tool in TOOL_REGISTRY.values():
        assert tool.cutting_speed_factor > 0
        assert tool.feed_factor > 0


# --- User Story 2: override/append via user-supplied config file (T027) ---


def test_tool_override_takes_effect(tmp_path):
    path = tmp_path / "override.toml"
    path.write_text("""
        [[tools]]
        name = "Carbide"
        cutting_speed_factor = 3.0
        feed_factor = 1.1
        """)
    overridden = get_tool("Carbide", str(path))
    assert overridden is not None
    assert math.isclose(overridden.cutting_speed_factor, 3.0, rel_tol=1e-9)
    assert math.isclose(get_tool("Carbide").cutting_speed_factor, 2.5, rel_tol=1e-9)


def test_tool_append_new_name(tmp_path):
    path = tmp_path / "add.toml"
    path.write_text("""
        [[tools]]
        name = "Ceramic"
        cutting_speed_factor = 4.0
        feed_factor = 1.0
        """)
    names = list_tools(config_path=str(path))
    assert "Ceramic" in names
    assert "HSS" in names
    assert "Ceramic" not in list_tools()


def test_tool_unaffected_built_ins_untouched(tmp_path):
    path = tmp_path / "override.toml"
    path.write_text("""
        [[tools]]
        name = "Carbide"
        cutting_speed_factor = 3.0
        feed_factor = 1.1
        """)
    hss = get_tool("HSS", str(path))
    assert hss is not None
    assert math.isclose(hss.cutting_speed_factor, 1.0, rel_tol=1e-9)


# --- User Story 3: display_name / translations (T035) ---


def test_tool_display_name_returns_translation_when_present():
    tool = DrillingTool("Test", 1.0, 1.0, translations={"fr": "Essai"})
    assert tool.display_name("fr") == "Essai"


def test_tool_display_name_falls_back_to_english_when_locale_absent():
    tool = DrillingTool("Test", 1.0, 1.0, translations={"fr": "Essai"})
    assert tool.display_name("de") == "Test"


def test_tool_display_name_falls_back_to_english_when_no_translations():
    tool = DrillingTool("Test", 1.0, 1.0)
    assert tool.display_name("fr") == "Test"


# --- User Story 4: unit_system accepted/stored but no-op for tools (T041) ---


def test_tool_imperial_unit_system_accepted_but_no_conversion(tmp_path):
    path = tmp_path / "imperial.toml"
    path.write_text("""
        [[tools]]
        name = "Imperial Tool"
        cutting_speed_factor = 2.0
        feed_factor = 1.0
        unit_system = "imperial"
        """)
    tool = get_tool("Imperial Tool", str(path))
    assert tool is not None
    assert tool.unit_system == "imperial"
    # No conversion applied - factors are dimensionless (research.md #5).
    assert math.isclose(tool.cutting_speed_factor, 2.0, rel_tol=1e-9)
    assert math.isclose(tool.feed_factor, 1.0, rel_tol=1e-9)


def test_tool_invalid_entry_raises_registry_config_error(tmp_path):
    path = tmp_path / "missing_field.toml"
    path.write_text("""
        [[tools]]
        name = "Incomplete"
        cutting_speed_factor = 2.0
        """)
    with pytest.raises(RegistryConfigError) as exc_info:
        get_tool("Incomplete", str(path))
    # The error must point at the user file that actually defined the
    # invalid entry, not the bundled tools.toml (Copilot review fix).
    assert exc_info.value.kwargs["path"] == str(path)


def test_tool_invalid_override_entry_reports_user_path_not_bundled(tmp_path):
    path = tmp_path / "override.toml"
    path.write_text("""
        [[tools]]
        name = "HSS"
        cutting_speed_factor = -1.0
        feed_factor = 1.0
        """)
    with pytest.raises(RegistryConfigError) as exc_info:
        get_tool("HSS", str(path))
    assert exc_info.value.kwargs["path"] == str(path)
    assert exc_info.value.kwargs["path"] != "tools.toml"


def test_tool_wrong_type_field_raises_registry_config_error(tmp_path):
    path = tmp_path / "wrong_type.toml"
    path.write_text("""
        [[tools]]
        name = "Bad Type"
        cutting_speed_factor = "not-a-number"
        feed_factor = 1.0
        """)
    with pytest.raises(RegistryConfigError) as exc_info:
        get_tool("Bad Type", str(path))
    assert exc_info.value.message_key == "error.materials_config.invalid_entry"
    assert exc_info.value.kwargs["path"] == str(path)
