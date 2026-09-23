"""Unit tests for the material-number/shortened-designation notation fields
(specs/023-material-selector-dialog).

Covers ``WorkpieceMaterial.material_number``/``short_notation`` parsing,
warn-and-continue validation (mirroring ``material_type``'s existing policy,
see ``test_registry_material_types.py``'s ``TestInvalidMaterialType``), and
the two new keys' sticky-field merge behavior (research.md Decision 5).
"""

from __future__ import annotations

import pytest

from mfgparams.registry import get_material, get_material_validation


def _write_config(tmp_path, body: str) -> str:
    """Write ``body`` to a user materials config file and return its path."""

    path = tmp_path / "user-materials.toml"
    path.write_text(body, encoding="utf-8")
    return str(path)


class TestValidNotations:
    """Present, valid values round-trip onto ``WorkpieceMaterial`` (FR-002)."""

    def test_both_fields_round_trip(self, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Chromoly Steel"
material_type = "metal"
reference_cutting_speed = 20.0
reference_feed_per_rev = 0.18
specific_cutting_force = 2100.0
material_number = "1.7225"
short_notation = "42CrMo4+N"
""",
        )

        material = get_material("Chromoly Steel", config_path)
        assert material.material_number == "1.7225"
        assert material.short_notation == "42CrMo4+N"

    def test_surrounding_whitespace_is_stripped(self, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Chromoly Steel"
material_type = "metal"
reference_cutting_speed = 20.0
reference_feed_per_rev = 0.18
specific_cutting_force = 2100.0
material_number = "  1.7225  "
short_notation = "  42CrMo4+N  "
""",
        )

        material = get_material("Chromoly Steel", config_path)
        assert material.material_number == "1.7225"
        assert material.short_notation == "42CrMo4+N"

    def test_absent_fields_default_to_none(self, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Unlabeled Alloy"
material_type = "metal"
reference_cutting_speed = 30.0
reference_feed_per_rev = 0.22
specific_cutting_force = 1800.0
""",
        )

        material = get_material("Unlabeled Alloy", config_path)
        assert material.material_number is None
        assert material.short_notation is None

    def test_one_field_present_other_absent(self, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Partly Labeled"
material_type = "metal"
reference_cutting_speed = 25.0
reference_feed_per_rev = 0.20
specific_cutting_force = 1900.0
material_number = "1.0038"
""",
        )

        material = get_material("Partly Labeled", config_path)
        assert material.material_number == "1.0038"
        assert material.short_notation is None


class TestInvalidNotations:
    """An invalid value warns and continues, per FR-010's blank-cell handling."""

    @pytest.mark.parametrize("field_name", ["material_number", "short_notation"])
    @pytest.mark.parametrize("raw_value", ["123", '""', "true"])
    def test_non_string_or_empty_value_falls_back_and_records_issue(
        self, tmp_path, field_name, raw_value
    ):
        config_path = _write_config(
            tmp_path,
            f"""
[[materials]]
name = "Odd"
material_type = "metal"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
{field_name} = {raw_value}
""",
        )

        material = get_material("Odd", config_path)
        assert getattr(material, field_name) is None
        # The material stays usable and selectable despite the bad notation.
        assert material.is_usable

        record = get_material_validation("Odd", config_path)
        assert record.status == "warning"
        assert any(field_name in issue for issue in record.issues)

    @pytest.mark.parametrize("field_name", ["material_number", "short_notation"])
    def test_control_character_value_falls_back_and_records_issue(self, tmp_path, field_name):
        config_path = tmp_path / "materials.toml"
        config_path.write_text(
            "[[materials]]\n"
            'name = "Odd"\n'
            'material_type = "metal"\n'
            "reference_cutting_speed = 45.0\n"
            "reference_feed_per_rev = 0.18\n"
            "specific_cutting_force = 750.0\n"
            f'{field_name} = "1.72\\tN"\n',
            encoding="utf-8",
        )

        material = get_material("Odd", config_path=str(config_path))
        assert getattr(material, field_name) is None
        assert material.is_usable

        record = get_material_validation("Odd", config_path=str(config_path))
        assert record.status == "warning"
        assert any(field_name in issue for issue in record.issues)

    def test_invalid_notation_does_not_affect_the_other_field(self, tmp_path):
        config_path = _write_config(
            tmp_path,
            """
[[materials]]
name = "Half Odd"
material_type = "metal"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
material_number = 123
short_notation = "42CrMo4+N"
""",
        )

        material = get_material("Half Odd", config_path)
        assert material.material_number is None
        assert material.short_notation == "42CrMo4+N"


