"""Contract test: fixed-RPM mode INVALID_TARGET_RPM error response (T018).

Per contracts/library-api-delta.md.
"""

import math

from mfgparams import CalculationMode, calculate


def test_zero_target_rpm_is_invalid():
    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=0,
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"
    assert result.spindle_speed_rpm is None


def test_negative_target_rpm_is_invalid():
    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=-100,
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_missing_target_rpm_is_invalid():
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


def test_nan_target_rpm_is_invalid():
    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=math.nan,
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_infinite_target_rpm_is_invalid():
    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=math.inf,
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_invalid_target_rpm_never_raises():
    """FR-015: never raises, always returns a structured CalculationResult."""
    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=-1,
    )
    assert result.error.code == "INVALID_TARGET_RPM"
