"""Unit tests for `mfgparams.registry_config` (T013).

Covers valid parse, malformed TOML, missing/unreadable user path,
duplicate-within-file rejection, override-by-name, append-new-name, and
per-locale translation merge (data-model.md "Merge Algorithm").
"""

from __future__ import annotations

import math

import pytest

from mfgparams.registry_config import (
    RawRegistryEntry,
    RegistryConfigError,
    load_and_merge,
    merge_entries,
    parse_toml_entries,
    require_positive_finite_field,
)

VALID_TOML = """
[[materials]]
name = "Bronze"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0

[materials.translations]
fr = "Bronze"
"""

MALFORMED_TOML = '[[materials]\nname = "Broken"\n'

DUPLICATE_TOML = """
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
"""

INVALID_UNIT_SYSTEM_TOML = """
[[materials]]
name = "Bronze"
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
unit_system = "furlongs"
"""

MISSING_NAME_TOML = """
[[materials]]
reference_cutting_speed = 45.0
reference_feed_per_rev = 0.18
specific_cutting_force = 750.0
"""


def test_parse_valid_toml_produces_expected_entry():
    entries = parse_toml_entries(VALID_TOML, "materials", "test.toml")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.name == "Bronze"
    assert math.isclose(entry.fields["reference_cutting_speed"], 45.0, rel_tol=1e-9)
    assert entry.unit_system == "metric"
    assert entry.translations == {"fr": "Bronze"}


def test_parse_malformed_toml_raises_registry_config_error():
    with pytest.raises(RegistryConfigError) as exc_info:
        parse_toml_entries(MALFORMED_TOML, "materials", "bad.toml")
    assert exc_info.value.message_key == "error.materials_config.malformed"
    assert exc_info.value.kwargs["path"] == "bad.toml"


def test_parse_invalid_unit_system_raises_registry_config_error():
    with pytest.raises(RegistryConfigError) as exc_info:
        parse_toml_entries(INVALID_UNIT_SYSTEM_TOML, "materials", "bad.toml")
    assert exc_info.value.message_key == "error.materials_config.invalid_entry"


def test_parse_missing_name_raises_registry_config_error():
    with pytest.raises(RegistryConfigError) as exc_info:
        parse_toml_entries(MISSING_NAME_TOML, "materials", "bad.toml")
    assert exc_info.value.message_key == "error.materials_config.invalid_entry"


def test_parse_non_string_name_raises_registry_config_error():
    """Copilot review finding on specs/019-turning-calculations PR #100:
    `name = 123` passed the old truthiness-only check (123 is truthy) and
    was stored as an int, breaking every registry's documented
    `list[str]` return type — a shared gap across every registry
    (materials, drilling/milling/turning tools alike), not turning-
    specific."""
    non_string_name_toml = """
    [[materials]]
    name = 123
    reference_cutting_speed = 45.0
    reference_feed_per_rev = 0.18
    specific_cutting_force = 750.0
    """
    with pytest.raises(RegistryConfigError) as exc_info:
        parse_toml_entries(non_string_name_toml, "materials", "bad.toml")
    assert exc_info.value.message_key == "error.materials_config.invalid_entry"
    assert "name" in exc_info.value.kwargs["details"]


def test_parse_name_with_control_character_raises_registry_config_error():
    """Copilot review finding on specs/019-turning-calculations PR #100
    (round 3): a name containing a control character (e.g. ESC, the lead
    byte of every ANSI escape sequence) is later emitted as a TUI option
    label, where it can corrupt the menu display or inject terminal
    control sequences. Mirrors registry.py's identical
    `_FORBIDDEN_ID_CATEGORIES` check already applied to `material_type`."""
    control_char_name_toml = (
        '[[tools]]\nname = "Bad\\u001bName"\ncutting_speed_factor=1.0\nfeed_factor=1.0\n'
    )
    with pytest.raises(RegistryConfigError) as exc_info:
        parse_toml_entries(control_char_name_toml, "tools", "bad.toml")
    assert exc_info.value.message_key == "error.materials_config.invalid_entry"
    assert "control characters" in exc_info.value.kwargs["details"]


