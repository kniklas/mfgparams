"""Contract test: fixed-RPM mode INVALID_TARGET_RPM error response (T019).

Per contracts/library-api-milling-modes-delta.md; mirrors
tests/contract/test_library_api_fixed_rpm_errors.py (drilling) for both
milling sub-operations.
"""

import math

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


def test_end_milling_zero_target_rpm_is_invalid():
    result = calculate_end_milling(
        **_END_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=0
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"
    assert result.spindle_speed_rpm is None


def test_end_milling_negative_target_rpm_is_invalid():
    result = calculate_end_milling(
        **_END_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=-100
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_end_milling_missing_target_rpm_is_invalid():
    result = calculate_end_milling(
        **_END_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=None
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_end_milling_nan_target_rpm_is_invalid():
    result = calculate_end_milling(
        **_END_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=math.nan
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_end_milling_infinite_target_rpm_is_invalid():
    result = calculate_end_milling(
        **_END_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=math.inf
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_end_milling_invalid_target_rpm_never_raises():
    """FR-015: never raises, always returns a structured CalculationResult."""
    result = calculate_end_milling(
        **_END_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=-1
    )
    assert result.error.code == "INVALID_TARGET_RPM"


def test_face_milling_zero_target_rpm_is_invalid():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=0
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_face_milling_negative_target_rpm_is_invalid():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=-100
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_face_milling_missing_target_rpm_is_invalid():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=None
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_face_milling_nan_target_rpm_is_invalid():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=math.nan
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_face_milling_infinite_target_rpm_is_invalid():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=math.inf
    )
    assert result.error is not None
    assert result.error.code == "INVALID_TARGET_RPM"


def test_face_milling_invalid_target_rpm_never_raises():
    """FR-015: never raises, always returns a structured CalculationResult."""
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=-1
    )
    assert result.error.code == "INVALID_TARGET_RPM"
