"""Opt-in tests exercising the real ``_run_case_in_child`` subprocess
boundary (issue #23, review follow-up).

Unlike ``tests/unit/performance/test_harness_memory_validation.py`` (which
only feeds hand-built child-process result *payloads* to the pure
:func:`tests.performance.harness._build_report`), the tests here spawn a
real child process end-to-end through :func:`~tests.performance.harness._run_case_in_child` —
covering the pipe/serialization/process-lifecycle code that a synthetic
payload cannot reach: a genuine positive RSS reading, a target that raises
inside the child, and a hung child that must be terminated/reaped within
its timeout.

This module deliberately lives under the auto-skipped ``tests/performance/``
directory (see ``tests/performance/conftest.py``) rather than
``tests/unit/performance/``: spawning real subprocesses is measurement-
adjacent, non-trivial-cost logic, and the suite contract (FR-006, SC-004;
contracts/performance-suite-contract.md) requires the default/blocking
suite to never execute measurement logic from ``tests/performance/`` or
have its own duration affected by it. Run explicitly via::

    MFGPARAMS_RUN_PERFORMANCE_TESTS=1 pytest tests/performance/ \\
        -m performance -p no:cacheprovider --no-cov -v -s
"""

from __future__ import annotations

import time

import pytest

from . import harness


def _case(**overrides: object) -> harness.PerformanceTestCase:
    defaults: dict[str, object] = {
        "name": "dummy-case",
        "target": lambda: None,
        "time_budget_seconds": 1.0,
        "memory_budget_bytes": 128 * 1024 * 1024,
    }
    defaults.update(overrides)
    return harness.PerformanceTestCase(**defaults)  # type: ignore[arg-type]


def _sum_small_range() -> int:
    return sum(range(1000))


@pytest.mark.performance
def test_run_case_in_child_measures_a_real_subprocess():
    """Exercises the actual subprocess boundary (:func:`_run_case_in_child`),
    not just :func:`_build_report` with a synthetic payload — proves a real
    spawned child reports a genuine, valid measurement end-to-end through
    the pipe/serialization boundary.

    Uses a module-level (picklable) target: the ``spawn`` context requires
    the target be importable by name in the fresh child interpreter, unlike
    a lambda/closure.

    On a platform without the ``resource`` module (Windows), a real child
    can never report a positive RSS reading at all — the measurement is
    always invalid there by design (issue #23; see the platform-capability
    contract), so this test asserts accordingly rather than assuming Linux/
    macOS behavior everywhere.
    """

    case = _case(target=_sum_small_range)

    child_result = harness._run_case_in_child(case)

    assert child_result["error_type"] is None
    assert child_result["elapsed_seconds"] >= 0.0

    report = harness._build_report(case, child_result)
    if harness.resource is None:  # pragma: no cover - not exercised on Linux/macOS CI
        assert child_result["memory_bytes"] is None
        assert report.memory_measurement_valid is False
    else:
        assert child_result["memory_bytes"] is not None
        assert harness._is_valid_memory_measurement(child_result["memory_bytes"]) is True
        assert report.memory_measurement_valid is True
    assert report.time_passed is True


def _raise_value_error() -> None:
    raise ValueError("boom")


@pytest.mark.performance
def test_run_case_in_child_reports_target_exception_without_crashing_harness():
    """A target that raises inside the child process must be reported as an
    error result (not propagate/crash the parent), through the real
    subprocess boundary."""

    case = _case(target=_raise_value_error)

    child_result = harness._run_case_in_child(case)

    assert child_result["error_type"] == "ValueError"
    assert "boom" in (child_result["error_message"] or "")

    report = harness._build_report(case, child_result)
    assert report.time_passed is False
    assert report.memory_passed is False


def _hang_forever() -> None:
    time.sleep(3600)


@pytest.mark.performance
def test_run_case_in_child_times_out_and_is_reaped_promptly():
    """A hung child (never returns) must be terminated and reported as an
    invalid/failed measurement, and must not block for materially longer
    than one timeout window (regression test for the double-timeout bug
    fixed in an earlier review round)."""

    original_timeout = harness._CHILD_TIMEOUT_SECONDS
    harness._CHILD_TIMEOUT_SECONDS = 0.5
    try:
        case = _case(target=_hang_forever)

        start = time.perf_counter()
        child_result = harness._run_case_in_child(case)
        elapsed = time.perf_counter() - start

        # Generous upper bound: should be roughly 1x the (shortened) timeout,
        # never ~2x it (the double-timeout bug this test guards against).
        assert elapsed < harness._CHILD_TIMEOUT_SECONDS * 3
        # A hung/reaped child must be reported as an explicit timeout, not
        # conflated with the "exited without reporting" crash/EOF message
        # (review follow-up: these are distinguishable failure modes).
        assert child_result["error_type"] == "TimeoutError"
        assert child_result["memory_bytes"] is None

        report = harness._build_report(case, child_result)
        assert report.memory_measurement_valid is False
        assert report.memory_passed is False
    finally:
        harness._CHILD_TIMEOUT_SECONDS = original_timeout


@pytest.mark.performance
def test_run_case_in_child_reports_unpicklable_target_startup_failure():
    """``multiprocessing.Process.start()`` (spawn context) requires the
    target to be picklable — a lambda/local closure fails at ``start()``
    time, before any child process is even created. This must be converted
    into a well-formed, failing invalid-measurement report rather than
    propagating the pickling exception out of :func:`_run_case_in_child`."""

    case = _case(target=lambda: None)

    child_result = harness._run_case_in_child(case)

    assert child_result["memory_bytes"] is None
    assert child_result["error_type"] is not None
    assert "failed to start measurement child process" in (child_result["error_message"] or "")

    report = harness._build_report(case, child_result)
    assert report.memory_measurement_valid is False
    assert report.memory_passed is False
    assert report.time_passed is False
