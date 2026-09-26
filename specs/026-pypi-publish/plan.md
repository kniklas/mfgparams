# Implementation Plan: Automated PyPI Publishing on Merge to Main

**Branch**: `026-pypi-publish` | **Date**: 2026-09-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/026-pypi-publish/spec.md`

## Summary

The project constitution already requires that every merge to `main` trigger an automated
GitHub Actions workflow that builds and publishes a new PyPI release, but no such workflow
exists yet (issue #40). This feature adds a new `.github/workflows/publish.yml`, triggered via
`workflow_run` immediately after `ci.yml` finishes successfully on `main`, that downloads the
exact `dist/*` artifact `ci.yml`'s existing `build` job already produced and validated,
publishes it to PyPI using OIDC Trusted Publishing (`pypa/gh-action-pypi-publish`) with
`skip-existing: true` for idempotency, and supports a manual `workflow_dispatch` path targeting
TestPyPI for one-off pipeline validation and future backend-change dry runs. A separate file
(rather than a job inside `ci.yml`) keeps the OIDC trusted-publisher binding — which PyPI keys
to an exact workflow filename — small, rarely-changed, and outside `ci.yml`'s pull-request
surface area entirely.

## Technical Context

**Language/Version**: GitHub Actions workflow YAML (new `.github/workflows/publish.yml`); no
new Python language-version requirement beyond the existing 3.9-3.12 support matrix.

**Primary Dependencies**: `pypa/gh-action-pypi-publish` (new, pinned, OIDC-based upload action),
`actions/download-artifact@v4` (already used elsewhere in `ci.yml`, reused here to fetch the
`build` job's `dist` artifact across workflow files via `run-id`), `twine` (new dev dependency,
for a `twine check dist/*` metadata-validation step before upload).

**Storage**: N/A.

**Testing**: `pytest` against a new `tests/static/test_publish_workflow.py`, parsing
`publish.yml` with `pyyaml` (the existing `tests/static/*.py` pattern — e.g.
`test_ci_ok_aggregate_check.py`, `test_ci_path_selection.py`) to assert its trigger, permissions,
`skip-existing` idempotency, and absence of any long-lived-token secret reference, since GitHub
Actions trigger/permission wiring cannot be exercised by running the workflow in a unit test.
The actual publish-to-PyPI behavior itself is validated manually per `quickstart.md` (a real
`workflow_dispatch` run against TestPyPI, then observing the first real production publish) —
this is an ordinary infrastructure/rollout validation, not a Constitution Principle XIII case
(see Constitution Check below).

**Target Platform**: GitHub Actions (`ubuntu-latest`), publishing to PyPI (`pypi.org`) and,
for manual dry runs, TestPyPI (`test.pypi.org`).

**Project Type**: CI/infrastructure addition to an existing packaged library; no
`src/mfgparams/**` runtime code is touched.

**Performance Goals**: A version-bump merge to `main` is installable from PyPI within 10
minutes (spec SC-001) — bounded by `ci.yml`'s own runtime plus one short `workflow_run`-triggered
job, not a new performance-sensitive code path.

**Constraints**: MUST NOT depend on a long-lived PyPI API token (FR-004); MUST publish only the
artifact `ci.yml`'s `build` job already validated (FR-006); MUST be safely re-runnable/idempotent
so a merge that doesn't bump the version, or a retry after a transient failure, never produces a
duplicate-publish error (FR-002, FR-007, FR-008); MUST NOT become a new required status check
that blocks pull requests — it only ever runs after a push to `main` (mirrors the existing
`deploy-docs` job's scope, and the constitution's Additional Constraints list PyPI publishing
alongside Pages publishing as a main-only, post-merge action, not a PR gate).

**Scale/Scope**: One new workflow file (~60-80 lines), one small addition to `ci.yml`'s existing
`build` job (upload the artifact it already produces), one new static test file, one
`pyproject.toml` dev-dependency addition (`twine`), and the manual, one-time PyPI/TestPyPI
Trusted Publisher configuration described in `quickstart.md` (outside this repository, per
spec FR-009).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle VII (Documentation & Publishing) / Additional Constraints**: This feature's
  entire purpose is satisfying the constitution's own standing, previously-unmet requirement
  ("every merge to `main` MUST trigger a workflow that builds and publishes to PyPI"). **Gate:
  PASS** — this feature closes the gap rather than creating one.
- **Principle II (Testing Standards)**: The new workflow's structure (trigger, permissions,
  idempotency, no stored token) gets an automated static test per the existing
  `tests/static/*.py` pattern; the actual PyPI side-effect is out of automated-test reach (no
  test suite can safely publish real packages), so it is validated manually once per
  `quickstart.md` — consistent with how this repo already treats GitHub Actions
  trigger/permission logic (see `test_ci_path_selection.py`'s own rationale). **Gate: PASS.**
- **Principle IV (Python Packaging & Versioning Standards)**: No change to the single-sourced
  `__version__` mechanism, build backend, or `pyproject.toml` structure; this feature only adds
  a publish path on top of the existing, already-compliant packaging. **Gate: PASS.**
- **Principle IX (Automated Code Quality, Complexity & Security Gates)**: `publish.yml` is a
  post-merge deployment action, not one of Principle IX's named quality/security gates, and
  MUST NOT (and per Project Structure below, does not) become part of `ci-ok` or any required
  pull-request status check — directly analogous to the existing `deploy-docs` job, which
  `tests/static/test_ci_ok_aggregate_check.py`'s `SUPPORTING_JOBS` already documents as
  deliberately excluded for the same reason ("runs on pushes to main, never on a pull
  request"). **Gate: PASS.**
- **Principle X (Licensing & Author Rights)**: N/A — no change to license text or terms; the
  package published to PyPI already carries the correct `pyproject.toml` license metadata.
- **Principle XII (Long-Lived Feature Branches for Multi-PR Work)**: N/A — this is one small,
  ordinarily-sized change (one new workflow file, one small edit to an existing job, one new
  test file), deliverable in a single pull request like 013/014/015/016, not a multi-PR feature
  needing an integration branch.
- **Principle XIII (Manual Verification for Interactive & Reference-Fidelity Features)**: N/A —
  this feature has no interactive console/TUI/GUI surface and makes no claim of matching an
  external visual/behavioral reference exactly. The manual TestPyPI/production-publish
  validation in `quickstart.md` is ordinary infrastructure rollout verification (confirming a
  side effect against a real external service that automated tests cannot safely exercise), not
  the look-and-feel/reference-fidelity gap this principle addresses. Not tracked as a
  Principle XIII task.
- **Other principles** (I, III, V, VI, VIII, XI): N/A — no calculation logic, no user-facing
  message, no resource-constraint-relevant runtime code, and no per-agent instruction file is
  touched by this feature.

No violations requiring justification. **Constitution Check: PASS** (re-confirmed post-design
below).

## Project Structure

### Documentation (this feature)

```text
specs/026-pypi-publish/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/
│   └── publish-workflow-contract.md
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created here)
```

### Source Code (repository root)

```text
.github/
└── workflows/
    ├── ci.yml                              # MODIFIED: `build` job gains a step uploading
    │                                        # dist/*.whl + dist/*.tar.gz as the `dist` artifact
    │                                        # (no change to build's existing pass/fail logic
    │                                        # or path-based `if:` condition)
    └── publish.yml                         # NEW: workflow_run(ci.yml, main)-triggered publish
                                             # job (OIDC, skip-existing) + workflow_dispatch
                                             # path targeting TestPyPI for manual dry runs

pyproject.toml                              # MODIFIED: `dev` extra gains `twine` (metadata
                                             # validation step in publish.yml)

tests/
└── static/
    └── test_publish_workflow.py            # NEW: asserts publish.yml's trigger (workflow_run
                                             # on ci.yml/main), permissions (id-token: write,
                                             # least-privilege), skip-existing idempotency, and
                                             # that no PyPI API-token secret is referenced
                                             # anywhere in the file
```

No `src/mfgparams/**` or `docs/source/**` changes. Like specs/016, this feature's entire change
surface is CI configuration plus its static test coverage — there is no application-code
"Option 1/2/3" project structure to choose between.

**Structure Decision**: A dedicated `publish.yml`, triggered by `workflow_run` off `ci.yml`
rather than added as a job inside `ci.yml` (unlike `deploy-docs`, which is a job in `ci.yml`).
This keeps the `id-token: write` permission and the PyPI Trusted Publisher's workflow-filename
binding confined to one small, rarely-touched file outside `ci.yml`'s much larger pull-request
surface area, and — because it lives outside `ci.yml` entirely — it never needs to appear in
`tests/static/test_ci_ok_aggregate_check.py`'s `SUPPORTING_JOBS`/`REQUIRED_JOBS` lists at all,
avoiding any risk to that already-delicate invariant (see research.md #1 for the full
alternatives comparison).

## Constitution Check (post-design re-check)

Phase 1 design (data-model.md, contracts/publish-workflow-contract.md) confirms the change
surface stays exactly as scoped above: one new workflow file, one additive step in `build`
(upload, not modify, its existing output), one new static test file, and one dev-dependency
addition. No runtime code, public library API, calculation logic, or per-agent instruction file
is touched, and `publish.yml` is structurally incapable of becoming a required pull-request
check (it has no `pull_request` trigger at all). **Gate: PASS, unchanged.**

## Complexity Tracking

*No Constitution Check violations — this section is not needed.*
