"""Accuracy tests against the published milling formulas (T011a/T053, SC-002).

Constitution Principle III requires calculation formulas to be traceable to
an external published source. The formulas themselves are cited from the
Sandvik Coromant "Machining Formulas" reference (see
``specs/009-milling-calculations/research.md`` #1):

    n  [rpm]      = (vc * 1000) / (pi * Dcap)
    vf [mm/min]   = n * fz * ZEFF
    Q  [cm^3/min] = (ap * ae * vf) / 1000
    Pc [kW]       = (ap * ae * vf * kc) / (60 * 10^6)
    Mc [Nm]       = (Pc * 30 * 10^3) / (pi * n)

This module contains two distinct kinds of check, and does not conflate
them (a Phase 8 convergence fix, T053):

1. ``test_matches_published_formula_outputs`` (below) verifies each output
   against a genuinely **externally published worked example** — the
   classic slab-milling problem widely reproduced across manufacturing
   engineering courses and textbooks (attributed to Groover, *Fundamentals
   of Modern Manufacturing*): a 300 mm x 62.5 mm workpiece is slab-milled by
   a 75 mm diameter, 10-tooth cutter at vc = 37.5 m/min and a feed of
   0.15 mm/tooth per revolution, at a 7.5 mm depth of cut. The expected
   spindle speed, feed rate and material-removal-rate figures below are
   *not copied from any source's own rounding* — they are computed once,
   independently of this project's code, directly from that published
   problem statement using the formulas above (verified by hand, not by
   calling ``calculate_milling_metrics()``), so a transcription error in a
   constant or a unit-conversion bug would move the target independently of
   the module under test.

   Torque and net cutting power are deliberately **not** asserted against
   this example: the widely-available secondary sources reproducing it use
   a different specific-energy convention (a unit-power ``Uc`` factor) than
   this project's ``kc``-based net-power formula, and no edition/page-cited
   ``kc`` value for the workpiece material in this specific example could be
   confirmed. Asserting a torque/power figure without that citation would
   silently reintroduce the same "looks published but isn't" problem this
   task exists to fix, so those two outputs are covered only by the formula
   self-consistency checks below, not by an external numeric reference.

2. ``test_formula_self_consistency`` and ``test_power_is_net_not_motor_power``
   verify that the module's own arithmetic agrees with the published
   *expressions* evaluated longhand for other operating points, and that net
   cutting power is not confusable with a machine's motor input power. These
   catch a genuine class of regression (an internal-consistency break, e.g.
   a stray unit conversion) but — because both sides use the same formula —
   cannot catch a bug shared by both, which is exactly why (1) exists.

All comparisons use ``math.isclose()``; the tolerance is SC-002's 5%
per-output accuracy budget, applied independently to each output value.
"""

import math

import pytest

from mfgparams.operations.milling._shared import calculate_milling_metrics
from mfgparams.registry import WorkpieceMaterial

#: SC-002: each reported value must be within 5% of the reference value.
SC002_REL_TOL = 0.05

#: A drive efficiency in the middle of the range the source quotes for
#: machine tools, used only to show net and motor power are distinguishable.
_TYPICAL_DRIVE_EFFICIENCY = 0.8


def _material(vc_ref: float, kc: float) -> WorkpieceMaterial:
    """Build a material carrying exactly a worked example's vc and kc."""

    return WorkpieceMaterial(
        name="Reference Example Stock",
        reference_cutting_speed_m_min=vc_ref,
        reference_feed_per_rev_mm=0.2,
        specific_cutting_force_kc=kc,
    )


def _published_expectations(
    vc: float, diameter_mm: float, fz: float, zn: float, ap: float, ae: float, kc: float
) -> dict:
    """Evaluate the published formulas longhand, independent of the module."""

    n = (vc * 1000.0) / (math.pi * diameter_mm)
    vf = n * fz * zn
    q = (ap * ae * vf) / 1000.0
    pc = (ap * ae * vf * kc) / (60.0 * 10**6)
    # The reference's torque form, Mc = Pc * 30 * 10^3 / (pi * n), is the
    # exact-constant version of the 9550 constant the module uses; agreeing
    # with it to within SC-002 is part of what this test asserts.
    mc = (pc * 30.0 * 10**3) / (math.pi * n)
    return {"n": n, "vf": vf, "q": q, "pc": pc, "mc": mc}


# --- (1) Genuinely external worked example --------------------------------

#: Groover slab-milling worked example inputs (widely reproduced across
#: manufacturing-engineering course materials): workpiece 300mm x 62.5mm,
#: 75mm/10-tooth cutter, vc=37.5 m/min, fz=0.15 mm/tooth, ap=7.5mm depth.
#: Radial engagement (ae) equals the workpiece width for a full-width slab
#: cut. The material's kc is irrelevant to n/vf/Q, so an arbitrary value is
#: used and only those three outputs are asserted below.
_GROOVER_SLAB_MILLING = {
    "diameter_mm": 75.0,
    "axial_depth_of_cut_mm": 7.5,
    "radial_engagement_mm": 62.5,
    "feed_per_tooth_mm": 0.15,
    "number_of_teeth": 10,
    "length_of_cut_mm": 300.0,
    "material": _material(vc_ref=37.5, kc=1900.0),
    "cutting_speed_factor": 1.0,
}

