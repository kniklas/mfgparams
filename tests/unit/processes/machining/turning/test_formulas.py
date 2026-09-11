"""Unit tests for turning formulas (specs/019-turning-calculations), mirroring
tests/unit/processes/machining/drilling/test_formulas.py.

Nominal, boundary, and known-reference-value checks per SC-002 (results
within 5%, applied independently per output value), added per Copilot
review finding: formulas.py previously had no direct unit tests, only
integration/contract coverage of the wrapper functions.
"""

import math

from mfgparams.processes.machining.turning.formulas import calculate_turning_metrics
from mfgparams.processes.machining.turning.tools import get_turning_tool
from mfgparams.registry import get_material


def test_nominal_mild_steel_carbide():
    material = get_material("Mild Steel")
    tool = get_turning_tool("Carbide")

    metrics = calculate_turning_metrics(40, 2, 100, material, tool)

    # vc = 25 * 2.4 = 60.0 m/min; n = (60.0*1000)/(pi*40) ~= 477.46 RPM
    expected_rpm = (60.0 * 1000) / (math.pi * 40)
    assert math.isclose(metrics.spindle_speed_rpm, expected_rpm, rel_tol=0.05)

    # fn = 0.20 * 1.05 = 0.21 mm/rev
    expected_feed = expected_rpm * 0.21
    assert math.isclose(metrics.feed_rate_mm_min, expected_feed, rel_tol=0.05)

    expected_time = 100 / expected_feed
    assert math.isclose(metrics.machining_time_min, expected_time, rel_tol=0.05)

    # Fc = Kc * ap * fn = 1900 * 2 * 0.21
    expected_force = 1900.0 * 2 * 0.21
    assert math.isclose(metrics.cutting_force_n, expected_force, rel_tol=0.05)

    expected_torque = expected_force * (40 / 2) / 1000
    assert math.isclose(metrics.torque_nm, expected_torque, rel_tol=0.05)

    expected_power = (expected_torque * expected_rpm) / 9550
    assert math.isclose(metrics.power_kw, expected_power, rel_tol=0.05)


def test_all_registered_materials_and_tools_produce_positive_results():
    from mfgparams.processes.machining.turning.tools import list_turning_tools
    from mfgparams.registry import list_materials

    for material_name in list_materials():
        for tool_name in list_turning_tools():
            material = get_material(material_name)
            tool = get_turning_tool(tool_name)
            metrics = calculate_turning_metrics(20, 1, 50, material, tool)
            assert metrics.spindle_speed_rpm > 0
            assert metrics.feed_rate_mm_min > 0
            assert metrics.machining_time_min > 0
            assert metrics.cutting_force_n > 0
            assert metrics.torque_nm > 0
            assert metrics.power_kw > 0


def test_larger_diameter_reduces_spindle_speed():
    material = get_material("Mild Steel")
    tool = get_turning_tool("HSS")

    small = calculate_turning_metrics(20, 1, 50, material, tool)
    large = calculate_turning_metrics(80, 1, 50, material, tool)

    assert large.spindle_speed_rpm < small.spindle_speed_rpm


def test_larger_depth_of_cut_increases_cutting_force_and_power_only():
    """Depth of cut affects cutting force (and everything derived from it)
    but not spindle speed or feed rate, which depend only on cutting speed
    and feed per revolution (research.md #1)."""

    material = get_material("Mild Steel")
    tool = get_turning_tool("HSS")

    shallow = calculate_turning_metrics(40, 1, 100, material, tool)
    deep = calculate_turning_metrics(40, 3, 100, material, tool)

    assert math.isclose(shallow.spindle_speed_rpm, deep.spindle_speed_rpm, rel_tol=1e-9)
    assert math.isclose(shallow.feed_rate_mm_min, deep.feed_rate_mm_min, rel_tol=1e-9)
    assert deep.cutting_force_n > shallow.cutting_force_n
    assert deep.torque_nm > shallow.torque_nm
    assert deep.power_kw > shallow.power_kw


def test_boundary_minimal_diameter_depth_of_cut_and_length():
    material = get_material("Aluminum")
    tool = get_turning_tool("HSS")

    metrics = calculate_turning_metrics(1.0, 0.01, 0.1, material, tool)

    assert metrics.spindle_speed_rpm > 0
    assert metrics.machining_time_min > 0
    assert metrics.cutting_force_n > 0
