"""Contract test: turning rotation-and-feed-constrained mode success
response shape (specs/021-turning-combined-constraints).

Per contracts/library-api-turning-combined-constraints-delta.md: both
spindle speed and feed per rotation are supplied directly by the caller and
echoed exactly, neither derived from the material/tool's reference values.
Mirrors tests/contract/test_library_api_turning_feed_rate_constrained.py.
"""

import math

from mfgparams import CalculationMode, UnitSystem, calculate_turning

_ARGS = dict(
    diameter=40,
    depth_of_cut=2,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)


def test_rotation_and_feed_constrained_success_response_shape():
    standard = calculate_turning(**_ARGS)

    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
        target_rpm=900,
        target_feed_rate=0.3,
    )

    assert result.error is None
    assert result.mode is CalculationMode.ROTATION_AND_FEED_CONSTRAINED
    assert result.unit_system is UnitSystem.METRIC
    # FR-001: neither value is derived from the material/tool.
    assert result.spindle_speed_rpm == 900
    assert result.feed_per_rotation == 0.3
    assert not math.isclose(result.spindle_speed_rpm, standard.spindle_speed_rpm, rel_tol=1e-9)
    assert not math.isclose(result.feed_per_rotation, standard.feed_per_rotation, rel_tol=1e-9)
    assert result.feed_rate is not None
    assert result.machining_time is not None
    assert result.torque is not None
    assert result.power_required is not None
    assert result.cutting_force is not None


def test_rotation_and_feed_constrained_dependent_metrics_recomputed_from_supplied_values():
    """Machining time, cutting force, torque, and power are all computed
    from the two supplied values, not from any material/tool reference."""

    standard = calculate_turning(**_ARGS)

    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
        target_rpm=900,
        target_feed_rate=0.3,
    )

    assert not math.isclose(result.cutting_force, standard.cutting_force, rel_tol=1e-9)
    assert not math.isclose(result.torque, standard.torque, rel_tol=1e-9)
    assert not math.isclose(result.machining_time, standard.machining_time, rel_tol=1e-9)
    assert not math.isclose(result.power_required, standard.power_required, rel_tol=1e-9)
    # Feed rate (mm/min) = spindle speed * feed per rotation, exactly.
    assert math.isclose(result.feed_rate, 900 * 0.3, rel_tol=1e-9)


def test_rotation_and_feed_constrained_feasibility_warning_when_power_exceeded():
    """FR-006: available_power remains optional/advisory in this mode -- a
    warning is included if exceeded, absent if not, and the estimated
    power is still returned when available_power is omitted entirely."""

    exceeded = calculate_turning(
        **_ARGS,
        mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
        target_rpm=900,
        target_feed_rate=0.3,
        available_power=0.01,
    )
    assert exceeded.error is None
    assert exceeded.feasibility_warning is not None

    sufficient = calculate_turning(
        **_ARGS,
        mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
        target_rpm=900,
        target_feed_rate=0.3,
        available_power=1000.0,
    )
    assert sufficient.error is None
    assert sufficient.feasibility_warning is None

    omitted = calculate_turning(
        **_ARGS,
        mode=CalculationMode.ROTATION_AND_FEED_CONSTRAINED,
        target_rpm=900,
        target_feed_rate=0.3,
    )
    assert omitted.error is None
    assert omitted.feasibility_warning is None
    assert omitted.power_required is not None
