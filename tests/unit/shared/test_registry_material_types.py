"""Unit tests for material categorization (specs/008-material-categorization).

Covers the registry-level half of the two-step type-then-material selection
flow: the ``WorkpieceMaterial.material_type`` field, the
``list_material_types`` query, the ``material_type`` filter on
``list_materials``, and the data-driven extensibility/backward-compatibility
guarantees (008 FR-001, FR-002, FR-004, FR-005, FR-006, FR-010, FR-011).
"""

from __future__ import annotations

import pytest

from mfgparams.registry import (
    DEFAULT_MATERIAL_TYPE,
    get_material,
    get_material_validation,
    list_material_types,
    list_materials,
)

_METALS = ("Mild Steel", "Stainless Steel", "Aluminum", "Cast Iron", "Brass", "Titanium")
_WOODS = ("Oak", "Maple", "Pine", "Spruce", "Fir", "Plywood", "MDF")


def _write_config(tmp_path, body: str) -> str:
    """Write ``body`` to a user materials config file and return its path."""

    path = tmp_path / "user-materials.toml"
    path.write_text(body, encoding="utf-8")
    return str(path)


class TestBundledCategorization:
    """The bundled registry is fully categorized into metal and wood (FR-001)."""

    def test_lists_exactly_metal_and_wood(self):
        assert list_material_types() == ["metal", "wood"]

    @pytest.mark.parametrize("name", _METALS)
    def test_metals_are_categorized_as_metal(self, name):
        assert get_material(name).material_type == "metal"

    @pytest.mark.parametrize("name", _WOODS)
    def test_woods_are_categorized_as_wood(self, name):
        assert get_material(name).material_type == "wood"

    def test_no_bundled_material_is_uncategorized(self):
        uncategorized = [
            name
            for name in list_materials()
            if get_material(name).material_type == DEFAULT_MATERIAL_TYPE
        ]
        assert uncategorized == []


class TestListMaterialsFiltering:
    """``list_materials(material_type=...)`` narrows to one category (FR-002)."""

    def test_filter_returns_only_that_category(self):
        assert list_materials(material_type="metal") == list(_METALS)
        assert list_materials(material_type="wood") == list(_WOODS)

    def test_filtered_lists_partition_the_full_list(self):
        combined = list_materials(material_type="metal") + list_materials(material_type="wood")
        assert sorted(combined) == sorted(list_materials())

    def test_omitting_filter_preserves_pre_008_behavior(self):
        """The added keyword argument must not change the default call (FR-014 of 005)."""

        assert list_materials() == list(_METALS) + list(_WOODS)

    def test_unknown_category_returns_empty_list_without_raising(self):
        """A stale/removed category degrades gracefully rather than erroring (FR-011)."""

        assert list_materials(material_type="does-not-exist") == []

    def test_filter_preserves_registration_order(self):
        """Display order is configurable via TOML entry order (FR-010)."""

        assert list_materials(material_type="wood")[0] == "Oak"
        assert list_materials(material_type="wood")[-1] == "MDF"


class TestDataDrivenExtensibility:
    """New categories come from data alone, with no code change (FR-004, FR-005)."""

    def test_new_category_is_registered_from_user_config(self, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Portland Cement"
material_type = "cement"
reference_cutting_speed = 30.0
reference_feed_per_rev = 0.15
specific_cutting_force = 1400.0
""",
        )

        assert "cement" in list_material_types(config_path)
        assert list_materials(config_path, material_type="cement") == ["Portland Cement"]
        assert get_material("Portland Cement", config_path).material_type == "cement"

    def test_new_category_is_appended_after_bundled_ones(self, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "ABS"
material_type = "plastic"
reference_cutting_speed = 80.0
reference_feed_per_rev = 0.30
specific_cutting_force = 400.0
""",
        )

        assert list_material_types(config_path) == ["metal", "wood", "plastic"]

    def test_material_can_be_added_to_an_existing_category(self, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Bronze"
material_type = "metal"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
""",
        )

        assert list_material_types(config_path) == ["metal", "wood"]
        assert "Bronze" in list_materials(config_path, material_type="metal")


class TestBackwardCompatibility:
    """Config files written before ``material_type`` existed still work (FR-011)."""

    def test_new_material_without_type_falls_back_to_default(self, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Bronze"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
""",
        )

        assert get_material("Bronze", config_path).material_type == DEFAULT_MATERIAL_TYPE
        assert DEFAULT_MATERIAL_TYPE in list_material_types(config_path)

    def test_override_without_type_keeps_the_bundled_category(self, tmp_path):
        """``material_type`` is sticky, so an override does not silently decategorize."""

        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Oak"
reference_cutting_speed = 36.0
reference_feed_per_rev = 0.22
specific_cutting_force = 1200.0
""",
        )

        material = get_material("Oak", config_path)
        assert material.material_type == "wood"
        # The override's numeric value still wins; only the category is sticky.
        assert material.reference_cutting_speed_m_min == 36.0
        assert DEFAULT_MATERIAL_TYPE not in list_material_types(config_path)

    def test_override_can_explicitly_recategorize(self, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Oak"
material_type = "engineered"
reference_cutting_speed = 35.0
reference_feed_per_rev = 0.22
specific_cutting_force = 1200.0
""",
        )

        assert get_material("Oak", config_path).material_type == "engineered"
        assert "Oak" not in list_materials(config_path, material_type="wood")


