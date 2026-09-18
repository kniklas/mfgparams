"""Contract test: turning power-and-feed-constrained mode success response
shape (specs/021-turning-combined-constraints).

Per contracts/library-api-turning-combined-constraints-delta.md: feed per
rotation is supplied directly and echoed exactly; spindle speed is solved
to the highest value feasible within the supplied power at that feed.
Mirrors tests/contract/test_library_api_turning_power_constrained.py.
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


def test_power_and_feed_constrained_success_response_shape():
    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=0.5,
        target_feed_rate=0.3,
    )

    assert result.error is None
    assert result.mode is CalculationMode.POWER_AND_FEED_CONSTRAINED
    assert result.unit_system is UnitSystem.METRIC
    assert result.feed_per_rotation == 0.3
    assert result.power_required is not None
    assert result.power_required <= 0.5 or math.isclose(result.power_required, 0.5, rel_tol=1e-9)
    assert result.spindle_speed_rpm is not None
    assert result.machining_time is not None
    assert result.torque is not None
    assert result.cutting_force is not None


def test_power_and_feed_constrained_no_op_when_budget_comfortably_exceeds_nominal():
    """A generous budget returns the same result an unconstrained
    (feed-rate-constrained) calculation at the same feed would."""

    generous = calculate_turning(
        **_ARGS,
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=1000.0,
        target_feed_rate=0.3,
    )
    nominal = calculate_turning(
        **_ARGS, mode=CalculationMode.FEED_RATE_CONSTRAINED, target_feed_rate=0.3
    )

    assert math.isclose(generous.spindle_speed_rpm, nominal.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(generous.power_required, nominal.power_required, rel_tol=1e-9)


def test_power_and_feed_constrained_reduces_spindle_speed_when_budget_below_nominal():
    nominal = calculate_turning(
        **_ARGS, mode=CalculationMode.FEED_RATE_CONSTRAINED, target_feed_rate=0.3
    )
    budget = nominal.power_required * 0.5

    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=budget,
        target_feed_rate=0.3,
    )

    assert result.error is None
    assert result.spindle_speed_rpm < nominal.spindle_speed_rpm
    assert math.isclose(result.power_required, budget, rel_tol=1e-9)
    assert result.feed_per_rotation == 0.3


def test_power_and_feed_constrained_never_emits_a_feasibility_warning():
    """research.md #6: available_power is a hard constraint this mode's
    result already satisfies by construction -- an advisory "exceeds
    available power" warning would be spurious, unlike STANDARD/FIXED_RPM/
    ROTATION_AND_FEED_CONSTRAINED, where available_power is only advisory."""

    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=0.001,
        target_feed_rate=0.3,
    )

    assert result.error is None
    assert result.feasibility_warning is None
