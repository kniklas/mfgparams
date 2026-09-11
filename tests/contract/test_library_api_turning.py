"""Contract test: the public turning API surface (specs/019-turning-calculations).

Checks ``calculate_turning``/``list_turning_tools`` against
``contracts/library-api-turning.md``: importability from ``mfgparams``
without touching ``processes.machining.turning`` directly (User Story 2),
the standard-mode success shape against a hand-computed reference value
(SC-002), and the documented error codes.

Reference calculation (Mild Steel: vc=25.0 m/min, fn=0.20 mm/rev,
Kc=1900.0 N/mm^2; Carbide turning tool: cutting_speed_factor=2.4,
feed_factor=1.05; diameter=40mm, depth_of_cut=2mm, length_of_cut=100mm):

- vc_eff = 25.0 * 2.4 = 60.0 m/min
- n = (60.0 * 1000) / (pi * 40) = 477.4648... RPM
- fn_eff = 0.20 * 1.05 = 0.21 mm/rev
- feed_rate = n * fn_eff = 100.2676... mm/min
- machining_time = 100 / feed_rate = 0.99733... min
- cutting_force = 1900 * 2 * 0.21 = 798.0 N
- torque = 798.0 * (40/2) / 1000 = 15.96 N*m
- power = 15.96 * n / 9550 = 0.79794... kW

(Exact constants below are taken from a verified run of the implementation
itself, not re-derived by hand a second time, to avoid a transcription
error in this docstring's manual arithmetic silently becoming the source
of truth a future reader trusts over the code.)
"""

import math

import pytest

import mfgparams
from mfgparams import CalculationMode, UnitSystem, calculate_turning, list_turning_tools

_DIAMETER = 40.0
_DEPTH_OF_CUT = 2.0
_LENGTH_OF_CUT = 100.0
_MATERIAL = "Mild Steel"
_TOOL = "Carbide"

_EXPECTED_SPINDLE_SPEED_RPM = 477.46482927568604
_EXPECTED_FEED_RATE_MM_MIN = 100.26761414789408
_EXPECTED_MACHINING_TIME_MIN = 0.9973310011396167
_EXPECTED_CUTTING_FORCE_N = 798.0
_EXPECTED_TORQUE_NM = 15.96
_EXPECTED_POWER_KW = 0.7979412225382146


def test_calculate_turning_and_list_turning_tools_are_top_level_exports():
    """User Story 2: usable without importing ``processes.machining.turning``."""

    assert mfgparams.calculate_turning is calculate_turning
    assert mfgparams.list_turning_tools is list_turning_tools
    assert callable(calculate_turning)
    assert callable(list_turning_tools)


def test_list_turning_tools_includes_bundled_defaults():
    tools = list_turning_tools()

    assert "HSS" in tools
    assert "Cobalt" in tools
    assert "Carbide" in tools


def test_standard_mode_matches_hand_computed_reference_independently_per_field():
    """SC-002: spindle speed, feed rate, cutting force, and power are each
    independently verified, not merely as an aggregate."""

    result = calculate_turning(
        diameter=_DIAMETER,
        depth_of_cut=_DEPTH_OF_CUT,
        length_of_cut=_LENGTH_OF_CUT,
        material=_MATERIAL,
        tool=_TOOL,
    )

    assert result.error is None
    assert math.isclose(result.spindle_speed_rpm, _EXPECTED_SPINDLE_SPEED_RPM, rel_tol=1e-6)
    assert math.isclose(result.feed_rate, _EXPECTED_FEED_RATE_MM_MIN, rel_tol=1e-6)
    assert math.isclose(result.machining_time, _EXPECTED_MACHINING_TIME_MIN, rel_tol=1e-6)
    assert math.isclose(result.cutting_force, _EXPECTED_CUTTING_FORCE_N, rel_tol=1e-6)
    assert math.isclose(result.torque, _EXPECTED_TORQUE_NM, rel_tol=1e-6)
    assert math.isclose(result.power_required, _EXPECTED_POWER_KW, rel_tol=1e-6)
    assert result.feasibility_warning is None


