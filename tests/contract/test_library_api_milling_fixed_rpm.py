"""Contract test: fixed-RPM mode success response shape (T018).

Per contracts/library-api-milling-modes-delta.md: ``spindle_speed_rpm``
echoes ``target_rpm`` exactly, ``mode=FIXED_RPM``, and all dependent
fields are populated for both milling sub-operations. Mirrors
tests/contract/test_library_api_fixed_rpm.py (drilling).
"""

from mfgparams import (
    CalculationMode,
    UnitSystem,
    calculate_end_milling,
    calculate_face_milling,
)


def test_end_milling_fixed_rpm_success_response_shape():
    result = calculate_end_milling(
        diameter=10,
        axial_depth_of_cut=2,
        radial_depth_of_cut=5,
        feed_per_tooth=0.05,
        number_of_teeth=4,
        length_of_cut=100,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=3000,
    )

    assert result.error is None
    assert result.mode is CalculationMode.FIXED_RPM
    assert result.unit_system is UnitSystem.METRIC
    assert result.spindle_speed_rpm == 3000
    assert result.feed_rate is not None
    assert result.machining_time is not None
    assert result.torque is not None
    assert result.power_required is not None
    assert result.material_removal_rate is not None


def test_face_milling_fixed_rpm_success_response_shape():
    result = calculate_face_milling(
        diameter=50,
        axial_depth_of_cut=1.5,
        width_of_cut=40,
        feed_per_tooth=0.15,
        number_of_teeth=5,
        length_of_cut=200,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=500,
    )

    assert result.error is None
    assert result.mode is CalculationMode.FIXED_RPM
    assert result.unit_system is UnitSystem.METRIC
    assert result.spindle_speed_rpm == 500
    assert result.feed_rate is not None
    assert result.machining_time is not None
    assert result.torque is not None
    assert result.power_required is not None
    assert result.material_removal_rate is not None
