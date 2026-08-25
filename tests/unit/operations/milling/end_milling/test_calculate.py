"""Validation-matrix tests for ``calculate_end_milling()`` (T022).

Covers every error code in ``data-model.md`` "New Error Codes" reachable
through this entry point, asserting in each case that the function returns
rather than raises (FR-012) and that **all** numeric fields — including the
new ``material_removal_rate`` — are ``None`` (SC-003).
"""

import math

import pytest

from mfgparams import calculate_end_milling
from mfgparams.models import CalculationMode, UnitSystem
from mfgparams.registry_config import clear_cache

_NUMERIC_FIELDS = (
    "spindle_speed_rpm",
    "feed_rate",
    "machining_time",
    "torque",
    "power_required",
    "material_removal_rate",
)


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    clear_cache()
    yield
    clear_cache()


def _calc(**overrides):
    kwargs = {
        "diameter": 10.0,
        "axial_depth_of_cut": 2.0,
        "radial_depth_of_cut": 4.0,
        "feed_per_tooth": 0.1,
        "number_of_teeth": 4,
        "length_of_cut": 200.0,
        "material": "Mild Steel",
        "tool": "Carbide",
    }
    kwargs.update(overrides)
    return calculate_end_milling(**kwargs)


def _assert_error(result, code):
    assert result.error is not None, "expected an error result"
    assert result.error.code == code
    assert result.error.message
    for field in _NUMERIC_FIELDS:
        assert getattr(result, field) is None, f"{field} must be None on an error result"
    assert result.feasibility_warning is None


def test_valid_inputs_produce_a_complete_result():
    result = _calc()

    assert result.error is None
    for field in _NUMERIC_FIELDS:
        value = getattr(result, field)
        assert value is not None and math.isfinite(value) and value > 0
    assert result.unit_system is UnitSystem.METRIC
    assert result.mode is CalculationMode.STANDARD


@pytest.mark.parametrize("material", [None, "", "   "])
def test_missing_material_is_reported(material):
    _assert_error(_calc(material=material), "MISSING_MATERIAL")


def test_unknown_material_is_reported():
    result = _calc(material="Unobtainium")

    _assert_error(result, "MISSING_MATERIAL")
    assert "Unobtainium" in result.error.message


@pytest.mark.parametrize("tool", [None, "", "   "])
def test_missing_tool_is_reported(tool):
    _assert_error(_calc(tool=tool), "MISSING_TOOL")


def test_unknown_tool_is_reported():
    result = _calc(tool="Adamantium")

    _assert_error(result, "MISSING_TOOL")
    assert "Adamantium" in result.error.message


def test_unusable_material_with_non_positive_kc_is_reported(tmp_path):
    """FR-010: milling torque/power need a usable specific cutting force."""

    path = tmp_path / "materials.toml"
    path.write_text("""
        [[materials]]
        name = "Nonsense Alloy"
        reference_cutting_speed = 30.0
        reference_feed_per_rev = 0.2
        specific_cutting_force = -5.0
        """)

    result = _calc(material="Nonsense Alloy", materials_config_path=str(path))

    _assert_error(result, "UNUSABLE_MATERIAL")
    assert "Nonsense Alloy" in result.error.message
    assert "specific_cutting_force" in result.error.message


@pytest.mark.parametrize("diameter", [0, -1, float("nan"), float("inf")])
def test_invalid_diameter_is_reported(diameter):
    _assert_error(_calc(diameter=diameter, **{"radial_depth_of_cut": 0.5}), "INVALID_DIAMETER")


def test_diameter_above_the_bound_is_reported():
    _assert_error(_calc(diameter=10_000.0), "INVALID_DIAMETER")


@pytest.mark.parametrize("value", [0, -1, float("nan")])
def test_invalid_axial_depth_of_cut_is_reported(value):
    _assert_error(_calc(axial_depth_of_cut=value), "INVALID_DEPTH_OF_CUT")


def test_axial_depth_above_the_bound_is_reported():
    _assert_error(_calc(axial_depth_of_cut=10_000.0), "INVALID_DEPTH_OF_CUT")


@pytest.mark.parametrize("value", [0, -1, float("nan")])
def test_invalid_radial_depth_of_cut_is_reported(value):
    _assert_error(_calc(**{"radial_depth_of_cut": value}), "INVALID_DEPTH_OF_CUT")


def test_radial_depth_of_cut_exceeding_the_diameter_is_reported():
    """FR-009: geometrically impossible engagement is rejected, not clamped."""

    result = _calc(**{"radial_depth_of_cut": 10.0 + 1})

    _assert_error(result, "INVALID_ENGAGEMENT")
    assert "Radial depth of cut" in result.error.message


def test_radial_depth_of_cut_equal_to_the_diameter_is_accepted():
    result = _calc(**{"radial_depth_of_cut": 10.0})

    assert result.error is None


@pytest.mark.parametrize("value", [0, -0.1, float("nan")])
def test_invalid_feed_per_tooth_is_reported(value):
    _assert_error(_calc(feed_per_tooth=value), "INVALID_FEED_PER_TOOTH")


@pytest.mark.parametrize("value", [0, -2, 4.5, float("nan")])
def test_invalid_tooth_count_is_reported(value):
    _assert_error(_calc(number_of_teeth=value), "INVALID_TOOTH_COUNT")


@pytest.mark.parametrize("value", [0, -10, float("nan")])
def test_invalid_length_of_cut_is_reported(value):
    _assert_error(_calc(length_of_cut=value), "INVALID_LENGTH_OF_CUT")


def test_length_of_cut_above_the_bound_is_reported():
    _assert_error(_calc(length_of_cut=100_000.0), "INVALID_LENGTH_OF_CUT")


def test_material_is_validated_before_the_geometry():
    """data-model.md "Validation Order": material first, so the user fixes
    the most fundamental problem first rather than chasing a geometry
    message that would disappear anyway."""

    result = _calc(material="Unobtainium", diameter=-1)

    _assert_error(result, "MISSING_MATERIAL")


def test_available_power_below_requirement_warns_without_erroring():
    generous = _calc()
    result = _calc(available_power=generous.power_required / 2)

    assert result.error is None
    assert result.feasibility_warning is not None
    # A warning never suppresses the numbers (FR-011).
    assert result.power_required is not None


def test_available_power_above_requirement_does_not_warn():
    generous = _calc()
    result = _calc(available_power=generous.power_required * 2)

    assert result.error is None
    assert result.feasibility_warning is None
