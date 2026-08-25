"""Auto-skip hook for the opt-in ``tests/performance/`` suite.

``pyproject.toml``'s ``testpaths = ["tests"]`` means a bare ``pytest`` run
(what CI's ``test`` job and any local default invocation use) discovers
files under ``tests/performance/`` by default, since it is a subdirectory of
``tests/``. This hook applies ``pytest.mark.skip`` to every item collected
under this directory unless ``MFGPARAMS_RUN_PERFORMANCE_TESTS`` is set to
a truthy value, so the existing default/blocking suite's duration,
pass/fail outcome, and coverage percentage are unaffected (FR-006, FR-007,
SC-004, research.md #1) — the new tests are collected but auto-skipped at
near-zero cost, not the actual multi-second measurement runs.
"""

from __future__ import annotations

import os

import pytest

from . import results

_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _opt_in_enabled() -> bool:
    raw = os.environ.get("MFGPARAMS_RUN_PERFORMANCE_TESTS", "")
    return raw.strip().lower() in _TRUTHY_VALUES


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _opt_in_enabled():
        return

    skip_marker = pytest.mark.skip(
        reason=(
            "tests/performance/ is opt-in — set MFGPARAMS_RUN_PERFORMANCE_TESTS=1 "
            "to run (see specs/006-legacy-hardware-performance-tests/quickstart.md)"
        )
    )
    for item in items:
        if "tests/performance/" in str(item.fspath).replace(os.sep, "/"):
            item.add_marker(skip_marker)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Write the run's Suite Run Summary JSON (T028/T028b), so a subsequent
    CI step (outside this pytest process) can compute the `status_label`/
    `metric` outputs surfaced to `quality-summary`, without depending on
    `continue-on-error`'s always-`success` job result
    (contracts/ci-performance-job-contract.md Non-goals).

    Only writes when the opt-in suite actually ran — a bare/default `pytest`
    invocation (opt-in disabled) never touches this file, so it has no effect
    on the existing gated suite.
    """

    if not _opt_in_enabled():
        return
    results.write_summary()
