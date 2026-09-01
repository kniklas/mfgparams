"""Integration tests for the CLI ``--materials-config`` flag (T028, T029, T036, T042).

Covers the four startup paths (absent, missing/unreadable, malformed,
valid override/addition), the duplicate-name-within-file rejection, the
translated-name display with locale fallback (quickstart.md Scenario 4),
and the imperial-declared-material end-to-end equivalence (quickstart.md
Scenario 5).
"""

from __future__ import annotations

import builtins
import math
from pathlib import Path

import pytest

from mfgparams import i18n
from mfgparams.console.cli import run


def _feed_inputs(monkeypatch, inputs):
    iterator = iter(inputs)
    monkeypatch.setattr(builtins, "input", lambda _prompt="": next(iterator))


_BASE_REPL_INPUTS = [
    "drilling",  # machining operation (009 FR-001)
    "metric",  # unit system
    "standard",  # calculation mode -- no blank/default option (FR-001a)
    "Metal",  # material type
    "Mild Steel",  # material
    "Carbide",  # tool
    "10",  # diameter
    "25",  # depth
    "",  # available power (blank/unknown)
    "n",  # do not run another calculation
]


# --- T028: absent / missing / malformed / valid paths ---


def test_absent_flag_reproduces_zero_config(monkeypatch, capsys):
    _feed_inputs(monkeypatch, _BASE_REPL_INPUTS)
    run(materials_config_path=None)
    out = capsys.readouterr().out
    assert "Spindle speed:" in out


def test_missing_path_prints_notice_and_proceeds(monkeypatch, capsys, tmp_path):
    missing = str(tmp_path / "does-not-exist.toml")
    _feed_inputs(monkeypatch, _BASE_REPL_INPUTS)
    run(materials_config_path=missing)
    out = capsys.readouterr().out
    assert "not found" in out or "not readable" in out
    assert "Spindle speed:" in out


def test_malformed_file_exits_without_traceback(monkeypatch, capsys, tmp_path):
    bad = tmp_path / "bad.toml"
    bad.write_text('[[materials]\nname = "Broken"\n')
    with pytest.raises(SystemExit):
        run(materials_config_path=str(bad))
    out = capsys.readouterr().out
    assert "Traceback" not in out
    assert "could not be parsed" in out


def test_invalid_positive_value_exits_without_traceback(monkeypatch, capsys, tmp_path):
    """Invalid material entries should warn and continue startup (FR-008)."""

    bad = tmp_path / "bad.toml"
    bad.write_text("""
        [[materials]]
        name = "Bad"
        reference_cutting_speed = -1.0
        reference_feed_per_rev = 0.2
        specific_cutting_force = 1900.0
        """)
    _feed_inputs(monkeypatch, _BASE_REPL_INPUTS)
    run(materials_config_path=str(bad))
    out = capsys.readouterr().out
    assert "Traceback" not in out
    assert "Spindle speed:" in out


def test_warning_and_continue_with_invalid_wood_fixture(monkeypatch, caplog, tmp_path):
    source_fixture = (
        Path(__file__).resolve().parents[1] / "fixtures" / "materials" / "wood-invalid-params.toml"
    )
    fixture = tmp_path / "wood-invalid-params.toml"
    fixture.write_text(source_fixture.read_text(encoding="utf-8"), encoding="utf-8")
    _feed_inputs(monkeypatch, _BASE_REPL_INPUTS)
    caplog.set_level("WARNING")
    run(materials_config_path=str(fixture))
    assert "validation issue(s)" in caplog.text
    assert str(fixture) in caplog.text


def test_valid_override_file_lists_new_material(monkeypatch, capsys, tmp_path):
    config = tmp_path / "my-mfgparams.toml"
    config.write_text("""
        [[materials]]
        name = "Bronze"
        reference_cutting_speed = 45.0
        reference_feed_per_rev = 0.18
        specific_cutting_force = 750.0

        [[tools]]
        name = "Carbide"
        cutting_speed_factor = 3.0
        feed_factor = 1.1
        """)
    inputs = [
        "drilling",  # machining operation (009 FR-001)
        "metric",
        "standard",
        "Uncategorized",  # material type
        "Bronze",  # new material appears in the prompt options
        "Carbide",
        "10",
        "25",
        "",
        "n",
    ]
    _feed_inputs(monkeypatch, inputs)
    run(materials_config_path=str(config))
    out = capsys.readouterr().out
    assert "Spindle speed:" in out


