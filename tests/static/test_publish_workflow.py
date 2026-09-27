"""Static check: the PyPI publish workflow stays wired to its contract.

``specs/026-pypi-publish`` adds ``.github/workflows/publish.yml`` to satisfy the constitution's
Additional Constraints requirement that every merge to `main` trigger a workflow that builds and
publishes a new PyPI release (issue #40). None of what makes this safe — OIDC-only auth, never a
long-lived token; idempotent (`skip-existing`) uploads; reusing `ci.yml`'s own validated `dist`
artifact rather than rebuilding independently; a metadata check before every upload — is checked
anywhere at runtime, and a GitHub Actions trigger/permission mistake is invisible in a diff
review and fails nothing until the first real merge. This module encodes
``contracts/publish-workflow-contract.md`` so all of the above are checkable here, the same way
``test_ci_path_selection.py`` encodes ``contracts/path-selection-contract.md``.
"""

from __future__ import annotations

import pathlib
import re

import pytest

yaml = pytest.importorskip("yaml")

PUBLISH_WORKFLOW = (
    pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows" / "publish.yml"
)

_RAW_TEXT = PUBLISH_WORKFLOW.read_text(encoding="utf-8")
_WORKFLOW = yaml.safe_load(_RAW_TEXT)
_PUBLISH_JOB = _WORKFLOW["jobs"]["publish"]
_STEPS = _PUBLISH_JOB["steps"]

# PyYAML parses the `on:` mapping key as the boolean `True` under default-safe-load rules
# (YAML 1.1 treats bare `on`/`off`/`yes`/`no` as booleans) - this repo's own
# `test_ci_path_selection.py` doesn't hit this because it never reads `ci.yml`'s `on:` block
# directly. Handled once, here.
_TRIGGERS = _WORKFLOW.get("on", _WORKFLOW.get(True))


def _step_index(predicate) -> int:
    """Index of the first step matching ``predicate``, or -1 if none does."""
    for index, step in enumerate(_STEPS):
        if predicate(step):
            return index
    return -1


def _uses(step: dict, action: str) -> bool:
    return str(step.get("uses", "")).startswith(action)


# ---------------------------------------------------------------------------
# Trigger contract
# ---------------------------------------------------------------------------


def test_workflow_run_trigger_targets_ci_workflow() -> None:
    workflow_run = _TRIGGERS.get("workflow_run")
    assert workflow_run is not None, "publish.yml MUST define a workflow_run trigger"
    assert workflow_run.get("workflows") == ["CI"]
    assert workflow_run.get("types") == ["completed"]


def test_workflow_dispatch_trigger_has_pypi_testpypi_target_choice() -> None:
    dispatch = _TRIGGERS.get("workflow_dispatch")
    assert dispatch is not None, "publish.yml MUST define a workflow_dispatch trigger"
    target_input = dispatch["inputs"]["target"]
    assert target_input["type"] == "choice"
    assert set(target_input["options"]) == {"pypi", "testpypi"}
    # Defaults to the safe dry-run target: GitHub's manual-dispatch UI pre-selects `default`,
    # so defaulting to `pypi` would let an operator publish to the real index by running the
    # dispatch without touching the dropdown (found in local review, round 2).
    assert target_input["default"] == "testpypi"


def test_no_pull_request_trigger() -> None:
    # The one thing that makes this workflow structurally incapable of ever becoming a
    # required pull-request status check (Constitution Principle IX gates only apply to
    # checks that can run on a pull request) - plan.md's Structure Decision relies on this.
    assert "pull_request" not in _TRIGGERS
    assert "pull_request_target" not in _TRIGGERS


def test_publish_job_if_asserts_success_and_main_or_manual_dispatch() -> None:
    condition = _PUBLISH_JOB["if"]
    assert "workflow_dispatch" in condition
    assert "workflow_run.conclusion == 'success'" in condition
    assert "workflow_run.head_branch == 'main'" in condition


def test_publish_job_if_rejects_a_forked_head_repository() -> None:
    # `head_branch` alone is a fork-controlled string (a fork can name its own branch `main`);
    # without also pinning `head_repository` to this repo, a forked pull_request run of ci.yml
    # could spoof the automatic trigger and get its own code published to real PyPI.
    condition = _PUBLISH_JOB["if"]
    assert "workflow_run.head_repository.full_name == github.repository" in condition