def test_parse_name_with_newline_raises_registry_config_error():
    """The same control-character guard also covers a literal newline,
    not just non-printable escape codes."""
    newline_name_toml = (
        '[[tools]]\nname = "Bad\\nName"\ncutting_speed_factor=1.0\nfeed_factor=1.0\n'
    )
    with pytest.raises(RegistryConfigError) as exc_info:
        parse_toml_entries(newline_name_toml, "tools", "bad.toml")
    assert exc_info.value.message_key == "error.materials_config.invalid_entry"
    assert "control characters" in exc_info.value.kwargs["details"]


class TestRequirePositiveFiniteField:
    """Unit tests for `require_positive_finite_field`, the shared helper
    factored out of drilling's/milling's/turning's own tool converters
    (Copilot review finding on PR #100 — Reuse/Altitude: this exact
    validation was hand-copied per operation instead of living here once,
    Constitution Principle VI)."""

    def test_accepts_a_valid_positive_number(self):
        value = require_positive_finite_field(
            {"factor": 2.5}, "factor", source_path="t.toml", kind="tool", name="X"
        )
        assert math.isclose(value, 2.5, rel_tol=1e-9)

    def test_rejects_missing_field(self):
        with pytest.raises(RegistryConfigError) as exc_info:
            require_positive_finite_field({}, "factor", source_path="t.toml", kind="tool", name="X")
        assert "missing required field" in exc_info.value.kwargs["details"]

    @pytest.mark.parametrize("bad_value", [True, False, "1.8", "fast", None, [1.0]])
    def test_rejects_non_numeric_or_boolean_values(self, bad_value):
        with pytest.raises(RegistryConfigError) as exc_info:
            require_positive_finite_field(
                {"factor": bad_value}, "factor", source_path="t.toml", kind="tool", name="X"
            )
        assert "must be a number" in exc_info.value.kwargs["details"]

    @pytest.mark.parametrize("bad_value", [0, -1.0, float("nan"), float("inf"), float("-inf")])
    def test_rejects_non_positive_or_non_finite_values(self, bad_value):
        with pytest.raises(RegistryConfigError) as exc_info:
            require_positive_finite_field(
                {"factor": bad_value}, "factor", source_path="t.toml", kind="tool", name="X"
            )
        assert "must be positive" in exc_info.value.kwargs["details"]

    def test_rejects_arbitrary_precision_int_too_large_for_a_float(self):
        """Copilot review finding on PR #100 (round 3): tomllib/tomli
        impose no bound on an integer literal, so `cutting_speed_factor =
        10**1000` in a hand-edited config reaches here as a plain Python
        int. `float(raw_value)` then raises OverflowError, which
        previously escaped unhandled instead of the documented
        RegistryConfigError."""
        with pytest.raises(RegistryConfigError) as exc_info:
            require_positive_finite_field(
                {"factor": 10**1000}, "factor", source_path="t.toml", kind="tool", name="X"
            )
        assert "too large to represent" in exc_info.value.kwargs["details"]


def test_missing_user_path_returns_bundled_only_with_notice(tmp_path):
    missing_path = str(tmp_path / "does-not-exist.toml")
    result = load_and_merge("mfgparams.data", "materials.toml", missing_path, "materials")
    assert result.notice_key == "notice.materials_config.not_found"
    assert dict(result.notice_kwargs)["path"] == missing_path
    names = [entry.name for entry in result.entries]
    assert "Mild Steel" in names


def test_none_user_path_returns_bundled_only_no_notice():
    result = load_and_merge("mfgparams.data", "materials.toml", None, "materials")
    assert result.notice_key is None
    names = [entry.name for entry in result.entries]
    assert names == [
        "Mild Steel",
        "Stainless Steel",
        "Aluminum",
        "Cast Iron",
        "Brass",
        "Titanium",
        "Oak",
        "Maple",
        "Pine",
        "Spruce",
        "Fir",
        "Plywood",
        "MDF",
    ]


