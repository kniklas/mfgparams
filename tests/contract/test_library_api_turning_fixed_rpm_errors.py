"""Contract test: turning fixed-RPM mode INVALID_TARGET_RPM/MODE_CONFLICT
errors (specs/019-turning-calculations).

Mirrors tests/contract/test_library_api_milling_fixed_rpm_errors.py.
"""

import math

from mfgparams import CalculationMode, calculate_turning

_ARGS = dict(
    diameter=40,
    depth_of_cut=2,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)


def test_zero_target_rpm_is_invalid():
    result = calculate_turning(**_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=0)
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"
    assert result.spindle_speed_rpm is None


def test_negative_target_rpm_is_invalid():
    result = calculate_turning(**_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=-100)
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_missing_target_rpm_is_invalid():
    result = calculate_turning(**_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=None)
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_nan_target_rpm_is_invalid():
    result = calculate_turning(**_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=math.nan)
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_infinite_target_rpm_is_invalid():
    result = calculate_turning(**_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=math.inf)
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_invalid_target_rpm_never_raises():
    """FR-016: never raises, always returns a structured CalculationResult."""
    result = calculate_turning(**_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=-1)
    assert result.error.code == "INVALID_TARGET_RPM"


def test_target_rpm_combined_with_power_constrained_is_mode_conflict():
    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        target_rpm=900,
        available_power=0.5,
    )
    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"
