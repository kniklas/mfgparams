"""Contract test: turning rotation-and-feed-constrained mode error responses
(specs/021-turning-combined-constraints).

Covers INVALID_TARGET_RPM/INVALID_TARGET_FEED_RATE (missing/zero/negative/
non-numeric, individually and simultaneously), that MISSING_MATERIAL/
MISSING_TOOL still take precedence, and the CALCULATION_OVERFLOW guard.
Mirrors tests/contract/test_library_api_turning_feed_rate_constrained_errors.py.

Note: unlike FEED_RATE_CONSTRAINED/POWER_CONSTRAINED, ROTATION_AND_FEED_CONSTRAINED
has no MODE_CONFLICT trigger of its own -- target_rpm is one of this mode's own
two required inputs (not something it derives), so it is never rejected as a
conflict here, only under modes that actually derive spindle speed. See
test_target_rpm_is_accepted_not_rejected_unlike_derived_modes below.
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


def test_missing_target_rpm_reports_invalid_target_rpm():
    result = calculate_turning(
        **_ARGS, mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED, target_feed_rate=0.3
    )

    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"
    assert result.spindle_speed_rpm is None
    assert result.feed_per_rotation is None


def test_missing_target_feed_rate_reports_invalid_target_feed_rate():
    result = calculate_turning(
        **_ARGS, mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED, target_rpm=900
    )

    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_FEED_RATE"
    assert result.spindle_speed_rpm is None


def test_both_missing_reports_invalid_target_rpm_first():
    """data-model.md's precedence rule: when both required inputs are
    missing, target_rpm's own validity is checked first -- the same order
    its parameter appears in calculate_turning()'s own signature, and the
    order _validate_mode_inputs() checks the FIXED_RPM-shared block before
    the FEED_RATE_CONSTRAINED-shared block."""

    result = calculate_turning(**_ARGS, mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED)

    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


@pytest.mark.parametrize(
    "bad_value", [0, -1, -0.5, float("nan"), float("inf"), float("-inf"), "fast"]
)
def test_invalid_target_rpm_reports_invalid_target_rpm(bad_value):
    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
        target_rpm=bad_value,
        target_feed_rate=0.3,
    )

    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


@pytest.mark.parametrize(
    "bad_value", [0, -1, -0.5, float("nan"), float("inf"), float("-inf"), "fast"]
)
def test_invalid_target_feed_rate_reports_invalid_target_feed_rate(bad_value):
    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
        target_rpm=900,
        target_feed_rate=bad_value,
    )

    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_FEED_RATE"


def test_target_rpm_is_accepted_not_rejected_unlike_derived_modes():
    """Unlike POWER_CONSTRAINED/FEED_RATE_CONSTRAINED (which derive spindle
    speed and reject a directly-supplied target_rpm as MODE_CONFLICT),
    ROTATION_AND_FEED_CONSTRAINED requires target_rpm directly -- supplying
    it is never a conflict for this mode."""

    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
        target_rpm=900,
        target_feed_rate=0.3,
    )

    assert result.error is None


def test_missing_material_takes_precedence_over_rotation_and_feed_constrained_validation():
    """FR-009: material/tool presence is required before any mode-specific
    check runs, exactly as the other turning modes already require."""

    result = calculate_turning(
        diameter=40,
        depth_of_cut=2,
        length_of_cut=100,
        material="",
        tool="Carbide",
        mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
        target_rpm=900,
        target_feed_rate=0.3,
    )

    assert result.error is not None
    assert result.error.code == "MISSING_MATERIAL"


def test_missing_tool_takes_precedence_over_rotation_and_feed_constrained_validation():
    result = calculate_turning(
        diameter=40,
        depth_of_cut=2,
        length_of_cut=100,
        material="Mild Steel",
        tool="",
        mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
        target_rpm=900,
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
        mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
        target_rpm=5e-320,
        target_feed_rate=5e-320,
    )

    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.spindle_speed_rpm is None
    assert result.feed_per_rotation is None
