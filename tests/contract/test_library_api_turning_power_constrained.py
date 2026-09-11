"""Contract test: turning power-constrained mode success response shape
(specs/019-turning-calculations).

Mirrors tests/contract/test_library_api_milling_power_constrained.py.
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


def test_turning_power_constrained_success_response_shape():
    nominal = calculate_turning(**_ARGS)
    budget_kw = nominal.power_required * 0.5

    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=budget_kw,
    )

    assert result.error is None
    assert result.mode is CalculationMode.POWER_CONSTRAINED
    assert result.unit_system is UnitSystem.METRIC
    assert result.spindle_speed_rpm < nominal.spindle_speed_rpm
    assert math.isclose(result.torque, nominal.torque, rel_tol=1e-9)
    assert math.isclose(result.cutting_force, nominal.cutting_force, rel_tol=1e-9)
    assert math.isclose(result.power_required, budget_kw, rel_tol=1e-9)
    assert result.feasibility_warning is None


def test_turning_power_constrained_no_reduction_needed_matches_standard_mode():
    """spec.md: if available power is already sufficient at the nominal
    spindle speed, the result equals the standard-mode result except mode."""

    nominal = calculate_turning(**_ARGS)
    generous_budget = nominal.power_required * 2

    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=generous_budget,
    )

    assert result.error is None
    assert math.isclose(result.spindle_speed_rpm, nominal.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(result.cutting_force, nominal.cutting_force, rel_tol=1e-9)
