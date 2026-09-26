---

description: "Task list for Automated PyPI Publishing on Merge to Main"
---

# Tasks: Automated PyPI Publishing on Merge to Main

**Input**: Design documents from `/specs/026-pypi-publish/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/publish-workflow-contract.md, quickstart.md

**Tests**: Included as first-class tasks (static tests, following this repo's existing
`tests/static/*.py` convention for GitHub Actions trigger/permission logic — Constitution
Principle II).

**Organization**: Tasks are grouped by user story per spec.md's priorities (US1 > US2 > US3).
Two tasks (T016) are placed *after* the User Story 2 phase despite being labeled `[US1]` — this
is a deliberate, spec-documented exception (see Dependencies & Execution Order below), not an
error: spec.md's own User Story 2 rationale states its TestPyPI validation "happens once, ahead
of enabling User Story 1's automation."

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1/US2/US3); Setup/Foundational/Polish
  tasks carry no story label
- Every task names its exact file path

---

## Phase 1: Setup

- [X] T001 [P] Add `twine>=5.0` to the `dev` extra in `pyproject.toml`, for local
  `twine check dist/*` validation matching `.github/skills/pypi-package-builder/SKILL.md` §5
  (research.md #7) — `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared `publish.yml` skeleton and the `dist` artifact both user stories'
trigger paths depend on. No user story's trigger-specific work can start until this is done.

- [X] T002 Add an `actions/upload-artifact@v4` step to the `build` job in
  `.github/workflows/ci.yml`, uploading `dist/*.whl` and `dist/*.tar.gz` under artifact name
  `dist`, without changing `build`'s existing pass/fail logic or `if:` condition (research.md
  #3; data-model.md Dist Artifact) — `.github/workflows/ci.yml`
- [X] T003 Create `.github/workflows/publish.yml`: workflow `name: Publish`, top-level
  `permissions: contents: read`, and a single `publish` job on `ubuntu-latest` with job-level
  `permissions: id-token: write` (research.md #5; contract Credential contract) — no trigger
  and no upload step yet, both added by later phases — `.github/workflows/publish.yml`
- [X] T004 Add a `pip install --upgrade build twine` step to the `publish` job in
  `.github/workflows/publish.yml`, run unconditionally (both the `workflow_run` path's `twine
  check` and the `workflow_dispatch` path's `python -m build`/`twine check` need these tools
  available) (research.md #6/#7) — `.github/workflows/publish.yml`
- [X] T005 [P] Scaffold `tests/static/test_publish_workflow.py`, parsing
  `.github/workflows/publish.yml` with `pyyaml` (mirroring `tests/static/
  test_ci_path_selection.py`'s pattern), asserting: the `publish` job's `permissions.id-token`
  equals `write`, no substring matching a PyPI API-token secret name (e.g. a case-insensitive
  `PYPI` + `TOKEN` pair) appears anywhere in the raw file text, and a `twine check` step exists
  before any `pypa/gh-action-pypi-publish` step (contract Credential/Pre-upload-validation
  contracts) — `tests/static/test_publish_workflow.py`

**Checkpoint**: `publish.yml` exists with OIDC permissions and the `build`/`twine` CLI tools
installed; `build` (the `ci.yml` job) produces a reusable `dist` artifact; a static test locks
in the credential contract and the not-yet-satisfied pre-upload-validation contract (it will
start passing once T008/T012 add each path's `twine check` step). Nothing publishes anywhere
yet — no trigger is wired up.

---

## Phase 3: User Story 1 - Version bump on `main` becomes installable automatically (Priority: P1) 🎯 MVP

**Goal**: A version-bump merge to `main` becomes installable from PyPI without any manual
publish action.

**Independent Test**: Merge a version-bump PR to `main`; confirm `publish.yml` fires
automatically via `workflow_run` once `ci.yml` succeeds, and that `pip install
mfgparams==<version>` works afterward (quickstart Scenario 3). The safe, no-production-impact
half of this story — a merge that does *not* bump the version completing as a clean no-op
(quickstart Scenario 4) — can be verified as soon as this phase's tasks are done; the real
production-publish half (Scenario 3) is deliberately deferred to T016 (see Dependencies).

### Implementation for User Story 1

- [X] T006 [US1] Add the `workflow_run` trigger to `.github/workflows/publish.yml`
  (`workflows: ["CI"]`, `types: [completed]`), gating the `publish` job on
  `github.event.workflow_run.conclusion == 'success' && ...head_branch == 'main' &&
  ...head_repository.full_name == github.repository` — the third clause, added after local
  review found `head_branch` alone spoofable by a forked pull_request run, is load-bearing, not
  optional (contract Trigger contract) — `.github/workflows/publish.yml`
- [X] T007 [US1] Add the artifact-download step for the `workflow_run` path
  (`actions/download-artifact@v4`, `run-id: ${{ github.event.workflow_run.id }}`,
  `name: dist`, `continue-on-error: true`), and gate every subsequent step in that path on
  `if: steps.download.outcome == 'success'`, so a commit with no `dist` artifact (i.e. `build`
  was path-filtered out) completes as a clean no-op rather than a failure (research.md #3/#4;
  contract Artifact contract; spec Edge Cases) — `.github/workflows/publish.yml`
- [X] T008 [US1] Add a `twine check dist/*` step gated
  `if: github.event_name == 'workflow_run' && steps.download.outcome == 'success'`, followed by
  the production upload step for the `workflow_run` path using
  `pypa/gh-action-pypi-publish@release/v1` with `skip-existing: true`, running under the `pypi`
  GitHub Environment (research.md #2/#5/#7; contract Idempotency/Environment/Pre-upload-
  validation contracts) — `.github/workflows/publish.yml`
- [X] T009 [US1] Extend `tests/static/test_publish_workflow.py` with assertions for the
  `workflow_run` path: the trigger is present and targets `ci.yml`'s `CI` workflow, the `if:`
  checks `conclusion == 'success'`, `head_branch == 'main'`, and `head_repository.full_name ==
  github.repository`, `skip-existing: true` is set on the production upload step, and that step
  runs under the `pypi` environment (contract Trigger/Idempotency/Environment contracts) —
  `tests/static/test_publish_workflow.py`
- [ ] T010 [US1] Manually perform quickstart.md Scenario 4 (merge a change that does not bump
  `__version__`; confirm `publish.yml` completes as a clean, non-failing no-op) —
  `specs/026-pypi-publish/quickstart.md` Scenario 4

**Checkpoint**: User Story 1's mechanics are code-complete and verifiable without any
production side effect (Scenario 4). Its production cutover (Scenario 3) is completed by T016,
after User Story 2's validation below.

---

## Phase 4: User Story 2 - Validate the pipeline safely before it can affect the public listing (Priority: P2)

**Goal**: Prove the publishing pipeline works end-to-end against TestPyPI before it is ever
trusted with the real, public PyPI listing — and keep that capability available for future
backend changes.

**Independent Test**: Manually dispatch `publish.yml` with `target: testpypi`; confirm install
from TestPyPI in a clean environment (quickstart Scenario 1). Re-dispatch without a version
change and confirm an idempotent no-op (quickstart Scenario 2). Entirely independent of User
Story 1's `workflow_run` path — no merge to `main` is required.

### Implementation for User Story 2

- [X] T011 [US2] Add a `workflow_dispatch` trigger to `.github/workflows/publish.yml` with a
  `target` choice input (`pypi` default, `testpypi` alternative), plus a checkout +
  `python -m build` step used only on this path, since there is no preceding `ci.yml` run to
  reuse a `dist` artifact from (research.md #6) — `.github/workflows/publish.yml`
- [X] T012 [US2] Add a `twine check dist/*` step gated `if: github.event_name ==
  'workflow_dispatch'` immediately after T011's build step, then parameterize the upload step's
  destination on the `target` input: `target: pypi` uses the `pypi` environment and PyPI's
  default index; `target: testpypi` uses the `testpypi` environment and `repository-url:
  https://test.pypi.org/legacy/`; both keep `skip-existing: true` (contract
  Environment/Idempotency/Pre-upload-validation contracts) — `.github/workflows/publish.yml`
- [X] T013 [US2] Extend `tests/static/test_publish_workflow.py` with assertions for the
  `workflow_dispatch` path: a `target` choice input exists with `testpypi` as a valid option,
  and the `testpypi` branch resolves to the `testpypi` environment and
  `test.pypi.org`/`https://test.pypi.org/legacy/` (contract Environment contract) —
  `tests/static/test_publish_workflow.py`
- [ ] T014 [US2] Register a Trusted Publisher for this repository on TestPyPI (workflow
  filename `publish.yml`, environment `testpypi`) and create the `testpypi` GitHub Environment
  — manual, one-time, outside this repository (quickstart.md Scenario 1, steps 1-2) —
  `specs/026-pypi-publish/quickstart.md` Scenario 1
- [ ] T015 [US2] Manually perform quickstart.md Scenario 1 (TestPyPI dry run: dispatch with
  `target: testpypi`, confirm install from TestPyPI in a clean environment) and Scenario 2
  (re-dispatch without a version change, confirm idempotent no-op), confirming both expected
  outcomes — `specs/026-pypi-publish/quickstart.md` Scenarios 1-2

**Checkpoint**: The shared plumbing (artifact/build handling, `twine check`, OIDC auth,
`skip-existing` behavior) is now proven against TestPyPI. User Story 1's automatic path is safe
to trust with the real index.

---

## Production Rollout (completes User Story 1)

**Depends on**: T015 (User Story 2's TestPyPI validation) passing — this is the intentional,
spec-documented ordering exception noted at the top of this file, not a phase-numbering error.

- [ ] T016 [US1] Correct the production PyPI Trusted Publisher's workflow filename from
  `ci.yml` to `publish.yml` (FR-009), create the `pypi` GitHub Environment if not already
  present, then merge a real version-bump PR to `main` and manually perform quickstart.md
  Scenario 3 end-to-end, confirming `pip install mfgparams==<version>` succeeds against the
  real, public PyPI index within 10 minutes (SC-001) — `specs/026-pypi-publish/quickstart.md`
  Prerequisites and Scenario 3

---

## Phase 5: User Story 3 - No long-lived publish credentials to leak (Priority: P3)

**Goal**: Confirm the automated publish path never relies on a stored, long-lived PyPI/TestPyPI
credential.

**Independent Test**: Inspect the repository's and both Environments' (`pypi`, `testpypi`)
configured secrets; confirm none exists and every publish authenticates via OIDC only
(quickstart Scenario 6). The underlying OIDC wiring was already built in T003/T006-T008/
T011-T012 and locked in by T005/T009's static assertions — this phase is verification, not new
implementation.

### Implementation for User Story 3

- [ ] T017 [US3] Manually perform quickstart.md Scenario 6: inspect the repository's and the
  `pypi`/`testpypi` Environments' configured secrets and confirm no PyPI/TestPyPI API token
  exists anywhere — `specs/026-pypi-publish/quickstart.md` Scenario 6

**Checkpoint**: All three user stories are independently verified. The feature is complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T018 [P] Add a `CHANGELOG.md` entry under `## [Unreleased]` describing the new automated
  PyPI publishing workflow, per this project's existing changelog convention —
  `CHANGELOG.md`
- [X] T019 [P] Document the release process for maintainers in `DEVELOPMENT.md` (bump
  `__version__`, add a changelog entry, merge to `main` — publishing to PyPI is now automatic;
  cross-reference the one-time TestPyPI dry-run path for future build-backend changes) —
  `DEVELOPMENT.md`
- [ ] T020 Manually perform quickstart.md Scenario 5 (simulate a transient publish failure on a
  `workflow_run`-triggered run, then use GitHub's "Re-run failed jobs" and confirm it publishes
  successfully with no new commit required) — `specs/026-pypi-publish/quickstart.md` Scenario 5

**Note on Constitution Principle XIII**: Not applicable to this feature (confirmed in
`plan.md`'s Constitution Check) — no interactive console/TUI/GUI surface and no external
visual/behavioral reference-fidelity claim, so no Principle XIII-specific manual-verification
task is required beyond the ordinary rollout validation tasks above.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup. Blocks every user story.
- **User Story 1, Part A (Phase 3, T006-T010)**: Depends on Foundational. No dependency on
  User Story 2 or 3.
- **User Story 2 (Phase 4)**: Depends on Foundational. No dependency on User Story 1 — it is
  reachable and fully testable via `workflow_dispatch` alone.
- **Production Rollout (T016, completing User Story 1)**: Depends on Phase 3 (T006-T009) AND
  T015 (User Story 2's TestPyPI validation). This is the one deliberate cross-story dependency
  in this feature, required by spec.md's own User Story 2 rationale — a real, irreversible
  production publish MUST NOT happen before the pipeline has been proven safe on TestPyPI.
- **User Story 3 (Phase 5)**: Depends on Foundational for the underlying OIDC wiring, but its
  verification task (T017) is most meaningful once both Environments exist (i.e. after T014
  and T016), so it is sequenced last among the user stories.
- **Polish (Phase 6)**: Depends on all preceding phases.

### Parallel Opportunities

- T001 (Setup) has nothing else to run in parallel with in its own phase, but has no dependents
  blocking it either.
- T005 (Foundational) can run in parallel with nothing else in Phase 2 (it depends on T003/T004
  existing to have something to assert against, so it follows them, though its own file is
  independent).
- T009 (US1) and T013 (US2) both extend the same file T005 creates
  (`tests/static/test_publish_workflow.py`), sequentially after T005 and after each other where
  both apply — none of the three carry a `[P]` marker, since none can run concurrently with
  another edit to that file.
- T018 and T019 (Polish) touch different files and can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 mechanics only, no production cutover)

1. Complete Phase 1 (Setup) and Phase 2 (Foundational).
2. Complete Phase 3 (T006-T010) — User Story 1's mechanics are demonstrable via the no-op case
   (Scenario 4) without touching the real PyPI index.
3. **STOP and VALIDATE** using quickstart Scenario 4 before going further.

### Full, Safe Rollout (recommended order — differs from priority order above)

1. Setup → Foundational → User Story 1 mechanics (Phase 3) → User Story 2 (Phase 4, TestPyPI
   validation) → Production Rollout (T016) → User Story 3 verification (Phase 5) → Polish.
2. This mirrors quickstart.md's own scenario ordering (TestPyPI scenarios before the real
   production scenario) and is why T016, though labeled `[US1]`, is sequenced after Phase 4.
