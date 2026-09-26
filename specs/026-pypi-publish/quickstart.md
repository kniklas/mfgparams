# Quickstart: Validating Automated PyPI Publishing

This is the manual validation guide for this feature — the actual PyPI/TestPyPI side effects
cannot be safely exercised by an automated test suite, so these scenarios are run by hand once,
per Constitution Principle II's testing-standards intent and the Constitution Check's note in
`plan.md` (this is ordinary infrastructure rollout verification, not a Principle XIII case).

## Prerequisites

- Repository owner access to configure PyPI/TestPyPI Trusted Publishers and GitHub Environments.
- `mfgparams`'s existing local dev setup: `pip install -e ".[dev]"` (now including `twine` per
  this feature).
- The registered production PyPI Trusted Publisher for this repo currently references the
  wrong workflow filename (`ci.yml` — a pre-existing mismatch, research.md #8). This MUST be
  corrected to `publish.yml` before Scenario 3 below, or the OIDC exchange will fail.

## Local validation (before any CI run)

```bash
python -m pip install --upgrade build twine
python -m build                 # produces dist/*.whl and dist/*.tar.gz
python -m twine check dist/*    # same metadata check publish.yml runs before every upload
```

Both MUST succeed before proceeding — this mirrors `publish-workflow-contract.md`'s pre-upload
validation contract locally.

## Scenario 1 — TestPyPI dry run (User Story 2, FR-005)

1. On PyPI's TestPyPI instance, register a new Trusted Publisher for this repository, workflow
   filename `publish.yml`, environment `testpypi`.
2. In GitHub, create the `testpypi` Environment if it does not already exist.
3. From the Actions tab, manually run `publish.yml` via `workflow_dispatch` with `target:
   testpypi`.
4. **Expected outcome**: the run succeeds; `twine check` passes; the package appears on
   `test.pypi.org`.
5. In a clean virtual environment: `pip install --index-url https://test.pypi.org/simple/
   mfgparams` and confirm it imports and its CLI entry point runs.

This scenario MUST pass once before Scenario 3 is attempted for the first time.

## Scenario 2 — Idempotent no-op on an unchanged version (US1 edge case, FR-002/FR-007)

1. Manually re-run `publish.yml` via `workflow_dispatch` with `target: testpypi` again, without
   having changed `__version__` since Scenario 1.
2. **Expected outcome**: the run still reports overall success; the upload step reports the
   version already exists (`skip-existing` no-op) rather than failing.

## Scenario 3 — Real production publish on a version-bump merge (User Story 1, FR-001/FR-003)

1. Correct the production PyPI Trusted Publisher's workflow filename from `ci.yml` to
   `publish.yml` (FR-009) — this is a prerequisite, not a step this workflow can perform itself.
2. Merge an ordinary pull request to `main` that bumps `__version__` and adds the corresponding
   `CHANGELOG.md` entry (the project's existing convention).
3. Watch `ci.yml` complete successfully on `main`, then confirm `publish.yml` fires
   automatically (`workflow_run`) immediately afterward.
4. **Expected outcome**: within 10 minutes of the merge (SC-001), `pip install
   mfgparams==<new-version>` succeeds against the real, public PyPI index, with no manual
   action beyond the merge itself.

## Scenario 4 — No-op on a merge that doesn't touch the version (US1 edge case, FR-002)

1. Merge an ordinary pull request to `main` that does not change `__version__` (e.g. a
   docs-only change, or one where `build` is path-filtered out entirely).
2. **Expected outcome**: `publish.yml` still runs (or, if `build` didn't run at all for that
   commit, reports a clean no-op per the artifact contract) but does not error and does not
   attempt to publish a duplicate version.

## Scenario 5 — Retry after a transient failure (FR-008, SC-005)

1. Simulate a transient failure (e.g. temporarily point the upload step at an invalid
   `repository-url`, or wait for/observe a real PyPI outage) on a `workflow_run`-triggered run.
2. From the Actions tab, use "Re-run failed jobs" on that same run — without creating any new
   commit.
3. **Expected outcome**: the retried run re-fetches the same `dist` artifact by `run-id` and
   successfully publishes, with no new commit required.

## Scenario 6 — No stored long-lived credential (User Story 3, FR-004/SC-003)

1. Inspect the repository's and both Environments' (`pypi`, `testpypi`) configured secrets.
2. **Expected outcome**: no secret resembling a PyPI/TestPyPI API token is present anywhere;
   every publish run authenticates via OIDC only.
