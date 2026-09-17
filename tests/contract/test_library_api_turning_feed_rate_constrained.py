"""Contract test: turning feed-rate-constrained mode success response shape
(specs/020-turning-feed-per-rotation).

Per contracts/library-api-turning-feed-per-rotation-delta.md: spindle speed
is derived exactly as standard mode, `feed_per_rotation` echoes the supplied
value, and dependent metrics (cutting force, torque, power) are recomputed
from it. Mirrors tests/contract/test_library_api_turning_fixed_rpm.py.
"""

import math

from mfgparams import CalculationMode, UnitSystem, calculate_turning
from mfgparams.units import n_to_lbf

_ARGS = dict(
    diameter=40,
    depth_of_cut=2,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)


def test_turning_feed_rate_constrained_success_response_shape():
    standard = calculate_turning(**_ARGS)

    result = calculate_turning(
        **_ARGS, mode=CalculationMode.FEED_RATE_CONSTRAINED, target_feed_rate=0.5
    )

    assert result.error is None
    assert result.mode is CalculationMode.FEED_RATE_CONSTRAINED
    assert result.unit_system is UnitSystem.METRIC
    # FR-005: spindle speed is derived exactly as standard mode's.
    assert math.isclose(result.spindle_speed_rpm, standard.spindle_speed_rpm, rel_tol=1e-9)
    # feed_per_rotation echoes the supplied value directly.
    assert result.feed_per_rotation == 0.5
    assert result.feed_rate is not None
    assert result.machining_time is not None
    assert result.torque is not None
    assert result.power_required is not None
    assert result.cutting_force is not None


def test_turning_feed_rate_constrained_dependent_metrics_recomputed_from_supplied_feed():
    """Unlike FIXED_RPM's torque/cutting_force (unchanged from nominal),
    feed-rate-constrained mode's cutting_force/torque/power_required DO
    change from the nominal value, because turning's cutting force depends
    directly on feed per revolution."""

    standard = calculate_turning(**_ARGS)

    result = calculate_turning(
        **_ARGS, mode=CalculationMode.FEED_RATE_CONSTRAINED, target_feed_rate=0.5
    )

    assert not math.isclose(result.cutting_force, standard.cutting_force, rel_tol=1e-9)
    assert not math.isclose(result.torque, standard.torque, rel_tol=1e-9)
    assert not math.isclose(result.feed_rate, standard.feed_rate, rel_tol=1e-9)


def test_turning_feed_rate_constrained_feasibility_warning_when_power_exceeded():
    """FR-008: available_power remains optional/advisory in feed-rate-
    constrained mode -- a warning is included if exceeded, absent if not."""

    exceeded = calculate_turning(
        **_ARGS,
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
        target_feed_rate=0.5,
        available_power=0.1,
    )
    assert exceeded.error is None
    assert exceeded.feasibility_warning is not None

    sufficient = calculate_turning(
        **_ARGS,
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
        target_feed_rate=0.5,
        available_power=1000.0,
    )
    assert sufficient.error is None
    assert sufficient.feasibility_warning is None


def test_turning_feed_rate_constrained_imperial_round_trip_matches_metric():
    """MEDIUM Copilot review finding on this PR: no contract test exercised
    target_feed_rate under IMPERIAL. An imperial call converts diameter/
    depth/length/target_feed_rate to canonical metric internally and
    converts results back, so it must describe the same physical
    feed-rate-constrained operation as the equivalent metric call --
    mirroring test_library_api_turning.py's own imperial/metric round-trip
    test for the base (non-mode) contract."""

    metric = calculate_turning(
        **_ARGS,
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
        target_feed_rate=0.5,
        unit_system=UnitSystem.METRIC,
    )
    imperial = calculate_turning(
        diameter=_ARGS["diameter"] / 25.4,
        depth_of_cut=_ARGS["depth_of_cut"] / 25.4,
        length_of_cut=_ARGS["length_of_cut"] / 25.4,
        material=_ARGS["material"],
        tool=_ARGS["tool"],
        mode=CalculationMode.FEED_RATE_CONSTRAINED,
        target_feed_rate=0.5 / 25.4,
        unit_system=UnitSystem.IMPERIAL,
    )

    assert imperial.error is None
    # feed_per_rotation echoes the supplied in/rev value directly.
    assert math.isclose(imperial.feed_per_rotation, 0.5 / 25.4, rel_tol=1e-9)
    # Spindle speed (RPM) and machining time (minutes) are unit-independent.
    assert math.isclose(imperial.spindle_speed_rpm, metric.spindle_speed_rpm, rel_tol=1e-6)
    assert math.isclose(imperial.machining_time, metric.machining_time, rel_tol=1e-6)
    # Cutting force/torque/power drive the same physical operation, just
    # expressed in imperial units.
    assert math.isclose(imperial.cutting_force, n_to_lbf(metric.cutting_force), rel_tol=1e-6)
