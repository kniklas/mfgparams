"""Session-wide collection + Suite Run Summary aggregation (T028/T028b).

Individual :class:`~tests.performance.harness.PerformanceReport` objects are
recorded here as each parametrized case in ``test_calculation_budgets.py``
runs. ``conftest.py``'s ``pytest_sessionfinish`` hook then aggregates all
recorded reports into a single Suite Run Summary
(``specs/006-legacy-hardware-performance-tests/data-model.md``) and writes it
to a JSON file that the CI ``performance`` job's summary step
(``contracts/ci-performance-job-contract.md``) reads to compute the
``status_label``/``metric`` outputs surfaced to ``quality-summary``.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from . import budgets
from .harness import PerformanceReport

#: Environment variable a caller (e.g. CI) can set to override where the
#: Suite Run Summary JSON is written; defaults to a fixed path under the
#: system temp directory so it never gets committed to the repo.
SUMMARY_PATH_ENV_VAR = "MFGPARAMS_PERFORMANCE_SUMMARY_PATH"
_DEFAULT_SUMMARY_FILENAME = "mfgparams_perf_summary.json"

_REPORTS: list[PerformanceReport] = []


def record(report: PerformanceReport) -> None:
    """Record one case's report for later Suite Run Summary aggregation."""

    _REPORTS.append(report)


def all_reports() -> list[PerformanceReport]:
    """Return a copy of every report recorded so far this session."""

    return list(_REPORTS)


def summary_path() -> str:
    """Resolve the path the Suite Run Summary JSON is written to/read from."""

    override = os.environ.get(SUMMARY_PATH_ENV_VAR, "").strip()
    if override:
        return override
    return os.path.join(tempfile.gettempdir(), _DEFAULT_SUMMARY_FILENAME)


def build_suite_run_summary(reports: list[PerformanceReport]) -> dict[str, Any]:
    """Aggregate per-case reports into the Suite Run Summary dict
    (data-model.md's "Suite Run Summary (CI/quality-summary projection)").

    Returns an empty-but-well-formed dict (``has_measurements: False``) when
    ``reports`` is empty, so callers can distinguish "ran but measured
    nothing" from "never ran at all" (the latter is detected by the absence
    of the JSON file itself, per the CI contract's placeholder-fallback
    rule).
    """

    if not reports:
        return {"has_measurements": False}

    worst_time = max(report.measured_time_seconds for report in reports)
    worst_memory = max(report.measured_memory_bytes for report in reports)
    overall_pass = all(report.time_passed and report.memory_passed for report in reports)
    cpu_pin_enforced_overall = all(report.cpu_pin_enforced for report in reports)
    memory_ceiling_enforced_overall = all(report.memory_ceiling_enforced for report in reports)
    # Distinct from `cpu_pin_enforced_overall`/`memory_ceiling_enforced_overall`
    # (which describe *enforcement* — i.e. best-effort mode on a platform
    # like macOS, which is allowed to still "pass" per FR-009/FR-010; this
    # can't happen on Windows, where the lack of the `resource` module
    # means no measurement is ever taken and the reading is always invalid
    # rather than valid-but-unenforced): this instead reports whether every
    # case's memory *reading* itself was usable at all (issue #23). An
    # invalid reading always means `overall_pass=False` too, but the CI
    # summary needs this as a separate signal so it reports a real "fail"
    # for an invalid measurement instead of being masked by the
    # (also-true, but weaker) "⚠️ degraded" case.
    any_invalid_memory_measurement = any(not report.memory_measurement_valid for report in reports)

    return {
        "has_measurements": True,
        "worst_case_time_seconds": worst_time,
        "worst_case_memory_bytes": worst_memory,
        "overall_pass": overall_pass,
        "cpu_pin_enforced_overall": cpu_pin_enforced_overall,
        "memory_ceiling_enforced_overall": memory_ceiling_enforced_overall,
        "any_invalid_memory_measurement": any_invalid_memory_measurement,
        "time_budget_seconds": budgets.TIME_BUDGET_SECONDS,
        "memory_budget_bytes": budgets.MEMORY_BUDGET_BYTES,
    }


def write_summary(path: str | None = None) -> None:
    """Write the current session's Suite Run Summary to ``path`` (JSON)."""

    target_path = path or summary_path()
    parent_dir = os.path.dirname(os.path.abspath(target_path))
    os.makedirs(parent_dir, exist_ok=True)
    summary = build_suite_run_summary(all_reports())
    with open(target_path, "w", encoding="utf-8") as handle:
        json.dump(summary, handle)
