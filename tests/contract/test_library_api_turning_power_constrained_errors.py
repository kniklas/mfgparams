"""Contract test: turning power-constrained mode INFEASIBLE_POWER_BUDGET /
MODE_CONFLICT errors (specs/019-turning-calculations).

Mirrors tests/contract/test_library_api_milling_power_constrained_errors.py.
"""

from mfgparams import CalculationMode, calculate_turning

_ARGS = dict(
    diameter=40,
    depth_of_cut=2,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)


def test_zero_available_power_is_infeasible():
    result = calculate_turning(**_ARGS, mode=CalculationMode.POWER_CONSTRAINED, available_power=0)
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.cutting_force is None


def test_negative_available_power_is_infeasible():
    result = calculate_turning(
        **_ARGS, mode=CalculationMode.POWER_CONSTRAINED, available_power=-1.0
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.feed_rate is None
    assert result.machining_time is None
    assert result.torque is None
    assert result.power_required is None
    assert result.cutting_force is None
    assert result.mode is CalculationMode.POWER_CONSTRAINED


def test_missing_available_power_is_mode_conflict():
    result = calculate_turning(**_ARGS, mode=CalculationMode.POWER_CONSTRAINED)
    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"


def test_infeasible_error_does_not_raise():
    """FR-016: never raises, always returns a structured CalculationResult."""
    result = calculate_turning(
        **_ARGS, mode=CalculationMode.POWER_CONSTRAINED, available_power=-100.0
    )
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
