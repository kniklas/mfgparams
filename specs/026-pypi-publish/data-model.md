# Data Model: Automated PyPI Publishing on Merge to Main

This feature has no runtime data model — like specs/016-ci-path-based-selection, its
"entities" are CI/release configuration concepts that exist only inside `.github/workflows/
publish.yml`, `ci.yml`'s `build` job, and the external PyPI/TestPyPI registrations. They are
documented here because the relationships between them are exactly what could silently drift
(e.g. the Trusted Publisher Binding pointing at the wrong workflow filename — the very mismatch
this feature's rollout corrects, per research.md #8).

## Dist Artifact

The built package (`dist/*.whl` + `dist/*.tar.gz`) produced once per `ci.yml` run by the
`build` job, uploaded as a named GitHub Actions artifact so `publish.yml` can consume the exact
bytes CI already validated (research.md #3).

| Field | Description |
|---|---|
| `name` | `dist` — the artifact name both `upload-artifact` (in `ci.yml`) and `download-artifact` (in `publish.yml`) reference. |
| `producing_run` | The `ci.yml` workflow run whose `build` job uploaded it; may not exist for a given `main` push if `build` was path-filtered out (research.md #4). |
| `contents` | Exactly the files `python -m build` wrote to `dist/` for that commit — one wheel, one sdist. |

## Publish Attempt

One execution of `publish.yml`'s `publish` job, either automatic (`workflow_run`, targeting
`pypi`) or manual (`workflow_dispatch`, targeting `pypi` or `testpypi`).

| Field | Description |
|---|---|
| `trigger` | `workflow_run` (automatic, only ever targets `pypi`) or `workflow_dispatch` (manual, `target` input selects `pypi`/`testpypi`). |
| `target` | Which index this attempt uploads to — determines the Trusted Publisher Binding and GitHub Environment used. |
| `dist_source` | For `workflow_run`: the `Dist Artifact` from the triggering `ci.yml` run. For `workflow_dispatch`: built fresh in-job (research.md #6), since there is no preceding CI run to attach to. |
| `outcome` | One of: *published* (new version uploaded), *skipped-existing* (version already present — `skip-existing: true`'s no-op, not a failure), *skipped-no-artifact* (automatic run only; `build` didn't run for this commit, research.md #4), *failed* (metadata check or upload itself failed). |

A Publish Attempt MUST NOT be able to reach *published* for a version that is already present
on the target index — that guarantee is `skip-existing: true` itself (research.md #2), not
logic this feature implements independently.

## Trusted Publisher Binding

The out-of-band PyPI/TestPyPI configuration (not stored in this repository) that authorizes
OIDC publishes from a specific GitHub repo + workflow filename + (optionally) environment.

| Field | Description |
|---|---|
| `index` | `pypi.org` or `test.pypi.org` — each needs its own separate binding. |
| `workflow_filename` | MUST be `publish.yml` for both. The production binding currently points at `ci.yml` (a pre-existing mismatch, research.md #8) and MUST be corrected before this feature's first automatic run; the TestPyPI binding does not yet exist and must be created. |
| `environment` | `pypi` or `testpypi` — matches the GitHub Environment name each Publish Attempt runs under (see below), scoping which branch/approval rules apply. |

## GitHub Environment

A GitHub Actions Environment (`pypi` or `testpypi`) the `publish` job runs under, giving PyPI's
OIDC claim a stable environment name to bind to and providing an optional place to attach
protection rules (e.g. required reviewers) independent of this feature's initial scope.

| Field | Description |
|---|---|
| `name` | `pypi` (production path) or `testpypi` (dry-run path). |
| `used_by` | The `publish` job, selected via the Publish Attempt's `target`. |
