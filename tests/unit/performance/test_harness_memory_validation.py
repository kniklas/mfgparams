"""Unit tests proving invalid memory measurements always fail (issue #23).

These exercise ``tests.performance.harness``'s pure validation/report-
building helpers directly with hand-built child-process result payloads, so
they run as part of the normal (non-opt-in) test suite — unlike
``tests/performance/test_calculation_budgets.py``, which lives under the
auto-skipped ``tests/performance/`` directory (see
``tests/performance/conftest.py``) and only runs when
``MFGPARAMS_RUN_PERFORMANCE_TESTS=1`` is set. No subprocess is spawned
here; :func:`tests.performance.harness._build_report` is deterministic given
a result dict, which is exactly what makes it unit-testable without paying
for/depending on real process isolation.

Tests that exercise the real ``_run_case_in_child`` subprocess boundary (a
real spawned child, a real target exception, a real timeout/hang/reap case)
live in ``tests/performance/test_harness_subprocess_boundary.py`` instead —
that measurement-adjacent, subprocess-spawning logic belongs under the
opt-in ``tests/performance/`` directory (FR-006, SC-004: the default suite
must not execute measurement logic or have its duration affected), not
here.
"""

from __future__ import annotations

import sys
from pathlib import Path

# `tests/` has no `__init__.py` (it is not a regular package, and pytest's
# default "prepend" import mode does not add the repository root to
# `sys.path` on its own — only the nearest package-free ancestor of each
# collected file, per file). Insert the repository root explicitly so
# `tests.performance` resolves as an (implicit namespace) package regardless
# of which test file pytest collects first or how it is invoked in CI.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.performance import harness, results  # noqa: E402 — must follow the sys.path fix-up above


def _case(**overrides: object) -> harness.PerformanceTestCase:
    defaults: dict[str, object] = {
        "name": "dummy-case",
        "target": lambda: None,
        "time_budget_seconds": 1.0,
        "memory_budget_bytes": 128 * 1024 * 1024,
    }
    defaults.update(overrides)
    return harness.PerformanceTestCase(**defaults)  # type: ignore[arg-type]


def _child_result(**overrides: object) -> dict:
    defaults: dict[str, object] = {
        "elapsed_seconds": 0.01,
        "memory_bytes": 1024,
        "error_type": None,
        "error_message": None,
        "cpu_pin_enforced": True,
        "memory_ceiling_enforced": True,
    }
    defaults.update(overrides)
    return defaults


def test_is_valid_memory_measurement_rejects_zero_and_none_and_negative():
    assert harness._is_valid_memory_measurement(1) is True
    assert harness._is_valid_memory_measurement(0) is False
    assert harness._is_valid_memory_measurement(None) is False
    assert harness._is_valid_memory_measurement(-1) is False


def test_is_valid_memory_measurement_rejects_non_int_types():
    """The child-process payload is only loosely typed (``Any``, off a
    pipe) — a malformed reading of the wrong type must be classified as
    invalid rather than silently passing (`bool` is a subtype of `int` in
    Python, so `True`/`False` need an explicit check) or crashing report
    generation deep inside `_build_report`."""

    assert harness._is_valid_memory_measurement(True) is False  # type: ignore[arg-type]
    assert harness._is_valid_memory_measurement(False) is False  # type: ignore[arg-type]
    assert harness._is_valid_memory_measurement(1.5) is False  # type: ignore[arg-type]
    assert harness._is_valid_memory_measurement("1024") is False  # type: ignore[arg-type]


def test_zero_byte_memory_reading_fails_the_case():
    """A `0 B` reading (this issue's original symptom) must never pass."""

    case = _case()
    child_result = _child_result(memory_bytes=0)

    report = harness._build_report(case, child_result)

    assert report.memory_passed is False
    assert report.measured_memory_bytes == 0
    assert report.memory_measurement_valid is False
    assert "invalid memory measurement" in report.overage_detail


def test_none_memory_reading_fails_the_case():
    """An unavailable/never-taken reading (e.g. no `resource` module, or a
    crashed child) must also never pass."""

    case = _case()
    child_result = _child_result(memory_bytes=None)

    report = harness._build_report(case, child_result)

    assert report.memory_passed is False
    assert report.measured_memory_bytes == 0
    assert report.memory_measurement_valid is False
    assert "invalid memory measurement" in report.overage_detail


def test_negative_memory_reading_fails_the_case():
    case = _case()
    child_result = _child_result(memory_bytes=-5)

    report = harness._build_report(case, child_result)

    assert report.memory_passed is False
    assert report.memory_measurement_valid is False
    assert "invalid memory measurement" in report.overage_detail


def test_malformed_string_memory_reading_fails_without_propagating_the_string():
    """A malformed non-int payload (e.g. a stray string from a corrupted
    pipe read) must be classified as invalid AND must not be stored
    verbatim in `measured_memory_bytes` — downstream numeric consumers
    (`build_suite_run_summary`'s `max()`, the CI workflow's byte/MB
    division) would otherwise raise `TypeError` instead of reporting the
    intended explicit failure."""

    case = _case()
    child_result = _child_result(memory_bytes="1024")

    report = harness._build_report(case, child_result)

    assert report.memory_measurement_valid is False
    assert report.memory_passed is False
    assert isinstance(report.measured_memory_bytes, int)
    assert report.measured_memory_bytes == 0
    assert "invalid memory measurement" in report.overage_detail