def test_publish_job_if_requires_the_upstream_run_was_a_push() -> None:
    # Without this, any other way ci.yml can complete on main (e.g. a maintainer's manual
    # workflow_dispatch re-run of ci.yml itself) would also satisfy the condition, even though
    # FR-001 means an actual merge (found in local review, round 3).
    condition = _PUBLISH_JOB["if"]
    assert "workflow_run.event == 'push'" in condition


# ---------------------------------------------------------------------------
# Credential contract
# ---------------------------------------------------------------------------


def test_job_declares_id_token_write_permission() -> None:
    assert _PUBLISH_JOB["permissions"]["id-token"] == "write"


_TOKEN_SECRET_PATTERN = re.compile(r"secrets\.[A-Za-z0-9_]*PYPI[A-Za-z0-9_]*TOKEN", re.IGNORECASE)


def test_no_long_lived_pypi_token_secret_referenced() -> None:
    # OIDC only (FR-004) - a `secrets.PYPI_API_TOKEN`-shaped reference anywhere in this file
    # would mean a stored, long-lived credential exists, defeating Trusted Publishing entirely.
    assert not _TOKEN_SECRET_PATTERN.search(_RAW_TEXT)


def test_publish_steps_use_gh_action_pypi_publish_with_no_password_input() -> None:
    publish_steps = [s for s in _STEPS if _uses(s, "pypa/gh-action-pypi-publish")]
    assert publish_steps, "expected at least one pypa/gh-action-pypi-publish step"
    for step in publish_steps:
        assert "password" not in step.get("with", {})


# ---------------------------------------------------------------------------
# Idempotency contract
# ---------------------------------------------------------------------------


def test_every_publish_step_sets_skip_existing_true() -> None:
    publish_steps = [s for s in _STEPS if _uses(s, "pypa/gh-action-pypi-publish")]
    assert publish_steps
    for step in publish_steps:
        assert step["with"]["skip-existing"] is True


def test_no_publish_step_has_continue_on_error() -> None:
    # Unlike the artifact-download step (which MUST tolerate a missing artifact), a real
    # upload failure MUST fail the job - otherwise it would be indistinguishable from a
    # legitimate skip-existing no-op (FR-007).
    publish_steps = [s for s in _STEPS if _uses(s, "pypa/gh-action-pypi-publish")]
    assert publish_steps
    for step in publish_steps:
        assert step.get("continue-on-error") is not True


# ---------------------------------------------------------------------------
# Artifact contract
# ---------------------------------------------------------------------------


def test_job_declares_actions_read_permission_for_cross_run_download() -> None:
    # actions/download-artifact@v4 requires this for a cross-run download (`run-id`, the
    # workflow_run path). Without it the download 403s, and `continue-on-error: true` makes
    # that indistinguishable from the legitimate no-artifact no-op - silently making the whole
    # automatic publish path inert with no visible error (found in local review, round 2).
    assert _PUBLISH_JOB["permissions"]["actions"] == "read"


def test_workflow_run_path_downloads_dist_by_run_id_and_tolerates_absence() -> None:
    download_index = _step_index(lambda s: _uses(s, "actions/download-artifact"))
    assert download_index != -1, "expected a download-artifact step for the workflow_run path"
    download = _STEPS[download_index]
    assert download["with"]["name"] == "dist"
    assert "workflow_run.id" in str(download["with"]["run-id"])
    assert download.get("continue-on-error") is True

    download_id = download.get("id")
    assert download_id, "download step needs an id so later steps can gate on its outcome"

    # Everything in the workflow_run path that follows the download MUST be gated on that
    # download having actually succeeded (spec Edge Cases: a commit with `build` path-filtered
    # out completes as a clean no-op, not a failure).
    for step in _STEPS[download_index + 1 :]:
        condition = str(step.get("if", ""))
        if "workflow_run" in condition and _uses(step, "pypa/gh-action-pypi-publish"):
            assert f"steps.{download_id}.outcome" in condition


def test_workflow_dispatch_path_builds_fresh() -> None:
    dispatch_steps = [s for s in _STEPS if "workflow_dispatch" in str(s.get("if", ""))]
    assert any(_uses(s, "actions/checkout") for s in dispatch_steps)
    assert any("python -m build" in str(s.get("run", "")) for s in dispatch_steps)