class TestStickyFieldMerge:
    """A user override omitting either key carries over the bundled value
    (research.md Decision 5), tested at ``merge_entries``'s own level
    directly -- isolating the sticky-field merge mechanism itself from
    which real bundled entries currently happen to carry notation values
    (see ``TestBundledNotations`` below for that)."""

    def test_override_without_notations_keeps_the_bundled_values(self):
        from mfgparams.registry import _STICKY_FIELDS
        from mfgparams.registry_config import RawRegistryEntry, merge_entries

        bundled = [
            RawRegistryEntry(
                name="Mild Steel",
                fields={
                    "reference_cutting_speed": 25.0,
                    "reference_feed_per_rev": 0.20,
                    "specific_cutting_force": 1900.0,
                    "material_type": "metal",
                    "material_number": "1.0038",
                    "short_notation": "S235JR",
                },
            )
        ]
        user = [
            RawRegistryEntry(
                name="Mild Steel",
                fields={"reference_cutting_speed": 28.0},
            )
        ]

        merged = merge_entries(bundled, user, sticky_fields=_STICKY_FIELDS)

        assert len(merged) == 1
        assert merged[0].fields["reference_cutting_speed"] == 28.0
        assert merged[0].fields["material_number"] == "1.0038"
        assert merged[0].fields["short_notation"] == "S235JR"

    def test_override_can_explicitly_replace_notations(self):
        from mfgparams.registry import _STICKY_FIELDS
        from mfgparams.registry_config import RawRegistryEntry, merge_entries

        bundled = [
            RawRegistryEntry(
                name="Mild Steel",
                fields={
                    "reference_cutting_speed": 25.0,
                    "reference_feed_per_rev": 0.20,
                    "specific_cutting_force": 1900.0,
                    "material_number": "1.0038",
                    "short_notation": "S235JR",
                },
            )
        ]
        user = [
            RawRegistryEntry(
                name="Mild Steel",
                fields={"reference_cutting_speed": 28.0, "material_number": "1.0044"},
            )
        ]

        merged = merge_entries(bundled, user, sticky_fields=_STICKY_FIELDS)

        assert merged[0].fields["material_number"] == "1.0044"
        # short_notation was not restated, so it is still carried over.
        assert merged[0].fields["short_notation"] == "S235JR"


class TestBundledNotations:
    """The real bundled `data/materials.toml` (no config override) carries
    the exact notation values tasks.md T035 populated -- not just the
    synthetic values the classes above construct via `tmp_path` configs.
    Mirrors `test_registry_material_types.py`'s `TestBundledCategorization`
    precedent, which tests real bundled `material_type` values the same way
    (tasks.md T049, from the second `/speckit-converge` pass on this
    feature)."""

    @pytest.mark.parametrize(
        ("name", "material_number", "short_notation"),
        [
            ("Mild Steel", "1.0038", "S235JR"),
            ("Stainless Steel", "1.4301", "X5CrNi18-10"),
        ],
    )
    def test_populated_bundled_metals_carry_their_documented_notations(
        self, name, material_number, short_notation
    ):
        material = get_material(name)
        assert material.material_number == material_number
        assert material.short_notation == short_notation

    @pytest.mark.parametrize("name", ["Aluminum", "Cast Iron", "Brass", "Titanium"])
    def test_unpopulated_bundled_metals_have_neither_notation(self, name):
        material = get_material(name)
        assert material.material_number is None
        assert material.short_notation is None
