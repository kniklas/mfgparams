"""Static check: CI path-based job selection stays wired correctly.

``specs/016-ci-path-based-selection`` makes ``lint``/``complexity``/``typecheck``/``security``/
``test``/``build``/``docs`` conditional on which paths a pull request actually changed, via a
new ``changes`` job (``dorny/paths-filter``) feeding each of those jobs' ``if:``. Three ways
this could silently break, none visible in a diff review and none failing anything at
runtime in the common case:

* a filtered job's ``if:`` loses the fail-open clause, so a broken ``changes`` job (a bad pin,
  an upstream outage) silently skips it instead of running it anyway - see
  ``contracts/path-selection-contract.md``'s "Fail-open contract";
* ``ci-ok``'s blocking predicate reverts to "any non-success blocks", re-breaking every
  path-filtered pull request the moment it fires;
* a job this feature explicitly excludes from path selection (``dependency-scan``,
  ``sync-agent-integrations``, ``performance``, ``quality-summary``, ``deploy-docs``) quietly
  grows a ``needs.changes`` reference, coupling it to a mechanism FR-006 says it must not
  depend on.

This module encodes the contract in ``contracts/path-selection-contract.md`` so all three are
checkable here, the same way ``test_ci_ok_aggregate_check.py`` checks the aggregate's own
composition invariant.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")

CI_WORKFLOW = pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"

# The seven jobs FR-002/FR-003/FR-004 make conditional on the `changes` job's outputs
# (data-model.md's Job Path Policy table, `filtered: true` rows).
FILTERED_JOBS = frozenset(
    {
        "lint",
        "complexity",
        "typecheck",
        "security",
        "test",
        "build",
        "docs",
    }
)

# Jobs FR-006 explicitly keeps out of path selection - they must run on every non-scheduled
# trigger exactly as before this feature, independent of `changes`.
EXCLUDED_JOBS = frozenset(
    {
        "dependency-scan",
        "sync-agent-integrations",
        "performance",
        "quality-summary",
        "deploy-docs",
    }
)

EXPECTED_PYTHON_GLOBS = {
    "src/**",
    "tests/**",
    "pyproject.toml",
    "tox.ini",
    "scripts/sync_agent_integrations.py",
    "scripts/setup_skill_symlinks.py",
}

# The "known-non-code" paths from spec.md's Assumptions: never trigger the toolchain on their
# own, and MUST be excluded from `other`'s negation too - they are not unanticipated, they are
# the everyday case this feature exists to skip the toolchain for (data-model.md's Path
# Category "Correction" note; found by live quickstart validation, not planning).
EXPECTED_KNOWN_NON_CODE_GLOBS = {
    "specs/**",
    ".github/skills/**",
    "*.md",
    ".claude/**",
}


@pytest.fixture(scope="module")
def ci_jobs() -> dict:
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))["jobs"]


@pytest.fixture(scope="module")
def changes_filters(ci_jobs: dict) -> dict:
    """The `filters:` block passed to `dorny/paths-filter`, parsed as YAML.

    `paths-filter`'s `with.filters` is itself a YAML document embedded as a string, so it
    needs a second `yaml.safe_load` pass - the outer parse only sees one long string.
    """
    steps = ci_jobs["changes"]["steps"]
    filter_step = next(s for s in steps if s.get("uses", "").startswith("dorny/paths-filter"))
    return yaml.safe_load(filter_step["with"]["filters"])


def test_changes_job_exists_and_is_schedule_guarded(ci_jobs: dict) -> None:
    """The filter producer must exist and never run on the weekly cron.

    Every filtered job's own `if:` also excludes `schedule` (unchanged from before this
    feature); if `changes` did not share that guard, it would run pointlessly on a trigger
    with no pull request diff to classify.
    """
    assert "changes" in ci_jobs, "the `changes` job (dorny/paths-filter) is missing"
    condition = ci_jobs["changes"]["if"]
    assert "github.event_name != 'schedule'" in condition


def test_changes_job_defines_exactly_the_four_named_filters(changes_filters: dict) -> None:
    """The category set must match data-model.md's Path Category table exactly.

    Fewer categories silently drops FR-003's catch-all or FR-004's CI-config bypass; extra,
    undocumented categories drift from what the spec/plan/contract describe.
    """
    assert set(changes_filters) == {"python", "docs", "ci_config", "other"}


def test_python_filter_globs_match_the_documented_set(changes_filters: dict) -> None:
    assert set(changes_filters["python"]) == EXPECTED_PYTHON_GLOBS


def test_docs_filter_globs_match_the_documented_set(changes_filters: dict) -> None:
    assert set(changes_filters["docs"]) == {"docs/**"}


def test_ci_config_filter_globs_match_the_documented_set(changes_filters: dict) -> None:
    assert set(changes_filters["ci_config"]) == {".github/workflows/**"}


def test_other_filter_is_a_positive_catch_all_with_named_exclusions(
    changes_filters: dict,
) -> None:
    """FR-003: a genuinely unanticipated path must default every filtered job back on.

    `dorny/paths-filter` composes a filter's match from its list of glob entries in order:
    a bare `**` matches everything, and each subsequent `!`-prefixed entry excludes matches
    from what came before. A single `!(a/**|b/**|...)` extglob string was tried first and is
    silently unreliable once the alternatives contain `**` - live quickstart validation
    showed a `specs/**` file still matching `other = true` even with `specs/**` inside that
    negation string (data-model.md's Path Category "Correction" note, second entry). This
    asserts the list form instead: `**` first, then only `!`-prefixed exclusion entries.
    """
    other_globs = changes_filters["other"]
    assert other_globs[0] == "**", "`other` must start with a bare `**` positive match"
    exclusions = other_globs[1:]
    assert len(set(exclusions)) == len(exclusions), "duplicate exclusion entries in `other`"
    for entry in exclusions:
        assert entry.startswith("!"), f"{entry!r} in `other` must be `!`-prefixed"


def test_other_filter_excludes_every_named_and_known_non_code_glob(
    changes_filters: dict,
) -> None:
    """Every glob any other category *or* the known-non-code row uses must appear, negated,
    in `other` - regression test for the bug live validation caught (see the docstring
    above): a specs-only change matched `other` because `specs/**` was not excluded, running
    every filtered job for the exact case US1 exists to skip it for.
    """
    other_globs = set(changes_filters["other"])
    excluded_elsewhere = (
        EXPECTED_PYTHON_GLOBS | {"docs/**", ".github/workflows/**"} | EXPECTED_KNOWN_NON_CODE_GLOBS
    )
    for glob in excluded_elsewhere:
        assert f"!{glob}" in other_globs, f"{glob!r} is not excluded from `other`"


def test_ci_ok_predicate_accepts_success_and_skipped(ci_jobs: dict) -> None:
    """FR-005: a skip by path selection must not block `ci-ok`.

    Parses the literal predicate out of `ci-ok`'s assertion step, the same technique
    `test_ci_ok_aggregate_check.py::test_ci_ok_actually_asserts_its_dependencies` already uses
    for `sys.exit(1)`/`NEEDS_JSON` - a predicate that silently reverts to "any non-success
    blocks" would re-break every path-filtered pull request the moment someone "simplifies"
    this step, with no other test in this repo catching it.
    """
    steps = ci_jobs["ci-ok"]["steps"]
    body = "\n".join(step.get("run", "") for step in steps)
    assert 'not in ("success", "skipped")' in body, (
        "ci-ok's assertion must accept both 'success' and 'skipped' as non-blocking "
        "(contracts/path-selection-contract.md's blocking-predicate table)"
    )


@pytest.mark.parametrize("job", sorted(FILTERED_JOBS))
def test_filtered_job_depends_on_changes(ci_jobs: dict, job: str) -> None:
    assert "changes" in ci_jobs[job].get(
        "needs", []
    ), f"{job!r} must declare `needs: [changes]` to read the path-selection outputs"


@pytest.mark.parametrize("job", sorted(FILTERED_JOBS))
def test_filtered_job_runs_for_its_relevant_category_and_unmatched_paths(
    ci_jobs: dict, job: str
) -> None:
    """FR-002/FR-003: every filtered job must run for `python` (its relevance category) and
    for `other` (the unmatched-path default) - deliberately not asserting `ci_config` or the
    fail-open clause here; those are separate tests below, mirroring how US1 (this test) and
    US3/US2 (below) are independently verifiable properties of the same `if:` string.
    """
    condition = ci_jobs[job]["if"]
    assert "needs.changes.outputs.python" in condition
    assert "needs.changes.outputs.other" in condition


def test_docs_job_additionally_runs_for_the_docs_category(ci_jobs: dict) -> None:
    """`docs` has one more relevance category than the other six filtered jobs: a Sphinx
    build also depends on `docs/**` itself, not just Python docstrings (data-model.md Job
    Path Policy).
    """
    assert "needs.changes.outputs.docs" in ci_jobs["docs"]["if"]


def test_quality_summary_still_depends_on_every_filtered_job(ci_jobs: dict) -> None:
    """FR-008: `quality-summary` must keep seeing every filtered job's result, including a
    skip, so its existing `status_label()` "⏭️ skipped" rendering stays reachable. Guards
    against a future edit dropping a job from `quality-summary`'s `needs:` - no other test in
    this repo would catch that, since `quality-summary` reporting a row for one fewer job
    fails nothing at runtime.
    """
    needs = set(ci_jobs["quality-summary"]["needs"])
    assert FILTERED_JOBS <= needs


@pytest.mark.parametrize("job", sorted(FILTERED_JOBS))
def test_filtered_job_fails_open_on_changes_failure(ci_jobs: dict, job: str) -> None:
    """A broken `changes` job must never silently narrow the gate (research.md #5).

    Both halves of the fail-open clause are required together: `needs.changes.result ==
    'failure'` alone does nothing, because GitHub Actions implicitly ANDs a bare `if:`
    expression with `success()` of every listed `needs:` unless the expression itself
    contains `always()`, `cancelled()`, or `failure()`. Without the explicit override, a
    `changes` failure would skip this job regardless of what the rest of the condition says -
    and a skip is exactly what the (now non-blocking) `ci-ok` predicate above lets through.
    """
    condition = ci_jobs[job]["if"]
    assert (
        "needs.changes.result == 'failure'" in condition
    ), f"{job!r} is missing the fail-open clause"
    assert "!cancelled()" in condition, (
        f"{job!r} is missing the explicit status-check override needed for the fail-open "
        "clause to actually take effect"
    )


@pytest.mark.parametrize("job", sorted(FILTERED_JOBS))
def test_filtered_job_bypasses_selection_for_ci_config_changes(ci_jobs: dict, job: str) -> None:
    """FR-004: a change to the CI workflow itself must run every filtered job unconditionally,
    regardless of what else did or did not change in the same diff.
    """
    assert "needs.changes.outputs.ci_config" in ci_jobs[job]["if"]


@pytest.mark.parametrize("job", sorted(EXCLUDED_JOBS))
def test_excluded_job_does_not_reference_changes(ci_jobs: dict, job: str) -> None:
    """FR-006: these jobs must stay independent of the path-selection mechanism entirely."""
    condition = str(ci_jobs[job].get("if", ""))
    needs = ci_jobs[job].get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    assert "needs.changes" not in condition, f"{job!r}'s `if:` references `needs.changes`"
    assert "changes" not in needs, f"{job!r} declares `needs: [changes]`"
