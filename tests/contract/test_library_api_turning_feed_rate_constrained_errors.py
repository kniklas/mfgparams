"""Contract test: turning feed-rate-constrained mode error responses
(specs/020-turning-feed-per-rotation).

Covers INVALID_TARGET_FEED_RATE (missing/zero/negative/non-numeric), the
full MODE_CONFLICT symmetry (FR-007), and that MISSING_MATERIAL/MISSING_TOOL
still take precedence over a feed-rate-specific error (FR-009). Mirrors
tests/contract/test_library_api_turning_fixed_rpm_errors.py.
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


def test_missing_target_feed_rate_reports_invalid_target_feed_rate():
    result = calculate_turning(**_ARGS, mode=CalculationMode.FEED_RATE_CONSTRAINED)

    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_FEED_RATE"
    assert result.spindle_speed_rpm is None
    assert result.feed_per_rotation is None


@pytest.mark.parametrize(
    "bad_value", [0, -1, -0.5, float("nan"), float("inf"), float("-inf"), "fast"]
)
def test_invalid_target_feed_rate_reports_invalid_target_feed_rate(bad_value):
    result = calculate_turning(
        **_ARGS, mode=CalculationMode.FEED_RATE_CONSTRAINED, target_feed_rate=bad_value
    )

    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_FEED_RATE"


def test_feed_rate_constrained_with_target_rpm_is_mode_conflict():
    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
        target_feed_rate=0.5,
        target_rpm=900,
    )

    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"


def test_invalid_target_feed_rate_combined_with_target_rpm_is_still_mode_conflict():
    """Copilot review finding on this PR: when *two* mode-driving inputs are
    supplied at once (target_feed_rate and target_rpm, under
    FEED_RATE_CONSTRAINED), MODE_CONFLICT must win even if the
    target_feed_rate value is itself individually invalid -- mirroring
    POWER_CONSTRAINED's own established precedent (its target_rpm-conflict
    check already runs before its available_power validity check inside
    validate_mode_arguments). Previously, target_feed_rate's own
    positive/finite check ran first and returned INVALID_TARGET_FEED_RATE
    before the target_rpm conflict was ever considered."""

    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
        target_feed_rate=-1,
        target_rpm=900,
    )

    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"


@pytest.mark.parametrize(
    "mode",
    [CalculationMode.STANDARD, CalculationMode.POWER_CONSTRAINED, CalculationMode.FIXED_RPM],
)
def test_target_feed_rate_supplied_under_a_different_mode_is_mode_conflict(mode):
    """FR-007: target_feed_rate only makes sense under FEED_RATE_CONSTRAINED
    mode -- supplying it under any other mode is rejected, not silently
    ignored, mirroring how a stray target_rpm under an unrelated mode is
    also rejected."""

    kwargs = dict(**_ARGS, mode=mode, target_feed_rate=0.5)
    if mode is CalculationMode.POWER_CONSTRAINED:
        kwargs["available_power"] = 1.0
    if mode is CalculationMode.FIXED_RPM:
        kwargs["target_rpm"] = 900

    result = calculate_turning(**kwargs)

    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"


def test_missing_material_takes_precedence_over_feed_rate_constrained_validation():
    """FR-009: material/tool presence is required before any mode-specific
    check runs, exactly as the other three turning modes already require."""

    result = calculate_turning(
        diameter=40,
        depth_of_cut=2,
        length_of_cut=100,
        material="",
        tool="Carbide",
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
        target_feed_rate=0.5,
    )

    assert result.error is not None
    assert result.error.code == "MISSING_MATERIAL"


def test_missing_tool_takes_precedence_over_feed_rate_constrained_validation():
    result = calculate_turning(
        diameter=40,
        depth_of_cut=2,
        length_of_cut=100,
        material="Mild Steel",
        tool="",
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
        target_feed_rate=0.5,
    )

    assert result.error is not None
    assert result.error.code == "MISSING_TOOL"


def test_extreme_subnormal_input_returns_structured_overflow_error_not_a_stale_success():
    """spec.md Edge Cases: an extreme-but-individually-"valid" feed rate
    combined with subnormal geometry must not silently underflow a
    dependent metric to 0.0 while still returning error=None -- mirrors
    test_extreme_subnormal_geometry_returns_structured_overflow_error_not_a_stale_success
    in test_library_api_turning.py, which already covers this for
    STANDARD mode (research.md #6: _reject_if_invalid's guard now also
    covers feed_per_rev_mm)."""

    result = calculate_turning(
        diameter=1e-300,
        depth_of_cut=1e-310,
        length_of_cut=1,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
        target_feed_rate=5e-320,
    )

    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.spindle_speed_rpm is None
    assert result.feed_per_rotation is None
