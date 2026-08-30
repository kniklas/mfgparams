"""Static check: the ``ci-ok`` aggregate status check stays honest.

``main``'s branch-protection ruleset requires the single ``ci-ok`` check
instead of naming every job individually (issue #75 P2.4), so ``ci-ok``'s
dependency list *is* the merge gate. Two ways it could silently stop being
one, both called out in ``.github/skills/code-review/SKILL.md`` §7a:

* a supporting job (``performance``, which is ``continue-on-error`` by
  design, or the reporting/deploy jobs) gets added to ``needs:``, quietly
  promoting it to a merge blocker;
* a genuinely required job gets dropped from ``needs:``, quietly removing
  it from the gate while the ruleset still shows one green check.

Neither is visible in a diff review of a 600-line workflow, and neither
fails anything at runtime - the PR just goes green. Both sides of the
invariant are committed to this repo, which is what makes this checkable
here at all: the ruleset itself lives in GitHub's configuration and cannot
be read from CI.
"""

from __future__ import annotations

import pathlib

import pytest

yaml = pytest.importorskip("yaml")

CI_WORKFLOW = pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"

# Jobs that MUST gate a merge. Keep in sync with the ruleset's single
# `ci-ok` entry - this list is what `ci-ok` expands to.
REQUIRED_JOBS = frozenset(
    {
        "lint",
        "complexity",
        "typecheck",
        "security",
        "dependency-scan",
        "test",
        "build",
        "docs",
    }
)

# Jobs that MUST NOT gate a merge, with why - so a future contributor
# adding one to `ci-ok` has to argue with a named reason, not just a test.
SUPPORTING_JOBS = {
    "performance": "continue-on-error by design (FR-013); reports a "
    "non-blocking row rather than failing the build",
    "quality-summary": "posts the PR comment; reporting only",
    "deploy-docs": "runs on pushes to main, never on a pull request",
    "sync-agent-integrations": "schedule/workflow_dispatch only",
}


@pytest.fixture(scope="module")
def ci_jobs() -> dict:
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))["jobs"]


def test_ci_ok_exists_and_is_not_itself_gated_away(ci_jobs: dict) -> None:
    """``ci-ok`` must exist and must run even when a dependency fails.

    Without ``always()`` a failed dependency leaves ``ci-ok`` *skipped*,
    and a required check that never reports leaves the pull request
    blocked with no failing check to point at.
    """
    assert "ci-ok" in ci_jobs, "ci-ok job is missing; main's ruleset requires it"
    assert "always()" in ci_jobs["ci-ok"]["if"], (
        "ci-ok must use `if: always()` or a failed dependency skips it " "instead of failing it"
    )


def test_ci_ok_gates_exactly_the_required_jobs(ci_jobs: dict) -> None:
    assert set(ci_jobs["ci-ok"]["needs"]) == set(REQUIRED_JOBS)


@pytest.mark.parametrize("job,reason", sorted(SUPPORTING_JOBS.items()))
def test_ci_ok_does_not_gate_supporting_jobs(ci_jobs: dict, job: str, reason: str) -> None:
    """A supporting job in ``needs:`` becomes a merge blocker by the back door."""
    assert job not in ci_jobs["ci-ok"]["needs"], (
        f"{job!r} must not gate merges: {reason}. Adding it to ci-ok's "
        "`needs:` makes it one (code-review/SKILL.md §7a)."
    )


def test_every_ci_job_is_classified(ci_jobs: dict) -> None:
    """No job may be silently neither required nor knowingly excluded.

    This is the check that survives a future job being added: whoever adds
    it must decide, here, whether it gates a merge.
    """
    classified = set(REQUIRED_JOBS) | set(SUPPORTING_JOBS) | {"ci-ok"}
    unclassified = set(ci_jobs) - classified
    assert not unclassified, (
        f"ci.yml jobs not classified as required or supporting: "
        f"{sorted(unclassified)}. Add each to REQUIRED_JOBS (it gates "
        f"merges, and ci-ok must `needs:` it) or to SUPPORTING_JOBS."
    )
