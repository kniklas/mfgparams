"""Integration test: fixed-RPM mode with optional advisory available_power
(T020; FR-008), for both milling sub-operations.

An exceeded power budget sets ``feasibility_warning`` without altering
``target_rpm``/``spindle_speed_rpm``; a sufficient budget leaves no
warning. Mirrors tests/integration/test_fixed_rpm_feasibility.py
(drilling).
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


def test_end_milling_exceeded_power_sets_feasibility_warning_but_keeps_target_rpm():
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=20000,  # deliberately high RPM -> large power requirement
        available_power=0.01,  # deliberately low available power
    )

    assert result.error is None
    assert result.mode is CalculationMode.FIXED_RPM
    assert result.spindle_speed_rpm == 20000
    assert result.feasibility_warning is not None


def test_end_milling_sufficient_power_produces_no_feasibility_warning():
    baseline = calculate_end_milling(
        **_END_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=3000
    )
    assert baseline.error is None

    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=3000,
        available_power=baseline.power_required * 2,  # ample surplus
    )

    assert result.error is None
    assert result.spindle_speed_rpm == 3000
    assert result.feasibility_warning is None


def test_face_milling_exceeded_power_sets_feasibility_warning_but_keeps_target_rpm():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=5000,  # deliberately high RPM -> large power requirement
        available_power=0.01,  # deliberately low available power
    )

    assert result.error is None
    assert result.mode is CalculationMode.FIXED_RPM
    assert result.spindle_speed_rpm == 5000
    assert result.feasibility_warning is not None


def test_face_milling_sufficient_power_produces_no_feasibility_warning():
    baseline = calculate_face_milling(
        **_FACE_MILLING_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=500
    )
    assert baseline.error is None

    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=500,
        available_power=baseline.power_required * 2,  # ample surplus
    )

    assert result.error is None
    assert result.spindle_speed_rpm == 500
    assert result.feasibility_warning is None