class TestInvalidMaterialType:
    """An invalid ``material_type`` warns and continues, per FR-008 of 005."""

    @pytest.mark.parametrize("raw_value", ["123", '""', "true"])
    def test_non_string_or_empty_type_falls_back_and_records_issue(self, tmp_path, raw_value):
        config_path = _write_config(
            tmp_path,
            f"""
[[materials]]
name = "Odd"
material_type = {raw_value}
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
""",
        )

        material = get_material("Odd", config_path)
        assert material.material_type == DEFAULT_MATERIAL_TYPE
        # The material stays usable and selectable despite the bad category.
        assert material.is_usable

        record = get_material_validation("Odd", config_path)
        assert record.status == "warning"
        assert any("material_type" in issue for issue in record.issues)

    def test_surrounding_whitespace_is_stripped(self, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Spaced"
material_type = "  metal  "
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
""",
        )

        assert get_material("Spaced", config_path).material_type == "metal"
        assert "Spaced" in list_materials(config_path, material_type="metal")


class TestMultilineMaterialTypeRejected:
    """Control characters in a type id would make it unselectable (FR-006a)."""

    def test_multiline_material_type_falls_back_to_default(self, tmp_path):
        """A TOML multiline id is rejected rather than offered as a prompt option.

        `input()` returns a single line, so an option containing a newline
        could never be entered and the CLI would re-prompt forever.
        """
        config_path = tmp_path / "materials.toml"
        config_path.write_text(
            "[[materials]]\n"
            'name = "Bronze"\n'
            'material_type = """metal\nalloy"""\n'
            "reference_cutting_speed = 45.0\n"
            "reference_feed_per_rev = 0.18\n"
            "specific_cutting_force = 750.0\n",
            encoding="utf-8",
        )

        types = list_material_types(config_path=str(config_path))

        assert all("\n" not in material_type for material_type in types), types
        assert "metal\nalloy" not in types
        assert DEFAULT_MATERIAL_TYPE in types
        assert "Bronze" in list_materials(
            config_path=str(config_path), material_type=DEFAULT_MATERIAL_TYPE
        )

    def test_tab_in_material_type_falls_back_to_default(self, tmp_path):
        """Interior tabs are control characters too and are rejected alike."""
        config_path = tmp_path / "materials.toml"
        config_path.write_text(
            "[[materials]]\n"
            'name = "Bronze"\n'
            'material_type = "met\\tal"\n'
            "reference_cutting_speed = 45.0\n"
            "reference_feed_per_rev = 0.18\n"
            "specific_cutting_force = 750.0\n",
            encoding="utf-8",
        )

        types = list_material_types(config_path=str(config_path))

        assert all("\t" not in material_type for material_type in types), types
        assert DEFAULT_MATERIAL_TYPE in types

    def test_c1_control_in_material_type_falls_back_to_default(self, tmp_path):
        """Non-whitespace C1 controls are rejected too, not just line breaks.

        U+009B is not whitespace, so a whitespace-based check would let it
        through and emit a terminal control sequence straight into the prompt.
        """
        config_path = tmp_path / "materials.toml"
        config_path.write_text(
            "[[materials]]\n"
            'name = "Bronze"\n'
            'material_type = "met\\u009Bal"\n'
            "reference_cutting_speed = 45.0\n"
            "reference_feed_per_rev = 0.18\n"
            "specific_cutting_force = 750.0\n",
            encoding="utf-8",
        )

        types = list_material_types(config_path=str(config_path))

        assert all("\u009b" not in material_type for material_type in types), types
        assert DEFAULT_MATERIAL_TYPE in types

    def test_non_breaking_space_in_material_type_is_allowed(self, tmp_path):
        """Printable non-ASCII spacing stays valid — it is selectable and single-line."""
        config_path = tmp_path / "materials.toml"
        config_path.write_text(
            "[[materials]]\n"
            'name = "Bronze"\n'
            'material_type = "light\\u00A0metal"\n'
            "reference_cutting_speed = 45.0\n"
            "reference_feed_per_rev = 0.18\n"
            "specific_cutting_force = 750.0\n",
            encoding="utf-8",
        )

        assert "light\u00a0metal" in list_material_types(config_path=str(config_path))

    def test_interior_space_in_material_type_is_still_allowed(self, tmp_path):
        """Ordinary spaces remain valid — only control characters are rejected."""
        config_path = tmp_path / "materials.toml"
        config_path.write_text(
            "[[materials]]\n"
            'name = "Bronze"\n'
            'material_type = "light metal"\n'
            "reference_cutting_speed = 45.0\n"
            "reference_feed_per_rev = 0.18\n"
            "specific_cutting_force = 750.0\n",
            encoding="utf-8",
        )

        assert "light metal" in list_material_types(config_path=str(config_path))