def test_engineered_materials_can_be_selected(monkeypatch, capsys):
    inputs = [
        "drilling",  # machining operation (009 FR-001)
        "metric",
        "standard",
        "Wood",  # material type
        "Plywood",
        "Carbide",
        "10",
        "25",
        "",
        "n",
    ]
    _feed_inputs(monkeypatch, inputs)
    run(materials_config_path=None)
    out = capsys.readouterr().out
    assert "Spindle speed:" in out


# --- T029: duplicate-name-within-file rejection ---


def test_duplicate_name_within_file_rejected(monkeypatch, capsys, tmp_path):
    dup = tmp_path / "dup.toml"
    dup.write_text("""
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
        """)
    with pytest.raises(SystemExit):
        run(materials_config_path=str(dup))
    out = capsys.readouterr().out
    assert "Bronze" in out
    assert "more than one" in out


# --- T036: translated material names with English fallback ---


def test_translated_name_shown_for_active_locale(monkeypatch, capsys, tmp_path):
    config = tmp_path / "translations.toml"
    config.write_text("""
        [[materials]]
        name = "Mild Steel"
        reference_cutting_speed = 25.0
        reference_feed_per_rev = 0.20
        specific_cutting_force = 1900.0

        [materials.translations]
        fr = "Acier doux"
        """)
    monkeypatch.setenv("MFGPARAMS_LOCALE", "fr")
    i18n.clear_catalog_cache()
    inputs = iter(
        [
            "drilling",  # machining operation (009 FR-001)
            "metric",
            "standard",
            "Metal",  # material type
            "Acier doux",  # translated label must be selectable
            "Carbide",
            "10",
            "25",
            "",
            "n",
        ]
    )

    def _input_with_echo(prompt=""):
        print(prompt, end="")
        return next(inputs)

    monkeypatch.setattr(builtins, "input", _input_with_echo)
    run(materials_config_path=str(config))
    out = capsys.readouterr().out
    assert "Acier doux" in out


def test_unsupported_locale_falls_back_to_english_name(monkeypatch, capsys, tmp_path):
    config = tmp_path / "translations.toml"
    config.write_text("""
        [[materials]]
        name = "Mild Steel"
        reference_cutting_speed = 25.0
        reference_feed_per_rev = 0.20
        specific_cutting_force = 1900.0

        [materials.translations]
        fr = "Acier doux"
        """)
    monkeypatch.setenv("MFGPARAMS_LOCALE", "xx-no-catalog")
    i18n.clear_catalog_cache()
    # No translation exists for "xx-no-catalog" -> the material prompt's
    # options must still include the plain English name (fallback), so
    # feeding "Mild Steel" as the selection succeeds without a
    # RegistryConfigError-adjacent reprompt loop.
    _feed_inputs(monkeypatch, _BASE_REPL_INPUTS)
    run(materials_config_path=str(config))
    out = capsys.readouterr().out
    assert "Spindle speed:" in out


# --- T042: imperial-declared material end-to-end equivalence ---


def test_imperial_declared_material_matches_metric_equivalent_metric_mode(
    monkeypatch, capsys, tmp_path
):
    config = tmp_path / "imperial.toml"
    config.write_text("""
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
    from mfgparams import calculate

    imperial_result = calculate(
        diameter=10,
        depth=25,
        material="Bronze Imperial",
        tool="Carbide",
        materials_config_path=str(config),
    )
    metric_result = calculate(
        diameter=10,
        depth=25,
        material="Bronze Metric",
        tool="Carbide",
        materials_config_path=str(config),
    )
    assert imperial_result.error is None
    assert metric_result.error is None
    assert math.isclose(
        imperial_result.spindle_speed_rpm, metric_result.spindle_speed_rpm, rel_tol=1e-3
    )
    assert math.isclose(imperial_result.torque, metric_result.torque, rel_tol=1e-3)
    assert math.isclose(imperial_result.power_required, metric_result.power_required, rel_tol=1e-3)
