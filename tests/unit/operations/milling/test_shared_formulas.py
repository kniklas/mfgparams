"""Unit tests for the shared milling formula core (T011).

Covers each of the seven formulas in
``specs/009-milling-calculations/data-model.md`` "Formulas" with
hand-computed reference values, plus boundary cases. All numeric
comparisons use ``math.isclose()`` per Constitution Principle III.
"""

import math

import pytest

from mfgparams.processes.machining.milling._shared import (
    MM3_PER_CM3,
    POWER_SCALE,
    TORQUE_POWER_CONSTANT,
    calculate_milling_metrics,
)
from mfgparams.registry import get_material

# Mild Steel bundled reference data: vc_ref = 25 m/min, kc = 1900 N/mm^2.
_VC_REF = 25.0
_KC = 1900.0


def _metrics(**overrides):
    kwargs = {
        "diameter_mm": 10.0,
        "axial_depth_of_cut_mm": 2.0,
        "radial_engagement_mm": 5.0,
        "feed_per_tooth_mm": 0.05,
        "number_of_teeth": 4,
        "length_of_cut_mm": 100.0,
        "material": get_material("Mild Steel"),
        "cutting_speed_factor": 2.5,
    }
    kwargs.update(overrides)
    return calculate_milling_metrics(**kwargs)


def test_material_fixture_matches_the_values_the_expectations_are_derived_from():
    """Guard the hand-computed expectations against bundled-data drift."""

    material = get_material("Mild Steel")
    assert math.isclose(material.reference_cutting_speed_m_min, _VC_REF)
    assert math.isclose(material.specific_cutting_force_kc, _KC)


def test_spindle_speed_uses_vc_times_factor_over_pi_d():
    # vc = 25 * 2.5 = 62.5 m/min; n = (62.5 * 1000) / (pi * 10)
    expected = (_VC_REF * 2.5 * 1000) / (math.pi * 10.0)

    assert math.isclose(_metrics().spindle_speed_rpm, expected, rel_tol=1e-12)


def test_feed_rate_is_speed_times_feed_per_tooth_times_tooth_count():
    metrics = _metrics()
    expected = metrics.spindle_speed_rpm * 0.05 * 4

    assert math.isclose(metrics.feed_rate_mm_min, expected, rel_tol=1e-12)


def test_material_removal_rate_converts_mm3_to_cm3():
    metrics = _metrics()
    expected = (2.0 * 5.0 * metrics.feed_rate_mm_min) / MM3_PER_CM3

    assert math.isclose(metrics.material_removal_rate_cm3_min, expected, rel_tol=1e-12)
    # Sanity-check the documented unit conversion constant itself.
    assert MM3_PER_CM3 == 1000.0


def test_power_is_net_cutting_power_from_kc():
    metrics = _metrics()
    expected = (2.0 * 5.0 * metrics.feed_rate_mm_min * _KC) / POWER_SCALE

    assert math.isclose(metrics.power_kw, expected, rel_tol=1e-12)


def test_torque_is_derived_from_power_and_spindle_speed():
    metrics = _metrics()
    expected = (metrics.power_kw * TORQUE_POWER_CONSTANT) / metrics.spindle_speed_rpm

    assert math.isclose(metrics.torque_nm, expected, rel_tol=1e-12)


def test_machining_time_is_length_over_feed_rate():
    metrics = _metrics()
    expected = 100.0 / metrics.feed_rate_mm_min

    assert math.isclose(metrics.machining_time_min, expected, rel_tol=1e-12)


def test_power_and_removal_rate_stay_proportional():
    """Q and Pc share the same ``ap * ae * vf`` product, differing only by kc."""

    metrics = _metrics()
    # Pc / Q  ==  kc / (60 * 10^6 / 1000)  ==  kc / 60000
    assert math.isclose(
        metrics.power_kw / metrics.material_removal_rate_cm3_min,
        _KC / (POWER_SCALE / MM3_PER_CM3),
        rel_tol=1e-12,
    )


@pytest.mark.parametrize("teeth", [1, 2, 4, 8])
def test_feed_rate_scales_linearly_with_tooth_count(teeth):
    baseline = _metrics(number_of_teeth=1)
    scaled = _metrics(number_of_teeth=teeth)

    assert math.isclose(scaled.feed_rate_mm_min, baseline.feed_rate_mm_min * teeth, rel_tol=1e-12)
    # More teeth -> proportionally faster -> proportionally shorter time.
    assert math.isclose(
        scaled.machining_time_min, baseline.machining_time_min / teeth, rel_tol=1e-12
    )


def test_torque_scales_with_tooth_count_via_power_at_fixed_spindle_speed():
    """Mc = Pc * 9550 / n, and both Pc and n scale together with vf.

    Torque is *not* independent of tooth count here — the docstring below
    documents why it doubles even though spindle speed (n) does not: at a
    fixed chip load, doubling the tooth count doubles the feed rate and
    therefore the cutting power, which flows directly into torque.
    """

    four = _metrics(number_of_teeth=4)
    eight = _metrics(number_of_teeth=8)

    # Doubling zn doubles vf, hence doubles Pc, while n is unchanged.
    assert math.isclose(eight.torque_nm, four.torque_nm * 2, rel_tol=1e-12)
    assert math.isclose(eight.spindle_speed_rpm, four.spindle_speed_rpm, rel_tol=1e-12)


def test_full_slot_engagement_at_the_diameter_boundary_is_accepted():
    """ae == D is the FR-009 upper bound and must compute normally."""

    metrics = _metrics(radial_engagement_mm=10.0)

    assert metrics.material_removal_rate_cm3_min > 0
    assert math.isfinite(metrics.power_kw)


@pytest.mark.parametrize("diameter", [0.1, 1.0, 200.0])
def test_all_outputs_are_finite_and_positive_across_the_diameter_range(diameter):
    metrics = _metrics(diameter_mm=diameter, radial_engagement_mm=diameter / 2)

    for value in (
        metrics.spindle_speed_rpm,
        metrics.feed_rate_mm_min,
        metrics.material_removal_rate_cm3_min,
        metrics.machining_time_min,
        metrics.torque_nm,
        metrics.power_kw,
    ):
        assert math.isfinite(value)
        assert value > 0
