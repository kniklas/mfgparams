"""Unit tests for the FaceMillTool registry (T030).

Covers bundled defaults, user-config override/append via ``registry_config``,
and rejection of an invalid ``cutting_speed_factor``.
"""

from __future__ import annotations

import math

import pytest

from mfgparams.operations.milling.face_milling.tools import (
    FACE_MILL_TOOL_REGISTRY,
    FaceMillTool,
    get_face_mill_tool,
    list_face_mill_tools,
)
from mfgparams.registry_config import RegistryConfigError, clear_cache

_EXPECTED_BUNDLED_TOOLS = {"HSS": 1.0, "Carbide": 2.5, "Coated Carbide": 3.0, "Cermet": 3.5}

_TABLE = "face_mill_tools"


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    """``load_and_merge`` is cached per (path, table); isolate each test."""

    clear_cache()
    yield
    clear_cache()


def _write(tmp_path, body: str) -> str:
    path = tmp_path / "tools.toml"
    path.write_text(body)
    return str(path)


def test_bundled_tools_load_with_no_configuration():
    assert list_face_mill_tools() == list(_EXPECTED_BUNDLED_TOOLS)
    for name, factor in _EXPECTED_BUNDLED_TOOLS.items():
        tool = get_face_mill_tool(name)
        assert isinstance(tool, FaceMillTool)
        assert math.isclose(tool.cutting_speed_factor, factor, rel_tol=1e-9)


def test_registry_entries_are_unique_and_positive():
    names = list_face_mill_tools()
    assert len(names) == len(set(names))
    assert all(tool.cutting_speed_factor > 0 for tool in FACE_MILL_TOOL_REGISTRY.values())


def test_unknown_tool_resolves_to_none():
    assert get_face_mill_tool("No Such Tool") is None


def test_explicit_none_config_path_matches_the_zero_config_lookup():
    assert get_face_mill_tool("Carbide", None) == get_face_mill_tool("Carbide")


def test_user_config_can_override_a_bundled_tool(tmp_path):
    path = _write(tmp_path, f'[[{_TABLE}]]\nname = "Carbide"\ncutting_speed_factor = 9.0\n')

    tool = get_face_mill_tool("Carbide", path)

    assert math.isclose(tool.cutting_speed_factor, 9.0, rel_tol=1e-9)
    # The bundled registry object itself is untouched.
    assert not math.isclose(
        FACE_MILL_TOOL_REGISTRY["Carbide"].cutting_speed_factor, 9.0, rel_tol=1e-9
    )


def test_user_config_can_append_a_new_tool(tmp_path):
    path = _write(tmp_path, f'[[{_TABLE}]]\nname = "Diamond"\ncutting_speed_factor = 6.0\n')

    names = list_face_mill_tools(path)

    assert names[: len(_EXPECTED_BUNDLED_TOOLS)] == list(_EXPECTED_BUNDLED_TOOLS)
    assert "Diamond" in names
    assert math.isclose(get_face_mill_tool("Diamond", path).cutting_speed_factor, 6.0, rel_tol=1e-9)


def test_translations_are_carried_through(tmp_path):
    path = _write(
        tmp_path,
        f'[[{_TABLE}]]\nname = "Carbide"\ncutting_speed_factor = 2.5\n'
        f'[{_TABLE}.translations]\npl = "Weglik"\n',
    )

    tool = get_face_mill_tool("Carbide", path)

    assert tool.display_name("pl") == "Weglik"
    assert tool.display_name("en") == "Carbide"
    assert tool.display_name("de") == "Carbide"


@pytest.mark.parametrize("factor", ["0", "-1.0"])
def test_non_positive_cutting_speed_factor_is_rejected(tmp_path, factor):
    path = _write(tmp_path, f'[[{_TABLE}]]\nname = "Bad"\ncutting_speed_factor = {factor}\n')

    with pytest.raises(RegistryConfigError) as excinfo:
        list_face_mill_tools(path)

    assert "cutting_speed_factor" in excinfo.value.kwargs["details"]


def test_missing_cutting_speed_factor_is_rejected(tmp_path):
    path = _write(tmp_path, f'[[{_TABLE}]]\nname = "Bad"\n')

    with pytest.raises(RegistryConfigError) as excinfo:
        list_face_mill_tools(path)

    assert "cutting_speed_factor" in excinfo.value.kwargs["details"]


def test_non_numeric_cutting_speed_factor_is_rejected(tmp_path):
    path = _write(tmp_path, f'[[{_TABLE}]]\nname = "Bad"\ncutting_speed_factor = "fast"\n')

    with pytest.raises(RegistryConfigError) as excinfo:
        list_face_mill_tools(path)

    assert "cutting_speed_factor" in excinfo.value.kwargs["details"]


def test_milling_tools_need_no_feed_factor(tmp_path):
    """Feed per tooth is a direct input, not a registry multiplier (research.md #4)."""

    path = _write(tmp_path, f'[[{_TABLE}]]\nname = "Fine"\ncutting_speed_factor = 1.5\n')

    tool = get_face_mill_tool("Fine", path)

    assert not hasattr(tool, "feed_factor")
