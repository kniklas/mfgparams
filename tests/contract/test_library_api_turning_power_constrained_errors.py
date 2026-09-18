"""Contract test: turning power-constrained mode INFEASIBLE_POWER_BUDGET /
MODE_CONFLICT errors (specs/019-turning-calculations).

Mirrors tests/contract/test_library_api_milling_power_constrained_errors.py.
"""

from mfgparams import CalculationMode, calculate_turning

_ARGS = dict(
    diameter=40,
    depth_of_cut=2,
    length_of_cut=100,
    material="Mild Steel",
    tool="Carbide",
)


def test_zero_available_power_is_infeasible():
    result = calculate_turning(**_ARGS, mode=CalculationMode.POWER_CONSTRAINED, available_power=0)
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.cutting_force is None


def test_negative_available_power_is_infeasible():
    result = calculate_turning(
        **_ARGS, mode=CalculationMode.POWER_CONSTRAINED, available_power=-1.0
    )
    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
    assert result.feed_rate is None
    assert result.machining_time is None
    assert result.torque is None
    assert result.power_required is None
    assert result.cutting_force is None
    assert result.mode is CalculationMode.POWER_CONSTRAINED


def test_missing_available_power_is_mode_conflict():
    result = calculate_turning(**_ARGS, mode=CalculationMode.POWER_CONSTRAINED)
    assert result.error is not None
    assert result.error.code == "MODE_CONFLICT"


def test_infeasible_error_does_not_raise():
    """FR-016: never raises, always returns a structured CalculationResult."""
    result = calculate_turning(
        **_ARGS, mode=CalculationMode.POWER_CONSTRAINED, available_power=-100.0
    )
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"


def test_arbitrary_precision_int_budget_with_subnormal_geometry_does_not_raise():
    """specs/021-turning-combined-constraints Copilot review finding on PR
    #102: an arbitrary-precision available_power (e.g. 10**1000, which
    _is_positive_finite_number() accepts) combined with subnormal geometry
    can drive nominal.power_kw to nan (0 torque * inf spindle speed),
    which fails the `<=` short-circuit and falls through to
    math.isclose() -- whose CPython implementation converts both
    arguments to C doubles unconditionally, previously raising
    OverflowError instead of the documented never-raises structured
    result. Pre-existing latent bug, not introduced by this PR, but only
    found once specs/021-turning-combined-constraints's
    _scale_metrics_to_power_budget() extraction made it easy to test the
    shared helper directly."""

    result = calculate_turning(
        diameter=1e-305,
        depth_of_cut=1e-310,
        length_of_cut=1,
        material="Mild Steel",
        tool="Carbide",
        mode=CalculationMode.POWER_CONSTRAINED,
        available_power=10**1000,
    )

    assert result.error is not None
    assert result.error.code == "INFEASIBLE_POWER_BUDGET"
    assert result.spindle_speed_rpm is None
