# Research: Automated PyPI Publishing on Merge to Main

## 1. Where the publish job lives: separate `publish.yml` vs. a job inside `ci.yml`

**Decision**: A new, dedicated `.github/workflows/publish.yml`, triggered by `workflow_run`
watching `ci.yml`'s completion on `main`, not a job added to `ci.yml` itself.

**Rationale**: PyPI's OIDC Trusted Publishing binds to an exact workflow *filename* — that
binding is a real security boundary, not cosmetic. `ci.yml` is this repository's largest,
most-frequently-changed workflow (~950 lines, touched by nearly every PR that changes CI
config), so keeping `id-token: write` and the trusted-publisher binding there maximizes the
file a change to that permission has to be reviewed against. A separate file also sidesteps
`tests/static/test_ci_ok_aggregate_check.py`'s `SUPPORTING_JOBS`/`REQUIRED_JOBS` invariant
entirely — that test's own docstring calls out how easy it is to silently mis-wire which jobs
gate a merge, and a job living outside `ci.yml` altogether cannot accidentally end up in either
list. This matches the guidance already written into `.github/skills/pypi-package-builder/
SKILL.md` §6.

**Alternatives considered**:
- *Job inside `ci.yml`, gated like `deploy-docs`* (`if: github.event_name == 'push' &&
  github.ref == 'refs/heads/main'`, `needs: [build]`): the repo's own existing precedent, and
  simpler in that it needs no cross-workflow artifact fetch. Rejected because it would put
  `id-token: write` in the file most likely to be touched by unrelated PRs, and would require
  `publish` to be added to `test_ci_ok_aggregate_check.py`'s `SUPPORTING_JOBS` with a rationale
  comment — an extra, easy-to-get-wrong edit to an already load-bearing test, for a job that
  gains nothing from being co-located.
- *Trigger on `push: branches: [main]]` directly in `publish.yml` (rebuilding independently)*:
  simplest cross-file option, but fails FR-006 (publish the artifact CI already validated) and
  would publish even if `ci.yml`'s tests failed on that commit — `workflow_run` lets the publish
  job assert `github.event.workflow_run.conclusion == 'success'` first, which a same-commit
  independent `push` trigger cannot do (it has no way to know `ci.yml`'s outcome on that commit).

**Correction (found in local review, round 3):** `workflow_run` fires whenever the named
workflow completes on `main`, regardless of *what triggered that completion* — the initial `if:`
checked `conclusion`/`head_branch`/`head_repository` but not `github.event.workflow_run.event`,
so a maintainer's manual `workflow_dispatch` re-run of `ci.yml` itself (already a supported,
pre-existing trigger on `ci.yml`) would also satisfy the condition, even though it is not a
merge. Added `github.event.workflow_run.event == 'push'` to pin this to FR-001's literal "every
merge to main," not "every way `ci.yml` can complete on main."

## 2. Idempotency: how a merge that doesn't bump the version avoids a duplicate-publish error

**Decision**: Always attempt the upload; rely on `pypa/gh-action-pypi-publish`'s built-in
`skip-existing: true` input, which queries PyPI itself and treats "this exact version already
exists" as a successful no-op rather than a failure.

**Rationale**: This is the officially-documented mechanism this action provides for exactly
this case, and it removes the need for any custom version-comparison logic (no need to call
PyPI's JSON API, parse the response, and compare against `__version__` in a separate step) —
fewer moving parts, and the source of truth for "is this version already published" stays PyPI
itself rather than a second, potentially-stale check this repo would have to maintain.

**Alternatives considered**: A custom pre-flight step (`curl https://pypi.org/pypi/mfgparams/
<version>/json`, compare, conditionally skip the upload step) — rejected as unnecessary
complexity duplicating what `skip-existing` already does, and it would introduce a second
possible source of drift (the check and the actual upload could disagree under a race).

## 3. Artifact reuse across workflow files

**Decision**: `ci.yml`'s existing `build` job (which already runs `python -m build` and
`pytest -m packaging`) gains one additional step, `actions/upload-artifact@v4`, uploading
`dist/*.whl` and `dist/*.tar.gz` under the name `dist`. `publish.yml` downloads that same
artifact via `actions/download-artifact@v4`, passing `run-id: ${{ github.event.workflow_run.id
}}` and `github-token` to reach across workflow files.

**Rationale**: Directly satisfies FR-006 — the artifact published is byte-for-byte the one
`build`'s own `pytest -m packaging` assertions (bundled-data-in-wheel checks) already
validated, not a second, independently (re)built artifact those checks never saw.
`actions/download-artifact@v4` supports fetching another run's artifact by `run-id` precisely
for this cross-workflow pattern.

**Alternatives considered**: Rebuild inside `publish.yml` (`pip install -e ".[test]"; python -m
build` again) — simpler wiring, but reintroduces exactly the "artifact CI never validated"
risk FR-006 exists to close, and duplicates build time on every merge for no benefit.

