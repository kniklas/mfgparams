"""Unit tests for calculate_turning_metrics_at_rpm() and the power-scaling
helper, mirroring
tests/unit/processes/machining/drilling/test_formulas_at_rpm.py.

Covers: nominal-equals-standard case, boundary case where available power
exactly equals nominal power (asserting the no-reduction/no-op path,
math.isclose(rel_tol=1e-9)), reduced-RPM case, and zero/negative available
power. Added per Copilot review finding: formulas.py previously had no
direct unit tests.
"""

import math

from mfgparams.processes.machining.turning.formulas import (
    calculate_turning_metrics,
    calculate_turning_metrics_at_rpm,
    calculate_turning_power_constrained_metrics,
)
from mfgparams.processes.machining.turning.tools import get_turning_tool
from mfgparams.registry import get_material


def test_at_rpm_matches_standard_when_given_the_nominal_rpm():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_metrics(40, 2, 100, material, tool)
    at_rpm = calculate_turning_metrics_at_rpm(40, 2, 100, material, tool, nominal.spindle_speed_rpm)

    assert math.isclose(at_rpm.feed_rate_mm_min, nominal.feed_rate_mm_min, rel_tol=1e-9)
    assert math.isclose(at_rpm.feed_per_rev_mm, nominal.feed_per_rev_mm, rel_tol=1e-9)
    assert math.isclose(at_rpm.machining_time_min, nominal.machining_time_min, rel_tol=1e-9)
    assert math.isclose(at_rpm.cutting_force_n, nominal.cutting_force_n, rel_tol=1e-9)
    assert math.isclose(at_rpm.torque_nm, nominal.torque_nm, rel_tol=1e-9)
    assert math.isclose(at_rpm.power_kw, nominal.power_kw, rel_tol=1e-9)