#: Expected values computed independently from the published inputs above,
#: using the cited formulas evaluated by hand (see module docstring):
#: n = (37.5 * 1000) / (pi * 75) = 159.155 rpm
#: vf = 159.155 * 0.15 * 10 = 238.732 mm/min
#: Q = (7.5 * 62.5 * 238.732) / 1000 = 111.906 cm^3/min
_GROOVER_EXPECTED_SPINDLE_SPEED_RPM = 159.155
_GROOVER_EXPECTED_FEED_RATE_MM_MIN = 238.732
_GROOVER_EXPECTED_MRR_CM3_MIN = 111.906


def test_matches_published_formula_outputs():
    """Spindle speed, feed rate and MRR match a genuine external example.

    Unlike the self-consistency checks below, the expected values here come
    from a real worked problem's published inputs, not from re-running this
    project's own formula on arbitrary numbers (T053, SC-002).
    """

    metrics = calculate_milling_metrics(**_GROOVER_SLAB_MILLING)

    assert math.isclose(
        metrics.spindle_speed_rpm, _GROOVER_EXPECTED_SPINDLE_SPEED_RPM, rel_tol=SC002_REL_TOL
    )
    assert math.isclose(
        metrics.feed_rate_mm_min, _GROOVER_EXPECTED_FEED_RATE_MM_MIN, rel_tol=SC002_REL_TOL
    )
    assert math.isclose(
        metrics.material_removal_rate_cm3_min, _GROOVER_EXPECTED_MRR_CM3_MIN, rel_tol=SC002_REL_TOL
    )
    assert math.isclose(
        metrics.machining_time_min,
        _GROOVER_SLAB_MILLING["length_of_cut_mm"] / _GROOVER_EXPECTED_FEED_RATE_MM_MIN,
        rel_tol=SC002_REL_TOL,
    )


# --- (2) Formula self-consistency across a spread of operating points -----

#: Worked examples: (label, vc, D, fz, zn, ap, ae, kc, length). Values span
#: the reference's steel / stainless / aluminium milling-data ranges so the
#: checks are not all clustered around one operating point. These are
#: **not** externally-sourced numeric examples — see the module docstring.
_SELF_CONSISTENCY_EXAMPLES = [
    ("steel end milling", 200.0, 20.0, 0.10, 4, 5.0, 10.0, 1800.0, 150.0),
    ("stainless face milling", 150.0, 80.0, 0.15, 6, 3.0, 60.0, 2300.0, 300.0),
    ("aluminium high-speed slotting", 500.0, 12.0, 0.08, 3, 8.0, 12.0, 700.0, 200.0),
]


@pytest.mark.parametrize(
    "label,vc,diameter,fz,zn,ap,ae,kc,length",
    _SELF_CONSISTENCY_EXAMPLES,
    ids=[e[0] for e in _SELF_CONSISTENCY_EXAMPLES],
)
def test_formula_self_consistency(label, vc, diameter, fz, zn, ap, ae, kc, length):
    """The module's arithmetic agrees with the published formulas longhand.

    This catches an internal-consistency break (e.g. a stray unit
    conversion) but, because both sides evaluate the same expressions, it
    cannot catch a bug shared by both — that gap is why
    ``test_matches_published_formula_outputs`` exists.
    """

    metrics = calculate_milling_metrics(
        diameter_mm=diameter,
        axial_depth_of_cut_mm=ap,
        radial_engagement_mm=ae,
        feed_per_tooth_mm=fz,
        number_of_teeth=zn,
        length_of_cut_mm=length,
        material=_material(vc, kc),
        cutting_speed_factor=1.0,
    )
    expected = _published_expectations(vc, diameter, fz, zn, ap, ae, kc)

    assert math.isclose(metrics.spindle_speed_rpm, expected["n"], rel_tol=SC002_REL_TOL)
    assert math.isclose(metrics.feed_rate_mm_min, expected["vf"], rel_tol=SC002_REL_TOL)
    assert math.isclose(metrics.material_removal_rate_cm3_min, expected["q"], rel_tol=SC002_REL_TOL)
    assert math.isclose(metrics.power_kw, expected["pc"], rel_tol=SC002_REL_TOL)
    assert math.isclose(metrics.torque_nm, expected["mc"], rel_tol=SC002_REL_TOL)
    assert math.isclose(metrics.machining_time_min, length / expected["vf"], rel_tol=SC002_REL_TOL)


def test_power_is_net_not_motor_power():
    """The reported Pc must be net cutting power, not motor input power.

    ``Pm = Pc / eta`` is a materially different number, and confusing the two
    is the failure mode research.md #1 warns about. Asserting the reported
    value matches ``Pc`` *and* is distinguishable from ``Pm`` at SC-002's
    tolerance makes that confusion detectable.
    """

    label, vc, diameter, fz, zn, ap, ae, kc, length = _SELF_CONSISTENCY_EXAMPLES[0]
    metrics = calculate_milling_metrics(
        diameter_mm=diameter,
        axial_depth_of_cut_mm=ap,
        radial_engagement_mm=ae,
        feed_per_tooth_mm=fz,
        number_of_teeth=zn,
        length_of_cut_mm=length,
        material=_material(vc, kc),
        cutting_speed_factor=1.0,
    )
    net_power = _published_expectations(vc, diameter, fz, zn, ap, ae, kc)["pc"]
    motor_power = net_power / _TYPICAL_DRIVE_EFFICIENCY

    assert math.isclose(metrics.power_kw, net_power, rel_tol=SC002_REL_TOL)
    assert not math.isclose(metrics.power_kw, motor_power, rel_tol=SC002_REL_TOL)


def test_torque_agrees_with_the_exact_constant_form():
    """The module's 9550 constant is the rounded form of ``30 * 10^3 / pi``."""

    assert math.isclose(9550.0, (30.0 * 10**3) / math.pi, rel_tol=1e-3)
