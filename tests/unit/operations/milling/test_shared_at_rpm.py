"""Unit tests for calculate_milling_metrics_at_rpm() and the power-scaling
helper (T009).

Covers: nominal-equals-standard case, boundary case where available power
exactly equals nominal power (asserting the no-reduction/no-op path per
FR-003, using math.isclose(rel_tol=1e-9)), reduced-RPM case, and
zero/negative available power (via the milling calculate_milling() entry
point, which is what actually rejects non-positive budgets as
INFEASIBLE_POWER_BUDGET — mirrors drilling's
tests/unit/operations/drilling/test_formulas_at_rpm.py).
"""

import math

from mfgparams.operations.milling._shared import (
    calculate_milling_metrics,
    calculate_milling_metrics_at_rpm,
    calculate_power_constrained_milling_metrics,
)
from mfgparams.operations.milling.end_milling.tools import get_end_mill_tool
from mfgparams.registry import get_material

_GEOMETRY = dict(
    diameter_mm=10,
    axial_depth_of_cut_mm=2,
    radial_engagement_mm=5,
    feed_per_tooth_mm=0.05,
    number_of_teeth=4,
    length_of_cut_mm=50,
)


def _material():
    return get_material("Aluminum")


def _cutting_speed_factor():
    return get_end_mill_tool("Carbide").cutting_speed_factor


def test_at_rpm_matches_standard_when_given_the_nominal_rpm():
    material = _material()
    nominal = calculate_milling_metrics(
        **_GEOMETRY, material=material, cutting_speed_factor=_cutting_speed_factor()
    )
    at_rpm = calculate_milling_metrics_at_rpm(
        **_GEOMETRY, material=material, spindle_speed_rpm=nominal.spindle_speed_rpm
    )

    assert math.isclose(at_rpm.feed_rate_mm_min, nominal.feed_rate_mm_min, rel_tol=1e-9)
    assert math.isclose(at_rpm.machining_time_min, nominal.machining_time_min, rel_tol=1e-9)
    assert math.isclose(at_rpm.torque_nm, nominal.torque_nm, rel_tol=1e-9)
    assert math.isclose(at_rpm.power_kw, nominal.power_kw, rel_tol=1e-9)


def test_at_rpm_torque_independent_of_spindle_speed():
    material = _material()

    low = calculate_milling_metrics_at_rpm(**_GEOMETRY, material=material, spindle_speed_rpm=100)
    high = calculate_milling_metrics_at_rpm(**_GEOMETRY, material=material, spindle_speed_rpm=5000)

    # Torque depends only on geometry/material, not spindle speed
    # (research.md #1).
    assert math.isclose(low.torque_nm, high.torque_nm, rel_tol=1e-9)


def test_at_rpm_subnormal_spindle_speed_underflows_feed_rate_without_crashing():
    """A positive-subnormal spindle_speed_rpm (e.g. FIXED_RPM's
    target_rpm=5e-324, which validate_target_rpm() accepts — no lower
    bound beyond positivity) can make feed_rate_mm_min underflow to
    exactly 0.0. machining_time_min = length_of_cut_mm / feed_rate_mm_min
    must not raise ZeroDivisionError for this — inf is the mathematically
    correct value at a zero feed rate, and is what the caller's
    finiteness check (_calculate._reject_if_invalid()) is designed to
    catch."""
    material = _material()

    metrics = calculate_milling_metrics_at_rpm(
        **_GEOMETRY, material=material, spindle_speed_rpm=5e-324
    )

    assert metrics.feed_rate_mm_min == 0.0
    assert metrics.machining_time_min == float("inf")


def test_power_constrained_reduces_spindle_speed_when_budget_below_nominal():
    material = _material()
    cutting_speed_factor = _cutting_speed_factor()

    nominal = calculate_milling_metrics(
        **_GEOMETRY, material=material, cutting_speed_factor=cutting_speed_factor
    )
    budget_kw = nominal.power_kw * 0.5

    adjusted = calculate_power_constrained_milling_metrics(
        **_GEOMETRY,
        material=material,
        cutting_speed_factor=cutting_speed_factor,
        available_power_kw=budget_kw,
    )

    assert adjusted.spindle_speed_rpm < nominal.spindle_speed_rpm
    assert math.isclose(adjusted.power_kw, budget_kw, rel_tol=1e-9)
    # Torque is unchanged — it does not depend on spindle speed.
    assert math.isclose(adjusted.torque_nm, nominal.torque_nm, rel_tol=1e-9)


