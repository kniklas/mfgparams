# Contract: PyPI Publish Workflow

This is the interface this feature exposes to contributors reading `main`'s post-merge
automation and to future changes to `.github/workflows/ci.yml` / `publish.yml`, in the same
spirit `specs/016-ci-path-based-selection/contracts/path-selection-contract.md` documents the
path-selection mechanism. `tests/static/test_publish_workflow.py` is the authoritative
enforcement of this contract — this document is the human-readable detail behind it.

## Trigger contract

`publish.yml` MUST define exactly two ways to run:

| Trigger | When it fires | `target` |
|---|---|---|
| `workflow_run` | `ci.yml` (by its `name:`, `CI`) completes, on `main` only | always `pypi` — never manually overridable on this path |
| `workflow_dispatch` | Manually invoked | operator-selected `pypi` (default) or `testpypi` |

`publish.yml` MUST NOT define a `pull_request` (or `pull_request_target`) trigger of any kind —
this is what makes it structurally impossible for this workflow to ever become a required
pull-request status check (Constitution Principle IX gates only apply to checks that *can* run
on a pull request).

The `workflow_run`-triggered path MUST assert both:
- `github.event.workflow_run.conclusion == 'success'` — a failed or cancelled `ci.yml` run MUST
  NOT be published from.
- `github.event.workflow_run.head_branch == 'main'` — a `ci.yml` run for any other branch
  (e.g. a future long-lived Principle XII integration branch) MUST NOT trigger a publish.

## Artifact contract

The `publish` job's `workflow_run` path MUST fetch the `dist` artifact from the *triggering*
`ci.yml` run (`run-id: ${{ github.event.workflow_run.id }}`), never rebuild independently. If
that artifact does not exist (the `build` job was path-filtered out for that commit), the
download step MUST be allowed to fail (`continue-on-error: true`) and every subsequent step
MUST be skipped via `if: steps.download.outcome == 'success'` — this run's overall job status
MUST still report success, not failure, per the spec's no-version-change edge case.

The `workflow_dispatch` path builds `dist/` fresh in-job (research.md #6) and is exempt from
this reuse requirement — it is an explicit, human-initiated dry run, not the automatic
per-merge path FR-006 targets.

## Idempotency contract

Every actual upload attempt (both `pypi` and `testpypi` targets) MUST pass
`skip-existing: true` to `pypa/gh-action-pypi-publish`. A run whose target version is already
published on the destination index MUST report overall success (a legitimate no-op), never a
failure.

## Credential contract

The `publish` job MUST declare `permissions: id-token: write` and MUST NOT reference any
secret whose name suggests a stored PyPI/TestPyPI API token (e.g. matching `*PYPI*TOKEN*` in
`secrets.*`) anywhere in `publish.yml`. Authentication MUST be OIDC-only, via
`pypa/gh-action-pypi-publish`'s native support — no `password`/`repository-url`-plus-token
input pattern.

## Environment contract

Each target MUST run under its own named GitHub Environment (`pypi` for the `pypi` target,
`testpypi` for the `testpypi` target) — never a shared or unnamed environment — so each one's
Trusted Publisher binding, and any future protection rule, is scoped independently.

## Pre-upload validation contract

Every upload attempt, regardless of target, MUST run `twine check dist/*` (or equivalent
metadata validation) against the artifact immediately before the upload step, and MUST fail the
job (not attempt the upload) if that check fails.

## Retry contract

A failed `workflow_run`-triggered publish attempt MUST be retryable by re-running that same
workflow run (GitHub's built-in "Re-run failed jobs") without requiring a new commit/merge —
this holds automatically as a consequence of the trigger and artifact contracts above (the
artifact is fetched by `run-id`, which is stable across re-runs of the same `publish.yml` run),
not something this feature must implement separately.