def test_never_raises_and_always_returns_a_calculation_result():
    """The never-raises contract: every one of these deliberately-invalid
    calls must return a structured error, not propagate an exception."""

    cases = [
        dict(
            diameter=0,
            depth_of_cut=_DEPTH_OF_CUT,
            length_of_cut=_LENGTH_OF_CUT,
            material=_MATERIAL,
            tool=_TOOL,
        ),
        dict(
            diameter=_DIAMETER,
            depth_of_cut="not-a-number",
            length_of_cut=_LENGTH_OF_CUT,
            material=_MATERIAL,
            tool=_TOOL,
        ),
        dict(
            diameter=_DIAMETER,
            depth_of_cut=_DEPTH_OF_CUT,
            length_of_cut=_LENGTH_OF_CUT,
            material="",
            tool=_TOOL,
        ),
        dict(
            diameter=_DIAMETER,
            depth_of_cut=_DEPTH_OF_CUT,
            length_of_cut=_LENGTH_OF_CUT,
            material=_MATERIAL,
            tool="",
        ),
        dict(
            diameter=_DIAMETER,
            depth_of_cut=_DEPTH_OF_CUT,
            length_of_cut=_LENGTH_OF_CUT,
            material="Unobtainium",
            tool=_TOOL,
        ),
        dict(
            diameter=_DIAMETER,
            depth_of_cut=_DEPTH_OF_CUT,
            length_of_cut=_LENGTH_OF_CUT,
            material=_MATERIAL,
            tool="Unobtainium Tool",
        ),
    ]
    for kwargs in cases:
        result = calculate_turning(**kwargs)
        assert result.error is not None
        assert result.spindle_speed_rpm is None
        assert result.cutting_force is None


def test_missing_material_reports_missing_material():
    result = calculate_turning(
        diameter=_DIAMETER,
        depth_of_cut=_DEPTH_OF_CUT,
        length_of_cut=_LENGTH_OF_CUT,
        material="",
        tool=_TOOL,
    )

    assert result.error.code == "MISSING_MATERIAL"


def test_missing_tool_reports_missing_tool_with_turning_wording():
    result = calculate_turning(
        diameter=_DIAMETER,
        depth_of_cut=_DEPTH_OF_CUT,
        length_of_cut=_LENGTH_OF_CUT,
        material=_MATERIAL,
        tool="",
    )

    assert result.error.code == "MISSING_TOOL"
    assert "turning tool" in result.error.message


def test_unknown_tool_reports_missing_tool():
    result = calculate_turning(
        diameter=_DIAMETER,
        depth_of_cut=_DEPTH_OF_CUT,
        length_of_cut=_LENGTH_OF_CUT,
        material=_MATERIAL,
        tool="Unobtainium Tool",
    )

    assert result.error.code == "MISSING_TOOL"
    assert "Unobtainium Tool" in result.error.message


def test_depth_of_cut_at_or_beyond_radius_is_rejected():
    """spec.md Edge Cases: depth of cut >= workpiece radius is physically impossible."""

    result = calculate_turning(
        diameter=10.0,  # radius = 5mm
        depth_of_cut=6.0,
        length_of_cut=_LENGTH_OF_CUT,
        material=_MATERIAL,
        tool=_TOOL,
    )

    assert result.error is not None
    assert result.error.code == "INVALID_DEPTH_OF_CUT"
    assert "radius" in result.error.message


@pytest.mark.parametrize(
    "field, invalid_value, expected_code",
    [
        ("diameter", -1, "INVALID_DIAMETER"),
        ("depth_of_cut", -1, "INVALID_DEPTH_OF_CUT"),
        ("length_of_cut", -1, "INVALID_LENGTH_OF_CUT"),
    ],
)
def test_invalid_dimensional_inputs_report_the_expected_code(field, invalid_value, expected_code):
    kwargs = dict(
        diameter=_DIAMETER,
        depth_of_cut=_DEPTH_OF_CUT,
        length_of_cut=_LENGTH_OF_CUT,
        material=_MATERIAL,
        tool=_TOOL,
    )
    kwargs[field] = invalid_value

    result = calculate_turning(**kwargs)

    assert result.error is not None
    assert result.error.code == expected_code


def test_console_and_library_identical_results_for_identical_inputs():
    """FR-016: two calls with identical inputs produce identical results
    (a proxy for console/library parity, since the console screen's
    ``calculate_result`` is a thin adapter over this same function --
    see tests/integration/test_turning_console_library_parity.py for the
    direct adapter-level check)."""

    first = calculate_turning(
        diameter=_DIAMETER,
        depth_of_cut=_DEPTH_OF_CUT,
        length_of_cut=_LENGTH_OF_CUT,
        material=_MATERIAL,
        tool=_TOOL,
    )
    second = calculate_turning(
        diameter=_DIAMETER,
        depth_of_cut=_DEPTH_OF_CUT,
        length_of_cut=_LENGTH_OF_CUT,
        material=_MATERIAL,
        tool=_TOOL,
    )

    assert first == second


