"""Contract test: power-constrained mode INFEASIBLE_POWER_BUDGET error
response (T012).

Per contracts/library-api-milling-modes-delta.md; mirrors
tests/contract/test_library_api_power_constrained_errors.py (drilling) for
both milling sub-operations.
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


def test_end_milling_zero_available_power_is_infeasible():
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=0,
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.material_removal_rate is None


def test_end_milling_negative_available_power_is_infeasible():
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=-1.0,
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.feed_rate is None
    assert result.machining_time is None
    assert result.torque is None
    assert result.power_required is None
    assert result.mode is CalculationMode.POWER_CONSTRAINED


def test_end_milling_infeasible_error_does_not_raise():
    """FR-015: never raises, always returns a structured CalculationResult."""
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=-100.0,
    )
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"


def test_face_milling_zero_available_power_is_infeasible():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=0,
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.material_removal_rate is None


def test_face_milling_negative_available_power_is_infeasible():
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=-1.0,
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.mode is CalculationMode.POWER_CONSTRAINED


def test_face_milling_infeasible_error_does_not_raise():
    """FR-015: never raises, always returns a structured CalculationResult."""
    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=-100.0,
    )
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"


def test_end_milling_subnormal_available_power_is_infeasible_not_crash():
    """A positive-subnormal available_power (e.g. 5e-324) can make the
    adjusted spindle speed underflow, or leave a downstream division
    overflowing to inf, before it ever reaches this function's own
    positivity check — must still surface as a structured
    INFEASIBLE_POWER_BUDGET result, never a ZeroDivisionError crash
    (FR-015)."""
    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=5e-324,
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None


def test_end_milling_tiny_feed_per_tooth_no_op_path_is_infeasible_not_a_bad_result():
    """A tiny positive feed_per_tooth can make the *nominal* power
    underflow towards zero while machining_time overflows to inf — this
    happens on the no-reduction-needed no-op path (available power
    comfortably exceeds nominal), which returns the nominal metrics
    directly, before ever reaching the adjusted-path finiteness guard in
    calculate_power_constrained_milling_metrics(). Must still surface as
    a structured INFEASIBLE_POWER_BUDGET result, not a "successful"
    result containing inf/nan fields."""
    result = calculate_end_milling(
        **{**_END_MILLING_ARGS, "feed_per_tooth": 5e-320},
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=1000.0,
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.machining_time is None
