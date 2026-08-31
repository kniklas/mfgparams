"""Unit tests for calculate_end_milling_metrics_at_rpm() (T010).

The wrapper delegates to the shared at-RPM core, so these tests pin the
mapping it is responsible for (radial depth of cut -> radial engagement)
and confirm it produces the expected values for a caller-supplied spindle
speed, mirroring test_formulas.py's coverage of the standard wrapper.
"""

import math

from mfgparams.processes.machining.milling._shared import calculate_milling_metrics_at_rpm
from mfgparams.processes.machining.milling.end_milling.formulas import (
    EndMillingMetrics,
    calculate_end_milling_metrics_at_rpm,
)
from mfgparams.registry import get_material

_MATERIAL = "Mild Steel"


def _call(**overrides):
    kwargs = {
        "diameter_mm": 10.0,
        "axial_depth_of_cut_mm": 2.0,
        "radial_depth_of_cut_mm": 4.0,
        "feed_per_tooth_mm": 0.1,
        "number_of_teeth": 4,
        "length_of_cut_mm": 200.0,
        "material": get_material(_MATERIAL),
        "spindle_speed_rpm": 1500.0,
    }
    kwargs.update(overrides)
    return calculate_end_milling_metrics_at_rpm(**kwargs)


def test_returns_the_sub_operations_own_metrics_type():
    assert isinstance(_call(), EndMillingMetrics)


def test_delegates_to_the_shared_at_rpm_core_with_radial_engagement_mapping():
    """This mapping is the wrapper's entire reason to exist (FR-014)."""

    metrics = _call()
    shared = calculate_milling_metrics_at_rpm(
        diameter_mm=10.0,
        axial_depth_of_cut_mm=2.0,
        radial_engagement_mm=4.0,
        feed_per_tooth_mm=0.1,
        number_of_teeth=4,
        length_of_cut_mm=200.0,
        material=get_material(_MATERIAL),
        spindle_speed_rpm=1500.0,
    )

    assert math.isclose(metrics.spindle_speed_rpm, shared.spindle_speed_rpm, rel_tol=1e-12)
    assert math.isclose(metrics.feed_rate_mm_min, shared.feed_rate_mm_min, rel_tol=1e-12)
    assert math.isclose(
        metrics.material_removal_rate_cm3_min, shared.material_removal_rate_cm3_min, rel_tol=1e-12
    )
    assert math.isclose(metrics.torque_nm, shared.torque_nm, rel_tol=1e-12)
    assert math.isclose(metrics.power_kw, shared.power_kw, rel_tol=1e-12)
    assert math.isclose(metrics.machining_time_min, shared.machining_time_min, rel_tol=1e-12)


def test_spindle_speed_echoes_the_supplied_value_exactly():
    metrics = _call(spindle_speed_rpm=3141.5)

    assert metrics.spindle_speed_rpm == 3141.5


def test_torque_independent_of_spindle_speed():
    low = _call(spindle_speed_rpm=100)
    high = _call(spindle_speed_rpm=5000)

    assert math.isclose(low.torque_nm, high.torque_nm, rel_tol=1e-9)
