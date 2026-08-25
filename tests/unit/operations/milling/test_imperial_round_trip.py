"""Imperial/metric round-trip equivalence for milling (T023b, FR-013).

Driving each entry point with imperial inputs must describe the *same*
physical cut as the metric-equivalent inputs, so converting the imperial
results back to metric must reproduce the metric results. This covers every
converted quantity: diameter, both depths, feed per tooth and length of cut
on the way in; feed rate, MRR, torque and power on the way out. Machining
time is unit-system independent (always fractional minutes) and must match
without conversion.
"""

import math

import pytest

from mfgparams import calculate_end_milling, calculate_face_milling
from mfgparams.models import UnitSystem
from mfgparams.units import (
    cm3_min_to_in3_min,
    hp_to_kw,
    in3_min_to_cm3_min,
    in_to_mm,
    kw_to_hp,
    mm_to_in,
    nm_to_in_lb,
)

# A cut expressed in canonical metric, and the tolerance for the round trip.
_METRIC_INPUTS = {
    "diameter": 12.0,
    "axial_depth_of_cut": 3.0,
    "engagement": 6.0,
    "feed_per_tooth": 0.08,
    "length_of_cut": 250.0,
    "number_of_teeth": 4,
}
_REL_TOL = 1e-9

_CASES = [
    pytest.param(calculate_end_milling, "radial_depth_of_cut", id="end_milling"),
    pytest.param(calculate_face_milling, "width_of_cut", id="face_milling"),
]


def _run(fn, engagement_arg, unit_system, scale):
    """Run ``fn`` with the shared cut, converted with ``scale`` (mm -> unit)."""

    return fn(
        diameter=scale(_METRIC_INPUTS["diameter"]),
        axial_depth_of_cut=scale(_METRIC_INPUTS["axial_depth_of_cut"]),
        **{engagement_arg: scale(_METRIC_INPUTS["engagement"])},
        feed_per_tooth=scale(_METRIC_INPUTS["feed_per_tooth"]),
        number_of_teeth=_METRIC_INPUTS["number_of_teeth"],
        length_of_cut=scale(_METRIC_INPUTS["length_of_cut"]),
        material="Mild Steel",
        tool="Carbide",
        unit_system=unit_system,
    )


@pytest.mark.parametrize("fn,engagement_arg", _CASES)
def test_imperial_results_convert_back_to_the_metric_results(fn, engagement_arg):
    metric = _run(fn, engagement_arg, UnitSystem.METRIC, lambda mm: mm)
    imperial = _run(fn, engagement_arg, UnitSystem.IMPERIAL, mm_to_in)

    assert metric.error is None and imperial.error is None
    assert imperial.unit_system is UnitSystem.IMPERIAL

    # Spindle speed is RPM in both systems -- no conversion at all.
    assert math.isclose(imperial.spindle_speed_rpm, metric.spindle_speed_rpm, rel_tol=_REL_TOL)
    # Machining time is always fractional minutes (FR-013).
    assert math.isclose(imperial.machining_time, metric.machining_time, rel_tol=_REL_TOL)

    assert math.isclose(in_to_mm(imperial.feed_rate), metric.feed_rate, rel_tol=_REL_TOL)
    assert math.isclose(
        in3_min_to_cm3_min(imperial.material_removal_rate),
        metric.material_removal_rate,
        rel_tol=_REL_TOL,
    )
    assert math.isclose(hp_to_kw(imperial.power_required), metric.power_required, rel_tol=_REL_TOL)
    assert math.isclose(nm_to_in_lb(metric.torque), imperial.torque, rel_tol=_REL_TOL)


@pytest.mark.parametrize("fn,engagement_arg", _CASES)
def test_metric_results_convert_forward_to_the_imperial_results(fn, engagement_arg):
    """The same equivalence, asserted in the opposite direction."""

    metric = _run(fn, engagement_arg, UnitSystem.METRIC, lambda mm: mm)
    imperial = _run(fn, engagement_arg, UnitSystem.IMPERIAL, mm_to_in)

    assert math.isclose(mm_to_in(metric.feed_rate), imperial.feed_rate, rel_tol=_REL_TOL)
    assert math.isclose(
        cm3_min_to_in3_min(metric.material_removal_rate),
        imperial.material_removal_rate,
        rel_tol=_REL_TOL,
    )
    assert math.isclose(kw_to_hp(metric.power_required), imperial.power_required, rel_tol=_REL_TOL)


@pytest.mark.parametrize("fn,engagement_arg", _CASES)
def test_available_power_is_interpreted_in_the_callers_unit_system(fn, engagement_arg):
    """An HP budget must be compared against the required power as HP."""

    metric = _run(fn, engagement_arg, UnitSystem.METRIC, lambda mm: mm)
    ample_hp = kw_to_hp(metric.power_required) * 2
    tight_hp = kw_to_hp(metric.power_required) / 2

    ample = fn(
        diameter=mm_to_in(_METRIC_INPUTS["diameter"]),
        axial_depth_of_cut=mm_to_in(_METRIC_INPUTS["axial_depth_of_cut"]),
        **{engagement_arg: mm_to_in(_METRIC_INPUTS["engagement"])},
        feed_per_tooth=mm_to_in(_METRIC_INPUTS["feed_per_tooth"]),
        number_of_teeth=_METRIC_INPUTS["number_of_teeth"],
        length_of_cut=mm_to_in(_METRIC_INPUTS["length_of_cut"]),
        material="Mild Steel",
        tool="Carbide",
        unit_system=UnitSystem.IMPERIAL,
        available_power=ample_hp,
    )
    tight = fn(
        diameter=mm_to_in(_METRIC_INPUTS["diameter"]),
        axial_depth_of_cut=mm_to_in(_METRIC_INPUTS["axial_depth_of_cut"]),
        **{engagement_arg: mm_to_in(_METRIC_INPUTS["engagement"])},
        feed_per_tooth=mm_to_in(_METRIC_INPUTS["feed_per_tooth"]),
        number_of_teeth=_METRIC_INPUTS["number_of_teeth"],
        length_of_cut=mm_to_in(_METRIC_INPUTS["length_of_cut"]),
        material="Mild Steel",
        tool="Carbide",
        unit_system=UnitSystem.IMPERIAL,
        available_power=tight_hp,
    )

    assert ample.feasibility_warning is None
    assert tight.feasibility_warning is not None
