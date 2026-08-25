"""Unit tests for the material and drilling-tool registries."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from mfgparams.operations.drilling.tools import TOOL_REGISTRY, get_tool, list_tools
from mfgparams.registry import (
    MATERIAL_REGISTRY,
    WorkpieceMaterial,
    get_material,
    get_material_validation,
    list_materials,
)
from mfgparams.registry_config import RegistryConfigError

_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "materials"
_INVALID_FIXTURE = _FIXTURES_DIR / "wood-invalid-params.toml"

_EXPECTED_BUNDLED_MATERIALS = {
    "Mild Steel": (25.0, 0.20, 1900.0),
    "Stainless Steel": (15.0, 0.15, 2400.0),
    "Aluminum": (60.0, 0.25, 700.0),
    "Cast Iron": (20.0, 0.20, 1500.0),
    "Brass": (45.0, 0.20, 800.0),
    "Titanium": (12.0, 0.10, 2100.0),
    "Oak": (35.0, 0.22, 1200.0),
    "Maple": (40.0, 0.24, 1100.0),
    "Pine": (70.0, 0.30, 650.0),
    "Spruce": (65.0, 0.28, 700.0),
    "Fir": (60.0, 0.27, 750.0),
    "Plywood": (55.0, 0.23, 900.0),
    "MDF": (45.0, 0.20, 1000.0),
}


def test_material_names_are_unique():
    names = list_materials()
    assert len(names) == len(set(names))
    assert len(names) >= 1


def test_all_materials_have_positive_reference_values():
    for material in MATERIAL_REGISTRY.values():
        assert material.reference_cutting_speed_m_min > 0
        assert material.reference_feed_per_rev_mm > 0
        assert material.specific_cutting_force_kc > 0


def test_get_material_returns_none_for_unknown():
    assert get_material("Unobtainium") is None


def test_get_material_returns_expected_entry():
    material = get_material("Mild Steel")
    assert material is not None
    assert material.name == "Mild Steel"


def test_tool_names_are_unique():
    names = list_tools()
    assert len(names) == len(set(names))
    assert len(names) >= 1


def test_all_tools_have_positive_factors():
    for tool in TOOL_REGISTRY.values():
        assert tool.cutting_speed_factor > 0
        assert tool.feed_factor > 0


def test_get_tool_returns_none_for_unknown():
    assert get_tool("Diamond-Coated Unobtainium") is None


def test_get_tool_returns_expected_entry():
    tool = get_tool("Carbide")
    assert tool is not None
    assert tool.name == "Carbide"


def test_material_validate_rejects_non_positive_fields():
    from mfgparams.registry import _validate as validate_material

    assert "reference_cutting_speed_m_min must be positive" in validate_material(
        WorkpieceMaterial("Bad", 0, 0.2, 1900.0)
    )
    assert "reference_feed_per_rev_mm must be positive" in validate_material(
        WorkpieceMaterial("Bad", 25.0, 0, 1900.0)
    )
    assert "specific_cutting_force_kc must be positive" in validate_material(
        WorkpieceMaterial("Bad", 25.0, 0.2, 0)
    )


def test_tool_validate_rejects_non_positive_fields():
    from mfgparams.operations.drilling.tools import DrillingTool
    from mfgparams.operations.drilling.tools import _validate as validate_tool

    with pytest.raises(RegistryConfigError):
        validate_tool(DrillingTool("Bad", 0, 1.0))
    with pytest.raises(RegistryConfigError):
        validate_tool(DrillingTool("Bad", 1.0, 0))


def test_list_materials_zero_config_matches_expected_names_and_values():
    names = list_materials()
    assert names == list(_EXPECTED_BUNDLED_MATERIALS.keys())
    for name, (speed, feed, force) in _EXPECTED_BUNDLED_MATERIALS.items():
        material = get_material(name)
        assert material is not None
        assert math.isclose(material.reference_cutting_speed_m_min, speed, rel_tol=1e-9)
        assert math.isclose(material.reference_feed_per_rev_mm, feed, rel_tol=1e-9)
        assert math.isclose(material.specific_cutting_force_kc, force, rel_tol=1e-9)


def test_get_material_zero_config_none_path_matches_no_config_path():
    assert get_material("Mild Steel", None) == get_material("Mild Steel")


def test_material_override_takes_effect(tmp_path):
    path = tmp_path / "override.toml"
    path.write_text("""
        [[materials]]
        name = "Mild Steel"
        reference_cutting_speed = 28.0
        reference_feed_per_rev = 0.20
        specific_cutting_force = 1900.0
        """)
    overridden = get_material("Mild Steel", str(path))
    assert overridden is not None
    assert math.isclose(overridden.reference_cutting_speed_m_min, 28.0, rel_tol=1e-9)
    default_material = get_material("Mild Steel")
    assert math.isclose(default_material.reference_cutting_speed_m_min, 25.0, rel_tol=1e-9)


def test_material_append_new_name(tmp_path):
    path = tmp_path / "add.toml"
    path.write_text("""
        [[materials]]
        name = "Bronze"
        reference_cutting_speed = 45.0
        reference_feed_per_rev = 0.18
        specific_cutting_force = 750.0
        """)
    names = list_materials(config_path=str(path))
    assert "Bronze" in names
    assert "Mild Steel" in names
    assert "Bronze" not in list_materials()


def test_material_unaffected_built_ins_untouched(tmp_path):
    path = tmp_path / "override.toml"
    path.write_text("""
        [[materials]]
        name = "Mild Steel"
        reference_cutting_speed = 28.0
        reference_feed_per_rev = 0.20
        specific_cutting_force = 1900.0
        """)
    aluminum = get_material("Aluminum", str(path))
    assert aluminum is not None
    assert math.isclose(aluminum.reference_cutting_speed_m_min, 60.0, rel_tol=1e-9)


def test_material_config_omitting_flag_reproduces_zero_config():
    assert list_materials(config_path=None) == list_materials()


def test_display_name_returns_translation_when_present():
    material = WorkpieceMaterial("Test", 1.0, 1.0, 1.0, translations={"fr": "Essai"})
    assert material.display_name("fr") == "Essai"


def test_display_name_falls_back_to_english_when_locale_absent():
    material = WorkpieceMaterial("Test", 1.0, 1.0, 1.0, translations={"fr": "Essai"})
    assert material.display_name("de") == "Test"


def test_display_name_falls_back_to_english_when_no_translations():
    material = WorkpieceMaterial("Test", 1.0, 1.0, 1.0)
    assert material.display_name("fr") == "Test"


def test_translation_merge_preserves_untouched_locale(tmp_path):
    path = tmp_path / "translations.toml"
    path.write_text("""
        [[materials]]
        name = "Mild Steel"
        reference_cutting_speed = 25.0
        reference_feed_per_rev = 0.20
        specific_cutting_force = 1900.0

        [materials.translations]
        de = "Weichstahl"
        """)
    material = get_material("Mild Steel", str(path))
    assert material is not None
    assert material.translations.get("de") == "Weichstahl"


def test_imperial_declared_material_converts_to_expected_metric(tmp_path):
    path = tmp_path / "imperial.toml"
    path.write_text("""
        [[materials]]
        name = "Bronze Imperial"
        reference_cutting_speed = 250.0
        reference_feed_per_rev = 0.008
        specific_cutting_force = 130000.0
        unit_system = "imperial"
        """)
    material = get_material("Bronze Imperial", str(path))
    assert material is not None
    assert material.unit_system == "imperial"
    assert math.isclose(material.reference_cutting_speed_m_min, 76.2, rel_tol=1e-3)
    assert math.isclose(material.reference_feed_per_rev_mm, 0.2032, rel_tol=1e-3)
    assert math.isclose(material.specific_cutting_force_kc, 896.3, rel_tol=1e-3)


def test_imperial_declared_material_matches_metric_authored_equivalent(tmp_path):
    path = tmp_path / "imperial.toml"
    path.write_text("""
        [[materials]]
        name = "Bronze Imperial"
        reference_cutting_speed = 250.0
        reference_feed_per_rev = 0.008
        specific_cutting_force = 130000.0
        unit_system = "imperial"

        [[materials]]
        name = "Bronze Metric"
        reference_cutting_speed = 76.2
        reference_feed_per_rev = 0.2032
        specific_cutting_force = 896.3
        """)
    imperial = get_material("Bronze Imperial", str(path))
    metric = get_material("Bronze Metric", str(path))
    assert imperial is not None and metric is not None
    assert math.isclose(
        imperial.reference_cutting_speed_m_min,
        metric.reference_cutting_speed_m_min,
        rel_tol=1e-3,
    )
    assert math.isclose(
        imperial.reference_feed_per_rev_mm, metric.reference_feed_per_rev_mm, rel_tol=1e-3
    )
    assert math.isclose(
        imperial.specific_cutting_force_kc, metric.specific_cutting_force_kc, rel_tol=1e-3
    )


def test_wood_hardwood_presence_and_positive_parameters():
    for name in ("Oak", "Maple"):
        material = get_material(name)
        assert material is not None
        assert material.reference_cutting_speed_m_min > 0
        assert material.reference_feed_per_rev_mm > 0
        assert material.specific_cutting_force_kc > 0


def test_wood_softwood_presence_and_distinct_from_hardwoods():
    oak = get_material("Oak")
    maple = get_material("Maple")
    assert oak is not None
    assert maple is not None
    hardwood_speeds = {oak.reference_cutting_speed_m_min, maple.reference_cutting_speed_m_min}
    for name in ("Pine", "Spruce", "Fir"):
        material = get_material(name)
        assert material is not None
        assert material.reference_cutting_speed_m_min not in hardwood_speeds


def test_engineered_wood_single_entry_types():
    names = list_materials()
    assert names.count("Plywood") == 1
    assert names.count("MDF") == 1


def test_all_built_in_wood_materials_declare_metric_unit_system():
    for name in ("Oak", "Maple", "Pine", "Spruce", "Fir", "Plywood", "MDF"):
        material = get_material(name)
        assert material is not None
        assert material.unit_system == "metric"


def test_invalid_material_entries_are_registered_with_warning_metadata(caplog, tmp_path):
    fixture = tmp_path / "wood-invalid-params.toml"
    fixture.write_text(_INVALID_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    caplog.set_level("WARNING")
    names = list_materials(config_path=str(fixture))
    assert "Oak" in names
    assert "Pine" in names
    assert "Spruce" in names

    oak_validation = get_material_validation("Oak", str(fixture))
    pine_validation = get_material_validation("Pine", str(fixture))
    spruce_validation = get_material_validation("Spruce", str(fixture))
    assert oak_validation is not None
    assert pine_validation is not None
    assert spruce_validation is not None
    assert oak_validation.status == "warning"
    assert pine_validation.status == "warning"
    assert spruce_validation.status == "warning"
    assert str(fixture) in caplog.text


def test_non_finite_numeric_fields_are_marked_as_warnings(tmp_path):
    path = tmp_path / "non_finite.toml"
    path.write_text("""
        [[materials]]
        name = "Infinite Oak"
        reference_cutting_speed = inf
        reference_feed_per_rev = 0.22
        specific_cutting_force = 1200.0
        """)
    names = list_materials(config_path=str(path))
    assert "Infinite Oak" in names

    material = get_material("Infinite Oak", str(path))
    assert material is not None
    assert not material.is_usable

    record = get_material_validation("Infinite Oak", str(path))
    assert record is not None
    assert record.status == "warning"
    assert "must be finite" in " ".join(record.issues)


def test_is_usable_true_for_all_built_in_materials():
    for name in list_materials():
        material = get_material(name)
        assert material is not None
        assert material.is_usable


def test_is_usable_false_for_invalid_entries(tmp_path):
    fixture = tmp_path / "wood-invalid-params.toml"
    fixture.write_text(_INVALID_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    for name in ("Oak", "Pine", "Spruce"):
        material = get_material(name, str(fixture))
        assert material is not None
        assert not material.is_usable


def test_is_usable_false_for_non_positive_field():
    assert not WorkpieceMaterial("Bad", 0.0, 1.0, 1.0).is_usable
    assert not WorkpieceMaterial("Bad", 1.0, -1.0, 1.0).is_usable
    assert not WorkpieceMaterial("Bad", 1.0, 1.0, float("nan")).is_usable
