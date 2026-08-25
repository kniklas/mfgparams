"""Contract test: milling mode mutual exclusivity, MODE_CONFLICT (T022,
T035; FR-009).

Per quickstart.md Scenario 6, for both milling sub-operations:
- ``POWER_CONSTRAINED`` mode with a ``target_rpm`` supplied is rejected.
- ``POWER_CONSTRAINED`` mode with no ``available_power`` supplied is
  rejected (FR-009's other conflicting-arguments sub-case; T035, closing
  a gap found by ``/speckit.converge``).
- ``FIXED_RPM`` mode with ``target_rpm`` omitted is rejected.

Mirrors tests/contract/test_mode_conflict.py (drilling).
"""

from mfgparams import CalculationMode, calculate_end_milling, calculate_face_milling

_END_MILLING_ARGS = dict(
    diameter=10,
    axial_depth_of_cut=2,
    radial_depth_of_cut=5,
    feed_per_tooth=0.05,
    number_of_teeth=4,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)

_FACE_MILLING_ARGS = dict(
    diameter=50,
    axial_depth_of_cut=1.5,
    width_of_cut=40,
    feed_per_tooth=0.15,
    number_of_teeth=5,
    length_of_cut=200,
    material="Mild Steel",
    tool="Carbide",
)


def test_end_milling_power_constrained_with_target_rpm_is_mode_conflict():
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=1.0,
        target_rpm=3000,
    )

    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"
    assert result.spindle_speed_rpm is None


def test_end_milling_power_constrained_without_available_power_is_mode_conflict():
    """FR-009's other conflicting-arguments sub-case: POWER_CONSTRAINED mode
    requires available_power; omitting it is MODE_CONFLICT, not treated as
    an unconstrained standard calculation (T035)."""

    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=None,
    )

    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"
    assert result.spindle_speed_rpm is None


def test_end_milling_fixed_rpm_without_target_rpm_is_invalid_target_rpm():
    """A missing target_rpm in FIXED_RPM mode is INVALID_TARGET_RPM, not
    MODE_CONFLICT (FIXED_RPM's own required-field check fires first)."""

    result = calculate_end_milling(
        **_END_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=None
    )

    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"
    assert result.spindle_speed_rpm is None


def test_end_milling_standard_mode_ignores_target_rpm_and_available_power_together():
    """STANDARD mode never conflicts: any supplied target_rpm/available_power
    is simply unused/ignored (mode is authoritative)."""

    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.STANDARD,
        available_power=1.0,
        target_rpm=3000,
    )

    assert result.error is None
    assert result.mode is CalculationMode.STANDARD


def test_face_milling_power_constrained_with_target_rpm_is_mode_conflict():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=1.0,
        target_rpm=500,
    )

    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"
    assert result.spindle_speed_rpm is None


def test_face_milling_power_constrained_without_available_power_is_mode_conflict():
    """FR-009's other conflicting-arguments sub-case: POWER_CONSTRAINED mode
    requires available_power; omitting it is MODE_CONFLICT, not treated as
    an unconstrained standard calculation (T035)."""

    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=None,
    )

    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"
    assert result.spindle_speed_rpm is None


def test_face_milling_fixed_rpm_without_target_rpm_is_invalid_target_rpm():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=None
    )

    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"
    assert result.spindle_speed_rpm is None


def test_face_milling_standard_mode_ignores_target_rpm_and_available_power_together():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.STANDARD,
        available_power=1.0,
        target_rpm=500,
    )

    assert result.error is None
    assert result.mode is CalculationMode.STANDARD