def test_workflow_dispatch_build_step_skips_the_unnecessary_editable_install() -> None:
    # `python -m build` builds in its own PEP 517 isolated environment; this path runs no
    # tests, so installing the package first (as ci.yml's own `build` job does, for its later
    # `pytest -m packaging` step) is dead weight here (found in local review, round 3).
    build_step = next(s for s in _STEPS if "python -m build" in str(s.get("run", "")))
    assert "pip install -e" not in str(build_step.get("run", ""))


def test_build_outcome_step_queries_the_triggering_runs_build_job() -> None:
    # Distinguishing "build was legitimately skipped" from "build succeeded but the artifact
    # couldn't be downloaded" requires knowing what ci.yml's own build job actually reported for
    # that specific run - independent of whether the download step itself succeeded.
    step = next(
        (s for s in _STEPS if s.get("id") == "build_outcome"),
        None,
    )
    assert step is not None, "expected a step (id: build_outcome) querying ci.yml's build job"
    run = str(step.get("run", ""))
    assert "workflow_run.id" in run
    assert 'select(.name == "build")' in run
    assert "GITHUB_OUTPUT" in run


def test_download_failure_after_build_success_fails_the_job() -> None:
    # A real download failure on a commit where build actually succeeded MUST NOT be silently
    # treated the same as the legitimate no-artifact no-op (FR-007; found in local review,
    # round 3).
    step = next(
        (s for s in _STEPS if "could not be downloaded" in str(s.get("name", ""))),
        None,
    )
    assert step is not None, "expected a step that fails the job on an unexpected download failure"
    condition = str(step.get("if", ""))
    assert "steps.download.outcome != 'success'" in condition
    assert "steps.build_outcome.outputs.conclusion == 'success'" in condition
    assert "exit 1" in str(step.get("run", ""))
    assert step.get("continue-on-error") is not True


# ---------------------------------------------------------------------------
# Pre-upload validation contract
# ---------------------------------------------------------------------------


def test_twine_check_precedes_every_publish_step() -> None:
    publish_index = _step_index(lambda s: _uses(s, "pypa/gh-action-pypi-publish"))
    assert publish_index != -1

    twine_check_seen = any("twine check" in str(s.get("run", "")) for s in _STEPS[:publish_index])
    assert twine_check_seen, "a `twine check` step MUST run before the first upload step"

    for step in _STEPS:
        if _uses(step, "pypa/gh-action-pypi-publish"):
            preceding = _STEPS[: _STEPS.index(step)]
            assert any("twine check" in str(s.get("run", "")) for s in preceding)


# ---------------------------------------------------------------------------
# Environment contract
# ---------------------------------------------------------------------------


def test_environment_resolves_pypi_or_testpypi_per_target() -> None:
    # The environment name is a runtime expression, not a static string - it selects
    # `inputs.target` (`pypi`/`testpypi`) for workflow_dispatch runs and defaults to the
    # literal `pypi` for the automatic workflow_run path (data-model.md GitHub Environment;
    # contract Environment contract).
    environment_name = str(_PUBLISH_JOB["environment"]["name"])
    assert "inputs.target" in environment_name
    assert "'pypi'" in environment_name


def test_testpypi_target_uses_test_pypi_repository_url() -> None:
    publish_steps = [s for s in _STEPS if _uses(s, "pypa/gh-action-pypi-publish")]
    dispatch_publish = [s for s in publish_steps if "workflow_dispatch" in str(s.get("if", ""))]
    assert dispatch_publish, "expected a workflow_dispatch-gated publish step"
    repository_url_expr = str(dispatch_publish[0]["with"].get("repository-url", ""))
    # An exact-match assertion on the whole expression, rather than a substring containment
    # check against a URL-shaped value, sidesteps CodeQL's incomplete-url-substring-sanitization
    # pattern (`"test.pypi.org" in url`) entirely - this is a fixed literal in our own workflow
    # source, not attacker-influenced input, but the exact form of the assertion is what CodeQL
    # actually pattern-matches on.
    assert repository_url_expr == (
        "${{ inputs.target == 'testpypi' && 'https://test.pypi.org/legacy/' || '' }}"
    )
