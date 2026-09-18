"""Contract test: turning fixed-RPM mode success response shape
(specs/019-turning-calculations).

Per contracts/library-api-turning.md: ``spindle_speed_rpm`` echoes
``target_rpm`` exactly, ``mode=FIXED_RPM``, and every dependent field
(including the new ``cutting_force``) is populated. Mirrors
tests/contract/test_library_api_milling_fixed_rpm.py.
"""

from mfgparams import CalculationMode, UnitSystem, calculate_turning

_ARGS = dict(
    diameter=40,
    depth_of_cut=2,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)


def test_turning_fixed_rpm_success_response_shape():
    result = calculate_turning(**_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=900)

    assert result.error is None
    assert result.mode is CalculationMode.FIXED_RPM
    assert result.unit_system is UnitSystem.METRIC
    assert result.spindle_speed_rpm == 900
    assert result.feed_rate is not None
    assert result.machining_time is not None
    assert result.torque is not None
    assert result.power_required is not None
    assert result.cutting_force is not None
    assert result.feed_per_rotation is not None  # specs/020-turning-feed-per-rotation FR-001


def test_turning_fixed_rpm_cutting_force_and_torque_independent_of_rpm():
    """research.md #1: cutting force/torque depend only on geometry and
    material/tool, never on spindle speed."""

    at_900 = calculate_turning(**_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=900)
    at_300 = calculate_turning(**_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=300)

    assert at_900.cutting_force == at_300.cutting_force
    assert at_900.torque == at_300.torque
    assert at_900.feed_rate != at_300.feed_rate
    assert at_900.power_required != at_300.power_required
    # feed_per_rotation is derived from material/tool, not spindle speed
    # (specs/020-turning-feed-per-rotation research.md #1).
    assert at_900.feed_per_rotation == at_300.feed_per_rotation


def test_turning_fixed_rpm_feasibility_warning_when_power_exceeded():
    result = calculate_turning(
        **_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=900, available_power=0.1
    )

    assert result.error is None
    assert result.feasibility_warning is not None
