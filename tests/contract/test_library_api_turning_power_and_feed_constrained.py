"""Contract test: turning power-and-feed-constrained mode success response
shape (specs/021-turning-combined-constraints).

Per contracts/library-api-turning-combined-constraints-delta.md: feed per
rotation is supplied directly and echoed exactly; spindle speed is solved
to the highest value feasible within the supplied power at that feed.
Mirrors tests/contract/test_library_api_turning_power_constrained.py.
"""

import math

from mfgparams import CalculationMode, UnitSystem, calculate_turning
from mfgparams.units import kw_to_hp, n_to_lbf, nm_to_in_lb

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


def test_power_and_feed_constrained_imperial_round_trip_matches_metric():
    """MEDIUM Copilot review finding on PR #102: no contract test exercised
    available_power/target_feed_rate under IMPERIAL for this mode. An
    imperial call converts diameter/depth/length/target_feed_rate/
    available_power to canonical metric internally and converts results
    back, so it must describe the same physical operation as the
    equivalent metric call -- mirroring
    test_library_api_turning_feed_rate_constrained.py's own round-trip
    test for the sibling mode."""

    budget_kw = 0.5
    metric = calculate_turning(
        **_ARGS,
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=budget_kw,
        target_feed_rate=0.3,
        unit_system=UnitSystem.METRIC,
    )
    imperial = calculate_turning(
        diameter=_ARGS["diameter"] / 25.4,
        depth_of_cut=_ARGS["depth_of_cut"] / 25.4,
        length_of_cut=_ARGS["length_of_cut"] / 25.4,
        material=_ARGS["material"],
        tool=_ARGS["tool"],
        mode=CalculationMode.POWER_AND_FEED_CONSTRAINED,
        available_power=kw_to_hp(budget_kw),
        target_feed_rate=0.3 / 25.4,
        unit_system=UnitSystem.IMPERIAL,
    )

    assert imperial.error is None
    assert math.isclose(imperial.feed_per_rotation, 0.3 / 25.4, rel_tol=1e-9)
    assert math.isclose(imperial.spindle_speed_rpm, metric.spindle_speed_rpm, rel_tol=1e-6)
    assert math.isclose(imperial.machining_time, metric.machining_time, rel_tol=1e-6)
    assert math.isclose(imperial.cutting_force, n_to_lbf(metric.cutting_force), rel_tol=1e-6)
    assert math.isclose(imperial.torque, nm_to_in_lb(metric.torque), rel_tol=1e-6)
    assert math.isclose(imperial.power_required, kw_to_hp(metric.power_required), rel_tol=1e-6)