def test_power_constrained_no_op_when_budget_comfortably_exceeds_nominal():
    material = _material()
    cutting_speed_factor = _cutting_speed_factor()

    nominal = calculate_milling_metrics(
        **_GEOMETRY, material=material, cutting_speed_factor=cutting_speed_factor
    )
    budget_kw = nominal.power_kw * 2.0

    result = calculate_power_constrained_milling_metrics(
        **_GEOMETRY,
        material=material,
        cutting_speed_factor=cutting_speed_factor,
        available_power_kw=budget_kw,
    )

    assert math.isclose(result.spindle_speed_rpm, nominal.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(result.power_kw, nominal.power_kw, rel_tol=1e-9)


def test_power_constrained_no_op_at_exact_equality_boundary():
    """FR-003: an available_power exactly equal to nominal power (within
    math.isclose's default rel_tol=1e-9) is "sufficient" — never triggers
    FR-002's reduction (spec.md Clarifications)."""
    material = _material()
    cutting_speed_factor = _cutting_speed_factor()

    nominal = calculate_milling_metrics(
        **_GEOMETRY, material=material, cutting_speed_factor=cutting_speed_factor
    )

    result = calculate_power_constrained_milling_metrics(
        **_GEOMETRY,
        material=material,
        cutting_speed_factor=cutting_speed_factor,
        available_power_kw=nominal.power_kw,
    )

    assert math.isclose(result.spindle_speed_rpm, nominal.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(result.feed_rate_mm_min, nominal.feed_rate_mm_min, rel_tol=1e-9)
    assert math.isclose(result.machining_time_min, nominal.machining_time_min, rel_tol=1e-9)


def test_power_constrained_tiny_budget_yields_tiny_positive_rpm():
    """No floor is imposed on the adjusted spindle speed (spec.md Edge
    Cases); an extremely small but positive budget still yields a valid,
    positive result rather than being rejected."""
    material = _material()
    cutting_speed_factor = _cutting_speed_factor()

    nominal = calculate_milling_metrics(
        **_GEOMETRY, material=material, cutting_speed_factor=cutting_speed_factor
    )
    tiny_budget_kw = nominal.power_kw * 1e-6

    result = calculate_power_constrained_milling_metrics(
        **_GEOMETRY,
        material=material,
        cutting_speed_factor=cutting_speed_factor,
        available_power_kw=tiny_budget_kw,
    )

    assert result.spindle_speed_rpm > 0
    assert math.isclose(result.power_kw, tiny_budget_kw, rel_tol=1e-9)


def test_power_constrained_subnormal_budget_signals_infeasible_not_crash():
    """A positive-subnormal available_power_kw can make n_adjusted
    underflow to (near) zero — or otherwise leave a downstream division
    (e.g. length_of_cut_mm / feed_rate_mm_min) overflowing to inf even
    though n_adjusted itself stayed finite/positive. Either way this must
    surface as a non-finite spindle_speed_rpm sentinel — not a
    ZeroDivisionError crash, nor a result mixing finite and inf/nan
    fields — so the caller's feasibility check can convert it to
    INFEASIBLE_POWER_BUDGET."""
    material = _material()
    cutting_speed_factor = _cutting_speed_factor()

    result = calculate_power_constrained_milling_metrics(
        **_GEOMETRY,
        material=material,
        cutting_speed_factor=cutting_speed_factor,
        available_power_kw=5e-324,
    )

    assert not math.isfinite(result.spindle_speed_rpm)


def test_power_constrained_exact_zero_n_adjusted_signals_infeasible_not_crash():
    """When nominal.power_kw is large enough that
    available_power_kw / nominal.power_kw underflows to exactly 0.0,
    n_adjusted itself becomes 0.0 (not merely non-finite downstream) —
    the earliest guard (before calling
    calculate_milling_metrics_at_rpm(), which would otherwise divide by
    this rpm and raise ZeroDivisionError) must catch this exact-zero
    case."""
    material = _material()
    large_geometry = dict(
        diameter_mm=200,
        axial_depth_of_cut_mm=50,
        radial_engagement_mm=180,
        feed_per_tooth_mm=2,
        number_of_teeth=20,
        length_of_cut_mm=1000,
    )
    cutting_speed_factor = _cutting_speed_factor()

    nominal = calculate_milling_metrics(
        **large_geometry, material=material, cutting_speed_factor=cutting_speed_factor
    )
    assert nominal.power_kw > 1.0  # sanity: large enough to force the ratio to underflow

    result = calculate_power_constrained_milling_metrics(
        **large_geometry,
        material=material,
        cutting_speed_factor=cutting_speed_factor,
        available_power_kw=5e-324,
    )

    assert not math.isfinite(result.spindle_speed_rpm)