def test_positive_memory_reading_within_budget_passes():
    case = _case(memory_budget_bytes=1000)
    child_result = _child_result(memory_bytes=500)

    report = harness._build_report(case, child_result)

    assert report.memory_passed is True
    assert report.measured_memory_bytes == 500
    assert report.memory_measurement_valid is True
    assert report.overage_detail is None


def test_positive_memory_reading_over_budget_fails_without_invalid_note():
    """A real (valid) over-budget reading fails for being over budget, not
    for being "invalid" — the two failure modes must stay distinguishable."""

    case = _case(memory_budget_bytes=100)
    child_result = _child_result(memory_bytes=500)

    report = harness._build_report(case, child_result)

    assert report.memory_passed is False
    assert report.memory_measurement_valid is True
    assert "budget exceeded" in report.overage_detail
    assert "invalid memory measurement" not in report.overage_detail


def test_child_process_error_fails_both_dimensions():
    case = _case()
    child_result = _child_result(
        memory_bytes=None,
        error_type="ChildProcessError",
        error_message="measurement child process exited without reporting a result (exit code -9)",
    )

    report = harness._build_report(case, child_result)

    assert report.time_passed is False
    assert report.memory_passed is False
    assert report.memory_measurement_valid is False
    assert "ChildProcessError" in report.overage_detail


def test_crashed_child_with_invalid_memory_includes_invalid_note_not_fabricated_overage():
    """A crashed child with no usable memory reading must state the reading
    is invalid, not compute a bogus overage against a `0`/`None` value."""

    case = _case()
    child_result = _child_result(
        memory_bytes=None,
        error_type="ChildProcessError",
        error_message="measurement child process exited without reporting a result (exit code -9)",
    )

    report = harness._build_report(case, child_result)

    assert report.memory_measurement_valid is False
    assert "invalid memory measurement" in report.overage_detail
    assert "over by -" not in report.overage_detail


def test_crashed_target_with_valid_memory_reports_real_overage():
    """A target exception with a real memory reading captured beforehand
    (e.g. hit the enforced ceiling) should still report a genuine overage,
    not an invalid-measurement note."""

    case = _case(memory_budget_bytes=100)
    child_result = _child_result(
        memory_bytes=500,
        error_type="MemoryError",
        error_message="",
    )

    report = harness._build_report(case, child_result)

    assert report.memory_passed is False
    assert report.memory_measurement_valid is True
    assert "invalid memory measurement" not in report.overage_detail
    assert "over by 400 bytes" in report.overage_detail


def test_crashed_target_with_valid_within_budget_memory_reports_no_negative_overage():
    """A target exception with a real, *within-budget* memory reading (e.g.
    a `MemoryError` triggered by something other than the tracked resource,
    with only 500 bytes measured against a 128MB budget) must never report
    a fabricated negative "over by" figure — it should instead say the
    reading was within budget."""

    case = _case(memory_budget_bytes=128 * 1024 * 1024)
    child_result = _child_result(
        memory_bytes=500,
        error_type="MemoryError",
        error_message="",
    )

    report = harness._build_report(case, child_result)

    assert report.memory_measurement_valid is True
    assert "invalid memory measurement" not in report.overage_detail
    assert "over by" not in report.overage_detail
    assert "within the" in report.overage_detail
    assert "byte memory budget" in report.overage_detail


def test_build_suite_run_summary_flags_any_invalid_memory_measurement():
    """Covers the aggregation step Copilot's review flagged as untested:
    a suite containing one invalid-measurement report must still surface
    ``any_invalid_memory_measurement=True`` in the Suite Run Summary, even
    when every other report in the run is perfectly valid — this is the
    signal ``ci.yml`` relies on to give a hard "fail" precedence over the
    weaker "⚠️ degraded" label (issue #23)."""

    valid_case = _case(name="valid-case")
    valid_report = harness._build_report(valid_case, _child_result(memory_bytes=1024))
    assert valid_report.memory_measurement_valid is True

    invalid_case = _case(name="invalid-case")
    invalid_report = harness._build_report(invalid_case, _child_result(memory_bytes=None))
    assert invalid_report.memory_measurement_valid is False

    summary = results.build_suite_run_summary([valid_report, invalid_report])

    assert summary["any_invalid_memory_measurement"] is True
    # A single invalid case must not be washed out by an otherwise-valid run.
    assert summary["has_measurements"] is True


def test_build_suite_run_summary_reports_no_invalid_measurement_when_all_valid():
    case_a = _case(name="case-a")
    case_b = _case(name="case-b")
    report_a = harness._build_report(case_a, _child_result(memory_bytes=1024))
    report_b = harness._build_report(case_b, _child_result(memory_bytes=2048))

    summary = results.build_suite_run_summary([report_a, report_b])

    assert summary["any_invalid_memory_measurement"] is False