def test_imperial_and_metric_calls_describe_the_same_physical_operation():
    """FR-017: an imperial call converts inputs to canonical metric
    internally and converts results back, so it must describe the same
    physical turning pass as the equivalent metric call — spindle speed
    and machining time are unit-independent; feed rate, torque, power,
    and cutting force are converted (Copilot review finding: no existing
    turning test exercised the imperial path at all, unlike drilling's/
    milling's own imperial round-trip tests)."""

    metric = calculate_turning(
        diameter=_DIAMETER,
        depth_of_cut=_DEPTH_OF_CUT,
        length_of_cut=_LENGTH_OF_CUT,
        material=_MATERIAL,
        tool=_TOOL,
        unit_system=UnitSystem.METRIC,
    )
    imperial = calculate_turning(
        diameter=_DIAMETER / 25.4,
        depth_of_cut=_DEPTH_OF_CUT / 25.4,
        length_of_cut=_LENGTH_OF_CUT / 25.4,
        material=_MATERIAL,
        tool=_TOOL,
        unit_system=UnitSystem.IMPERIAL,
    )

    assert imperial.error is None
    # Spindle speed (RPM) and machining time (minutes) are unit-independent.
    assert math.isclose(imperial.spindle_speed_rpm, metric.spindle_speed_rpm, rel_tol=1e-6)
    assert math.isclose(imperial.machining_time, metric.machining_time, rel_tol=1e-6)
    # Feed rate/torque/power/cutting_force differ because they are
    # converted to imperial units, but describe the same physical values.
    assert imperial.feed_rate != metric.feed_rate
    assert imperial.torque != metric.torque
    assert imperial.power_required != metric.power_required
    assert imperial.cutting_force != metric.cutting_force
    # Round-trip: converting the imperial cutting_force (lbf) back to N
    # must reproduce the metric value.
    assert math.isclose(
        imperial.cutting_force * 4.4482216152605, metric.cutting_force, rel_tol=1e-6
    )


def test_extreme_subnormal_geometry_returns_structured_overflow_error_not_a_stale_success():
    """Copilot review finding on PR #100: a subnormal-but-individually-
    "valid" diameter/depth_of_cut (no lower bound beyond positivity) could
    previously underflow torque/power to exactly 0.0 while still
    returning error=None — a silently wrong "successful" result. Must now
    return a structured CALCULATION_OVERFLOW error instead."""

    result = calculate_turning(
        diameter=1e-300, depth_of_cut=1e-310, length_of_cut=1, material=_MATERIAL, tool=_TOOL
    )

    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.spindle_speed_rpm is None
    assert result.cutting_force is None


def test_subnormal_target_rpm_returns_structured_overflow_error_not_zerodivisionerror():
    """Copilot review finding on PR #100: target_rpm has no lower bound
    beyond positivity/finiteness, so a positive subnormal value could
    previously reach ZeroDivisionError inside the formula layer instead of
    the documented never-raises structured-error contract."""

    result = calculate_turning(
        diameter=_DIAMETER,
        depth_of_cut=_DEPTH_OF_CUT,
        length_of_cut=_LENGTH_OF_CUT,
        material=_MATERIAL,
        tool=_TOOL,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=5e-324,
    )

    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"


def test_arbitrary_precision_int_target_rpm_returns_structured_error_not_overflowerror():
    """Copilot review finding on PR #100: an int too large to convert to a
    C double (e.g. 10**1000) previously raised OverflowError from
    validate_target_rpm()'s bare math.isfinite() call, escaping the
    never-raises contract shared by drilling, milling, and turning."""

    result = calculate_turning(
        diameter=_DIAMETER,
        depth_of_cut=_DEPTH_OF_CUT,
        length_of_cut=_LENGTH_OF_CUT,
        material=_MATERIAL,
        tool=_TOOL,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=10**1000,
    )

    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"


def test_arbitrary_precision_int_imperial_available_power_does_not_raise():
    """Copilot review finding on PR #100: an oversized positive Python int
    supplied as imperial available_power previously reached hp_to_kw()
    and raised OverflowError during int-to-float conversion, instead of
    behaving as an effectively-unlimited power budget."""

    result = calculate_turning(
        diameter=1.0,
        depth_of_cut=0.1,
        length_of_cut=10.0,
        material=_MATERIAL,
        tool=_TOOL,
        unit_system=UnitSystem.IMPERIAL,
        available_power=10**1000,
    )

    assert result.error is None
    assert result.feasibility_warning is None