def test_at_rpm_feed_per_rev_mm_override_replaces_material_tool_derived_value():
    """specs/020-turning-feed-per-rotation research.md #2: an explicitly
    supplied feed_per_rev_mm is used directly instead of being derived from
    material.reference_feed_per_rev_mm * tool.feed_factor, and every
    dependent metric (feed rate, machining time, cutting force, torque,
    power) is recomputed from it."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_metrics_at_rpm(40, 2, 100, material, tool, 500)
    overridden = calculate_turning_metrics_at_rpm(
        40, 2, 100, material, tool, 500, feed_per_rev_mm=0.5
    )

    assert not math.isclose(nominal.feed_per_rev_mm, 0.5, rel_tol=1e-9)
    assert overridden.feed_per_rev_mm == 0.5
    assert overridden.spindle_speed_rpm == 500
    assert math.isclose(overridden.feed_rate_mm_min, 500 * 0.5, rel_tol=1e-9)
    assert math.isclose(overridden.cutting_force_n, 1900.0 * 2 * 0.5, rel_tol=1e-9)
    assert not math.isclose(overridden.cutting_force_n, nominal.cutting_force_n, rel_tol=1e-9)


def test_at_rpm_cutting_force_and_torque_independent_of_spindle_speed():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    low = calculate_turning_metrics_at_rpm(40, 2, 100, material, tool, 100)
    high = calculate_turning_metrics_at_rpm(40, 2, 100, material, tool, 5000)

    # Cutting force and torque depend only on diameter/depth-of-cut/
    # material/tool, not spindle speed (research.md #1).
    assert math.isclose(low.cutting_force_n, high.cutting_force_n, rel_tol=1e-9)
    assert math.isclose(low.torque_nm, high.torque_nm, rel_tol=1e-9)
    assert low.power_kw < high.power_kw


def test_power_constrained_reduces_spindle_speed_when_budget_below_nominal():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_metrics(40, 2, 100, material, tool)
    budget_kw = nominal.power_kw * 0.5

    adjusted = calculate_turning_power_constrained_metrics(40, 2, 100, material, tool, budget_kw)

    assert adjusted.spindle_speed_rpm < nominal.spindle_speed_rpm
    assert math.isclose(adjusted.power_kw, budget_kw, rel_tol=1e-9)
    # Cutting force/torque are unchanged — they do not depend on spindle speed.
    assert math.isclose(adjusted.cutting_force_n, nominal.cutting_force_n, rel_tol=1e-9)
    assert math.isclose(adjusted.torque_nm, nominal.torque_nm, rel_tol=1e-9)


def test_power_constrained_no_op_when_budget_comfortably_exceeds_nominal():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_metrics(40, 2, 100, material, tool)
    budget_kw = nominal.power_kw * 2.0

    result = calculate_turning_power_constrained_metrics(40, 2, 100, material, tool, budget_kw)

    assert math.isclose(result.spindle_speed_rpm, nominal.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(result.power_kw, nominal.power_kw, rel_tol=1e-9)


def test_power_constrained_no_op_at_exact_equality_boundary():
    """An available_power exactly equal to nominal power (within
    math.isclose's default rel_tol=1e-9) is "sufficient" — never triggers
    the reduction (mirrors drilling's spec.md Clarifications 2026-07-11)."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_metrics(40, 2, 100, material, tool)

    result = calculate_turning_power_constrained_metrics(
        40, 2, 100, material, tool, nominal.power_kw
    )

    assert math.isclose(result.spindle_speed_rpm, nominal.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(result.feed_rate_mm_min, nominal.feed_rate_mm_min, rel_tol=1e-9)
    assert math.isclose(result.machining_time_min, nominal.machining_time_min, rel_tol=1e-9)


def test_power_constrained_zero_budget_underflows_without_crashing():
    """calculate_turning_power_constrained_metrics() does not itself
    validate available_power_kw (per its docstring): a zero budget
    produces a zero adjusted spindle speed, which underflows
    feed_rate_mm_min to exactly 0.0. Unlike drilling's identical formula
    (which still raises ZeroDivisionError here, matching its own
    now-superseded test), turning's calculate_turning_metrics_at_rpm
    guards this division explicitly (Copilot review finding on PR #100,
    mirroring milling's identical guard): machining_time_min becomes
    inf rather than raising. This is still why
    processes/machining/turning's calculate_turning() entry point MUST
    reject non-positive budgets as INFEASIBLE_POWER_BUDGET before ever
    reaching this helper via the public API — the orchestration layer's
    own _reject_if_invalid() is what actually catches the resulting inf
    — but the formula layer no longer crashes outright either."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    result = calculate_turning_power_constrained_metrics(40, 2, 100, material, tool, 0.0)

    assert result.spindle_speed_rpm == 0.0
    assert result.machining_time_min == float("inf")


def test_at_rpm_subnormal_spindle_speed_underflows_feed_rate_without_crashing():
    """A positive-subnormal spindle_speed_rpm (e.g. FIXED_RPM's
    target_rpm=5e-324, which validate_target_rpm() accepts — no lower
    bound beyond positivity) can make feed_rate_mm_min underflow to
    exactly 0.0. machining_time_min must not raise ZeroDivisionError for
    this — inf is the mathematically correct value at a zero feed rate,
    and is what the orchestration layer's finiteness check
    (__init__.py's _reject_if_invalid()) is designed to catch."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    metrics = calculate_turning_metrics_at_rpm(40, 2, 100, material, tool, 5e-324)

    assert metrics.feed_rate_mm_min == 0.0
    assert metrics.machining_time_min == float("inf")


def test_at_rpm_arbitrary_precision_int_spindle_speed_does_not_overflow():
    """An int too large to convert to a C double (e.g. FIXED_RPM's
    target_rpm=10**1000, which validate_target_rpm() now accepts per its
    own overflow fix) must not raise OverflowError from the first
    multiplication — inf is the mathematically sensible limit, caught by
    the orchestration layer's finiteness check afterwards."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    metrics = calculate_turning_metrics_at_rpm(40, 2, 100, material, tool, 10**1000)

    assert metrics.spindle_speed_rpm == float("inf")
    assert metrics.feed_rate_mm_min == float("inf")


def test_power_constrained_tiny_budget_yields_tiny_positive_rpm():
    """No floor is imposed on the adjusted spindle speed; an extremely
    small but positive budget still yields a valid, positive result rather
    than being rejected."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    nominal = calculate_turning_metrics(40, 2, 100, material, tool)
    tiny_budget_kw = nominal.power_kw * 1e-6

    result = calculate_turning_power_constrained_metrics(40, 2, 100, material, tool, tiny_budget_kw)

    assert result.spindle_speed_rpm > 0
    assert math.isclose(result.power_kw, tiny_budget_kw, rel_tol=1e-9)