**Correction (found in local review, round 2, before the first remote round):** the initial
implementation gave the `publish` job only `contents: read`/`id-token: write` permissions.
`actions/download-artifact@v4`'s own documentation states cross-run downloads (via `run-id`)
require a token with `actions: read` — without it, the download step gets a 403 that
`continue-on-error: true` silently converts into the same no-op path as a legitimately-missing
artifact (research.md #4), making the entire automatic publish feature inert with no visible
error on every real merge. Added `actions: read` to the job's `permissions:` block.

## 4. Handling a merge where `build` was path-filtered out (no `dist` artifact produced)

**Decision**: `publish.yml`'s download step runs with `continue-on-error: true`; the actual
publish step is gated on that download having succeeded (`if: steps.download.outcome ==
'success'`).

**Rationale**: `build` is one of `ci.yml`'s path-filtered jobs (Principle IX's path-based
selection exception) — a docs-only or specs-only merge to `main` legitimately produces no
`dist` artifact at all. Per spec's edge cases, this MUST complete as a cheap no-op, not a
failure. A version-bump always touches `src/mfgparams/__init__.py`, which the `python` path
category (specs/016-ci-path-based-selection) always runs `build` for, so this no-op path can
only occur on merges that could not possibly be a real release anyway.

**Alternatives considered**: None seriously — this falls directly out of decision #1
(`workflow_run`) combined with the pre-existing path-filtering behavior; not handling it would
turn every docs-only merge into a red check on `publish.yml`, a regression `ci-ok` itself
already avoids for the equivalent `build`/`test`/etc. cases.

**Correction (found in local review, round 3):** `continue-on-error: true` alone cannot
distinguish this legitimate no-op from a real, transient download failure on a commit where
`build` actually succeeded (a network blip, a future permissions regression) — both looked
identical, so a real release could silently never publish with no visible error (FR-007). Added
a step that queries the triggering run's `build` job conclusion directly (`gh api
.../actions/runs/<id>/jobs`, requiring the `actions: read` permission decision #3's correction
already added) and a second step that fails the job loudly specifically when `build` succeeded
but the download still failed — the no-op path (build's conclusion is `skipped`) is unaffected.

## 5. Credentials: OIDC Trusted Publishing vs. API token

**Decision**: `pypa/gh-action-pypi-publish@release/v1`, using its native OIDC support
(`id-token: write` permission on the `publish` job, no `password`/token input configured) — no
PyPI API token stored as a secret anywhere.

**Rationale**: Directly satisfies FR-004/SC-003 and matches `.github/skills/pypi-package-
builder/SKILL.md` §6's explicit preference. A short-lived, per-run OIDC credential cannot be
exfiltrated and reused later the way a long-lived stored token can.

**Alternatives considered**: A `PYPI_API_TOKEN` repository secret — rejected outright; this is
the exact anti-pattern the skill's §7 calls out.

## 6. One-time (and reusable) TestPyPI validation

**Decision**: `publish.yml` also accepts `workflow_dispatch` with a `target` choice input
(`testpypi` default, `pypi` alternative — defaulting to the safe dry-run target so running it
without touching the dropdown never publishes to the real index, found in local review round 2).
A `testpypi`-targeted manual run builds fresh
(checkout + `python -m build`, since there is no preceding `workflow_run` artifact to reuse for
an ad hoc dry run) and uploads to `test.pypi.org` under a separate `testpypi` GitHub
Environment with its own Trusted Publisher binding.

**Rationale**: Satisfies FR-005 as a one-time pre-rollout gate, but — unlike a purely ad hoc,
never-encoded-in-CI local `twine upload --repository testpypi` — leaves a permanent, reusable
capability in place. `.github/skills/pypi-package-builder/SKILL.md` §6 recommends testing
against TestPyPI "for any new package or backend change," implying a recurring need, not a
single throwaway action; encoding it as a `workflow_dispatch` path costs almost nothing extra
(it reuses the same job body with a parameterized `repository-url`) and means a future backend
change (e.g. switching build backends) can be dry-run the same way again.

**Alternatives considered**: A one-off, undocumented local `twine upload` never captured in the
workflow — rejected as not reusable and not reviewable (no PR diff records that the validation
happened or how).

**Correction (found in local review, round 3):** the initial `workflow_dispatch` build step ran
`pip install -e ".[test]"` before `python -m build`, copied from `ci.yml`'s own `build` job —
but that install exists there only for the `pytest -m packaging` step that follows it, which
this dry-run path doesn't have. `python -m build` builds in its own PEP 517 isolated
environment and never needed the package installed first. Removed the now-pointless install.

## 7. Metadata validation before upload

**Decision**: Add a `twine check dist/*` step in `publish.yml` immediately before the actual
upload step (both the `pypi` and `testpypi` paths), and add `twine` to `pyproject.toml`'s `dev`
extra so it's available for the same check locally.

**Rationale**: Directly addresses the spec's edge case ("a distribution that fails PyPI's own
metadata validation ... as a normal build/test failure, not a silent partial publish") —
`twine check` catches a malformed `README.md` rendering or invalid metadata before any network
call to PyPI, turning what would otherwise be a rejected-upload error deep in the publish step
into an earlier, clearer failure.

**Alternatives considered**: Relying solely on `pypa/gh-action-pypi-publish` to reject bad
metadata at upload time — works, but produces a less specific error and wastes the upload
attempt; `twine check` is the tool this repo's own skill already names for this exact purpose
(§5).

## 8. Correcting the existing Trusted Publisher registration

**Decision**: Documented as a manual, one-time PyPI web-UI step in `quickstart.md` (repoint the
already-registered production Trusted Publisher from `ci.yml` to `publish.yml`, and register a
second Trusted Publisher entry on TestPyPI for the `testpypi` path) — not automated, since
PyPI's trusted-publisher configuration has no API this repository's own automation can drive.

**Rationale**: Directly satisfies FR-009. This must happen before `publish.yml`'s first real
run on `main` after merge, or the OIDC exchange will fail outright (wrong workflow filename
bound on PyPI's side).

**Alternatives considered**: None — this is inherently an out-of-band, human action on a
third-party service.
