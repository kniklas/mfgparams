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

Round 2 of Copilot's review of PR #89 found the original "known-non-code" set
(``specs/**``, ``.github/skills/**``, root ``*.md``, ``.claude/**``) was too broad: three of
those paths are load-bearing for specific checks (``lint``'s skill-symlink check, ``build``'s
packaging of ``README.md``/``LICENSE.md``, and two repo-wide static tests inside ``test``).
The ``skills``/``packaging_metadata`` categories and the ``repo-invariants`` job below exist to
close those three gaps without giving up the skip for everything else under those paths.

This module encodes the contract in ``contracts/path-selection-contract.md`` so all of the
above are checkable here, the same way ``test_ci_ok_aggregate_check.py`` checks the
aggregate's own composition invariant.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

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

# Every category name a filtered job's `if:` can reference.
ALL_CATEGORIES = ("python", "docs", "ci_config", "skills", "packaging_metadata", "other")

# The one extra category (beyond `python`/`ci_config`/`other`, which every filtered job shares)
# each of these three jobs alone depends on.
EXTRA_CATEGORY_BY_JOB = {"docs": "docs", "lint": "skills", "build": "packaging_metadata"}


def _outputs(**overrides: str) -> dict[str, str]:
    """A `needs.changes.outputs` stand-in with every category `'false'` except `overrides`."""
    values = {category: "false" for category in ALL_CATEGORIES}
    values.update(overrides)
    return values


def _evaluate_condition(
    condition: str,
    *,
    event_name: str,
    cancelled: bool,
    changes_result: str,
    outputs: dict[str, str],
) -> bool:
    """Actually evaluate a job's `if:` string for representative inputs, rather than grepping
    it for predicate-shaped substrings - an inverted clause (`!(needs.changes.result ==
    'failure')`) or a reordered/all-`&&` condition can contain every substring the tests below
    look for while behaving nothing like the real thing (Copilot round-3 MEDIUM finding on PR
    #89). Translates the small subset of GitHub Actions expression syntax this repo's `if:`
    strings actually use into an equivalent Python boolean expression and evaluates it with a
    restricted namespace - not a general GitHub Actions expression evaluator, just enough of
    one for `!cancelled()`, `&&`, `||`, `==`, `!=`, and the three dotted-path forms below.
    """
    expr = condition
    expr = expr.replace("!cancelled()", "(not cancelled)")
    expr = re.sub(r"needs\.changes\.outputs\.(\w+)", r"outputs['\1']", expr)
    expr = expr.replace("needs.changes.result", "changes_result")
    expr = expr.replace("github.event_name", "event_name")
    expr = expr.replace("&&", " and ").replace("||", " or ")
    # Restricted namespace (no builtins); the expression comes from this repo's own ci.yml,
    # never from external input.
    try:
        result = eval(
            expr,
            {"__builtins__": {}},
            {
                "event_name": event_name,
                "cancelled": cancelled,
                "changes_result": changes_result,
                "outputs": outputs,
            },
        )
    except NameError as exc:
        raise AssertionError(
            f"_evaluate_condition doesn't model a construct in this if: string "
            f"(translated to {expr!r}, original {condition!r}) - extend the translation "
            f"above for whatever new GitHub Actions syntax was added ({exc})"
        ) from exc
    return bool(result)


# Jobs FR-006 explicitly keeps out of path selection - they must run on every non-scheduled
# trigger exactly as before this feature, independent of `changes`, in every sense: neither
# their own `if:` nor their `needs:` may reference it. `quality-summary` is deliberately NOT
# here even though its own `if:` must equally never become conditional on path selection
# (FR-008 requires it to always run and report one row per job) - unlike these five, it is
# supposed to have `changes`/`repo-invariants` in its `needs:`, to report their result too
# (see test_quality_summary_also_depends_on_changes_and_repo_invariants above). See
# test_quality_summary_if_never_references_changes below for its narrower version of this
# same invariant.
EXCLUDED_JOBS = frozenset(
    {
        "dependency-scan",
        "sync-agent-integrations",
        "performance",
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

# `.github/skills/**`/`.claude/**`: `lint`'s `setup_skill_symlinks.py --check` step verifies
# every canonical skill under the former has a matching symlink under the latter, so either
# changing is exactly the case that check exists to catch (Copilot round-2 HIGH finding #1).
EXPECTED_SKILLS_GLOBS = {
    ".github/skills/**",
    ".claude/**",
}

# `README.md`/`LICENSE.md`: named as `readme`/`license-files` in `pyproject.toml`, so `build`
# (which packages them into the wheel) must run when either changes, unlike every other root
# `*.md` file (Copilot round-2 HIGH finding #2).
EXPECTED_PACKAGING_METADATA_GLOBS = {
    "README.md",
    "LICENSE.md",
}

# Paths that trigger no filtered job at all (spec.md's Assumptions), and MUST be excluded from
# `other`'s negation too - they are not unanticipated, they are the everyday case this feature
# exists to skip the toolchain for (data-model.md's Path Category "Correction" note; found by
# live quickstart validation, not planning). `.github/skills/**`/`.claude/**` and
# `README.md`/`LICENSE.md` used to be in this set too; they are still excluded from `other`
# (handled by their own categories above, not "unanticipated"), but no longer trigger *no*
# job - see `EXPECTED_SKILLS_GLOBS`/`EXPECTED_PACKAGING_METADATA_GLOBS` above.
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
def paths_filter_steps(ci_jobs: dict) -> list[dict]:
    """Both `dorny/paths-filter` steps in the `changes` job, in order.

    Split into two steps because `other`'s exclusion idiom (a positive `**` plus a
    `!`-prefixed entry per excluded glob) only works under `predicate-quantifier: every`
    (all listed patterns must match) - under the default `some` (any pattern matches),
    the bare `**` alone already matches everything, making every negation after it moot.
    `python`/`docs`/`ci_config` are plain OR-lists with no negation, so they stay on the
    default `some` in the first step; `other` gets its own step with `every` explicitly
    set. See `test_other_filter_step_uses_every_quantifier` for why this is checked
    directly rather than only inferred from `other`'s live behavior.
    """
    steps = ci_jobs["changes"]["steps"]
    return [s for s in steps if s.get("uses", "").startswith("dorny/paths-filter")]


@pytest.fixture(scope="module")
def named_filters(paths_filter_steps: list[dict]) -> dict:
    """The `python`/`docs`/`ci_config` filters from the first `paths-filter` step.

    `paths-filter`'s `with.filters` is itself a YAML document embedded as a string, so it
    needs a second `yaml.safe_load` pass - the outer parse only sees one long string.
    """
    return yaml.safe_load(paths_filter_steps[0]["with"]["filters"])


@pytest.fixture(scope="module")
def other_filter_step(paths_filter_steps: list[dict]) -> dict:
    """The second `paths-filter` step, which defines only `other`."""
    return paths_filter_steps[1]


@pytest.fixture(scope="module")
def other_filter_globs(other_filter_step: dict) -> list[str]:
    filters = yaml.safe_load(other_filter_step["with"]["filters"])
    return filters["other"]


def test_changes_job_exists_and_is_schedule_guarded(ci_jobs: dict) -> None:
    """The filter producer must exist and never run on the weekly cron.

    Every filtered job's own `if:` also excludes `schedule` (unchanged from before this
    feature); if `changes` did not share that guard, it would run pointlessly on a trigger
    with no pull request diff to classify.
    """
    assert "changes" in ci_jobs, "the `changes` job (dorny/paths-filter) is missing"
    condition = ci_jobs["changes"]["if"]
    assert "github.event_name != 'schedule'" in condition


def test_changes_job_also_excludes_workflow_dispatch(ci_jobs: dict) -> None:
    """FR-006 in full: every filtered job already bypasses `changes`'s outputs on manual
    dispatch, so `changes` running (and possibly failing) for that trigger only adds a way
    for a required `ci-ok` dependency to fail a manual run nothing downstream needed it for
    (Copilot round-2 HIGH finding: excluding `workflow_dispatch` from the filtered jobs'
    `if:` wasn't enough while `changes` itself still ran for it).
    """
    condition = ci_jobs["changes"]["if"]
    assert "github.event_name != 'workflow_dispatch'" in condition


def test_changes_job_has_contents_read_permission(ci_jobs: dict) -> None:
    """`dorny/paths-filter` needs a checked-out repo to diff non-`pull_request` events (see
    `test_changes_job_checks_out_for_non_pull_request_events`), and checkout needs read
    access to contents - without this permission the checkout step itself can fail on the
    restricted default `GITHUB_TOKEN` this workflow's top-level `permissions:` sets.
    """
    permissions = ci_jobs["changes"].get("permissions", {})
    assert (
        permissions.get("contents") == "read"
    ), "the `changes` job must grant `contents: read` for its checkout step"


def test_changes_job_checks_out_for_non_pull_request_events(ci_jobs: dict) -> None:
    """`dorny/paths-filter` reads changed files via the GitHub API for `pull_request` events,
    but needs a real git checkout to diff `push`/`workflow_dispatch` events - without one the
    `filter`/`other_filter` steps fail on those triggers, and since `changes` is a required
    dependency of `ci-ok`, that failure blocks every push to `main` (the HIGH finding
    Copilot's review caught on PR #89: this job originally had neither `actions/checkout` nor
    `contents: read`).
    """
    steps = ci_jobs["changes"]["steps"]
    checkout_steps = [s for s in steps if s.get("uses", "").startswith("actions/checkout")]
    assert checkout_steps, "the `changes` job must checkout the repo for non-PR diffing"
    filter_step = next(s for s in steps if s.get("uses", "").startswith("dorny/paths-filter"))
    assert steps.index(checkout_steps[0]) < steps.index(
        filter_step
    ), "checkout must precede the paths-filter steps"
    condition = str(checkout_steps[0].get("if", ""))
    assert condition == "github.event_name != 'pull_request'", (
        "the checkout step's `if:` must be exactly this - a substring check "
        "(e.g. containing 'pull_request') would also accept the inverted, wrong "
        "condition `github.event_name == 'pull_request'`, which omits checkout on "
        "exactly the events that need it (Copilot's round-2 MEDIUM finding on PR #89)"
    )


def test_changes_job_has_exactly_two_paths_filter_steps(paths_filter_steps: list[dict]) -> None:
    assert len(paths_filter_steps) == 2, (
        "expected exactly one paths-filter step for python/docs/ci_config and a second, "
        "separate one for other (see the `paths_filter_steps` fixture docstring for why)"
    )


def test_other_filter_step_uses_every_quantifier(other_filter_step: dict) -> None:
    """The one setting that makes `other`'s exclusion idiom actually work.

    Regression test for the bug live validation caught *twice*: a specs-only change kept
    matching `other = true` even after `other`'s glob list correctly listed `!specs/**`
    (and every other exclusion), because the default `predicate-quantifier: some` only
    needs *one* listed pattern to match - and the leading bare `**` always does, making
    every negation after it moot. Without this setting, `other_filter_globs`'s content can
    be perfectly correct and `other` will still evaluate `true` for everything.
    """
    assert other_filter_step["with"].get("predicate-quantifier") == "every", (
        "the `other` paths-filter step must set `predicate-quantifier: every`, or its "
        "`!`-prefixed exclusions are silently ignored (data-model.md's Path Category "
        "'Corrections' note #3)"
    )


def test_changes_job_defines_exactly_the_six_named_filters(
    named_filters: dict, other_filter_globs: list[str]
) -> None:
    """The category set must match data-model.md's Path Category table exactly.

    Fewer categories silently drops FR-003's catch-all or FR-004's CI-config bypass (or, since
    round 2, the `skills`/`packaging_metadata` carve-outs); extra, undocumented categories
    drift from what the spec/plan/contract describe.
    """
    assert set(named_filters) == {
        "python",
        "docs",
        "ci_config",
        "skills",
        "packaging_metadata",
    }
    assert other_filter_globs  # the second step must actually define something


def test_changes_job_outputs_wire_to_the_matching_filter_step_output(ci_jobs: dict) -> None:
    """Every filter *definition* checked above is useless if the job's `outputs:` block maps
    its name to the wrong `steps.*.outputs.*` expression - e.g. `python` wired to
    `steps.filter.outputs.docs` - since every job downstream reads `needs.changes.outputs.*`,
    never the filter step's output directly. No other test in this module would catch that: the
    filter-definition tests above only look at the `filter`/`other_filter` steps' own `with:`
    blocks, and the per-job `if:` tests below only look for `needs.changes.outputs.<name>`
    appearing in a job's condition, which is unaffected by which step that name actually reads
    (Copilot round-3 MEDIUM finding on PR #89).
    """
    outputs = ci_jobs["changes"]["outputs"]
    expected = {
        "python": "${{ steps.filter.outputs.python }}",
        "docs": "${{ steps.filter.outputs.docs }}",
        "ci_config": "${{ steps.filter.outputs.ci_config }}",
        "skills": "${{ steps.filter.outputs.skills }}",
        "packaging_metadata": "${{ steps.filter.outputs.packaging_metadata }}",
        "other": "${{ steps.other_filter.outputs.other }}",
    }
    assert outputs == expected


def test_python_filter_globs_match_the_documented_set(named_filters: dict) -> None:
    assert set(named_filters["python"]) == EXPECTED_PYTHON_GLOBS


def test_docs_filter_globs_match_the_documented_set(named_filters: dict) -> None:
    assert set(named_filters["docs"]) == {"docs/**"}


def test_ci_config_filter_globs_match_the_documented_set(named_filters: dict) -> None:
    assert set(named_filters["ci_config"]) == {".github/workflows/**"}


def test_skills_filter_globs_match_the_documented_set(named_filters: dict) -> None:
    assert set(named_filters["skills"]) == EXPECTED_SKILLS_GLOBS


def test_packaging_metadata_filter_globs_match_the_documented_set(named_filters: dict) -> None:
    assert set(named_filters["packaging_metadata"]) == EXPECTED_PACKAGING_METADATA_GLOBS


def test_other_filter_is_a_positive_catch_all_with_named_exclusions(
    other_filter_globs: list[str],
) -> None:
    """FR-003: a genuinely unanticipated path must default every filtered job back on.

    Under `predicate-quantifier: every` (asserted separately by
    `test_other_filter_step_uses_every_quantifier`), `dorny/paths-filter` requires *every*
    listed pattern to match: a bare `**` (always true) plus a `!`-prefixed entry per
    excluded glob (true only for files outside that glob) together mean "matches something,
    and isn't any of the named exclusions." This asserts the list shape: `**` first, then
    only `!`-prefixed exclusion entries.
    """
    assert other_filter_globs[0] == "**", "`other` must start with a bare `**` positive match"
    exclusions = other_filter_globs[1:]
    assert len(set(exclusions)) == len(exclusions), "duplicate exclusion entries in `other`"
    for entry in exclusions:
        assert entry.startswith("!"), f"{entry!r} in `other` must be `!`-prefixed"


def test_other_filter_excludes_every_named_and_known_non_code_glob(
    other_filter_globs: list[str],
) -> None:
    """Every glob any other category *or* the known-non-code row uses must appear, negated,
    in `other` - regression test for the bug live validation caught (see
    `test_other_filter_step_uses_every_quantifier`'s docstring for the two-part fix): a
    specs-only change matched `other` because `specs/**` was neither excluded nor - even
    once it was - evaluated under a quantifier where the exclusion could take effect,
    running every filtered job for the exact case US1 exists to skip it for.
    """
    other_globs = set(other_filter_globs)
    excluded_elsewhere = (
        EXPECTED_PYTHON_GLOBS | {"docs/**", ".github/workflows/**"} | EXPECTED_KNOWN_NON_CODE_GLOBS
    )
    for glob in excluded_elsewhere:
        assert f"!{glob}" in other_globs, f"{glob!r} is not excluded from `other`"


@pytest.fixture(scope="module")
def ci_ok_assertion_script(ci_jobs: dict) -> str:
    """The embedded `python3 - <<'PY' ... PY` heredoc body from `ci-ok`'s assertion step,
    extracted so it can be executed directly rather than just grepped for a substring.
    """
    steps = ci_jobs["ci-ok"]["steps"]
    body = "\n".join(step.get("run", "") for step in steps)
    match = re.search(r"<<'PY'\n(.*?)\nPY\b", body, re.DOTALL)
    assert match, "could not find the python3 <<'PY' heredoc in ci-ok's assertion step"
    return match.group(1)


@pytest.mark.parametrize(
    "results,expect_exit_zero",
    [
        pytest.param({"lint": "success", "test": "success"}, True, id="all-success"),
        pytest.param({"lint": "success", "changes": "skipped"}, True, id="success-and-skipped"),
        pytest.param({"lint": "skipped", "test": "skipped"}, True, id="all-skipped"),
        pytest.param({"lint": "success", "test": "failure"}, False, id="one-failure"),
        pytest.param({"lint": "success", "test": "cancelled"}, False, id="one-cancelled"),
    ],
)
def test_ci_ok_predicate_accepts_success_and_skipped(
    ci_ok_assertion_script: str, results: dict, expect_exit_zero: bool
) -> None:
    """FR-005: a skip by path selection must not block `ci-ok`, but a real failure still must.

    Actually *executes* the extracted assertion script against representative `NEEDS_JSON`
    payloads rather than grepping the step body for a predicate-shaped substring - a substring
    check would stay green if the matched text moved into a comment or dead branch while the
    live code path silently accepted `failure`/`cancelled` (Copilot round-3 MEDIUM finding on
    PR #89). `test_ci_ok_aggregate_check.py::test_ci_ok_actually_asserts_its_dependencies`
    checks the surrounding wiring (`toJSON(needs)`, `sys.exit(1)` presence); this test checks
    the predicate's actual behavior.
    """
    needs_payload = {name: {"result": result} for name, result in results.items()}
    completed = subprocess.run(
        [sys.executable, "-c", ci_ok_assertion_script],
        env={**os.environ, "NEEDS_JSON": json.dumps(needs_payload)},
        capture_output=True,
        text=True,
    )
    if expect_exit_zero:
        assert completed.returncode == 0, (
            f"expected ci-ok's assertion to pass for {results!r}, but it exited "
            f"{completed.returncode}:\n{completed.stdout}{completed.stderr}"
        )
    else:
        assert completed.returncode != 0, (
            f"expected ci-ok's assertion to fail for {results!r}, but it exited 0 "
            f"(a real failure/cancellation must still block the merge):\n{completed.stdout}"
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


def test_lint_job_additionally_runs_for_the_skills_category(ci_jobs: dict) -> None:
    """`lint` runs `setup_skill_symlinks.py --check`, so a `.github/skills/**`/`.claude/**`
    change must trigger it even when nothing else in `python`/`ci_config`/`other` changed
    (Copilot round-2 HIGH finding #1 on PR #89).
    """
    assert "needs.changes.outputs.skills" in ci_jobs["lint"]["if"]


def test_build_job_additionally_runs_for_the_packaging_metadata_category(ci_jobs: dict) -> None:
    """`build` packages `README.md`/`LICENSE.md` (`pyproject.toml`'s `readme`/
    `license-files`), so a change to either must trigger it even when nothing else in
    `python`/`ci_config`/`other` changed (Copilot round-2 HIGH finding #2 on PR #89).
    """
    assert "needs.changes.outputs.packaging_metadata" in ci_jobs["build"]["if"]


def test_quality_summary_still_depends_on_every_filtered_job(ci_jobs: dict) -> None:
    """FR-008: `quality-summary` must keep seeing every filtered job's result, including a
    skip, so its existing `status_label()` "⏭️ skipped" rendering stays reachable. Guards
    against a future edit dropping a job from `quality-summary`'s `needs:` - no other test in
    this repo would catch that, since `quality-summary` reporting a row for one fewer job
    fails nothing at runtime.
    """
    needs = set(ci_jobs["quality-summary"]["needs"])
    assert FILTERED_JOBS <= needs


def test_quality_summary_also_depends_on_changes_and_repo_invariants(ci_jobs: dict) -> None:
    """A `changes` or `repo-invariants` failure blocks `ci-ok` exactly like any filtered job's
    failure does, so `quality-summary`'s comment must show it too - otherwise a reviewer sees
    every one of the rows above green while `ci-ok` is separately red, with no clue in the
    friendly comment as to why (a local-review finding on PR #89: these two jobs were added to
    `ci-ok`'s `needs:` across earlier rounds of this same review but never propagated here).
    """
    needs = set(ci_jobs["quality-summary"]["needs"])
    assert {"changes", "repo-invariants"} <= needs
    env = ci_jobs["quality-summary"]["steps"][-2]["env"]
    assert env["CHANGES_RESULT"] == "${{ needs.changes.result }}"
    assert env["REPO_INVARIANTS_RESULT"] == "${{ needs.repo-invariants.result }}"
    build_summary_run = ci_jobs["quality-summary"]["steps"][-2]["run"]
    assert "$CHANGES_RESULT" in build_summary_run
    assert "$REPO_INVARIANTS_RESULT" in build_summary_run
    # Both must count toward the FAIL/PASS verdict, not just appear as a row - the `results=`
    # line is what the run script uses to compute the overall status.
    results_line = next(
        line for line in build_summary_run.splitlines() if line.strip().startswith("results=")
    )
    assert "$CHANGES_RESULT" in results_line
    assert "$REPO_INVARIANTS_RESULT" in results_line


def test_quality_summary_if_never_references_changes(ci_jobs: dict) -> None:
    """FR-008: unlike its `needs:` (which legitimately includes `changes`/`repo-invariants` now
    - see the test above), `quality-summary`'s own `if:` must never become conditional on path
    selection. It has to always run and show a row for every job regardless of what changed;
    the whole point of a filtered job reporting `skipped` is that `quality-summary` renders
    that skip, not that `quality-summary` itself gets skipped too.
    """
    condition = str(ci_jobs["quality-summary"].get("if", ""))
    assert "needs.changes" not in condition


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
def test_filtered_job_bypasses_selection_for_workflow_dispatch(ci_jobs: dict, job: str) -> None:
    """FR-006: a manually-dispatched run must be unaffected by path selection - this job must
    run regardless of what `changes` classified, matching its pre-016 behavior for
    `workflow_dispatch` (the second HIGH finding from Copilot's review of PR #89: dispatch
    reached the path selector like any other trigger and could be skipped by it).
    """
    condition = ci_jobs[job]["if"]
    assert (
        "github.event_name == 'workflow_dispatch'" in condition
    ), f"{job!r} is missing the workflow_dispatch bypass required by FR-006"


@pytest.mark.parametrize("job", sorted(FILTERED_JOBS))
def test_filtered_job_bypasses_selection_for_ci_config_changes(ci_jobs: dict, job: str) -> None:
    """FR-004: a change to the CI workflow itself must run every filtered job unconditionally,
    regardless of what else did or did not change in the same diff.
    """
    assert "needs.changes.outputs.ci_config" in ci_jobs[job]["if"]


# (event_name, cancelled, changes_result, outputs, expected)
_GENERIC_IF_CASES = [
    pytest.param(
        "schedule",
        False,
        "success",
        _outputs(python="true", other="true"),
        False,
        id="schedule-excluded",
    ),
    pytest.param("workflow_dispatch", False, "success", _outputs(), True, id="dispatch-bypass"),
    pytest.param(
        "pull_request", False, "failure", _outputs(), True, id="fail-open-on-changes-failure"
    ),
    pytest.param(
        "pull_request",
        True,
        "failure",
        _outputs(python="true"),
        False,
        id="cancelled-overrides-everything",
    ),
    pytest.param("pull_request", False, "success", _outputs(), False, id="nothing-matched-skips"),
    pytest.param(
        "pull_request", False, "success", _outputs(ci_config="true"), True, id="ci-config-bypass"
    ),
    pytest.param(
        "pull_request", False, "success", _outputs(other="true"), True, id="other-catch-all"
    ),
    pytest.param(
        "pull_request", False, "success", _outputs(python="true"), True, id="python-category-match"
    ),
]


@pytest.mark.parametrize("job", sorted(FILTERED_JOBS))
@pytest.mark.parametrize("event_name,cancelled,changes_result,outputs,expected", _GENERIC_IF_CASES)
def test_filtered_job_if_condition_evaluates_correctly(
    ci_jobs: dict,
    job: str,
    event_name: str,
    cancelled: bool,
    changes_result: str,
    outputs: dict,
    expected: bool,
) -> None:
    """Behaviorally re-verifies every property the substring-based tests above check
    individually (schedule exclusion, dispatch bypass, fail-open, ci_config bypass, the
    `python`/`other` categories) by actually evaluating each job's full `if:` string via
    `_evaluate_condition` - the fix for Copilot's round-3 MEDIUM finding that the substring
    checks alone would pass an inverted or restructured condition that behaves nothing like
    the real one. `cancelled=True` additionally checks a property no substring test above
    covers at all: `!cancelled()` must override *every* other clause, including a `changes`
    failure and a matched category, not just gate the fail-open clause specifically.
    """
    condition = ci_jobs[job]["if"]
    actual = _evaluate_condition(
        condition,
        event_name=event_name,
        cancelled=cancelled,
        changes_result=changes_result,
        outputs=outputs,
    )
    assert actual == expected, (
        f"{job}'s if: evaluated to {actual}, expected {expected} "
        f"(event={event_name!r}, cancelled={cancelled}, changes_result={changes_result!r}, "
        f"outputs={outputs!r})"
    )


@pytest.mark.parametrize("category", sorted(EXTRA_CATEGORY_BY_JOB.values()))
def test_only_the_owning_job_runs_for_its_extra_category(ci_jobs: dict, category: str) -> None:
    """`docs`/`skills`/`packaging_metadata` must each start exactly the one job that reads it -
    the behavioral counterpart to `test_docs_job_additionally_runs_for_the_docs_category` and
    its `lint`/`build` equivalents above, none of which check that the category is *absent*
    from every other filtered job's condition. Without this, a copy-paste of the extra clause
    onto the wrong job (or every job) would pass every existing test in this module.
    """
    owning_job = next(job for job, cat in EXTRA_CATEGORY_BY_JOB.items() if cat == category)
    outputs = _outputs(**{category: "true"})
    for job in sorted(FILTERED_JOBS):
        condition = ci_jobs[job]["if"]
        actual = _evaluate_condition(
            condition,
            event_name="pull_request",
            cancelled=False,
            changes_result="success",
            outputs=outputs,
        )
        expected = job == owning_job
        assert actual == expected, (
            f"{job}'s if: evaluated to {actual} when only {category!r} matched; expected "
            f"{expected} (only {owning_job!r} should run for this category)"
        )


@pytest.mark.parametrize("job", sorted(EXCLUDED_JOBS))
def test_excluded_job_does_not_reference_changes(ci_jobs: dict, job: str) -> None:
    """FR-006: these jobs must stay independent of the path-selection mechanism entirely."""
    condition = str(ci_jobs[job].get("if", ""))
    needs = ci_jobs[job].get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    assert "needs.changes" not in condition, f"{job!r}'s `if:` references `needs.changes`"
    assert "changes" not in needs, f"{job!r} declares `needs: [changes]`"


def test_repo_invariants_job_exists_and_is_unfiltered(ci_jobs: dict) -> None:
    """Unlike `EXCLUDED_JOBS` above (pre-existing jobs FR-006 keeps independent of path
    selection), `repo-invariants` is new *because* of path selection: `test`'s skip is unsound
    for two of its tests (see the job's own comment in ci.yml), so they run again here,
    unconditionally, rather than ever being subject to `needs.changes` at all.
    """
    assert "repo-invariants" in ci_jobs, "the `repo-invariants` job is missing"
    job = ci_jobs["repo-invariants"]
    condition = str(job.get("if", ""))
    needs = job.get("needs", [])
    if isinstance(needs, str):
        needs = [needs]
    assert "needs.changes" not in condition, "repo-invariants must not reference needs.changes"
    assert "changes" not in needs, "repo-invariants must not declare needs: [changes]"
    assert "github.event_name != 'schedule'" in condition


def test_repo_invariants_job_runs_both_repo_wide_static_tests(ci_jobs: dict) -> None:
    """The whole point of this job: it must actually invoke the two tests whose skip inside
    `test` would otherwise go uncaught (Copilot round-2 HIGH finding #3 on PR #89).
    """
    steps = ci_jobs["repo-invariants"]["steps"]
    body = "\n".join(step.get("run", "") for step in steps)
    assert "tests/static/test_no_old_package_name.py" in body
    assert "tests/static/test_no_old_layout.py" in body
