"""Contract test: CALCULATION_OVERFLOW guard for extreme-but-individually
-valid inputs.

``feed_per_tooth`` and ``target_rpm`` deliberately have no configurable
upper bound (FR-008/FR-018, spec.md Clarifications) — but an extreme value
in either can still make a downstream product (e.g. ``feed_rate_mm_min =
rpm * feed_per_tooth_mm * number_of_teeth``) overflow to ``inf``. Rather
than surface a result mixing finite and inf/nan fields, this must be
reported as a structured ``CALCULATION_OVERFLOW`` error (FR-012/FR-015
never-raises contract) for STANDARD and FIXED_RPM modes (POWER_CONSTRAINED
already has its own ``INFEASIBLE_POWER_BUDGET`` guard, covered by
tests/contract/test_library_api_milling_power_constrained_errors.py).
"""

from mfgparams import CalculationMode, calculate_end_milling, calculate_face_milling

_END_MILLING_ARGS = dict(
    diameter=10,
    axial_depth_of_cut=2,
    radial_depth_of_cut=5,
    number_of_teeth=4,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)

_FACE_MILLING_ARGS = dict(
    diameter=50,
    axial_depth_of_cut=1.5,
    width_of_cut=40,
    number_of_teeth=5,
    length_of_cut=200,
    material="Mild Steel",
    tool="Carbide",
)


def test_end_milling_extreme_feed_per_tooth_standard_mode_reports_overflow():
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        feed_per_tooth=1e308,
        mode=CalculationMode.STANDARD,
    )
    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.spindle_speed_rpm is None
    assert result.feed_rate is None
    assert result.material_removal_rate is None


def test_face_milling_extreme_feed_per_tooth_standard_mode_reports_overflow():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        feed_per_tooth=1e308,
        mode=CalculationMode.STANDARD,
    )
    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.spindle_speed_rpm is None


def test_end_milling_extreme_feed_per_tooth_fixed_rpm_mode_reports_overflow():
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        feed_per_tooth=1e308,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=1200,
    )
    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.spindle_speed_rpm is None


def test_end_milling_normal_feed_per_tooth_does_not_overflow():
    """Sanity check: an ordinary, realistic feed_per_tooth is unaffected."""
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        feed_per_tooth=0.05,
        mode=CalculationMode.STANDARD,
    )
    assert result.error is None
    assert result.spindle_speed_rpm is not None


def test_end_milling_subnormal_target_rpm_reports_overflow_not_crash():
    """FIXED_RPM's target_rpm has no lower bound beyond positivity — a
    positive-subnormal value (e.g. 5e-324) underflows feed_rate_mm_min to
    exactly 0.0, which previously raised ZeroDivisionError when computing
    machining_time_min (length_of_cut_mm / feed_rate_mm_min). Must
    instead surface as a structured CALCULATION_OVERFLOW result
    (FR-012/FR-015 never-raises contract)."""
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        feed_per_tooth=0.05,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=5e-324,
    )
    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.spindle_speed_rpm is None


def test_face_milling_subnormal_target_rpm_reports_overflow_not_crash():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        feed_per_tooth=0.15,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=5e-324,
    )
    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.spindle_speed_rpm is None


def test_end_milling_subnormal_axial_depth_of_cut_reports_overflow_not_zero():
    """``axial_depth_of_cut`` has no configurable lower bound beyond
    positivity — a positive-subnormal value (e.g. 5e-324) underflows
    torque_nm/power_kw/material_removal_rate_cm3_min to exactly 0.0
    while every field stays finite. Since none of these outputs can ever
    legitimately be zero for validated-positive inputs, a computed zero
    must be rejected as CALCULATION_OVERFLOW rather than returned as a
    spuriously "successful" zero-power result (_reject_if_invalid()
    requires every field to be finite AND strictly positive)."""

    end_milling_args = dict(_END_MILLING_ARGS)
    end_milling_args["axial_depth_of_cut"] = 5e-324

    result = calculate_end_milling(
        **end_milling_args,
        feed_per_tooth=0.05,
        mode=CalculationMode.STANDARD,
    )
    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.power_required is None
    assert result.torque is None
    assert result.material_removal_rate is None


def test_face_milling_subnormal_axial_depth_of_cut_reports_overflow_not_zero():
    face_milling_args = dict(_FACE_MILLING_ARGS)
    face_milling_args["axial_depth_of_cut"] = 5e-324

    result = calculate_face_milling(
        **face_milling_args,
        feed_per_tooth=0.15,
        mode=CalculationMode.STANDARD,
    )
    assert result.error is not None
    assert result.error.code == "CALCULATION_OVERFLOW"
    assert result.power_required is None
    assert result.torque is None
    assert result.material_removal_rate is None
