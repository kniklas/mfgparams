"""Unit tests for calculate_turning_power_and_feed_constrained_metrics()
(specs/021-turning-combined-constraints FR-003/FR-004/FR-005, research.md #3).

Mirrors tests/unit/processes/machining/turning/test_formulas_at_rpm.py's
existing POWER_CONSTRAINED test coverage, seeded at a caller-supplied feed
instead of the material/tool-derived one.
"""

import math

from mfgparams.processes.machining.turning.formulas import (
    calculate_turning_feed_rate_constrained_metrics,
    calculate_turning_power_and_feed_constrained_metrics,
)
from mfgparams.processes.machining.turning.tools import get_turning_tool
from mfgparams.registry import get_material


def test_feed_per_rev_mm_echoes_the_supplied_value():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    result = calculate_turning_power_and_feed_constrained_metrics(
        40, 2, 100, material, tool, 10.0, 0.3
    )

    assert result.feed_per_rev_mm == 0.3


def test_no_op_when_nominal_at_supplied_feed_already_fits_budget():
    """The "nominal" point here is the cutting-speed-derived spindle speed
    at the *supplied* feed (not the material/tool-derived one) -- mirrors
    calculate_turning_feed_rate_constrained_metrics() exactly."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_feed_rate_constrained_metrics(40, 2, 100, material, tool, 0.3)
    budget_kw = nominal.power_kw * 2.0

    result = calculate_turning_power_and_feed_constrained_metrics(
        40, 2, 100, material, tool, budget_kw, 0.3
    )

    assert math.isclose(result.spindle_speed_rpm, nominal.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(result.power_kw, nominal.power_kw, rel_tol=1e-9)
    assert result.feed_per_rev_mm == 0.3


def test_no_op_at_exact_equality_boundary():
    """An available_power exactly equal to nominal power (within
    math.isclose's default rel_tol=1e-9) is "sufficient" -- never triggers
    the reduction, mirroring POWER_CONSTRAINED's identical boundary."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_feed_rate_constrained_metrics(40, 2, 100, material, tool, 0.3)

    result = calculate_turning_power_and_feed_constrained_metrics(
        40, 2, 100, material, tool, nominal.power_kw, 0.3
    )

    assert math.isclose(result.spindle_speed_rpm, nominal.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(result.machining_time_min, nominal.machining_time_min, rel_tol=1e-9)


def test_reduces_spindle_speed_when_budget_below_nominal():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_feed_rate_constrained_metrics(40, 2, 100, material, tool, 0.3)
    budget_kw = nominal.power_kw * 0.5

    result = calculate_turning_power_and_feed_constrained_metrics(
        40, 2, 100, material, tool, budget_kw, 0.3
    )

    assert result.spindle_speed_rpm < nominal.spindle_speed_rpm
    assert math.isclose(result.power_kw, budget_kw, rel_tol=1e-9)
    assert result.feed_per_rev_mm == 0.3
    # Cutting force/torque are unchanged -- they do not depend on spindle
    # speed, only on the (fixed) feed and depth of cut.
    assert math.isclose(result.cutting_force_n, nominal.cutting_force_n, rel_tol=1e-9)
    assert math.isclose(result.torque_nm, nominal.torque_nm, rel_tol=1e-9)


def test_zero_budget_underflows_without_crashing():
    """Mirrors POWER_CONSTRAINED's identical zero-budget formula-layer
    behavior: this function does not itself validate available_power_kw --
    the orchestration layer rejects non-positive budgets as
    INFEASIBLE_POWER_BUDGET before ever reaching this helper via the
    public API."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    result = calculate_turning_power_and_feed_constrained_metrics(
        40, 2, 100, material, tool, 0.0, 0.3
    )

    assert result.spindle_speed_rpm == 0.0
    assert result.machining_time_min == float("inf")


def test_subnormal_feed_underflows_without_crashing():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    result = calculate_turning_power_and_feed_constrained_metrics(
        40, 2, 100, material, tool, 10.0, 5e-320
    )

    assert result.feed_per_rev_mm == 5e-320
    assert math.isfinite(result.machining_time_min) or result.machining_time_min == float("inf")


def test_arbitrary_precision_int_budget_does_not_overflow():
    """Mirrors POWER_CONSTRAINED's identical arbitrary-precision-int
    coverage -- an oversized budget behaves as an effectively-unlimited
    one rather than raising OverflowError."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_feed_rate_constrained_metrics(40, 2, 100, material, tool, 0.3)

    result = calculate_turning_power_and_feed_constrained_metrics(
        40, 2, 100, material, tool, 10**1000, 0.3
    )

    assert math.isclose(result.spindle_speed_rpm, nominal.spindle_speed_rpm, rel_tol=1e-9)
