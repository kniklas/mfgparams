"""Contract test: fixed-RPM mode success response shape (T017).

Per contracts/library-api-delta.md: ``spindle_speed_rpm`` echoes
``target_rpm`` exactly, ``mode=FIXED_RPM``, and all dependent fields
(feed_rate, machining_time, torque, power_required) are populated.
"""

from mfgparams import CalculationMode, UnitSystem, calculate


def test_fixed_rpm_success_response_shape():
    result = calculate(
        diameter=10,
        depth=25,
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


def test_fixed_rpm_success_imperial():
    result = calculate(
        diameter=10 / 25.4,
        depth=25 / 25.4,
        material="Mild Steel",
        tool="Carbide",
        unit_system=UnitSystem.IMPERIAL,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=750,
    )

    assert result.error is None
    assert result.mode is CalculationMode.FIXED_RPM
    assert result.unit_system is UnitSystem.IMPERIAL
    assert result.spindle_speed_rpm == 750
