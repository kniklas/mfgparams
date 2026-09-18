"""Contract test: turning power-and-feed-constrained mode error responses
(specs/021-turning-combined-constraints).

Covers MODE_CONFLICT, INFEASIBLE_POWER_BUDGET, INVALID_TARGET_FEED_RATE,
that MISSING_MATERIAL/MISSING_TOOL still take precedence, the mixed-invalid
precedence case, and the CALCULATION_OVERFLOW guard. Mirrors
tests/contract/test_library_api_turning_power_constrained_errors.py and
tests/contract/test_library_api_turning_rotation_and_feed_constrained_errors.py.
"""

import pytest

from mfgparams import CalculationMode, calculate_turning

_ARGS = dict(
    diameter=40,
    depth_of_cut=2,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)


def test_missing_available_power_is_mode_conflict():
    result = calculate_turning(
        **_ARGS, mode=CalculationMode.POWER_AND_FEED_CONSTRAINED, target_feed_rate=0.3
    )

    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"
    assert result.spindle_speed_rpm is None


def test_target_rpm_supplied_under_this_mode_is_mode_conflict():
    """This mode solves for spindle speed; it does not accept one
    directly, mirroring POWER_CONSTRAINED's identical rejection."""

    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=0.5,
        target_feed_rate=0.3,
        target_rpm=900,
    )

    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"


@pytest.mark.parametrize("bad_value", [0, -1, -0.5, float("nan"), float("inf"), float("-inf")])
def test_invalid_available_power_reports_infeasible_power_budget(bad_value):
    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=bad_value,
        target_feed_rate=0.3,
    )

    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"


def test_missing_target_feed_rate_reports_invalid_target_feed_rate():
    result = calculate_turning(
        **_ARGS, mode=CalculationMode.POWER_AND_FEED_CONSTRAINED, available_power=0.5
    )

    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_FEED_RATE"


@pytest.mark.parametrize(
    "bad_value", [0, -1, -0.5, float("nan"), float("inf"), float("-inf"), "fast"]
)
def test_invalid_target_feed_rate_reports_invalid_target_feed_rate(bad_value):
    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=0.5,
        target_feed_rate=bad_value,
    )

    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_FEED_RATE"


def test_missing_available_power_and_invalid_target_feed_rate_is_mode_conflict():
    """data-model.md's precedence rule (Copilot review PR #101's finding,
    applied here from the start rather than rediscovered, research.md #4):
    when target_feed_rate is missing/invalid AND available_power is
    simultaneously missing, MODE_CONFLICT wins -- the shared
    validate_mode_arguments() call (available_power's own check) runs
    before target_feed_rate's own-value check. Mirrors
    test_both_missing_reports_invalid_target_rpm_first for
    ROTATION_AND_FEED_CONSTRAINED."""

    result = calculate_turning(**_ARGS, mode=CalculationMode.POWER_AND_FEED_CONSTRAINED)

    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"


def test_missing_material_takes_precedence_over_power_and_feed_constrained_validation():
    result = calculate_turning(
        diameter=40,
        depth_of_cut=2,
        length_of_cut=100,
        material="",
        tool="Carbide",
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=0.5,
        target_feed_rate=0.3,
    )

    assert result.error is not None
    assert result.error.code == "MISSING_MATERIAL"


def test_missing_tool_takes_precedence_over_power_and_feed_constrained_validation():
    result = calculate_turning(
        diameter=40,
        depth_of_cut=2,
        length_of_cut=100,
        material="Mild Steel",
        tool="",
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=0.5,
        target_feed_rate=0.3,
    )

    assert result.error is not None
    assert result.error.code == "MISSING_TOOL"


def test_extreme_subnormal_input_returns_structured_overflow_error_not_a_stale_success():
    """spec.md Edge Cases: extreme-but-individually-"valid" supplied values
    combined with subnormal geometry must not silently underflow a
    dependent metric to 0.0 while still returning error=None."""

    result = calculate_turning(
        diameter=1e-300,
        depth_of_cut=1e-310,
        length_of_cut=1,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=5e-320,
        target_feed_rate=5e-320,
    )

    assert result.error is not None
    assert result.error.code in ("CALCULATION_OVERFLOW", "INFEASIBLE_POWER_BUDGET")
    assert result.spindle_speed_rpm is None
    assert result.feed_per_rotation is None


def test_arbitrary_precision_int_budget_with_subnormal_geometry_does_not_raise():
    """Copilot review finding on this PR: an arbitrary-precision
    available_power (e.g. 10**1000) combined with subnormal geometry can
    drive nominal.power_kw to nan, which previously reached
    math.isclose() and raised OverflowError converting the huge int to a
    C double, instead of the documented never-raises structured result.
    Mirrors the identical fix/test for the sibling POWER_CONSTRAINED mode
    in test_library_api_turning_power_constrained_errors.py -- both modes
    share the same underlying _scale_metrics_to_power_budget() helper."""

    result = calculate_turning(
        diameter=1e-305,
        depth_of_cut=1e-310,
        length_of_cut=1,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=10**1000,
        target_feed_rate=0.3,
    )

    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
