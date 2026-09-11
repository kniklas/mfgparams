"""Integration test: turning fixed-RPM mode with optional advisory
available_power (specs/019-turning-calculations FR-014).

An exceeded power budget sets ``feasibility_warning`` without altering
``target_rpm``/``spindle_speed_rpm``; a sufficient budget leaves no
warning. Mirrors tests/integration/test_milling_fixed_rpm_feasibility.py.
"""

from mfgparams import CalculationMode, calculate_turning

_ARGS = dict(
    diameter=40,
    depth_of_cut=2,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)


def test_exceeded_power_sets_feasibility_warning_but_keeps_target_rpm():
    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=5000,  # deliberately high RPM -> large power requirement
        available_power=0.01,  # deliberately low available power
    )

    assert result.error is None
    assert result.mode is CalculationMode.FIXED_RPM
    assert result.spindle_speed_rpm == 5000
    assert result.feasibility_warning is not None


def test_sufficient_power_produces_no_feasibility_warning():
    baseline = calculate_turning(**_ARGS, mode=CalculationMode.FIXED_RPM, target_rpm=900)
    assert baseline.error is None

    result = calculate_turning(
        **_ARGS,
        mode=CalculationMode.FIXED_RPM,
        target_rpm=900,
        available_power=baseline.power_required * 2,  # ample surplus
    )

    assert result.error is None
    assert result.spindle_speed_rpm == 900
    assert result.feasibility_warning is None
