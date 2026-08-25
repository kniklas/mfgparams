"""Opt-in legacy-hardware time/memory budget checks (User Story 1, T011-T013).

One :class:`~tests.performance.harness.PerformanceTestCase` per currently
existing public calculation function (FR-001, SC-002: 100% coverage of
``mfgparams.calculate``, ``calculate_drilling_metrics``,
``calculate_drilling_metrics_at_rpm``, ``calculate_power_constrained_metrics``,
and — since specs/009-milling-calculations — ``calculate_end_milling`` and
``calculate_face_milling``), each invoked with a representative, realistic,
happy-path input (data-model.md's validation rule: inputs must not trigger
the target's own input-validation error path).

Skipped by default (see ``tests/performance/conftest.py``); run explicitly
via::

    MFGPARAMS_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/ \\
        -m performance -p no:cacheprovider --no-cov -v -s
"""

from __future__ import annotations

import pytest

from mfgparams import calculate, calculate_end_milling, calculate_face_milling
from mfgparams.operations.drilling.formulas import (
    calculate_drilling_metrics,
    calculate_drilling_metrics_at_rpm,
    calculate_power_constrained_metrics,
)
from mfgparams.operations.drilling.tools import get_tool
from mfgparams.registry import get_material

from . import budgets, harness, results

_MATERIAL = get_material("Mild Steel")
_TOOL = get_tool("Carbide")

# One representative, realistic input set per measured function (T011): a
# 10mm-diameter, 25mm-deep mild-steel/carbide drilling case, matching the
# examples already used across the existing unit-test suite (e.g.
# tests/unit/operations/drilling/test_calculate.py, test_formulas_at_rpm.py).
CASES: list[harness.PerformanceTestCase] = [
    harness.PerformanceTestCase(
        name="calculate() (standard mode)",
        target=calculate,
        call_kwargs={
            "diameter": 10,
            "depth": 25,
            "material": "Mild Steel",
            "tool": "Carbide",
        },
        time_budget_seconds=budgets.TIME_BUDGET_SECONDS,
        memory_budget_bytes=budgets.MEMORY_BUDGET_BYTES,
    ),
    harness.PerformanceTestCase(
        name="calculate_drilling_metrics",
        target=calculate_drilling_metrics,
        call_args=(10, 25, _MATERIAL, _TOOL),
        time_budget_seconds=budgets.TIME_BUDGET_SECONDS,
        memory_budget_bytes=budgets.MEMORY_BUDGET_BYTES,
    ),
    harness.PerformanceTestCase(
        name="calculate_drilling_metrics_at_rpm",
        target=calculate_drilling_metrics_at_rpm,
        call_args=(10, 25, _MATERIAL, _TOOL, 1000.0),
        time_budget_seconds=budgets.TIME_BUDGET_SECONDS,
        memory_budget_bytes=budgets.MEMORY_BUDGET_BYTES,
    ),
    harness.PerformanceTestCase(
        name="calculate_power_constrained_metrics",
        target=calculate_power_constrained_metrics,
        call_args=(10, 25, _MATERIAL, _TOOL, 0.5),
        time_budget_seconds=budgets.TIME_BUDGET_SECONDS,
        memory_budget_bytes=budgets.MEMORY_BUDGET_BYTES,
    ),
    # Milling cases (009 T049). Same 10mm/mild-steel/carbide posture as the
    # drilling cases above, using the representative inputs from
    # specs/009-milling-calculations/quickstart.md so the measured work
    # matches what a real REPL session performs.
    harness.PerformanceTestCase(
        name="calculate_end_milling",
        target=calculate_end_milling,
        call_kwargs={
            "diameter": 10.0,
            "axial_depth_of_cut": 2.0,
            "radial_depth_of_cut": 5.0,
            "feed_per_tooth": 0.05,
            "number_of_teeth": 4,
            "length_of_cut": 100.0,
            "material": "Mild Steel",
            "tool": "Carbide",
        },
        time_budget_seconds=budgets.TIME_BUDGET_SECONDS,
        memory_budget_bytes=budgets.MEMORY_BUDGET_BYTES,
    ),
    harness.PerformanceTestCase(
        name="calculate_face_milling",
        target=calculate_face_milling,
        call_kwargs={
            "diameter": 50.0,
            "axial_depth_of_cut": 1.5,
            "width_of_cut": 40.0,
            "feed_per_tooth": 0.15,
            "number_of_teeth": 5,
            "length_of_cut": 200.0,
            "material": "Mild Steel",
            "tool": "Carbide",
        },
        time_budget_seconds=budgets.TIME_BUDGET_SECONDS,
        memory_budget_bytes=budgets.MEMORY_BUDGET_BYTES,
    ),
]


@pytest.mark.performance
@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
def test_calculation_meets_legacy_hardware_budget(case: harness.PerformanceTestCase) -> None:
    """Each calculation's measured time/memory must stay within budget.

    Prints a per-case report line (visible with ``-v``/``-s``) and asserts
    both dimensions, using the actionable ``overage_detail`` text (User
    Story 3) as the assertion message on failure instead of a bare
    ``assert`` failure (SC-003).
    """

    report = harness.run_case(case)
    results.record(report)

    print(
        f"[performance] {report.case_name}: "
        f"time={report.measured_time_seconds:.4f}s/{case.time_budget_seconds:.4f}s "
        f"(pass={report.time_passed}), "
        f"memory={report.measured_memory_bytes}B/{case.memory_budget_bytes}B "
        f"(pass={report.memory_passed}), "
        f"cpu_pin_enforced={report.cpu_pin_enforced}, "
        f"memory_ceiling_enforced={report.memory_ceiling_enforced}, "
        f"memory_measurement_valid={report.memory_measurement_valid}"
    )

    assert report.time_passed and report.memory_passed, report.overage_detail
