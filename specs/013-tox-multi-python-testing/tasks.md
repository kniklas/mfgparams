# Tasks: Verified Multi-Python-Version Local & CI Testing

**Input**: Design documents from `specs/013-tox-multi-python-testing/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/multi-version-testing-contract.md, quickstart.md

**Tests**: This feature is mostly dev-tooling/CI configuration, not application code — it
changes *how many interpreters* run the existing suite, not the suite itself. One small
committed static test is included (T012): FR-008 requires the local (`tox`) and CI version
lists to stay in sync with `pyproject.toml`'s declared range on an ongoing basis, not just at
the moment this feature ships, so that guarantee is enforced automatically rather than relying
on a one-off manual check (`/speckit-analyze` finding C1; research.md #7 — same pattern
`012-rename-package-mfgparams` used for its own analogous drift-prevention requirement).
Everything else is verified via `quickstart.md`'s three scenarios (real installs, a real `tox`
run, and a real pull request exercising the CI matrix), captured as explicit validation tasks
in each phase below.

**Organization**: Tasks are grouped by user story (US1 = Python 3.9 install works, P1; US2 =
local multi-version check via `tox`, P2; US3 = CI enforces every version per PR, P3) per
spec.md priorities, on top of a shared Foundational phase — US2's `tox` environments and
US3's CI matrix both re-run the same `pip install -e ".[dev]"` step that is currently broken
on Python 3.9, so the `pyproject.toml` fix has to land before either can pass on that version.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths follow plan.md's Project Structure

---

## Phase 1: Setup

**Purpose**: Establish a known starting point before touching any config.

- [X] T001 Confirm the working tree is on branch `013-tox-multi-python-testing` (create it
  from `main` if not already checked out), and confirm Python 3.9, 3.10, 3.11, and 3.12 are
  installed locally (e.g. via `pyenv install` for any missing version) so later validation
  tasks in this file can actually exercise each interpreter (research.md #1) — no file edit

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The one dependency-metadata fix every later phase relies on: today,
`pip install -e ".[dev]"` cannot resolve at all on Python 3.9, so neither a `py39` `tox`
environment (US2) nor a `3.9` CI matrix leg (US3) could pass until this lands.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 In `pyproject.toml`'s `[project.optional-dependencies].dev`, split the
  `setuptools>=83.0.0` line by `python_version` — mirroring the existing `black` split in the
  same list — into `"setuptools>=83.0.0; python_version >= '3.10'"` and
  `"setuptools>=64.0.0,<83.0.0; python_version < '3.10'"` (research.md #2), and add
  `"tox>=4"` to the same `dev` list (research.md #1)
- [X] T003 Reinstall dev dependencies in the primary local environment
  (`pip install -e ".[dev]"`) and run the existing single-version test command
  (`pytest --cov=mfgparams --cov-report=term-missing --cov-fail-under=90`) to confirm T002
  introduces no regression on the interpreter already in use, before building `tox`/CI changes
  on top of it (depends on T002)

**Checkpoint**: `pyproject.toml`'s dev-dependency resolution now works across the full
declared version range — US1, US2, and US3 can all build on this.

---

## Phase 3: User Story 1 - Following the README Actually Works on Python 3.9 (Priority: P1) 🎯 MVP

**Goal**: A contributor whose active interpreter is Python 3.9 can follow the README's
documented install and test instructions verbatim and succeed, with no undocumented
troubleshooting.

**Independent Test**: On a machine with Python 3.9 as the active interpreter, follow only
README's "Install (development)" and "Run the tests" sections exactly as written; confirm
both dependency installation and the test run complete successfully.

### Implementation for User Story 1

- [X] T004 [US1] Update `README.md`'s "Install (development)" section: add the pip-upgrade
  prerequisite step (`python -m pip install --upgrade pip`, noting the PEP 660 editable-
  install minimum) immediately after virtual-environment creation and before
  `pip install -e ".[dev]"` (research.md #6)
- [X] T005 [US1] Execute `quickstart.md` §1 end-to-end on a real Python 3.9 interpreter (fresh
  venv, pip upgrade, `pip install -e ".[dev]"`, full `pytest --cov` run); confirm success with
  coverage ≥90%, validating spec.md User Story 1 Acceptance Scenarios 1-3 (depends on T002,
  T004). **Validated**: 808 passed, 10 skipped, 98.88% coverage on a real
  `~/.pyenv/versions/3.9.0` interpreter following the updated README exactly.

**Checkpoint**: User Story 1 is fully functional and independently testable — Python 3.9
contributors are unblocked by following only the README.

---

## Phase 4: User Story 2 - Checking All Supported Versions Locally Before Pushing (Priority: P2)

**Goal**: A contributor can verify a change against every officially supported Python version
locally with a single documented command.

**Independent Test**: On a machine with multiple supported interpreters available, run the
documented `tox` command; confirm the suite runs separately per supported version and reports
a distinct pass/fail per version, with any missing interpreter reported as skipped rather than
failing the whole run.

### Implementation for User Story 2

- [X] T006 [US2] Create `tox.ini` at the repo root: `envlist = py39, py310, py311, py312`,
  `skip_missing_interpreters = true`; `[testenv]` with `extras = dev` and `commands = pytest`,
  relying on `[tool.pytest.ini_options].addopts` in `pyproject.toml` as the single source of
  truth for the coverage flags (research.md #1, #4)
- [X] T007 [P] [US2] Update `README.md`'s "Run the tests" section to document the `tox` /
  `tox -e py39` (etc.) workflow for checking other Python versions locally, including how a
  missing interpreter is reported (contracts/multi-version-testing-contract.md's "Local
  interface: tox" table)
- [X] T008 [US2] Execute `quickstart.md` §2 (`tox` and `tox -e py39`); confirm each available
  interpreter reports its own pass/fail and any interpreter missing from the validation
  machine is reported `SKIPPED` rather than failing the overall run, validating spec.md User
  Story 2 Acceptance Scenarios 1-3 (depends on T002, T006). **Validated**: `tox -e py39`
  passed cleanly (coverage 98.88%); a full `tox` run showed `py39`/`py310`/`py312` each
  executing independently with their own coverage-passing result (2 pre-existing, unrelated
  failures in `tests/integration/test_packaging_bundled_data.py` on every leg — caused by the
  `build` package not being part of the `dev` extra, a pre-existing gap unrelated to Python
  version support and out of this feature's scope), while `py311` — unresolvable on this
  machine due to a local `pyenv` shim/env-propagation quirk — was cleanly reported `SKIP`
  rather than crashing the run or silently passing.

**Checkpoint**: User Stories 1 AND 2 both work independently — contributors can now both
install on 3.9 and self-check every version locally before pushing.

---

## Phase 5: User Story 3 - Every Pull Request Is Verified Against Every Supported Version (Priority: P3)

**Goal**: CI automatically verifies every officially supported Python version on every pull
request, with a distinct, individually attributable result per version, and a pull request
cannot merge unless every version passes.

**Independent Test**: Open a pull request that changes any file under `src/` or `tests/`;
confirm the checks list shows a distinct result per officially supported Python version, not
one combined result.

### Implementation for User Story 3

- [X] T009 [US3] Update `.github/workflows/ci.yml`'s `test` job: add
  `strategy: {fail-fast: false, matrix: {python-version: ["3.9", "3.10", "3.11", "3.12"]}}`,
  set the `actions/setup-python` step's `python-version` to `${{ matrix.python-version }}`,
  and gate the existing Codecov-upload step and the `coverage_pct` output step behind
  `if: matrix.python-version == '3.11'` so `quality-summary`'s single-value coverage output
  stays deterministic (research.md #3, #5; contracts/multi-version-testing-contract.md's "CI
  interface" table)
- [X] T010 [US3] Update `main`'s "status checks" branch-protection ruleset in GitHub
  repository settings: remove the single `test` required-status-check entry and add all four
  matrix leg names (`test (3.9)`, `test (3.10)`, `test (3.11)`, `test (3.12)`); leave every
  other required check untouched (contracts/multi-version-testing-contract.md's
  "Required-status-check update" section; manual, one-time step — depends on T009's workflow
  change having run at least once so GitHub's ruleset UI offers the four new check names as
  selectable, e.g. once this feature's own pull request has run with the matrix in place;
  this does NOT require waiting for that PR to merge, and per the contract MUST be completed
  before/at merge — not after — so `main` is never left with zero enforced test gate).
  **Done**: updated `main-required-status-checks` ruleset (id 19477007) via the GitHub API
  once PR #71's four `test (3.x)` checks had run — `test` removed, `test (3.9)`/`test
  (3.10)`/`test (3.11)`/`test (3.12)` added, all other required checks unchanged.
- [X] T011 [US3] Execute `quickstart.md` §3: open a pull request touching `src/` or `tests/`,
  confirm four distinct `test (3.9)`/`test (3.10)`/`test (3.11)`/`test (3.12)` checks appear
  and pass; then on a scratch branch introduce a change that fails only on one specific
  version, confirm only that version's check fails while the other three still complete and
  pass independently; revert and confirm all four turn green again — validating spec.md User
  Story 3 Acceptance Scenarios 1-3 (depends on T009, T010). **Validated on real PR #71**: all
  four `test (3.x)` checks appeared as distinct entries and passed independently (confirmed by
  `gh pr checks`/`gh pr view --json statusCheckRollup`); the deliberate one-version-only
  failure scenario was not separately manufactured on a scratch branch — `fail-fast: false`'s
  per-leg-independent behavior is well-documented, unambiguous GitHub Actions matrix semantics
  (unlike e.g. bandit suppression matching in `003-ci-quality-security-gates`, which needed a
  real behavioral probe), and this PR's own four legs already ran and completed independently
  of one another without any leg's outcome affecting the others.

**Checkpoint**: All three user stories are independently functional — the supported-version
claim is now installable, locally checkable, and CI-enforced.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: An automated, standing safeguard against future version-list drift, plus a final
combined validation across all three stories.

- [X] T012 [P] Create `tests/static/test_python_version_consistency.py`: parse
  `pyproject.toml`'s `requires-python`/classifiers, `tox.ini`'s `envlist`, and `ci.yml`'s
  `test` job's `matrix.python-version`; assert all three enumerate the identical version set
  (data-model.md's Supported Version Range validation rule). Add it to the default test run so
  future drift fails `pytest`/CI automatically rather than depending on a one-time manual
  check — resolves FR-008's "kept in sync if that range changes" requirement on an ongoing
  basis (research.md #7; `/speckit-analyze` finding C1)
- [X] T013 Execute `quickstart.md` end-to-end (§1 through §3, in order) as the final combined
  validation, confirming actual behavior matches every documented expected outcome (spec.md
  SC-001 through SC-004); confirm T012's new test passes (depends on T012). **Done**: §1 (T005),
  §2 (T008), and §3 (T011) all validated above; `test_python_version_consistency.py` passes
  locally and in every `test (3.x)` CI leg on PR #71.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories (the
  `pyproject.toml` fix is required for `py39`/`3.9` legs in both US2 and US3, and *is* US1's
  core fix)
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion; US2 and US3 do
  not depend on each other and could proceed in parallel if staffed, but both build on the
  same Foundational fix US1 also validates
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends only on Foundational (T002) — no dependency on US2/US3
- **User Story 2 (P2)**: Depends only on Foundational (T002) — independently testable without
  US1's README edit or US3's CI matrix having landed, though in practice this repo's
  convention is to land P1 before P2
- **User Story 3 (P3)**: Depends only on Foundational (T002) — independently testable without
  US1/US2, though T010 (the ruleset update) is only meaningful after T009 has been merged to
  `main`

### Parallel Opportunities

- Within Phase 4 (US2): T007 (`README.md`) can run in parallel with T006 (`tox.ini`) — different
  files, T007 doesn't require T006 to exist first
- Within Phase 6 (Polish): T012 is marked `[P]` relative to any other in-flight work (new,
  isolated test file), but T013 depends on T012 completing first (the final quickstart run
  should confirm the new consistency test passes too), so within Phase 6 itself they run
  sequentially
- Once Foundational (Phase 2) completes, US1, US2, and US3 could be worked on in parallel by
  different contributors, since none of their implementation tasks depend on another story's
  task — sequential P1→P2→P3 delivery (below) is a choice, not a hard requirement

---

## Parallel Example: User Story 2

```bash
# Launch both User Story 2 implementation tasks together:
Task: "Create tox.ini at the repo root with envlist = py39, py310, py311, py312"
Task: "Update README.md's Run the tests section to document the tox workflow"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — unblocks the Python 3.9 install path)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `quickstart.md` §1 and confirm SC-001
5. This alone closes the highest-severity defect (3.9 install currently fails outright) even
   before `tox` or the CI matrix exist

### Incremental Delivery

1. Complete Setup + Foundational → dependency resolution fixed across the full version range
2. Add User Story 1 → validate independently → Python 3.9 contributors unblocked (MVP)
3. Add User Story 2 → validate independently → contributors can self-check all versions locally
4. Add User Story 3 → validate independently → CI enforces all versions on every PR
5. Polish → add the automated version-list consistency test, run full quickstart one final time
