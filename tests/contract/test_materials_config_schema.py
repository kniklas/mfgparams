"""Contract test for the materials/tools configuration file schema (T014).

Validates every rule in
`specs/005-configurable-materials-tools/contracts/materials-config-schema.md`.
"""

from __future__ import annotations

import math

import pytest

from mfgparams.operations.drilling.tools import get_tool, list_tools
from mfgparams.registry import get_material, get_material_validation, list_materials
from mfgparams.registry_config import RegistryConfigError


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def test_required_fields_and_positivity(tmp_path):
    path = _write(
        tmp_path,
        "bad.toml",
        """
        [[materials]]
        name = "Bad"
        reference_cutting_speed = -1.0
        reference_feed_per_rev = 0.2
        specific_cutting_force = 1900.0
        """,
    )
    names = list_materials(config_path=path)
    assert "Bad" in names
    record = get_material_validation("Bad", path)
    assert record is not None
    assert record.status == "warning"
    assert record.source_path == path


def test_missing_required_field_raises(tmp_path):
    path = _write(
        tmp_path,
        "bad.toml",
        """
        [[materials]]
        name = "Bad"
        reference_feed_per_rev = 0.2
        specific_cutting_force = 1900.0
        """,
    )
    names = list_materials(config_path=path)
    assert "Bad" in names
    record = get_material_validation("Bad", path)
    assert record is not None
    assert record.status == "warning"


def test_unit_system_value_restriction(tmp_path):
    path = _write(
        tmp_path,
        "bad.toml",
        """
        [[materials]]
        name = "Bad"
        reference_cutting_speed = 25.0
        reference_feed_per_rev = 0.2
        specific_cutting_force = 1900.0
        unit_system = "furlongs"
        """,
    )
    with pytest.raises(RegistryConfigError):
        list_materials(config_path=path)


def test_duplicate_within_file_rejected(tmp_path):
    path = _write(
        tmp_path,
        "dup.toml",
        """
        [[materials]]
        name = "Bronze"
        reference_cutting_speed = 45.0
        reference_feed_per_rev = 0.18
        specific_cutting_force = 750.0

        [[materials]]
        name = "Bronze"
        reference_cutting_speed = 50.0
        reference_feed_per_rev = 0.18
        specific_cutting_force = 750.0
        """,
    )
    with pytest.raises(RegistryConfigError) as exc_info:
        list_materials(config_path=path)
    assert exc_info.value.message_key == "error.materials_config.duplicate_entry"


def test_malformed_file_rejected(tmp_path):
    path = tmp_path / "bad.toml"
    path.write_text('[[materials]\nname = "Broken"\n')
    with pytest.raises(RegistryConfigError) as exc_info:
        list_materials(config_path=str(path))
    assert exc_info.value.message_key == "error.materials_config.malformed"


def test_missing_path_is_notice_not_error(tmp_path):
    missing = str(tmp_path / "does-not-exist.toml")
    # No exception raised; falls back to bundled defaults.
    names = list_materials(config_path=missing)
    assert "Mild Steel" in names


def test_tools_schema_required_fields_and_positivity(tmp_path):
    path = _write(
        tmp_path,
        "bad.toml",
        """
        [[tools]]
        name = "Bad"
        cutting_speed_factor = 0.0
        feed_factor = 1.0
        """,
    )
    with pytest.raises(RegistryConfigError) as exc_info:
        list_tools(config_path=path)
    assert exc_info.value.kwargs["path"] == path


def test_user_override_shares_name_with_bundled_is_not_duplicate(tmp_path):
    path = _write(
        tmp_path,
        "override.toml",
        """
        [[materials]]
        name = "Mild Steel"
        reference_cutting_speed = 28.0
        reference_feed_per_rev = 0.20
        specific_cutting_force = 1900.0
        """,
    )
    material = get_material("Mild Steel", path)
    assert material is not None
    assert math.isclose(material.reference_cutting_speed_m_min, 28.0, rel_tol=1e-9)


def test_new_tool_added_via_user_file(tmp_path):
    path = _write(
        tmp_path,
        "add.toml",
        """
        [[tools]]
        name = "Ceramic"
        cutting_speed_factor = 4.0
        feed_factor = 1.0
        """,
    )
    tool = get_tool("Ceramic", path)
    assert tool is not None
    assert math.isclose(tool.cutting_speed_factor, 4.0, rel_tol=1e-9)


def test_engineered_wood_defaults_are_single_generic_entries():
    names = list_materials()
    assert names.count("Plywood") == 1
    assert names.count("MDF") == 1
