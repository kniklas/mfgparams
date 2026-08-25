"""Integration test: power-constrained mode is a no-op when the supplied
budget already covers the nominal requirement (T012).

Covers both the comfortable-surplus case and the exact-equality boundary
(FR-003, spec.md Clarifications 2026-07-11; quickstart.md Scenario 2).
"""

import math

from mfgparams import CalculationMode, calculate


def test_power_constrained_matches_standard_when_budget_exceeds_nominal():
    standard = calculate(diameter=10, depth=25, material="Mild Steel", tool="Carbide")
    generous_budget = standard.power_required * 2.0

    constrained = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=generous_budget,
    )

    assert constrained.error is None
    assert math.isclose(constrained.spindle_speed_rpm, standard.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(constrained.feed_rate, standard.feed_rate, rel_tol=1e-9)
    assert math.isclose(constrained.machining_time, standard.machining_time, rel_tol=1e-9)
    assert math.isclose(constrained.torque, standard.torque, rel_tol=1e-9)
    assert math.isclose(constrained.power_required, standard.power_required, rel_tol=1e-9)
    # Only mode differs.
    assert constrained.mode is CalculationMode.POWER_CONSTRAINED
    assert standard.mode is CalculationMode.STANDARD


def test_power_constrained_matches_standard_at_exact_equality_boundary():
    """spec.md FR-003, Clarifications 2026-07-11: available_power exactly
    equal to nominal required power (within math.isclose rel_tol=1e-9) is
    treated as "already sufficient" — never triggers FR-002's reduction."""
    standard = calculate(diameter=10, depth=25, material="Mild Steel", tool="Carbide")

    constrained = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=standard.power_required,
    )

    assert constrained.error is None
    assert math.isclose(constrained.spindle_speed_rpm, standard.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(constrained.power_required, standard.power_required, rel_tol=1e-9)
