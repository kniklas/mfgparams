"""Contract test: power-constrained mode success response shape (T011).

Per contracts/library-api-milling-modes-delta.md; mirrors
tests/contract/test_library_api_power_constrained.py (drilling) for both
milling sub-operations.
"""

import math

from mfgparams import (
    CalculationMode,
    UnitSystem,
    calculate_end_milling,
    calculate_face_milling,
)

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


def test_end_milling_power_constrained_success_response_shape():
    nominal = calculate_end_milling(**_END_MILLING_ARGS)
    budget_kw = nominal.power_required * 0.5

    result = calculate_end_milling(
        **_END_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=budget_kw,
    )

    assert result.error is None
    assert result.mode is CalculationMode.POWER_CONSTRAINED
    assert result.unit_system is UnitSystem.METRIC
    assert result.spindle_speed_rpm < nominal.spindle_speed_rpm
    assert math.isclose(result.torque, nominal.torque, rel_tol=1e-9)
    assert math.isclose(result.power_required, budget_kw, rel_tol=1e-9)
    assert result.feasibility_warning is None


def test_face_milling_power_constrained_success_response_shape():
    nominal = calculate_face_milling(**_FACE_MILLING_ARGS)
    budget_kw = nominal.power_required * 0.5

    result = calculate_face_milling(
        **_FACE_MILLING_ARGS,
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=budget_kw,
    )

    assert result.error is None
    assert result.mode is CalculationMode.POWER_CONSTRAINED
    assert result.unit_system is UnitSystem.METRIC
    assert result.spindle_speed_rpm < nominal.spindle_speed_rpm
    assert math.isclose(result.torque, nominal.torque, rel_tol=1e-9)
    assert math.isclose(result.power_required, budget_kw, rel_tol=1e-9)
    assert result.feasibility_warning is None
