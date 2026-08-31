"""Unit tests for drilling formulas (T014).

Nominal, boundary, and known-reference-value checks per SC-002 (results
within 5%, applied independently per output value).
"""

import math

from mfgparams.processes.machining.drilling.formulas import calculate_drilling_metrics
from mfgparams.processes.machining.drilling.tools import get_tool
from mfgparams.registry import get_material


def test_nominal_mild_steel_carbide():
    material = get_material("Mild Steel")
    tool = get_tool("Carbide")

    metrics = calculate_drilling_metrics(10, 25, material, tool)

    # vc = 25 * 2.5 = 62.5 m/min; n = (62.5*1000)/(pi*10) ~= 1989.4 RPM
    expected_rpm = (62.5 * 1000) / (math.pi * 10)
    assert math.isclose(metrics.spindle_speed_rpm, expected_rpm, rel_tol=0.05)

    # fn = 0.20 * 1.1 = 0.22 mm/rev
    expected_feed = expected_rpm * 0.22
    assert math.isclose(metrics.feed_rate_mm_min, expected_feed, rel_tol=0.05)

    expected_time = (25 + 0.3 * 10) / expected_feed
    assert math.isclose(metrics.machining_time_min, expected_time, rel_tol=0.05)

    expected_torque = (1900.0 * 10**2 * 0.22) / 4000
    assert math.isclose(metrics.torque_nm, expected_torque, rel_tol=0.05)

    expected_power = (expected_torque * expected_rpm) / 9550
    assert math.isclose(metrics.power_kw, expected_power, rel_tol=0.05)


def test_all_registered_materials_and_tools_produce_positive_results():
    from mfgparams.processes.machining.drilling.tools import list_tools
    from mfgparams.registry import list_materials

    for material_name in list_materials():
        for tool_name in list_tools():
            material = get_material(material_name)
            tool = get_tool(tool_name)
            metrics = calculate_drilling_metrics(5, 20, material, tool)
            assert metrics.spindle_speed_rpm > 0
            assert metrics.feed_rate_mm_min > 0
            assert metrics.machining_time_min > 0
            assert metrics.torque_nm > 0
            assert metrics.power_kw > 0


def test_larger_diameter_reduces_spindle_speed():
    material = get_material("Mild Steel")
    tool = get_tool("HSS")

    small = calculate_drilling_metrics(5, 20, material, tool)
    large = calculate_drilling_metrics(20, 20, material, tool)

    assert large.spindle_speed_rpm < small.spindle_speed_rpm


def test_boundary_minimal_diameter_and_depth():
    material = get_material("Aluminum")
    tool = get_tool("HSS")

    metrics = calculate_drilling_metrics(0.1, 0.1, material, tool)

    assert metrics.spindle_speed_rpm > 0
    assert metrics.machining_time_min > 0
