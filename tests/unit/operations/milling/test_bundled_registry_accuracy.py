"""End-to-end accuracy tests against the bundled registries (T054, SC-002).

``test_shared_formulas.py`` and ``test_shared_formulas_reference.py`` verify
the shared formula core in isolation, either with hand-computed values or a
synthetic/externally-sourced material. Neither drives the public entry
points (``calculate_end_milling`` / ``calculate_face_milling``) with an
actual **bundled** material and tool name, so a wrong number transcribed
into ``registry.py``'s built-in material table or an
``end_milling/data/tools.toml`` / ``face_milling/data/tools.toml``
``cutting_speed_factor`` would not be caught by any existing test — a gap
identified in the ``speckit.converge`` audit (F2) and closed here.

Each case below reads the bundled reference data live via the same public
registry lookups the entry point itself uses (``get_material``,
``get_end_mill_tool`` / ``get_face_mill_tool``), then computes the expected
outputs by evaluating the published formulas (research.md #1) longhand in
this test file — independently of ``calculate_milling_metrics()`` — before
calling the full public entry point. This catches a bug in either the
bundled data *or* the entry point's own plumbing (unit handling, tool
resolution, wrapper adaptation) while remaining tied to the exact same
"first-party" bundled values a real user would exercise by name.
"""

import math

import pytest

from mfgparams import calculate_end_milling, calculate_face_milling
from mfgparams.processes.machining.milling.end_milling.tools import get_end_mill_tool
from mfgparams.processes.machining.milling.face_milling.tools import get_face_mill_tool
from mfgparams.registry import get_material
from mfgparams.registry_config import clear_cache

#: SC-002: each reported value must be within 5% of the reference value.
SC002_REL_TOL = 0.05


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    clear_cache()
    yield
    clear_cache()


def _expected_metrics(vc_ref, factor, kc, diameter, ap, ae, fz, zn, length):
    """Evaluate the published formulas longhand from live registry values."""

    vc = vc_ref * factor
    n = (vc * 1000.0) / (math.pi * diameter)
    vf = n * fz * zn
    q = (ap * ae * vf) / 1000.0
    pc = (ap * ae * vf * kc) / (60.0 * 10**6)
    mc = (pc * 30.0 * 10**3) / (math.pi * n)
    tc = length / vf
    return {"n": n, "vf": vf, "q": q, "pc": pc, "mc": mc, "tc": tc}


def test_end_milling_matches_bundled_mild_steel_and_carbide():
    """``calculate_end_milling`` agrees with Mild Steel/Carbide's own data."""

    material = get_material("Mild Steel")
    tool = get_end_mill_tool("Carbide")
    geometry = dict(
        diameter=10.0,
        axial_depth_of_cut=2.0,
        radial_depth_of_cut=5.0,
        feed_per_tooth=0.05,
        number_of_teeth=4,
        length_of_cut=100.0,
    )

    result = calculate_end_milling(
        **geometry,
        material="Mild Steel",
        tool="Carbide",
    )
    expected = _expected_metrics(
        vc_ref=material.reference_cutting_speed_m_min,
        factor=tool.cutting_speed_factor,
        kc=material.specific_cutting_force_kc,
        diameter=geometry["diameter"],
        ap=geometry["axial_depth_of_cut"],
        ae=geometry["radial_depth_of_cut"],
        fz=geometry["feed_per_tooth"],
        zn=geometry["number_of_teeth"],
        length=geometry["length_of_cut"],
    )

    assert result.error is None
    assert math.isclose(result.spindle_speed_rpm, expected["n"], rel_tol=SC002_REL_TOL)
    assert math.isclose(result.feed_rate, expected["vf"], rel_tol=SC002_REL_TOL)
    assert math.isclose(result.material_removal_rate, expected["q"], rel_tol=SC002_REL_TOL)
    assert math.isclose(result.power_required, expected["pc"], rel_tol=SC002_REL_TOL)
    assert math.isclose(result.torque, expected["mc"], rel_tol=SC002_REL_TOL)
    assert math.isclose(result.machining_time, expected["tc"], rel_tol=SC002_REL_TOL)


def test_face_milling_matches_bundled_mild_steel_and_carbide():
    """``calculate_face_milling`` agrees with Mild Steel/Carbide's own data."""

    material = get_material("Mild Steel")
    tool = get_face_mill_tool("Carbide")
    geometry = dict(
        diameter=63.0,
        axial_depth_of_cut=2.0,
        width_of_cut=40.0,
        feed_per_tooth=0.1,
        number_of_teeth=5,
        length_of_cut=150.0,
    )

    result = calculate_face_milling(
        **geometry,
        material="Mild Steel",
        tool="Carbide",
    )
    expected = _expected_metrics(
        vc_ref=material.reference_cutting_speed_m_min,
        factor=tool.cutting_speed_factor,
        kc=material.specific_cutting_force_kc,
        diameter=geometry["diameter"],
        ap=geometry["axial_depth_of_cut"],
        ae=geometry["width_of_cut"],
        fz=geometry["feed_per_tooth"],
        zn=geometry["number_of_teeth"],
        length=geometry["length_of_cut"],
    )

    assert result.error is None
    assert math.isclose(result.spindle_speed_rpm, expected["n"], rel_tol=SC002_REL_TOL)
    assert math.isclose(result.feed_rate, expected["vf"], rel_tol=SC002_REL_TOL)
    assert math.isclose(result.material_removal_rate, expected["q"], rel_tol=SC002_REL_TOL)
    assert math.isclose(result.power_required, expected["pc"], rel_tol=SC002_REL_TOL)
    assert math.isclose(result.torque, expected["mc"], rel_tol=SC002_REL_TOL)
    assert math.isclose(result.machining_time, expected["tc"], rel_tol=SC002_REL_TOL)
