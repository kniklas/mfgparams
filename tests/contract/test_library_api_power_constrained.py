"""Contract test: power-constrained mode success response shape (T010).

Per contracts/library-api-delta.md.
"""

import math

from mfgparams import CalculationMode, UnitSystem, calculate


def test_power_constrained_success_response_shape():
    nominal = calculate(diameter=10, depth=25, material="Mild Steel", tool="Carbide")
    budget_kw = nominal.power_required * 0.5

    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=budget_kw,
    )

    assert result.error is None
    assert result.mode is CalculationMode.POWER_CONSTRAINED
    assert result.unit_system is UnitSystem.METRIC
    # Spindle speed is reduced from the standard (unconstrained) result.
    assert result.spindle_speed_rpm < nominal.spindle_speed_rpm
    # Torque is unchanged — it does not depend on spindle speed (research.md #1).
    assert math.isclose(result.torque, nominal.torque, rel_tol=1e-9)
    # Required power equals the supplied budget (within float tolerance).
    assert math.isclose(result.power_required, budget_kw, rel_tol=1e-9)
    assert result.feasibility_warning is None


def test_power_constrained_success_imperial():
    result = calculate(
        diameter=10 / 25.4,
        depth=25 / 25.4,
        material="Mild Steel",
        tool="Carbide",
        unit_system=UnitSystem.IMPERIAL,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=0.1,
    )
    assert result.error is None
    assert result.mode is CalculationMode.POWER_CONSTRAINED
    assert result.unit_system is UnitSystem.IMPERIAL
    assert math.isclose(result.power_required, 0.1, rel_tol=1e-9)
