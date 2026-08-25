"""Contract test: mode mutual exclusivity, MODE_CONFLICT (T021; FR-009).

Per quickstart.md Scenario 6:
- ``POWER_CONSTRAINED`` mode with a ``target_rpm`` supplied is rejected.
- ``FIXED_RPM`` mode with ``target_rpm`` omitted is rejected.
"""

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
