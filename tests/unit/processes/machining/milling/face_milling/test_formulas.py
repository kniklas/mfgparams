"""Unit tests for the face-milling formulas wrapper (T031).

The wrapper delegates to the shared core, so these tests pin the *mapping*
it is responsible for — that the width of cut becomes the shared core's radial
engagement — plus nominal and boundary values. Comparisons use
``math.isclose()`` per Constitution Principle III.
"""

import math

import pytest

from mfgparams.processes.machining.milling._shared import calculate_milling_metrics
from mfgparams.processes.machining.milling.face_milling.formulas import (
    FaceMillingMetrics,
    calculate_face_milling_metrics,
)
from mfgparams.processes.machining.milling.face_milling.tools import get_face_mill_tool
from mfgparams.registry import get_material

_MATERIAL = "Mild Steel"
_TOOL = "Carbide"


def _call(**overrides):
    kwargs = {
        "diameter_mm": 63.0,
        "axial_depth_of_cut_mm": 2.0,
        "width_of_cut_mm": 40.0,
        "feed_per_tooth_mm": 0.1,
        "number_of_teeth": 5,
        "length_of_cut_mm": 200.0,
        "material": get_material(_MATERIAL),
        "tool": get_face_mill_tool(_TOOL),
    }
    kwargs.update(overrides)
    return calculate_face_milling_metrics(**kwargs)


def test_returns_the_sub_operations_own_metrics_type():
    """Each sub-operation re-wraps the shared result in its own type (research.md #2)."""

    assert isinstance(_call(), FaceMillingMetrics)


def test_nominal_values_match_hand_computed_expectations():
    material = get_material(_MATERIAL)
    factor = get_face_mill_tool(_TOOL).cutting_speed_factor
    metrics = _call()

    expected_rpm = (material.reference_cutting_speed_m_min * factor * 1000) / (math.pi * 63.0)
    expected_feed = expected_rpm * 0.1 * 5
    expected_mrr = (2.0 * 40.0 * expected_feed) / 1000.0
    expected_power = (2.0 * 40.0 * expected_feed * material.specific_cutting_force_kc) / (
        60.0 * 10**6
    )

    assert math.isclose(metrics.spindle_speed_rpm, expected_rpm, rel_tol=1e-12)
    assert math.isclose(metrics.feed_rate_mm_min, expected_feed, rel_tol=1e-12)
    assert math.isclose(metrics.material_removal_rate_cm3_min, expected_mrr, rel_tol=1e-12)
    assert math.isclose(metrics.power_kw, expected_power, rel_tol=1e-12)
    assert math.isclose(metrics.torque_nm, (expected_power * 9550.0) / expected_rpm, rel_tol=1e-12)
    assert math.isclose(metrics.machining_time_min, 200.0 / expected_feed, rel_tol=1e-12)


def test_width_of_cut_mm_is_passed_through_as_the_radial_engagement():
    """This mapping is the wrapper's entire reason to exist (FR-014)."""

    metrics = _call()
    shared = calculate_milling_metrics(
        diameter_mm=63.0,
        axial_depth_of_cut_mm=2.0,
        radial_engagement_mm=40.0,
        feed_per_tooth_mm=0.1,
        number_of_teeth=5,
        length_of_cut_mm=200.0,
        material=get_material(_MATERIAL),
        cutting_speed_factor=get_face_mill_tool(_TOOL).cutting_speed_factor,
    )

    assert math.isclose(metrics.material_removal_rate_cm3_min, shared.material_removal_rate_cm3_min)
    assert math.isclose(metrics.power_kw, shared.power_kw)
    assert math.isclose(metrics.torque_nm, shared.torque_nm)


def test_removal_rate_scales_linearly_with_width_of_cut_mm():
    half = _call(**{"width_of_cut_mm": 40.0 / 2})
    full = _call()

    assert math.isclose(
        full.material_removal_rate_cm3_min, half.material_removal_rate_cm3_min * 2, rel_tol=1e-12
    )


def test_engagement_equal_to_the_diameter_is_a_valid_boundary():
    metrics = _call(**{"width_of_cut_mm": 63.0})

    assert metrics.material_removal_rate_cm3_min > 0
    assert math.isfinite(metrics.power_kw)


@pytest.mark.parametrize("ap", [0.1, 1.0, 5.0, 50.0])
def test_all_outputs_stay_finite_across_the_axial_depth_range(ap):
    metrics = _call(axial_depth_of_cut_mm=ap)

    assert all(
        math.isfinite(v) and v > 0
        for v in (
            metrics.spindle_speed_rpm,
            metrics.feed_rate_mm_min,
            metrics.material_removal_rate_cm3_min,
            metrics.machining_time_min,
            metrics.torque_nm,
            metrics.power_kw,
        )
    )


def test_full_symmetric_engagement_is_assumed_with_no_chip_thinning():
    """spec.md Assumptions: average chip thickness == feed per tooth.

    A chip-thinning correction would scale the effective feed by a factor
    depending on ae/D, making a narrow-engagement pass differ from the
    plain ``vf = n * fz * zn`` result. Asserting that a narrow pass still
    matches the uncorrected formula exactly pins the assumption down.
    """

    narrow = _call(width_of_cut_mm=1.0)
    wide = _call(width_of_cut_mm=50.0)

    # Feed rate depends only on n, fz and zn -- never on the engagement.
    assert math.isclose(narrow.feed_rate_mm_min, wide.feed_rate_mm_min, rel_tol=1e-12)
    assert math.isclose(narrow.machining_time_min, wide.machining_time_min, rel_tol=1e-12)
    # And no correction factor is folded into the removal rate either.
    assert math.isclose(
        narrow.material_removal_rate_cm3_min * 50.0,
        wide.material_removal_rate_cm3_min,
        rel_tol=1e-12,
    )
