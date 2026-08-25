"""Integration test: fixed-RPM mode with optional advisory available_power
(T019; FR-008).

An exceeded power budget sets ``feasibility_warning`` without altering
``target_rpm``/``spindle_speed_rpm``; a sufficient budget leaves no warning.
"""

from mfgparams import CalculationMode, calculate


def test_exceeded_power_sets_feasibility_warning_but_keeps_target_rpm():
    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=2000,  # deliberately high RPM -> large power requirement
        available_power=0.01,  # deliberately low available power
    )

    assert result.error is None
    assert result.mode is CalculationMode.FIXED_RPM
    assert result.spindle_speed_rpm == 2000
    assert result.feasibility_warning is not None


def test_sufficient_power_produces_no_feasibility_warning():
    # First, discover the actual power requirement at this target RPM.
    baseline = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=500,
    )
    assert baseline.error is None

    result = calculate(
        diameter=10,
        depth=25,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.FIXED_RPM,
        target_rpm=500,
        available_power=baseline.power_required * 2,  # ample surplus
    )

    assert result.error is None
    assert result.spindle_speed_rpm == 500
    assert result.feasibility_warning is None
