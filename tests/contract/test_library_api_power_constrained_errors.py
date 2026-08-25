"""Contract test: power-constrained mode INFEASIBLE_POWER_BUDGET error
response (T011).

Per contracts/library-api-delta.md.
"""

from mfgparams import CalculationMode, calculate


def test_zero_available_power_is_infeasible():
    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=0,
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None


def test_negative_available_power_is_infeasible():
    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
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


def test_infeasible_error_does_not_raise():
    """FR-015: never raises, always returns a structured CalculationResult."""
    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=-100.0,
    )
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
