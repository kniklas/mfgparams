"""Contract test: mode mutual exclusivity, MODE_CONFLICT (T021; FR-009).

Per quickstart.md Scenario 6:
- ``POWER_CONSTRAINED`` mode with a ``target_rpm`` supplied is rejected.
- ``FIXED_RPM`` mode with ``target_rpm`` omitted is rejected.
"""

import pytest

from mfgparams import CalculationMode, calculate


def test_power_constrained_with_target_rpm_is_mode_conflict():
    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=1.0,
        target_rpm=500,
    )

    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"
    assert result.spindle_speed_rpm is None


def test_fixed_rpm_without_target_rpm_is_invalid_target_rpm():
    """A missing target_rpm in FIXED_RPM mode is INVALID_TARGET_RPM, not
    MODE_CONFLICT (per data-model.md/validate_mode_arguments semantics —
    FIXED_RPM's own required-field check fires first)."""
    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=None,
    )

    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"
    assert result.spindle_speed_rpm is None


def test_feed_rate_constrained_mode_is_unsupported_for_drilling():
    """Copilot review finding on specs/020-turning-feed-per-rotation PR
    #101 (HIGH): FEED_RATE_CONSTRAINED is turning-only, but the shared
    CalculationMode enum member still passes drilling's own type contract.
    Without an explicit rejection, drilling's mode dispatch silently fell
    through to its STANDARD branch and returned standard metrics tagged
    with FEED_RATE_CONSTRAINED instead of a structured error."""

    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
    )

    assert result.error is not None
    assert result.error.code == "UNSUPPORTED_MODE"
    assert result.spindle_speed_rpm is None
    assert result.mode is CalculationMode.FEED_RATE_CONSTRAINED


@pytest.mark.parametrize(
    "mode",
    [CalculationMode.ROTATION_AND_FEED_CONSTRAINED, CalculationMode.POWER_AND_FEED_CONSTRAINED],
)
def test_combined_constraint_modes_are_unsupported_for_drilling(mode):
    """specs/021-turning-combined-constraints research.md #7: both new
    turning-only modes are turning-only, same as FEED_RATE_CONSTRAINED --
    extended proactively rather than left for a review round to catch."""

    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=mode,
    )

    assert result.error is not None
    assert result.error.code == "UNSUPPORTED_MODE"
    assert result.spindle_speed_rpm is None
    assert result.mode is mode
    # MEDIUM Copilot review finding on PR #102: the rendered message must
    # not misleadingly name a different mode (it used to hardcode
    # "Feed-rate-constrained mode" for every TURNING_ONLY_MODES rejection).
    assert "feed-rate-constrained" not in result.error.message.lower()


def test_standard_mode_ignores_target_rpm_and_available_power_together():
    """STANDARD mode never conflicts: any supplied target_rpm/available_power
    is simply unused/ignored (mode is authoritative)."""
    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.STANDARD,
        available_power=1.0,
        target_rpm=500,
    )

    assert result.error is None
    assert result.mode is CalculationMode.STANDARD