def test_duplicate_name_within_user_file_raises(tmp_path):
    path = tmp_path / "dup.toml"
    path.write_text(DUPLICATE_TOML)
    with pytest.raises(RegistryConfigError) as exc_info:
        load_and_merge("mfgparams.data", "materials.toml", str(path), "materials")
    assert exc_info.value.message_key == "error.materials_config.duplicate_entry"
    assert exc_info.value.kwargs["name"] == "Bronze"


def test_malformed_user_file_raises(tmp_path):
    path = tmp_path / "bad.toml"
    path.write_text(MALFORMED_TOML)
    with pytest.raises(RegistryConfigError) as exc_info:
        load_and_merge("mfgparams.data", "materials.toml", str(path), "materials")
    assert exc_info.value.message_key == "error.materials_config.malformed"


def test_override_by_name_replaces_fields_and_unit_system():
    bundled = [
        RawRegistryEntry(name="Mild Steel", fields={"reference_cutting_speed": 25.0}),
    ]
    user = [
        RawRegistryEntry(
            name="Mild Steel", fields={"reference_cutting_speed": 28.0}, unit_system="imperial"
        )
    ]
    merged = merge_entries(bundled, user)
    assert len(merged) == 1
    assert math.isclose(merged[0].fields["reference_cutting_speed"], 28.0, rel_tol=1e-9)
    assert merged[0].unit_system == "imperial"


def test_append_new_name():
    bundled = [RawRegistryEntry(name="Mild Steel", fields={"reference_cutting_speed": 25.0})]
    user = [RawRegistryEntry(name="Bronze", fields={"reference_cutting_speed": 45.0})]
    merged = merge_entries(bundled, user)
    names = [entry.name for entry in merged]
    assert names == ["Mild Steel", "Bronze"]


def test_unaffected_bundled_entries_are_untouched():
    bundled = [
        RawRegistryEntry(name="Mild Steel", fields={"reference_cutting_speed": 25.0}),
        RawRegistryEntry(name="Aluminum", fields={"reference_cutting_speed": 60.0}),
    ]
    user = [RawRegistryEntry(name="Bronze", fields={"reference_cutting_speed": 45.0})]
    merged = merge_entries(bundled, user)
    aluminum = next(entry for entry in merged if entry.name == "Aluminum")
    assert math.isclose(aluminum.fields["reference_cutting_speed"], 60.0, rel_tol=1e-9)


def test_translation_merge_user_wins_per_locale_others_preserved():
    bundled = [
        RawRegistryEntry(
            name="Mild Steel",
            fields={"reference_cutting_speed": 25.0},
            translations={"fr": "Acier doux (bundled)", "de": "Weichstahl"},
        )
    ]
    user = [
        RawRegistryEntry(
            name="Mild Steel",
            fields={"reference_cutting_speed": 28.0},
            translations={"fr": "Acier doux"},
        )
    ]
    merged = merge_entries(bundled, user)
    assert merged[0].translations == {"fr": "Acier doux", "de": "Weichstahl"}


def test_no_user_entries_returns_bundled_unchanged():
    bundled = [RawRegistryEntry(name="Mild Steel", fields={"reference_cutting_speed": 25.0})]
    merged = merge_entries(bundled, None)
    assert merged == bundled
    merged_empty = merge_entries(bundled, [])
    assert merged_empty == bundled


def test_unreadable_user_file_returns_notice_not_error(tmp_path):
    import os
    import stat

    path = tmp_path / "unreadable.toml"
    path.write_text(VALID_TOML)
    try:
        path.chmod(0)
        # Root (and some CI sandboxes) can still read a 0-permission file;
        # skip in that case rather than asserting a false negative.
        if os.access(path, os.R_OK):
            pytest.skip("current user can still read a 0-permission file")
        result = load_and_merge("mfgparams.data", "materials.toml", str(path), "materials")
        assert result.notice_key == "notice.materials_config.not_found"
    finally:
        path.chmod(stat.S_IWRITE | stat.S_IREAD)


def test_clear_cache_does_not_raise():
    from mfgparams.registry_config import clear_cache

    clear_cache()
    result = load_and_merge("mfgparams.data", "materials.toml", None, "materials")
    assert result.notice_key is None
