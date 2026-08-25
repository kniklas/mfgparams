"""Integration test: power-constrained mode is a no-op when the supplied
budget already covers the nominal requirement (T013).

Covers both the comfortable-surplus case and the exact-equality boundary
(FR-003; quickstart.md Scenario 2) for both end-milling and face-milling.
Mirrors tests/integration/test_power_constrained_noop.py (drilling).
"""

import math

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


def _assert_noop(standard, constrained):
    assert constrained.error is None
    assert math.isclose(constrained.spindle_speed_rpm, standard.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(constrained.feed_rate, standard.feed_rate, rel_tol=1e-9)
    assert math.isclose(constrained.machining_time, standard.machining_time, rel_tol=1e-9)
    assert math.isclose(constrained.torque, standard.torque, rel_tol=1e-9)
    assert math.isclose(constrained.power_required, standard.power_required, rel_tol=1e-9)
    assert constrained.mode is CalculationMode.POWER_CONSTRAINED
    assert standard.mode is CalculationMode.STANDARD


def test_end_milling_power_constrained_matches_standard_when_budget_exceeds_nominal():
    standard = calculate_end_milling(**_END_MILLING_ARGS)
    generous_budget = standard.power_required * 2.0

    constrained = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=generous_budget,
    )

    _assert_noop(standard, constrained)


def test_end_milling_power_constrained_matches_standard_at_exact_equality_boundary():
    standard = calculate_end_milling(**_END_MILLING_ARGS)

    constrained = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=standard.power_required,
    )

    assert constrained.error is None
    assert math.isclose(constrained.spindle_speed_rpm, standard.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(constrained.power_required, standard.power_required, rel_tol=1e-9)


def test_face_milling_power_constrained_matches_standard_when_budget_exceeds_nominal():
    standard = calculate_face_milling(**_FACE_MILLING_ARGS)
    generous_budget = standard.power_required * 2.0

    constrained = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=generous_budget,
    )

    _assert_noop(standard, constrained)


def test_face_milling_power_constrained_matches_standard_at_exact_equality_boundary():
    standard = calculate_face_milling(**_FACE_MILLING_ARGS)

    constrained = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=standard.power_required,
    )

    assert constrained.error is None
    assert math.isclose(constrained.spindle_speed_rpm, standard.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(constrained.power_required, standard.power_required, rel_tol=1e-9)
